# Round 19: the null memset's direct cause — an AllocateMemoryPages that returned false

No repository change, no commit. **HEAD stays `2682fbc`.** Static analysis only; 20-minute budget spent, no
diagnostic run performed, no fix submitted (no proof of cause yet).

## Correction to Round 18
I wrote that the field was zeroed earlier "in the same function". **It is not.** `main+0x1240ab0` lies in function
`0x1240a38` (next function at 0x1240b00); the crash is in function `0x1241860` (next at 0x1241af4). A smaller
address proves nothing about execution order, so the "released then not re-acquired" story was unfounded and is
withdrawn.

Also withdrawn: the UNIMPL call is **not** established as the cause. It happened earlier in the log, but the
crashing path does not touch it.

## What the disassembly actually proves
Crash object: `x19 = 0x1085b7a28` from the crash register dump = **`main+0x1c3fa28`**, a bss structure in `main`
(main base 0x106978000, so the object is inside main and `[x19+0x58]` is `main+0x1c3fa80`).

Inside function `main+0x1241860`:

[Fenced excerpt omitted from the shareable research record.]

So the chain is: `nn::os::AllocateMemoryPages` returns **false**, the caller stores zero into `[x19+0x58]`, and then
memsets 0x20000 bytes at it **without using the result**. The null memset is a *consequence*; the failing allocation
is the cause to explain.

`0x12435a0` is not an HLE stub — it is real `main` code that calls `nn::os::AllocateMemoryPages` (PLT
`0x1295670`), which is implemented in **sdk at `0x344d00`** (export `_ZN2nn2os19AllocateMemoryPagesEmm`) and
delegates to `VammManager::AllocateMemoryPages` (**sdk `0x346c48`**, size 0x1a0). The host has no
`AllocateMemoryPages` implementation and needs none: this is guest code over the VAMM.

## The 0x20000 is not an exception-stack size
`0x20000` is loaded locally (`mov w1, #0x20000` / `mov w2, #0x20000`) as the allocation size **and** the memset
size. Nothing connects it to `nnosGetDefaultUserExceptionStackForApplication`; that import has **no implementation in
`dm/host` at all** and fell through to the generic `UNIMPL` stub, but I have not traced its return into this field,
and `x0` happening to point at a stack object in the log is not ABI evidence. **The two are treated as separate
until shown otherwise.** For the record, I did not get to verify that function's real ABI (argument count/width,
out-pointer vs return value, ownership) within the time box; it is listed as open, not as the cause.

## What is missing for a decision
The single decisive datum is **the address and size passed to `AllocateMemoryPages` and why VAMM rejected them**.
Statically the address is computed from the object's own counter (`x8` from `[x20]` plus an atomic bump, minus a
constant `0xFFFFFFFEFFFE0000`), so it is not statically knowable.

Runtime evidence is thin in the direction that matters: with `DM_SVC=1` the run logged exactly one mapping,
`MapPhysicalMemory 0x135e04000+0x1000` (the alias base), before the failure — so VAMM appears to have rejected the
request **before** issuing any mapping syscall the host can see. That points at VAMM's own bookkeeping (region
accounting, i.e. how much virtual address space it believes it owns), not at `MapPhysicalMemory`'s range check.

Minimal observation I would need, one run: break at `sdk+0x344d00` return and print `(x0, x1, w0)`, or at
`VammManager::AllocateMemoryPages`'s exit print its reason. Either requires a probe that does not exist yet; the
host has no guest-PC trap facility for this, so it would have to be a temporary gdb/lldb session on the host binary
with the guest image loaded, or a temporary host probe. I did not build one without your word, and I did not guess a
memory-config change: the four memory keys are still the unvalidated guesses from Round 17/18.

## Not done (deliberately)
- No second boot, no diagnostic run, no fix, no HLE implementation, no profile change.
- No stub sweep, no `MapPhysicalMemory` tweak, no forced non-zero value.
- The exception-stack HLE was not implemented: it is unproven to be related.

## Candidate next steps, for your call
1. Authorise one 30 s diagnostic run with a temporary read-only probe at `sdk+0x344d00`'s return printing
   `(addr, size, bool)`, then at `VammManager::AllocateMemoryPages`'s failure branch to get its reason. That gives
   the exact request and the region inequality in one shot.
2. If VAMM's accounting is the issue, the fix is likely a memory-partition value for **this title only** (the
   external profile), not an HLE. The numbers must come from that run.

## Artifacts
`/path/to/external-drive/xc3/work/build/patched_v3/main.patched.bin` (main build `82d187fe…`, sdk `e8cdceb1…` — the same
build the run used), `/path/to/external-drive/xc3/work/logs/boot.log`,
`/path/to/external-drive/xc3/proto/out/round19_evidence.txt`. Nothing new was built or extracted.
