# Round 15: the translator was never missing — a runtime lookup; guard side effects fixed; three real translations

**HEAD `2682fbc`** on `xc3`, author armyja, appended over `54fb37d`, not pushed. 17 files: 1 new test, 2 edited
tools/tests, 14 regenerated chain headers.

## A. Runtime: the diagnosis in earlier reports was wrong

`dmsh_xlate_bin/dmsh_xlate` is a self-contained apphost; it could not find a .NET runtime because none is in the
default locations. One is already installed by Homebrew:
[Fenced excerpt omitted from the shareable research record.]
With `DOTNET_ROOT_ARM64` / `DOTNET_ROOT` set to `/opt/homebrew/Cellar/dotnet/10.0.401_1/libexec` and nothing
else changed (no installer, no SDK install, no PATH edit, no shell profile):
[Fenced excerpt omitted from the shareable research record.]
So every tool matches the lock — translator DLLs, Ryujinx DLLs, spirv-cross and both Metal compilers. Nothing was
published, no binary changed, the lock was not updated. **Correction: "the translator was not built" was false.**
It was a runtime-discovery failure; no download was needed.

## B. The guard's side effect, fixed and tested at the entry

`if IOSOUT: … os.makedirs(IOSOUT)` sat near the top, before the preflight, so a refused selection had already
created the iOS directory. The path is still computed there; the directory is now created with the other
post-preflight work. Everything else is unchanged.

`dm/gfx/tests/test_dmsh_build_entry.py` runs the **real script** — synthetic profile via `DM_GAMES_DIR`, synthetic
`shader_map.tsv` (vs/ps/cs/gs rows) and package, and a stand-in translator placed inside a **copy of the real tool
directory** so `check_tools` still fingerprints real DLLs and `--source-sha` answers correctly.

| case | result |
|---|---|
| select `gs` with `IOSOUT` set | exit ≠ 0; message carries the key and `gs_pkg.bin#0`; **output dir absent, iOS dir absent, translator never invoked**, cache untouched |
| select everything (no key argument) | refused the same way, nothing created |
| pre-existing cache entry for the gs key | still refused before any cache access; cache directory byte-identical afterwards; translator never invoked |
| explicit `vs`+`ps` | **no** geometry message; the `b-<V>` library directory and the `IOSOUT` directory appear — i.e. it passed the preflight and reached the per-key work |

The stand-in translator records invocations by touching a file, so "no translator call" is observed, not inferred.
`spirv-cross`/`metal` cannot run before the guard because nothing past the guard executes. The old
"the module has no `subprocess` string" test is kept but relabelled as a module property, not proof.

`Ran 4 tests ... OK`. `test_dmsh_stage.py`'s own unclosed reads now use `with`; `Ran 9 ... OK` under
`-W error::ResourceWarning`. `test_spch.py` `Ran 26 ... OK`.

`dmsh_build.py` is a chain file, so all 14 `dmsh_chain.h` were regenerated (`--header`); current V for
`0100A5C00D162000` is `f1882e506dbf`.

## C. Three real translations (no GS, no library, no Metal)

Keys from the real adapter, one plain VS/PS program plus one compute stage:

| file | slct/prog/entry | stage | key | code | ctl | c1 |
|---|---|---|---|---|---|---|
| shd_ocean.wishp | 0/0/0 | vs | `f08a30202513bbba` | 512 | 2176 | 512..512 (empty) |
| shd_ocean.wishp | 0/0/1 | ps | `8b37aad9f6878b32` | 256 | 2176 | 256..256 (empty) |
| shd_cloud.wishp | 3/0/0 | cs | `f625a4f33c78facd` | 5632 | 2176 | 5376..5632 |

Code/CTL sha256 are recorded in `jobs_meta.json`. Jobs follow `job_for`'s contract exactly: code area with the
0x30 header stripped (compute: 0x30 header and the zeroed 0x30..0x100 padding stripped), `c1` sliced from the code
area at the control's `+0x700`/`+0x704`, empty `tex`/`img`/`attr`/`fout` because no answer table exists for this
title — **so every query is answered with translator defaults**, which is recorded, not hidden.

Results, one request per key:
[Fenced excerpt omitted from the shareable research record.]
`.res.json` per key: vs 1 cbuf / 0 textures, ps 1 cbuf / 0 textures / `frag_out_map` 15, cs 1 cbuf / 1 texture; no
notes on any of them. `spirv-val` is **not installed**, so the SPIR-V is not externally validated and I did not
install it.

This says those three requests translate into SPIR-V. It says nothing about Metal, linking, a library, the game,
or the other 3,701 stages.

## Chain procedure — what is and is not done
Done: `--header` for all 14 profiles; `--check-tools` passes.
**Not done** (and not claimed): rebuilding the shader libraries, regenerating each profile's `c1_full.tsv`,
rebuilding the host. Those need a real per-profile build against real packages, and this round deliberately did
not run a build.

## Workspace
`XC3-SETUP.md` untracked and unstaged; nothing else modified. No push, no PR, no AGENTS / host / nx_extract
change, no new extraction, no system install, no game run, no host build. Runtime and experiment files live only
under `/path/to/external-drive/xc3/proto/translate` and the Homebrew install already present.

## Remaining
- `DOTNET_ROOT` must be set for any build in this environment; it is not in the shell profile (by instruction) and
  the tools do not discover the Homebrew prefix themselves.
- The three translated keys used default answers for every resource query; a real profile will change those.
- Geometry is refused at build time but the host still has no geometry encoding path.
