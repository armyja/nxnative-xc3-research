# Round 38: the wisty state machine is identified; my wait-path probe was invalid, so that step stays unobserved

**HEAD `7be6d27`**, no commit. One run. No fix, no production change.

## The state machine, from the class's own code
The constructor chain you pointed at leads to a four-value lifecycle, all on `object+0x254`:
[Fenced excerpt omitted from the shareable research record.]
The 94 `str w?,[x?,#0x254]` sites were indeed the wrong list — the class uses `add #0x254` + `stlr`, which is why
your `add`-based finding was the right entry point. `0x5c06c`'s virtual `+0x18` is `main+0x596ac`, the payload setter
shape you described (`str x1,[x0,#0x258]; str w2,[x0,#0x260]; ret`).

So state 2 means **the read was submitted and waited on, but the payload has not been applied**; state 4 means
**applied**. The type-2 record is filtered exactly because it sits between those two steps.

## What the run showed
Constructor entry with the real resource paths (probe_str on `x1`):
[Fenced excerpt omitted from the shareable research record.]
and **36 promotions through `0x5c06c`** during the run, i.e. the apply step does run for many objects. The run again
ended at the same SIGSEGV.

## My error, stated plainly
I put the wait-path probe at **`0x5c10c`, which is a `bl` — PC-relative**, exactly what `DM_PROBE` forbids. The host
installed it (`original instruction 94480fb0`) and it never fired, but **that zero is meaningless**: a trampolined
`bl` would branch from the slot. So this run says **nothing** about whether the wait pass reached the wisty object;
`0x5c114` remains the only static writer of state 2, and its execution for this object is unobserved. The safe point
would have been `0x5c108` (`add x0,x0,#0x30`) or the function entry `0x5c0ec`.

## Chain as far as it is proven
[Fenced excerpt omitted from the shareable research record.]
The link that is **not** proven is the one between "state 2" and "the payload was never applied": that needs the wait
call's presence/return for this object, which my invalid probe did not capture.

## Fix boundary (not implemented)
Either the type-8 handler must not consume a `+0x100` that a still-unapplied type-2 record owns, or the apply step must
have run before dispatch. Both are ordering/ownership questions at the owner level, not a change to the wisty class or
to the state values.

## Run facts
One run, `dmhost-oe`, same profile/patches/library/map, 5 s cap, same SIGSEGV (exit 139); 84 probe lines;
`5c10c` hits = 0 (invalid point, not used as evidence); `5c06c` hits = 36. No second run, no state forcing, no stub.
Artifacts: `runs/20261021-100452/`.
