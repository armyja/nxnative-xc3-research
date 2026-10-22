# Round 7: the prefix model tested on 1,882 programs — partial, not sufficient to implement

No repository change this round. HEAD stays **fe5bccc**.

## 1. The recurrence itself holds

Per program, `code_prefix = ctl_prefix = 0` and for each entry in order: `vx == code_prefix`, `vu == ctl_prefix`, then `code_prefix += fx`, `ctl_prefix += fu`; finally the prefixes must equal the last entry's `vx+fx` and `vu+fu`.

| file | programs | entries=1 | =2 | =3 | prefix holds | final total holds |
|---|---|---|---|---|---|---|
| shd_ocean | 13 | 0 | 13 | 0 | 13 | 13 |
| cloud | 79 | 1 | 78 | 0 | 79 | 79 |
| shd_layout | 460 | 0 | 460 | 0 | 460 | 460 |
| shd_lgt | 325 | 4 | 319 | 2 | 325 | 325 |
| shd_post | 1005 | 60 | 942 | 3 | 1005 | 1005 |
| **total** | **1,882** | 65 | 1,812 | 5 | **1,882** | **1,882** |

So the entries are a prefix chain, exactly as your model says, and the last entry's sizes are the accumulated totals — the last entry's `vx` is genuinely a prefix, not a single stage's size. That part is confirmed.

**One correction to your model as stated:** the final prefix equals the *last entry's* `vx+fx` / `vu+fu`, not the Slct's `xv4_total_size` / `unk_item_total_size`, which are the sums over all programs of the Slct. Checking against the Slct window fails for 1,830 of 1,882 programs. I removed that check before the table above.

## 2. The three-entry programs: a real geometry stage

| | entry 0 | entry 1 | entry 2 |
|---|---|---|---|
| **shd_lgt slct3 prog0** | span `(0, 768, 0, 2176)` → xv4 `0x4b000`+768, bits **1 = vs**, ctl at `0x1ba00`+2176, `+0x704` = 768 | span `(768, 256, 2176, 2176)` → xv4 `0x4b300`+256, bits **4 = gs**, ctl at `0x1c280`+2176, `+0x704` = 256 | span `(1024, 1280, 4352, 2176)` → xv4 `0x4b400`+1280, bits **5 = ps**, ctl at `0x1cb00`+2176, `+0x704` = 1280 |
| **shd_post slct83 prog0** | `(0, 256, 0, 2176)` → `0x9c200`+256, bits **1 = vs**, `+0x704` = 256 | `(256, 1280, 2176, 2176)` → `0x9c300`+1280, bits **4 = gs**, `+0x704` = 1280 | `(1536, 2560, 4352, 2176)` → `0x9c800`+2560, bits **5 = ps**, `+0x704` = 2560 |

For these two programs the model works completely: three leaves, VS / GS / PS, each with its own control record, and every `+0x704` equals that span's `fx`. **The 5 three-entry programs contain a genuine geometry stage**, not a variant and not an alias. That answers the question your summary raised.

## 3. Where the model breaks

The same strict check (`+0x704 == fx`, code magic, control magic) on every entry of every program:

| file | programs fully passing | `+0x704 != fx` | other failures |
|---|---|---|---|
| shd_ocean | 6 of 13 | 7 | none |
| cloud | 27 of 79 | 52 | none |
| shd_layout | 89 of 460 | 371 | none |
| shd_lgt | 56 of 325 | 269 | none |
| shd_post | 661 of 1005 | 344 | none |

There is exactly one failure mode, and it is not a prefix break — the prefix chain always holds. It is that `ctl +0x704` names a length **short of** the entry's `fx`.

Worked case, `shd_layout slct0 prog1`: entries `(0, 768, 0, 2176)` and `(768, 512, 2176, 2176)`. The `+0x704` values are **768 and 256**, so the declared code lengths sum to 1,024, while `sum(fx)` and the last entry's `vx+fx` are both **1,280**. The 512-byte span of entry 1 contains a second graphics code header at +256 (`78 56 34 12` at both offsets). So that window holds **three** code areas but only **two** entries.

Reading `+0x704` as the leaf length instead of `fx` does not rescue it either: that variant fails on 232–371 programs per file with additional code-magic errors, i.e. the shorter slice no longer starts at a header.

## 4. Conclusion

The prefix recurrence is confirmed and the three-entry case is fully explained (VS/GS/PS). But **the descriptor does not determine every leaf's code boundary**: in roughly 30–60% of programs the entry's `fx` spans more than one code area, and `+0x704` is not consistently either the span or the true length.

Under your rule — "if the recurrence does not hold or an unknown layout appears, refuse explicitly, no fallback" — this is *partially* satisfied, so I did **not** implement the model and did **not** change the rejection rule. All five containers still stop at `slct0 program0`.

## 5. Correction to the previous round's statistics

Round 6 said "sum-to-last: 0/1822". That number was produced by comparing `Σ(previous entries' vx)` and `Σ(previous entries' vu)` against the last entry's `vx` and `vu` — the expression was `sum(x[0] for x in es[:-1]) == last[0] and sum(x[2] for x in es[:-1]) == last[2]`, evaluated per program but counted per program, giving 0. Your ocean example shows the intended relation was `previous entry's fx == next entry's vx`, which holds by construction now. The 0/1822 figure tested something else and should be discarded. What actually holds is the prefix chain in the table above: **1,882/1,882**.

The 551/1,845 figures from Round 5 remain wrong for the reasons given last round: 1,822 leading entries, of which 1,817 fragment-only and 1,812 of those have `(fx, fu) == (last.vx, last.vu)`.

## 6. What would disambiguate, if you want it

Since the entries are a genuine prefix chain but do not resolve code boundaries, the smallest next step is a **static consumer** rather than more slicing: find in the game's `main` the code that walks `nvsd_shaders` (or the Slct's program records) and see whether it uses `fx` as the code length or consults the control record's `+0x704`. That is also the point where a real answer for the `+0x704 != fx` programs exists — there may be a second descriptor field I have not located, and guessing at it further would be exactly the unbounded search you ruled out.

## Artifacts
Diagnosis code: `/path/to/external-drive/xc3/proto/diag/recur.py`, `leaves.py`. Per-leaf tables in this report. Samples in `/path/to/external-drive/xc3/proto/out/`. `XC3-SETUP.md` untracked. No push, no PR, no AGENTS/host/nx_extract change, no new extraction, no tool install, no translation/build/game run.
