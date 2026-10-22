# Report 76 — DM_NVN_SSBO_OBS P1 fixes, extracted wrapper test, rewritten wiring test, new host

Offline only: no guest, no shader build, no profile/base/facts/library change. Local commit by armyja, no amend, no
push/PR. **Budget: this round ran ~48 minutes, well past the 30-minute window**, because the wiring generator needed
several extraction fixes; nothing was relaxed or skipped to fit. Final HEAD `c9a2dc0a328a3dcb09476c2a63f495fca96d304d`.

## 1. P1 fixes

- **Inert when off/invalid/closed.** The draw branches no longer touch `g_so` before the armed check: `OP_DRAW` /
  `OP_DRAW_IDX` call `ssbo_obs_draw_skipped()` (render-condition skip) or `ssbo_obs_draw()`; both return immediately
  unless `mode == 1`, so no key query, no counter change, no slot copy.
- **Skip is no longer "any conditional skip".** `ssbo_obs_draw_skipped()` runs the same lookup-only identity test as
  the draw: a confirmed target increments the skip counter, logs once, and **stays armed** so a later real draw can
  still produce the record; an unknown identity is reported as identity-unavailable (once), never as a skipped target;
  no match or no vertex binding is silent.
- **One-shot reporting.** `rep_skip`, `rep_unknown`, `rep_invalid`, `done` are explicit flags; `skips`, `unknown`,
  `invalid` are 64-bit saturating counters and are never used as "already reported" gates, so the former 8-bit wrap that
  could repeat the log after 256 events is gone.
- **Format failures are explicit and terminal.** The key-list, header and slot formatters each check their result; any
  failure logs `diagnostic-error … closed without a done line` and closes, independent of earlier invalid/unknown
  reports. The key-list overflow path no longer falls through to a normal header/done. `done` is printed only after the
  header and all 16 slot lines fit.
- `nvn_ssboobs.h` includes `<stdio.h>` itself and uses the real capacity `SSBO_OBS_STAGES` (6) as the key bound.

## 2. Tests actually run

| test | result |
|---|---|
| `t_ssboobs.c` (pure helpers, ASan/UBSan) | **25 ok**, fails none |
| `gen_ssboobs_wrapper.py` (extracts the production block verbatim, stubs `prog_t`/`S`/key cache/`MLOG`/counters; ASan/UBSan) | **16 ok**, rc 0; the generator additionally asserts `diagnostic-error` and `done` appear in stdout as appropriate |
| `gen_switch_wiring.py` (extracts the complete `DRAW`/`DRAW_IDX`/`IMG`/`SSBO` + grouped `SCISSOR…COPY_STRIDE` block, compiles and **runs** it, propagates the exit code) | **25 ok**, rc 0 |

Wrapper coverage: absent/invalid latch once; off and closed are inert (no log, no counter, no query); unknown past 512
events still one line with a saturating counter; invalid nstage past 512 likewise; target skip counted/logged once and
still armed, with a later real draw completing the record; hit while another entry is unknown; partial cache without a
hit is identity-unknown; one-shot then silent; invalid report followed by a format failure closes with
`diagnostic-error` and no `done`; worst-case 64-bit slot line completes. Bind tests: vertex binds recorded with frame and
sequence; another stage and index 16 do not touch the vertex table.

Wiring coverage: every label in the real block (`SCISSOR`, `BIND_PROGRAM`, `BIND_STATE`, `BIND_VATTR`, `BIND_VSTREAM`,
`BIND_VBUF`, `BIND_UBO`, `BIND_TEX`, `BIND_SAMP`, `STENCIL`, `POLY_OFFSET`, `VIEWPORTS`, `DEPTH_RANGE`, `DEPTH_CLAMP`,
`BLEND_COLOR`, `COPY_STRIDE`) reaches `state_op` exactly once with its own opcode and triggers no observation;
`OP_BIND_SSBO` triggers only the SSBO bind; `OP_BIND_IMG` keeps the imgdiag bind; `OP_DRAW`/`OP_DRAW_IDX` call the
snapshot once and strictly before `draw`; the render-condition skip path calls the skip hook and not `draw`.
**Mutation check**: moving the independent `OP_BIND_SSBO` case into the middle of the group makes the generated harness
fail (rc 1), so the test detects a fallthrough instead of only looking right statically.

Static check of the production file: the only `ssbo_obs_*` calls are inside the diagnostic block and the three switch
lines (`DRAW`, `DRAW_IDX`, `SSBO`); the `state_op` and lookahead-scan region contains none.

Limits, stated: the wrapper harness stubs the program/state/keys/`MLOG` environment, so it tests the extracted wrapper,
not the renderer; the wiring harness stubs `state_op`/`draw`/imgdiag and covers routing and order only — its "off"
behaviour is not exercised there (inertness is covered by the wrapper harness); neither harness touches `draw()`,
encoders or the GPU; the host was compiled without sanitizers (ASan/UBSan apply to the unit and wrapper builds).

## 3. Experiment host

`linkcheck/dmhost-ssboobs2`, full sha256
`6ff573ee74423cb3d22ece9f45785063685eb7b157103f781b4813d576dc5c7b`, chain `012cc15f1405` embedded once, rc 0 with
0 errors. Built with the unchanged `fout-uint-correct645` profile (vertex SSBO base still 0, img base 0x120, img slots
1, tex slots 16), headers generated into the experiment directory; compile line and build log saved. The previous
`dmhost-ssboobs` and all other hosts were kept; nothing was overwritten.

## 4. Not covered / open

- No guest run, so the diagnostic has still never produced a live record.
- No base conclusion: the real vertex storage-buffer base remains unmeasured; the synthesised c0 is not evidence.
- The wiring harness does not exercise the off/on distinction (by design); the skip identity is tested in the wrapper
  harness, not in the real switch.
- `pass_counter` remains explicitly unassociated with the final render pass.

## Erratum (mutation test)

The mutation described in section 2 was not a fallthrough test: it removed the independent `OP_BIND_SSBO` case without
moving it into the group, so the mutated failure only proved that a missing case is detected. Report77 replaces it with
a real move (label multiset unchanged, `OP_BIND_SSBO` moved between group labels, both builds compile, only the run-time
routing assertions fail) and saves the mutated source and failing stdout.
