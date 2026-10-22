# Round 47: request+0x1f4 is a failure-attempt counter; error 2 means every candidate returned false

**HEAD `7be6d27`**, no commit. One validated run. No production change.

## request+0x1f4 is a counter, not a length
[Fenced excerpt omitted from the shareable research record.]
`0x125910c` is the function that owns this tail. So the field the worker compares against the candidate count is a
**number of failed attempts**, not a size or a type, and the comparison at `0x125fa44` (`count == attempts`) therefore
means: **every candidate in the list was tried and every one returned false**. That is what writes `error = 2`
(`0x125fa4c`), which the completion path then reports as `status 4` and copies to `task+0x104`.

This also answers the open question from the previous round without guessing: error 2 is the worker's "candidates
exhausted" record, produced inside the guest worker, after the request was accepted and dispatched.

## The run
[Fenced excerpt omitted from the shareable research record.]
The target task (`0x7cc47aa340` in this run) appears among the completion lines with **status word 4**, consistent with
Round 46's error 2.

Provider/callee observations (tolerant parse; several probe lines interleave across threads, so these are counts of
*lines*, not a clean per-request table):
[Fenced excerpt omitted from the shareable research record.]
`main+0x125910c` is the same function whose tail increments `+0x1f4` on failure, and `main+0x1255608` is a second
implementation. So at least two provider backends are consulted for the requests in this run, neither of which returned
true for the target's request.

I am **not** calling `0x1255608` the failing backend for the font specifically: the run's probe lines interleave, and I
did not get a clean per-request provider/result pairing. That is the one thing the next observation must fix (single
request, ordered lines, or a per-request key).

## What is established / not established
Established:
- `request+0x1f4` is a failure counter (instruction-level).
- error 2 ⇔ candidate count == failure count, i.e. all candidates failed.
- The failing request is a **completion failure recorded by the guest worker**, not a submit rejection, not a host
  archive-provider gap.
Not established:
- Which backend failed for `menu/font/bf3_us.wisty` and why — the two candidate callees were seen, but not tied to the
  target request by address in a clean sequence.
- Whether `main+0x1255608` (the second provider) is the one that would succeed for this path.

## Next observation (one run, if needed)
Key every event by the **request pointer** the submit returns (already available at `0x125ff88`): probe the candidate
loop with the request in a register, log `(request, candidate index, callee, result)` in one line per step, and stop
after the target request's loop completes. That gives the provider that failed for this path without interleaving
ambiguity, and then a single static follow-up on that one backend.

## Limits
One run; no second launch. No archive provider/overlay, no consumer change, no state forcing, no HLE/rewriter/memory/
scheduler edit, no tracked change, no commit. Artifacts: `runs/20261021-103237/`, `probe_plan.json`,
`validate_probes.py`.
