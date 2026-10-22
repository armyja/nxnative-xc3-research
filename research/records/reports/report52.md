# Round 52: the game's own loading screen, captured and inspected

**HEAD `7be6d27`**, no commit. One 8 s headless run. No production change.

## Correction first: the reflection field is `reg`, not `slot`
The base reflection `5e2fd9a7dbcdbd8f_b.json` has **`reg: 0`** on its `tex`/`samp_tex` bindings — `slot` is not a schema
field at all. My earlier text ("slot=None, decoded only in the variant") was wrong; the statistic script counted a
non-existent field. The JSON was already correct and was not modified. What the `nvn_tex_base = 0x20` change did is
visible in the **build's own criterion** (undecoded bindings 5 → 0) and in the five generated `_bf` variants, not in
that field.

Scope correction accepted as well: the run **measured one** pixel stage's binding
(`5e2fd9a7dbcdbd8f`, texture reg 0 real, sampler reg 0 real). The other four are covered by the same structure and
formula statically, not by runtime observation.

## The run
Same host (`dmhost`, sha256 prefix `2b947630b07d89e8`), same profile and 14-key library, chain `367c383d8da0`,
`DM_LANG=en-GB`, no CPU probes, no PASSDUMP; supervisor with a real 8 s wall clock:
[Fenced excerpt omitted from the shareable research record.]
Both frames were captured before the `CAMetalLayer` check (the shot path runs earlier), so this works headless.

## The images
[Fenced excerpt omitted from the shareable research record.]
Both decode completely (IDAT inflates to exactly `1920*1080*3 + 1080` bytes). Absolute paths:
[Fenced excerpt omitted from the shareable research record.]

**I opened both and looked at them** (no statistical proxy):
- Both show the game's **loading screen**: a black field with a small blue-and-gold circular emblem at the lower right
  and the word **`Loading`** immediately left of it, in the game's own font.
- The frames differ exactly as an animation should: frame 45 reads `Loading.` (one dot), frame 60 reads `Loading...`
  (three dots). The emblem's inner glow differs slightly between the two.
- No black screen, no colour blocks, no transparency artefacts, no stretching; aspect is correct at 1920×1080.
That is the first direct evidence in this project of the game producing a **correct-looking UI frame**, not merely a
created PSO or a bound texture.

## What this does and does not establish
Established: the title boots, renders, and presents its real loading UI through the translated shader path, with the
14-key set and the derived texture base — including the new pair that used a real 88×88 2D BC7 texture in one draw.
Not established: gameplay/picture correctness beyond this screen; per-PS component facts other than the one measured;
any title-wide texture/sampler table (only slot 0 of a one-slot set); `image`/fragment-output/attribute facts remain
defaults.

## Known issues still open (unchanged, not addressed this round)
- `nvnTextureWriteTexelsStrided` unimplemented.
- Save transaction falls back to a read-only committed directory (`errno=45`).
- `c1_full.tsv` stale/missing and `pso_manifest.tsv` missing warnings.

## Limits
No tracked change, no commit, no push/PR, no install, no new asset extraction, no shader build, no change to memory,
scheduling, HLE, rewriter, GS, driver bases or global language; shared `dmhost` untouched; all artifacts on the SSD.
