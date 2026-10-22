# Resource audit of the corrected 645 build (offline, read-only)

Base: `rebuilt-correct-645` (645 verified packages, chain `34aab9ef1ab1`). Nothing rebuilt, no profile or repo change.
Machine table: `/path/to/external-drive/xc3/work/experiments/resource-audit.tsv` (4,596 rows, one per binding).

## 0. A schema correction first

Counting "undecoded" as `reg is None` over every kind is wrong, and the builder's own summary line does exactly that:
its `SLOTK` set includes `sbuf`, whose emitted schema carries **`index`** (all 45 bindings have one, 0..4) and no
`reg` at all, and `drvcb`, which carries **`bank`** and no `reg` field.

| kind | fields present | undecoded? |
|---|---|---|
| tex, samp_tex, img, cbuf | `arg_id, kind, msl_name, msl_type, reg` | yes when `reg` is absent |
| sbuf | `…, index, reg, rw` | **no**: `index` is the slot (45/45 set) |
| drvcb | `…, bank` (no `reg` key) | **no**: addressed by bank |
| c1, support | `…, bank` / none | by design |

So the build's "56 shaders with a binding whose slot was not decoded" over-counts. By schema it is **29 shaders /
183 bindings**: tex 87, samp_tex 87, img 9. The 56 is not a contradiction of the build's work, it is its counter
treating sbuf/drvcb as slot bindings.

## 1. Textures (87 + 87)

All 87 undecoded texture bindings are named `*_t_tcb_<hex>`, i.e. **combined handles** in the c[2] handle table. The
decode in `dmsh_build.decode_tex` is:

[Fenced excerpt omitted from the shareable research record.]

So the unit of the "26" is the **decoded slot**, not a handle word and not a byte offset: words run **0x28..0x3C**
(bytes 0xA0..0xF0), and with `TEX_BASE = 0x20` they yield slots **16..26**, all exact (no remainder). The rejection for
every one of them is the **upper bound**, not the formula: with `TEX_SLOTS = 16`, `0x20 + 8*16 = 0xA0` and every one of
these words has `o0*4 >= 0xA0`.

| boundary | word | byte | decoded slot | status with slots=16 |
|---|---|---|---|---|
| 15 | 0x20 | 0x80 | 15 | inside (not in this set) |
| 16 | 0x28 | 0xA0 | 16 | **rejected** (first one out) |
| 26 | 0x3C | 0xF0 | 26 | **rejected** (largest seen) |

**Candidate, not applied:** keep `TEX_BASE = 0x20` and raise `TEX_SLOTS` to **27**. Supporting evidence: all 11 distinct
words in this set decode to exact integers under the same formula, the words are contiguous, and the smallest failing
word is exactly the first one outside the current range. Counter-evidence to look for before changing anything: a
program in this set whose handle table is *not* at 0x20 (none seen), or any word above 0x3C (none seen). This is a
candidate about *slots*, not a claim that the textures behind them are correct.

Items with no NVSD: every entry whose source is `runtime_dump#…` / `recovered#…` (no container program, so no NVSD to
align against). The container-sourced ones could be aligned with NVSD per program; that was not done here (budget).

## 2. Images (9)

All nine are the same construct, `fp_i_cb2_48_r32ui`, all pixel stage, all in `shd_lgt` (slct 5 program 1/73/75/77/83/109/119,
slct 7 program 1) except one whose source is a runtime dump (`570940180d9bb760`).

The image branch of `decode_tex` rejects because the profile declares `nvn_img_base = 0` and `nvn_img_slots = 0`, so the
range test `IMG_BASE <= x*4 < IMG_BASE + 8*IMG_SLOTS` can never hold; it is **not** a format problem and not a wrong
handle. What is missing is the title's real image handle table base and size.
Do **not** substitute `TEX_BASE` for it: the texture and image tables are different tables in the driver.

## 3. SSBO (45) and the two driver readers

- The 45 `sbuf` bindings (27 shaders, `vp_s0/s1`, `fp_s0..s4`) are addressed by `index` 0..4 and are not undecoded.
- The 2 `drvcb` bindings are `fp_c0`, `bank = 0`, on **`0104dd056a3b1902`** (shd_lgt 0:17) and **`16653b901bfc4560`**
  (shd_layout 10:2). These are the two the build reports as "reading driver segments at run time (c0 2)"; their
  `drv_reads` are c0. They are the same fact as the build's driver-segment count, not a second problem.

## 4. The three `+0x714 = 2` dumps

All three re-hash to their key, have a valid control (2176 bytes) and a graphics code area whose **SPH stage bits are 4**.
Running the production parser on them:

[Fenced excerpt omitted from the shareable research record.]

So `714 = 2` is **not** a stage name; these are geometry shaders, which the project refuses. `714` is an empirical field
and the code area is authoritative. They stay out of the map.

## 5. Smallest next observation (not executed)

For the image question only: run one `shd_lgt` frame with `DM_NVN_PASSDUMP` and look for a pass whose shader is one of the
nine and whose bindings include an image; the pass record's descriptor (target/format/level) is the runtime fact that
would give the image table an anchor, the way the texture handle words did. Until such a record exists, `IMG_BASE` and
`IMG_SLOTS` remain unknown and nothing should be set by guess.
