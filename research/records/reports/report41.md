# Round 41: ownership gate, the RTTI-gated release pass, and the one condition still unobserved

**HEAD `7be6d27`**, no commit, **no run**. Static only, as instructed.

## Withdrawal
"State 2 necessarily means payload == NULL, apply can never succeed, an early cancel is proven to cause the crash"
is **not** established and is withdrawn. `0x125ffcc` skips the whole free block when ownership is 0, so a released
task can legitimately keep a caller-owned payload; and my Round 39 samples were taken at a function entry, so their
`c8 = 0 / d0 = -1` cannot be attributed to that call's own effect.

## Short field table (task = object+0x30; object offsets in the second column)
| task field | object offset | meaning | evidence |
|---|---|---|---|
| `+0xc0` | `+0xf0` | async request handle | written at `0x125ff88` from `0x125d394`; cleared at `0x1260008` |
| `+0xc8` | `+0xf8` | payload pointer | callback `0x1260154`; freed `0x1260030`/`0x126004c`; read by apply as `ldr x1,[x0,#0xf8]` |
| `+0xd0` | `+0x100` | length (signed) / status | `-2` submit failure, `-1` release, else payload length; apply reads it as `ldrsw x2,[x0,#0x100]` |
| `+0xf0` | `+0x120` | **ownership byte = callback w4 & 1** | `0x1260160 and w8,w4,#1` → `0x1260170 strb w8,[x0,#0xf0]`; gates the free at `0x126000c` |
| `+0xf4` | `+0x124` | phase: 1 accepted, 3 failed, 0 after release | `0x125ff90` / `0x125ffac` / `0x1260058` |
| `+0xf8` | `+0x128` | allocator for an owned payload | `0x126001c`, released through its virtual `+0x18` |

`0x1260154` has **no direct caller** — it is installed as a callback and invoked through a pointer, which matches an
async completion. Its `w4&1` is where ownership comes from; the async subsystem decides it, not the wisty class.

## The release pass, with its guard
`0x5b6f4`:
[Fenced excerpt omitted from the shareable research record.]
Caller `0xefec` is inside a function starting at `0xee40` and the call is **RTTI-gated**, not time-based:
[Fenced excerpt omitted from the shareable research record.]
So this is a **typed per-tick sweep of a service's release queue**, not a timer and not an expiry heuristic. The
earlier "0xefec is the caller" statement is corrected: `0xefec` is an offset inside `0xee40`.

## Normal protocol as far as instructions show
1. `0x5bf90` constructor: path, async submit `0x125d394` → `c0` handle, `f4 = 1`, object `+0x254 = 1`.
2. async completion `0x1260154`: `c8 = payload`, `d0 = length`, `f0 = w4 & 1`, then a notify call `0x1275e70`.
3. apply pass `0x5bcfc`: per entry, `0x125fd1c` (`c8 != 0`) → `0x5c06c`: virtual `+0x18` applies (`ldr x1,[x0,#0xf8]`,
   `ldrsw x2,[x0,#0x100]`), then `+0x254 = 4`.
4. release sweep `0x5b6f4`: `0x5c0ec` → if `+0x254 == 1`, `0x125ffcc` cancels (`c0`) and **frees only if `f0 != 0` and
   `c8 != 0`**, then `+0x254 = 2`; the `== 4` path `0x5c0b4` runs virtual `+0x20` and sets `+0x254 = 0`.
So **both orders exist**: apply-then-release (state 4 → 0) and release-without-apply (state 1 → 2). A state-2 object
may still carry a payload when ownership was 0, and that is a normal path, not a fault by itself.

## Observed violation: none proven
What the runs established is only that the type-2 record's object is at `+0x254 = 2` at dispatch time and that the
owner's `+0x100` is null. Whether that object still had `c8`/`f0` set, and whether its entry was ever in the apply
list, is **not** in any log — the probes never read those fields for that object.

## The one missing observation (design, not a run)
Target association: `main:e69ca8@x20` (record → `flag`, `object`) and `main:e69c98@x20+0x10` (type, id) give the
record→object mapping in the same pass; the object is `[record+8]`.
Fields for that object, at a point where the object is in a register and reachable for it: the state getter entry
`main:5c060@x0+0xf0` dumps 16 bytes = **`c0` handle + `c8` payload**, and `main:5c060@x0+0x100` dumps **`d0` length +
`f4` phase**; `@x0+0x120` would give `f0` ownership. All three are `add`-based safe points (`0x5c060` is
`add x8,x0,#0x254`), and each probe host instruction must still pass the capstone precheck.
Falsification targets, both branches:
- **A**: the target object has `c8 != 0` when state is 2 → release-with-ownership-0 path, and the crash comes from the
  consumer instead;
- **B**: `c8 == 0` with `f0 != 0` → an owned payload was freed before use, and the release sweep's timing is the
  failure.
No other field is needed to choose between them.

## Not done
No run, no state forcing, no HLE/rewriter/scheduler/memory change, no tracked edit, no commit. Functions still unread
beyond the sweep: the body of `0x125da90` (cancel internals) and `0x1275e70` (the notify in the callback).
