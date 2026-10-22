# Round 17: external provisional profile, three-sample resource facts, and a corrected compute job

No repository change. **HEAD `2682fbc`**, no commit, no push, no PR. Everything under `/path/to/external-drive/xc3/`.

## 1. Provisional profile (outside the repo)

`/path/to/external-drive/xc3/build/profile/010074F013262000/game.tsv`, found through
`DM_GAME=010074F013262000 DM_GAMES_DIR=/path/to/external-drive/xc3/build/profile`.
Loader check: `game.py 010074F013262000 title_id` → `010074F013262000`; `game.py list` shows
`010074F013262000  010074F013262000  Xenoblade Chronicles 3`.

Built from the already-extracted `/path/to/external-drive/xc3/build/{ExeFS,RomFS}` plus a RomFS manifest generated
locally from those 250 files (15,194,639,214 bytes) — no XCI re-extraction, no `build_ipa_from_nsp.py` run.

### Verified facts and their evidence
| item | value | evidence |
|---|---|---|
| title id / program id | `010074F013262000` | ACID inside `main.npdm` (magic `ACID` at 0x460, title id at ACID+0x10); `nx_extract` reported the same id from the card's NCA |
| name | Xenoblade Chronicles 3 | the NACP in the card's control data |
| display version | 2.2.0 | NACP at 0x3060 |
| modules | `main subsdk0 sdk` | `profile_guess`: every module `main` imports from; main has 448 dynamic imports, sdk is nnSdk (26,897 exports), subsdk0 is NintendoSDK_movie (10,895) |
| graphics | `nvn` | `main` imports `nvnBootstrapLoader` |
| romfs_marker | `/bf3.ard` | largest RomFS entry, 9,710,938,520 bytes |
| build ids | main `82d187fe…`, sdk `e8cdceb1…`, subsdk0 `be1ee79a…`, rtld `e79ab9af…` | extracted NSO headers |
| `shader_main_glslc` | on | 396 occurrences of `0x19866891` in `main`, **and every one has a plausible total size at +0x44** (396/396 checked). This is a real finding, not a guess |
| SDK | 12 | `profile_guess` from the modules' SDK strings; 32 MB system resource from `main.npdm` via `profile_guess.npdm()` |

### Marked provisional (not measured)
`mem_reserve 0x40000000`, `mem_alias 0x10000000`, `mem_stack 0x10000000`, `app_pool 0xCD500000` — all derived by
`profile_guess` from "main never sets a heap (its memory is its own bss)"; main's bss is 8.0 MB. No heap check was
run and nothing here was measured at run time. `shader_separable on` is `profile_guess`'s consequence of
`shader_main_glslc`; whether those 396 are single-stage and combined per draw is unmeasured for this title.
`build v3` — the `3` is the NCA header's Version field carried by both base and update Program NCAs; **the numeric
title version was not independently established**, only the display version 2.2.0.

### One guess reason that is wrong
`profile_guess` justifies `shader_main_glslc` by "the RomFS has no BNSH / BAHS / UnityFS, so the shaders are
compiled into main". For this title the game's shaders are the SPCH containers in `/bf3.ard`; the 396 GLSLC
outputs are real and **additional**. The key stays on because the fact holds, but the stated reason does not.
`profile_guess` has no SPCH rule and predates the extractor.

## 2. Three-sample resource facts

Pinned `xc3_lib` 0.21.0, from the actual NVSDs the keys come from:

| | ocean slct0 prog0 (vs+ps) | cloud slct3 prog0 (cs) |
|---|---|---|
| uniforms | 2 | 12 |
| attributes | 1 | 3 |
| uniform buffers | 1 × `U_OCE` count 2, handle 0, **VertexFragment**, 80 B | 0 |
| storage buffers | 0 | 3 × `BufferObject` h2 / `CalcObject` h3 / `LightObject` h4, all **Fragment**, 32/224/32 B |
| samplers | 0 | 1 × `t2d`, handle 0, **Fragment** |

