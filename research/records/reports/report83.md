# Report 83 — NVSD metadata of the two shd_layout programs whose VS has an sbuf at offset 0x130

Offline read-only: no new translator request, no MSL/Metal/host/library build, no guest, no profile/base/facts/translator/
lock change, no commit. HEAD `ddd7d0a`. Artifacts:
`/path/to/external-drive/xc3/work/experiments/ssbo-nvsd-offset130/` (`src/main.rs`, `Cargo.toml`, `Cargo.lock`, `build.log`,
`out.txt`, `err.txt`).

## 1. Provenance

- Container `/path/to/external-drive/xc3/proto/out/others/shd_layout.wishp`, **3,162,112 bytes**, sha256 prefix
  `6931c8e24b84e2a6fed915cc`.
- Helper: sha256 prefix `ce824d148870c7c9b20c00c6`; pinned `xc3_lib 0.21.0` (lock sha prefix `27b1bc1212044ecfe531`,
  matching the cached registry source); `cargo build --offline --locked` rc 0; run rc 0. No new parser, no install, no
  fetch, no lock update.
- Read path exactly `Spch::read → slct_offsets[10].read_slct → programs[2/3].read_nvsd`.

## 2. Raw metadata

[Fenced excerpt omitted from the shareable research record.]

## 3. Identity (by hash, not size)

| package | key | ctl | code area | container entry | stage |
|---|---|---|---|---|---|
| `vs_shd_layout_s10p2.bin@0` | `ab5b6564e4add61c` | 2176 `e8feba743b9461b9` | 512 `ce34fc8483dc0a9a` | `#SPCH#10:2:0:vs` | vs |
| `vs_shd_layout_s10p3.bin@0` | `cea273f9f0936f5b` | 2176 `69d0b0c84b883e09` | 512 `d002fbf391877be1` | `#SPCH#10:3:0:vs` | vs |

`spch.shaders()` over the container has 920 entries; exactly one entry per package matched **both** the control and the
code hash, at entry 0 of program 2 and program 3 respectively, each stage `vs`. Size agreement alone was not used.

## 4. The two keys' raw responses (from report82's survey, not re-translated)

| key | stage | reflection index | response binding | slot | cb_slot | cb_offset (words) | off (bytes) | flags | rw |
|---|---|---|---|---|---|---|---|---|---|
| `ab5b6564e4add61c` | vs | 0 | 1 | 0 | 0 | 76 | **0x130** | 0 | false |
| `cea273f9f0936f5b` | vs | 0 | 1 | 0 | 0 | 76 | **0x130** | 1 | false |

## 5. Comparison with the report71 target

| | Slct175 program0 (VS `9b770cf888d729bd`) | Slct10 program2 (`ab5b6564e4add61c`) | Slct10 program3 (`cea273f9f0936f5b`) |
|---|---|---|---|
| storage buffers in the program | 1 | **3** | **1** |
| names | `U_Instance` | `DataBlock`, `SecBlock`, `U_SKIP` | `U_SKIP` |
| handles | 0 | 0, 1, 2 | 2 |
| sizes | 28 | 4, 4, 16 | 16 |
| response off | 0x110 | **0x130** | **0x130** |
| response slot | 0 | 0 | 0 |

## 6. What is and is not established

- Both layout programs contain a single `U_SKIP` buffer with **handle 2** and size 16, and their VS response is a single
  sbuf at `0x130`. Under the *hypothesis* base_vs = 0x110, `0x130 = 0x110 + 16·2`, i.e. reg 2, which coincides with
  handle 2 — an extra **static compatibility** observation, not a measured reg.
- It is not proof: program 2's storage list has three buffers and the metadata is program-wide; `buffers2_indices`
  (`[0,1,2]` vs `[-1,-1,0]`) does not by itself say which buffer the *vertex* stage's single sbuf uses. The response's
  `slot` is 0 for both keys while the offset would imply reg 2, another instance of slot ≠ reg.
- The source's own TODOs stay: `handle+3?` and "visibility doesn't work for storage buffers" — the literal `Fragment`
  here is not evidence that the VS cannot read these buffers.
- The runtime three-slot snapshot in report80 is from a different program (slct175 program0, pass 553266); it is not a
  same-draw association with these two programs, and the old slot sizes (140/576000/16) are background only.
- No base is computed, no slot/reg is written to any profile, and no title-wide conclusion is drawn.

## 7. Remaining unknowns

- Whether the vertex stage's single sbuf actually refers to `U_SKIP` (and not `DataBlock`/`SecBlock`) in program 2; the
  program-level index lists do not resolve per-stage selection.
- The real c0 table base (0x110 remains a hypothesis), and whether NVSD `handle` equals the NVN reg at all.
- Any same-draw relation between these programs and the three-slot observation.
