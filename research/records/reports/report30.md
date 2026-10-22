# Round 30: both instances reproduced from the static image; the code side has no structural link

**HEAD `3c1117e`**, no commit, no tracked change. `AGENTS.md`, `XC3-SETUP.md` and the shared `dmhost` untouched.

Correction accepted: the run's dump files total **5,120 bytes** (2176 + 512 + 2176 + 256); the "640 KiB" was `du`'s
allocated-block figure, not content. And 175 MiB was the peak of three RSS samples, not a guarantee about the whole
initialization.

## 1. Static input identity
`/path/to/external-drive/xc3/work/main.orig.bin`: **37,138,432 bytes (0x236b000)**, decompressed NSO image, `MOD0` at +8.
`main.patched.bin`'s first 0x236b000 bytes are **not** equal to it — the rewriter edits instructions in place — so
`orig` is the only static evidence and was used exclusively. File offset = module offset in this image (the earlier
disassembly at `main+0x1241860` addressed byte 0x1241860 of the patched image, same space).

All four ranges are byte-exact against the dumps:

| key | control offset | code offset | control | code |
|---|---|---|---|---|
| `58e2e00d24c6f3ea` | `0x14e0528` | `0x14e41c0` | 2176 B exact | 512 B exact |
| `5d36d4144f49ec9a` | `0x14e0f10` | `0x14e43c0` | 2176 B exact | 256 B exact |

## 2. The control side *is* structural
The controls form a contiguous, 8-byte-aligned array, and `+0x20` is the section's own byte length:
[Fenced excerpt omitted from the shareable research record.]
Verified on both instances **and** the neighbour after them (three consecutive controls). The gap bytes are zero
padding (`0x14e0528+0x9e1 .. 0x14e0f10` is seven `00`).

Across the whole image there are **402** occurrences of the control magic, all 8-byte aligned, all with
`own ∈ [0x700,0x1000)`. Most are `0x880`; six differ: `0x9e1, 0x87f, 0xa0e, 0x92e, 0x93e, 0x8fd`. So the field is a
real stored length, not a coincidence of the two instances.

## 3. What +0x20 = 0x9e1 / 0x87f actually means
- **vs, 0x9e1 = 0x880 + 0x161.** Bytes `[0x880, 0x9e1)` after the control are **100 % printable ASCII** (a text
  listing of the shader: `}\nTEMP R0, R1;\nLDC.F32X4 R0, buf0[48]; …`). The binary control is 0x880; the section
  stores 353 more bytes of listing. **Yes, 0x9e1 bytes are really stored.**
- **ps, 0x87f.** The stored section is one byte shorter than 0x880; the byte the host copies at `+0x87f` is the
  padding `00` before the next control. **Yes, 0x87f is the real span.**

The host's hash rule (`own` only when `0x760 ≤ own < 0x880`, else `0x880`) is therefore **not** a storage-span rule:
for the vs it hashes 0x880 and skips the listing entirely; for the ps it hashes the exact 0x87f. My prototype
initially applied `own` unconditionally and got a wrong key for the vs instance — proof that the rule, not the span,
decides the key. I did not change `prog_key`, `spch`'s own-length handling or `shard_split`'s `ctl_len`.

## 4. The code side is *not* structural
No reference to any of the four addresses exists in the image: searching for each as a 4-byte and an 8-byte
little-endian value gives **zero** hits, so there is no static descriptor table of `{control*, code*}` (nor offsets)
that pairs them. The code areas sit ~0x3C98 / 0x3CB0 after their controls, but nothing links them.

**Therefore the association is input, not output.** The prototype
`/path/to/external-drive/xc3/work/experiments/xc3-static/extract.py` reproduces both instances exactly:

[Fenced excerpt omitted from the shareable research record.]
(±`nctl` is the host's hash-rule length, shown next to the stored span on purpose.)

## 5. Can a thin adapter support this?
**In part.** A thin adapter can locate and size **control** sections structurally (find the magic, read `own`, align
to 8) — that part generalizes and is verified on three consecutive sections. It **cannot** yet derive the code area
or the control↔code pairing from the image, because the image contains no pointer, offset or table that does so.

So the honest status is: the two instances are **reproducible by fixed offset plus a structural control span**, and
the prototype is labelled a forensic extractor, not a general scanner. I did not infer GLSLC from these instances
(the `91 68 86 19` search before each control is -1, as you found, and I did not retest it), and I did not touch the
396 candidates.

## 6. The single missing observation
**Where the runtime gets `sd->data` and the code length for a control section.** In the static image that association
is not data; it is presumably built by code (`adrp`/`add` around the descriptor construction) or held in a structure
whose layout is not a bare pointer table. One bounded next step would be to trace, in the *unmodified* image, the
call path that fills an `NVNshaderData` for a program and see which register/base the code pointer is computed from —
that would turn the code side into a structural rule too.

Until then, any extraction of these two must take the code offset as an input.

## Not done
No translation, no shader library, no map/profile/driver-bases change, no guest run, no archive export, no tool
install, no change to the 396 candidates' status, no tracked commit, no push/PR. New scripts and this report live on
the SSD.
