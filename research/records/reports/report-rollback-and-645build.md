# Rollback fix, pair provenance audit, and the isolated 645 rebuild

HEAD `7b2e945` + `6a2ebe1` (tag `xc3-refill-rollback`). No guest run, no host/game change.

## 1. The reported rollback defect: fixed and regression-tested

Was: the publish loop replaced every package it wanted - including one that already existed with identical bytes - and
recorded it as created, so a failed publish deleted a package that predated the run.

Now: a package that already exists with the same bytes is **left alone** (not replaced, its inode and timestamps stay,
not recorded, not removed by a rollback); only genuinely new packages are written, each through its own temporary file,
and only those are removed on failure. The recovery message reports how many were removed and how many untouched, and
prints RECOVERY INCOMPLETE (with [RED] lines) when a restore itself fails instead of claiming success.

Reproduced exactly as reported (empty map/pairs, the package for one of the keys pre-placed with identical bytes,
`--allow-dump-only --no-build DM_REFILL_TEST_FAIL=pairs`):

[Fenced excerpt omitted from the shareable research record.]

The selftest carries the same case: pre-existing package survives with its exact bytes, the map and pairs are
byte-identical to before, and the package this run created is gone.

## 2. Pair provenance audit (correct-645)

Every pair now carries a provenance. Classification over the 91 pairs that were there:

| provenance | count |
|---|---|
| container: both keys are the ordered `[vs, ps]` of one SPCH program | **89** |
| same-draw log: the first pair (Round 32 `[kd]` line) | **1** |
| unproven -> **removed** | **1** |

The removed pair is `d7bec51f33a503a4` + `ef5549568475fd20`, and it is exactly the case the review predicted: both keys
belong to `shd_post#83:0`, whose entries are `vs` (0), **`gs` (1)**, `ps` (2). The program is not an ordered
`[vs, ps]`, so the old "GS refused, still pair the two ends" path had produced it.

Evidence file: `correct-645/profile/010074F013262000/shader_pairs.provenance.tsv` (one line per pair).
The 32 pairs produced earlier by the "last key per stage" rule are **not used and not claimed**: the fixed rule
(one pass, exactly one vertex and one pixel key) yields 33 pairs across the 36 recorded runs, and none of the 90 kept
pairs depends on that list - they are structural or the Round 32 draw. A same-pass pair is still labelled
"not a draw proof".

## 3. Isolated rebuild (authorised once)

`work/experiments/rebuilt-correct-645/` - inputs copied from `correct-645`, real chain tool, **fresh** CAS and out:

[Fenced excerpt omitted from the shareable research record.]

### What the build reports, unmodified
[Fenced excerpt omitted from the shareable research record.]
Boundary that the numbers make concrete: the texture handles in this set reach **26**, so `nvn_tex_slots` would need to
be **>= 27**, while the profile declares 16 (derived earlier from the 0..15 range). Nothing was changed to make the
counts go away: base/slots, facts, GS and stage rules are untouched, so 56 shaders keep an undecoded slot and 2 keep a
driver-segment dependency.

### Not done, and not claimed
- No guest run, no console comparison, no picture claim from this build.
- The image bindings (`img`, 9 bindings) and the two driver-segment readers are still unresolved.
- The 3 keys whose control declares `+0x714 = 2` remain out of the map (refused, as before).
- The old polluted profile and its packages are kept as evidence and are not used anywhere.
