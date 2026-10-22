# Report 86 — minimal `[sbuf-final]` selection log and matching host

Offline only: no guest, no shader rebuild/translation, no profile/base/facts/library/translator/lock change, no other NVN
logic touched. Local armyja commit `cac7c6f755c7b1513f420261faf53d0b7f06b4b8`; no amend, no push/PR.
Host: `linkcheck/dmhost-vs110-sbuffinal`. Build headers: `ssbo-vs110-correct645` (chain `26c9ad81719f`).

## 1. The diff (only `dm/gfx/nvn/nvn_mtl.m`, +9/−1)

[Fenced excerpt omitted from the shareable research record.]

- Preserved verbatim: the `u` condition, the `mtl_gpu_addr` call and its argument (`u->size ? u->size : 1`), `use_rec`,
  `slots[aid] = gpu`, both `USE` calls, the dummy branch, and the old B line.
- The success branch only gains `resolve_success = 1`. On failure `mb/mo/gpu` are never read; the reported slot is always
  the value finally stored in `slots[aid]`, and the log never infers `real` from a non-zero slot (a dummy slot may be
  non-zero).
- No new environment switch, parser, helper, header or state; the guard is the existing `g_kd_force`, and the log is
  emitted only for `NVN_RB_SBUFP` (UBOP unchanged, no log).
- Fields: frame, pass counter, stage, shader key, reg, aid, `u` presence, original `u->addr`/raw size (0 when absent),
  effective resolve size, `resolved` 0/1 with `actual` real/dummy, the final `slots[aid]` value (a GPU address, not a
  texture rid/serial) and `rw`.

## 2. Host and tool-scope verification

- `linkcheck/dmhost-vs110-sbuffinal`, full sha256
  `70c76712facf3a519fd69e421359d71db4790bfc8a4faacc504a296d0bd04275`; build rc 0, 0 errors; compile line and log saved
  (`dmhost-vs110-sbuffinal.compileline` / `.build.log`).
- Built with the `ssbo-vs110-correct645` generated headers first: embedded chain `26c9ad81719f` appears once,
  `012cc15f1405` and `9f73847b56ec` zero times; `sbuf-final` present once. Macros: SSBO base 0x110 for stage 0 / 0
  otherwise, image 0x120 slots 1, tex slots 16.
- Checked with the real chain tool: `dmsh_chain.FILES` does **not** contain `nvn_mtl.m` and `version()` is still
  `26c9ad81719f`, so the existing library was not rebuilt and the chain was not refreshed. `dmhost-vs110`, older hosts and
  the shared `dmhost` were not overwritten; the launch plan was not pointed at this host.

## 3. What is verified and what is not

- Static review of the selection path: the only behavioural addition is the flag assignment; no extra lookup, no guest
  read, no resource materialisation.
- Wiring verified by a successful compile of the real renderer into the experiment host.
- **Not verified:** the new log has never been emitted (no guest run). It would prove only which value `encode_args`
  finally wrote into the argument slot; it is not GPU execution, not an access/content proof, and not proof that the NVN
  register mapping is correct.

## 4. Draft for a future candidate-behaviour acceptance (not implemented, no launch)

- `DM_NVN_KEYDUMP=7faa92fddfdd06bd:1` — the switch matches by the fragment key, so this selects the draw whose PS is the
  partner of the target VS.
- Expected in the same pass: `K … st0 key=9b770cf888d729bd…`, one `[sbuf-final] … st0 key=9b770cf888d729bd…`, and the draw
  record `d` naming that VS/PS pair. Both `actual=real` and `actual=dummy` are terminal results; the run must not wait for
  `real`. `DM_NVN_IMGBIND`, `DM_NVN_PSOFAIL_RT` and `DM_NVN_SSBO_OBS` stay unset so the run does not stop before the draw.
- If the first `KEYDUMP` match lands on a different vertex shader, report "target not obtained"; do not raise the count,
  change inputs or rerun. The supervisor and a launch are not authorised by this report.
