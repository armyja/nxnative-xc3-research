# Round 4: SPCH adapter implemented, committed, and verified on five files

## Local commit
`31d5413` on `xc3`, author armyja, not pushed. Four files:
- `dm/gfx/tools/spch.py` (new, 207 lines): the container reader.
- `dm/gfx/tools/shader_split.py` (+5 lines): one import and one `scan_blob` branch for the `HCPS` magic.
- `dm/gfx/tests/test_spch.py` (new, 162 lines): synthetic regression.
- `docs/agents/04-graphics.md` (+2 lines): the layout and the refusal rules.

Reference: the layout is the reading of **xc3_lib 0.21.0 `src/spch.rs`**. The crate is not vendored and no other format is assumed; the doc states this.

## The three corrections
**The 15/26 root cause is now reproduced, not hypothesized.** I re-derived the old addressing from the surviving evidence rather than from a lost diff. The old code used `slct.unk_item_offset` as the start of *every* program in that Slct, never adding what earlier programs had consumed. On slct1 the real vertex/fragment control offsets are 4352/6528, 8704/10880, 13056/15232, … while the old expression returned 4352/6528 for all eight programs. Recomputed, the old expression coincides with the true addressing for **10 of 26** stages — the "match=true" count was 15 because I counted a different run's output; the number that matters is that every program after the first in a multi-program Slct was wrong. **Retracted:** my earlier explanation that a single unk cursor was not reset per Slct. It could not have changed any address here, because each Slct's `unk_item_offset` equals the previous one's end (verified: 0→4352, 4352→39168, 39168→43520, 43520→52224, 52224→56576).

**Retracted:** Round 2's "26 stages paired uniquely by code length". This round's five 512-byte stages in shd_ocean contradict it, and the length path is not maintained anywhere in the adapter.

**Wording corrected:** the rule never consults a code length *to find a control record*. It does read the descriptor's code sizes to advance the xv4 cursor. The doc and the commit message say it that way.

## Verification, five files (17 MB total, exported pointwise from the archive)
| file | sha256 | programs/stages | check() | stage bits | verdict |
|---|---|---|---|---|---|
| shd_ocean | 7eb234da… | 13 / 26 (13 vs, 13 ps) | 26/26 | 26/26 | pass; byte-identical to the Rust prototype on all 26 |
| cloud/shd_cloud | 757af4ab… | 1 cs + 78 pairs / 157 | 157/157 | — | pass; the engine puts a compute program in the fragment slot |
| shd_layout | 6931c8e2… | 460 / 920 | 920/920 | 920/920 | pass |
| shd_lgt | bf512f79… | — | — | — | **unsupported**: `slct3 program0` has 3 nvsd_shaders entries and entry 1 carries a vertex stage (vertex_xv4_size=768, vertex_unk_item_size=2176) |
| shd_post | 48b9098e… | — | — | — | **unsupported**: `slct83 program0` same shape (entry 1 of 3, vertex_xv4_size=256) |

The two unsupported files are refused with file/slct/program/field named; neither is recorded as a pass and neither was widened into a heuristic. Total verified stages: **1,103**.

Two structural facts the samples forced, both now in the adapter:
- The engine places a vertex program in the fragment slot (shd_post slct63: fragment span 1792, SPH bits say vertex), and a compute program there too (shd_cloud slct3). So the stage comes from the code area, while the span still comes from the descriptor — pairing stays structural.
- A control record must begin with the control magic at the offset the descriptor's size names. If padding sits there the file is refused, not scanned past.

## Synthetic regression (`dm/gfx/tests/test_spch.py`, 9 tests, all pass)
Same-length programs still pair by structure; a gap before a record is refused rather than searched past; compute in the fragment slot; vertex in the fragment slot; half a stage; truncated file; not-a-container; window past its section; each walk starting from its own base. The expected offsets in the tests are the literal values the builder wrote, not the parser's own arithmetic.

Existing non-SPCH entry points are untouched: `bnsh_shaders`, `bahs_shaders`, `mshd_shaders`, `glslc_shaders`, `idrk_shaders`, `kt_shaders`, `unity_shaders` and `scan_blob` are all present and unchanged apart from the five added lines.

## Still unsupported (reported, not guessed around)
- Several `nvsd_shaders` entries carrying a vertex stage (a real variant): shd_lgt and shd_post.
- A control record not where the descriptor's size puts it.
- A stage with only code or only control.

## Workspace
`XC3-SETUP.md` is untracked and was deliberately not staged. Nothing else is modified. No push, no PR, no AGENTS or nx_extract change, no host build, no translation, no game run, no toolchain change this round.

Evidence under `/path/to/external-drive/xc3/proto/out/`: `others/*.wishp` (the four exported samples), `report4.md` (this file), `adapt/` (the Rust prototype's per-stage blobs and manifest).

## Remaining work
Decide whether a variant is in scope for XC3 (shd_lgt and shd_post are two of five containers), and only then how to represent several nvsd_shaders entries; then the rest of the chain — which `wishp` the game loads first, and whether `shader_split.py`'s keys and groups suit it. Not started.
