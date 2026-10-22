# Round 8: storage span vs logical length separated; the old magic claim reproduced and its cause found

**No repository change. HEAD stays fe5bccc.** Diagnosis only, as instructed.

## 1. The two quantities, kept apart
Implemented exactly as specified in `/path/to/external-drive/xc3/proto/diag/separate.py`:

[Fenced excerpt omitted from the shareable research record.]
Cursors advance by the descriptor only (`+= fx`, `+= fu`); `n` never moves anything. Reading `+0x704` from a record the structure already located is not length matching.

Pinned check: `xc3_lib 0.21.0 src/spch.rs` `UnkItem` seeks to `base_offset + 1776` (0x6f0), reads four u32, then `constant_buffer_offset` lands at **+0x700**, followed by three more u32. `dmsh_build.py:249` reads `(+0x700, +0x704)` as (c1 offset, instruction-area length). Same as the pinned source. I did not modify either.

## 2. My Round 7 claim was wrong, and here is why
I wrote that slicing with `+0x704` "produces extra magic errors". It cannot, and on a fixed start it did not: for `shd_layout`, **stored-span head ≠ code magic on 180 entries and logical(n) head ≠ code magic on the same 180**. Identical sets, so the failures come from `entry_start` itself, not from `n`.

The extra failures came from my old inline script advancing the storage cursor by `Σn`. First divergence there: `slct0 prog1 entry0`, `vx = 0`, but the `Σn` cursor had reached **1024** (the previous program's declared lengths). That is exactly the error you described: using the logical length to move the storage cursor. Corrected expression is the one in §1, and with it **prefix breaks = 0 and control-magic failures = 0** across all 3,704 entries.

## 3. All 3,704 entries classified
| class | count |
|---|---|
| `n == fx` | 2,260 |
| `0 < n < fx` | 1,190 |
| `n > fx` | 254 |
| `n` below SPH header | 0 |
| `n == 0` | 0 |
| no control record / too short | 0 |

By real stage of the stored span: vs 1,910, ps 1,121, cs 12, gs 6, and **401 entries whose stored span does not begin with a code magic** (132 at `n==fx`, 269 at `n<fx`). `fx − n` for the trimmed case: 256 ×694, 512 ×270, 768 ×61, 1536 ×47, 2048 ×40, 1280 ×16, 2304 ×12, 1024 ×10.

## 4. check() on the logical code
Of the 3,450 entries with `n <= fx`, **3,049 pass `check(ctl, logical_code)`** with the stage bits agreeing independently; 401 fail, all of them the `code_magic` entries above (same 401, no new failure mode). No failure is a `+0x704` mismatch or a short header.

**c1 is never lost:** of these 3,450, 2,872 have `c1 == n` (no constant segment) and **578 have `0 < c1 < n`, every one inside `logical_code`, with `+0x704 == n`**. c1 never falls outside the trimmed code.

First successful trim, `shd_ocean slct1 prog1 entry0`: `vx=0 fx=2816 n=2560`, remainder 256, `+0x700 = 2560`, `+0x704 = 2560`, stage vs (bits 1), check passes. The remainder begins `78 56 34 12`, i.e. it is itself a code object.

Named case `shd_layout slct0 prog1`: entry0 `fx=768 n=768` (no remainder, vs); entry1 `fx=512 n=256`, remainder 256, `+0x700 = 256`, `+0x704 = 256`, logical code is ps (bits 5), remainder begins `78 56 34 12`. So the descriptor gives 2 entries while the window holds **3 code objects**; the third has no entry of its own.

Remainder classification for the 1,190 trimmed entries: **942 begin with a code magic**, **248 are something else**. Per entry, storage span and logical code are hashed separately and the remainder is hashed with its size, so nothing is discarded.

## 5. Byte reconstruction against the Rust reference
Per program I concatenated the descriptor storage spans (all `fx`, not the trimmed code) and compared them with the pinned reader's `vertex_binary ++ fragment_binary`:

| file | programs | identical | different |
|---|---|---|---|
| shd_ocean | 13 | 13 | 0 |
| cloud | 79 | 79 | 0 |
| shd_layout | 460 | 460 | 0 |
| shd_lgt | 325 | 325 | 0 |
| shd_post | 1005 | 1005 | 0 |

**1,882 / 1,882 byte-identical.** The storage coordinate system is right; no data is lost by trimming because the remainder is retained and hashed.

## 6. What the separation does not settle
One thing blocks implementation: the **program storage base**. Every program's first entry has `vx == 0`, so `vx` is relative to a per-program base, but the base is not the sum of previous programs' spans. In `shd_ocean slct1`, accumulating spans puts program 1 at `0x1a00`, where the bytes are `f0 07 20 ee` (SASS, not a code header), and every program after the first fails the same way. The per-program windows also sum exactly to the Slct's `xv4_total_size` (`0xdf00` for that Slct), so the spans are consistent with the Slct while the base is not.

That is a structural failure the separation cannot explain, so per your rule I stop here, do not implement, and do not guess further. The minimal next item is one read-only observation of the game's own program-base computation for a multi-program Slct — not a loader-reverse-engineering project, and not something I will start without your word.

## Status
Storage reconstruction: **correct and complete**. Logical code with trim: **3,049 of 3,450 pass check**, c1 preserved everywhere. Remaining unknown: (a) the per-program storage base, (b) 248 trimmed remainders that are not code magic, (c) the 401 entries whose start is not a code object. No pipeline pairing, no translation, no profile, no host, no game.

Artifacts: `/path/to/external-drive/xc3/proto/diag/separate.py`, `recur.py`; samples in `/path/to/external-drive/xc3/proto/out/`. `XC3-SETUP.md` untracked. No push, no PR, no tool install, no new extraction.
