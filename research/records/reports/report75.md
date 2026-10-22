# Report 75 — DM_NVN_SSBO_OBS implemented, unit and wiring tests, experiment host built

Offline only: no guest, no shader translation/build, no profile/base/slots/facts/library change. Local commits by armyja,
no push/PR. Budget note: this took slightly over the 30-minute window (final verification and the path fix ran past it);
nothing was relaxed to fit.

Final HEAD: `ae2e3c49c502fbb10ea83dbd02fb4c0a3b00abfe` (diagnostic commit `0567402a`, path fix `ae2e3c4`).

## 1. Scope of the change

| file | change |
|---|---|
| `dm/gfx/nvn/nvn_ssboobs.h` | new: pure parse/verdict/bind/format helpers, `SSBO_OBS_STAGES 6`, 16 slots, bounded formatting |
| `dm/gfx/nvn/nvn_mtl.m` | arm at `mtl_exec`, own `OP_BIND_SSBO` case, draw hook after `g_rc_skip`, one-shot record |
| `dm/gfx/nvn/tests/t_ssboobs.c` | new: pure unit tests |
| `dm/gfx/nvn/tests/gen_switch_wiring.py` | new: extracts the real switch cases and compiles a stub harness |

## 2. Behaviour

- `DM_NVN_SSBO_OBS=<16 lowercase hex vertex key>`: parsed once at `mtl_exec`; absent or invalid latches closed, invalid
  logs once; when off nothing queries keys, copies slots or counts.
- Real `OP_BIND_SSBO` is its own case (`nvn_mtl.m:7528` at commit time, outside the grouped label chain, which no longer
  contains it): `state_op(h.op, a)` unchanged, then `ssbo_obs_bind(a)`; only stage 0 and index < 16 are recorded, with
  frame and bind sequence; other stages and out-of-range indices do not touch the vertex table.
- Real `OP_DRAW` / `OP_DRAW_IDX`: after the `g_rc_skip` check, before `draw()`: `ssbo_obs_draw()`. Known skip increments
  a counter and stays armed; `skip_d` (attachment omission) is untouched and not treated as a skip.
- Identity: `S.bst[0]` (raw `prog_t`), `prog_key_cached` per input index, no `serial_get`/`prog_get`/`shader_get`/
  `prog_key`, no control/data reads, no hash. Capacity is the real `sizeof p->sd / sizeof p->sd[0]` = 6; `nstage == 0`
  or `> 6` fails closed as invalid count (never truncated into "all cached" or "target absent"); a nil `S.bst[0]` is
  silent. Partial cache with no hit is `identity-unavailable` (once, plus counter, "not evidence that the target is
  absent"); a hit stands even when other entries are unknown.
- First hit records once: `obs_seq`, `frame`, `pass_counter` explicitly labelled `(unassociated-final-pass)`, `nstage`,
  `cached=n/nstage`, `hit`, per-index key or `unknown`, then 16 slot lines (raw `addr`/`size`, per-slot real bind
  provenance with frame/seq, `explicit-unbind` for a zero addr with a real bind, `unknown-provenance` when no bind was
  ever observed) and a `done` line with `candidates` and `ambiguous`; then closes. Format overflow logs an explicit
  error and closes without a normal done line.
- No GPU object, no `mtl_gpu_addr`, no guest memory read; an `addr` is never called an actual GPU resource. The
  host-synthesised c0 table is not used as evidence.

## 3. Tests actually run

- `t_ssboobs.c`, `clang -O1 -Wall -Wextra -fsanitize=address,undefined`: **25 checks, fails: none**. Covers absent/
  short/uppercase/invalid parse, 0/6/7-entry verdicts, partial cache without and with a hit (including hit at index 1),
  bind from another stage and index 16 ignored, provenance update and closed-state binding, zero/one/two candidates,
  explicit-unbind vs unknown-provenance wording, worst-case slot line, and a short buffer reporting failure.
- `gen_switch_wiring.py`: extracts the real `OP_DRAW`, `OP_DRAW_IDX`, `OP_BIND_SSBO` and grouped-label cases from
  `nvn_mtl.m` (lines 7522, 7523, 7528, 7530-7532 at commit time) into a stub harness, compiles it with clang and runs
  **12 checks, fails: none**: each opcode reaches `state_op` exactly once with its own opcode; only `OP_BIND_SSBO` calls
  the bind diagnostic; `DRAW`/`DRAW_IDX` call the snapshot once and strictly before `draw`; a known skip calls neither
  and increments the counter; a predictor-style `state_op` call produces no observation event.
- Limits: the harness stubs `state_op`, `draw` and the imgdiag hooks, and only covers the extracted case bodies and the
  label chain; it is not a renderer test and does not exercise `draw()`, encoders or the GPU. The unit test covers only
  the pure helpers. No claim that the full wiring is exercised.

## 4. Experiment host

- `linkcheck/dmhost-ssboobs`, full sha256 `d1289a9af69eb7a89c4f42758a7505ce9c6b1d5c087f2156b9fb95f04c2879b1`.
- Built with the existing `fout-uint-correct645` profile (**vs base still 0**, img base 0x120, img slots 1, tex slots 16)
  and its library chain `012cc15f1405`; headers generated from that profile into the experiment directory
  (`game_profile.h` + `dmsh_chain.h`), embedded chain appears once, old `9f73847b56ec` zero times.
- `linkcheck/dmhost-ssboobs.compileline` and `.build.log` saved; rc 0, 0 errors. Shared `dmhost`, old hosts and
  `dm/host` untouched.

## 5. Not done / gaps

- No guest run, so the diagnostic has never produced a record; only its build and offline tests exist.
- No base conclusion: the real vertex storage-buffer base is still unmeasured, `handle`/`slot`/`reg` correspondence
  remains unproven, and the synthesised c0 cannot evidence it.
- The host was compiled without sanitizers (ASan/UBSan apply to the unit test only).
- The record's `pass_counter` is explicitly not associated with the final render pass; a separate design is still needed
  for that.
