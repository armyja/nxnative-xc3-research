# Report 77 — real fallthrough mutation, strengthened wrapper test (tests only)

Tests and reports only; production code unchanged since `c9a2dc0`, so the experiment host is unchanged. No guest, no host
or shader build, no profile/base/facts/library change. **Budget: this round again ran past the 20-minute window** (the
wrapper rewrite took longer); I stopped here and list what is not covered instead of extending. Final HEAD
`ddd7d0a6c29708e6993cf7af382a83a3a8ecf8f5`.

## 1. P1: the mutation really moves the case now

- The generator takes the single `OP_BIND_SSBO` case line and inserts it between the group labels (after the
  `OP_BIND_STATE` label line, before the shared `state_op(h.op, a); break;` body), removing only its original position.
- Structural assertion before running: the label multiset is unchanged and `OP_BIND_SSBO` appears exactly once in both
  builds; only its label position may differ (normal position 3 → mutated position 9).
- `compile_rc` and `run_rc` are reported separately: normal **compile_rc 0, run_rc 0**; mutated **compile_rc 0,
  run_rc 1**. A compile failure would be rejected, not counted as detection.
- The mutated run fails through routing assertions on upstream labels, not through a missing case:
  `FAIL OP_SCISSOR: no observation event`, `FAIL OP_BIND_PROGRAM`, `FAIL OP_BIND_STATE`, `FAIL OP_BIND_VATTR`, …
  The generator asserts that at least one of `OP_SCISSOR` / `OP_BIND_PROGRAM` / `OP_BIND_STATE` appears among the
  failures.
- Evidence saved: `experiments/wiring2/mutated_wiring.c` and `mutated_stdout.txt` (the failing run's stdout).

This supersedes the mutation claim in report76, which only removed the case; an erratum has been appended there.

## 2. P2: wrapper test coverage made real

- The stubbed `prog_key_cached` now counts queries (`cache_q`), and the off/closed cases use a non-nil, matchable
  program so a query would have happened if the code allowed it.
- Off: assert no log, `cache_q == 0`, and a byte-for-byte `memcmp` of the whole diagnostic state before/after calling
  `ssbo_obs_draw`, `ssbo_obs_draw_skipped` and `ssbo_obs_bind`.
- Closed (mode 2): same whole-state comparison and zero queries for all three entry points.
- Invalid value: exactly **one** log and closed, and a second arm does not log again.
- Skip: 513 calls of the skip hook produce **one** skip log, an **exact** count of 513 and the mode stays armed; the
  following real draw completes the record. An unknown identity on the skip path increments no skip count and logs the
  identity-unavailable line instead.
- Saturation: `skips`, `unknown` and `invalid` are set to `UINT64_MAX - 1` and exercised twice; each stays at
  `UINT64_MAX` (no wrap). The earlier "saturates past 512" wording was wrong and is replaced by this test.
- Format failures are asserted locally per case: for key-list, header and first-slot injection (`fail_at = 0/1/2`),
  each case resets the log counters and asserts **one** `diagnostic-error` log, **zero** `done` logs, mode closed and
  `done == 0`. The generator also asserts the whole stdout contains `diagnostic-error` and a normal `done` elsewhere.
- Worst case: `addr`, `size` and `frame` are all `UINT64_MAX` and the record still completes with no error.
- One-shot: after the record, further `draw`/`skip`/`bind` calls add no log and change no counter.

Results: unit test **25 ok** (ASan/UBSan); wrapper test **21 ok**, rc 0 (ASan/UBSan); wiring normal **43 ok** lines
across the label matrix, rc 0.

## 3. Not covered (explicit gaps)

- The optional extra wrapper cases were not added: legal 6 entries with the target at index 5, nil `S.bst[0]`, zero
  `nstage`, and a fully-known cache with no hit. They are straightforward but were cut when the time budget ran out.
- The worst-case header was only exercised with one entry; a 6-key header with large `frame/obs_seq/pass_counter` is
  not tested, so the "worst-case record" claim is limited to the slot line and the single-entry header.
- The wiring harness still stubs `state_op`/`draw`/imgdiag and covers routing/order only; it does not exercise the
  diagnostic's off/on behaviour (that is the wrapper test's job).
- No production change, so the host remains `linkcheck/dmhost-ssboobs2`, sha256
  `6ff573ee74423cb3d22ece9f45785063685eb7b157103f781b4813d576dc5c7b`, and was not relinked.
- No guest run; no base conclusion.

## Erratum (format-failure coverage)

The wrapper prelude includes `nvn_ssboobs.h` **before** the `snprintf` macro is defined, so `ssbo_obs_fmt_slot` inside the
header is not injected; and in the n=1 path the snprintf order is: the single key token, the key list, the header, then
the slots. `fail_at = 0/1/2` therefore fails at the key token / key list / header respectively — the **slot** failure path
is not exercised by those three cases. What is actually covered: key-list overflow and header overflow, each asserted
locally (one `diagnostic-error`, no `done`, closed). The slot path was reviewed statically only. No production defect was
found; no host rebuild is needed.
