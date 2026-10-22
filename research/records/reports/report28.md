# Round 28: heap-growth log from the transaction snapshot; shader-map path audited (no guest)

**HEAD `3c1117e`** on `xc3`, author armyja, three local commits over `80c3030`, none pushed. No guest run.

## 1. The non-blocking log bug is gone
`hle_svc.c` no longer decides "did the heap grow" from `size > hr.used_before - mb_alias()`. That expression mixed the
fixed usage into the heap figure and took a second alias reading after the lock was released, so it could underflow
and misreport a shrink as a growth. `mb_result` now carries **`heap_before`**, captured inside the transaction beside
`used_before`; the log compares `size > hr.heap_before`. No getter is called after unlocking for this decision.
`mb_map`/`mb_unmap` fill the same field so the struct is always complete.

Tests (`t_membudget`) assert the pair on grow, shrink and same-size:
[Fenced excerpt omitted from the shareable research record.]
[Fenced excerpt omitted from the shareable research record.]
Independent host build to `/path/to/external-drive/xc3/work/experiments/mac-wide-va/dmhost5` succeeded; the shared
`dm/host/dmhost` was not touched.

## Lock description corrected
My previous wording ("`mb_*` is never called under another host lock") was wrong. `QueryMemory` holds `g_map_lock` and
calls `mb_heap()`, so the real edge is **`g_map_lock` → budget lock**. The budget code never takes `g_map_lock`, and
the effect adapters only call `mprotect`/`madvise`, so no reverse edge exists. That statement is now a comment at the
place the edge is created (`case 0x06`), and this report supersedes the earlier claim. No refactor was done for it.

## 2. Shader-map path: cause found from the saved log, no backend change
Production resolution (`dm/gfx/nvn/nvn_mtl.m:2549`):
[Fenced excerpt omitted from the shareable research record.]
Round 25's FATAL named
`/path/to/external-drive/xc3/work/experiments/mac-wide-va/../games/010074F013262000/shader_map.tsv` — the binary's own
directory plus `../games/<id>/`, which is the **default branch**, so `DM_NVN_SHMAP` was unset in that process.

The launcher for that run was an inline heredoc, not a saved file, so the process environment cannot be replayed; what
remains is the log path itself, and it is decisive for the branch taken. Inspecting the launcher I used: it built its
environment from `DM_ROMFS/DM_SAVE/DM_TEMP/DM_MSL_DIR/DM_SVC/DM_MEMSTAT` and **explicitly removed**
`DM_WINDOW/DM_AUDIO/DM_FS/DM_PROBE` — `DM_NVN_SHMAP` was never added. It was not "set but unexported": it was absent.
(The Round 23 launcher did pass `DM_NVN_SHMAP`, but that run died before the graphics path, so it never exercised it.)

Intended vs actual:
| | intended | actual in Round 25 |
|---|---|---|
| profile | the MAC-ONLY wide-VA copy under `work/experiments/mac-wide-va/profile/010074F013262000` | same (build time), but the runtime looked under `<host dir>/../games/…` |
| shader map | `<profile>/shader_map.tsv` | `<host dir>/../games/010074F013262000/shader_map.tsv` (does not exist) |
| MSL dir | empty run-local directory | set and empty |

Placeholder tables verified: both the baseline and the experiment copy are 191-byte ASCII files, mode readable,
containing only the `# CPU-ONLY PLACEHOLDER` comment lines. They are deliberately empty and were not altered.

**Fix (SSD only):** `work/experiments/mac-wide-va/run.sh` now sets every path absolutely — `DM_NVN_SHMAP=$PROFILE/shader_map.tsv`,
`DM_MSL_DIR=$RUN/msl` — checks executability, existence and readability **before `exec`**, creates the run-local
save/temp/msl directories, and prints the non-sensitive final values plus the map's byte count and first line.
Dry run (`run.dry.sh`, host exec replaced by an echo):
[Fenced excerpt omitted from the shareable research record.]
Because the map is a CPU-only placeholder, a graphics run would now load it and then find no shader libraries — which
is the **next** blocker, separate from "the file could not be read".

## Not done / limits
- No guest boot; no shader translation, library build, IPA, tool install, memory-key, sysres, iOS VA, HLE/rewriter or
  NVN-bases change; `AGENTS.md` and the untracked `XC3-SETUP.md` untouched; all artifacts on the SSD.
- The old process environment is not recoverable; the conclusion rests on the log path showing the default branch.
- Shader libraries and resource facts remain missing, independently of this path fix.
