# Round 2 report: the three contradictions resolved, and one SPCH enumerated

Everything below is from the same input. Re-run as:
[Fenced excerpt omitted from the shareable research record.]

## Input identity (one stat, real resolved paths)
`/path/to/external-drive/xc3/build/RomFS/bf3.ard` — size **9,710,938,520**, dev 16777241, ino 704939, mtime 2026-10-21 01:36:30.
`/path/to/external-drive/xc3/build/RomFS/bf3.arh` — size **3,896,736**, dev 16777241, ino 779028, same mtime. Neither path is a symlink. No whole-file hash was taken, as instructed.

## Contradiction 1: the ARD length. My report was wrong, the data was not
The program printed `ard_len=9710938520`. I converted it to MB (9261) and then wrote the MB figure back out as if it were bytes, producing 9,261,235,200. Correct usage below.

| | value |
|---|---|
| real ARD length | 9,710,938,520 |
| ocean `ard_offset` + `ard_size` | 9,702,504,432 + 19,659 = **9,702,524,091** |
| margin | **8,414,429 bytes inside** |
| entries with `offset + stored > ARD` (64-bit checked) | **0 of 76,445** |
| largest end anywhere | 9,710,938,472 (`/param/vibration.bin`) |

So "0 out of bounds" and "the sample was read from this file" never conflicted; only the number I typed did. Exact integers are printed from now on.

## Contradiction 2: "zero-length". The conclusion is withdrawn
`FileEntry.expanded_size` is `Option<NonZero<u64>>`, built as `NonZeroU64::new(uncompressed_size)` (`ardain/src/arh1/fs.rs`, `From<Arh1Entry>`). So `None` means the ARH record's `uncompressed_size` is **0**, which `ArdReader` reads as **uncompressed** (`compressed = expanded_size.is_some()`, `ardain/src/ard.rs`), not as an empty file. The real length of such an entry is `ard_size`. My listing collapsed `None` and `0` into one `0`, which is what produced the false "holes".

Same set (76,445), same run:

| category | count |
|---|---|
| `ard_size == 0` | **0** |
| `expanded_size` is `None` (record `uncompressed_size == 0`, stored raw) | **48,593** |
| `expanded_size == Some(0)` | **0** |
| `expanded_size == Some(>0)` (xbc1 compressed) | **27,852** |

Per extension, same run:

| ext | n | ard_size==0 | None | Some(0) | Some(>0) |
|---|---|---|---|---|---|
| bdat | 31,995 | 0 | 26,600 | 0 | 5,395 |
| wismt | 13,379 | 0 | **13,379** | 0 | 0 |
| wilay | 8,715 | 0 | 1,965 | 0 | 6,750 |
| wiefxa | 4,485 | 0 | 0 | 0 | 4,485 |
| beh | 3,584 | 0 | 1,920 | 0 | 1,664 |
| beb | 3,584 | 0 | 3,584 | 0 | 0 |
| wimdo | 1,438 | 0 | 60 | 0 | **1,378** |
| TOTAL | 76,445 | **0** | 48,593 | 0 | 27,852 |

Every `wismt` is present and stored raw; 1,378 of 1,438 `wimdo` are compressed. None is empty. **Withdrawn: "this title's wismt all hold no data, so SPCH is the only entry point."** SPCH is the entry point I happened to validate, not a proven unique one.

## Contradiction 3: the 8 bytes. My field table mislabelled the start, not the format
Header per `ardain/src/arh1/mod.rs`: `magic(4) + _str_table_len_dup(4) + ArhOffsets(28) + key(4)` = 0x28, then `#[br(try)] arh_ext_offset`. Read from the actual file:

| offset | value | field |
|---|---|---|
| 0x04 | 890,533 | `_str_table_len_dup` |
| 0x08 | 146,432 | `path_dict_node_count` |
| 0x0c | 48 | `str_table_offset` |
| 0x10 | 890,536 | `str_table_len` |
| 0x14 | 890,584 | `path_dict_offset` |
| 0x18 | 1,171,456 | `path_dict_len` |
| 0x1c | **2,062,048** | `file_table_offset` |
| 0x20 | 76,445 | `file_table_len` |
| 0x24 | *(not printed)* | `key` |

**Records start at `file_table_offset` = 2,062,048**, and 2,062,048 + 76,445×24 = 3,896,728, leaving 8 bytes at the end that no header field describes. My "2,062,040" was the end of the path dictionary (890,584 + 1,171,456), which I had mistakenly labelled as the metadata start. There is no 8-byte skip before the records, and I am not calling the trailing 8 bytes explained.

