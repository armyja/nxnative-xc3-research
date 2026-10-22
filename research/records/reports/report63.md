# Report 63 — psort diagnostic completeness fixes (offline, no run)

Scope: the five diagnostic-completeness fixes only. No guest run, no shader build, no renderer/format/PSO change.
Baseline `dcb7fdf`; local commit `82f488bc2fde4a882357d4ca3f1faaabe17df09a` (author armyja, no amend, no push/PR).
One file, `dm/gfx/nvn/nvn_mtl.m`, +31/−15.

## 1. lmap is now the real map, on its own line

`[psort] map enabled=1 physical->logical=<k.lmap[0..7]>` prints all eight actual values taken from the failing key
(`k.lmap`, copied at `:3445` from `g_pso_lmap`). With no merge it prints
`[psort] map enabled=0 physical->logical=identity (no merge: logical colour index = physical attachment index)`, so a
zero array is never presented as "all slots map to 0". Values are never re-derived from `R`. The header keeps `fsfn=`,
`ms=`, `fzkind=` and now drops the old `lmap=` boolean, which the map line replaces.

## 2. Capture moved to where every fixed field is set

`psort_capture(pd)` used to run before `g_pass.dfmt`/`sfmt`/`samples` were assigned, so those three fields were still
zero in the snapshot. It now runs immediately after `if (dt || stt) g_pass.samples = …` (`:2538`), i.e. after the colour
slots, depth, stencil and sample count are all fixed and while the real `pd` is still in scope. It still copies scalars
only and still runs after `g_pass.serial` is assigned, so the same `assoc=same-pass` test applies unchanged.

## 3. The closed state is latched

`psort_arm` now treats mode 0 as *unparsed* and 2 as *closed*: an absent switch, an invalid value and a finished record
all latch 2, so `getenv` is read once and later `rp_begin_ex_` calls return at the first check. Accepted form is stated
in the log: a complete **lowercase** 16-hex fragment key; an invalid value still logs exactly one line and stays closed.

## 4. Truncation can no longer look like success

Every `snprintf` return is checked. The `cfmt` buffer is 128 bytes, which holds eight `uint32` decimals with commas
(worst case 8×10+7 = 87). If any header, map or slot line does not fit, the record prints
`[psort] diagnostic-error: … this record is incomplete and no done line follows` and **no** `done` line, then disarms.
A reader can therefore treat a missing `done` as an incomplete record, and a present `done` as a complete one.

## 5. cview fields are copied only when a view exists

The capture copies `set_format`/`format`/`set_levels`/`base_level`/`set_layers`/`min_layer` only when
`i < R.rt.n && R.rt.has_cview[i]`. A slot without a view prints
`cview=0 setfmt=- fmt=- setlv=- base=- setly=- minly=- (no view object: override fields not copied, not zero values)`,
so an absent view is never offered as evidence of an override, and its zero-filled struct is not reported as "zero
values".

## 6. Verification actually performed

- **Extracted production fragment test** (`linkcheck/psort_fragment_test.c`): the arm/match functions were cut verbatim
  from `nvn_mtl.m` (no rewriting) into a small TU with a `MLOG` stub and compiled with `clang -O1 -Wall` (0 warnings
  from that fragment). 11/11 checks pass: absent switch latches closed and is not re-parsed open; short key closed;
  uppercase rejected; valid key arms; exact key and `_b` match; `_bf`, a different key and NULL do not; closed after
  done.
- **Real host link**: the diagnostic file compiles into the experiment host with rc=0 and 0 errors; the only warnings in
  the build log are pre-existing ones on unrelated lines. New strings are present in the binary.
- **Static review** covers the parts a fragment test cannot reach: the map line, the truncation checks and the cview
  branch are inside `psort_report`, which needs Metal types; their bounds are arithmetic (128-byte `cfmt`, 512-byte
  lines, checked returns) and were reviewed line by line. They are **not** run-tested, and no claim is made that a
  snapshot was ever printed — that still needs the next authorised run.

## 7. Host

- `linkcheck/dmhost-psort2`, rc=0 / 0 errors, chain `9f73847b56ec`, full sha256
  `1aa43a7c84331f3268f4f4a1803fd5f77fa2c63a16a2adce8c4cb70c047e19f6` (prefix `1aa43a7c84331f32`).
- Compile line `linkcheck/dmhost-psort2.build.log` header is the same source list as before with only `-o` changed; the
  prior hosts `dmhost-imgfinal`, `dmhost-imgdiag`, `dmhost-psort` and the shared `dmhost` were not overwritten.

## 8. Unchanged and still unknown

No format/attachment/PSO/cache/format-kind behaviour changed, no cache cleared, no `fout`/facts added. The table keeps:
slot index of the 103 attachment unknown; NVN original format, view override, slot-1 existence and the original sample
values unknown. The next-run draft in report62 stands, with `DM_NVN_PSOFAIL_RT=4bae5b8abd3bec7f`, and now expects a
`[psort] map` line and a `done` line only for a complete record.

## Erratum (SSBO model)

As in report61: `sbuf` `index` is a list position, not an NVN slot, and `reg=None` means the derivation from
`cb_slot`/`cb_offset`/profile base failed. "Only the converter rejects a complete schema" is withdrawn. See report69.
