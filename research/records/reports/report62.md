# Report 62 — pass-attachment provenance diagnostic implemented, one experiment host built (no run)

Scope: offline implementation + SSD host build only. No guest run, no shader build, no profile/facts/value change.
Baseline `5c5120f`; local commit `dcb7fdf7f6725e6fb6fa8a6dc363378b50ca7743` (author armyja, no amend, no push/PR).

## 1. Supervisor's two design corrections, accepted and reflected

- `pso_get_` is called **from inside `draw()`** (`nvn_mtl.m:6041`), not before it. The diagnostic therefore consumes its
  record from that draw's own pipeline fetch, and never claims to be "before the draw".
- `newRenderPipelineStateWithDescriptor:` also exists in the background precompile (`:3426`) and the prewarm
  (`:3513`). Those paths have no `g_pass`/`R` context of this draw. The record is produced **only** by the real
  `pso_get_` failure branch (`:3460`) and its cached-failure branch (`:3449`); nothing was added to `pso_pend_kick`,
  `pso_desc`, prewarm or precompile.
- The Metal message names no colour index. "target0 = 103" is **not** asserted: the slot-0 line in the table below is a
  pending observation, not a fact, and the old nearby `RED_ONCE` is not used as an association.

## 2. What was added (diff)

One file, `dm/gfx/nvn/nvn_mtl.m` (+102/−2), no new file, no build-system change, no `dmsh_chain` file list change (that
list covers `tools/*` only, so no shader rebuild and no lock change).

- `psort_slot` + `g_psort` (fixed 8 slots, scalars only, ~600 bytes, no allocation, no retained GPU object).
- `psort_arm()`: `DM_NVN_PSOFAIL_RT=<16-hex fragment key>`, parsed **once**. Empty/absent → mode 0 (off). Wrong length or
  non-lowercase-hex → one `MLOG` line and disabled. Valid → one `MLOG` line and armed.
