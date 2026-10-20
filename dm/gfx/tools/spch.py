# SPCH ('HCPS') shader containers: the .wishp files of Monolith Soft's Xenoblade engine (Xenoblade Chronicles 3).
#
# Structure as read from xc3_lib 0.21.0 `src/spch.rs` (the reference for this parser; the pinned crate is not
# vendored, only this reading of its layout is reproduced):
#   +0x00 magic 'HCPS', +0x04 version, then five {offset, count} u32 pairs relative to the start of the file's
#   HCPS magic: slct_offsets, unk4s, slct_section, xv4_section, unk_section; +0x30 string_section pointer,
#   +0x34 unk7, +0x38 padding[4].
#   slct_offsets[i] = {u32 offset, u32 unk1}; the Slct at slct_section + offset starts with 'SLCT', then
#   {unk_strings offset,count}, {programs offset,count}, unk5, unk_offset, unk_offset1, unk_item_offset,
#   unk_item_total_size, xv4_offset, xv4_total_size (all u32; xv4_offset is relative to xv4_section).
#   A ShaderProgram is {program_data offset, count} into the same file; its bytes are an NVSD whose
#   nvsd_shaders list holds {vertex_xv4_size, fragment_xv4_size, vertex_unk_item_size, fragment_unk_item_size}.
#
# Association is purely structural, never by searching for a magic or matching a code length:
#   xv4 cursor: starts at Slct.xv4_offset, advances by vertex_xv4_size + fragment_xv4_size per program
#   unk cursor: starts at Slct.unk_item_offset, advances by vertex_unk_item_size + fragment_unk_item_size
# Each Slct's two walks must land exactly on the ends its own fields declare, corroborated by
# xv4_total_size / unk_item_total_size, or this module refuses the file. Two programs with identical code
# lengths still get different windows because no step depends on a code length.
#
# Supported layout: one nvsd_shaders entry carrying data (the last one), any earlier entry all zero. Any other
# arrangement is reported as unsupported rather than guessed at: a variant is never dropped silently.

import struct

HCPS = b'HCPS'
SLCT = b'SLCT'
# SPH stage bits (word at code +0x30, bits 10..13), the same mapping shader_split.SPH_STAGE uses
_SPH_STAGE = {1: 'vs', 2: 'hs', 3: 'ds', 4: 'gs', 5: 'ps'}
GFX_MAGIC, CS_MAGIC = bytes.fromhex('78563412'), bytes.fromhex('79563412')
CTL_MAGIC = bytes.fromhex('34127698')


class Unsupported(Exception):
    """A layout this parser does not understand: reported with file/slct/program/field, never guessed around."""


def _u32(d, at):
    return struct.unpack_from('<I', d, at)[0]


def _pair(d, at, base):
    """{offset, count} u32 pair at `at`; the offset is relative to `base` (0 = the file's HCPS magic)."""
    off, cnt = struct.unpack_from('<II', d, at)
    return base + off, cnt


