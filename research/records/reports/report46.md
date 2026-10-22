# Round 46: the target request completes with status 4 / error 0x2, and the error's writer is a size comparison

**HEAD `7be6d27`**, no commit. One validated run. No production change.

## The secondary interface is real and was entered
`0x125ff2c add x10,x19,#0xb8` places `task+0xb8` (the secondary this) into the submit descriptor, and the run shows 48
submissions, 48 secondary dispatches, 37 success paths and 11 failure paths — so the interface I previously failed to
see is exercised. The primary `0x126006c` staying at zero was an artifact of looking at the wrong slot.

## The target, same run
[Fenced excerpt omitted from the shareable research record.]
So for `menu/font/bf3_us.wisty`: submit accepted (request `0x8020cd3170`), completion delivered with **status 4**
(the `!= 2` branch), **error 0x2**. The failure path writes `d0 = -2`, `f4 = 3`, error → `task+0x104`, clears `c0`.
That is the origin of every `-2 / phase 3` seen on this object; it is a **completion failure**, not a submit failure.

Other requests in the same run show the same split (37 successes with status 2, 11 failures with status 4 / error 2),
so error 2 is not unique to the font — it marks a class of loads.

## The error's writer (static)
`0x125f8f4` region:
[Fenced excerpt omitted from the shareable research record.]
So error 2 is written when **`[ctx+0x320] == [request+0x1f4]`**. `x19` here is the worker/context object, not the task;
the two fields are what the worker compares before recording the failure.

Also present in the same function: `0x125fa18 mov w9,#2; str w9,[x8,#0x1e8]; str w9,[x19,#8]` — a separate 2 in the
worker state, not the completion error.

## What is still unknown, precisely
**The meaning of `[ctx+0x320]` and `[request+0x1f4]`, and which of them carries the archive-side value that fails for
this resource.** Both are compared as equal; whether that is a length check, an offset/end check, or a
decompression-type check is not yet established, and I did not name it. That comparison is the producer boundary: the
error is recorded by the worker itself, after the request was accepted and dispatched, so the earlier "host archive
provider" and "no worker" hypotheses are both dead.

Error 2 is a small internal enum (not a Horizon `Result`, which would be in the 0x…01 range seen for the memory
limits); I did not map it to a named status.

## Limits
One run; no second launch. No state forcing, archive provider/overlay, consumer change, HLE/rewriter/memory/scheduler
edit, tracked change or commit. Artifacts: `runs/20261021-103001/` (`boot.log`, `env_probe.txt`), `probe_plan.json`,
`validate_probes.py`.
