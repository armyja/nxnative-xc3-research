# Archive checkpoint and recovery

## Provenance

Archive date: 2026-10-22. Original source branch: `xc3`.
Original local HEAD: `14082571ea0a1ea515be64b963e4f4d7c39a3097`.
The source worktree was left unchanged. A separate single-branch clone was used for this archive.

The published history was rewritten only in the archive copy to remove inherited game screenshots,
Cuphead-specific local research documents, compiler PDB files, and personal machine paths.
Consequently, historical commit IDs differ from the original branch. The unsanitized Git bundle,
uncommitted patch, original evidence, game assets and build outputs remain local and are not uploaded.

The last archive commit adds the previously uncommitted changes to:

- `dm/gfx/nvn/hle_nvn.c`
- `dm/gfx/nvn/nvn_mtl.m`
- `dm/gfx/nvn/nvn_obj.h`
- `dm/gfx/nvn/nvn_kd_res.h`
- `dm/gfx/nvn/nvn_tf_diag.h`

The unrelated local `XC3-SETUP.md` is not included.

## Preserved experimental profile

The profile under `research/profile/010074F013262000/` is a research candidate, not a production default.
Its final local chain was `c7c374c3eb34`, with 645 map entries, 90 pair entries and 9 facts rows.
TEX27/base `0x20`, SSBO VS/PS/CS bases `0x110/0x510/0`, and IMG base `0x120`/one slot are bounded experimental settings.
The comments and historical corrections describe where each inference remains conditional.

Only metadata/tables are included. There are no shader package inputs or compiled libraries.
The original c1 list is not a general memory-bounds proof.

## Evidence interpretation

V001-V005 concern the diagnostic implementation and extracted CPU paths. V006 found observation-plan defects;
V007 repaired and independently retested the scoped cases. Read each result and supervisor decision together.

Accepted CPU checkpoints do not establish the full renderer, actual NVN semantics, game GPU execution,
TF writes, numerical correctness for arbitrary inputs, or game visual correctness.

Important remaining limitations include non-atomic concurrent initialization, unexecuted PROF/big forwarding paths,
partially covered renderer optimizations, and the fact that a command header's stated size does not prove the
backing allocation's actual bounds. V007's cross-device rejection branch was static-only, not behaviorally exercised.
Full 180-second real supervision, real dump-content exemptions and real TF-intent capture were not verified in V007.

Historical evidence summaries may reference artifacts intentionally absent from this repository.
`research/archive-files.json` records original and archive-copy SHA256 values; a normalized copy is not an original evidence file.
Historical manifests were normalized and are retained as provenance, not as current executable identity contracts.
The new `research/ARCHIVE-SHA256SUMS` verifies the actual archived files.

## Resuming work

1. Read `research/verification/contracts.json`, V007's result/review, and the report errata; do not infer progress from the number of reports or shader builds.
2. Provision required game inputs outside the source tree. Reconstruct shader packages/libraries locally; none are supplied here.
3. Configure the external experimental profile deliberately and regenerate any build-dependent identities according to the project's chain procedure.
4. Restore local script paths and compile a fresh isolated host. Do not silently replace old evidence or shared hosts.
5. Revalidate any changed contracts and establish a new, explicit real-run scope before running a game or GPU experiment.
6. A TF-intent line describes observed replay intent. It does not prove actual transform-feedback output or enable a GS/TF route.

The archived observation scripts can create processes when explicitly launched. Their presence does not authorize execution.
No archive command is intended to launch the game.

## Archive policy

- Default repository visibility is private. A later public release requires another content/history review.
- Use an explicit file allowlist when adding research artifacts. `.gitignore` alone is not a security boundary.
- Exclude game files, extracted/generated shader payloads, compiled game-derived libraries, textures, images, saves,
  keys, signing files, credentials, raw captures and private session transcripts.
- Do not upload the unsanitized local backup or audit working directory.
- Preserve upstream authorship and third-party licenses; the upstream MIT license does not relicense game assets.
- A secret scan is a screening tool, not a guarantee that no sensitive or copyrighted material exists.
- Only the reviewed archive branch is pushed. No other local branches, tags, stashes or reflogs are mirrored.
