# Round 5: review fixes on 31d5413, and what they cost

Complete HEAD: **887f9a1**, on `xc3`, author armyja, appended on top of 31d5413 (not rewritten), not pushed.

## What changed
1. **Version is now verified.** `SUPPORTED_VERSION = 1010`, read from all five containers. Any other value is refused before the layout is used, with the version named in the error.
2. **Every non-zero leading entry is refused.** The old check looked only at `vertex_xv4_size` / `vertex_unk_item_size`, so a leading entry with fragment sizes vanished. I surveyed all five containers: **1,845 leading entries** carry non-zero fragment sizes, and in **551 of 551** multi-entry programs the leading entry's fragment sizes equal the last entry's vertex sizes. That regularity is suggestive but it is not proof, and xc3_lib itself says `TODO: Why is only the last set of shaders used?`. Per your rule I did not convert it into an exception: any non-zero field in a leading entry is now unsupported.
3. **Program table and NVSD payload are bounded to `slct_section`.** Confirmed against the pinned reading: a Slct is parsed as a slice of `slct_section` and `ShaderProgram.program_data` is read with `parse_offset32_count32` against that base, so both must lie inside `slct_section`, not merely inside the file. `_read_nvsd` now takes the section's base and end, and its docstring no longer contradicts the base it receives.
4. **Two tests replaced.** The two-Slct test built one Slct with two programs; it now builds two Slcts with distinct, non-zero, gapped xv4 and unk bases and asserts the second Slct's code bytes, control markers (0/100 vs 1000/1100) and addresses. The same-length test used identical control bytes; each program now carries its own marker at control +0x100 and every stage's record is asserted individually, so a parser reusing the first record fails.
5. **`scan_blob` failures are uniform.** Both `Unsupported` and `ValueError` become the script's `[RED] <label> (SPCH): …` form; `ValueError` no longer escapes as a traceback. Verified that a failing file leaves `out` empty, so no partial package can be mistaken for success.
6. **Wording.** The doc and module header now say the pairing never uses a code length *to choose a control record* and that the descriptor's code sizes do advance the xv4 cursor; the doc calls these the five *investigated* containers and states `wismt` is an unverified entry point.

## Regression (13 synthetic tests, all pass)
| case | result |
|---|---|
| unknown version (0xdeadbeef) | refused, version named |
| leading entry, fragment sizes only | refused, "not all zero" |
| leading entry with a vertex stage | refused, "not all zero" |
| payload past `slct_section` (inside the file) | refused |
| real two-Slct container with gapped bases | each walk starts at its own base, markers 0/100 then 1000/1100, second Slct's code bytes asserted |
| same-length programs, distinct markers | six stages get records 0/100, 1/101, 2/102 in order |
| gap where a record should start | refused, not searched past |
| compute in the fragment slot | reported as compute |
| vertex program in the fragment slot | reported as vertex |
| half a stage | refused |
| truncated file / not a container / window past its section | refused |

## Five files, current state
| file | verdict |
|---|---|
| shd_ocean | UNSUPPORTED, `slct0 program0` leading entry not all zero |
| cloud/shd_cloud | UNSUPPORTED, same |
| shd_layout | UNSUPPORTED, same |
| shd_lgt | UNSUPPORTED, same |
| shd_post | UNSUPPORTED, same |

**Coverage change: 1,103 stages → 0.** The leading entry is not an edge case; every program of every container has one, so my Round 4 statement that three files passed described a parser that was silently discarding one entry per program. That result is withdrawn.

## Byte comparison status — corrected
Round 4 said "26/26 byte-identical to the Rust prototype" for shd_ocean. That comparison is still true of the *pairing walk* as it then stood, but it was performed against a parser that had dropped the leading entry, so it validated the walk on inputs the current parser refuses. For the other four files **no byte comparison against the Rust reference was ever run** — only `check()` counts were reported, and I over-claimed by summarising it as agreement. With all five refused there is now nothing to compare; the comparison should be re-run once a leading-entry rule is agreed.

## Still unverified
- The meaning of the leading `nvsd_shaders` entry (a prefix description, a shared declaration, or a real second stage). Needs the variant decision, not this parser.
- Whether `wismt` carries shaders, beyond the archive listing.
- Which container the game loads first, and how `shader_split.py` keys and groups fit XC3.

## Workspace
`XC3-SETUP.md` remains untracked and unstaged. No push, no PR, no AGENTS/host/nx_extract change, no tool install or upgrade, no translation, build or game run.
