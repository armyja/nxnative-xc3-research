# Report 60 — the target draw is reached, but its pipeline is rejected by Metal (integer colour attachment)

Round scope: harden a target-acceptance supervisor offline, pass synthetic-child tests, then one authorised guest run
under a pre-launch resource gate. No host or shader build, no tracked change, no commit, no second launch.

## 1. Offline: target acceptance, and a prefix the plan had wrong

The round's plan described the three records as carrying a `[dm] [nvn-mtl] [pass]` prefix. The source does not emit
that: `PD` writes `[pass] F%llu ` (`dm/gfx/nvn/nvn_mtl.m:1983`) and `MLOG` adds `[dm] [nvn-mtl] ` (`:49`). A matcher
built on the planned prefix can never fire. This was caught offline, before the run, by comparing the emitted formats
with a real `DM_NVN_KEYDUMP` log (`first-runtime-pair-integrated/runs/20261021-093906/boot.log:121`), and the host
binary itself contains the exact img-final format line:

[Fenced excerpt omitted from the shareable research record.]

`supervise3.py` (built on `supervise2.py`, which is unchanged) accepts only the ordered triple in one pass:
`[pass] F<n> K <pass> st1 key=<key>` → `[dm] [nvn-mtl] [img-final] F<n> p<pass> st1 key=<key>` →
`[pass] F<n> d <pass> … fs=<key>`. The key must be complete, with an optional `_b` suffix. A `d` naming the target
before that pass has seen the img-final poisons the pass permanently, so an out-of-order `d` cannot be completed by a
later img-final. Everything else is non-terminal: a lone `W`, K+img-final, a different pass, a different key, the
wrong stage, the old wrong prefix. The log is read incrementally by offset, so a record split across two polls is
reassembled; a shrinking log resets the offset instead of keeping a stale one. Kept from `supervise2.py`: one monotonic
clock, bounded sampling with an error (never a default) on any deviation, signal intent only, and a finally path that
always reclaims the child.

`supervise3.py` adds the pre-launch gate: with `--gate-secs 10 --gate-mib 3072` it samples the real pagesize and
free+inactive+speculative at >=1 Hz for 10 s before launching; any sample below the bar is reported as **not launched**
(exit 3) and nothing starts, with no waiting, retry, app closing or purge.

Tests (`tests/t4.py`, synthetic child, 16 cases, all pass): triple; `_b` suffix; half-lines split across polls; W then
triple; poison-then-good; and the negative cases lone W, K+img-final, different pass, different key, `d` first,
img-final first, old wrong prefix, lone K; gate impossible (not launched, no boot.log) and gate pass (launch, gate.csv
written). The fault-path suites were re-run against the new supervisor (`t2_s3.py`, `t3_s3.py`: try/finally, exemption
by content, dump limits, sampling failures, signals, refusal of leftover test switches): `fails: none`.

## 2. Pre-launch verification (read-only)

| item | value |
|---|---|
| HEAD | `5c5120f` (tracked tree clean; `XC3-SETUP.md` untracked and untouched) |
| host | `linkcheck/dmhost-imgfinal`, sha256 prefix `ffb82aca2b2770ee`, embeds chain `9f73847b56ec` and the img-final format line |
| library | `imgbase120-correct645`, chain `9f73847b56ec`, map 645 rows / 645 keys / 90 pairs / **0 validation problems**, 645 `_b` metallib+json, 72 `_bf`, `DM_MSL_DIR=<candidate>/out` |
| c1 | `c1_full.tsv` is header-only: **0** shaders proven bounded (recorded state, unchanged) |
| facts | `shader_facts.tsv` remains DEFAULT-ONLY (diagnostic build) |
| exemptions | the two audited geometry records only, matched by ctl/code length and sha |

## 3. Gate and the single run

The gate first refused (2628 MiB) because the machine was at that level; the owner closed the browser, and after that
10/10 samples were 3418–3438 MiB. The run's own gate then sampled min **3539 MiB** and launched.

The first refusal (2628 MiB, before the browser was closed) exists only as printed output: at that point the
supervisor did not write a record on the gate path. It now writes `timing.txt` with `kind=gate` on any refusal and the
tests assert it; the run reported here used the earlier build, whose only difference is that record.

Run `imgdiag-run3/run-triple-20261021-182341`: host as above, `DM_NVN_KEYDUMP=4bae5b8abd3bec7f:1`, `DM_NVN_IMGBIND`
unset, six input steps unchanged, 180 s cap, 1 GiB in-run stop unchanged.

