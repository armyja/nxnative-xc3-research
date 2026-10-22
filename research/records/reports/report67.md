# Report 67 — full 645 candidate library rebuilt with the one fout row, plus a matching experiment host

Scope: offline only. No guest, no GPU smoke, no full host build of the shared tree, no tracked change (HEAD `82f488b`,
0 tracked modifications). Experiment: `/path/to/external-drive/xc3/work/experiments/fout-uint-correct645/`.

## 1. Facts: precise diff and provenance

The audited candidate's `shader_facts.tsv` was copied byte-for-byte from the two-key experiment; the diff against
`imgbase120-correct645` is exactly the two original comment lines replaced by four comment lines plus one data row:

[Fenced excerpt omitted from the shareable research record.]

sha256 prefix of the table: `5ae41c2d2aa8db426534` in both experiments (the full-645 copy was first written with a
renamed provenance filename in a comment; that changed the chain, so it was restored to the byte-identical table —
comments are hashed by the chain tool). Provenance file `provenance-fout-uint-two-key.md` (copied; it is the filename
the facts comment references) records: run `run-psort-20261021-190120`, `boot.log:571–581`, pass `553275`,
`assoc=same-pass`, identity map, slot0 NVN `0x17`→MTL 103, slot1 NVN `0x0b`→MTL 53, slots 2–7 absent. It is **not** PC
reflection; `pc_missing` stays true and every other query is still answered with the default.

## 2. Inputs verified

- All **645 packages byte-identical** to `imgbase120-correct645` (sha256 compared one by one, 0 differing).
- Map: **645 keys, 0 validation problems** — 284 vertex + 361 pixel, **no gs/hs/ds**.
- Pairs: **90 rows, 0 problems**, provenance 90 rows; unchanged from the audited source, so the 89 structural pairs plus
  the one same-draw pair are preserved and no geometry-shader endpoint pair exists.
- Profile constants unchanged: `nvn_img_base` 0x120, `nvn_img_slots` 1, `nvn_tex_slots` 16, image base still a
  candidate, other constants untouched.

## 3. Chain, header and the one build

- `dmsh_chain.py --check-tools` passes with the existing runtime (`DOTNET_ROOT=/opt/homebrew/opt/dotnet/libexec`, no
  install). Chain computed by the real tool: **`012cc15f1405`**, identical to the two-key experiment because the facts
  table is byte-identical. `--header` wrote that value into the experiment copy's `dmsh_chain.h` only.
- One build, one configuration, explicit all 645 keys, `J=1`, fresh `DMSH_CAS`, no `IOSOUT`, no `PREFILL`:
  `rc=0` in 3m52s. Summary: `shaders 645: ok 645`, `new key 645`, `variant cache: generated 72, hit 1, rebuilt 71,
  compiled 71`, `Metal cache: mac 105 reused, 540 compiled`, `queries without a PC answer 645`.
- Completeness: 645/645 keys have `<key>_b.metallib` and `<key>_b.json` (0 missing); `4bae5b8abd3bec7f_b.metal` etc.
  present; 717 metallibs in total (645 + 72 `_bf` variants, listed separately), 646 json (645 + `_b_build.json`).
- `PCmissing = 645` reads as: no PC reflection for any key; **one** pixel shader has two fragment-output component types
  from the runtime observation; all its other queries and every other key still use translator defaults.

## 4. Real c1 table

`c1_guard.py out/b-012cc15f1405 profile/c1_full.tsv` → `not proven bounded: 0 shaders`, rc=0. The new
`c1_full.tsv` is a real, freshly generated header-only table naming chain `012cc15f1405`. No c1 fingerprint was copied
from an older chain.

## 5. Target artifacts: consistent with the two-key experiment

| file | this build | two-key build |
|---|---|---|
| `4bae5b8abd3bec7f_b.metal` | `41f08a3a3ac7` | `41f08a3a3ac7` |
| `4bae5b8abd3bec7f_b.json` | `1a8c6cddc755` | `1a8c6cddc755` |
| `e4e34184aa4759c5_b.metal` | `fb14dea36661` | `fb14dea36661` |

Reflection stays `img` reg 0 `texture2d<uint>` (arg 2), `cbuf` reg 1, `support`, `drv_reads` empty; the pixel shader's
colour outputs are `uint4`; the other 8 image bindings remain static reg 0 **without** a runtime observation, and the
other 8 pixel shaders keep float outputs — only the target key carries this candidate fact.

## 6. Experiment host

- Generated for this profile: `gen/010074F013262000/game_profile.h` from the experiment `game.tsv` and
  `profile/dmsh_chain.h` (`012cc15f1405`), both under the experiment dir; the shared `dm/host`, `dm/games` profiles and
  the lock were not touched.
- Compile: the base line is the previous experiment host's line with the two experiment include dirs placed **first**
  and only `-o` changed; full command in `linkcheck/dmhost-foutuint.compileline`, log
  `linkcheck/dmhost-foutuint.build.log`, `rc=0`, 0 errors.
- The first attempt placed the include dirs after the repository `gen/`, so the binary embedded the old chain; it was
  discarded and rebuilt with the includes first. The shipped binary contains `012cc15f1405` once and `9f73847b56ec`
  zero times.
- Host: `linkcheck/dmhost-foutuint`, full sha256
  `aa9bbe705d613c1603794ee67eda8bc34e208b90367b9122562f0865a8f031c0`, and the interesting macros come from the real
  generated header (`010074F013262000`, img base `0x120`, img slots 1, tex slots 16).

## 7. Draft for a later guest acceptance (not executed, not authorised)

- Run: experiment host above, profile `fout-uint-correct645` (chain `012cc15f1405`), six unchanged inputs,
  `DM_LANG=en-GB`, headless, `DM_AUDIO=0`, fresh save/temp/shdump/log, `DM_NVN_KEYDUMP=4bae5b8abd3bec7f:1` plus a fresh
  `DM_PSO_RECORD`; **`DM_NVN_PSOFAIL_RT` and `DM_NVN_IMGBIND` unset**.
- Success condition: the ordered same-pass triple `K <pass> st1 key=4bae5b8abd3bec7f` → `[img-final] … p<pass> st1
  key=4bae5b8abd3bec7f …` → `d <pass> … fs=4bae5b8abd3bec7f`, reporting `actual=real` or `dummy` with `usage_blocked`;
  both outcomes end the run. If the triple never appears, report where it stopped (dump, threshold, deadline) and do not
  relax anything.
- Gate: owner's 2800 MiB (same formula, 10 s at ≥1 Hz); in-run stops unchanged; two audited geometry records exempt by
  content only; the four newer GS are still not exempt and not built.

## 8. Not established

No GPU execution, no image read/write, no image correctness; other float-target uses of the target pixel shader are
unknown; the other 8 image bindings have no runtime observation; the 645-library build is an experiment artifact and was
not exercised by a host; c1 shows nothing bounded for this chain. This observation configuration is not written into any
production profile.
