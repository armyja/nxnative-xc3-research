# Round 45: the completion dispatch is never entered — the requests are submitted and never complete

**HEAD `7be6d27`**, no commit. One validated run. No production change.

## Static: the completion dispatch, and how it is installed
`0x126006c` matches the semantics exactly (x0 = task, x1 = completion status):
[Fenced excerpt omitted from the shareable research record.]
It has **no direct `bl` caller**: the address appears once as a 4-byte literal at `0x1420ab8` (a slot/trampoline
table), i.e. it is installed as a pointer and called indirectly.

## The run
48 submit entries and 48 handle stores; the target task's own attempt:
[Fenced excerpt omitted from the shareable research record.]
**`main+0x126006c` was never entered: zero hits in the whole run**, and `main+0x12600d0` likewise. So the completion
dispatch — the only path that installs a payload and sets `f4 = 2`, or that produces `-2 / f4 = 3` with the request's
error code — ran for **no request at all** in this session, including the target's.

## What that means for the earlier observations
The `d0 = -2, f4 = 3` seen in Round 43 cannot have come from this dispatch (it never ran). Within the submit function
the only other writer of those values is the **submit-failure** path (`0x125ffa0..ac`), which fires when
`0x125d394`/`0x125ce58` produce no request. So over the lifetime of one object there have been attempts that got a
handle and attempts that did not; Round 43 and Round 44 sampled different attempts, which is exactly why their value
sets did not reconcile. This round's target attempt is a **successful submit** (`request = 0x7b60cd3170`).

The chain as far as it is now evidenced:
[Fenced excerpt omitted from the shareable research record.]
The FS volume seen earlier (`bf3.ard` 319 reads) is unrelated to this request's completion: those are the archive
index/data reads through the ordinary file path, not an async request being served.

## The producer boundary, precisely
**Nothing ever calls the completion dispatch `0x126006c`.** That is the producer-side gap: either the worker that should
consume the queued request never runs, or it runs and never invokes the installed pointer. The next observation is
therefore not the submit and not the consumer: it is the worker side — who owns the queue that `0x125d394` posts to,
and whether that worker dequeues anything. The literal slot at `0x1420ab8` is where the dispatch pointer is stored and
is the natural place to identify the installer.

## Limits
One run; no second launch. No state forcing, no archive provider/overlay, no consumer change, no HLE/rewriter/memory/
scheduler edit, no tracked change, no commit. Artifacts: `runs/20261021-102716/` (`boot.log`, `env_probe.txt`),
`probe_plan.json`, `validate_probes.py`.
