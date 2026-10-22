# Report 70 — one raw translation of 9b770cf888d729bd: the range predicate against the placeholder base is the blocker

Offline only: one translator request, no MSL/Metal/metallib, no build, no guest, no value changed, no commit.
HEAD `82f488b` unchanged. Artifacts: `/path/to/external-drive/xc3/work/experiments/ssbo-9b770-raw/`.

## 0. Labelling correction

`shd_post#175:0:0:vs` = **Slct 175 / program 0 / entry 0 / vs**, not "program 175"; the package name
`vs_shd_post_s175p0.bin` reads the same way. Reports must not call 175 the program number.

## 1. Raw inputs, exactly per `job_for`

| item | value |
|---|---|
| package | `vs_shd_post_s175p0.bin@0` (fout-uint-correct645 `pkg`) |
| record | `BTCDBTCD`, control section at record `ci`, ctl bytes 2176, sha256 `2e73bb65cd577a57` |
| code area (with 0x30 header) | 1792 bytes, sha256 `1cee8b5dd7e17232` |
| stripped code (job) | `code_area[0x30:]` = 1744 bytes, sha256 `e2b191dbc8e957cb` |
| ctl `+0x700` / `+0x704` | **1792 / 1792** → c1 relative offset 1792, instruction-area total 1792 |
| c1 slice | `rec[0x38+1792 : 0x38+1792]` = **0 bytes**, sha256 `e3b0c44298fc1c14` (empty, as the +0x700 == +0x704 says) |
| stage | `vs` (map column + code-area SPH stage) |
| recomputed key | `9b770cf888d729bd` |
| job | one element, `tex/img/attr/fout {}`, `c1 ""`, `debug true`, `reduced true`, `pc_missing true`; no facts added |

Files kept: `ctl.bin`, `code.bin`, `c1.bin`, `job.json`, plus the package location recorded above.

## 2. The single translation request

`dmsh_xlate --source-sha` → `38a1c0b4e3ebd5fa` (matches the lock; this is not a translation). One request with the
one-element job list:

[Fenced excerpt omitted from the shareable research record.]

No spirv-cross, no Metal, no metallib, no translator rebuild, no lock or install change.

## 3. The response, verbatim

[Fenced excerpt omitted from the shareable research record.]

`cb_offset` is in **words**: 68 × 4 = **272 = 0x110 bytes**. `flags 0` → `rw false`.

## 4. Predicate table (profile base is still the placeholder `vs=0`)

| predicate | value | result |
|---|---|---|
| `cb_slot == 0` | 0 | **pass** |
| `off` defined | 0x110 | **pass** |
| `0 <= off - base < 0x100` | 0x110 − 0 = 0x110 | **FAIL** |
| `(off - base) % 16 == 0` | 0x110 % 16 = 0 | **pass** |
| `reg = (off-base)/16` | — | not produced (only the range predicate fails) |

So the single blocker for this key is the **range check against the placeholder base 0**, not `cb_slot` and not
alignment. With `base = 0x110`, delta = 0 and `reg` would be 0.

Candidate base, stated as a hypothesis only: `off − 16 × slot = 0x110 − 0 = 0x110`, where `slot 0` is the response's
own slot for this buffer and matches the MSL name `vp_s0`. The cbuf entries support the reading that `slot` is the NVN
slot (binding 2 → slot 3 → `vp_c3`, binding 3 → slot 4 → `vp_c4`), but that consistency is evidence, not proof for
`sbufs`, and a single key is not a title-wide base proof. `0x110` also happens to be the vertex storage base in the
code comment's Mario layout; here it is this key's measured `cb_offset`, and the Mario number was not used as evidence.

## 5. Container cross-check (read-only, existing asset)

`/path/to/external-drive/xc3/proto/out/others/shd_post.wishp`, 6,918,144 bytes, magic `HCPS`, version 1010. Parsed with the
production `dm/gfx/tools/spch.py`: **1953 entries**, and exactly **one** entry whose control and code hashes equal the
package's: `#SPCH#175:0:0:vs@xv4+0x105900/unk+0x227700`, stage `vs`, ctl 2176, code 1792, both hashes equal to the
package's (`2e73bb65cd577a57`, `1cee8b5dd7e17232`). So the package really is that container program, and the
Slct175/program0/entry0 reading is confirmed.

## 6. NVSD storage metadata: not obtained

`spch.py` parses the SPCH header, the Slct/program tables and each entry's NVSD `nvsd_shaders` sizes and control/code
spans; it has **no** `storage_buffers` / indices / handle / visibility structure, and the in-repo documentation
describes none. Obtaining those fields would need a new parser (or a pinned tool that supports them), which this round
does not install or write. Therefore no independent NVSD constraint is claimed, and no metadata storage index, handle or
NVN slot is equated with the response's `slot`/`binding`. If several NVSD storage buffers exist for this program, this
round cannot say which is stage-visible or which one is slot 0.

## 7. Runtime meaning of `reg` versus the profile base (unchanged)

`OP_BIND_SSBO` fills `S.ssbo[stage][index<16]`; for `NVN_RB_SBUFP` the encoder reads `S.ssbo[st][reg]`, so `reg` is the
NVN slot the guest bound. The c0 table itself is written at `DM_GAME_NVN_SSBO_BASE(stage)`, i.e. the profile base is the
**address of that table**, not a slot. Filling `reg = 0` for a `None` would silently bind slot 0, and setting the base
to a guessed value would move the whole table; neither was done.

## 8. Next minimal falsifiable action (not done)

Either (a) in a throwaway experiment profile set `nvn_ssbo_bases vs=0x110` (this value only, no production change) and
rebuild **this one key**; the prediction is `reg = 0`, `rw false`, `vp_s0` unchanged, and the replay loader no longer
rejects the shader — one key, one predicate, immediately falsified if `reg` differs or the range still fails; or
(b) obtain the NVSD `storage_buffers`/handle/visibility for this program with a parser that supports them, which would
give the independent slot correspondence the current tools cannot. Neither was executed here.

## Erratum (artifact hash pairing)

The two digests in section 2 were paired with the wrong files: `9b770cf888d729bd.res.json` (388 bytes) has sha256
`bd9dd7f361b0ed2f…`, and `9b770cf888d729bd.spv` (16204 bytes) has sha256 `3659d6839dc24242…`. Sizes, contents and all
conclusions are unaffected; only the labels in that sentence were swapped.
