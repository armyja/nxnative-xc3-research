# Refill source integrity: fixes, tests, and the audit of the 645-key library

HEAD `885128c` (on top of `640cc3f`). Two tools changed, no other behaviour touched. No guest run this round.

## 1. What was wrong, and what the tools do now

`dmsh_refill.py`
- **Package names carry the key.** Every dump-only shader used to be written to `vs_runtime_dump.bin` /
  `ps_runtime_dump.bin`, so each one overwrote the previous while older map rows kept pointing at offset 0 of the
  survivor.
- **Every package is verified as it is written**: header, both lengths, the control's own length field, the key
  recomputed from ctl+code, and the stage byte. A map row is only emitted for a package that passed; "the key was
  found in a container" is never accepted on its own.
- **Dump-only shaders are never paired.** They used to key `(None, None, None)`, so the last vertex and the last pixel
  of a batch were written out as a pair no draw ever used.
- **Container pairs need an ordered, complete `[vs, ps]` of one program** — no duplicate stage, no geometry stage, no
  extra stage; every other program is reported with its reason.
- **`--profile` must be the profile `DM_GAME`/`DM_GAMES_DIR` resolve to**, checked before anything is written.
- **Fail before write**: everything is built in a temporary directory, validated, then moved in; the map and pairs are
  replaced through temporary files. A refusal leaves the profile untouched, and an existing package is never replaced
  by different bytes.
- `--selftest` runs the rule set plus an end-to-end CLI round on synthetic dumps (no game files, no compiler) and
  `--no-build` stops after the inputs are verified.

`dmsh_pairs_from_log.py`
- A pass pairs only when it binds **exactly one vertex and one pixel key**. A pass with several keys for a stage is
  reported as ambiguous instead of pairing the last of each. Reproduced before the fix: one pass with
  `(vs a, ps b)` then `(vs c, ps d)` produced only `(c, d)`, and an interleaved pass could name a combination that was
  never bound together. `--selftest` covers the clean, multi-program, duplicate-vertex and cross-pass cases.

Both selftests pass (`selftest: 0 failure(s)` for each).

## 2. Audit of the 645-key profile (`boot217`, chain `1c007b9f97e3`)

Read-only, per map row: open the named package at the row's offset, re-hash it, check the stage byte.

[Fenced excerpt omitted from the shareable research record.]

So the 645-key library is a **build result whose input identity is not established for 384 of its rows**. Only the 261
container-sourced rows have packages that hash back to their key. This is the state the earlier reports should have
carried: "645 keys were built", not "645 keys are correct".

## 3. Recovery (new directory, nothing overwritten)

`work/experiments/recovered-384/boot217/` — 384 correctly named packages rebuilt from the **immutable run dumps**, with
`provenance.tsv` naming, per key, the run it came from and both lengths. 384 of 384 recovered; 0 unrecoverable.

## 4. Which builds are affected

| library | keys | chain | rows with wrong input |
|---|---|---|---|
| boot156 and earlier | ≤156 | — | **0** |
| boot197 | 197 | 6f3fa616b578 | 41 |
| boot212 | 210 | 582ad4e2d205 | 41 |
| boot213 | 213 | 3353ff7f3625 | 41 |
| boot214 | 230 | aace01260889 | 41 |
| boot215 | 234 | c3198d91fe1d | 41 |
| boot216 | 641 | fa7115230a50 | 384 |
| boot217 | 645 | 1c007b9f97e3 | 384 |

Their MSL and metallib files for those rows were translated from the wrong bytes and must be rebuilt from the recovered
packages before anything is concluded from them. A CAS hit is not evidence of provenance: the cache is keyed on bytes,
and the wrong bytes simply hit their own entries.

## 5. Corrections that follow

- **The three `locn4` interface mismatches are withdrawn as evidence.** All three pairs came from the invented
  dump-only pairing, so `dmsh_link_check` was reading pairs that no draw ever used. The checker's own rule still holds;
  its input here did not.
- **The 32 pairs recovered from pass records are no longer used** for a build; that tool had the "last key per stage"
  defect and its output was merged into `boot212`'s profile before the rule existed.
- The title-screen conclusion stays exactly where it was: the albedo and normal targets have no consumer *in the
  recorded pass graph*, which does not exclude framebuffer fetch, attachment load or aliasing, and the titan's
  brightness is unresolved.

## 6. Still unproven
- Whether integration images (`fp_i_cb2_48_r32ui` failed to resolve a slot) need a driver base we do not have.
- What control `+0x714 = 2` means; those keys stay refused.
- Everything in section 5's third bullet.
