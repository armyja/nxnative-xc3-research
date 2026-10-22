# Audit follow-up: corrected boundaries, NVSD coverage, image observability, next bounded step

Base `6a2ebe1` / chain `34aab9ef1ab1`. Offline only; nothing built, nothing changed in the profile or the tree.

## 0. Boundary table, recomputed by the same expression (asserted)

`slot = (word*4 - 0x20) / 8`, and `word_for(slot) = (0x20 + 8*slot) / 4`; every pair asserted in both directions.

| slot | word | byte | notes |
|---|---|---|---|
| 12 | 0x20 | 0x80 | **my previous table wrongly listed this as slot 15** |
| 15 | **0x26** | **0x98** | last slot inside `slots = 16` |
| 16 | 0x28 | 0xA0 | first slot outside; 20 bindings at exactly this word |
| 26 | 0x3C | 0xF0 | largest word seen; 1 binding |

## 1. NVSD coverage for the undecoded textures: **none**

All **87** undecoded texture bindings belong to shaders whose only source is a runtime dump
(`recovered#<key>` / `runtime_dump#<key>`). **Zero** of them is container-sourced, so there is no NVSD to compare
against for any of them - including both extremes (slot 26: `89a81e2bdb64721f`; slot 16: 20 shaders, e.g.
`0ab147eb78119b45`).

Consequences, stated separately:

- **Independent metadata support for `slots = 27`: none.** The candidate rests entirely on the decode formula plus the
  observation that the words are contiguous and all divide exactly. That is a derivation, not a runtime verification.
- The container-sourced shaders (261 rows) have no undecoded textures left, so nothing there argues against 27 either.
- Remaining runtime-only list: the whole 87 (the table `resource-audit.tsv` carries each one with its word, byte,
  derived slot and source).

## 2. Image: the name is a cbuf word, and NVSD has no image metadata

`decode_tex` matches `fp_i_cb2_48_r32ui` as `bank = 2`, `h = int("48", 16) = 0x48`, so the handle is read from **c[2] at
byte 0x120** - the `48` is a **cbuf word index**, not a byte offset and not the handle itself.

`Nvsd` (xc3_lib 0.21) carries `uniform_buffers`, `storage_buffers`, `samplers`, `attributes` - **no images field**. So
there is no NVSD fact that could constrain the image index; the only anchor would be a runtime observation.

The current rejection is the range test in `decode_tex`, which cannot hold while `IMG_BASE = IMG_SLOTS = 0`:

[Fenced excerpt omitted from the shareable research record.]

If a runtime observation gives the NVN image register `r` for this binding, then `IMG_BASE = 0x120 - 8*r` would make it
decode to slot `r`. **One binding cannot establish that**: with a single `(handle, r)` pair, base and stride are only
constrained along one line. Two bindings with different handles and different observed `r` would be needed to pin both,
and only then could a base be called supported.

## 3. Can the existing instrumentation see it? No - the branch is downstream of the failure

Static path: `shader_load` returns nil when the reflection cannot be converted (exactly what
`fp_i_cb2_48_r32ui` causes), so the program has no pixel function; the draw is never encoded, and the
`NVN_RB_IMG` branch inside the argument encoder (which reads
[Fenced excerpt omitted from the shareable research record.]
) is only reached while encoding a program's bindings. PASSDUMP's per-pass binding records enumerate the same loaded
stage, so **a blind PASSDUMP run would show nothing for these draws**. That is a property of where the record is taken,
not of the run.

What *is* reachable: `OP_BIND_IMG` in the command stream. It fills `S.img[stage][first..first+n)` from the command's
handle array and runs while the game records the buffer, i.e. **before and independently of** any shader load, so it is
reachable for draws that later fail. It has **no logging today** - that is the gap.

## 4. Minimal observation plan (designed, not implemented)

- **Point**: the `OP_BIND_IMG` handler (`dm/gfx/nvn/nvn_mtl.m`, the `case OP_BIND_IMG:` arm).
- **Switch**: one new read-only env variable, e.g. `DM_NVN_IMGBIND=<frame>`, active for that single frame only, silent
  otherwise; no change to any state, no effect on encoding.
- **Record per call**: `frame`, the pass counter `g_stat_pass`, `stage`, `first`, `count`, and for each handle
  `i` in the array: the handle word, the resolved serial, and the texture's width/height/format.
- **Timing**: any frame after the title screen is up (the recorded runs reach it at ~frame 2100); the command that
  binds images for the lighting programs is recorded every frame regardless of our shader failure, so the window does
  not depend on guessing a frame in which the draw succeeds.
- **Target**: stage = fragment, and the records whose pass also binds the `shd_lgt` programs. The nine keys are known;
  `shd_lgt` slct 5 program 1/73/75/77/83/109/119 and slct 7 program 1.
- **Tuple that answers the question**: `(stage, first, count, handle[i], serial, width, height, format)` for the
  fragment binding whose resolved texture is an integer-format target of the lighting size.
- **Success**: a fragment record with `count == 1` gives `r = first` unambiguously, and with the handle's descriptor we
  can state `IMG_BASE = 0x120 - 8*r` as a *candidate*; a second later binding with a different handle and different
  `r` upgrades it to supported.
- **Refutation**: no `OP_BIND_IMG` with a fragment stage anywhere in the run means images are never bound on this path,
  and the shader can never run - the image question is then closed for this title, not "still unknown".
- **Ambiguity branch**: if `count > 1`, the array gives several `r` but not which one the single declared image uses;
  the shader's own `reg` would be needed and it is unavailable (it is what fails to decode), so that record narrows by
  format/size only and must be reported as ambiguous, not as an answer.