def shaders(d, label, want=None):
    """SPCH bytes → [(where, stage, control, code)], the same shape bnsh_shaders returns.

    `want` limits the output to the given stages (shader_split passes its STAGES); None keeps every stage.
    Raises Unsupported for a layout this parser does not understand and ValueError for a truncated or
    inconsistent file: the caller must not turn either into a partial result.
    """
    if len(d) < 0x48:
        raise ValueError(f'{label}: {len(d)} bytes, shorter than an SPCH header')
    if d[:4] != HCPS:
        raise Unsupported(f'{label}: not an SPCH container (first four bytes {d[:4]!r})')
    base = 0
    version = _u32(d, 0x04)
    slct_tab, slct_cnt = _pair(d, 0x08, base)   # the Slct offset table, file-absolute
    slct_sec, slct_sec_len = _pair(d, 0x18, base)   # every section offset is file-absolute
    xv4, xv4_len = _pair(d, 0x20, base)
    unk, unk_len = _pair(d, 0x28, base)
    for what, o, n in (('slct_section', slct_sec, slct_sec_len), ('xv4_section', xv4, xv4_len), ('unk_section', unk, unk_len)):
        if o < 0x48 or o + n > len(d):
            raise ValueError(f'{label}: {what} {o:#x}+{n:#x} lies outside the {len(d):#x}-byte file')
    slct_bytes, xv4_bytes, unk_bytes = d[slct_sec:slct_sec + slct_sec_len], d[xv4:xv4 + xv4_len], d[unk:unk + unk_len]
    if slct_tab + 8 * slct_cnt > len(d):
        raise ValueError(f'{label}: {slct_cnt} Slct offsets at {slct_tab:#x} run past the file')

    out = []
    for si in range(slct_cnt):
        # The table holds offsets into slct_section
        s_rel = _u32(d, slct_tab + 8 * si)
        if s_rel >= slct_sec_len:
            raise ValueError(f'{label}: Slct {si} offset {s_rel:#x} is past slct_section ({slct_sec_len:#x})')
        s_at = slct_bytes[s_rel:]
        if s_at[:4] != SLCT:
            raise ValueError(f'{label}: Slct {si} at slct_section+{s_rel:#x} has magic {s_at[:4]!r}, not SLCT')
        if len(s_at) < 0x44:
            raise ValueError(f'{label}: Slct {si} is truncated')
        # Slct: +0x0c unk_strings offset, +0x10 programs count, +0x14 programs offset (both relative to the Slct).
        prog_cnt = _u32(s_at, 0x10)
        prog_off = _u32(s_at, 0x14)
        # Slct tail: unk_item_offset, unk_item_total_size, xv4_offset, xv4_total_size (u32 each)
        item_off, item_total = struct.unpack_from('<II', s_at, 0x28)
        xoff, xtotal = struct.unpack_from('<II', s_at, 0x30)
        if xoff + xtotal > len(xv4_bytes):
            raise ValueError(f'{label} slct{si}: xv4 window {xoff:#x}+{xtotal:#x} outside xv4_section ({len(xv4_bytes):#x})')
        if item_off + item_total > len(unk_bytes):
            raise ValueError(f'{label} slct{si}: unk window {item_off:#x}+{item_total:#x} outside unk_section ({len(unk_bytes):#x})')
        xcur, ucur = xoff, item_off
        for pi in range(prog_cnt):
            # program records are relative to the Slct itself; their {offset,length} is relative to the Slct too
            nvsd = _read_nvsd(d, slct_sec + s_rel + prog_off + 8 * pi, slct_sec + s_rel, label, si, pi)
            sizes = _program_sizes(nvsd, label, si, pi)
            vx, fx, vu, fu = sizes
            # xv4 side: vertex then fragment
            xv4_walk = (xcur, xcur + vx, xcur + vx + fx)
            # unk side: vertex record then fragment record, as xc3_lib's read_fragment_unk_item walks it
            unk_walk = (ucur, ucur + vu, ucur + vu + fu)
            for slot, st, code_span, ctl_span in (('vertex', 'vs', (xv4_walk[0], xv4_walk[1]), (unk_walk[0], unk_walk[1])),
                                                  ('fragment', 'ps', (xv4_walk[1], xv4_walk[2]), (unk_walk[1], unk_walk[2]))):
                ncode, nctl = code_span[1] - code_span[0], ctl_span[1] - ctl_span[0]
                if ncode == 0 and nctl == 0:
                    continue   # the stage is absent, which the descriptor says explicitly
                if ncode == 0 or nctl == 0:
                    raise Unsupported(f'{label} slct{si} program{pi} {st}: code {ncode} bytes but control {nctl} bytes: a stage with one side missing')
                if code_span[0] + ncode > xoff + xtotal or ctl_span[0] + nctl > item_off + item_total:
                    raise ValueError(f'{label} slct{si} program{pi} {slot}: window runs past its Slct (code {code_span}, ctl {ctl_span})')
                code = xv4_bytes[code_span[0]:code_span[1]]
                # The slot spans what the walk consumes, which may include padding after the record: the record
                # itself is as long as its own header says (control +0x20), and it must start with the magic.
                raw = unk_bytes[ctl_span[0]:ctl_span[1]]
                ctl = _record(raw, label, si, pi, slot)
                # The descriptor only fixes the span; the stage itself is what the code area says. A compute
                # area in either slot is compute, and a graphics area carries its own stage in the SPH bits.
                # Pairing is still structural: the span comes from the descriptor, never from the stage.
                st = _stage_of(code, slot, label, si, pi)
                if want is None or st in want:
                    out.append((f'{label}#SPCH#{si}:{pi}:{st}@xv4+{code_span[0]:#x}/unk+{ctl_span[0]:#x}', st, ctl, code))
            xcur += vx + fx
            ucur += vu + fu
        if xcur != xoff + xtotal:
            raise ValueError(f'{label} slct{si}: the xv4 walk ended at {xcur:#x}, but xv4_offset+xv4_total_size is {xoff + xtotal:#x}')
        if ucur != item_off + item_total:
            raise ValueError(f'{label} slct{si}: the unk walk ended at {ucur:#x}, but unk_item_offset+unk_item_total_size is {item_off + item_total:#x}')
    if not out:
        raise Unsupported(f'{label}: the container holds no vertex or pixel stage')
    return out


