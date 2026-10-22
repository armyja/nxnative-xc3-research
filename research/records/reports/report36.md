# Round 36: the type-2 record exists and is filtered by state — A requires 4, the object is in state 2

**HEAD `7be6d27`**, no commit. One run. No production change, no fix.

Correction applied first: `0x5af8c`'s `p == NULL` path returns **0** (the `cbz` lands on the epilogue with x0 = 0), so a
NULL object fails that predicate too; only `0x5afcc` returns 1 for a NULL object. The pseudocode in Round 35 was wrong
and is not used here.

## The five-record table (owner 0x7940058890, thread 1001, one pass, in order)
`flag/object` read at `e69ca8` with `@x20`; `type/id` read at `e69c98` with `@x20+0x10`; `B` = reached `e69cb4`
(passed `0x5afcc`), `A` = reached `e69cc0` (passed `0x5af8c`).

| # | record | flag | object | type | id | pred B | pred A |
|---|---|---|---|---|---|---|---|
| 1 | 0x794b165ad0 | 11327 | 0x7944799a10 | 1 | 1 | pass | pass |
| 2 | 0x794b165ae8 | 11288 | 0x7944799d10 | 1 | 6 | pass | pass |
| 3 | 0x794b165b00 | 11279 | 0x794479a010 | 1 | 8 | pass | pass |
| 4 | 0x794b165b18 | 11322 | 0x794479a310 | **2** | 1 | **pass** | **FAIL** |
| 5 | 0x794b165b30 | 28685 | 0x794479a610 | 8 | (not read: crash before `e69c98`) | pass | pass |

Record 5's type 8 comes from the previous round's `cmp` probe; in this run its `type/id` dump was never taken because
the type-8 handler crashes inside the same iteration.

## The proven failing condition
Record 4 **is the type-2 record** — so "the list has no type-2 record" is now disproved. It is filtered by
**predicate A** and not by B:

- B (`0x5afcc`) returns `state == 2 || state == 4` → passed, so state is 2 or 4.
- A (`0x5af8c`) returns `state == 4` (after the `[rec] == -1` early exit, which cannot have happened because
  `flag = 11322 != -1`) → **failed**.
- Therefore the object's atomic state at `+0x254` is **2**, and dispatch requires **4**.

Consequence, in order:
[Fenced excerpt omitted from the shareable research record.]
This is exactly your case **A** with the precise predicate: **not** a NULL object, **not** `flag == -1`, but
`state != 4`.

## What is still missing (one value, not a whole chain)
**What moves that object's `+0x254` from 2 to 4, and why it had not happened by this iteration.** The state is an
atomic u32 written by 94 distinct `str w?,[x?,#0x254]` sites across the image, so it cannot be attributed without the
object's type. The single next observation is therefore **the identity of the object at `0x794479a310`** — its vtable
word or its type tag — which turns those 94 writers into a small set, and with it the completion condition that
should have set state 4.

A one-run way to get it exists with the current facility: at the loop point `main:e69ca8`, the suffix `@*x20+8` prints
16 bytes at the object itself (the record's `+8` is the pointer), which yields the vtable/type word for every record
in the same pass; no new probe machinery needed.

## Not attributed
`save` clone `errno=45`, `nvnTextureWriteTexelsStrided`, the exception-stack getter: none of these is used by this
chain and none is claimed.

## Run facts
One run, host `dmhost-oe`, same profile/patches/library/map, 5 s cap, stopped by the same SIGSEGV at ~2.61 s
(exit 139). Log 260,590 bytes (437 probe lines); the two global helper points (`5afe0`, `5afb0`, `5afb8`, `5b000`) are
called from many other sites and produced most of it — the owner table above uses only the local loop points. No new
dumps (both shaders in the map). Artifacts under
`work/experiments/first-runtime-pair-integrated/runs/20261021-095358/`.
