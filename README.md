# XC3 native graphics research archive

This is a paused personal research archive based on [seedds/nxnative](https://github.com/seedds/nxnative).
It preserves the XC3 branch, diagnostic source changes, experimental profile metadata, and selected research and independent CPU-validation records as of 2026-10-22.

**This is not a playable XC3 release. Real game GS/TF integration is incomplete.**
There is no game download, ready-to-run game package, or game-derived shader library in this repository.

## What was preserved

- The `xc3` source branch history, sanitized in an independent copy. Original authorship and licenses are retained.
- The latest uncommitted GS-resource and TF-intent diagnostic source changes, included in this archive commit.
- The experimental XC3 profile in [`research/profile/010074F013262000/`](research/profile/010074F013262000/).
- Historical research reports, with local paths/session routes normalized and fenced excerpts omitted.
- Frozen source/plan snapshots and independent verification source for V001-V007, plus structured decisions.
- The latest TF-intent observation plan and the isolated host build recipe, as historical source only.

Start with [the checkpoint and recovery notes](ARCHIVE.md) and [the research index](research/README.md).
The inherited player/development documentation describes the upstream project; it is not an XC3 support claim.

## Current checkpoint

- Integer render-target work produced bounded compatibility and runtime encoding evidence; it did not establish general numerical or visual correctness.
- Synthetic VS -> GS -> passthrough -> test-fragment experiments produced limited numerical/pixel evidence locally. Their game-derived shader artifacts and images are not distributed here.
- A real 95bf resource snapshot was observed locally. It did not prove real GS execution or TF output.
- The default-off TF diagnostic implementation passed scoped independent CPU verification through V005.
- V007 passed scoped CPU/synthetic verification of the observation plan, including production-format log association and child cleanup on evidence errors.
- The matching host was compiled locally but not executed. No real TF-intent observation was authorized by the V007 review.
- **Real game GS/TF route: NO-GO. Research is paused.**

## Excluded content

No NSP/XCI/NCA, RomFS/ExeFS, original or patched game modules, raw shader ctl/code, extracted shader packages,
game-derived SPIR-V/MSL/AIR/metallib, game textures, screenshots, saves, keys, credentials, local conversations,
or raw runtime captures are included in this archive addition. Inherited game screenshots and compiler PDBs were removed from the published history.

Pinned compiler executables/DLLs already present in the upstream source history are tools, not game binaries;
retain the corresponding third-party licenses and notices. They are not covered by a claim that all repository contents were authored here.

## Reproduction and privacy

Historical scripts have normalized `/path/to/...` placeholders and frozen-machine identities. They require deliberate
local configuration and regenerated identity manifests; they are not a portable launcher and must not be treated as execution authorization.
Obtain any required game inputs and keys independently and keep them outside this repository.
See [the archive policy](ARCHIVE.md#archive-policy) before adding files or making this repository public.

The upstream MIT [LICENSE](LICENSE) and dependency licenses are preserved. This archive grants no rights in Nintendo/game assets.
