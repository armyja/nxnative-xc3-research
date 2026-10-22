# Round 33: the `oe` album switch is taken over; the old fault is gone, frame 8, new null in the game

**HEAD `7be6d27`** on `xc3`, author armyja, one commit over `3c1117e`, not pushed. Diff: **4 added lines in
`dm/host/hle_oe.c`**, nothing else. No tracked change to shader tables, chain files, HLE elsewhere, rewriter, sysres
or memory keys.

## ABI re-verified before coding
From the sdk dynamic symbol table of the *original* module and the patched disassembly:
[Fenced excerpt omitted from the shareable research record.]
No argument register is read, and the single return is `ret` with no value written, so the signature is
**`void f(void)`** — it matches the `HLE_FORCE(..., void, …, void)` form. Had the ABI disagreed, this round would have
stopped as instructed.

## The entry
[Fenced excerpt omitted from the shareable research record.]
placed next to `EnableScreenShot`/`EnableRecording`, with an English comment saying the SDK reaches it through
`am::GetSelfController`, that the host has no `am` and no Horizon album notification source, so enabling needs no am
session and nothing has to be delivered. It does **not** implement `GetSelfController`, does not fabricate a vtable or
object, does not bypass the load or force registers, and adds nothing for neighbouring `am`/`oe` functions.

**Why the mechanism covers an intra-SDK call:** `loader.c`'s `force_lookup` matches by mangled name for every module
and `force_init` documents the table as overriding "the definition inside the module"; the call here is the SDK's own
PLT to `GetSelfController`, not a `main` import, and the run below shows it intercepted.

## The one run
Same supervisor as Round 32 (real 5 s clock, `unset DM_WINDOW`, `DM_AUDIO=0`, own-child RSS/available sampling, 32 MiB
dump cap, TERM→KILL), new run directory, same patches / memory keys / library directory / two-key map. Only the host
changed: `dmhost-oe`, sha256 prefix `308610651d968ff2`, built from the integrated profile whose chain is still
`83e5bf7805f3`; shared `dmhost` untouched.

[Fenced excerpt omitted from the shareable research record.]

## Result: the old fault is crossed
- **Zero** occurrences of `sdk+0x33b0f0` in this run (it was the stop in Round 32).
- Frames advanced from **1** (Round 32) to **8** (`frame 8 (1.03 s)`), i.e. the game kept running and presenting
  through its own loop for another ~3 s.
- The draw from the previous round is unchanged: `[kd] F4 pass 6 vs=58e2e00d24c6f3ea_b fs=5d36d4144f49ec9a_b …`.

## First new blocker
[Fenced excerpt omitted from the shareable research record.]
A null pointer dereference in the **game's own code** (not the SDK), 0x50 bytes into a null object, reached from a
call chain that stays inside `main`. Left untouched, as instructed; this is where the next round starts.

## Memory and limits
RSS peak **550,656 KiB ≈ 538 MiB** over 12 samples (up from ~175 MiB, expected with 8 frames and more resources
live); no `DM_MEMSTAT` threshold and no dump cap was approached. That is a sample peak, not a guarantee about the whole
run. No new dumps, because both shaders were already in the map — no translation was triggered, and no new key was
added.

## Not claimed
Frame counts and the PSO/draw records are **not** evidence of a correct image; no pixel comparison was made and no
display validation exists. The correction from review is accepted: the guest's stride-24 / format 0x22,0x25 layout
differs from the smoke's stride 32, which shows the smoke layout is not the game's, but does not by itself disprove
that the MSL `float4` components are right — that needs the format semantics and was not changed this round.
