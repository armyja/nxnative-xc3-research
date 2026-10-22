# Round 59 (offline only): a 24-key set builds on a new chain; `shd_post` slct85 stops at the slot boundary

**HEAD `7be6d27`**, no commit, no guest run. Artifacts under `/path/to/external-drive/xc3/work/experiments/boot26/`.

## 1. Delta between the two bursts, and the two chosen programs
[Fenced excerpt omitted from the shareable research record.]
All four are in `shd_post.wishp` and form **two more structural [vs,ps] pairs**: slct36 program1 (`d379…`/`0bcf…`) and
slct138 program0 (`bac0…`/`460b…`). They are not built this round.

The two programs chosen in review, extracted through the current `spch` and `shader_split.check()`:

| program | entry | key | stage | ctl | code | vs Round 58 dump |
|---|---|---|---|---|---|---|
| `shd_post` slct38 p0 | 0 | `109c554fde29c46a` | vs | 2176 | 512 | control and code **byte-identical** |
| `shd_post` slct38 p0 | 1 | `11dcfcea9524c8f2` | ps | 2176 | 256 | byte-identical |
| `shd_post` slct85 p0 | 0 | `ca5aad4653097385` | vs | 2176 | 512 | byte-identical |
| `shd_post` slct85 p0 | 1 | `a7fe954c9b04785e` | ps | 2176 | 1024 | byte-identical |

## 2. The slot boundary (why only one pair was built)
NVSD metadata from the pinned `xc3_lib` for the two programs:
[Fenced excerpt omitted from the shareable research record.]
The validated configuration is `nvn_tex_base 0x20`, `nvn_tex_slots 2`, which covers handles 0–1. **`slct85 p0` needs
handles 0–6, i.e. at least 7 slots** — beyond the validated range, so per instruction I stopped at that boundary
rather than widen the base/slots or borrow constants. `slct38 p0` needs handle 0 only and was built.

## 3. The 24-key build
New external profile (22 packages copied unchanged + the two `slct38` packages, one structural pair added), real chain
computation, **fresh CAS** so nothing is silently reused:
[Fenced excerpt omitted from the shareable research record.]

## 4. Resources of the new pair
| key | stage | bindings | c1 | drv_reads | inputs / outputs |
|---|---|---|---|---|---|
| `109c554fde29c46a` | vs | 1 cbuf `vp_c3` reg 0 | empty | `{}` | 2 × float4 |
| `11dcfcea9524c8f2` | ps | 1 cbuf `fp_c3` reg 0, **1 tex `fp_t_tcb_8` reg 0**, 1 samp_tex reg 0 | empty | `{}` | raster colours **`[]`** |

Both decode with the existing base/slots; no driver segment is read. The pixel stage declares **no colour output**
(`colors: []`), which is a reflection fact worth noting — it suggests a depth/auxiliary pass rather than a colour
write, but that is not established.
The pair is a **structural** pairing from one SPCH program, not evidence of a runtime draw.

## 5. Status of the rest
- `shd_post` slct85's pair (`ca5a…`/`a7fe…`) is packaged-ready but **not built**: it needs `slots ≥ 7`.
- The two extra pairs from the four new keys (slct36 p1, slct138 p0) are identified but not built.
- GS stays refused; the 41 keys not in the five containers are unchanged and not investigated.
- Missing inputs are not the same as "must extract": nothing was extracted this round.

## Limits
No guest run, no input, no tracked edit, no commit, no install, no archive extraction; the 22-key library, chain
`c1ba6be7ba12` and the shared `dmhost` are untouched. New artifacts: `boot26/pkg`, `boot26/profile`, `boot26/cas`,
`boot26/out/b-0518cb756539`.
