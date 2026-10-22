# Round 26: the budget is one transaction now; range, effect and commit are serialized

**HEAD `be43e4a`** on `xc3`, author armyja, appended over `62143c5`, not pushed. 8 files. **No guest run this round.**

## P1 (1): the VM effect runs inside the transaction
The interface is now transactional rather than "commit, then mprotect":

[Fenced excerpt omitted from the shareable research record.]
Inside `membudget.c`, under **one** mutex, each call does: range validation → new-page count → budget comparison →
**`fx(ctx, off, size, …)`** → bitmap/counter commit → result snapshot. The SVC passes `alias_effect` (its two
`mprotect`/`madvise` calls) and `heap_effect` as that callback. There is no second lock and no window between the
accounting and the page permissions, so the interleaving you described (A commits a map, B unmaps the same range,
A resumes and mprotects it RW) cannot happen: B cannot enter until A's effect and commit are done.

**Lock order:** `membudget`'s mutex is a leaf. It is taken by `svc_dispatch` paths that hold no other host lock, and
`mb_*` takes no other lock while holding it. `g_map_lock` is never held across a `mb_*` call. The effect callback
calls only `mprotect`/`madvise`, which take no host lock.

**Failure semantics.** `fx` returning non-zero → `MB_E_EFFECT`, nothing committed, nothing changed, the SVC call
aborts the host for alias (a refused `mprotect` on a valid alias range is a host fault) and returns `0xD401` for the
heap (recoverable, heap unchanged). `GetInfo` reads through `mb_used()`, which takes the same lock, so a snapshot is
consistent.

## P1 (2): ranges are validated by subtraction
[Fenced excerpt omitted from the shareable research record.]
This reproduces both of your counter-examples as `MB_E_RANGE` (the old helper returned `rc=0, new=0` for
`mb_map(65536+4096, 4096)` and `mb_map(0, UINT64_MAX)`). The SVC's own `a + size` pointer comparison is gone; the
SVC now passes `UINT64_MAX` as the offset when `a < g_alias` so the helper refuses it.

Error separation: **`0xD401` (`ResultInvalidAddress`)** for an invalid range, **`0x10801`
(`ResultLimitReached`)** only for a pool refusal, **`0xD401`** also for a failed heap `mprotect` — a budget error is
never used to mean "bad address". Budget arithmetic is `need > budget - used` with a `used > budget` guard, so no
sum wraps; the fixed-usage-over-pool case is a regression test.

## P1 (3): no state is read after unlocking
`mb_result` is filled inside the lock and the SVC prints only from it (`used_before`, `new_bytes`, `limit`,
`alias_after`, `heap_after`). The contradictory "used+new == limit but refused" text came from reading globals after
`unlock`; that is gone, and the previous log line is no longer cited as a boundary measurement. The mutable getters
take the same lock.

## P2: SetHeapSize no longer reports false success
`mprotect` used to be logged and then `g_heap_cur` updated with `regs[0] = 0`. Now the heap change happens inside
`mb_set_heap`'s transaction: pool refusal → `0x10801`, size above the region → `0xD401` (existing `0xD401` OOM path),
failed `mprotect` → `0xD401` with the heap **unchanged** and a log line naming `errno`. Never a silent success.

## Tests (all three run through `make`, no profile)
[Fenced excerpt omitted from the shareable research record.]
- `t_membudget`: duplicate/overlap/hole/remap accounting, exact-budget success, one-page-over refusal with unchanged
  state, fully-mapped-at-full-pool success, heap+alias sharing with shrink freeing room, `MB_E_CAP`, and the new
  range cases (`off > cap`, end past cap, `UINT64_MAX`, size 0, unaligned off and size, fixed usage over the pool).
- `t_membudget_race`: **C11 `_Atomic` gate** (the `volatile` barrier is gone), 500 interleavings, exactly one of two
  maps may succeed and `used <= budget` afterwards.
- `t_membudget_vm` (new, **real VM**): a 1 MiB anonymous mapping, the production effect `mprotect`s it. Checks exact
  permissions after map/unmap (`vm_region_64`), an injected failing effect committing nothing and leaving
  `PROT_NONE`, a failed heap effect not moving the heap, and **2000 forced map/unmap interleavings** where the page
  protection must always agree with the committed bitmap.
- `t_hmap` still passes, but it is an **NVN hash-table** test: it does not exercise this path and is not counted as
  a Horizon map regression.

The SVC wiring is covered by the host build (the same `mb_*` calls the tests drive); no separate dispatcher-level
test exists yet, which I list as unverified rather than imply.

## Not verified
- No guest boot: the "two frames" of Round 25 are corrected here — those were NVN `QueuePresentTexture`/frame counts,
  **not** evidence of a headless draw or display. The run reached the present-API path and stopped on a missing
  shader map; why the placeholder map was not read is left for after the memory work.
- `sysres` (GetInfo 16/17) modelling and the iOS large-address-space model are untouched.
- RSS/footprint of the wide-VA configuration remains unmeasured.
