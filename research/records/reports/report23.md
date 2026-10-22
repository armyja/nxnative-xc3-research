# Round 23: 68 GiB address space — the old crash is crossed, and the game then maps 60 GiB of physical pages

No repository change, no commit. **HEAD stays `2682fbc`.** One run, stopped as soon as it reached `nnMain` (1.5 s).

## Profiles: two files, two hashes, two lines of difference
| | path | sha256 |
|---|---|---|
| baseline (untouched) | `/path/to/external-drive/xc3/build/profile/010074F013262000/game.tsv` | `0329033fc99b4cef60c29fccf4da57f1452a97ffb9dd55e73edffe931795d81a` |
| experiment | `/path/to/external-drive/xc3/work/experiments/mac-wide-va/profile/010074F013262000/game.tsv` | `a27816d803431f0f567bcf192cd45258e12a27b271c5fa8bbf6bb22c84ee19ef` |

Exact diff, non-comment lines only:
[Fenced excerpt omitted from the shareable research record.]
`mem_stack 0x10000000`, `app_pool 0xCD500000` and every NVN zero placeholder are unchanged. The copy is marked
`MAC-ONLY DIAGNOSTIC … NOT iOS / NOT production` in its header.

Host header generated from that profile and verified:
[Fenced excerpt omitted from the shareable research record.]
Experiment host: `/path/to/external-drive/xc3/work/experiments/mac-wide-va/dmhost`,
sha256 `19700584d882371a2602f7f958d213d908d0fba02d483909d3336da431a1a811` (1,901,192 B), built with the same
`make -n` compile line redirected; the shared `dm/host/dmhost` and the baseline binary were not touched. Patched
modules reused unchanged (`ace9e8fe…`, `e5b336a9…`, `57e50f0e…`).

## Actual regions (from the run)
[Fenced excerpt omitted from the shareable research record.]
Alias base = AS + 0x10000000 (the 256 MiB leading gap kept), alias cap 64 GiB, stack 256 MiB, heap offset
0x1020000000 and heap cap **0xE0000000 = 3.5 GiB** — exactly the partition you predicted.

## The probes: reservation succeeded and the limit was written
[Fenced excerpt omitted from the shareable research record.]
`main+0x1240888` is the instruction that writes `main+0x1c3fa20`, and it executed with `x21 = 0xF00000000`, so the
limit is 60 GiB. `main+0x1241860` then ran and returned. **The old null-memset crash did not happen.** All four
probes on thread `T=1001`, one hit each.

Note the honest limits of this observation: `x0=0x1` at `0x1240888` is the path condition (`tbz w0,#0` fell through),
which is the caller's success bool. I did not observe `AllocateAddressRegion`'s raw return value as a separate
quantity, so I report the success path and the written limit, not an error code.

## Timeline
`>>> nnosInitialize` → regions → `>>> nninitInitializeSdkModule` → `MapPhysicalMemory alias+0x1000` →
`>>> nninitStartup` → the initialiser at 0.99 s → limit written 1.22 s → old function returns → **`>>> nnMain` at
1.5 s** → the script stopped the host (SIGTERM, graceful exit: "received SIGTERM: graceful exit … graceful exit
done"). No heap line and no `SetHeapSize OOM` were reached, so the heap question remains open.

## The new observation, and why I stopped
The run issued:
[Fenced excerpt omitted from the shareable research record.]
with ranges growing to 12 MiB, from `0x7f54000000` upward, while the application pool is 3.21 GB. That is exactly
the "starts committing large physical ranges" case you told me to stop on: the virtual reservation became a
60 GiB physical mapping, not a static bitmap. I stopped the run at that point rather than let it become a
memory-pressure test, so I cannot say whether it would have stayed within the pool or been refused later.

Caveat on "physical": the host's `MapPhysicalMemory` may be implemented as an anonymous mapping, where untouched
pages cost nothing; the log gives the bytes **issued**, not measured resident pages. No resident/RSS line appears
before the stop, so resident usage is **unmeasured**.

## Classification of this round
- Host `mmap` of 68 GiB: **succeeded** (regions printed, host alive).
- SDK address-region allocation of 0xF00000000: **succeeded** (limit written).
- Old crash: **crossed** (function returns, no SIGSEGV).
- Next observed behaviour: **mass physical mapping (60.63 GiB issued)**, no failure before the stop.
- Not observed: GetInfo alias numbers as a separate log line, heap request, `nnMain` beyond its entry, resident
  memory.

## What I did not do
No second run, no size sweep, no change to `app_pool`, no iOS entitlement or production profile, no HLE, no
startup-order change, no allocator takeover, no shared-`dmhost` overwrite. The experiment profile stays on SSD.

## Artifacts (SSD)
`/path/to/external-drive/xc3/work/experiments/mac-wide-va/{profile,dmhost,build.log,run/boot.log}` plus the patched
images and their records already listed.
