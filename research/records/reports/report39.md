# Round 39: the submit fails — the task handle stays 0, so apply eligibility can never become true

**HEAD `7be6d27`**, no commit. One validated run. No fix, no production change.

## Probe safety, done before the run
`precheck.py` (capstone) reads the **patched** instruction at every probe point and rejects `b/bl/adr/adrp/cbz/tbz/
tbnz/conditional-b/literal-ldr`. All four points passed before the host was started:
[Fenced excerpt omitted from the shareable research record.]
The invalid `bl` point from Round 38 is gone, and the tool itself was not changed.

## Static: eligibility and the submit's failure path
[Fenced excerpt omitted from the shareable research record.]
So `[task+0xc8]` is the submit's handle; `0x125fd1c` refuses apply when it is 0; and a refused submit marks the task
`[task+0xf4] = 3`. **State 2 does not mean the read succeeded** — it only means the wait was entered.

## The run
[Fenced excerpt omitted from the shareable research record.]
At the wait entry, with the task at `x0` (= object+0x30), the 16 bytes at `task+0xc8` were dumped for every hit. The
sampled tasks all show
[Fenced excerpt omitted from the shareable research record.]
i.e. **their submit produced handle 0** — the request was refused at `0x1250068`, the task was marked 3, and
`0x125fd1c` can therefore never return true for them. Those objects can reach state 2 but never 4.

The 36 apply hits belong to objects whose handle was non-null (the two populations coexist); I did not isolate the
type-2 object's own handle in this run, so the mapping "our wisty object is one of the refused ones" is the remaining
link.

## Chain, with the gap marked
[Fenced excerpt omitted from the shareable research record.]
**The one missing value** is which request `0x1250068` refused for the target object (its path and the result it
returned), i.e. the failing input of the load path. Everything upstream of that is now evidenced.

## What I did not do
No state forcing, no early apply, no null bypass, no HLE/rewriter/memory/scheduler change, no new probe facility, no
tracked edit, no commit. One run only; no second launch.

## Artifacts
`work/experiments/first-runtime-pair-integrated/runs/20261021-100811/` (log, probe lines),
`precheck.py` (capstone gate), and the static notes above.
