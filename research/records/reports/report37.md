# Round 37: object identity obtained; the state-2 reads are recorded values, and the producer is still open

**HEAD `7be6d27`**, no commit. One run. No fix, no production change.

## Two corrections accepted
**State values are now quoted, not inferred.** From the run's own predicate probes (`5afe0` = B's read, `5afb0` = A's
read), the last passes show
[Fenced excerpt omitted from the shareable research record.]
i.e. for the type-2 record **both predicates actually read the value 2** (two separate `ldar`s). B passes because it
accepts 2 or 4; A fails because it requires exactly 4. So the earlier "a single moment" caveat is resolved by data,
not by inference.

**The list has 7 records, not 5.** Crash dump `*x19` gives `start=0x7d4b145ad0 end=0x7d4b145b78`; (0xb78-0xad0)/0x18 =
**7**. My earlier table was the **traversed prefix of 5** before the fault; the two tail records were never reached in
that iteration, and record 5's `type/id` was not dumped in this run (its type 8 comes from the previous round's `cmp`
probe and stays marked as cross-round).

## The record table (owner 0x7d40059a90, thread 1001, this run)
| # | record | flag | type | id | object | object vtable (module offset) |
|---|---|---|---|---|---|---|
| 1 | 0x7d4b145ad0 | 11327 | 1 | 1 | 0x7d44779a10 | main+0x1a92198 |
| 2 | 0x7d4b145ae8 | 11288 | 1 | 6 | 0x7d44779d10 | main+0x1a92198 |
| 3 | 0x7d4b145b00 | 11279 | 1 | 8 | 0x7d4477a010 | main+0x1a92198 |
| 4 | 0x7d4b145b18 | 11322 | **2** | 1 | 0x7d4477a310 | **main+0x1a92218** |
| 5 | 0x7d4b145b30 | 28685 | 8 (cross-round) | – | 0x7d4477a610 | main+0x1a94e30 |
| 6,7 | 0x…b48, 0x…b60 | – | not reached | – | – | – |
(module base this run `0x107e50000`; offsets computed from it, not from earlier runs.)

The three type-1 records share one vtable, the type-2 record has a **different** vtable (`+0x1a92218`), the type-8 a
third (`+0x1a94e30`).

## Static follow-up on the type-2 class (budget spent here)
The static image has zeros in the vtable slots; they are filled by `R_AARCH64_RELATIVE` relocations. From the module's
own RELA table:
[Fenced excerpt omitted from the shareable research record.]
Disassembly of the two distinct slots:
[Fenced excerpt omitted from the shareable research record.]
**Neither touches `+0x254`.** So the state producer is not a virtual method of this class, and the class's virtual
interface does not explain state 2.

A scan for code that materialises the vtable address itself (`adrp`+`add` to 0x1a92218) found **no hit**, so the
constructor is not reachable that way (it likely loads the address from a GOT-style slot or builds it from another
base) — that is where the 30-minute static budget ended.

## What is proven, and the one remaining gap
Proven chain: the record list has a type-2 entry whose object `+0x254` reads **2** in both predicates; predicate A
requires 4; the init branch is therefore skipped; the owner's `+0x100` is never stored and stays 0; the later type-8
handler dereferences `[0 + 0x50]` and faults.

Gap: **what writes 4 into that object's `+0x254` and when it is supposed to happen.** Narrowed by this round: it is
not one of the class's virtual slots; the constructor must be found through the vtable's actual materialisation path
(GOT load), and only then can the 94 generic `str w?,[x?,#0x254]` sites be intersected with this class's methods. I
did not guess one of the 94.

## Run facts
One run, host `dmhost-oe`, same profile/patches/library/map, 5 s cap, stopped by the same SIGSEGV (exit 139); log
316,329 bytes, 546 probe lines (the four helper points again dominate); no new dumps. No second run, no forced state,
no stub, no scheduling change. Artifacts: `runs/20261021-095820/`.
