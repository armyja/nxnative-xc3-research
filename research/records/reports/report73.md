# SUPERSEDED — see report74 for the corrected design

This version is kept for the record. Three substantive errors, corrected in report74:

1. **Identity after load failure is wrong.** `prog_get` (`nvn_mtl.m:2871`) caches and returns the `NvProg` even when a
   stage's `shader_get` failed: that stage's `o->sh[st]` is nil, and `serial_get` cannot recover its key. Therefore the
   claim that the draw is "resolved with keys and only fails at pipeline creation" is withdrawn, together with
   "draw submitted" — the existing RED lines prove a program-load attempt, not GPU submission. Identity must come from
   `S.bst[0]` plus `prog_key_cached` at the top-level draw hook, never from `serial_get`/`prog_get`/`shader_get`.
2. **`skip_d` is not a skipped draw.** At `:6147` it is the depth/stencil attachment-omission mode (`mode != 0`) and the
   draw proceeds through pipeline fetch and encoding; `:6153` only counts. It must not suppress the diagnostic, and the
   "depth skip" classification is removed. Only a real `g_rc_skip` command skip is a known-skipped draw.
3. **`g_stat_pass` is not the final pass serial.** The top-level hook runs before `rp_begin_ex`, so `g_pass.serial` does
   not exist yet; recording `g_stat_pass` as the draw's final pass (or as same-pass evidence) is wrong. The revised design
   records a replay draw-observation sequence and labels the pass counter as unassociated.

# Report 73 — minimal independent observation design for the target VS's SSBO slots (design only)

Offline, read-only, 20 minutes: no implementation, no compile, no translation, no profile/value change, no guest, no
commit. HEAD `82f488b`. Nothing was added to the tree; the design below is the deliverable.

## 1. What already exists as evidence

- The target vertex shader **is requested in real runs** and is rejected by the loader for the missing `reg`:
  `run-foutuint-20261021-192649/boot.log` and `run-psort-20261021-190120/boot.log` each contain
  `[RED] shader 9b770cf888d729bd_b reflection conversion failed: B binding vp_s0 has no resolved slot number` and
  `[RED] shader 9b770cf888d729bd (vertex) failed to load: …` (2 hits per log). So the scene is reachable and the draw
  is submitted; what it does not provide is any same-draw record of the SSBO slots.
- No existing log or diagnostic reports the vertex SSBO table for that draw, so this round delivers the design only.

## 2. Where the hooks are (real replay path)

- Real dispatch switch: `nvn_mtl.m:~7440-7452`. `OP_DRAW` / `OP_DRAW_IDX` call `draw(a, NULL)` / `draw(NULL, a)`;
  `OP_BIND_SSBO` currently sits in a **grouped label chain** (`case OP_BIND_SSBO: … state_op(h.op, a); break;`) together
  with program/UBO/texture binds. Splitting it needs its own `case`, exactly like the existing `OP_BIND_IMG` case, or
  the earlier labels fall through into the new body (the regression that was already fixed once for `OP_BIND_IMG`).
- `state_op` (`:4169`, `OP_BIND_SSBO` at `:4196`) is **also** called by the lookahead/predictor paths with `S` saved and
  restored (`fz_probe_cov2` at `:4272-4286` and the precompile scan at `:4230-4258`). It must never emit an event or
  mutate observation state.
- Real draw: `draw()` at `:6040`. It resolves the program with the materialising `prog_get` (`:2871`), then fetches the
  pipeline. A snapshot placed **after** `pr`/`vs`/`fs` are resolved and **before** the pipeline fetch is reached on every
  real draw, including the one whose shader later fails to load (the failure happens at pipeline creation, not before),
  and it is after the program identity exists.
- Identity must use the lookup-only path: `serial_get(p->serial)` (`:1341`) never creates; `prog_get` does materialise
  and must not be called by the diagnostic. If the program has not been materialised at snapshot time, the identity is
  recorded as unknown and nothing is forced.

## 3. What to record (scalars only)

At the first real draw whose vertex key equals the target (one-shot, then disarm):

