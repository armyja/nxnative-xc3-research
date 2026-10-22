# Round 42: the run's dumps are invalid — my probe spec had a double `@`; only the hit counts are usable

**HEAD `7be6d27`**, no commit. One run, and its memory dumps are **not usable**. No production change.

## The design bug, stated first
I built the `DM_PROBE` string by joining the table's `@suffix` column with an extra `@`, so the host received
`main:5afa0@@x0+0xf0`. `DM_PROBE`'s parser sees the first `@`, then `@x0+0xf0` is neither `*` nor `x`, so it falls
back to offset 0 with register x0 — every dump landed at **`[x0+0]`**. The labels prove it:
[Fenced excerpt omitted from the shareable research record.]
The capstone precheck validated the **instruction** at each PC and passed; it did not — and could not — catch my
suffix formatting outside the tool. So the target object's `c0/c8/d0/f0/f4/path` were **never read** this round.

Because only one run is allowed, I did not repeat it. The corrected spec is
`main:e69ca8@x20,main:e69c98@x20+0x10,main:5afa0@x0+0xf0,main:5afa4@x0+0x100,main:5c060@x0+0x120,main:5c064@x0+0x140,main:1260154,main:125ffcc`
(single `@`; the same PCs already passed the instruction precheck).

## What the run does still show (register/flow only)
[Fenced excerpt omitted from the shareable research record.]
The one solid new fact: **the completion callback `0x1260154` was never invoked in this run**, while the release entry
was hit 116 times. So in this session the pending requests were released, not completed — but I am **not** using a
population count as a per-object conclusion; the target object's own history is still unobserved.

## Corrected field coverage for the next attempt (design already verified)
| PC | instruction (prechecked) | register → object | suffix | fields |
|---|---|---|---|---|
| `e69ca8` | `mov x0,x20` | x20 = record | `@x20` | flag(+0), object(+8) |
| `e69c98` | `ldr x8,[x19,#0x10]` | x20 = record | `@x20+0x10` | type, id |
| `5afa0` | `ldr w8,[x8]` | x0 = object | `@x0+0xf0` | c0 handle, c8 payload |
| `5afa4` | `cmn w8,#1` | x0 = object | `@x0+0x100` | d0 length/status |
| `5c060` | `add x8,x0,#0x254` | x0 = object | `@x0+0x120` | f0 ownership, f4 phase, allocator |
| `5c064` | `ldar w0,[x8]` | x0 = object (before the load) | `@x0+0x140` | constructed path prefix |
| `1260154` | `stp` | x0 = task, x1 payload, w2 len, w4 flag | – | completion params |
| `125ffcc` | `stp` | x0 = task (= object+0x30) | – | release entry |
All eight are distinct PCs, none PC-relative, and each was checked against the patched image. Correlation key: record
address → `[record+8]` = object; task = object+0x30; callback and release both carry the task in x0.

## Per-object analysis: not possible this round
No field snapshot for the target object exists, so I cannot say whether its `c8` was 0 or non-zero, whether `f0` was
set, or which branch (payload retained vs freed) applies. The two branches remain unselected, and neither is asserted.

## Limits carried forward
The per-object history (constructor path, submit result `c0/f4`, callback, release) must all come from **one** run in
which the dumps actually land on the intended offsets; anything less cannot distinguish "pending", "failed",
"cancelled" or "already released".

## Not done
No second run, no state forcing, no early apply, no null bypass, no HLE/rewriter/scheduler/memory change, no tracked
edit, no commit. Artifacts: `runs/20261021-101549/`, `probes.tsv`, `precheck.py`.
