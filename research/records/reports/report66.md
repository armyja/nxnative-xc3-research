# Report 66 — fout candidate for the two target keys, new chain, and one no-draw PSO smoke

Scope: offline only. No guest, no host build, no full-645 rebuild, no tracked change (HEAD `82f488b`, 0 tracked
modifications). Experiment all under `/path/to/external-drive/xc3/work/experiments/fout-uint-two-key/`.

## 1. Facts: the exact diff and its provenance

`fout-uint-two-key/profile/010074F013262000/shader_facts.tsv` is the audited candidate's file plus one data row (and a
4-line comment that says what the row does and does not answer):

[Fenced excerpt omitted from the shareable research record.]

Diff: the two original `DEFAULT-ONLY` comment lines were replaced by four comment lines, and that one row was added.
No other file in the profile or package root differs; the candidate directory itself was not modified (its
`shader_facts.tsv` sha256 prefix is still `0c9209efdb427804`, `dmsh_chain.h` still `afbc345e12611bbd`).

Provenance (`provenance-fout-uint-two-key.md`): same-pass record of run `run-psort-20261021-190120`,
`boot.log:571–581` — pass `553275`, `assoc=same-pass`, `map` identity, slot0 NVN `0x17`→MTL 103, slot1 NVN `0x0b`→
MTL 53, both attached, slots 2–7 absent. It is **not** PC reflection; `pc_missing` stays true; `tex`/`img`/`attr` stay
empty and every other query for this key is still answered with the default. No claim about other uses of the pixel
shader, and the remaining 644 keys are absent and unchanged.

## 2. Input verification and the new chain

- Two package records re-read from the copied package root: `e4e34184aa4759c5` vertex, `ps_shd_lgt_s5p73.bin@0`,
  ctl 2176, code 512, recomputed key equal, code-area stage `vs`; `4bae5b8abd3bec7f` pixel, same package, ctl 2176, code
  768, recomputed key equal, stage `ps`.
- Full map re-validated against the copied packages: **645 keys, 0 problems; 90 pairs, 0 problems**.
- Tools: `dmsh_chain.py --check-tools` passes with the existing runtime
  (`DOTNET_ROOT=/opt/homebrew/opt/dotnet/libexec`; no install). Chain computed by the real tool from the changed facts
  table: **`012cc15f1405`**, and `dmsh_chain.py --header` wrote that value into the experiment copy's `dmsh_chain.h`
  only. No translator/lock change; no old chain library renamed or reused.

## 3. Build (one attempt, explicit two keys, J=1, fresh CAS)

[Fenced excerpt omitted from the shareable research record.]

rc=0. Summary: `new key 2`, `Metal cache: mac 0 reused, 2 compiled`, `shaders reading driver segments at run time 0
(c0 0, c2 0)`, `shaders with a binding whose slot was not decoded 0`, `queries without a PC answer 2`. Output:
`out/b-012cc15f1405/{4bae5b8abd3bec7f,e4e34184aa4759c5}_b.{metallib,json,metal}`.

## 4. The real job input (not just the profile row)

The build's own job JSON was captured before the temp workdir was removed:
`jobs/job_2844220512610255839.json`. It contains the two jobs, and the fragment job is

[Fenced excerpt omitted from the shareable research record.]

so the values that reached the translator are exactly colour output 0 → uint and 1 → uint. The vertex job has
`"fout":{}` — the VS got no new facts.

## 5. What changed in the generated shader, and what did not

| | old (`b-9f73847b56ec`) | new (`b-012cc15f1405`) |
|---|---|---|
| colour outputs | `float4 m_29 [[color(0)]]`, `float4 m_31 [[color(1)]]` | `uint4 m_30 [[color(0)]]`, `uint4 m_32 [[color(1)]]` |
| `as_type<float>` occurrences | 6 | **0** |
| writes | `out.m_29.x = as_type<float>(_136)` … | `out.m_30.x = uint(_137)` … (`uint(...)` integer conversion of the integer expression, not a bit cast) |

Unchanged: bindings are still `support_buffer` (arg 0), `fp_c4` (cbuf reg 1, arg 1) and `fp_i_cb2_48_r32ui`
(`texture2d<uint>`, img reg 0, arg 2); `drv_reads` is empty; the vertex MSL is **byte-identical** to the old build
(sha256 prefix `fb14dea36661db74` both), so only the fragment output types changed. The image base/slots and every
profile constant (`nvn_img_base` 0x120, `nvn_img_slots` 1, `nvn_tex_slots` 16) are untouched.

## 6. The one PSO smoke (no draw, no command buffer, no guest)

`psosmoke.m` (sha256 prefix `000eacf69ebb9b2a`) loads both new metallibs, prints their function names, and creates one
render pipeline. Full output (`smoke.log`):

[Fenced excerpt omitted from the shareable research record.]

Descriptor provenance:

- **From the same-pass runtime record**: colour 0 = MTL 103, colour 1 = MTL 53, depth = 260, stencil = 260, and the two
  program keys.
- **Diagnostic choices, not runtime facts**: `rasterSampleCount = 1` (no same-run sample-count evidence), the vertex
  layout (`attribute(0)` Float4, offset 0, stride 16, per-vertex) read from the new MSL input declaration, and the entry
  name `main0`.
- **Not shown**: that the game's own vertex layout or sample count is reproduced, that a stencil attachment is actually
  present, any GPU execution, any image read/write, or image correctness. A successful PSO only says these listed
  diagnostic descriptors are compatible.

## 7. What this establishes, and what stays unknown

- Establishes: the existing `fout` contract, given `{"0":"uint","1":"uint"}` in the real job, makes the translator emit
  `uint4` colour outputs and removes every `as_type<float>`; the resulting pair of libraries forms a pipeline with the
  recorded integer attachments and depth/stencil formats, where the old float4 pair did not.
- Stays unknown: whether this pixel shader is used against float targets elsewhere (and whether the uint declaration
  would then be wrong); the game's actual vertex layout and sample count; the actual image resource and any GPU read;
  the rest of the 645-key library (not rebuilt); c1/support fingerprint validity for a whole library (no host run, and
  this experiment has only two keys). The library built here is an experiment artifact, not a guest library.

## 8. Untouched

No tracked change, no commit; `AGENTS.md`, `XC3-SETUP.md`, the shared `dmhost`, the candidate 645 directory, its
packages, CAS and `out/` were not modified; no GS built, no exemption growth, no installation, no new asset extraction.

## Erratum (supervisor review)

Section 2 described both keys as coming from `ps_shd_lgt_s5p73.bin`. That is wrong: the map places the vertex key
`e4e34184aa4759c5` in `vs_shd_lgt_s5p73.bin@0` and the pixel key `4bae5b8abd3bec7f` in `ps_shd_lgt_s5p73.bin@0`, two
independent packages. The verification itself passed on both; only this sentence was inaccurate. No package was changed.
