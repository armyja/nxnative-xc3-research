# Round 25: the application pool now covers mapped alias pages; host fix committed

**HEAD `62143c5`** on `xc3`, author armyja, appended over `2682fbc`, not pushed. 8 files: 4 new, 4 edited.

## The accounting, stated exactly
[Fenced excerpt omitted from the shareable research record.]
Only **new** pages are charged; a map fully inside already-mapped pages is an idempotent success even at a full
pool; an unmap releases only pages it cleared and cannot go negative; a remap is charged again. **Error code
`0x10801`** (`ResultLimitReached`), the same one the host already used for this class of limit on `SetHeapSize`.
`inspect` of `SetHeapSize` still returns `0xD401` for a size above the heap region.

**Synchronisation / atomicity:** one `pthread_mutex` inside `membudget.c` covers the new-page count, the budget
comparison, the bitmap update and the counter update, so two threads cannot both see the same remaining pool.
The SVC only calls `mprotect` after the accounting committed; a refusal returns before any permission change,
bitmap set or counter change. An `mprotect` failure still aborts the host (`die`), so it cannot report false
success. The lock is separate from `g_map_lock` and takes no lock while holding neither — no lock-order cycle.

**Deliberately unchanged:** `sysres`-based GetInfo16/17, the iOS address-space model, `mem_used` for other titles.
The image lower bound (measured) and `mem_used` (profile approximation) remain two distinct constraints; I kept
both rather than silently redefining `mem_used` for every title.

## Tests (no profile needed)
[Fenced excerpt omitted from the shareable research record.]
`t_membudget` covers: exact map/unmap/used arithmetic; duplicate and partly-overlapping maps charging only the
new pages; unmap holes and repeated unmaps never negative; remap charged again; a map that exactly reaches the
budget succeeding and one more page refused with usage and bitmap unchanged; a fully mapped range still
succeeding at a full budget; heap + alias sharing the pool with heap growth refused and a shrink freeing room;
the heap-region bound unchanged. `t_membudget_race` releases two threads through a spin barrier and asserts exactly
one of two maps succeeds when only one fits, with `used <= budget` afterwards. Existing `t_hmap` still passes.

## The one verification run (Mac-wide-VA profile, unchanged 68 GiB / 64 GiB, app_pool untouched)
[Fenced excerpt omitted from the shareable research record.]
- The budget check fired **once**, on a 1 MiB map, with the numbers printed; the guest did not abort on it.
- The run then reached `nnMain` and **presented two frames** — further than Round 23, which I had stopped at the
  nnMain marker.
- It stopped on a **missing shader map**, i.e. the graphics path, which is out of scope here (no shader libraries
  are built for this title). That is a configuration stop, not a budget failure.
- `DM_MEMSTAT` was requested but the run died before the 1 s sampler wrote a row; **RSS/footprint unmeasured**.
  The `maxrss` I sampled came back 0 because the child's samples were not collected before the abort, so no
  residency figure is claimed.

Because the run ended in a graphics FATAL and not by my own stop conditions, I did not repeat it: the memory
question was answered (the refusal is real and the guest continues), and a graphics run needs shader libraries
this round does not build.

## Correction to my own instrumentation
The alias "mapped X GB" log line in that run was inflated (6.87 GB) because I accumulated the cleared bytes of an
unmap as positive. The budget uses `membudget`'s counter, which was correct; the display line was not. It now
reads `mb_alias()` and the refusal line prints `used+new`. Fixed after the run and rebuilt; **not re-run**, so the
verification log above carries the old (wrong) display value and I am not citing it as a measurement.

## Not proven / limits
- `sysres` (GetInfo16/17) still models only the NPDM system resource; whether the guest derives its own limits
  from it was not investigated.
- The iOS large-address-space question is untouched (iOS caps a single reservation, so the 64 GiB experiment is
  Mac-only by construction).
- RSS/footprint of the wide-VA configuration remains unmeasured.
- Whether 60 GiB of alias mapping is *appropriate* for this title is now a policy the budget will refuse past
  3.21 GiB; that is the kernel-compatible behaviour, but it means this title may not fit the current pool and the
  next blocker may be a legitimate `ResultLimitReached` the SDK handles by failing startup.
