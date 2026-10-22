# Report 61 — colour-slot provenance for the target pipeline (offline only)

Scope: offline only. No guest run, no host/shader build, no tracked change, no commit. HEAD `5c5120f` unchanged.
Supervisor correction accepted; the corresponding sentence in report60 is withdrawn here.

## 1. Correction: the NVN→MTL table does not have a kind fork

`dm/gfx/tex/nvn_fmt_mtl.c` writes the table entry by entry in NVN enum order. The line

[Fenced excerpt omitted from the shareable research record.]

initialises **three consecutive entries**, not one entry with three alternatives: `T[0x16] = RG32Float` → MTL 105,
`T[0x17] = RG32Uint` → MTL 103, `T[0x18] = RG32Sint` → MTL 104. `ent.kind` is `1` exact / `2` substitute (the macros
`E`/`X`/`S`/`SX` at `nvn_fmt_mtl.c:18-22`), and `nvn_fmt_to_mtl` (`:76-83`) only indexes `T[f]` (with a separate ASTC
range) and returns `e.kind`; `kind` never selects float/uint/sint.

So "the host turned NVN `0x16` into uint by kind" has **no evidence** and is contrary to the production conversion. The
Metal error proves only that the final MTL attachment was 103 (`RG32Uint`). Its NVN origin could be NVN `0x17`, a view
override to `0x17`, or another resolution path. Report60's "0x16 maps to three formats by kind" is wrong and is
withdrawn.

## 2. Where the attached format really comes from

[Fenced excerpt omitted from the shareable research record.]

`rt_view_fmt` (`:2301-2312`) returns the base texture's `pixelFormat` unless a `cview` override sets a *different* NVN
format that converts and is view-compatible, in which case the converted override is used. Therefore the MTL 103 in the
error comes from either the base texture's NVN format (converted when the texture was created) or from a `cview`
format override. No branch on `kind` exists anywhere on this path.

## 3. Target pair per-slot table (same run only)

Target pair: vertex `e4e34184aa4759c5_b`, fragment `4bae5b8abd3bec7f_b`.

| colour slot | known | evidence | unknown |
|---|---|---|---|
| 0 | MTL colour attachment format **103** (RG32Uint) | `run-triple-20261021-182341/boot.log:601`, same run, target pair | NVN original format (`0x17` or a view override), whether a `cview` format override was set, object serial / level / layer, and the NVN texture's declared usage |
| 1 | the built MSL declares `float4 m_31 [[color(1)]]` | target MSL, built artifact | whether slot 1 is attached in this pass at all; if attached, its MTL and NVN format |

The Metal message names **one** attachment ("a MTLPixelFormatRG32Uint color attachment"); it does not say which index,
and it establishes nothing about slot 1. Two `float4` outputs do not imply two integer attachments, and the error must
not be used to set every `fout` to uint.

## 4. Same-run sources checked, and why they are silent

- **R / P pass records: 0** in this run. `passdump()` returns 1 only while `g_kd_force` is set, and `g_kd_force` becomes
  set inside `draw()` (`nvn_mtl.m:6230`), after `rp_begin` has already emitted the pass records. So the target pass has
  no R record and no NVN format / override / serial for its attachments.
- **`pso_user.tsv`** is the prewarm seed list (`S <key> <0|1>`), not per-draw records. It names the target
  (`S 4bae5b8abd3bec7f_b 1`) and carries nothing about attachments.
- No other line in this run names the target's colour attachment.

Conclusion for B: the NVN original format, view override, object serial, level and layer are **missing facts** for this
run. They are not recovered from another pass, another run, or a title frame.

## 5. The existing `fout` contract, statically

- `dmsh_build.py:260` puts `'fout': {}` in the job JSON by default.
- `dmsh_facts.py:28,34` fills `f['fout'][str(index)] = component_type` from a profile's `fragment_outputs`.
- `dmsh_xlate/Program.cs:79-83` reads `job["fout"]` into `Array8<AttributeType>` and hands it to `GpuGraphicsState`;
  the consumer is in the Ryujinx translator binaries (the strings `FragmentOutputTypes` / `fragmentOutputTypes` are
  present in `dmsh_xlate_bin/Ryujinx.Graphics.Shader.dll`), not in source in this tree.
