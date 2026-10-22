# Round 14: the offline build refuses a selected geometry stage

**HEAD `54fb37d`** on `xc3`, author armyja, appended over `01bfd8e`, not pushed. 20 files: 2 new, 14 generated
headers, 4 edited.

## The guard
`dm/gfx/tools/dmsh_stage.py` holds the check; `dmsh_build.py` calls it at module level right after
`keys = sorted(want) if want else sorted(loc)`:

[Fenced excerpt omitted from the shareable research record.]

- **Stage source is job_for's own rule**: `stage_of.get(key, name[:2])` — the mapping table for embedded
  `main.rodata@` rows, the first two characters of the record name for packages. The `{'vertex': 'pixel'}`
  mapping at `dmsh_build.py:235` is not used and was not turned into a guard.
- **Position**: after the selection, **before** `os.makedirs(out)`, before the `MTL.fill()` prefill that copies
  earlier libraries into the compile cache, and before the first `cache_lookup()` in the loop. So a cached
  geometry entry cannot bypass it and a refusal writes nothing.
- **Selection semantics**: the guard iterates `keys`, i.e. what was asked for. With no key argument `keys` is
  every key, so a map containing geometry refuses; an explicit `vs` / `ps` / `cs` subset builds as before even
  when the map holds geometry.
- **Message**: `[RED] <key> (<name>#<offset>): unsupported geometry stage gs - the Metal backend encodes only the
  vertex and fragment stages (…nvn_mtl.m binds pr->sh[0] and pr->sh[1]), so this shader would load and never run`,
  then exit code 1. The offset is decimal, matching the `source` field the build already writes into reflection.
- **Extraction untouched**: `shader_split.py` still extracts every geometry stage and lists its key; nothing is
  filtered or deleted upstream.

## Chain procedure
`dmsh_stage.py` is now in `dmsh_chain.FILES`, so it participates in the version. `--header` was re-run for all
14 profiles and each header matches its source version (spot-checked):

| profile | V |
|---|---|
| 0100A5C00D162000 | `5614dce0071b` |
| 0100F2C0115B6000 | `b6b00d7296bf` |
| 010015100B514000 | `048b9f93ea4e` |

Spot check of all 14: `source == header` for each; the full list is in the commit.

**Lock untouched**, no fabricated fingerprint. `dmsh_chain.py --check-tools` still reports the pre-existing
blocker:
[Fenced excerpt omitted from the shareable research record.]
Because `dmsh_build.py` exits on that check at line 15, the script cannot be launched end to end here, and the
remaining chain steps (rebuild shader libraries, regenerate `c1_full.tsv`, rebuild the host) are outstanding for
that same reason. I did not run them and did not work around the check.

## Tests
[Fenced excerpt omitted from the shareable research record.]
`test_dmsh_stage.py`:
- a selected geometry key is refused, with key, `name#offset` source and `unsupported geometry stage` in the line;
- selecting everything that has geometry refuses;
- a map holding geometry does not block an explicit `vs/ps/cs` subset;
- embedded rows take their stage from the mapping table, and the table overrides a package name;
- the no-key form (every key) refuses;
- the module contains no `subprocess` / `os.system` / `xcrun` / `metallib` / `XLATE`, so refusing cannot reach
  the translator or the Metal compiler;
- **placement, read from `dmsh_build.py` itself** (the script cannot be launched here): the call follows the
  selection and precedes `os.makedirs(out)`, the first `cache_lookup(` after the selection, and the `MTL.fill(`
  prefill.

The 26 SPCH tests are unchanged and still pass.

## ResourceWarning
`scan_file`'s `open(path,'rb').read()` became a `with` block (the `.zs` branch is unchanged). Verified with
`-W error::ResourceWarning` on a synthetic file and on two real samples: no warning escapes. No other reads in
the tree were touched.

## Not done, and why
- No translation, no library build, no host build, no game run: the translator is not built (above).
- The guard is a **build-time** protection, not runtime fail-closed. The host still has no geometry encoding
  path; a library built before this commit, or assembled by hand, would still load such a shader and never run.
- No whitelist was invented for other unknown stages; only `gs` is refused, and anything else keeps its current
  behaviour.
- Geometry behaviour in `dmsh_build` beyond this refusal (`raster_facts` returning `{}`) is documented, not changed.

## Workspace
`XC3-SETUP.md` untracked and unstaged; nothing else modified. No push, no PR, no AGENTS / host / nx_extract
change, no extraction, no tool install, no profile table changed.

## Remaining
- The five-container extraction/pairing numbers remain my measurement; the supervisor has read the code and the
  26 tests but not re-read the SSD samples.
- `check_tools` failing means no offline build can run in this environment at all; that is the next concrete
  blocker if a build is wanted, and it needs the translator rebuilt from the in-repo source, not a lock update.
- A minimal VS/PS/CS translation sample is the agreed next step and was not started.