def _read_nvsd(d, at, base, label, si, pi):
    """The ShaderProgram record at file offset `at` is a {offset,length} pair; its bytes are an NVSD.

    Like the Slct's own offsets, the ShaderProgram offset is relative to slct_section, not to the file.
    """
    if at + 8 > len(d):
        raise ValueError(f'{label} slct{si}: program {pi} record at {at:#x} lies outside the file')
    off, cnt = struct.unpack_from('<II', d, at)
    start = base + off
    if start + cnt > len(d):
        raise ValueError(f'{label} slct{si} program{pi}: program_data {start:#x}+{cnt:#x} outside the file')
    return d[start:start + cnt]


def _program_sizes(nvsd, label, si, pi):
    """NVSD → (vertex_xv4, fragment_xv4, vertex_unk, fragment_unk).

    xc3_lib reads `nvsd_shaders.last()`; only the layout that use is known to be right for is accepted here:
    one entry with data at the end, every earlier entry all zero. Several entries with data, or an unknown
    shape, is unsupported: a variant must not be dropped silently.
    """
    if len(nvsd) < 0x20:
        raise Unsupported(f'{label} slct{si} program{pi}: NVSD is {len(nvsd)} bytes, too short to hold a header')
    # unks2[6] occupies 0x18, then {offset, count} (parse_offset32_count32, offset first). Entries are 5 u32:
    # unk6, vertex_xv4_size, fragment_xv4_size, vertex_unk_item_size, fragment_unk_item_size.
    off, cnt = _pair(nvsd, 0x18, 0)
    if cnt == 0:
        raise Unsupported(f'{label} slct{si} program{pi}: nvsd_shaders is empty')
    if off < 0x20:
        raise Unsupported(f'{label} slct{si} program{pi}: nvsd_shaders offset {off:#x} overlaps the NVSD header')
    if off + 0x14 * cnt > len(nvsd):
        raise Unsupported(f'{label} slct{si} program{pi}: nvsd_shaders {off:#x}+{0x14 * cnt:#x} outside the {len(nvsd):#x}-byte NVSD')
    entries = [struct.unpack_from('<5I', nvsd, off + 0x14 * k)[1:] for k in range(cnt)]
    # This engine writes one entry per program in a fixed shape: every entry before the last has no vertex
    # stage at all (vertex_xv4_size and vertex_unk_item_size zero), and the last carries the vertex / fragment
    # pair the Slct's walk consumes. A leading entry that does carry a vertex stage is a variant this parser
    # does not understand, and dropping it silently would lose a shader, so the file is refused instead.
    for k, (vx, _fx, vu, _fu) in enumerate(entries[:-1]):
        if vx or vu:
            raise Unsupported(f'{label} slct{si} program{pi}: nvsd_shaders entry {k} of {cnt} carries a vertex stage '
                              f'(vertex_xv4_size={vx}, vertex_unk_item_size={vu}); variants are not supported')
    last = entries[-1]
    if not any(last):
        raise Unsupported(f'{label} slct{si} program{pi}: the last nvsd_shaders entry of {cnt} carries no sizes')
    return entries[-1]


def _record(raw, label, si, pi, slot):
    """Trim a slot span down to the control record it starts with (control +0x20 holds its own length)."""
    if len(raw) < 0x704:
        raise ValueError(f'{label} slct{si} program{pi} {slot}: control span is {len(raw)} bytes, shorter than a record')
    if raw[:4] != CTL_MAGIC:
        raise Unsupported(f'{label} slct{si} program{pi} {slot}: control record starts with {raw[:4].hex()}, not the control magic')
    n = _u32(raw, 0x20)
    if not 0x760 <= n < 0x880:
        n = 0x880
    if n > len(raw):
        raise ValueError(f'{label} slct{si} program{pi} {slot}: control declares {n:#x} bytes but its slot holds {len(raw):#x}')
    return raw[:n]


def _stage_of(code, slot, label, si, pi):
    """The stage of the code area in `slot`: compute by its magic, otherwise the SPH header's stage bits."""
    if len(code) < 0x34:
        raise ValueError(f'{label} slct{si} program{pi} {slot}: code area is {len(code):#x} bytes, too short for an SPH header')
    if code[:4] == CS_MAGIC:
        return 'cs'
    if code[:4] != GFX_MAGIC:
        raise Unsupported(f'{label} slct{si} program{pi} {slot}: code area magic is {code[:4].hex()}, neither graphics nor compute')
    bit = (_u32(code, 0x30) >> 10) & 0xf
    st = _SPH_STAGE.get(bit)
    if st is None:
        raise Unsupported(f'{label} slct{si} program{pi} {slot}: SPH stage bits {bit} are not a known stage')
    return st
