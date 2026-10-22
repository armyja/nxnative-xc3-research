# Round 24: offline replay — 60 GiB is unique alias *virtual* pages, not physical residency

No run this round. No repository change, no commit. **HEAD stays `2682fbc`.**

## Reconstruction, two independent methods agreeing
All 61,571 operations from Round 23's log, 4 KB aligned (**0 unaligned ops**). Method A: a 4 KB page bitmap with
the host's own semantics (idempotent set/clear). Method B: a sorted interval set rebuilt per operation. They agree
on every synthetic case — duplicate map, fully contained map, partial overlap, unmap inside a mapped range, unmap
outside it, map → unmap → re-map, and a six-operation mixture with 49,152 B of duplicate coverage — and on the
real log's first 3,000 operations.

| quantity | value |
|---|---|
| map requests | 61,569 ops, 65,097,371,648 B = **60.627 GiB** |
| unmap requests | 2 ops, 4,063,232 B = **0.004 GiB** |
| **unique alias pages ever mapped** | 64,491,622,400 B = **60.063 GiB** (15,745,025 pages) |
| **peak net mapped** | 64,491,622,400 B = **60.063 GiB**, at operation 61,514 |
| **final net mapped** | 64,487,559,168 B = **60.059 GiB** (15,744,033 pages) |
| duplicate-covered bytes | 605,749,248 B = **0.565 GiB** (0.931 % of map requests) |
| unmap bytes actually cleared | 4,063,232 B; unmap over unmapped ranges: **0** |
| address depth from alias base `0x7f54000000` | 66,332,182,528 B = **61.781 GiB** (end `0x8ec6000000`) |
| **RSS / footprint** | **unknown — the log has no resident line before the stop** |

Cross-check against the host's own `[mem]` lines (482 of them): "mapped up to +61.75 GB" is the address depth and
matches 61.781 GiB; the last "alias region mapped 60.00 GB (application pool 3.21 GB)" is the bitmap net and matches
60.059 GiB within its 0.25 GiB print step. The `up to +X` figures are intervals, not byte counts, and were used only
as a consistency check.

## The 60.63 GiB headline, corrected
**Withdrawn as a physical claim.** What the run proves:
- 60.627 GiB was *requested* to be mapped;
- the unique alias range ever touched is 60.063 GiB and the net at the end is 60.059 GiB;
- the host's `MapPhysicalMemory` only `mprotect`s the alias region and its bitmap is idempotent, so this is a
  **virtual** accounting quantity;
- **physical residency is unmeasured**: no RSS/footprint sample exists, and mprotect of untouched pages does not
  commit memory. Saying "the game mapped 60 GiB of physical pages" is not supported by this log.

The corrected sentence is: *the title touches 60.06 GiB of the alias window as unique virtual ranges, with 0.93 %
duplicate coverage and 4 MB unmapped.*

## Peak versus the pool — so no second run
Peak unique alias 60.063 GiB, larger than the application pool by itself (`APP_POOL 0xCD500000` = 3.21 GB), before
adding heap or fixed `used`. Your condition for a second short run was "offline peak unique alias + known heap/used
does not exceed APP_POOL", and it is not met by a factor of ~19. **No run was started**, no size was swept.

This also re-frames the accounting question rather than answering it: the host prints the alias net against the
application pool but, per your reading, `GetInfo(UsedMemorySize)` does not include alias pages. I did not change
that; the numbers above are the evidence for deciding it.

## Caveats on precision
- The Map/Unmap lines carry no thread id, so log order is assumed to be bitmap order. With 61,569 operations in
  under 1.5 s, interleaving between the mprotect and the print would perturb an exact *instantaneous* peak; the
  final and unique totals are unaffected by ordering.
- 4 KB page granularity is exact here because every operation is 4 KB aligned; a differently aligned host would
  need the interval form.
- `[mem]` lines print in 0.25 GB steps; they corroborate, they do not define the byte values.

## Minimal next observation, for your decision
The missing quantity is **physical**, not virtual: a resident/footprint sample of the same experiment host over the
same 30 s window (the `DM_MEMSTAT` path you described, plus an RSS sampler), taken **only if** you first decide that
mapping 60 GiB of alias pages is acceptable accounting. If you prefer not to run the wide-VA experiment again, the
alternative is to decide the accounting rule statically: whether `MapPhysicalMemory` into the alias region should be
charged against the application pool (and refuse with the same error the pool path uses), which is a host policy
question, not a measurement.

## Not done
No guest run, no profile or memory-key change, no HLE, no `GetInfo`/`MapPhysicalMemory` change, no shared-`dmhost`
overwrite, no new assets or tools.

## Artifacts (SSD)
`/path/to/external-drive/xc3/work/experiments/mac-wide-va/`: `run/boot.log` (the replayed log), `analyze2.py` (page-bitmap
replay), `xcheck2.py` (two-method cross-check with the synthetic cases), `analyze.py` (first, superseded attempt).
