# Round 22: the object's initializer is called and fails on a 60 GiB address-region request

No repository change, no commit, no profile change. **HEAD stays `2682fbc`.** One 30 s diagnostic run used (0.3 s).

## Answer to the four questions, first
1. **Which function initialises the object?** `main+0x124081c` initialises it and calls
   `main+0x12434b0`, which is the wrapper of **`nn::os::AllocateAddressRegion(out, size)`**. On success the
   *caller* writes the limit: `main+0x1240888  str x21, [x19, #0x20]` (that is `main+0x1c3fa20`).
2. **When in the real SDK sequence should it run?** It runs in the SDK's own startup, between
   `nninitInitializeSdkModule` and the failing work in `nninitStartup` — see the ordering below.
3. **Did the host actually call it?** **Yes.** The probe at `main+0x12434b0` fired; the call is not skipped, not
   deferred, and not duplicated.
4. **Where does the limit come from, and was it zeroed?** It comes from the size argument of
   `AllocateAddressRegion` (`x21`). It was never written: the guarded store at `main+0x1240888` **did not execute**,
   because the call failed. Nothing zeroed it afterwards — it was simply never set.

## Static chain (with raw addresses)
[Fenced excerpt omitted from the shareable research record.]
The limit load in the crashing function is `0x12418c8  ldr x11, [x20, #0x18]` (x20 = obj = main+0x1c3fa08), i.e.
`main+0x1c3fa20` — the same word the caller would have written. The earlier reading of x11 at `cmp` time is that
load's result, not a later one.

## Measured request and the inequality
[Fenced excerpt omitted from the shareable research record.]
So the SDK asks for an address region of **`0xF00000000` = 64,424,509,440 B ≈ 60 GiB**, while the host's guest
address block reserved for this title is **`0x40000000` = 1 GiB** (`mem_reserve` in the external profile, still a
`profile_guess` value).

**`0xF00000000 > 0x40000000`** — the request cannot be satisfied inside the reserved block, `AllocateAddressRegion`
fails with **`0x1803`**, the limit is never written, both range checks compare against 0, the allocator is bypassed,
and `memset(0, 0, 0x20000)` faults.

This matches a condition the host already documents in `dm/host/hle_svc.c:34`: the AddressRegionManager takes a
fixed node area at the start of the alias region and the very first `AllocateAddressRegion` fails with 0x1803 when
the region is too small. For this title the mismatch is not only the alias size — the **whole reserved address
block** is far smaller than the 60 GiB the SDK wants to reserve.

## Classification
**A** again, now with the initialiser proven to run: the writer was called, its `AllocateAddressRegion` failed for a
measured size, and the failure guard skipped the store. Not "not called", not "written then zeroed".

## Is this a single-profile fix?
**Evidence says it is a memory-model change for this title, and it is larger than one value.** Two inequalities are
now measured or documented:
1. requested address region `0xF00000000` > `mem_reserve 0x40000000` (measured this run);
2. the AddressRegionManager node area `0x3FE00000` > `mem_alias 0x10000000` (host comment, `hle_svc.c:34`; it is the
   same 0x1803 failure).

Both are `profile_guess` values for this title. Raising `mem_reserve` alone to cover 60 GiB is a decision with
consequences the host's fixed partition comment discusses (alias / stack / heap are carved out of `mem_reserve`, and
the alias bitmap is allocated in host memory proportional to the alias size), so **I did not change any key**. Per
this round's instruction the fix is left for you to decide; my recommendation is to size `mem_reserve` from the
measured 60 GiB request plus the stack and heap, and to set `mem_alias` above the 0x3FE00000 node area, then re-run
this same bounded boot.

## Not done
No profile key changed, no HLE, no startup-order change, no forced register/branch, no second run, no lldb, no
`mem_alias`/`mem_reserve` experiment. Host tracked code, rewriter and shared `dm/host/dmhost` untouched.

## Artifacts (SSD)
`/path/to/external-drive/xc3/work/logs/probe3.log` (this run: probes, phases, crash),
`/path/to/external-drive/xc3/work/logs/probe2.log`, `probe.log`, the patched images and their `*.sites.tsv` /
`*.gates.tsv` / `*.fixups.tsv`, plus the launcher and hashes already listed in Round 21.