Translator reflection from the jobs (`.res.json`):

| key | cbufs | sbufs | textures | images |
|---|---|---|---|---|
| vs `f08a…` | 1 | 0 | 0 | 0 |
| ps `8b37…` | 1 | 0 | 0 | 0 |
| cs `f625…` | 1 | **3** | **1** | 3 |

The descriptor-derived counts agree with the NVSD metadata (1 uniform buffer for ocean; 3 storage buffers and 1
sampler for the compute program), so the **binding topology is statically corroborated**. What the jobs did not
carry is everything the translator answers from defaults:

- **statically provable, but only present in the NVSD**: uniform buffer names/counts/sizes and their visibility,
  storage buffer names/handles and visibility, sampler names/handles/visibility, attribute count. None of it was
  passed in `FACTS`, and no answer table exists for this title.
- **default-only in these three jobs**: every texture/image type and format, every attribute component type, every
  fragment output type — `tex`, `img`, `attr`, `fout` were empty. `.res.json` therefore reports reflection, not
  measured resource facts.
- **still needs a running game**: which textures occupy which slots, their formats and dimensions, the actual
  render targets and vertex layouts, and the driver-segment handle bases. Texture names (`t2d`, `U_OCE`) say
  nothing about dimensions or formats, and I did not infer any.

Handle bases: the translator has Mario's `TexBase` / `SampBase` built in. The NVSD gives handle **indices**
(0…4 here); the address is `base + 8 × handle` and the base for this title is unknown. That is a configuration
question for you, not something I can make up, and the translator was not touched.

## 3. The compute job was missing statically provable facts — corrected

The computer shader's control record declares them, and the translator consumes exactly these keys
(`Program.cs`: `Local(i)` from `job["local"]`, `QueryComputeSharedMemorySize()` from `job["shared"]`, defaults
`(1,1,1)` and `0`):

[Fenced excerpt omitted from the shareable research record.]

So the Round 15 job took the defaults. The SPIR-V proved it: `OpExecutionMode LocalSize = 1 1 1`.

Correction (only this one job, on SSD, as instructed):
[Fenced excerpt omitted from the shareable research record.]
VS/PS were not retranslated and the Round 16 MSL / metallib / pipeline smoke were **not** rerun, so those compute
artefacts correspond to the superseded `(1,1,1)` module and are stale by this fix. Shared memory matters to the
translated code, not to `MTLComputePipelineState`, which takes no such argument — so the pipeline object built in
Round 16 would not have revealed it.

Three quantities stay distinct: the CTL declares `(16,16,1)` and 7,184 B; the translation now uses them; the
**actual dispatch** thread count is still a game fact nobody has observed. `maxTotalThreadsPerThreadgroup = 1024`
from Round 16 is only the device ceiling.

## 4. Minimum prerequisites before a CPU bring-up attempt
1. An answer table for this title (texture/image types and formats, attribute and fragment-output types). Every
   resource query in these three jobs was a default; a build against defaults is not a real build.
2. The driver-segment handle bases (`TexBase`/`SampBase`, and the image base) for this title, or a translator
   that takes them from the profile.
3. The memory partition measured rather than guessed: `mem_reserve`/`mem_alias`/`mem_stack`/`app_pool` are all
   provisional, and no heap check or rewrite has been run.
4. A decision on the geometry chain: six programs contain a `gs` stage, the offline build now refuses a selected
   geometry key, and the host has no geometry encoding path.
5. Only then the remaining chain steps this round did not run: rewritten modules, `c1_full.tsv`, the per-profile
   shader library, the host build.

## Evidence
Profile: `/path/to/external-drive/xc3/build/profile/010074F013262000/game.tsv`; manifest
`/path/to/external-drive/xc3/build/romfs_manifest.tsv`. Experiment: `/path/to/external-drive/xc3/proto/translate/`
(`job_*.json`, `job_cs_old.json`, `work/*.spv` including `f625a4f33c78facd.old.spv`). Raw survey numbers come from
the scripts above, not from transcription.
