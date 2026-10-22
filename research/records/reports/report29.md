# Round 29: one bounded run — the map at the intended path is read, first shader identities captured

**HEAD `3c1117e`**, no commit this round (no tracked change was needed). `git status` shows only the untracked
`XC3-SETUP.md`. The 68 GiB/64 GiB Mac-only profile, its APP_POOL, the placeholder map and the empty MSL directory were
not modified.

Commit-count correction accepted: after `80c3030` there are **two** commits, `e513d37` and `3c1117e`.

## Supervisor (SSD only), and an honest note about attempts
`work/experiments/mac-wide-va/supervise.sh` replaces the old `run.sh` as an independent supervisor: hard wall clock
(`SECS=5`), explicit `unset` of inherited `DM_WINDOW DM_PROBE DM_NVN_PASSDUMP_ALL DM_NVN_* DM_FS DM_SVC DM_KEYS` and
friends, `DM_AUDIO=0`, absolute `DM_NVN_SHMAP`/`DM_MSL_DIR`/`DM_NVN_SHDUMP`/`DM_MEMSTAT`, exec-time readability
checks, a fresh timestamped run directory (no `rm -rf` of earlier runs), RSS and free-memory sampling of **its own
child** (`ps -o rss=`), a 32 MiB dump cap, and TERM → 10×0.2 s → KILL.

**The first invocation aborted at 0 s and produced no data**: my free-memory metric summed `vm_stat` pages as if a
page were 4 KiB, but this machine uses **16 KiB** pages, so it computed 449 MiB instead of ~1.8 GiB and tripped the
1 GiB threshold before the host ran. That was a defect in my supervisor, not a machine condition; I fixed it
(`sysctl -n hw.pagesize`) and then performed the single actual run below. Both directories are kept.

## The run (`runs/20261021-092703`)
[Fenced excerpt omitted from the shareable research record.]
`exit=0` is the host's graceful exit after the supervisor's SIGTERM; the host did not crash.

**Map read confirmed at the intended path** — the log names the absolute file:
[Fenced excerpt omitted from the shareable research record.]
0 entries is the expected result for the CPU-only placeholder. The Round 25 FATAL is gone because the launcher now
passes the path; the previously observed default path (`<host dir>/../games/…`) is no longer used.

Other expected gaps, all present and not worked around: shader library directory `msl/b-34e8ff282fcd` missing,
`c1_full.tsv` stale, `pso_manifest.tsv` missing, plus one NVN `[RED]` for `nvnDeviceRegisterFastClearDepth`.

## First shader identities (byte-verified, not by length)
`DM_NVN_SHDUMP` only writes shaders **missing from the map**, which with an empty map is all of them; it writes
`<key>.ctl` (the 0x880-byte control section) and `<key>.code` (length from control +0x704), at the first use of a
program.

| key | stage | ctl bytes | own len @0x20 | code bytes | ctl magic | code magic | `ctl[0x704]==len(code)` | re-derived key |
|---|---|---|---|---|---|---|---|---|
| `58e2e00d24c6f3ea` | **vs** | 2176 (0x880) | 0x9e1 (→ 0x880 used) | 512 | `34127698` | `78563412` | yes | matches |
| `5d36d4144f49ec9a` | **ps** | 2176 (0x880) | **0x87f** | 256 | `34127698` | `78563412` | yes | matches |

The key derivation matters: `prog_key` hashes `control[0:nctl] + code[0:ncode]` where `nctl` is the control's own
length at `+0x20` when it is in `[0x760, 0x880)`, else `0x880`. The second key only matches with that rule (0x87f);
hashing 0x880 for both would have reported a false mismatch. `shader_split.check`'s contract holds for both
(control magic, code magic, declared length equal to the file length), and the stages come from the repo's own
`spch._stage_of`, not from a guess (`thread group +0x748 = (0,0,0)`, so neither is compute).

First missing-shader log lines, in order:
[Fenced excerpt omitted from the shareable research record.]

## Against the five sample containers
Compared **by key and by real bytes**, not by length: computing the same `nctl`-aware key over every stage of the five
`.wishp` files, neither `58e2e00d24c6f3ea` nor `5d36d4144f49ec9a` occurs.
**Statement: not in the five-sample set.** I do not infer anything about GLSLC-in-main or `wismt` from that, and I
did not scan the 396 candidates or export new archives.

## Memory
- **RSS (external sampling of the child): peak 179,264 KiB ≈ 175 MiB**, 3 samples over 1 s.
- `DM_MEMSTAT` wrote a single row at t=0: `phys_footprint 23` (MiB). At t=0 the rest of the columns are not yet
  meaningful, so only that one figure is reported.
- Alias virtual volume is a **different quantity** and was not re-measured this round; no RSS↔alias comparison is
  made. Nothing here measures a display frame: the run reached the shader-lookup path, not presentation.

## Next minimal step
The two identities are the first concrete build targets for an offline shader library, but they are **not in the
extracted set**, so the next round's minimal object should be decided from where these two came from (they were used
by the game's own first program) rather than from the five containers. The missing library directory, stale
`c1_full.tsv` and missing `pso_manifest.tsv` are separate, known gaps.

## Not done
No shader translation or library build, no IPA, no tool install, no memory-key/sysres/iOS VA/GS/driver-bases/
rewriter/HLE change, no production-profile change, no tracked commit, no push/PR. `AGENTS.md` and `XC3-SETUP.md`
untouched; all new artifacts under `/path/to/external-drive/xc3/work/experiments/mac-wide-va/runs/`.