- The target's built JSON has **no** `fout` field, and the profile's `shader_facts.tsv` is DEFAULT-ONLY, so the target
  was translated with the float default.
- Corpus check: **0 of 645** built MSL files in `imgbase120-correct645` declare an integer `[[color(N)]]` output, so the
  `fout = uint` path has no built example in these experiments; whether it yields `uint4` outputs is **not proven
  offline**.
- `as_type<float>(...)` in the target MSL is a bit cast of the SASS result. On its own it does not prove an integer RT
  (a shader may deliberately write float bits); it is consistent with an integer attachment and nothing stronger.

## 6. Bookkeeping: "schema field complete" versus "runtime converter accepts it"

In the same run, `boot.log:587-595` reports `reflection conversion failed: B binding vp_s0 has no resolved slot number`.
The offline schema and runtime support are different things: the reflection JSON for `sbuf` entries carries `index`
(schema complete), yet the runtime converter still rejects an entry as `B binding <name> has no resolved slot number` at
`dm/gfx/nvn/nvn_refl.m:48`. So a complete schema field does not imply the host converter accepts the SSBO. Recorded
only; no converter change and no chase of the other 29 shaders this round.

## 7. Minimal read-only observation design (not implemented, not built, not run)

Goal: obtain exactly the facts §3/§4 are missing, on the real draw path, without depending on `kd_draw` or
`encode_args` (both run after pipeline creation) and without inventing events.

- **Placement**: inside the render-pipeline creation path, on the failure branch, immediately *before* the early return
  that currently prints the RED at `boot.log:601`. This point is reached before any encoding and before `draw()`, so it
  is independent of `kd_draw`/`encode_args` and remains on the true draw path.
- **Filter**: a static target key carried by an env gate, matching the fragment key `4bae5b8abd3bec7f` (optionally the
  pair). The attachment array index is used **as a slot**; the stage is never taken from it (the standing index ≠ stage
  lesson).
- **One-shot record** (first hit only), all from objects of the same pass:
  `g_pass.serial`, attached slot count, and for each `i < 8`: `g_pass.cfmt[i]` (MTL), `R.rt.color[i]->d.format` (NVN
  original), `R.rt.has_cview[i]`, `cview[i].set_format` and `cview[i].format` (override), the descriptor's attached
  view `pixelFormat` / `level` / `slice`, and `R.rt.color[i]->serial`; plus `g_pass.dfmt` / `sfmt` for context.
- **Why it suffices**: for the same pass and the same objects it puts the NVN original format and any override next to
  the MTL format Metal rejected — the missing fact in §3 — and it needs no GPU work and changes no behaviour.
- **Not part of the design**: no prewarm or prediction event, no format/usage/blend/fout/base/slots/TEX16/GS/stage/
  library/translator/lock/HLE/rewriter/memory/scheduler/language change.

## 8. Still unknown after this round

- The NVN original format of the target's colour slot 0 (`0x17` vs a view override) and whether slot 1 is attached.
- Whether the target's fragment outputs should be uint for both, one, or neither.
- Whether the same shader is used against a float RT elsewhere (no same-key draw evidence in these logs).
- Whether `fout = uint` changes emission at all (contract exists; no built example; consumer in a DLL).

Report path: `/path/to/external-drive/xc3/proto/out/report61.md`.

## Erratum (SSBO model)

The statement that `sbuf` entries are "schema complete (index present), only the runtime converter rejects them" is
withdrawn. `index` is the position in the translator's binding-sorted storage-buffer list, not an NVN slot; the NVN
`reg` is derived from that entry's `cb_slot`/`cb_offset` and the profile's storage-buffer base, and is `None` when that
derivation fails. The host requiring `reg` for `NVN_RB_SBUFP` is therefore correct protection, not a converter bug.
See report69.
