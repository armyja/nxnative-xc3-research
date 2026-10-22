# Report 71 — pinned xc3_lib reads the NVSD metadata for slct175/program0

Offline, 20-minute bounded: one small read-only helper built with the existing toolchain and the cached pinned crate;
no guest, no translation, no profile/value change, no commit. HEAD `82f488b` unchanged.
Artifacts: `/path/to/external-drive/xc3/work/experiments/ssbo-nvsd-pinned/`.

## 1. Helper, toolchain, provenance

- `src/main.rs` (sha256 prefix `54c425c902d32a08843b`): `Spch::read` → `slct_offsets[175].read_slct(&spch.slct_section)` →
  `programs[0].read_nvsd()`, then prints the NVSD fields; no other program, no writes.
- `Cargo.toml` is the existing wrapper's file verbatim (package `spch_enum`, deps `xc3_lib 0.21.0`, `binrw 0.15`,
  `anyhow`, `sha2`), so `--locked` accepts the copied `Cargo.lock` (sha256 prefix `27b1bc1212044ecfe531`).
- Lock pins `xc3_lib = 0.21.0` (checksum `e678b03ec57ddaa7eb277786da58a9fb58db25130b35af3a40da526ddc35e5fa`), matching
  `.../cargo-home/registry/src/index.crates.io-1949cf8c6b5b557f/xc3_lib-0.21.0/src/spch.rs`.
- Build: `CARGO_HOME=/path/to/external-drive/xc3/proto/cargo-home CARGO_TARGET_DIR=<exp>/target cargo build --offline --locked`
  → rc 0, 28.8 s, all dependencies from cache; no fetch, no install, no lock update, no new toolchain.
  First attempt failed only because the copied lock's root package name did not match a renamed package; using the
  original package name fixed it. Nothing about the crate changed.
- Input container: `shd_post.wishp`, sha256 prefix `48b9098e6ca42241ce20`, 6,918,144 bytes — the same file whose
  program matched the package byte-for-byte in report70 (ctl `2e73bb65cd577a57`, code `1cee8b5dd7e17232`).

## 2. Metadata as read (verbatim)

[Fenced excerpt omitted from the shareable research record.]

Entry 0 (`fx 1792`, `fu 2176`) is exactly the VS package's code and control lengths, so this NVSD is the program that
contains the target VS; entry 1 is its pixel partner. Stage is still taken from the entry's code header, not from any
`vertex`/`fragment` field name — `nvsd_shaders` carries sizes only.

## 3. What the metadata does and does not constrain

- **One storage buffer only** (`buffers2_count = 1`, index list `[0]`): the program has exactly one candidate, so the
  "don't take the first of several" hazard does not arise here. Name `U_Instance`, 2 uniforms, `size_in_bytes 28`,
  `unk3 372`, `handle 0`, `visibility Fragment`.
- Targets of the pinned source's own doubts, and therefore **not** usable as proof:
  - `UniformBuffer.handle` carries `// TODO: handle.handle + 3?` (spch.rs ~301), so the `handle` byte's meaning is
    unverified for storage buffers;
  - `Visibility` carries `// TODO: this doesn't work for storage buffers?` (~317): the literal `Fragment` must **not** be
    read as "the vertex stage cannot read this buffer" — the shader demonstrably does, and the library itself flags the
    field as unreliable.
- The raw response's `slot 0` and this `handle 0` coincide, and `vp_s0` is named 0, but these are three different
  namespaces (translator slot, NVSD handle, NVN register). Nothing read here proves `handle == NVN slot`, and the code's
  own `+3?` doubt points the other way. `buffers2_indices = [0]` likewise does not map to the SPIR-V binding 1.
- Therefore the metadata gives a **uniqueness** constraint (exactly one storage buffer in this program) and a candidate
  handle, but **no independent NVN-slot or base value**. `baseCandidate = 0x110` from report70 remains a hypothesis,
  and 0x110 is not established as the whole table base.

## 4. Runtime path and predicates (unchanged)

`reg` is the NVN slot read from `S.ssbo[stage][reg]` at encoding; the profile base is the c0 table address
(`vs=0` placeholder). For this key the only failing predicate is `0 <= off - base < 0x100` with `off = 0x110` and
`base = 0`; `cb_slot == 0` and 16-alignment pass. Nothing in this round changed the base, the reg, the converter or the
guard, and no single-key rebuild was done.

## 5. Next minimal falsifiable step (not done, needs authorisation)

Two independent checks, either of which is decisive on its own:

1. **Experiment-profile-only**: set `nvn_ssbo_bases vs=0x110` in a throwaway profile and rebuild only this key; predict
   `reg = 0`, `rw false`, `vp_s0` unchanged, loader no longer rejecting. Falsified immediately if `reg` is not 0 or the
   range still fails.
2. **Independent slot evidence**: a parser that exposes the NVSD handle semantics unambiguously (the pinned crate's own
   TODOs show 0.21.0 does not), or an observation of the guest's c0 writes for this stage, so that `handle`, translator
   `slot` and NVN `reg` can be separated.

Neither was executed. No other program was scanned, no ARD export, no driver project, no new general parser.
