# Report 72 — single-key build under the vs-base-0x110 hypothesis: `vp_s0.reg` 0, MSL unchanged

Offline, 20-minute bounded single-key candidate build. No host build, no guest, no translation of any other key, no
installation, no commit. HEAD `82f488b` unchanged.
Artifacts: `/path/to/external-drive/xc3/work/experiments/ssbo-base110-9b770/`.

## 0. Correction to report71 section 5

"Two independent checks, either decisive on its own" was wrong. A candidate build only tests the toolchain's
**mechanical prediction under the hypothesis**; it is not independent evidence of a real base value. Only independent
slot/base evidence would bear on whether the mapping is true. The two TODO notes and the three-namespace distinction
(translator `slot`, NVSD `handle`, NVN `reg`) stand as written there.

Also: report70's artifact digests were paired with the wrong files; an erratum was appended
(`res.json` 388 B = `bd9dd7f361b0ed2f…`, `spv` 16204 B = `3659d6839dc24242…`). Contents and conclusions unaffected.

## 1. The experiment profile: exact diff

Cloned from `fout-uint-correct645` (profile sha set recorded). Against the original `game.tsv`
(sha256 prefix `11fa16b175a59d65f94d`), the only non-comment change is:

[Fenced excerpt omitted from the shareable research record.]

plus one comment line above it stating that this is a single-key hypothesis, not a title-wide value and not a measured
NVN slot table. `ps=0` and `cs=0` are untouched; `nvn_img_base 0x120`, `nvn_img_slots 1`, `nvn_tex_slots 16`, the one
fout row and every other profile value are unchanged. The map (645 keys, 0 validation problems) and the 90 pairs are
the audited ones, with the packages copied byte-for-byte, so every map row still resolves. No Mario constant was used
as a value; 0x110 comes only from this key's `cb_offset 68` words.

## 2. Input and build

- Input `9b770cf888d729bd` = `vs_shd_post_s175p0.bin@0`, Slct175 / program0 / entry0; re-verified with the production
  validator: ctl 2176 (`2e73bb65cd577a57`), code area 1792 (`1cee8b5dd7e17232`), code-area stage `vs`, recomputed key
  matches.
- Tools: `dmsh_chain.py --check-tools` passes with the existing `DOTNET_ROOT`; chain computed by the real tool:
  **`26c9ad81719f`** (differs from `012cc15f1405` because `nvn_ssbo_bases` is one of the hashed profile keys), header
  written only in this experiment copy.
- Build: fresh `DMSH_CAS`, fresh `out`, `J=1`, explicit single key, no `IOSOUT`, no `PREFILL`, no translator/lock touch:
  rc=0 in 2.3 s. Summary: `new key 1`, `variant cache 0`, `Metal cache: mac 0 reused, 1 compiled`, driver-segment
  readers 0, undecoded slots 0, `queries without a PC answer 1`. No other key was built.
- Job and raw response were captured out of the temp workdir by a watcher: `jobs/job_7664823861541809849.json` and
  `jobs/9b770cf888d729bd.res.json`. The response is byte-identical to the report70 raw round
  (`bd9dd7f361b0ed2f…`), i.e. the translation input did not change. The job still has `tex/img/attr/fout {}`, `c1 ""`,
  `debug/reduced true`, `pc_missing true`.

## 3. Old vs new artifacts

| file | `b-012cc15f1405` (base 0) | `b-26c9ad81719f` (base 0x110) |
|---|---|---|
| `9b770cf888d729bd_b.metal` | `c28b12b019be` | `c28b12b019be` (identical) |
| `9b770cf888d729bd_b.metallib` | `27855d1b591f` | `27855d1b591f` (identical) |
| `9b770cf888d729bd_b.json` | `ccfe32085036` | `9281a08e5330` |

The JSON difference is exactly one field:

[Fenced excerpt omitted from the shareable research record.]

`vp_c3` (cbuf reg 0), `vp_c4` (cbuf reg 1), `index 0`, `rw false`, `arg_id 2` and `drv_reads {}` are unchanged, and the
shader's MSL/metallib are byte-identical — as expected, since `reg` is host-side reflection only.

## 4. Why `reg` becomes 0, and what that does and does not show

The response entry for the single sbuf is unchanged: `binding 1`, `slot 0`, `cb_slot 0`, `cb_offset 68` **words**,
`flags 0` → `off = 68 × 4 = 0x110` bytes. Under the assumed `base = 0x110`: `delta = 0`, `0 ≤ 0 < 0x100` holds,
`0 % 16 == 0` holds, so production `reflect` yields `reg = 0`. This is a **mechanical consequence of the hypothesis**,
not a measurement of the base: the build cannot distinguish a correct base from any other base that makes the same
arithmetic pass, and it says nothing about `handle`, translator `slot` or the real NVN register.

## 5. "Loader accepts" — not claimed

No production reflection parser was driven: the repository has no no-guest harness that loads `nvn_refl` (the only test
in `dm/gfx/nvn/tests` is `t_imgdiag.c`), and this round did not add one. So the correct statement is only: with the
new JSON, `vp_s0` **satisfies the missing-`reg` check** that previously rejected it; that is not an observed loader run,
not a GPU result, and not evidence that the buffer contents are right.

## 6. Unknowns and stop

- The real `nvn_ssbo_bases` for the vertex stage is still unmeasured; 0x110 remains a hypothesis.
- `handle 0` (NVSD) vs translator `slot 0` vs NVN `reg` remain three namespaces without a proven correspondence
  (source TODOs unchanged).
- Nothing was done for the other SSBO keys (27 shaders / 45 bindings) or the texture/sampler group; the 645 library was
  not rebuilt; no stage/format/`fout`/GS/TEX16 change; no push/PR.
- One key built, one hypothesis tested, stopping here.

## Addendum (supervisor review)

- The JSON difference is not one field: the top-level `chain` also changed (`012cc15f1405` → `26c9ad81719f`). The
  binding-level statement stands only for the `bindings` array (`vp_s0.reg` null → 0); the whole-file hash change
  includes `chain`.
- "27" is the total number of shaders with an unresolved `sbuf`; the target `9b770cf888d729bd` is inside that 27 (so
  the correct phrasing is "27 including the target", not "27 other"). The other 26 were not touched this round.
