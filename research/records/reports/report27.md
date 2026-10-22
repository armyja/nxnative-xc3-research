# Round 27: the heap transaction is closed; no shadow heap size left

**HEAD `80c3030`** on `xc3`, author armyja, appended over `be43e4a`, not pushed. **No guest run.**

## The P1, fixed at its source
The heap effect no longer reads a caller-visible copy. `mb_set_heap` calls
`fx(ctx, old_size, new_size, 2)` **inside the budget lock**, with `old_size` = the heap the previous transaction
committed (`g_heap` in `membudget.c`, the only authority). Your interleaving — A grows to 4 host pages and commits,
B shrinks to 2 and its effect still sees old = 0, releasing nothing while the accounting says 2 pages — cannot
happen: B cannot enter the transaction before A's commit, and when it does, its `old_size` is A's 4 pages, so it
releases 2..4.

**Where the old size comes from:** the transaction's own `g_heap`, read under the same lock that is held across the
effect and the commit. Not `g_heap_cur`, not a snapshot taken outside, not a call to a getter (which would
self-deadlock).

## The shadow state is gone
`g_heap_cur` is **deleted**, not made atomic. `mb_heap()` is the single heap size, and every reader now takes it or
the transaction snapshot:
| reader | before | now |
|---|---|---|
| `dm_guest_heap_readable` | unsynchronised `g_heap_cur` | `mb_heap()` |
| `QueryMemory` heap range and the low edge of the free range | unsynchronised `g_heap_cur` | one `mb_heap()` snapshot per query |
| heap log lines | rebuilt from `g_heap_cur` after unlock | the `mb_result` captured under the lock |
| 8 KB/region checks | — | unchanged |

**Lock order:** `membudget`'s mutex stays a leaf. It is acquired by `svc_dispatch` paths holding no other host lock;
`mb_*` acquires nothing else; the effect calls only `mprotect`/`madvise`; `mb_heap()` is never called while the lock
is held (the heap effect gets the value as an argument). `g_map_lock` is never held across a `mb_*` call, so no
order cycle exists.

## Production VM adapters, shared with the tests
The alias and heap adapters moved to **`dm/host/membudget_vm.c`** and take their region pointers from a context
struct. `hle_svc.c` passes `{g_alias, g_heap}`; the tests pass a small mmap. There is no second implementation for
the tests to drift from — this was the gap you identified, since `map == 2` previously returned 0 in the test.

## Deterministic interleaving, through the production path
`t_membudget_vm` builds a real 1 MiB alias region and a real 1 MiB heap region and checks the **actual** page
permissions (`vm_region_64`) against the counters. The interleaving test does not rely on timing:

1. the grower runs `mb_set_heap(16 pages, wrapper, …)`; the wrapper sits inside the transaction (lock held) and
   signals `inside`;
2. the test starts the shrinker, then asserts it has **not** completed while the lock is held;
3. it releases the grower; both finish;
4. it requires `mb_heap() == 8 pages`, `used == 8 pages`, pages 8..15 `PROT_NONE` and page 0..7 `RW`.
200 iterations. The wrapper delegates to `mb_vm_heap` — the production adapter — so the repair itself is not
duplicated in the test.

Results:
[Fenced excerpt omitted from the shareable research record.]
Also covered there: a failing effect commits nothing and leaves the pages `PROT_NONE` (map and heap), a failing grow
after a shrink leaves heap, `used` and permissions unchanged, and exact grow/shrink permission boundaries.

## API narrowing
`mb_set_fixed` is **removed**: it had no production caller and could set `fixed` near `UINT64_MAX` after pages were
already charged, breaking the `fixed + heap + alias` invariant the budget comparison depends on. No other change to
the fixed-usage convention.

## Not verified
- No guest boot this round, so the SVC wiring is covered only by the host build plus the shared-adapter tests; there
  is still no dispatcher-level test that constructs a `svc_dispatch` call end to end.
- `sysres` (GetInfo 16/17) and the iOS large-address-space model are untouched; wide-VA RSS/footprint still
  unmeasured.
- `t_hmap` remains an NVN hash-table test and does not cover this path.
