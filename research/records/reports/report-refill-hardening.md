# Refill hardening: code-area validation, whole-map validation, recoverable publish

HEAD `7b2e945`, tag `xc3-refill-audit`. Only `dm/gfx/tools/dmsh_refill.py` changed this round (plus its selftest).

## The four defects, and what the evidence shows now

**1. The code area was never validated.** Counterexample reproduced and fixed: a control section with `+0x704 = 8`,
stage byte 0 and `code = b'BADCODE!'` used to verify as a vertex shader. The stage now comes from the code area through
the production parser (`spch._stage_of`: compute by magic, graphics by the SPH header stage bits), so:

[Fenced excerpt omitted from the shareable research record.]

A code area shorter than the SPH header, an empty code area, and a vertex area declared as pixel are refused the same
way. `+0x714` is kept only as a **cross-check** for shaders with no container; a disagreement between it and the code
area is refused, never resolved in favour of one.

**2. Compute was always rejected.** `stage_of` returned only vs/ps, so every legitimate compute package failed with
"stage byte 2 is not cs". Compute is now verified as compute, and refused when declared as anything else. The selftest
covers both directions.

**3. Only the map's keys were read.** A row pointing at the wrong package, a missing file, a bad offset or a stage
mismatch used to be skipped while the run still claimed the input was verified. The whole map is now parsed row by row
and re-hashed, and the pairs file must only name keys the map verifies. Evidence on the real profile:

[Fenced excerpt omitted from the shareable research record.]

**4. Publishing claimed more than it delivered.** Now: validation failures write nothing; packages are published under
unique names first so a failure removes only what this run added; the map and pairs each go through a temporary file
with the previous contents kept in memory, and a failed rename writes them back. `DM_REFILL_TEST_FAIL=pairs` injects a
failure between the two renames: the run returns 3 and the map and pairs come back **identical** (the selftest asserts
the file contents). The docstring states the limit: this is a recoverable sequence, **not** a cross-file transaction.

Also: container bytes and runtime-dump bytes must now agree (code area and the hashed part of the control); a key match
alone no longer substitutes one for the other, and a control-tail difference beyond `ctl_len` is reported instead of
silently replaced. Keys that appear twice in the containers with different bytes are refused rather than using the
first. The incremental test now compares package **hashes**, not sizes, and a same-named package with different bytes is
refused.

## Corrected inputs for the whole 645, in a new directory (not compiled)

`work/experiments/correct-645/`: 261 rows keep their container-sourced packages, 384 come from the recovered packages,
3 invented pairs dropped.

[Fenced excerpt omitted from the shareable research record.]

No build was run; the chain header has not been regenerated. The old polluted profile and package directory are
untouched.

## Tests run
- `dmsh_refill.py --selftest`: 0 failures (rules + CLI round on synthetic data with real SPH headers).
- `dmsh_pairs_from_log.py --selftest`: 0 failures.
- `dm/gfx/tests/test_spch.py`: 26 tests OK.
- `dmsh_chain.py --check-tools` with the corrected profile: rc 0.

## Still not claimed
- `pairs_from_log`'s "one vertex and one pixel key in a pass" is still not a complete draw proof; its output is
  accepted as a conservative pair list, not as evidence that a draw happened.
- `dmsh_link_check` remains a regex heuristic.
- The title screen's albedo/normal consumers and the titan's brightness stay unresolved; nothing here addresses them.
