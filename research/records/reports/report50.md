# Round 50: the fourteen-key set builds on a new chain; five pixel stages still need texture slot facts

**HEAD `7be6d27`**, no commit. **No guest run.** Artifacts under `/path/to/external-drive/xc3/work/experiments/boot14/`.

## 1. The missing set, re-derived from the log
From `runs/20261021-103603/boot.log`, matching `shader <key> is not in` and de-duplicating:
**12 unique keys**, exactly the set in review. The log is interleaved across threads (several probe lines merge), but
this pattern is printed by the renderer on one thread and all 12 were recoverable.

## 2. Structural re-extraction (not from the old inventory)
Every key was taken from the current `shd_layout.wishp` through the `spch` parser, with `shader_split.check()` passing
(magic, control length, `+0x704` == code length) and the key recomputed from control+code:

| key | stage | program | entries | ctl | code |
|---|---|---|---|---|---|
| `f84043a8a27dfd92` | vs | slct0 p9 | 0 | 2176 | 768 |
| `d1b3aa20d2427eb7` | ps | slct0 p9 | 1 | 2176 | 512 |
| `140b0e5311a23571` | vs | slct1 p17 | 0 | 2176 | 768 |
| `5e2fd9a7dbcdbd8f` | ps | slct1 p17 | 1 | 2176 | 512 |
| `64bafa824aaf5cce` | vs | slct2 p1 | 0 | 2176 | 1024 |
| `a5a7b9e05c292d67` | ps | slct2 p1 | 1 | 2176 | 1024 |
| `b1237fccad9af2be` | vs | slct2 p9 | 0 | 2176 | 1024 |
| `b91a24420e7d8566` | ps | slct2 p9 | 1 | 2176 | 512 |
| `79faa786e9b4bb1b` | vs | slct2 p25 | 0 | 2176 | 1024 |
| `e175707686e5004b` | ps | slct2 p25 | 1 | 2176 | 1536 |
| `ef7f9b7065c1116c` | vs | slct3 p1 | 0 | 2176 | 1024 |
| `1ae940bcf3d4eae4` | ps | slct3 p1 | 1 | 2176 | 512 |

Manifest with source/slct/program/entry/stage/lengths and ctl+code sha256 prefixes:
`boot14/extracted.json`. The two runtime-observed keys keep their original packages byte-for-byte (`vs_first.bin`,
`ps_first.bin` copied, not rebuilt).

## 3. The fourteen-key build on a new chain
New external profile (`boot14/profile/010074F013262000`) keeps the Mac-only 68 GiB/64 GiB keys, unchanged `app_pool`
and the explicit zero NVN-bases placeholder; `shader_facts.tsv` remains **default-only**. Real chain computation:
[Fenced excerpt omitted from the shareable research record.]
The single "1 reused" is the tool's own cache hitting an identical artifact; nothing was renamed from the old chain.

## 4. Resource list, from `bindings[].kind` and `drv_reads` (machine-generated)
| key | st | bindings | cbuf regs | PS colours | drv_reads |
|---|---|---|---|---|---|
| `58e2e00d24c6f3ea` | vs | cbuf×1 | 0 | – | `{}` |
| `5d36d4144f49ec9a` | ps | – | – | [0] | `{}` |
| `f84043a8a27dfd92` | vs | cbuf×2 | 0,1 | – | `{}` |
| `d1b3aa20d2427eb7` | ps | cbuf×1 | 0 | [0,1] | `{}` |
| `140b0e5311a23571` | vs | cbuf×2 | 0,1 | – | `{}` |
| `5e2fd9a7dbcdbd8f` | ps | cbuf×1, **tex×1, samp_tex×1** | 0 | [0,1] | `{}` |
| `64bafa824aaf5cce` | vs | cbuf×2 | 0,1 | – | `{}` |
| `a5a7b9e05c292d67` | ps | cbuf×1, **c1×1, tex×1, samp_tex×1** | 0 | [0,1] | `{}` |
| `b1237fccad9af2be` | vs | cbuf×2 | 0,1 | – | `{}` |
| `b91a24420e7d8566` | ps | cbuf×1, **tex×1, samp_tex×1** | 0 | [0,1] | `{}` |
| `79faa786e9b4bb1b` | vs | cbuf×2 | 0,1 | – | `{}` |
| `e175707686e5004b` | ps | cbuf×1, **c1×1, tex×1, samp_tex×1** | 0 | [0,1] | `{}` |
| `ef7f9b7065c1116c` | vs | cbuf×2 | 0,1 | – | `{}` |
| `1ae940bcf3d4eae4` | ps | cbuf×1, **tex×1, samp_tex×1** | 0 | [0,1] | `{}` |

Correction to my own first pass: `cbuf` bindings carry `reg`, not `slot`, so a `slot is None` test over-counts; the
build's own criterion ("binding whose slot was not decoded") is the right one and gives **5**.

Every stage is uniform-buffer only in the driver sense: `drv_reads` is empty for all 14, so no driver-segment base is
needed by any of them. But **five pixel stages read a texture through a sampler whose slot is not decoded**
(`fp_t_tcb_8` / `fp_t_tcb_8Smplr`).

## 5. First unresolved resource fact
**`5e2fd9a7dbcdbd8f`** — pixel stage of `shd_layout.wishp` slct1 program17, texture `fp_t_tcb_8` + sampler
`fp_t_tcb_8Smplr`, both with `slot = None`. The other four (`a5a7b9e05c292d67`, `b91a24420e7d8566`,
`e175707686e5004b`, `1ae940bcf3d4eae4`) have the same two undecoded bindings; two of them also use `c1`.

This is the next runtime-facts target: the texture/sampler slot for these pixel stages has to come from the guest's
descriptor writes, not from a base constant. Until then their texture binding is unknown, and an offline build is not a
statement that the resource configuration is correct. PS colours `[0,1]` are reflection, not a measured render target.

## Limits
No guest run, no PSO sweep, no texture translation, no forced facts or borrowed constants, no GS work, no tracked
change, no commit. The `four-key` experiment directory was left untouched.