[Fenced excerpt omitted from the shareable research record.]

The supervisor stopped on the first non-exempt complete dump, as designed. The four non-exempt dumps are **all geometry
shaders** (`ef6ec0914d348ad3`, `4c0a9c8e53f088cb`, `eafdbb5a5af2a6dd`, `7a7eb30dfb6187b5`; stage from the code area),
none of them in the 645-key vs/ps map. The same four were also dumped by the previous observation run, but after its
snapshot stop, so they were never audited or exempted.

## 4. The finding: the target draw is reached and rejected

The target acceptance never fired because no record was ever emitted:

[Fenced excerpt omitted from the shareable research record.]

The reason is at `boot.log:601`, just after the frame-4500 statistics:

[Fenced excerpt omitted from the shareable research record.]

`e4e34184aa4759c5` / `4bae5b8abd3bec7f` are exactly the two program keys the earlier image snapshot reported for the
target draw, so this is the target draw's own pipeline. Nine more pipelines in the same region fail identically
(10 in total in this run; the previous run had 2, for a different pair and an `R8Uint` attachment). Without a pipeline
the draw is dropped before argument encoding, which is why no K, img-final or d record exists for it.

The emitted MSL for the target declares two colour outputs, both float4, and fills them with `as_type<float>` bit
casts:

[Fenced excerpt omitted from the shareable research record.]

So the shader writes integer bit patterns through float outputs. The host bound an `RG32Uint` attachment (NVN `0x16`,
which the format table maps to RG32Float / RG32Uint / RG32Sint by kind), and Metal requires the output type to match
the attachment's class. Two explanations remain open and need offline analysis, which this round forbade:

1. the NVN colour target is a float format and the host's kind selection for `0x16` picked the unsigned variant; or
2. the target really is integer and the translator should have emitted `uint4` outputs instead of float4 + bit casts.

Either way this is the integer-target incompatibility class, distinct from the earlier blend fix (`640cc3f`) and now
the first blocker on the path.

## 5. What changed relative to the previous observation run

| | `rebuilt-correct-645` (run-20261021-171600) | `imgbase120-correct645` (this run) |
|---|---|---|
| target reflection | **failed**: `B binding fp_i_cb2_48_r32ui has no resolved slot number` | **resolved**: img reg 0, arg_id 2, `texture2d<uint>` |
| target shader load | failed to load | loads |
| target pipeline | never created | rejected: float4 vs RG32Uint |
| reflection failures | 57 | 48 |
| pipeline output-type failures | 2 | 10 |
| img-final record | none (run stopped at the imgdiag snapshot, pre-draw) | none (pipeline rejected) |

The candidate build moved the blocker one step later: the image binding now resolves, and the failure is now the
colour-output type of the same draw. It also exposes how much of the same pass is affected, which the pre-draw
snapshot could not show.

## 6. What this run does and does not establish

- It **does** establish that the target draw is reached without `DM_NVN_IMGBIND`, that its pipeline is rejected for a
  concrete, reproducible reason, and that the image binding's reflection now resolves with reg 0 / arg_id 2.
- It does **not** observe `actual=real`/`dummy`, `usage_blocked`, a final `rid`, or the image register. The img-final
  line never printed in a real run; only its synthetic tests exist.
- `IMG_BASE = 0x120` remains a **candidate**. A pipeline rejection is not evidence about base or stride, and nothing
  here measures the value at `c[2]+0x120`. The stride-8 premise is unchanged and still a premise.
- No GPU-side evidence exists for any image read or write, and this run adds none.
- One authorised run was used; there was no rerun, no threshold change, and no forced draw.

## 7. Next offline step (not done in this round)

Settle the colour-target kind question for `0x16` and for the shaders that write integer bits through float outputs,
then decide which side changes (host format kind selection or translator output type). Only after that can a run
observe the img-final record; the four missing geometry shaders are a separate, pre-existing gap in a vs/ps-only map.

Artifacts: `imgdiag-run3/run-triple-20261021-182341/` (boot.log, timing.txt, samples.csv, exemptions.txt, shdump),
`imgdiag-run3/supervise3.py`, `imgdiag-run3/tests/{t4.py,fakehost.py,t2_s3.py,t3_s3.py}`, `imgdiag-run3/gate-check.sh`.
