# Round 43: the target object's fields — its resource is `menu/font/bf3_us.wisty`, and the load failed with -2

**HEAD `7be6d27`**, no commit. One valid run. No production change.

## Probe validation before exec
`validate_probes.py` decodes the spec with the host's own rules and compares to the expected table, then runs five
negative self-tests. All passed:
[Fenced excerpt omitted from the shareable research record.]
The run used the **same string object** that was validated (`env_probe.txt` records it, and the launcher asserted
equality before exec). The log's dump labels confirm the intended offsets: `[x20+0]`, `[x20+0x10]`, `[x0+0xf0]`,
`[x0+0x100]`, `[x0+0x120]`, `[x0+0x140]`.

## The target object (type-2, id 1), same-run snapshots
Record `0x7d0b125b18` → object `0x7d0475a310`, task `0x7d0475a340`.

| field | value | when / how |
|---|---|---|
| constructed path | **`menu/font/bf3_us`** (+ `.wisty` in the release call's x2 argument) | `5c064` dump at 2.5743 s (prefix, 16 B of the stored string) |
| `c0` async handle | **0** | `5afa0` snapshot, TID 1001 |
| `c8` payload | **0** | same snapshot |
| `d0` length/status | **-2** (`0xfffffffe`) | `5afa4` snapshot, TID 1001 |
| `f0` ownership | **1** (owned) | `5c060` snapshots |
| `f4` phase | **1** and, in other snapshots, **3** | `5c060` dumps |
| callback `1260154` for this task | **0 hits** | address match on `0x7d0475a340` |
| release entry `125ffcc` for this task | **1 hit at 2.5670 s**, `x2 = "menu/font/bf3_us.wisty"` | address match |

The snapshots are per-call, not one atomic read: the `f4 = 1` dumps come at 2.5743 s **after** the release call at
2.5670 s, and `f4 = 3` appears in other snapshots. I do not claim a single ordering; what is unambiguous is the value
set `{c0 = 0, c8 = 0, d0 = -2, f0 = 1, f4 ∈ {1,3}}` and that no completion callback was ever delivered to this task.

## What `-2` means, from the code
In the async submit `0x125fee8`, `-2` into `d0` and `3` into `f4` are written on exactly one path:
[Fenced excerpt omitted from the shareable research record.]
So the object's own fields say the **async submit never produced a handle**: `c0 = 0`, marked failed with `-2 / 3`,
no payload ever arrived (callback never ran), and therefore `0x125fd1c` ("payload present") can never be true for it.

## The producer boundary
The requested resource is **`menu/font/bf3_us.wisty`**. The extracted RomFS has only four top-level entries:
`bf3.ard` (9,710,938,520 B), `bf3.arh`, `movie/`, `sound/` — the path does not exist as a file, and the host's
`dm/host/hle_fs.c` contains **no ARD/ARH support at all** (grep finds none). The title reads its assets from the
`bf3.ard` archive; a host that only serves the plain RomFS tree cannot satisfy such a request, which is exactly the
`c0 = 0` the submit recorded.

So the chain is:
[Fenced excerpt omitted from the shareable research record.]
**This is a host filesystem feature gap (the ARD archive provider), not a game-logic bug and not an HLE stub.**

## What remains unknown
- Which of the two submit-failure entries was taken (manager null at `0x125ff78` vs `0x125d394` returning 0); both
  write the same `-2 / 3` and both are consistent with an unreachable path.
- The exact per-task ordering of `f4 = 1` vs `3` (snapshots at different instants; not an atomic read).
- Whether any other resource request in this run succeeded through the same path — not needed for this object.

## Limits
No second run, no state forcing, no early apply, no null bypass, no HLE/rewriter/scheduler/memory change, no tracked
edit, no commit. Artifacts: `runs/20261021-101857/`, `probe_plan.json`, `validate_probes.py`.
