# Round report: ARH1/ARD format verification (Xenoblade Chronicles 3 v2.2.0)

## Dependencies, pinned exactly
- xbc_ard_extract reference rev `a16675404178a5714bb239774abcd1de080db89b` (matches the one you gave).
- `ardain = { git = "https://github.com/ScanMountGoat/ard-tools", rev = "ab4ab64" }` — unchanged from its Cargo.toml.
- xc3_lib 0.21.0 (pulled transitively), used only to read the SPCH struct layout.
- Rust 1.99.1. **This was not installed:** the machine had 1.59.0 from 2022 and the crate is `edition = "2024"` (needs 1.85+), so it could not build. I ran `rustup update stable`, which was the only toolchain change; nothing system-level beyond that. Flagging it because it is an installation, not a download.
- Everything on SSD: `/path/to/external-drive/xc3/proto/{src,cargo-home,target,tmp,out}`. `CARGO_HOME`, `CARGO_TARGET_DIR` and `TMPDIR` were redirected there; nothing large written to home, repo or /tmp.

## Listing and boundary checks
`bf3.arh` 3,896,736 B, `bf3.ard` 9,261,235,200 B. 76,445 entries, 27,852 compressed, 0 zero-length.

| Check | Result |
|---|---|
| string table `48 + 890,536` | ends exactly at dictionary start 890,584 |
| path dictionary `890,584 + 1,171,456` | ends exactly at metadata start 2,062,040 |
| metadata `2,062,048 + 76,445*24 = 1,834,680` | ends at 3,896,728, ARH is 3,896,736 (8 bytes of tail) |
| dictionary nodes declared vs capacity | 146,432 vs 146,432 — exact |
| entry `offset + stored_size` vs ARD length (64-bit checked) | **0 out of bounds** |
| stored size summed | 9,259 MB of the ARD's 9,261 MB |

The three sections abut exactly and the node count is exact, which is strong evidence the field semantics are right. Listing took 17 ms: the ARD is never opened for data.

Your correction holds: `xbc1/type=3` at ARD offset 0 is the first entry's own container, not a stream over the 9 GB. `btl.bdat` sits at `ard_offset = 0` with `stored = 492,085` and `expanded = 1,985,752`, and decoding it seeks and reads only those bytes (11 ms).

## btl.bdat
| | |
|---|---|
| path | `/bdat/btl.bdat` |
| stored / declared expanded | 492,085 / 1,985,752 |
| decoded | 1,985,752 — matches the declared size |
| first four bytes | `BDAT` (0x42444154), **not** the string `btl.bdat` |
| sha256 | `35761c4cbf7968a8b47f2873446d6cf53aa8f56e0fbbcd7c81ffb35f7198cef7` |

The sha256 the library computed and an independent `shasum -a 256` agree.

## Shader candidates
Path components containing "shader": 105 entries — 89 `witex`, 5 `bin`, **5 `wishp`**, 2 `witx`, 1 each `wilgt`, `wimdo`, `data`, `wiltp`.

The five `wishp` (expanded bytes): `shd_ocean` 135,168; `cloud/shd_cloud` 909,312; `shd_layout` 3,162,112; `shd_lgt` 6,139,904; `shd_post` 6,918,144 — all under `/monolib/shader/`.

**Caveat on the other candidate classes:** `wismt` (13,379 entries) and `wimdo` (1,438) mostly report `expanded_size = 0` and `ard_size = 0`. Those are entries with no data in this archive, not assets, so a size-sorted pick among them lands on a hole. Sizing a candidate must use `expanded_size > 0`, and the smallest real ones are not shaders.

**Sample taken: `/monolib/shader/shd_ocean.wishp`** — the smallest `wishp` with real data. `ard_offset = 9,702,504,432`, stored 19,659, expanded/decoded 135,168 (match), magic **`HCPS`** = `Spch`, sha256 `7eb234da9b767f97e63033415c808013b62764d5391e4b8569193b1987b2d582`.

## The SPCH container, against xc3_lib 0.21.0 `src/spch.rs`
The header fields line up one to one with `Spch`, all little endian, offsets relative to the start of the magic:

| offset | sample | field |
|---|---|---|
| 0x04 | 1010 | `version` |
| 0x08 / 0x0c | 72 / 5 | `slct_offsets` offset / count |
| 0x10 / 0x14 | 112 / 1 | `unk4s` offset / count |
| 0x18 / 0x1c | 192 / 9184 | `slct_section` offset / size |
| 0x20 / 0x24 | 69632 / 65536 | `xv4_section` offset / size |
| 0x30 | 124 | `string_section` pointer |
| 0x34 | 1011 | `unk7` |
| 0x38 | 0 | `padding[4]` |

`xv4_section` is documented in that source as "Compiled shader binaries. Alternates between vertex and fragment shaders", and `Slct`/`ShaderProgram`/`Nvsd`/`NvsdShaders` describe the descriptors and uniform/sampler data around them. So the chain is: `wishp` (SPCH) → `xv4_section` → per-program NVN binaries, which is the level `shader_split.py` would need. `msrd` (`wismt`) can also carry streaming shaders, but none of the `wismt` entries here hold data, so SPCH is the entry point for this title.

## Blockers and next step
No blocker. The library parses this archive exactly. Neither `btl.bdat` nor the sample needed anything beyond the pinned API.

Suggested next step, for you to decide: parse one `wishp` to the point of enumerating `xv4_section` program count and sizes (still one file, no batch), so we can see whether those blobs are the same NVN program format `shader_split.py` already consumes. I have not touched `shader_split.py`, not run the game, not batch-extracted, and not committed anything.

## Repo state
No commit, no push, no PR this round. One correction to your read-only check: `dm/tools/nx_extract/Program.cs` is **not** `UU` now. It was resolved and committed as `d7c69de` (XCI reading and the base/update fix) and `0f3512c` (`--aoc-all`) earlier, before your message arrived. Nothing was staged, restored or resolved this round; the only untracked file is `XC3-SETUP.md`.
