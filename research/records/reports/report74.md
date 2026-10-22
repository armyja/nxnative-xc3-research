# Report 74 — corrected design: vertex SSBO slot snapshot at the top-level replay draw

Offline, design only, 20 minutes. No implementation, compile, translation, profile change, guest or commit. HEAD
`82f488b`. This supersedes report73; that file keeps its header pointing here.

## 1. The three corrections, with the code that forces them

1. **Identity.** `prog_get` (`nvn_mtl.m:2871-2905`) creates the `NvProg`, and for each stage calls `shader_get`; when that
   fails it logs the RED and leaves `o->sh[st]` nil — then still `serial_put`s and returns the object. So after a load
   failure there is an `NvProg` with a nil vertex shader, and `serial_get` (a read of the serial table) cannot give back
   the failed stage's key. `prog_key` may also compute a hash from `p->sd[st]` (the control section the game may have
   freed), so it must not be used either. Identity therefore comes only from `prog_key_cached`, which is lookup-only under
   `g_pk_mu` (`hle_nvn.c:494`) and returns 0 for an entry it does not have.
2. **`skip_d` is not a skip.** `draw()` at `:6147` computes `skip_d = mode != 0`, where `mode` is the depth/stencil
   attachment-omission mode; `:6153` only increments statistics, and the draw continues through pipeline fetch and
   encoding. It must not suppress the observation and is removed from the "skipped" classification.
3. **No final-pass claim.** The top-level hook runs before `draw()` and therefore before `rp_begin_ex` opens the encoder;
   `g_stat_pass` is a running counter at that moment, not the final pass serial, and `g_pass.serial` does not exist yet.
   The record must not present either as the draw's final pass, and "same-pass" association is out of scope this round.

## 2. The hook, precisely

- **Where**: the real replay switch (`nvn_mtl.m:~7440-7452`), in the `OP_DRAW` / `OP_DRAW_IDX` cases:
  `if (g_rc_skip) { …counts…; break; }` then the new read-only call, then `draw(a, NULL)` / `draw(NULL, a)` unchanged.
- **Identity**: `const prog_t *p = S.bst[0];` — `bind_stages` (`:3183`) writes `S.bst[st]` per NVN stage bit and
  `S.bst[0]` is the vertex binding source, which is where this hook gets its stage context. Then
  `for (unsigned i = 0; i < p->nstage && i < 8; i++) if (prog_key_cached(p, i, key)) …` — `i` is an **input index**,
  not a stage.
- **Never**: `serial_get`, `prog_get`, `shader_get`, `prog_key` (hash), any read of `p->sd[i].control/data`, any
  allocation, any materialisation.
- **Semantics**, per draw: let `n` be the number of cached keys and `hit` the index whose key equals the target.
  - `hit >= 0` → **hit** (target identified for this draw; `n` may be smaller than `nstage`, and the record says how many
    entries were readable);
  - `hit < 0` and `n == nstage` → **no target this draw**;
  - `hit < 0` and `n < nstage` → **identity unknown**: some entries could not be read and one of them might be the
    target, so it is never reported as "target absent". One line per run, plus a counter, exactly as `imgdiag_match`
    (`:5975-5995`) already does for the fragment program.
- If `S.bst[0]` is nil, there is no vertex binding: no record, no unknown line (nothing was unreadable).

## 3. Call order (with anchors)

[Fenced excerpt omitted from the shareable research record.]

The last comparison matters: the snapshot is taken **before the original replay draw command**, so it says nothing about
the encoder, the pipeline, GPU submission or execution, and a later load failure cannot invalidate it.

## 4. Record (scalars only)

One bounded record per run, first hit only, then disarm:

- `obs_seq` (a counter incremented at every real draw the hook sees), `frame`;
- `pass_counter=<g_stat_pass>` explicitly labelled **not the final pass** (no `g_pass.serial`, no same-pass wording);
- vertex program `nstage`, `cached=n/nstage`, per input index the cached key in hex or `unknown`, `hit=<i>`;
- the 16 vertex slots `S.ssbo[0][i]`: raw `addr`, `size`; observation-owned `last_bind{stage, index, seq, frame}` for
  each slot, updated only by the real `OP_BIND_SSBO` case and kept across frames and programs;
- `candidates` = number of slots with `addr != 0`; `ambiguous` = `candidates > 1`.

No guest memory is read, `mtl_gpu_addr` is not called, and a non-zero `addr` is never described as an actual GPU
resource.

## 5. Evidence levels (kept from report73, with the circularity note)

- one non-zero slot → unique **candidate** NVN reg `r` for this observation;
- two or more → **ambiguous**, no reg chosen, no tie-break from NVSD handle, translator slot or list index;
- none → no candidate;
- a slot last bound in an earlier frame is reported with that bind's frame and sequence, never as "unbound"; a slot whose
  provenance was never observed is `unknown-provenance`, distinct from `never bound`;
- one offset plus candidate `r` yields only `baseCandidate = off − 16·r`, for this observation, not title-wide and not a
  stride proof;
- `nvn_mtl.m:3924` fills the host arena's c0 table from `S.ssbo` at `DM_GAME_NVN_SSBO_BASE`; reading that table back is
  host-synthesised and cannot evidence the base. In the paths checked this round no profile-independent raw guest c0
  source was found; that is a check result, not a claim about the whole workspace or history.

## 6. Future acceptance (design-level; nothing added or implemented here)

| case | expected |
|---|---|
| switch off / invalid value | no copy, no event; invalid logs once and stays off; dispatch identical |
| target hit with other entries uncached | hit recorded, `cached=n/nstage` shown |
| no hit, all entries cached | "no target this draw", no unknown line |
| no hit, some entries uncached | identity unknown, one line + counter, never "absent" |
| `g_rc_skip` draw | skipped counter only, still armed, no binding record |
| `skip_d` draw | treated as a normal draw: snapshot emitted, no skip classification |
| target program fails to load later | snapshot already emitted; record makes no load claim |
| slot bound in an earlier frame | reported with that bind's frame and sequence |
| bind before program bind | last_bind metadata survives the later program bind |
| several input indices | loop bounded (i < nstage, i < 8), each cached key or unknown recorded |
| predictor/lookahead scan | no events (call-order: no observation call from `state_op` or the scans) |
| real dispatch case chain | `OP_BIND_SSBO` is its own label; the grouped UBO/TEX/SAMP/… labels are unchanged and nothing falls through (the `OP_BIND_IMG` lesson); static check of the switch text |
| multiple non-zero slots | ambiguous, no reg |
| one non-zero slot | unique candidate reg |

A no-guest harness that drives the **real** dispatch switch does not exist in the tree and this round does not add one;
the table is a future acceptance list, not an executed test.

## 7. Unknowns

The real vertex storage-buffer table base; the correspondence between NVSD handle, translator slot and NVN reg; whether
the target draw's 16-slot read is unique; which final render pass the draw belongs to (needs a separate association
design); and whether a non-circular guest c0 source can be obtained at all. No base, reg, converter, profile, library or
tool change; no implementation authorisation is assumed.