- `psort_match(key)`: exact 16-hex match with an optional `_b` suffix (the host's `fs->key` carries `_b`); a `_bf` or any
  other suffix does not match. No hardcoded XC3 target.
- `psort_capture(pd)`: called from the real `rp_begin_ex_` immediately after `g_pass.serial` is assigned and
  `g_pass.cfmt[]` is filled from the attached `pd` views (`:2464-2467`). Copies only scalars. Does nothing unless armed.
- `psort_report()` / `psort_cached()`: defined after the `g_fz` declaration (`:4562`), prototypes before `pso_get_`.
- Call sites: `if (hm_get_id(&g_pso_fail, &k)) { psort_cached(vs, fs); return nil; }` and, in the `!ps` branch,
  `psort_report(&k, vs, fs, ms_fn);` placed **after** the unchanged RED `MLOG` and before `hm_put_id`.

## 3. When the snapshot is captured, and how it is bound to `g_pass.serial`

Capture point: `rp_begin_ex_`, after `uint64_t ser = g_pass.serial + 1; memset(&g_pass, ...); g_pass.serial = ser;` and
after the loop that sets `g_pass.cfmt[i] = pd.colorAttachments[i].texture.pixelFormat`. At that moment `pd` is the real
descriptor the encoder will use and `g_pass.serial` is the pass identity that `pso_get_` later keys on
(`pso_key_fill(&k, vs, fs, g_pass.cfmt, ...)`, `:3444`). The snapshot stores `g_pass.serial`, `g_stat_pass`,
`g_cur_frame`, the `cfmt[8]`, `dfmt`, `sfmt`.

Binding evidence, printed in the record: `assoc=same-pass` only when **both** `snapshot.serial == g_pass.serial` **and**
`memcmp(k->cfmt, snapshot.cfmt) == 0`; otherwise `assoc=mismatch` and `snap=missing`/`valid` is shown. On mismatch the
record is still printed but makes no association claim and does **not** fall back to `R.rt`.

## 4. When the target failure consumes it

Only `pso_get_` (real replay path, called at `:6041`): (a) cached-failure branch `:3449` → `psort_cached()` prints
`cached failure … no descriptor record … no cache clear, no recompile` and disarms; (b) `!ps` branch `:3460` →
`psort_report()` prints the full record and disarms. The cache is not cleared, the PSO is not recompiled, no draw is
forced, and merge/prewarm/prediction are left as they are.

## 5. Merge / lmap, as recorded

`g_pso_lmap` (physical → logical colour mapping, set at `:6040` for readable-tile merge) and `g_pso_fsfn` are copied into
the key at `:3445` (`k.lmap[8]`, `k.fsfn`); `ms_fn` may override `fsfn` at `:3447`. The record prints `lmap=`,
`fsfn=`, `ms=`, `fzkind=` so a physical attachment index is not read as a logical shader colour location. `fz=`/`phase=`
and `defer=` (`g_defer_replaying`) and `fzchk=` (`g_fz_checking`) are printed as the actual context; none of them is
described as a top-level draw when it is not one.

## 6. 8-slot record format and missing-value rules

One header line, eight slot lines, one completion line `[psort] done key=… pass=… assoc=… slots=8`; each line is
formatted into a 512-byte stack buffer, so truncation is bounded and detectable by the missing `done` line. Per slot:

[Fenced excerpt omitted from the shareable research record.]

Rules: `nvn=0` means no live NVN candidate in that slot (only `i < R.rt.n` is read; a later slot is never defaulted to
"exists"); `nvn=1 attached=0` means an NVN candidate existed but the real `pd` did not attach it (which is exactly the
`cfmt=0` case an earlier plan would have mis-read); `attached=1` carries the pixelFormat/size/type/level/slice actually
in the descriptor; all cview fields are zero when there is no cview or the slot is not live.

## 7. Compile and host

- Build tree `dm/host`, chain `9f73847b56ec` (`gen/010074F013262000/profile/dmsh_chain.h`), candidate profile layout
  unchanged (645 map / 90 pairs, `DM_MSL_DIR` = candidate `out`).
- Exact compile line: `linkcheck/dmhost-psort.compileline` (the previous host's line with only `-o` changed).
- Result: **rc=0, 0 errors** (`linkcheck/dmhost-psort.build.log`).
- Host: `linkcheck/dmhost-psort`, full sha256
  `c5aec9cb7d4d2276bf40ea26a1a030f00899d8d73a0f571b56a2e99bc1aebefb` (prefix `c5aec9cb7d4d2276`). Embedded `DMSH_CHAIN "9f73847b56ec"`, and the strings `DM_NVN_PSOFAIL_RT`, `[psort] done` are
  present. No shared `dmhost`, no old experiment host was overwritten.

## 8. Verification actually performed (and not performed)

- Source path/lock/lifecycle review: capture on the replay thread inside `rp_begin_ex_`; report/cached on the replay
  thread inside `pso_get_`; no background read of `g_pass`/`R`; no new lock; no retained object.
- Default off: with the switch unset, `psort_arm` sets mode 0, and capture/report/cached return before any copy or log.
- Match rules: pure 6-line function, reviewed; success (`<key>`, `<key>_b`) and rejection (`_bf`, other key, shorter
  string) are by construction, **not** exercised by a runtime test this round. No separate test harness was added: the
  helper is inside the Objective-C file and extracting it would have meant a refactor the supervisor asked to avoid.
- **Not** claimed: that the production replay path was exercised end-to-end, that a snapshot was ever printed, or that a
  real failure was consumed. Those require the next (authorised) run.

## 9. Report table — still unknown, unchanged

| colour slot | known | still unknown |
|---|---|---|
| 0 | the failing pipeline's Metal attachment set contains a 103 (`RG32Uint`) | **which index**; NVN original format (0x17 or a view override); serial/level/layer; usage |
| 1 | the MSL declares `float4 [[color(1)]]` | whether slot 1 is attached at all; its MTL and NVN format |

No `fout` value is assigned; the original NVN format, the attached view, slot 1 and the original sample values remain
unknown. The SBUF/converter distinction from report61 stands, recorded only.

## 10. Draft trigger for the next single run (not executed)

Same recipe as `run-triple-20261021-182341` (host `dmhost-psort`, candidate chain `9f73847b56ec`, map 645, `DM_MSL_DIR`
candidate `out`, six unchanged inputs, `DM_NVN_KEYDUMP=4bae5b8abd3bec7f:1`, `DM_NVN_IMGBIND` unset, 180 s, gate 10 s
≥3072 MiB), plus `DM_NVN_PSOFAIL_RT=4bae5b8abd3bec7f`. Expected: the startup arm line; then, at the target pipeline
failure, one `[psort] fs=4bae5b8abd3bec7f_b … assoc=same-pass …` header, eight `[psort] slotN …` lines and
`[psort] done`. If the failure hits the cached-failure branch first, the `cached failure` line is the honest outcome for
that attempt. The run is not authorised here and was not executed.
