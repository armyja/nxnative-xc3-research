# Report 85 — vs110 matching host built; preflight-only plan ready (no launch)

Offline only: no guest, no shader rebuild, no GPU smoke, no new diagnostic code, no production change, no commit.
HEAD `ddd7d0a`. Host: `linkcheck/dmhost-vs110`; plan: `/path/to/external-drive/xc3/work/experiments/ssbo-vs110-plan/`.

## 1. Host identity

- Built from `ssbo-vs110-correct645` headers (`gen/010074F013262000/game_profile.h` generated from that profile,
  `profile/dmsh_chain.h` = `26c9ad81719f`), with those include directories placed **before** the repository `gen/`.
- `dmhost-vs110` sha256 `896f1da992ff661e188365230096a344247386249fd0aa4006cefcfc35303d30`; build rc 0, 0 errors;
  compile line and build log saved in `linkcheck/dmhost-vs110.compileline` / `.build.log`.
- Embedded chain `26c9ad81719f` appears once; `012cc15f1405` and `9f73847b56ec` zero times (verified with `strings`).
- Generated macros: SSBO base 0x110 for stage 0, 0 for the others; image base 0x120, image slots 1, tex slots 16;
  game id `010074F013262000`.

## 2. Preflight-only plan

- Copied the reviewed supervisor and launcher into `ssbo-vs110-plan/`; identity constants updated to this host, profile,
  library, c1 and chain. `preflight.py` checks host sha, `vs=0x110 ps=0 cs=0`, image/tex values, chain, production
  map/pairs validation (645/0, 90/0), per-key `_b.metallib`+`_b.json`, c1 header and absolute paths.
- Preflight actual result: `preflight ok`; host sha as above; 645 keys; library dir
  `.../ssbo-vs110-correct645/out/b-26c9ad81719f`; c1 header `# chain b-26c9ad81719f …`; patched-tree hash
  `479855830f40b86b…`; the three patched modules match the reviewed baseline hashes.
- Launcher default mode was executed: it printed the final DM configuration and **started nothing** (no run directory);
  `--launch` is not authorised and was not used.
- Supervisor tests re-run in the new directory: `tests/t_gate.py` 12/12, `tests/t_launch_guard.py` 9/9.

## 3. Boundaries

- The SSBO matcher works on the raw replay-state snapshot; using this library to repeat the same three-slot observation
  would **not** validate the base — it is the same table state, not a new anchor.
- No launch authorisation, no automatic gate attempt, no GPU execution implied. The vs base 0x110 remains an experiment
  hypothesis; PS base stays 0; tex/samp 87/87 remain unresolved; the two PS c0 readers are unchanged.
- The PS partner `7faa92fddfdd06bd` reflection has no sbuf (c1/cbuf1/cbuf0/tex0/samp0); its c1 field is not an
  unresolved reg, so the "26 PS sbufs" count stands unchanged.

## 4. Next acceptance design (report only, not implemented)

- A future run could use the same draw's key pair `9b770cf888d729bd` / `7faa92fddfdd06bd` with the PSO record and the
  K/B/d lines to show the old reflection rejection is crossed.
- The existing sbufp B line's `real` comes from `u->addr`, not from a successful `mtl_gpu_addr`; even `real` there can
  still end as the dummy, so it cannot prove a real GPU buffer was encoded.
- For the actual buffer choice, the minimal future point is immediately after the real `NVN_RB_SBUFP` if/else in
  argument encoding: record the finally stored `slots[aid]` and whether the resolve succeeded, with no new lookup and no
  guest memory read. That would be candidate-behaviour evidence, not NVN slot-mapping or GPU-content proof; it requires
  a separate authorisation and was not implemented.
