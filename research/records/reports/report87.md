# Report 87 — sbuf-final same-pass acceptance plan and no-guest tests (no launch)

Offline only: no guest, no host/shader rebuild, no production/profile/base/facts/library/translator/lock change, no
commit (plan and tests live on the SSD). HEAD `cac7c6f`. Plan:
`/path/to/external-drive/xc3/work/experiments/ssbo-vs110-final-plan/`.

## 1. Host and identity

- `linkcheck/dmhost-vs110-sbuffinal`, sha256 `70c76712facf3a519fd69e421359d71db4790bfc8a4faacc504a296d0bd04275`,
  built with `ssbo-vs110-correct645` headers first; embedded chain `26c9ad81719f` once, `012cc15f1405` / `9f73847b56ec`
  zero, `sbuf-final` once.
- Profile/library: `vs=0x110 ps=0 cs=0`, image 0x120 slots 1, tex slots 16, chain `26c9ad81719f`, library
  `out/b-26c9ad81719f`, map 645 / 0 problems, pairs 90 / 0 problems, every key has metallib+json, c1 names the same
  chain, the three patched modules match the reviewed baseline.

## 2. Supervisor

- `supervise7.py` reuses the reviewed sample-anchored gate, pre-Popen refusal guard, single clock, bounded sampling,
  finally-child reclaim, whitelist and the two GS exemptions unchanged.
- The only success route is the ordered same-pass triple `K st0 key=9b770cf888d729bd` →
  `[sbuf-final] p<pass> st0 key=9b770…` → `d … vs=9b770… fs=7faa92fddfdd06bd`. `real`/resolved 1 and `dummy`/resolved 0
  are both terminal; a consistent but abnormal record (e.g. real with slot 0) is reported, not waited on.
- Terminal invalid: `resolved`/`actual` contradiction, duplicate/conflicting K/sbuf-final/d, wrong pass/stage/key,
  `sbuf-final` before K, or `d` before `sbuf-final` (the pass is poisoned, not completed later). A first forced draw with
  a different vertex key is `target-not-obtained`; the selection is never widened. The old raw SSBO snapshot and the image
  records have no success route.
- The record is the final value written into the argument slot; it is not GPU execution, access content or NVN-register
  proof.

## 3. Environment, gates and tests

- Only `DM_NVN_KEYDUMP=7faa92fddfdd06bd:1` (PS-matched); IMGBIND/PSOFAIL_RT/SSBO_OBS and all skip/override/test switches
  are excluded by the whitelist; six inputs unchanged; en-GB, audio 0, headless.
- Gates unchanged: launch 2800 MiB over a full 10 s sample span (≥1 Hz, terminal sample), runtime available 1 GiB /
  RSS 2 GiB / dump 32 MiB / log 64 MiB / 180 s including the gate, only the two fixed GS exemptions, no retry.
- `tests/t_sbuf.py` **15/15**: real and dummy triples stop; no-d, K-only, B-only and old raw SSBO records run to the
  deadline; other-pass d, st1 K, duplicate K, d-before-sbuf, resolved/actual contradiction and wrong-PS d are invalid;
  `_bf` and a different VS are `target-not-obtained`; half-lines across polls complete.
- `tests/t_gate.py` 12/12 and `tests/t_launch_guard.py` 9/9 (deadline and parent signal leave no child marker; the
  matcher stops on real/dummy and stays waiting without `d`).
- `run-ssboobs.sh` default mode executed once: preflight ok, final DM configuration printed, **no run directory, no
  child**; `--launch` was not used.

## 4. Boundaries

- No launch authorisation and no automatic gate attempt; nothing was run against a guest. The vs base 0x110 and any
  reg mapping are hypotheses; PS base remains 0, the unresolved PS/tex sets and the two c0 readers are unchanged.

## Erratum and fix round

1. **Launcher entry was wrong**: the copy still exec'd `supervise6.py`, which does not exist in this directory. It now
   execs `supervise7.py` (launcher sha `a0ef2e5c…`, supervisor sha `d7a5f36e…`). `tests/t_launch_path.py` now reads the
   real launcher, asserts the entry file exists and contains `class SbufFinal`, and runs `--launch` against a substitute
   supervisor (the real host is never executed) to check `--host dmhost-vs110-sbuffinal`, `--gate-mib 2800`, `--secs 180`
   and a child env with only the KEYDUMP PS target and no IMGBIND/PSOFAIL_RT/SSBO_OBS. Default mode still starts nothing.
2. **Field/domain validation was missing.** The supervisor's direct-feed counterexample
   (`reg99 aid99 u=2 addr=BAD rawsize=16 size=16 resolved=2 actual=dummy slot=BAD rw=2`) was accepted. The matcher now
   requires resolved/u/rw ∈ {0,1}, actual ∈ {real,dummy} with real iff resolved 1, addr/slot plain uint64, rawsize/size
   uint64 with `size == rawsize` (or 1 when rawsize is 0), rejects resolved 1 with u=0 or addr=0, and treats reg≠0 /
   aid≠2 / rw≠0 as a terminal `unexpected-candidate-record` rather than acceptance. `real` with slot 0 is terminal
   `consistent-but-abnormal`; `rawsize 0`/`size 1` and dummy with a non-zero slot remain legal. A recognisably target
   `[sbuf-final]` line that is malformed is terminal invalid, never silently ignored. A numeric bug found by the tests
   (zero address compared as the string `0x0`) was fixed.
3. New run evidence: `t_fields.py` 17 checks, `t_sbuf.py` 17 cases, `t_gate.py` 12, `t_launch_guard.py` 7,
   `t_launch_path.py` 11 — all rc 0. Default launcher run again: preflight ok, no run directory, no child. The earlier
   counterexample is retained in the report history; no guest was launched at any point.
