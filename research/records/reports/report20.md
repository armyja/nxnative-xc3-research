# Round 20: DM_PROBE used; probes installed, zero hits, crash unchanged — the one observation did not land

No repository change, no commit. **HEAD stays `2682fbc`.** One guest run used (the single one authorised).

## Correction accepted: the probe facility exists
`host/probe.c` + `docs/agents/05-debugging.md` (from 05-debugging.md line ~45). **My Round 19 statement that the
host has no guest-PC trap facility was wrong.** `DM_PROBE=module:offset,…` writes `brk #0xf000` at the guest
address, routes SIGTRAP through `crash_set_trap_hook(probe_hit)` (`crash.c:130`, `crash.c:207`), prints registers
and a backtrace, then executes the original instruction from a trampoline. Only lldb remains the fallback.

## Points chosen, and why they are safe
Chosen for `DM_PROBE`'s two constraints (no PC-relative instruction; x16 dead):

| point | instruction | reason |
|---|---|---|
| `main:12418f8` | `mov w1, #0x20000` | the `size` argument is set here; `x0` already holds the address. Both `mov`, not PC-relative |
| `sdk:344d00` | `stp x29, x30, [sp, #-0x10]!` | `nn::os::AllocateMemoryPages` entry |
| `sdk:346c48` | `sub sp, sp, #0x40` | `VammManager::AllocateMemoryPages` entry |
| `main:1241918` | `mov x8, xzr` | reached **only** when the allocation returned false, i.e. a failure-path marker |

I did **not** probe `main+0x1241900`: it is `tbz w0, #0` (PC-relative), which `DM_PROBE` forbids.

## ABI verified before running
The exported symbol `_ZN2nn2os19AllocateMemoryPagesEmm` at `sdk+0x344d00` starts:
[Fenced excerpt omitted from the shareable research record.]
So the **export** takes `(x0 = addr, x1 = size)` and the **method** takes `(x0 = this, x1 = addr, x2 = size)`. The
method's addr/size are **not** in x0/x1 — exactly the trap you warned about. That is why both entries were probed:
the wrapper shows addr/size in x0/x1, the method shows them in x1/x2 with `this` in x0.

## The run
Same isolated environment as Round 18 (empty save/temp/msl, headless, `DM_SVC=1`, same patched build
main `82d187fe…` / sdk `e8cdceb1…`, host at `/path/to/external-drive/xc3/work/tools/dmhost`), plus:
[Fenced excerpt omitted from the shareable research record.]
Installation succeeded — the host printed the original instruction it replaced, which matches the disassembly:
[Fenced excerpt omitted from the shareable research record.]
**Zero hits.** Not one probe fired, and the run reproduced the identical failure:
[Fenced excerpt omitted from the shareable research record.]
Elapsed 0.6 s, exit 139. The guest block base differs from Round 18 (`0x7000000000` vs `0x125e04000`) because
address randomisation is only off under lldb; module bases and offsets are unchanged, and the crash offset is
identical, so it is the same fault.

## What this means, honestly
`main+0x124199c`'s `bl memset` sets `lr = main+0x12419a0`, and reaching that instruction requires executing
`main+0x12418f8`, which carried a `brk`. Both cannot be true, so **either the executed image is not the image the
probe patched, or the probe's trap is not being delivered**. I did not establish which, and I am not going to
theorise further without data.

Consequently the values the round was meant to obtain — the entry `addr`/`size`, the returned bool, VAMM's
rejecting branch and the range inequality — were **not obtained**. Everything about "alias too small" or "VAMM
rejects it" therefore remains unproven, and no fix is proposed.

## The precise gap, and the smallest next step
One more run is needed, and only to test the mechanism itself: install a single probe at a point **known** to
execute in this run, `main:1240898` (it appears in the printed backtrace `bt: main+0x1240898 …`). If that probe
also does not fire, the fault is in probe delivery (or the patched image is not the executed image) and lldb is
the fallback; if it fires, the four target points were simply not on the executed path and I will re-derive the
path from the printed backtrace instead of from linear reading.

That is one 30 s run with one probe, no guest change. I did not spend it, because the supervisor limited the round
to one run and asked for a stop when the observation does not land.

## State
- No HLE implemented; the exception-stack getter remains unimplemented and still unrelated to any proof.
- Host tracked code, rewriter, profile and memory keys untouched. Shared `dm/host/dmhost` not overwritten.
- Probe configuration, log: `/path/to/external-drive/xc3/work/logs/probe.log`; launcher kept on SSD.
