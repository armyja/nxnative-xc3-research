# Round 44: the archive is served, the submit succeeds — the "host lacks ARD" claim is withdrawn

**HEAD `7be6d27`**, no commit. One validated run. No production change.

## Withdrawal of Round 43's conclusion
"Host has no ARD/ARH provider, so the load failed" is **wrong**, and the new data shows why.

**The guest reads the raw archive through the host's ordinary file I/O** (`DM_FSLOG` per ReadFile):
[Fenced excerpt omitted from the shareable research record.]
So `hle_fs.c` not matching "ARH" in a grep was never evidence of a missing feature: the title brings its own
archive reader, and the host supplies the raw `bf3.arh`/`bf3.ard` bytes as asked. The absence of a per-path open for
`menu/font/bf3_us.wisty` in the log is therefore **not** a missing-file signal — the guest resolves archive members in
memory after reading the index.

## The submit is not the reject point either
Probes (`main:125fee8`, `main:125ff88`, `main:125ff9c`, `main:125d06c`), correlated by task = target object + 0x30:

| observation | value |
|---|---|
| submit entry for the target task | `x0 = 0x7a8474a340`, path string **`menu/font/bf3_us.wisty`** |
| handle store `[task+0xc0]` for that task | **`0x7ba0cd3170` — non-zero** |
| manager-null marker `0x125ff9c` | **0 hits** (the global manager was never null) |
| `0x125ce58` returns at `0x125d06c` | **86 / 86 non-zero** (never 0) |

So for this task the async submit **produced a valid request handle**, and the provider lookup never returned null.
`-2 / phase 3` seen in Round 43 therefore cannot be read as "this submit was rejected" — it belongs to a different
attempt or to a later reset of the same object, exactly the retry/reuse possibility raised in review.

## What is actually established
1. The host serves the archive correctly (319 reads of `bf3.ard`).
2. The target request is **accepted** (`c0` written non-zero at 2.x s).
3. No completion callback was observed for this task in either run so far, and the object was later seen with
   `c0 = 0, c8 = 0, d0 = -2, f0 = 1, f4 ∈ {1,3}` — a mixture that cannot be one instant, and cannot be explained by
   the submit path.
4. The release entry was called once for this task with `x2 = "menu/font/bf3_us.wisty"` (Round 43), i.e. the task was
   later released.

So the failure sits **after a successful submit**: either the request never completed and was released, or it completed
and the object was reset before the apply pass judged it. Both are consistent with the observed field mixture, and
neither is proven.

## What the next observation must be (not done here)
One run that follows the **same task** through the completion and release paths, keyed on the task address that the
submit itself gives (`x19` at `0x125ff88`): the completion callback `0x1260154` (x0 = task) and the release entry
`0x125ffcc` (x0 = task), with the object's `c0/c8/d0/f0/f4` sampled at the state getter only for that address, in
order. That distinguishes "completed then reset" from "released while pending" without inferring from value sets.

## Limits
No second run, no archive provider or overlay, no forced success, no consumer change, no HLE/rewriter/memory/scheduler
edit, no tracked change, no commit. Artifacts: `runs/20261021-102312/` (`fs.tsv`, probe log, `env_probe.txt`),
`probe_plan.json`, `validate_probes.py`.
