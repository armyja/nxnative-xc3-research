# Round 21: class A — the range check failed, the allocator was never entered

No repository change, no commit. **HEAD stays `2682fbc`.** One 30 s diagnostic run used (0.3 s, no crash timeout).

## Fixed identity for the run
[Fenced excerpt omitted from the shareable research record.]

## Step 1: are the probe points inside rewritten code? No
Read from the module's own records:
[Fenced excerpt omitted from the shareable research record.]
So none of these offsets is a rewritten window copy, a branch trampoline or a gate; the installed `brk` sits on the
code that is meant to execute. The failure in Round 20 was therefore **not** a mapping/copy problem.

## Step 2: the CFG has a branch that enters the memset block directly
Scanning every branch inside `main+0x1241860..0x1241af4` for targets in `[0x1241924,0x124199c)`:
[Fenced excerpt omitted from the shareable research record.]
and the tail itself:
[Fenced excerpt omitted from the shareable research record.]
`0x1241ad0` and `0x1241ae8` are the targets of the two `b.hs #…` at `0x1241898` and `0x124193c`. So there are two
paths to the memset that bypass the allocation at `0x12418fc` **and** both probe points of Round 20. That is exactly
why those probes never fired; it was never a trapping failure.

## Step 3: the run
[Fenced excerpt omitted from the shareable research record.]
Positive control first — the function entry fires:
[Fenced excerpt omitted from the shareable research record.]
Then the first range check:
[Fenced excerpt omitted from the shareable research record.]
`main+0x1241894` is `cmp x8, x11`; the following `b.hs` compares **x8 = 0x100020000** against **x11 = 0**, unsigned
higher-or-same → **taken**, to `0x1241ad0`:
[Fenced excerpt omitted from the shareable research record.]
and the second check fails the same way:
[Fenced excerpt omitted from the shareable research record.]
One thread (`T=1001`), one call each, no interleaving.

## The direct cause, with the numbers
`x11` comes from `ldr x11, [x20, #0x18]` at `0x12418c8`/`0x124192c`, i.e. the object's **limit/end field**, and it
is **0**. With `x8 = 0x100020000` (first check) and `0x180000` (second check) both `>= 0`, both `b.hs` branches are
taken, the allocation is skipped, `[x19+0x58]` stays/becomes 0, and `memset(0, 0, 0x20000)` faults.

Object placement: `x20 = 0x109a07a08 = main+0x1c3fa08`, `x19 = main+0x1c3fa28 = x20+0x20`, so the limit field is
**`main+0x1c3fa20`**, a static object in main's bss, and it reads 0.

**There is no evidence that `nn::os::AllocateMemoryPages` was called or that it returned false.** Both range checks
happen *before* it and both failed. Round 19's "the allocation returned false" is **withdrawn** — as you anticipated.
Nothing about VAMM can be claimed, and no `MapPhysicalMemory` was issued in this run before the fault.

## Classification
**A** — positive control hit, the allocation point did not, because the CFG bypassed it; the branch condition and
the object state are given above. Not B (no copies; the records show no window covering these offsets), not C
(the installed `brk` fired on the control site, so traps are delivered and not overwritten), not D.

## What this points to
The object at `main+0x1c3fa08` was never given a limit (`main+0x1c3fa20` = 0). Its initialisation is what must be
explained next — not the allocator. `main+0x1c3fa20` has **no direct `adrp`+`add` reference** in the image (scanned),
so it is reached indirectly (a pointer loaded from elsewhere), which is why a plain xref search does not find the
writer. That is the one remaining value: *who is supposed to write `main+0x1c3fa20`, and why did it stay 0.*

## Not done
No HLE implemented, no memory key changed, no guest logic forced, no second run, no lldb. Shared `dm/host/dmhost`
untouched; tracked host/rewriter untouched.

## Artifacts (SSD)
`/path/to/external-drive/xc3/work/logs/probe.log` (Round 20), `probe2.log` (this run), `build/patched_v3/*.sites.tsv`,
`*.gates.tsv`, `*.fixups.tsv`, the launcher and hashes under `/path/to/external-drive/xc3/proto/out/`.