- frame, global pass serial (the one the `K`/`d` records use), program serial, vertex key, fragment key if available;
- for **all 16** vertex slots `S.ssbo[0][i]`: `addr`, `size` (raw), plus observation-owned metadata updated only on real
  binds: last real bind stage, index, sequence number, frame. The metadata persists across frames and programs; a slot
  with no recent bind is reported with its last bind, never as "unbound" by default;
- `index` is the NVN bind index used by `OP_BIND_SSBO`; it is not the stage, and the observation loops over input indices
  while keeping the stage fixed;
- a candidate count computed from the non-zero slots, with the rule below;
- no guest memory is read, `mtl_gpu_addr` is not called, and a non-zero `addr` is never described as an actual GPU
  resource.

## 4. Evidence levels (stated in the record itself)

- exactly one non-zero slot → "unique candidate NVN reg r for this draw";
- two or more non-zero slots → "**ambiguous**": no reg is chosen, and the NVSD handle / translator slot / list index is
  never used to break the tie;
- no non-zero slot → "no candidate"; a slot that was last bound in an earlier frame is reported with that frame, not as
  absent, because a table entry can legitimately persist without a new bind in this draw;
- with one offset and candidate `r`, the only permissible statement is `baseCandidate = off − 16·r` for this observation,
  never a title-wide value or a stride proof;
- **circularity**: `nvn_mtl.m:3924` fills the host arena's c0 table from `S.ssbo` at `DM_GAME_NVN_SSBO_BASE(stage)`.
  Reading that synthesized table back is host-generated, not a guest write, and cannot be evidence for the base. No
  profile-independent raw guest c0 snapshot exists in this workspace; the guest's c0 bytes are not retained anywhere, so
  there is currently **no** non-circular raw-table source to read.

## 5. Wiring risks the implementation must respect

- No event from `state_op` (predictor scans call it); observation state must live outside it and be updated only from a
  new, separately labelled `case OP_BIND_SSBO` in the real switch plus the draw hook.
- The draw hook must not materialise a program, texture or pipeline; only read `S.bst[0]->serial` (lookup-only) and the
  already-resolved `pr`.
- Conditional skips (`g_rc_skip` for render-condition, `skip_d` for depth-only) must be counted as separate bounded
  events with their own counters, and must not emit a binding record; a skipped draw cannot be claimed observable.
- Program-load failure must still produce the pre-draw snapshot (the hook is before pipeline creation); the record notes
  whether the pipeline was then obtained or not, without pretending to be an execution result.
- Diagnostic off: the switch case, the draw hook and every counter must be inert; dispatch must be byte-for-byte the
  same as today.

## 6. Minimal design and falsifiable acceptance

Switch: `DM_NVN_SSBO_OBS=<16-hex vertex key>`, parsed once, default off, invalid value logs once and stays off, one
record per run (then disarm). Record: one header line plus 16 slot lines plus a `done` line with an explicit
`candidates=N` and `ambiguous=0|1`.

Acceptance cases (design-level, to be tested by whoever implements it):

| case | expected |
|---|---|
| no target draw | no record, dispatch unchanged |
| identity unknown (program not materialised) | record `identity=unknown`, no materialisation |
| draw skipped by render condition / depth skip | separate counter, no binding record |
| no non-zero slot | `candidates=0`, no reg |
| exactly one non-zero slot | `candidates=1`, unique candidate reg |
| two or more non-zero slots | `ambiguous=1`, no reg chosen |
| stale slot from an earlier frame | reported with its last bind frame, not treated as unbound |
| bind earlier than the program bind | still recorded, with bind sequence ordering |
| several shader input indices | loop over input indices, stage fixed |
| predictor scan runs | zero events from `state_op` paths |
| target shader fails to load | pre-draw snapshot still emitted |
| diagnostic off | identical dispatch |

Testability without a guest: a small in-process harness that feeds a synthetic command stream through the **real**
replay dispatch switch (not a helper re-implementation) would cover the case split and the draw hook; it does not exist
today and this round does not add it, so no claim that the wiring is tested is made. A static check that the new case is
outside the label chain is the minimum.

## 7. Unknowns (unchanged)

The real vertex storage-buffer table base; whether the one NVSD storage buffer corresponds to `vp_s0`; whether a single
16-slot read at that draw is unique; and whether any non-circular guest c0 source can ever be obtained. No base change,
no reg change, no converter change, no new experiment was run.