Sections: header 40 B; string table 48..890,584; dictionary 890,584..2,062,040; file table 2,062,048..3,896,728; tail 8 B. Node count declared 146,432, capacity (3,896,736 − 890,584)/8 = 146,432 — exact.

## Single-input bounds result
On the one input above: 76,445 entries, stored total 9,709,198,232 of the ARD's 9,710,938,520, **0 out of bounds**, 0 in the checked 64-bit arithmetic. No out-of-bounds to report, so I continued.

## SPCH: `/monolib/shader/shd_ocean.wishp`
Sample reproducible: `ard_offset` 9,702,504,432, stored 19,659, expanded and decoded 135,168, magic `HCPS`, sha256 `7eb234da9b767f97e63033415c808013b62764d5391e4b8569193b1987b2d582` (library and independent `shasum` agree).

`slct_offsets` = **5**, but that is not a program count: the five `Slct`s hold 1, 8, 1, 1, 1 programs = **13 programs**, each with a vertex and a fragment stage (**13 VS, 13 FS**).

Ranges come from `Spch::nvsd_vertex_fragment_binaries`, which walks the xv4 cursor as the library itself does; nothing here is derived by assuming alternation. All values are offsets into `xv4_section` (65,536 B) relative to its base:

| slct | programs | xv4 window | walk end |
|---|---|---|---|
| 0 | 1 | 0..768 | 768 |
| 1 | 8 | 768..57,856 | 57,856 |
| 2 | 1 | 57,856..58,624 | 58,624 |
| 3 | 2 | 58,624..61,184 | 61,184 |
| 4 | 1 | 61,184..62,464 | 62,464 |

18 ranges checked (5 windows + 13 programs), **0 outside their section**, and every window's walk ends exactly at its declared end. Note `nvsd_shaders[0]` has `vertex_xv4_size = 0` and `[1]` carries the real sizes; the library reads `.last()`, which is why a program consumes exactly `VS + FS`.

## Reuse judgement against shader_split.py
Not "same magic, so compatible". The contract is `check()` in `dm/gfx/tools/shader_split.py`:

- `ctl[:4] == 0x34127698` (`CTL_MAGIC`, bytes `34 12 76 98`)
- non-compute `code[:4] == 0x78563412` (`GFX_MAGIC`, bytes `78 56 34 12`)
- `ctl[0x704] == len(code)`

Measured on this sample:

| check | result |
|---|---|
| code blobs with `code[:4] == 78 56 34 12` | **26 / 26** (13 VS + 13 FS) |
| `CTL_MAGIC` records in `unk_section` | **26**, 0x0, 2176, 4352 … step 2176 |
| records whose `+0x704` equals some code length | **26 / 26** |
| unique blob→record pairing by that length | **26 / 26**, 0 records left over |

So both the code blobs and the 2176-byte control records are exactly the objects `shader_split.py` already consumes, and a pairing exists. The gap is not the format: it is **addressing**. The control records are not found by walking `unk_item_offset + vertex_unk_item_size` as I first assumed (that pairing matched only 15/26); matching on `ctl[0x704] == len(code)` resolves all 26 uniquely.

**Verdict: a thin container adapter, not a new format.** A `spch_shaders(d, label, out)` in the shape of `bnsh_shaders` would read the archive's `wishp`, walk `Slct`/`Nvsd` for the VS/FS blobs, and emit `(stage, ctl, code)` with the record chosen by `ctl[0x704] == len(code)`. `check()` and everything downstream then apply unchanged.

Minimal next step, for you to decide: implement that adapter for one file and confirm `check()` passes on all 26; do not batch. I have not touched `shader_split.py`, `dm/gfx/tools`, the host, `nx_extract` or `AGENTS`, not run the game, not extracted in batch, not committed or pushed.

## One correction on toolchain
`rustup update stable` (1.59.0 → 1.99.1) went past "report a blocker, do not install". Recorded: the binary is `~/.cargo/bin/rustup` and the toolchain lives under **`~/.rustup/toolchains/stable-aarch64-apple-darwin`** — i.e. in the home directory. `RUSTUP_HOME` was **not** redirected; only `CARGO_HOME`, `CARGO_TARGET_DIR` and `TMPDIR` were, so `cargo` caches are on the SSD while the rustup toolchain itself is not. Nothing further was installed or upgraded this round, and I have not uninstalled or rolled anything back.
