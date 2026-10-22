# Report 82 — raw-response survey of the 27 shaders with unresolved sbuf bindings (45 bindings)

Offline only: one raw `dmsh_xlate` request per key (26 invoked, the target reused), no MSL/spirv-cross/Metal, no host or
shader library build, no guest, no profile/base/facts/translator/lock change, no commit. HEAD `ddd7d0a`.
Artifacts: `/path/to/external-drive/xc3/work/experiments/ssbo-raw-survey27/` (`keyset.tsv`, `inputs.json`, per-key dirs,
`survey.tsv`, `summary.json`).

## 1. Set and inputs

- Recomputed from the current `out/b-012cc15f1405`: **27 keys, 45 sbuf bindings** (26 pixel, 19 vertex), matching the
  supervisor's count. `keyset.tsv` stores key/stage/index/arg_id.
- Each key: package resolved from the audited map, record magic checked, control/instructions split at the production
  control magic, c1 cut from the real `+0x700/+0x704` values (not assumed empty), the non-compute code area stripped by
  0x30, stage taken from the code header, and the key recomputed from control+code area — all 27 matched. The job follows
  the `job_for` contract (empty tex/img/attr/fout, existing profile facts only, `pc_missing` when absent,
  `debug/reduced` as the build defaults); `dmsh_build` was **not imported**.
- Translator `dmsh_xlate` with the existing `DOTNET_ROOT`; source sha `38a1c0b4e3ebd5fa`; `J=1`; at most one request per
  key. **26 invoked, 1 reused**: the target `9b770cf888d729bd` response is the report70 one (`bd9dd7f361b0ed2f…`), with
  identical c1 and inputs. 27/27 produced a response; 0 failures. Per key: `ctl.bin`, `code.bin`, `c1.bin`, `job.json`,
  `res.json`, `meta.json`, and for invoked keys `stderr.txt`/`stdout.txt`.

## 2. Per-binding facts (machine-recomputable in `survey.tsv`)

| stage | bindings | offsets (bytes) | cb_slot | alignment | failure reasons |
|---|---|---|---|---|---|
| vertex | 19 | 272 (0x110), 288 (0x120), 304 (0x130) | all 0 | all 16 | **range only** |
| pixel | 26 | 1296 (0x510) … 1360 (0x550), five values, 16 apart | all 0 | all 16 | **range only** |

- **All 45 bindings fail only the range predicate** under the profile's `vs=0 ps=0` base; none fails `cb_slot != 0`, none
  is misaligned, none has a missing field or index, and no sorted-list entry was missing.
- `flags` is 0 for 38 bindings and 1 for 7; the builder's `rw = flags & 2` is false for all 45.
- The response's `slot` is **not** consistent with the offset index: e.g. vertex `0x130` appears with slot 0 twice while
  `0x110` also has slot 0; pixel `0x510` appears with slot 0 and 1, `0x530` with slot 2 and 4. So `slot` cannot be used as
  the NVN reg; the `cb_offset`-derived path is the only self-consistent one.
- `index` remains only the position in the binding-sorted list (one sorted entry per binding here).

## 3. What the offsets do and do not determine

- The offsets form 16-byte-spaced sets per stage, starting at 0x110 (vertex) and 0x510 (pixel).
- The range predicate alone does **not** identify the table base: any base `b` with `0 <= off - b < 0x100` and
  `(off - b) % 16 == 0` for every offset in the stage is admissible. For vertex that is `b ∈ [0x40, 0x110]` in 16-byte
  steps (13 candidates), for pixel `b ∈ [0x460, 0x510]` (12 candidates). Choosing the minimum offset (0x110 / 0x510) is a
  **hypothesis**, not a measurement, and no profile was changed.
- `off - 16*slot` is named, if listed at all, only as a *candidate residual assuming translator.slot equals the NVN reg*;
  the inconsistency above shows that assumption does not hold, so no residual-based base is claimed.
- The static survey therefore cannot resolve the runtime's three-slot ambiguity from report80; it only shows that all 45
  unresolved sbufs share one failure class and that the current profile base 0 is why they are rejected.

## 4. Conclusions and missing evidence

- Same failure type for all 27 keys / 45 bindings: **range vs the placeholder base**, with `cb_slot == 0` and
  16-byte alignment already satisfied.
- Stage patterns are consistent (vertex 0x110 + 16k, pixel 0x510 + 16k), but the actual base is still unmeasured; the
  needed independent evidence is a real c0/table observation (or an NVSD handle↔slot correspondence), not a minimum-off
  inference, and not the Mario comment.
- Nothing was written to any profile; `base = 0x110` remains a hypothesis; the runtime three-slot result (ambiguous) is
  unchanged. No keys outside the 27 were touched, no NVSD walk and no new parser was added.

## Erratum

- The admissible vertex base range `[0x40, 0x110]` in 16-byte steps contains **14** values, not 13. The pixel count
  (12 for `[0x460, 0x510]`) is correct.
- "`slot` cannot be the NVN reg" is limited to the claim that no **general** equality (nor a common per-stage base
  mapping) can be built from it. It does not show that a particular key's `slot 0` is not NVN reg 0.
