# Research index

This directory contains sanitized historical research records, not a working game distribution.

| Path | Contents |
|---|---|
| `profile/010074F013262000/` | Final bounded experimental metadata, facts and shader-key relationships |
| `records/reports/` | Historical reports in their original language; later errata/superseding reports take precedence |
| `verification/contracts.json` | Supervisor-owned limited CPU decisions; separate from shader facts |
| `verification/v001` through `v007` | Source/plan snapshots, independent test source, structured results and review decisions |
| `observation-plan/` | Latest historical TF-intent parser, supervision, preflight and default-no-launch launcher source |
| `implementation-tests/` | Original CPU test source; no executable or raw command-stream payloads |
| `build-recipes/` | Historical isolated-host compile recipe; no host binary |
| `translator-experiments/` | Any retained source diffs; no experimental DLL or generated shaders |
| `archive-files.json` | Per-copy provenance, including sanitization flags and original/archive SHA256 |
| `ARCHIVE-SHA256SUMS` | SHA256 for actual files in this archive directory |

## Reading order

Read the root `ARCHIVE.md`, then the latest checkpoint and related errata.
Reports 115 and earlier SASS interpretations were superseded where explicitly stated; preserve corrections rather than combining contradictory conclusions.
V006 is a failed candidate; V007 is the accepted limited CPU observation-plan checkpoint.

The records describe locally observed artifacts that are not uploaded. Paths have been normalized, local session UUIDs removed,
and fenced excerpts omitted from prose reports. Original logs, game-derived binaries, shader dumps, images and private conversations remain local.
The historical reports are retained as research data in their original language; newly written archive documentation is English.

Original hashes in historical results describe original local files. They do not authenticate normalized copies.
Use `ARCHIVE-SHA256SUMS` for the shared copies. Historical tests often assume original local directory layouts and intentionally omitted artifacts;
read/adapt them before use and do not interpret missing artifacts as successful tests.
