# Round 11: prefix stage extraction implemented, committed, verified on five containers

**HEAD `a6acb22`** on `xc3`, author armyja, appended over `fe5bccc`, not pushed.

## What changed
| file | change |
|---|---|
| `dm/gfx/tools/spch.py` | per-program code/control base, per-entry prefix walk, `+0x704` check, control record must fill its span and state its own length; `_program_sizes` (one entry) replaced by `_entries` (all of them) |
| `dm/gfx/tests/test_spch.py` | rewritten for the prefix model: 12 tests |
| `docs/agents/04-graphics.md` | SPCH paragraph rewritten to the prefix rule; says five investigated containers, `wismt` unverified, pipeline pairing open |

Unchanged and still in force: version 1010 check, Slct-relative NVSD addressing with the `slct_section` bound, atomic failure (a refused file returns nothing), and every earlier guard.

## Rule implemented
[Fenced excerpt omitted from the shareable research record.]
Then both Slct walks must land on the declared window ends.

## Test command and result
[Fenced excerpt omitted from the shareable research record.]
Covers: two entries (VS, PS); three entries (VS, GS, PS) with each stage's bytes and its own marker asserted; single-entry compute; **a second program in the Slct reading its own distinct bytes at `xv4+0xe8` / `unk+0x1120`** (the regression for the base bug); two entries with identical code still receiving their own records; and refusals for a broken prefix, a control length mismatch, a half stage, an unknown version, a payload past `slct_section`, truncation and foreign input.

## Five containers, machine-generated (no hand-copied numbers)
[Fenced excerpt omitted from the shareable research record.]
3,704 stages, every one through the repository's own `check()`, zero failures. The totals were not written into any script; they come out of the run.

## Rust comparison
Rust is a structural reference only; its stage split is not claimed proven.
- **Code**: per program, the stages concatenated in entry order equal `vertex_binary ++ fragment_binary` — **1,882 / 1,882 byte-identical, 0 mismatches**.
- **Control**: per program, the concatenated control spans equal the spans its walk consumes — **1,882 / 1,882, 0 mismatches**.
- No trimming is applied anywhere, so the "trim to ctl_len" comparison does not arise: every control record fills its entry's `fu` span exactly (`+0x20` equals the span on all 3,704).

## ocean slct1 programs 0 and 1, from the adapter run
[Fenced excerpt omitted from the shareable research record.]
These four addresses are identical to the raw table in Round 10 (70400/13728, 72960/15904, 77056/18080, 79872/20256), and the code hashes match the pinned reader's `vs`/`fs` for those programs (`c5b571bc…`, `96e416ac…`, `7a844c19…`, `d26b4af0…`).

## Three-entry programs
`shd_lgt` slct3 program0:
[Fenced excerpt omitted from the shareable research record.]
Three real stages, each with its own record, `+0x704` matching each span. `shd_post` slct83 program0 is the same shape (256 / 1280 / 2560).

## Not verified, and deliberately not claimed
- `wismt` as a shader container: still an unverified entry point.
- Which `wishp` the game loads first, and any runtime behaviour.
- Pipeline pairing: `shader_split.var_pairs` only understands `#var` labels and vs/ps pairs, so these labels produce no pipeline pairs. I did not emit fake `#var` labels to work around it. VS/GS/PS pipeline representation is the next item.
- The Rust reader's `.last()` stage split is not endorsed; it is used only for structural byte comparison.

## Workspace
`XC3-SETUP.md` remains untracked and unstaged; no other file is modified. No push, no PR, no AGENTS/host/nx_extract change, no new extraction, no tool install, no translation/build/game run. Manifest of all 3,704 stages: `/path/to/external-drive/xc3/proto/out/manifest_round11.tsv`; table above: `/path/to/external-drive/xc3/proto/out/round11_table.txt`.
