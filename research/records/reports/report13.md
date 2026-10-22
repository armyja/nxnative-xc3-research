# Round 13: scan_file's pre-filter dropped HCPS — fixed, with the production entry under test

**HEAD `01bfd8e`** on `xc3`, author armyja, appended over `07362c7`, not pushed.

## The bug, confirmed before fixing
Reproduced with a temporary synthetic `.wishp` (no game bytes):
[Fenced excerpt omitted from the shareable research record.]
`scan_file` decides whether a file is scanned at all before `scan_blob` is called, and that condition named
`BNSH`, `BAHS`, `MSHD` and `SARC` but not `HCPS`. The parser and the pairing were right; the production path
never invoked them. The fix is one added term:
[Fenced excerpt omitted from the shareable research record.]
The set of files that were already skipped is unchanged; nothing is made to look like another magic.

## Production-entry regression (real files, not scan_blob)
Four tests write a temporary `.wishp` and call `scan_file((path, rel))`:
| case | assertion |
|---|---|
| plain `[vs, ps]` | 2 keys, stages `{vs, ps}`, the pair equals the keys of the bytes written, and each key carries the exact code bytes |
| `[vs, gs, ps]` | 3 keys, stages `{vs, gs, ps}`, **no pair**, each key carrying its own bytes |
| broken container (version 0xdeadbeef) | `SystemExit` — refused, not an empty success |
| ordinary non-container file | still skipped: `('rom/plain.bin', {}, set(), {})` |

`python3 dm/gfx/tests/test_spch.py` → **Ran 26 tests, OK**. The 22 existing tests are unchanged.

## Five containers through the real file entry
`scan_file` vs `scan_blob`, compared key by key (set, stage, control bytes, code bytes) and pair by pair:
[Fenced excerpt omitted from the shareable research record.]
`shd_post` gives 1,722 unique keys from 1,953 stages: `uniq_keys` dedups identical content, so the 3,704 leaf
count is not a key count. Total unique keys through the file entry **3,473**; unique pairs **1,803**.

## Two columns, no longer mixed
[Fenced excerpt omitted from the shareable research record.]
`plain_progs` counts programs whose chain is `[vs, ps]`; `unique_pairs` dedups identical `(vertex, pixel)` key
pairs, so `unique_pairs <= plain_progs` (1,803 <= 1,811). The eight that differ are inside one file. Partition:
1,811 plain + 71 other = 1,882. Both columns come from one script run; no expected number is written into it.

## GS audit correction
My previous round attributed a `KeyError` at `dmsh_build.py:235` to an SPCH geometry row. **That was wrong.**
The `{'vertex': 'pixel'}` mapping there belongs only to the `c[0].startswith('main.rodata@')` branch, i.e.
embedded shaders in `main`; the package path never touches it. What actually happens to a geometry job:
- `job_for` (`dmsh_build.py:248`): `stage = stage_of.get(key, name[:2])` — a package record's stage is the
  first two characters of its file name, so `gs_*` becomes `gs` with no error.
- `raster_facts` (264–272): only `ps` is special-cased and `stage != 'vs'` returns `{}`, so a geometry job gets
  no raster facts and that empty value is passed into the translation request (511).
- `dm/gfx/nvn/nvn_mtl.m`: every pipeline path takes `pr->sh[0]` and `pr->sh[1]`; `sh[2]` is loaded but never
  encoded, and Metal has no geometry stage.
So geometry is **unsupported and silently non-executing**, not rejected. I changed the documentation to say
this and did not add a guard at the wrong place. Making it an explicit refusal is a later decision, after this
entry fix is accepted.

## Workspace
`XC3-SETUP.md` untracked and unstaged; nothing else modified. No push, no PR, no AGENTS / host / nx_extract
change, no asset extraction, no tool install, no translation / build / game run.

## Remaining limits
- The five-container numbers come from my run; the supervisor has not re-read those files.
- `check()` is a format check; nothing here shows the shaders translate, link or run.
- Geometry chains are extracted, reported, unpaired and unexecutable; that needs a decision.
- The pre-filter now admits `HCPS` for every scan; a `.wishp` that is not a valid SPCH stops the run by design
  (that is the atomic-failure rule), which is worth remembering if a game ships one for another purpose.
