# Report 64 — psort run authorised; the pre-launch gate refused by 4 MiB, no guest was launched

Scope: one authorised supervised run with psort termination recognition. No second attempt, no threshold change, no
application closing, no purge. HEAD `82f488bc2fde4a882357d4ca3f1faaabe17df09a` unchanged; no tracked change, no commit.

## 1. Supervisor and its tests were ready before the attempt

`imgdiag-run3/supervise4.py` = `supervise3.py` plus psort record recognition (the img-final triple is kept but is not
this round's success condition). A record counts as complete only when the target header (`fs=4bae5b8abd3bec7f` or
`_b`, real `[dm] [nvn-mtl] [psort]` prefix) is followed by the map line, each of slot0…slot7 exactly once, and a
`done` line with the same key, the same pass, the same assoc and `slots=8`. Terminal-but-not-success: `assoc=mismatch`
(reported unassociated), cached failure / no record, `diagnostic-error`, and an invalid-switch log. The arm line is
informational and is never treated as a snapshot.

Tests (synthetic child, before any launch): `tests/t5.py` **15/15** — complete; unassociated; missing slot; duplicate
slot; header only; header+map; done with another key; done with another pass; done without map; cached; diagnostic-error;
invalid switch; arm-only; slot8; header and one slot split across two polls. The fault-path suites were re-run against
the new supervisor (`t2_s4.py`, `t3_s4.py`): `fails: none` (try/finally, exemptions by content, dump limits, sampling
failures, signals, refusal of leftover test switches).

## 2. Identity preconditions (read-only)

| item | value |
|---|---|
| HEAD / branch | `82f488b` / `xc3`, 0 tracked modifications |
| host | `linkcheck/dmhost-psort2`, full sha256 `1aa43a7c84331f3268f4f4a1803fd5f77fa2c63a16a2adce8c4cb70c047e19f6` |
| candidate | `imgbase120-correct645`: 645 keys, 90 pairs, **0 validation problems**, 645 packages, chain `9f73847b56ec`, `out/b-9f73847b56ec` present (717 metallibs), `c1_full.tsv` header-only (0 bounded c1) |
| paths | `DM_NVN_SHMAP` and `DM_MSL_DIR=<candidate>/out` absolute; no old profile/library/cas touched |
| environment | no `IMGSUP_TEST_*`, no `DM_NVN_IMGBIND` inherited |

## 3. The gate and the single result

Policy: 10 s at ≥1 Hz with the real pagesize and `free+inactive+speculative`; every sample must be ≥3072 MiB;
otherwise record "not launched" and stop, with no waiting, no re-check, no closing applications and no purge.

[Fenced excerpt omitted from the shareable research record.]

The window stopped at its first sample, 4 MiB short. Nothing was started: the run directory contains only `save/`,
`temp/`, `shdump/` (empty) and `timing.txt`; there is no `boot.log`, no `samples.csv`, no dump, no `psort.txt`, and no
guest or supervisor process is left running. The single authorised guest launch was therefore **not** consumed.

## 4. What this round establishes, and what it does not

- It establishes that the psort supervisor and its tests are in place, that the host/profile/chain identity matches the
  authorised configuration, and that the gate is enforced as written (a 4 MiB shortfall is a refusal).
- It does **not** produce any pass-attachment fact. No snapshot was captured, no `[psort]` record exists, and the table
  from reports 61–63 is unchanged: the index of the 103 attachment, the NVN original format, any view override, slot 1
  and the original sample values all remain unknown.
- No `fout` value was assigned and no format/attachment/PSO/cache behaviour was touched.

## 5. Per the instruction, no retry

The gate refusal is recorded as the round's single result. The earlier state from this morning (10 samples,
3418–3438 MiB) shows the bar is reachable on this machine, but the drop to 3068 MiB is an environment condition I am not
authorised to work around: no threshold change, no waiting, no re-check, no closing the owner's applications, no purge.
A further attempt needs a new authorisation from the owner/supervisor when the available figure is back above the bar.
