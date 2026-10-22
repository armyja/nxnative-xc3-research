# Round 10: the conflict is resolved — a missing base in MY diagnostic script

**Root cause found. All three Round 7/8/9 conclusions are withdrawn.** No repository change; HEAD stays `fe5bccc`.

## A. Sample identity (measured now, not copied)
[Fenced excerpt omitted from the shareable research record.]

## B. slct1 raw fields, Rust and Python agreeing field by field
[Fenced excerpt omitted from the shareable research record.]
Python read the same bytes and asserted the same values; the two readers agree on every field. **Correction to Round 9:** the table there wrote "descriptor prefix span 0x1a00 (vx 0x0 + fx 0x1a00)". That was a mislabel — `0x1a00` is the *sum* `last.vx+last.fx` of the **last** entry, whose raw quadruple is `(vx=2560, fx=4096, vu=2176, fu=2176)`. I put a computed total into a column headed by raw descriptor fields. That was wrong and is why program 1 looked inconsistent.

## C. The formula, and the two programs resolved
[Fenced excerpt omitted from the shareable research record.]
For all 8 programs of slct1 the sums are exactly the Slct's totals: Σ code = 57088 = `xv4_total`, Σ ctl = 34816 = `unk_item_total`.

| | program 0 | program 1 |
|---|---|---|
| program base (code) | 0 | 6656 (0x1a00) |
| program base (ctl) | 0 | 4352 (0x1100) |
| entry0 code abs | 70400 (0x11300) head16 `78563412000000000000000000000000`, magic ok | 77056 (0x12d00) head16 `78563412000000000000000000000000`, magic ok |
| entry0 ctl abs | 13728 (0x35a0) `34127698`, +0x700=2560, +0x704=2560, `decl==fx` | 18080 (0x46a0) `34127698`, +0x700=2816, +0x704=2816, `decl==fx` |
| entry1 code abs | 72960 (0x11d00) `78563412…`, magic ok | 79872 (0x13800) `78563412…`, magic ok |
| entry1 ctl abs | 15904 (0x3e20) `34127698`, +0x700=3840, +0x704=4096, `decl==fx` | 20256 (0x4f20) `34127698`, +0x700=4096, +0x704=4352, `decl==fx` |

**ALL_OK=True for all 8 programs of slct1.** Rust's helper agrees: program0 `vs.len=2560 vs[0..16]=7856341200000000 fs.len=4096`, program1 `vs.len=2816 fs.len=4352`, all four starting `78563412`.

## D. The exact divergence
`spch.py` (Round 4) carried a cursor and advanced it:
[Fenced excerpt omitted from the shareable research record.]
`separate.py` (Rounds 8–9) dropped the program accumulation:
[Fenced excerpt omitted from the shareable research record.]
For program 1 entry 0 that yields code at `69632+768+0 = 70400` (program **0**'s code) instead of `77056`, and the CTL at `9376+4352+0 = 13728` (program **0**'s control) instead of `18080`. Reading program 0's control record is why "control magic failures = 0" in Round 8 and why the code at the wrong address began with SASS bytes. **Same input, same bytes; the two scripts differ only in that one expression.**

With the corrected formula, applied once across all five files as a sanity check (not a substitute for the two programs above):
[Fenced excerpt omitted from the shareable research record.]
So the 1,190 "`n < fx`" entries, the 401 "no code magic" entries and the 254 "`n > fx`" entries of Rounds 7–9 **do not exist**; they were all the same off-by-one-program-base error. `decl == fx` holds on all 3,704 entries.

## Withdrawals
1. **"The descriptor does not determine code boundaries"** (Rounds 7, 8, 9) — withdrawn. It did; my script did not use it correctly.
2. **"Control-magic failures are zero"** (Round 8) — withdrawn as evidence, because it was reading program 0's records for every program. The statement is true, but for the wrong reason.
3. **"program 1's CTL is not a magic"** (Round 9) — withdrawn; with the Slct base included it is a valid record.
4. **"Storage reconstruction is correct and complete"** — now actually supported, but only because the formula is right, not because the earlier comparison proved it.
5. **"Magic-search route exhausted, so the parser does not compare magic"** — withdrawn as a conclusion; as you said, four scattered immediates do not exclude a split construction.
6. Round 9's `vx 0x0 + fx 0x1a00` table cell — withdrawn as a mislabel.

## What this means, and what I did not do
The Round 4 prefix model was right; the adapter's refusal since Round 6 (`leading entry not all zero`) is now the only thing preventing coverage, and the prefix model says every entry is a real stage. **I have not changed the adapter, per your instruction.** Coverage remains 0 and HEAD remains `fe5bccc`.

One sentence, as asked: **Rust and Python first diverge in my own diagnostic script, at `pbase = xo + vx` missing the cumulative program base; CTL magic does not fail once that base is included; and the Round 7/8/9 conclusions about indeterminate boundaries, control-magic failures and the 401 unreadable entries are all withdrawn.**

Full script and logs stay under `/path/to/external-drive/xc3/proto/diag`. No commit, no push, no PR, no new extraction, no tool install, no game/build/translation.
