# Report 69 — the SSBO `reg=None` model corrected: a list index is not an NVN slot

Offline only. No guest, no build/translate, no code/config/facts change, no commit. HEAD `82f488b` unchanged.
Reports 61 and 63 carry an erratum withdrawing the earlier "sbuf index resolved / only the converter rejects" model.

## 1. The production formula (the model that replaces the old one)

`dmsh_build.reflect` (`dm/gfx/tools/dmsh_build.py:333-357`):

[Fenced excerpt omitted from the shareable research record.]

So `vp_s0` means "the shader's storage-buffer argument number 0", which indexes a **binding-sorted list of the
translator's storage-buffer entries**, not NVN slot 0. The NVN slot comes only from that entry's `cb_slot == 0` and its
`cb_offset` (in words, multiplied by 4), range- and alignment-checked against the stage's storage-buffer base from the
profile (`nvn_ssbo_bases`, `SSBO`). `index` must never be passed to the host as `reg`.

## 2. Corrected schema table (regenerated from `fout-uint-correct645/out/b-012cc15f1405`)

645 shaders, 6061 bindings:

| kind | bindings | required field | missing | shaders with a missing one |
|---|---|---|---|---|
| `tex` | 2270 | `reg` | 87 | 20 |
| `samp_tex` | 2270 | `reg` | 87 | 20 |
| `sbuf` | 45 | `reg` (from `cb_slot`/`cb_offset`/base) | **45** | **27** |
| `img` | 9 | `reg` | 0 (all 0) | 0 |
| `cbuf` | 1117 | `reg` | 0 | 0 |
| `c1` | 314 | none (bank by design) | 0 | 0 |
| `support` | 34 | none | 0 | 0 |
| `drvcb` | 2 | `bank` (not `reg`) | 0 | 0 (2 real c0 readers, listed separately) |

Union of shaders with any unresolved binding: **47**, 219 bindings. `tex`/`samp_tex` are the same 20 keys (bindless
handle decode), `sbuf` is a different set of 27. The two `drvcb` entries carry `bank` and are not counted as unresolved;
their `drv_reads` are the two c0 driver readers that need their own line.

## 3. The first failing vertex shader: evidence chain

- Map row (`shader_map.tsv:480`): `vs_shd_post_s175p0.bin  0  vertex  9b770cf888d729bd  shd_post#175:0:0:vs` — a
  **container program** (`shd_post`, program 175, stage 0), not a `recovered` runtime dump (the map has 384 `recovered`
  rows; this is not one of them).
- Package re-verified: `ctl 2176`, `code 1792`, code-area stage `vs`, recomputed key `9b770cf888d729bd` — matches.
- Built reflection (`out/b-012cc15f1405/9b770cf888d729bd_b.json`): `vp_c3` cbuf reg 0, `vp_c4` cbuf reg 1, and
  `vp_s0` `{"kind":"sbuf","index":0,"reg":null,"rw":false,"arg_id":2}`; `drv_reads {}`.
- The exact failing inputs needed: `res['sbufs']` entry number 0 of the binding-sorted list — its `binding`, `cb_slot`,
  `cb_offset` (word), `flags`. Those values are produced by the translator and **were not retained**: the build's
  temporary work directory was removed, and the CAS stores only the final `<key>_b.{json,metal,metallib}` artifacts
  (verified: `cas/shader/<digest>/mac/` contains exactly those three), not the translator response.
- What can be stated from immutable data: the profile's storage-buffer bases are still the placeholder
  `nvn_ssbo_bases  vs=0  ps=0  cs=0`, and the host macro generated from it resolves stage 0 to `0`. With `base = 0` the
  acceptance test becomes `0 <= off < 0x100` and `off % 16 == 0`. A real storage-buffer address table for a stage lives
  at a non-zero c0 offset (the code comment's "vertex 0x110 / compute 0x310 / pixel 0x510" is Mario's layout and is **not**
  used here as XC3 evidence): any entry whose `cb_offset*4` is at or above `0x100` is rejected by the range predicate no
  matter how correct it is. So the placeholder base is a sufficient cause for a `None` reg in that case, but the actual
  offset for this key is missing, so this round cannot say whether the failure was the range, the alignment, or
  `cb_slot != 0`.

## 4. Independent NVSD metadata

The source label identifies a container program, and `dm/gfx/tools/spch.py` can parse an NVSD's `ShaderProgram` record
(`{offset, length}` → NVSD → `nvsd_shaders`), but the NVSD bytes themselves are not part of this experiment: the package
holds only the BTCD control/code record, and no container file was consulted. So no independent constraint
(`storage_buffers`, handles, visibility) was obtained, and none is claimed. A SPIR-V list index is not an NVN handle
either way.

## 5. Runtime path versus the build-time base (two different numbers)

- Binding: `OP_BIND_SSBO` fills `S.ssbo[stage][index]` for `index < 16` (`nvn_mtl.m:4196`).
- Encoding: for `NVN_RB_SBUFP` the host looks up `S.ssbo[st][b->reg]` (`nvn_mtl.m:5773`), i.e. **`reg` is the NVN slot
  the game bound**; `reg = None` makes the loader reject the shader, which is correct.
- The driver c0 table is filled at `base = DM_GAME_NVN_SSBO_BASE(stage)` (`nvn_mtl.m:3924`), which comes from the
  profile (`vs=0 ps=0 cs=0` here) and is the *address of the storage-buffer table in the driver segment*, not a slot.
  Filling `None` with `0` would silently bind slot 0, which is exactly what must not be done.

## 6. Next minimal falsifiable step (not done, needs authorisation)

One raw translator invocation for this single key, keeping the job JSON and recording the response's `sbufs` entries
(`binding`, `cb_slot`, `cb_offset` word, `flags`), then evaluate the formula by hand:

- if `cb_slot != 0`: the failing input is the entry's c0 source, not the profile base;
- if `cb_slot == 0` and `cb_offset*4` is outside `[0, 0x100)`: the placeholder base is the cause and the fix is a real
  `nvn_ssbo_bases` value (measured, not guessed);
- if the offset is inside the window but misaligned: alignment, a different cause again.

No MSL/compile is needed for that observation, and this round did not run it.

## 7. Untouched

No code, config, profile, base/slots/TEX16/GS/stage/fout/facts/library/translator/lock/HLE/rewriter/memory/scheduler/
language change; no new extraction or install; `AGENTS.md`, `XC3-SETUP.md`, shared `dmhost` untouched; no commit, no push.
