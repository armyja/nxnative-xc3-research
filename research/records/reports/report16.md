# Round 16: the three keys through MSL, Mac compilation, library load and pipeline creation

Experiment only. **HEAD unchanged at `2682fbc`**; no commit, no push, no PR, no repository change.
Everything below is under `/path/to/external-drive/xc3/proto/translate/`.

Correction carried from review: `dmsh_xlate_bin/dmsh_xlate` is a **framework-dependent** apphost, not a
self-contained one — it needs a shared .NET runtime, which is why `DOTNET_ROOT_ROOT` mattered. No commit for the
wording.

## Inputs (unchanged from Round 15, not re-extracted)
| key | stage | source | SPIR-V sha256 |
|---|---|---|---|
| `f08a30202513bbba` | vs | shd_ocean slct0 prog0 entry0 | `fe61876759aacdcf…` |
| `8b37aad9f6878b32` | ps | shd_ocean slct0 prog0 entry1 | `fcc327513e89b4ce…` |
| `f625a4f33c78facd` | cs | shd_cloud slct3 prog0 entry0 | `65635116869f40c1…` |

Resource facts: the three jobs carried empty `tex` / `img` / `attr` / `fout` because no answer table exists for this
title, so **every query was answered with translator defaults**. Nothing was invented to make a step succeed.

## Commands actually run
[Fenced excerpt omitted from the shareable research record.]
Tools: `spirv-cross` (the locked in-PATH binary), `Apple metal version 32023.921 (metalfe-32023.921.6)`,
`Apple clang version 21.0.0`, device **Apple M1**. No tool was installed; `spirv-val` is still absent and was not
added.

## Layered result per stage
| stage | SPIR-V generated | external spirv-val | MSL generated | Mac metal compile | metallib link | library load | pipeline created | VS↔PS interface linked |
|---|---|---|---|---|---|---|---|---|
| vs `f08a…` | pass | **not run (spirv-val absent)** | pass, 2006 B, rc 0 | pass, rc 0 | pass, 4259 B | pass | pass (as part of the pair) | **pass** (see below) |
| ps `8b37…` | pass | **not run (spirv-val absent)** | pass, 728 B, rc 0 | pass, rc 0 | pass, 3787 B | pass | pass (as part of the pair) | **pass** |
| cs `f625…` | pass | **not run (spirv-val absent)** | pass, 34457 B, rc 0 | pass, rc 0 | pass, 12907 B | pass | **pass**, `maxTotalThreadsPerThreadgroup=1024` | n/a |

No stage failed, so there is no first error to report.

## Exported functions (read from the loaded libraries, not guessed)
[Fenced excerpt omitted from the shareable research record.]

## Render descriptor, item by item
| item | value | where it comes from |
|---|---|---|
| vertex function | `main0` | library export |
| fragment function | `main0` | library export |
| vertex attribute 0 | `MTLVertexFormatFloat4`, buffer 0, offset 0 | the generated MSL declares `float4 m_22 [[attribute(0)]]` |
| vertex buffer 0 stride | 16 bytes, per-vertex | one float4 attribute; **not** a game vertex-layout fact |
| colour attachment 0 format | `MTLPixelFormatBGRA8Unorm` (80) | **experiment choice only** — the MSL says the fragment writes `float4 m_22 [[color(0)]]` but does not determine a pixel format |
| rasterisation | enabled in the successful attempt | see below |

Two attempts were made and both are reported:
[Fenced excerpt omitted from the shareable research record.]
The first attempt is why a format had to be chosen: Metal rejects a non-void vertex function with rasterisation
off, so disabling colour output could not avoid inventing a format. The single format used is stated above as an
experiment choice; no other format was tried, and no claim is made that BGRA8Unorm is what the game uses.

## Compute
`COMPUTE_PIPELINE_OK`, `maxTotalThreadsPerThreadgroup = 1024` (the device/function ceiling).
**The actual threadgroup size is not established here**: the MSL has no `[[threads_per_threadgroup]]` attribute
(grep count 0), so the size would come from the dispatcher — a game fact this experiment does not have. No
dispatch was performed, so nothing about the results is claimed.

## What this does and does not say
- These three shaders translate (no `spirv-val` exists to check the module externally), compile with the locked
  Metal compiler, load from a metallib, and build the pipeline objects.
- It says nothing about the game's render targets, vertex layouts, resource types, the other 3,701 stages, a full
  library, `c1_full.tsv`, the host, iOS, or any run. No command buffer, draw or dispatch was issued.
- Round 15's default answers for every resource query remain a standing limitation: the `1 cbuf / 0 textures`
  (vs, ps) and `1 cbuf / 1 texture` (cs) in the `.res.json` files are the translator's defaults, not measured XC3
  resource facts.
- `dmsh_build`'s post-processing (`vs_init`, `vs_pad`, the integer-input second pass) was **not** applied; this was
  a raw conversion, and it compiled and linked without it. Whether the game needs those steps is untested.

## Evidence
`/path/to/external-drive/xc3/proto/translate/`: `work/*.spv`, `msl/*.metal`, `lib/*.air`, `lib/*.metallib`,
`smoke/smoke.m`, `smoke/smoke`, `smoke/smoke.log`, `jobs_meta.json`, `results.json`.
`sha256: spv / msl / metallib` are in the tables above (full values on disk).

## Next blocker, precisely
Not a compiler or runtime problem: what is missing is the answer table (resource facts) and a real game profile,
plus a decision on the geometry chain. A minimal VS/PS/CS translation sample is now demonstrated end to end up to
pipeline construction; anything beyond that needs measured facts, not defaults.
