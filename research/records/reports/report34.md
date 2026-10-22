# Round 34: the NULL field was never written — the initialiser is a different function and never ran

**HEAD `7be6d27`**, no commit this round. Static trace plus one read-only probe run. No production change, no fix.

Correction accepted from review: what was taken over is **`oe::EnableAlbumImageTakenNotification`'s own definition**;
the SDK's `GetSelfController` PLT was *not* intercepted or replaced — it simply is no longer reached, because the
caller's body is replaced.

## 1. Static chain, and a correction to my own reading
[Fenced excerpt omitted from the shareable research record.]
The wrapper is exactly the tail-call pass-through you described; `lr` stays `0xe6a2cc` because `0x100e6b0` tail-branches
to `0x1014190`.

**Correction:** `0xe6a0ac` is **not** part of `0xe6a194`. It has its own prologue (`sub sp,sp,#0x40; stp x29,x30…`) and
the previous function ends with `ret` at `0xe6a0a8`; `sdis --fn` merged them because it only recognises a function
start at a symbol boundary. So the store `0xe6a0fc str x0,[x19,#0x100]` belongs to a **separate initialiser function
`0xe6a0ac`**, not to the crashing function.

The producer chain inside `0xe6a0ac` is:
[Fenced excerpt omitted from the shareable research record.]
Callers: `0xe6a0ac` ← `0xe69d84`; `0xe6a194` ← `0xe69c94`. Both are called from methods of the same object cluster, one
as the initialiser and one as the user.

## 2. What the probe run showed
One run, same host (`dmhost-oe`), profile, library directory and map, 5 s cap, `DM_PROBE=main:e6a0f4,main:e6a0fc,main:e6a2b4`,
`DM_PROBE_ALL=1`, new directory `runs/20261021-094808`.

[Fenced excerpt omitted from the shareable research record.]
**`0xe6a2b4` fired; `0xe6a0f4` and `0xe6a0fc` did not fire at all.** The store that would populate `[x19+0x100]` was
**never executed** in the entire run, so the field was read as the zero it was allocated with.

That retracts the hypothesis of the previous hour (a producer that returned 0 on some failure): the producer
`0x100dcd0` → `0x10136c0` was **never called**, and `0x10136c0` is an allocating constructor, not a lookup that can
fail to find something.

## 3. The chain as it now stands
[Fenced excerpt omitted from the shareable research record.]
Caller-side guard on the read path: `0xe6a2b0 cbz w8, 0xe6a524` tests `[sp+0x2c0]` (the result of `0xe6a6d4`), **not**
the pointer, so the null is not checked anywhere.

## 4. The one missing observation
**Why `0xe6a0ac` was never called for this object.** Its only caller is `0xe69d84`; that call site (and its guard)
is where the explanation lies. The next bounded step is to disassemble the function containing `0xe69d84`, find the
condition under which the initialiser is invoked, and — if the condition depends on a runtime value — probe that one
call site and its guard (both are ordinary `bl`/`cmp` sites; a safe non-PC-relative probe point exists next to each).

Not yet established: whether the object is created by a path that skips the initialiser (a second constructor), or
whether the initialiser's caller is itself never reached, or whether an earlier failure silently skipped the
initialisation. No fix is proposed until that is known.

## 5. Other leads, explicitly not attributed
The two earlier independent lines — `boot.log:82` save-transaction clone `errno=45` (degraded to a read-only committed
directory) and `:153` `nvnTextureWriteTexelsStrided` unimplemented — were **not** needed by this chain and are not
claimed as related. The `UNIMPL` exception-stack getter still has no evidence tying it to this path.

## 6. Memory / run facts
Run stopped on the same SIGSEGV at 2.7 s (host exit 139), no new dumps (both shaders in the map). No player input, no
second launch, no production edit, no tool install. Artifacts under
`work/experiments/first-runtime-pair-integrated/runs/20261021-094808/`.
