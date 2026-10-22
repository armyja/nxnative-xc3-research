# Round 40: corrected lifecycle — 0x125ffcc is cancel/release, and my "submit refused" reading was a wrong field

**HEAD `7be6d27`**, no commit, **no run this round**. Static model only.

## Withdrawal of Round 39's conclusion
"`0x1250068` refused the submit, so `[task+0xc8]` stayed 0" was wrong on three counts:
1. `0x125fcd8 bl 0x1250068` belongs to a **different function, `0x125fc40`**, the synchronous path; it is not part of
   the async submit `0x125fee8` that `0x5bf90` calls.
2. I dumped `+0xc8` and called it the handle. The async handle is at **`+0xc0`**; `+0xc8` is the payload pointer.
3. `0x125fd1c` ("`[+0xc8] != 0`") is a **payload-present** predicate, not a submit-success predicate.

So "all tasks are refused / never reach 4" is withdrawn; the 36 applies already contradicted a global claim.

## The async submit, as the instructions show
[Fenced excerpt omitted from the shareable research record.]

## Field table (task = object+0x30), evidence level
| field | meaning | evidence |
|---|---|---|
| `+0xc0` | async request handle | written at `0x125ff88` from `0x125d394`; cleared at `0x1260008` |
| `+0xc8` | payload pointer | written by the completion callback `0x1260154`; freed at `0x1260030`/`0x126004c`; also written by the **synchronous** `0x125fc40` path |
| `+0xd0` | length / status | `-2` on submit failure (`0x125ffa8`), `-1` on release (`0x1260050`), payload length on completion |
| `+0xf0` | ownership byte | gates the payload free (`0x126000c` `ldrb`) |
| `+0xf4` | phase | 1 accepted (`0x125ff90`), 3 failed (`0x125ffac`), 0 after release (`0x1260058`) |
| `+0xf8` | allocator | `0x126001c`, freed through its virtual `+0x18` |
Unknown: whether `+0xf4` has other values on paths I did not read.

## 0x125ffcc is cancel/release, not wait
[Fenced excerpt omitted from the shareable research record.]
It cancels the pending request, releases the payload and resets the task. My Round 39 dump at `+0xc8` showing 0 with
the next word `0xffffffff` (= -1 in `d0`) is exactly this **post-release** state, not a refused submit.

## The object's lifecycle, corrected
[Fenced excerpt omitted from the shareable research record.]
So **state 2 = "request cancelled/released"**, and such an object has **no payload**: `+0xc8` is 0, apply can never
qualify, `+0x100` is never set, and the type-8 consumer dereferences null. "Read complete but not applied" is
withdrawn.

## The remaining question, narrowed to one decision
**Why the release pass (`0x5b6f4`, reached from `0xefec`) cancels this object's request before the payload is
applied.** That is a manager-level policy decision (a frame-tick expire? an explicit cancel from another owner path?),
not a property of the wisty class. `0x5b6f4` and its caller `0xefec` are the two functions left to read; everything
between the record list and the crash is now accounted for by instructions.

I did not run: the model had to be corrected first, and the remaining question is static. No fix, no state forcing, no
null bypass, no tracked change, no commit. The invalid `+0xc8`-as-handle reading is corrected above and the earlier
run log is re-interpreted accordingly (its 116 `0x125ffcc` hits are release calls; its `d0 = -1` samples are the
reset marker).
