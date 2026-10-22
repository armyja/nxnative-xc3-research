# Round 3: structural association proven on one SPCH; the length heuristic is replaced, not patched

Single input, one file: `/monolib/shader/shd_ocean.wishp` (sha256 `7eb234da…f2d582`, decoded 135,168 B from ARD offset 9,702,504,432, stored 19,659).
Reproduce:
[Fenced excerpt omitted from the shareable research record.]
Validate with the repository's own function:
[Fenced excerpt omitted from the shareable research record.]
(`GAME` is only needed to satisfy that module's import; `check()` does not read the profile. No XC3 profile exists yet and none was created.)

## The two report corrections
**Program count.** The program prints `programs=` per slct: 1, 8, 1, 2, 1. Sum **13**. My prose said "1+8+1+1+1 = 12" while the table beside it said 13; the table was right, the sentence was a transcription error. Programs 13, stages 26 (13 VS + 13 PS).

**Dictionary node capacity.** It is `path_dict_len / 8 = 1,171,456 / 8 = 146,432`, exactly the declared `path_dict_node_count`. My earlier `(3,896,736 − 890,584)/8` = 375,769 was wrong: it treated everything after the dictionary start as dictionary, including the file table. The gap before the file table and the 8 trailing bytes stay unexplained, as you allowed.

## Root cause of the 15/26
Not a format issue and not a 2176 assumption: I carried **one unk cursor across the whole file**, so after slct[0] ended at 4352 my cursor continued from there into slct[1]'s first record only by luck, and every later Slct started mid-record.

Pinned 0.21.0 evidence (`src/spch.rs`, `Nvsd::read_fragment_unk_item`): it takes `start = cursor`, seeks `vertex_unk_item_size`, reads the fragment at that point, then sets `cursor = start + vertex_unk_item_size + fragment_unk_item_size`. `Spch::vertex_fragment_binaries` creates a **new** `Cursor::new(unk_section)` and `set_position(unk_offset)` for each call, i.e. **the unk cursor resets per Slct at `Slct::unk_item_offset`**. The same holds for xv4 at `Slct::xv4_offset`. That reset is what I had missed.

## Structural mapping rule, with the evidence
Per Slct (all coordinates are relative to `xv4_section` and `unk_section` respectively):

| walk | start | advance per program | sizes from |
|---|---|---|---|
| xv4 | `Slct::xv4_offset` | `vertex_xv4_size + fragment_xv4_size` | `nvsd_shaders.last()` |
| unk | `Slct::unk_item_offset` | `vertex_unk_item_size + fragment_unk_item_size` | `nvsd_shaders.last()` |

Both walks must land **exactly** on the Slct's declared ends, or the prototype refuses:

| slct | programs | xv4 walk end | declared `xv4_offset+xv4_total_size` | unk walk end | declared `unk_item_offset+unk_item_total_size` |
|---|---|---|---|---|---|
| 0 | 1 | 768 | 0+768 ✅ | 4,352 | 0+4,352 ✅ |
| 1 | 8 | 57,856 | 768+57,088 ✅ | 39,168 | 4,352+34,816 ✅ |
| 2 | 1 | 58,624 | 57,856+768 ✅ | 43,520 | 39,168+4,352 ✅ |
| 3 | 2 | 61,184 | 58,624+2,560 ✅ | 52,224 | 43,520+8,704 ✅ |
| 4 | 1 | 62,464 | 61,184+1,280 ✅ | 56,576 | 52,224+4,352 ✅ |

Each Slct's `unk_item_offset` equals the previous Slct's walk end, and the last ends exactly at `unk_section`'s 56,576. Nothing is fixed at 2176: the step is read from each record, and it merely happens to be 2176 here. The `nvsd_shaders[0]` entry has all-zero sizes and `[1]` carries the real ones; the library reads `.last()` for this, and the pinned source marks it `TODO: Always use the last item?`. I do not treat that `.last()` as proven correct in general; I only report that with it, both walks close exactly on every declared window, which is the structural evidence that it holds for this file.

## Results on all 26 stages
`check()` from `dm/gfx/tools/shader_split.py`, unchanged, against my outputs: **26/26 pass, 0 fail**. `code[0:4] = 78 56 34 12` and `ctl[0:4] = 34 12 76 98` on every stage.

Independent stage verification (not `check()`, which only tests the graphics magic for non-compute). `shader_split.py:91` reads the stage as `SPH_STAGE.get((u32(code,0x30) >> 10) & 0xf)`: **26/26 agree** — every descriptor-VS blob reports bit 1 (`vs`) and every descriptor-PS blob bit 5 (`ps`). Note the output interface names the fragment stage `ps`, never `fs`, as you required.

Bounds and lengths: every stage's code and CTL lie inside its section, every CTL carries `CTL_MAGIC`, and `ctl[0x704] == len(code)` on 26/26 — reported as a consistency property only, exactly as you framed it, and **not used** to choose any pairing. CTL windows are not assumed to be 0x880; each is `vertex_unk_item_size` and `fragment_unk_item_size` as the record declares, and both are bounds-checked.

Per-stage code/CTL offsets and sha256 are in `/path/to/external-drive/xc3/proto/out/adapt/manifest.tsv`; the individual blobs are beside it as `<label>.<stage>.code` / `.ctl`.

## Why it stays correct when two programs share a code length
The walk never reads a code length. It is cursor arithmetic from `Slct::unk_item_offset` plus per-record sizes, so two programs with equal code lengths still consume `vertex_unk_item_size + fragment_unk_item_size` each and land on different CTL windows. This sample already contains colliding lengths — five stages at 512 bytes — and they resolve to five **distinct** CTL windows (offsets 0, 39,168, 43,520, 47,872, 52,224) with five distinct CTL hashes. All 26 CTL hashes are pairwise distinct. A length-matching adapter could not separate those five; this rule separates them by construction.

## Recommendation
**Ready for a thin adapter in the repository**, not implemented this round. Shape: a `spch_shaders(d, label, out)` mirroring `bnsh_shaders`, which reads a `wishp`, walks `Slct` → `Nvsd` as above, emits `(stage, ctl, code)` with `stage` drawn from the SPH header bits (cross-checked against the descriptor side) rather than from position, and refuses when either walk misses its declared window. `check()` and everything downstream then apply unchanged.

Residual risks I would keep visible in that adapter: the `.last()` `nvsd_shaders` choice is the library's own TODO and is only validated here by the windows closing; and this is one file of five `wishp` in the base archive, so the rule is proven for this sample, not for every SPCH in the title.

## Scope held
No second `wishp`, no `wismt` enumeration, no batch extraction, no translation, no build, no game run. `shader_split.py`, `dm/gfx/tools`, host, `nx_extract` and `AGENTS` untouched. No toolchain change of any kind this round. No commit, push or PR. Prototypes, logs and outputs remain under `/path/to/external-drive/xc3/proto*`.
