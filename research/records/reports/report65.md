# Report 65 — target pass colour attachments: NVN 0x17 and 0x0b, directly mapped to MTL 103/53

Scope: the one authorised supervised psort run (owner lowered the launch gate to 2800 MiB explicitly; everything else
unchanged). No shader/host build, no profile/value change, no tracked change. HEAD `82f488b` unchanged.

## 1. Authorisation and gate

- Owner authorised lowering the pre-launch gate from 3072 to **2800 MiB** after the measured available fell below the
  original bar (2966–2989 MiB). Same formula, same 10 s at ≥1 Hz; in-run 1 GiB stop and every other stop unchanged.
- Gate: **10 samples, min available 2989 MiB** → launched.
- Run `imgdiag-run3/run-psort-20261021-190120`: host `dmhost-psort2` sha256
  `1aa43a7c84331f3268f4f4a1803fd5f77fa2c63a16a2adce8c4cb70c047e19f6`, candidate chain `9f73847b56ec`, six unchanged
  inputs, `DM_NVN_PSOFAIL_RT=4bae5b8abd3bec7f`, `DM_NVN_KEYDUMP=4bae5b8abd3bec7f:1`, `DM_NVN_IMGBIND` unset.
- Time: `first_at=164.737 s` (includes the 10 s gate; ≈154.7 s of guest), `term_at=164.740`, `gone_at=164.932`.
  Samples 638, min available **1644 MiB**, max RSS **1136 MiB**. Two audited geometry shaders exempted at 61.728 s by
  content; the four new GS were dumped but the psort terminal fired first.

## 2. The record (verbatim, boot.log:571–581)

[Fenced excerpt omitted from the shareable research record.]

Header and done agree on pass (`553275`), assoc (`same-pass`) and slot count; `snap=valid/553275` and `k.cfmt` equals
the snapshot `cfmt`, which is exactly the association condition. The only textual difference is the header's `_b`
variant suffix on the fragment key versus the bare key on the done line — the same shader.

## 3. Per-attachment facts (map is identity, so logical colour i = physical slot i)

| slot | NVN format | NVN meaning | serial | flags | size | view override | attached | Metal |
|---|---|---|---|---|---|---|---|---|
| 0 | `0x17` | RG32Uint | 12889 | `0xc` | 640x360x1 | set_format=1, fmt `0x17` (= base) | yes | **103** RG32Uint, level 0, slice 0 |
| 1 | `0x0b` | R32Uint | 12890 | `0xc` | 640x360x1 | set_format=1, fmt `0x0b` (= base) | yes | **53** R32Uint, level 0, slice 0 |
| 2–7 | none | — | — | — | — | no view object | no | — |

Depth/stencil: `dfmt=sfmt=260` (Depth32Float_Stencil8). Context: no merge (`lmap` disabled), no deferred replay, no
fence checking, no specialised fragment function (`fsfn=0 ms=0 fzkind=0`).

Mapping is direct and needs no kind inference: the production table has `T[0x17] = RG32Uint` (MTL 103) and
`T[0x0b] = R32Uint` (MTL 53); the view's `set_format=1` carries the *same* format as the base texture, so it is not a
format-changing override. The Metal error's `RG32Uint` is therefore the correct mapping of a genuinely integer NVN
attachment, **not** a host format-kind mistake. The slot index of the 103 attachment is now established: slot 0.

## 4. What this settles and what it does not

- Settles: the target pass has exactly **two** colour attachments, both integer (`0x17`, `0x0b`), both attached, both
  640x360, with the two program outputs mapping to them through identity (no merge). The target shader's two `float4`
  outputs are incompatible with both — which is exactly the observed Metal rejection.
- Does not settle: whether the correct repair is translator-side (`uint4` outputs) or facts-side (`fout` uint for these
  locations, a path that still has no built example), and it says nothing about the same program used against float
  attachments elsewhere. No `fout` value was assigned.
- The sampled image (`reg 0`, `texture2d<uint>`, 640x360, serial 12774 in the earlier observation) is a different
  object from slot 1 (serial 12890); slot 1 must not be reported as "the image".
- No GPU-side evidence; no read/write of any texture is claimed.

## 5. Supervisor defect found by this run (fixed offline)

`supervise4.py` compared the done key to the header key literally, so a header `…_b` with a bare done key was judged
malformed. The run's record is complete and associated; only the stop *label* was wrong. Fixed with a canonical key
comparison and a new synthetic case (`p16-done-bare-key`); `t5.py` is now 16/16, `t2_s4`/`t3_s4` unchanged. The raw
record above is the evidence and is unaffected by the label.

## 6. Not changed, not run

No format/attachment/usage/blend/PSO/cache/`fout`/base/slots/TEX16/GS/stage/facts/library/translator/lock/HLE/
rewriter/memory/scheduler/language change; `AGENTS.md`, `XC3-SETUP.md` and the shared `dmhost` untouched; no commit and
no push. One guest launch, no rerun. Artifacts: `run-psort-20261021-190120/` (boot.log, timing.txt, samples.csv,
exemptions.txt, shdump), `supervise4.py`, `tests/t5.py`.
