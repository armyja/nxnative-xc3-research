# Round 6: base-point regression fixed; leading-entry diagnosis

HEAD: **fe5bccc** on `xc3`, author armyja, appended over 887f9a1 (no history rewrite), not pushed.

## A. The base-point regression — you were right, it is fixed

Pinned source: `xc3_lib-0.21.0/src/spch.rs`, `SlctOffset::read_slct` calls `get_bytes(slct_section, self.offset, None)` and then `Cursor::new(bytes)`, so the cursor's zero is the **Slct start**. `Slct::programs` is `parse_count32_offset32` with no `args` override, so `parse_vec` seeks to `offset + FilePtrArgs::default().offset`, i.e. the raw offset from that zero. A section-relative base was wrong.

Measured on `shd_ocean`, **si = 1** (not slct0):

| | |
|---|---|
| Slct offset inside slct_section | 312 |
| Slct start (file) | 0x1f8 |
| slct_section start (file) | 0xc0 |
| program record's raw offset field | 0x11c |
| **Slct-relative** | **0x314** |
| section-relative | 0x1dc |
| pinned reader returns | 888 bytes at 0x314, sha256 `772eba887808c438…` |
| the fixed parser returns | same 888 bytes, same sha256 |

`_read_nvsd` now takes `relative_base` and `section_end` separately: the offset is measured from the Slct, the bound is still the end of slct_section, and the docstring states both.

The two-Slct fixture did not encode a section-relative offset to flatter the old code (the NVSD offset is the position inside the Slct), but its assertion was only a stage count, so it could not have caught this. It now places the second Slct at a non-zero offset inside slct_section, asserts its window bases, and checks that the resolved NVSD equals the bytes at the Slct-relative address **and differs from** the section-relative one.

Regression: **14 synthetic tests, all pass**. Rejection rules untouched.

## B. Leading-entry diagnosis

### B1. The statistics, stated precisely
Earlier numbers were muddled; these are recomputed from one pass over the five containers, with the denominator named each time.

| file | programs | programs with >1 entry | entries=1 | =2 | =3 |
|---|---|---|---|---|---|
| shd_ocean | 13 | 13 | 0 | 13 | 0 |
| cloud | 79 | 78 | 1 | 78 | 0 |
| shd_layout | 460 | 460 | 0 | 460 | 0 |
| shd_lgt | 325 | 321 | 4 | 319 | 2 |
| shd_post | 1005 | 945 | 60 | 942 | 3 |
| **total** | **1,882** | **1,817** | 65 | 1,812 | 5 |

Leading entries: **1,822**. Of those, **1,817 are fragment-only** (vertex_xv4_size and vertex_unk_item_size both zero) and **5 carry a vertex stage**.

The "551/551" of Round 5 was wrong twice over: 551 was counted on three files while the sentence implied all five, and the property it tested was not the one that holds. The correct statement is: **of the 1,817 fragment-only leading entries, 1,812 have fragment_xv4_size equal to the last entry's vertex_xv4_size and fragment_unk_item_size equal to its vertex_unk_item_size** — denominator 1,817, not 1,822 and not the program count. The 5 that do not match are worth separate study, not silently averaged.

### B2. Four cases, checked against the pinned reader's own `nvsd_shaders`
| case | entries | leading entry | last entry | leading (fx,fu) vs last (vx,vu) |
|---|---|---|---|---|
| shd_ocean slct0 prog0 | 2 | (0, 512, 0, 2176) | (512, 256, 2176, 2176) | equal → **exact vertex alias** |
| cloud slct3 prog0 | 1 | — | (0, 5632, 0, 2176) | compute program, no leading entry |
| shd_lgt slct3 prog0 | 3 | entry[1] = (768, 256, 2176, 2176) | (1024, 1280, 4352, 2176) | **not** equal; 768+256 = 1024 and 2176+2176 = 4352 |
| shd_post slct83 prog0 | 3 | entry[1] = (256, 1280, 2176, 2176) | (1536, 2560, 4352, 2176) | **not** equal; 256+1280 = 1536 and 2176+2176 = 4352 |

So there are two shapes, not one, and the shape a program takes depends on whether any leading entry carries a vertex stage.

### B3. Does a leading entry describe existing bytes, or new resources?
Using the last entry's own base as the reference and slicing with each entry's sizes:

- **ocean slct0 prog0, entry[0]** = fragment-only (fx 512, fu 2176). Read from the Slct's xv4/unk bases it is 512 bytes of code at xv4+0x0 with magic `78 56 34 12` and 2176 bytes of control at unk+0x0 with magic `34 12 76 98` — and those are **byte-identical to the last entry's vertex code and vertex control** (compared, not merely sized). Classification: **exact vertex alias**.
- **shd_lgt slct3 prog0, entry[1]** = (768, 256, 2176, 2176). Its vertex span 768 at the Slct base is **not** the last entry's vertex code (1024 bytes), and its control span 2176 is not the last entry's vertex control (4352 bytes). The sizes sum to the last entry's, which reads like a split of the same region, but the split is not at the boundaries the walk uses. Classification: **partially overlapping / differently partitioned — not an alias, and not yet explained**.
- **shd_post slct83 prog0, entry[1]** = (256, 1280, 2176, 2176): the same situation, sums to the last entry, boundaries differ. Classification: **not an alias, not yet explained**.

A sum-to-last test applied to all leading entries scores **0 of 1,822**, so the "split" reading does not generalise either; the two lgt/post sums are coincidences of those particular programs.

### B4. What that licenses
For the 1,817 fragment-only leading entries, an **explicit alias check** is supportable in principle: resolve the leading entry's span from the Slct base and require it to be byte-identical to the last entry's vertex code and control. I have verified that on one case (ocean) and not on the other 1,816, so it is a candidate rule, not a finding.

The 5 vertex-carrying leading entries (lgt, post) are **not** covered by that rule and must stay refused; their spans differ from the last entry's in bytes and boundaries. Nothing here was resolved by searching for a magic or matching a length.

### B5. Where I stop
This is diagnosis only: no general variant enumeration, no relaxation of the `.last()` refusal. All five containers still stop at the first leading entry:

| file | rejection point |
|---|---|
| shd_ocean | `slct0 program0`, leading entry not all zero |
| cloud | `slct0 program0`, same |
| shd_layout | `slct0 program0`, same |
| shd_lgt | `slct0 program0`, same |
| shd_post | `slct0 program0`, same |

**Coverage 0 is a parser-boundary decision, not evidence that the format is wrong.** The base-point bug was a real defect and is now fixed; the coverage number separately reflects the leading-entry rule you asked me to keep.

If you want the alias question settled rather than inferred, the smallest disambiguating step is a **static consumption point**: find the function in the game's `main` that reads `nvsd_shaders` and see whether it iterates every entry or indexes the last, and whether it uses the vertex or the fragment sizes of the leading entry. A read-only loader observation (which SLCT offset the game's shader setup loads first) would answer the same question from the other side. I have not done either.

## Artifacts
Reports and samples under `/path/to/external-drive/xc3/proto/out/`: `report6.md`, the five `.wishp`, `adapt/` (Rust-side blobs). `XC3-SETUP.md` remains untracked and unstaged. No push, no PR, no AGENTS/host/nx_extract change, no tool install, no new archive extraction, no translation, build or game run.
