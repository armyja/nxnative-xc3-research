# Report 80 — the target VS draw's 16 SSBO slots were captured: three non-zero, ambiguous, no reg chosen

One authorised gate attempt and one guest launch; no retry. No code/threshold/profile/library change; HEAD unchanged.
Pre-launch identities, the launch, the record and the stop are below.

## 1. Pre-launch identities (recorded before the launch)

- host `linkcheck/dmhost-ssboobs2` sha256 `6ff573ee74423cb3d22ece9f45785063685eb7b157103f781b4813d576dc5c7b`.
- patched modules, each matching the supervisor's Round-21 baseline: `main.patched.bin` `ace9e8fe…c23d`,
  `sdk.patched.bin` `e5b336a9…a26b2`, `subsdk0.patched.bin` `57e50f0e…12c4`.
- profile `fout-uint-correct645`: `nvn_ssbo_bases vs=0 ps=0 cs=0`, `nvn_img_base 0x120`, `nvn_img_slots 1`,
  `nvn_tex_slots 16`; header chain `012cc15f1405`; map **645 keys / 0 problems**, pairs **90 valid rows / 0 problems**;
  every key has `_b.metallib` + `_b.json`; no inherited `IMGSUP_TEST_*`.
- Recorded plan-file hashes and the pre-launch record: `ssboobs-run-plan/prelaunch-20261021-203354/`.

## 2. Gate, timing, resources

[Fenced excerpt omitted from the shareable research record.]

`launch=0.000` is the old compatibility field; the actual Popen time is `launch_at=9.176` after the 10 s gate. The guest
therefore ran about 156 s of the gate-inclusive 180 s budget. 640 samples: min available **1687 MiB**, max RSS
**1164 MiB**. The two audited geometry records were exempted by content at 61.982 s; no other dump stopped the run (the
record stop came first).

## 3. The record (verbatim, `ssbo-obs.txt`)

[Fenced excerpt omitted from the shareable research record.]

- The vertex program carries two shader-data keys: index 0 is the target `9b770cf888d729bd`, index 1 its pixel partner
  `7faa92fddfdd06bd`; the target was found at input index 0, with both entries cached.
- Three slots hold non-zero addresses: slot 0 (size 140), slot 1 (size 576000) and slot 2 (size 16). Therefore the
  observation is **ambiguous**: no NVN reg is chosen and no `baseCandidate` is computed (that arithmetic is only
  permissible for a single non-zero slot).
- slot 2's last real bind was in **frame 4587**, one frame earlier: the table legitimately persists across frames and
  this slot must not be attributed to this draw.
- Slots 3–15 have no observed bind ever (`unknown-provenance`) and zero addresses; the record does not call them
  "never bound" in general.

## 4. What this does and does not show

- It shows, for this draw of the target vertex program, which of the 16 vertex SSBO slots held non-zero addresses at the
  moment the replay layer was about to execute the draw, together with the last real bind provenance of each slot.
- It does **not** identify which slot `vp_s0` refers to: three slots are live, so the mapping stays ambiguous and the
  `baseCandidate = off − 16·r` arithmetic is not available this run. `base = 0x110` remains a hypothesis, and nothing
  was written to any profile.
- The record is a **binding snapshot taken before the original replay draw command**; it is not final-pass association
  (`pass_counter` is explicitly unassociated), not encoder or GPU execution, and not evidence about image contents or
  pixel correctness.
- No conclusion about the other SSBO keys, the 4 geometry shaders (still unsupported, still not exempted by content),
  or any resource's correctness.

## 5. Stop and budget

Stopped on the complete record at `first_at=165.112`; child reclaimed in the finally path (`term_at=165.114`,
`gone_at=165.420`). One gate attempt, one launch, no retry, no threshold change, no additional input, no profile write.

## Erratum (gate window length)

The gate as shipped does not cover a full 10 s monotonic window: it takes `n = ceil(secs)` samples at
`target = secs*i/n`, `i = 0..n-1`, so the last sample lands at 9.166 s for a 10 s configuration (`launch_at=9.176`).
`gate.csv` confirms ≈9.16 s of span. Every sample was ≥2800 MiB and the run thresholds were valid, and the SSBO record
is unaffected, but this must not be described as "a completed 10 s gate". The supervisor's earlier review missed this;
it is not a lowered threshold by the operator. No rerun is made to backfill it.
