# Report 81 — full-window gate fix (offline) and the target VS access constraints

Offline only: no guest, no host/shader build, no translator/profile/base/facts/library change, no commit. New SSD copy:
`/path/to/external-drive/xc3/work/experiments/gate10-fix/` (`supervise6.py`, `tests/t_gate.py`). Report80 carries an erratum
for the 9.16 s window; its evidence is unchanged.

## 1. The defect and the fix

The shipped gate took `n = ceil(secs)` samples at `secs*i/n` (`i = 0..n-1`), so a "10 s" window ended at 9.166 s and the
child was started without a sample at/after the declared end. `supervise6.gate` now:

- starts the window at the **first valid sample** (`t0 = clock()` before it), so the measured span begins with a sample;
- samples at least once per second (`next = min(t0 + len(rows), t0 + secs)`), keeping the last one at or after `t0+secs`;
- **cannot return success without a terminal sample at `elapsed >= secs`**; there is no "sleep to 10 s and launch";
- refuses on any sample below the bar or any sampling error, and the child is never started;
- writes `gate.csv` after **every** sample, so a refusal (below bar or sampling error) leaves the rows taken so far for
  review; no retry, no waiting for resources, no threshold change (2800 MiB, runtime stops unchanged).

It is the same single gate function used by `main`; no second implementation was derived, and the 180 s deadline still
starts at module import (`T0`), not reset at launch.

## 2. Clock/stub tests (`tests/t_gate.py`, 12 checks, all pass)

- terminal sample at 10.200 s for `secs=10` (≥ the declared window), and a sample inside the final second;
- maximum gap between samples 1.000 s (≥ one per second);
- passing gate writes every row to `gate.csv`;
- a sample at 2799 MiB refuses, and the 3 rows taken before it are saved;
- a sampling error propagates (`SamplingUnavailable`), so no launch;
- `secs=0` takes no sample and does not refuse (synthetic tests keep working);
- static checks: `T0` still at import, gate before the child, `if e > a.secs` unchanged, and `main` uses this one gate.

Not integrated into the reviewed launch plan: `ssboobs-run-plan/supervise5.py` keeps its gate until review; a future run
would use `supervise6.py` after review. No long suites were rerun; the sampling/cleanup/SSBO matcher and the two GS
exemptions are untouched.

## 3. Target VS access layout (read-only, same-run evidence only)

`out/b-012cc15f1405/9b770cf888d729bd_b.metal` line 66-84: `_68 = int(gl_InstanceIndex) - int(gl_BaseInstance)`,
`_72 = _68 * 28`, then reads at `+0, +4, +8, +12, +16, +24` (and the remaining word at +20) through
`_m0[(offset) >> 2]` — seven 32-bit words = 28 bytes per instance, matching the NVSD's single `U_Instance` entry
(`size_in_bytes 28`, report71).

Same-run slot facts from `run-20261021-203413`:

| slot | raw size | relation to 28 | note |
|---|---|---|---|
| 0 | 140 | exactly 5 × 28 | can hold five full instances |
| 1 | 576000 | 20571 full instances + 12 bytes | a 28-byte element fits unless the index is at the very end |
| 2 | 16 | 0.57 × 28 | cannot hold a full 28-byte instance from its start |
| 3–15 | 0 | — | no real bind observed |

Conditional constraints only:

- the access is 28 bytes from `(instanceIndex − baseInstance) × 28`; slot 2 is smaller than one element, but whether the
  access is out of range depends on the **instance index used by this draw**, which this diagnostic did not capture;
- slot 1's size is not a multiple of 28; that does **not** exclude it (a large buffer can hold a smaller prefix or padded
  region), so divisibility is not a discriminator;
- slot 0 being 5×28 is compatible, but not evidence that it is the one used.

**Missing evidence:** the same-run log contains no `inst=` draw record and no `d` line for pass 553266 (KEYDUMP was off),
so `instanceCount`, `baseInstance`, a zero-count draw and the per-draw instance index are all unknown. No cross-run draw
parameters were spliced in. Consequently no slot is selected, no `baseCandidate` is computed, `base = 0x110` remains a
hypothesis, and nothing was written to a profile.

## Erratum (gate time anchor)

The gate in section 1 was **not** anchored correctly. It set `t0 = clock()` *before* the first sample, so a slow first
sample shortened the measured window: the supervisor reproduced `rows` 0.9 s … 10.1 s with a valid-sample span of only
9.2 s (`experiments/review81-31mp622r/gate.csv`), and the previous assertion `rows[-1] >= 10` therefore tested nothing.
Additionally, the endpoint decision was taken with `clock()` *after* the CSV write, so a slow write could cross the
endpoint without a real terminal sample.

The corrected gate (still only in `gate10-fix/supervise6.py`, not integrated into the launch plan) records
`window_start` as the monotonic completion time of the first successful sample (first row elapsed = 0), records each
sample's own `sample_at` immediately, and succeeds only when that sample's `sample_at - window_start >= secs` and that
sample itself is at or above the bar. CSV time never counts: if a write crosses the endpoint, another valid sample is
taken or a sampling error refuses the launch. Scheduling stays nominal 1 Hz with actual sample times and latency
recorded; no hard real-time claim is made.

Tests (`tests/t_gate.py`, 12 checks, all pass after correcting one assertion): slow-first-sample then fast, first row 0,
terminal span 10.100 s; CSV write delay of 12 s plus a sampling error on the next call refuses instead of succeeding from
the early sample; a terminal sample below the bar refuses with its rows kept; a terminal sampling error propagates;
zero gate unchanged; `T0` at import, single gate before the child, 180 s comparison unchanged. The earlier counterexample
(9.16 s / 9.2 s) is kept as evidence; no long suite was rerun and nothing is claimed as integrated.
