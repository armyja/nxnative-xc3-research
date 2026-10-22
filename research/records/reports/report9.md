# Round 9: bounded static-consumer search — not found

**Conclusion: the consumer formula was NOT found within the 30-minute bound.** No repository change; HEAD stays `fe5bccc`.

## Corrections to my last report, as you directed
**"Storage reconstruction: correct and complete" is downgraded.** What was actually shown: for all 1,882 programs, concatenating the descriptor storage spans equals what `xc3_lib` returns as `vertex_binary ++ fragment_binary`. Since both sides accumulate the same `nvsd_shaders` sizes over the same Slct base, that is a reproduction of the reference algorithm, not independent evidence that the per-program storage base is right. The 401 entries whose start is not a code magic and the 254 `n > fx` cases are still unexplained, so the accurate statement is: **full-Slct raw storage intervals reconstruct identically to the reference implementation; the per-program-to-stage interpretation is unproven.**

**"Remainder starting with magic = another code object" and "three code objects but two entries" stay candidates.** A magic value does not by itself constitute a new object; no independent CTL or descriptor pairs with it. Reworded throughout as *magic candidate*.

## Step 1: the total fields, located from the pinned source
`Nvsd` ends with `xv4_total_size` and `unk_item_total_size` (`src/spch.rs`, with the crate's own TODO "Why do these not match the same values in the slct?"). In the real file those two are **not** at the end of the NVSD: they sit at **NVSD+0x68 (xv4) and NVSD+0x6c (unk_item)**, followed by variable-length attribute/uniform/name data. On `shd_ocean` slct1 those are 0x1a00 / 0x1100 for program 0 and 0x1c00 / 0x1100 for program 1, and they do equal that program's `last.vx+last.fx` and `last.vu+last.fu`.

Slct si=1 raw fields (verified against the parser): `prog_cnt=8`, `prog_off=108`, `unk5_cnt=0`, `unk5_off=172`, `unk_off=284`, `unk_off1=7240`, `unk_item_offset=4352`, `unk_item_total=34816`, `xv4_offset=768`, `xv4_total=57088`, `unks1[4]=0`.

So both Slct-level and program-level totals agree with the descriptor prefix sums, and neither supplies the missing per-program base.

## Step 2: what was searched, and excluded
| step | result |
|---|---|
| main image | `dm/tools/nso.py` → 37,138,432-byte image, module id `82d187fe9ef9be921b8e1b1cddf7bd28` |
| `HCPS` immediate | **0 occurrences** in main, **0** in sdk |
| `SLCT` immediate | 1 in main, at `0x14e01c0` — a **debug/name string**, next to `DEBUG_MODE`, not a compare |
| `NVSD` immediate | 3 in main (`0x14e02c0`, `0x14e03a0`, `0x14e04a0`) — all shader-source debug strings beside `U_MDL`, `gWVP`, `vPos` |
| sdk module | 0 SPCH magics |
| wishp path strings | found the loader at `main+0x10370a4` (`adrp/add` of `/monolib/shader/shd_layout.wishp`, fed to the resource system at `main+0x125f088`, handle stored at object `+0x38`); it loads handles, it does not parse SPCH |
| `LDR [X,#0x68]` / `[X,#0x6c]` | 647 / 296 sites — too generic to select |
| header-field access clusters | 531 clusters touching four or more of `+0x18..+0x34`; the three that recur at a regular stride (`main+0x3046c`, `0x31054`, `0x316d0`) are a **struct copy into a renderer object** followed by float constants (0.8 / 0.7 / −0.1), i.e. render parameters, not the parser |
| copied-field uses (`+0xa8`, `+0xb0`, `+0xb4`, `+0xb8`, `+0xbc`) | 1,650 / 1,836 / 249 / 1,536 / 143 sites — no convergence |

The parser does not compare a magic, so the magic-search route is exhausted; it must be reading the header by offset inside a function whose other arguments do not stand out. That is where the 30 minutes went.

## Step 3: the two specific addresses I could not derive
For `shd_ocean` slct1 I can state both sides of what needs explaining, but only one side has an answer:

| | program 0 | program 1 |
|---|---|---|
| descriptor prefix span | 0x1a00 (vx 0x0 + fx 0x1a00) | 0x1c00 (vx 0x0 + fx 0x1c00) |
| NVSD `+0x68` total | 0x1a00 | 0x1c00 |
| Slct `xv4_offset` | 768 | 768 |
| **predicted xv4 base under prefix accumulation** | 768 + 0 = **0x300** | 768 + 0x1a00 = **0x1d00** |
| bytes at that prediction | `78 56 34 12` (valid code magic) | `f0 07 20 ee` (SASS, **not** a code header) |
| **actual base** | unknown | **unknown — this is the missing value** |

The CTL side has the same shape and the same gap: predicted `unk` base 0x1100 then 0x1100+0x1100, and control magic passes at the first but not at the second. As you warned, control magic passing does not prove the two belong to one program, so I do not claim the CTL base either.

## What is still missing, concretely
One observation: **the value the game uses as the xv4 (and unk) base for a program that is not the first in its Slct.** Everything else I can reconstruct; that one number per program is what separates the working first program from the failing later ones.

Without it, the two candidate next steps are, in order of cost:
1. A single read-only loader observation — log the arguments of the shader-program setup call for the first two programs of one Slct while the game initialises. This is one data point, not a bootstrap project.
2. A VT/string-reference pass over the middle of `main` with a real decompiler (the repository has `dm/tools/ghidra/Decompile.java`, but no Ghidra install here and I will not download one without your word).

## Status
No repository change, no strategy change, no commit. Nothing extracted beyond the already-present five `wishp`; the disassembly image and scripts stay under `/path/to/external-drive/xc3/work` and `/path/to/external-drive/xc3/proto/diag`. Working tree untouched apart from the untracked `XC3-SETUP.md`. No push, no PR, no tool install, no translation/build/game run.
