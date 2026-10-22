# Round 51: derived texture base decodes the five slots, and the runtime binding is real

**HEAD `7be6d27`**, no commit. Static derivation, a rebuild, and one 5 s run. Artifacts under
`/path/to/external-drive/xc3/work/experiments/boot14-slots/`.

## 1. Static evidence for the derived base (before any build)
Pinned `xc3_lib`, the five pixel stages that had undecoded texture bindings, read from the same `shd_layout.wishp`:

| program | sampler_count | sampler_index_count | sampler | handle | visibility |
|---|---|---|---|---|---|
| slct1 p17 | 1 | 1 | `s0` | 0 | Fragment |
| slct2 p1 | 1 | 1 | `s0` | 0 | Fragment |
| slct2 p9 | 1 | 1 | `s0` | 0 | Fragment |
| slct2 p25 | 1 | 1 | `s0` | 0 | Fragment |
| slct3 p1 | 1 | 1 | `s0` | 0 | Fragment |

Every one has **exactly one** sampler, at **index/handle 0**, fragment-visible — and the translated code's combined
handle word is `8` (byte `0x20`). With the decode `t = (byte - TEX_BASE) / 8`, a base of `0x20` maps that word to
slot 0, which is the only slot the metadata describes. That is independent structural evidence for base `0x20` and
for `slots = 1` **as the minimum range covering this set**, not as a claim about the whole title's texture table.

## 2. Rebuild with the derived base
New external profile `boot14-slots` (the `boot14` profile copied, then only `nvn_tex_base = 0x20`,
`nvn_tex_slots = 1`; all other NVN bases stay 0, `shader_facts` stays default-only, the value is commented in the
profile as a derived hypothesis for this 14-key set). Real chain computation:
[Fenced excerpt omitted from the shareable research record.]
So the same five bindings that were undecoded now decode, and the five variant metallibs (`*_bf`) were produced.
Nothing from the old chain was reused; every artifact is under `out/b-367c383d8da0/`.

Note on the reflection file: `bindings[].slot` is still `None` there for tex/samp_tex — the decoded slot lands in the
**variant** artifact, not in the base reflection. I record that rather than claiming the JSON changed.

## 3. The run
Host rebuilt from this profile (`dmhost`, sha256 prefix `2b947630b07d89e8`), one 5 s headless run with
`DM_LANG=en-GB`, `DM_NVN_KEYDUMP=5e2fd9a7dbcdbd8f:1`, `DM_PSO_RECORD`, `DM_MEMSTAT`, `DM_NVN_SHDUMP`:
[Fenced excerpt omitted from the shareable research record.]
No crash, no FATAL, no Metal validation error; the run ended by the 5 s stop (exit 0).

## 4. What this establishes
- **The derived mapping is validated for these five stages**: the pixel stage's texture binding at **register 0** is a
  **real** texture object (`real`, `tid=838`), not a dummy, and the sampler at register 0 is real (`sid=256`), in a
  draw that uses the new pair `140b0e5311a23571` / `5e2fd9a7dbcdbd8f`.
- The texture is `target=2` (2D), `88x88x1`, 7 mip levels, `swz=2345`, `fmt=152` — so the default `texture2d<float>`
  translation is at least dimensionally consistent with the descriptor; it is **not** a measurement of the component
  type or of the game's intended format.
- Vertex and fragment uniform buffers are bound with real contents (160 B at r0 for both stages, plus 255 B at the
  vertex r1), and the draw targets 1920×1080.
- Runtime combination of this pair is now observed in one draw; the earlier statement that the texture slot "must
  come from descriptor writes rather than a base constant" is retired — the base constant plus the NVSD metadata
  **was** the missing piece, and the runtime binding then confirmed it.

## 5. What remains unmeasured
`image`, fragment-output and attribute facts are still defaults, as the reflection shows; the other NVN bases
(sampler/image/storage) are still placeholders; only slot 0 of a one-slot sampler set is covered, so this says nothing
about a title-wide texture table. Two-colour PS output is reflection, not a measured render target set. No claim about
picture correctness.

## Limits
No tracked change, no commit, no push/PR, no tool install, no new archive extraction, no GS/HLE/rewriter/memory/
scheduler/global-language change, no translator-constant or lock edit; the shared `dmhost` and the `boot14`/`four-key`
experiments were left untouched.
