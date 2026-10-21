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
# Association is purely structural and driven by the prefix chain the descriptor itself states. A Slct's
# programs are laid out back to back, so each program has its own code / control base; within one program the
# nvsd_shaders entries are a prefix chain, each contributing one stage, and the last entry's vx / vu are the
# accumulated totals. Nothing is matched by code length or found by scanning for a magic. Those bases are the
# whole point: a Slct base used for every program silently reads the first program's bytes for all of them.
#
# Supported: version 1010 and the layout above. An entry that does not continue the chain, a stage missing its
# code or control half, a control record whose stated length or +0x704 disagrees with the entry's span, and any
# window leaving its section are refused rather than guessed around.

import struct

HCPS = b'HCPS'
SLCT = b'SLCT'
# SPH stage bits (word at code +0x30, bits 10..13), the same mapping shader_split.SPH_STAGE uses
_SPH_STAGE = {1: 'vs', 2: 'hs', 3: 'ds', 4: 'gs', 5: 'ps'}
GFX_MAGIC, CS_MAGIC = bytes.fromhex('78563412'), bytes.fromhex('79563412')
CTL_MAGIC = bytes.fromhex('34127698')
SUPPORTED_VERSION = 1010   # the only version seen in the verified containers; the layout below is read for it


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
    # Every container verified so far (the five global .wishp of the Xenoblade 3 v2.2.0 card) is version 1010,
    # and the field layout below is read for that version only. A different version is refused rather than
    # parsed with this layout.
    if version != SUPPORTED_VERSION:
        raise Unsupported(f'{label}: SPCH version {version} ({version:#x}) is not the supported {SUPPORTED_VERSION}')
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
        # The program table is part of the Slct, which lives inside slct_section: it must fit there, or the
        # descriptor could borrow the slct_section from beyond this Slct's own section.
        if s_rel + prog_off + 8 * prog_cnt > slct_sec_len:
            raise ValueError(f'{label} slct{si}: program table {prog_off:#x}+{8 * prog_cnt:#x} at slct_section+{s_rel:#x} '
                             f'runs past slct_section ({slct_sec_len:#x})')
        # Slct tail: unk_item_offset, unk_item_total_size, xv4_offset, xv4_total_size (u32 each)
        item_off, item_total = struct.unpack_from('<II', s_at, 0x28)
        xoff, xtotal = struct.unpack_from('<II', s_at, 0x30)
        if xoff + xtotal > len(xv4_bytes):
            raise ValueError(f'{label} slct{si}: xv4 window {xoff:#x}+{xtotal:#x} outside xv4_section ({len(xv4_bytes):#x})')
        if item_off + item_total > len(unk_bytes):
            raise ValueError(f'{label} slct{si}: unk window {item_off:#x}+{item_total:#x} outside unk_section ({len(unk_bytes):#x})')
        # One Slct: each program's storage starts where the previous program ended, so the two cursors below
        # are per-Slct program bases, not the Slct base itself. Using the Slct base for every program reads the
        # first program's bytes for all of them.
        code_base, ctl_base = xoff, item_off
        for pi in range(prog_cnt):
            slct_start = slct_sec + s_rel
            nvsd = _read_nvsd(d, slct_start + prog_off + 8 * pi, slct_start,
                              slct_sec + slct_sec_len, label, si, pi)
            entries = _entries(nvsd, label, si, pi)
            # The entries of one program form a prefix chain: entry i starts where entries 0..i-1 ended, so
            # each entry contributes exactly one new stage and the last entry's vx/vu are running totals.
            code_prefix = ctl_prefix = 0
            for ei, (vx, fx, vu, fu) in enumerate(entries):
                if vx != code_prefix or vu != ctl_prefix:
                    raise Unsupported(f'{label} slct{si} program{pi} entry{ei}: the descriptor says vx={vx} vu={vu}, '
                                      f'but the entries before it end at code {code_prefix} control {ctl_prefix}; '
                                      f'this is not the prefix layout this parser reads')
                if not fx or not fu:
                    raise Unsupported(f'{label} slct{si} program{pi} entry{ei}: code {fx} bytes, control {fu} bytes; '
                                      f'a stage without both halves is not supported')
                code_span = (code_base + vx, code_base + vx + fx)
                ctl_span = (ctl_base + vu, ctl_base + vu + fu)
                if code_span[1] > xoff + xtotal:
                    raise ValueError(f'{label} slct{si} program{pi} entry{ei}: code {code_span[0]:#x}+{fx:#x} '
                                     f'runs past the Slct xv4 window ({xoff + xtotal:#x})')
                if ctl_span[1] > item_off + item_total:
                    raise ValueError(f'{label} slct{si} program{pi} entry{ei}: control {ctl_span[0]:#x}+{fu:#x} '
                                     f'runs past the Slct unk window ({item_off + item_total:#x})')
                code = xv4_bytes[code_span[0]:code_span[1]]
                raw = unk_bytes[ctl_span[0]:ctl_span[1]]
                ctl = _record(raw, label, si, pi, ei)
                # The record states the length of the code object it belongs to; it must be this entry's span.
                stated = _u32(ctl, 0x704)
                if stated != fx:
                    raise Unsupported(f'{label} slct{si} program{pi} entry{ei}: the control record says the code '
                                      f'is {stated:#x} bytes, but the entry spans {fx:#x}')
                st = _stage_of(code, ei, label, si, pi)
                where = f'{label}#SPCH#{si}:{pi}:{ei}:{st}@xv4+{code_span[0]:#x}/unk+{ctl_span[0]:#x}'
                if want is None or st in want:
                    out.append((where, st, ctl, code))
                code_prefix += fx
                ctl_prefix += fu
            last = entries[-1]
            # The program ends where its own descriptor says it does; anything else is an inconsistency.
            if code_prefix != last[0] + last[1]:
                raise Unsupported(f'{label} slct{si} program{pi}: the entries end at code {code_prefix}, '
                                  f'but the last entry declares {last[0] + last[1]}')
            if ctl_prefix != last[2] + last[3]:
                raise Unsupported(f'{label} slct{si} program{pi}: the entries end at control {ctl_prefix}, '
                                  f'but the last entry declares {last[2] + last[3]}')
            code_base += code_prefix
            ctl_base += ctl_prefix
        # The Slct's own totals must be exactly the sum of its programs.
        if code_base != xoff + xtotal:
            raise ValueError(f'{label} slct{si}: the programs end at xv4 {code_base:#x}, '
                             f'but xv4_offset+xv4_total_size is {xoff + xtotal:#x}')
        if ctl_base != item_off + item_total:
            raise ValueError(f'{label} slct{si}: the programs end at unk {ctl_base:#x}, '
                             f'but unk_item_offset+unk_item_total_size is {item_off + item_total:#x}')
    if not out:
        raise Unsupported(f'{label}: the container holds no vertex or pixel stage')
    return out


def _read_nvsd(d, at, relative_base, section_end, label, si, pi):
    """The ShaderProgram record at file offset `at` names an NVSD as {offset,length}.

    Two different things, deliberately separate:
      * `relative_base` is where the ShaderProgram offset is measured from. xc3_lib's SlctOffset::read_slct
        slices slct_section at the Slct's offset and parses a Cursor over that slice (spch.rs), and Slct's
        `programs` uses parse_count32_offset32 with no `args` override, so parse_vec seeks to
        offset + FilePtrArgs::default().offset = the raw offset. The zero point is therefore the **Slct start**,
        not the start of slct_section.
      * `section_end` is the last byte the data may occupy. The Slct, its program table and the NVSD the record
        names all live inside slct_section, so borrowing bytes from a following section is refused.
    Using one value for both is what broke this: a section-relative base reads the wrong bytes for any Slct
    that does not start at the beginning of slct_section.
    """
    if at + 8 > section_end:
        raise ValueError(f'{label} slct{si}: program {pi} record at {at:#x} lies past slct_section (ends {section_end:#x})')
    off, cnt = struct.unpack_from('<II', d, at)
    start = relative_base + off
    if start < relative_base or start + cnt > section_end:
        raise ValueError(f'{label} slct{si} program{pi}: program_data {start:#x}+{cnt:#x} runs outside slct_section '
                         f'[{relative_base:#x}, {section_end:#x})')
    return d[start:start + cnt]


def _entries(nvsd, label, si, pi):
    """NVSD → [(vertex_xv4_size, fragment_xv4_size, vertex_unk_item_size, fragment_unk_item_size)] in order.

    Every entry contributes one stage to the program's prefix chain, so all of them are returned. The library
    reads `nvsd_shaders.last()` and asks in a TODO why only the last set is used; on the five containers
    verified here the entries are a prefix chain, and refusing to read the earlier ones is what made them
    unreadable.
    """
    if len(nvsd) < 0x20:
        raise Unsupported(f'{label} slct{si} program{pi}: NVSD is {len(nvsd)} bytes, too short to hold a header')
    off, cnt = _pair(nvsd, 0x18, 0)
    if cnt == 0:
        raise Unsupported(f'{label} slct{si} program{pi}: nvsd_shaders is empty')
    if off < 0x20:
        raise Unsupported(f'{label} slct{si} program{pi}: nvsd_shaders offset {off:#x} overlaps the NVSD header')
    if off + 0x14 * cnt > len(nvsd):
        raise Unsupported(f'{label} slct{si} program{pi}: nvsd_shaders {off:#x}+{0x14 * cnt:#x} '
                          f'outside the {len(nvsd):#x}-byte NVSD')
    # Each entry is five u32: unk6, then the four sizes.
    return [struct.unpack_from('<5I', nvsd, off + 0x14 * k)[1:] for k in range(cnt)]


def _record(raw, label, si, pi, ei):
    """The control record filling this entry's whole span; it must state the same length as the span.

    No trimming and no exception for padding: every entry verified here has its control record filling the
    span exactly, so a shorter or longer record means the layout is not the one this parser reads.
    """
    if len(raw) < 0x708:
        raise ValueError(f'{label} slct{si} program{pi} entry{ei}: control span is {len(raw)} bytes, '
                         f'shorter than the +0x704 field')
    if raw[:4] != CTL_MAGIC:
        raise Unsupported(f'{label} slct{si} program{pi} entry{ei}: control record starts with {raw[:4].hex()}, '
                          f'not the control magic')
    own = _u32(raw, 0x20)
    if own != len(raw):
        raise Unsupported(f'{label} slct{si} program{pi} entry{ei}: the control record declares {own:#x} bytes '
                          f'but its span is {len(raw):#x}')
    return raw


def _stage_of(code, ei, label, si, pi):
    """The stage of this entry's code area: compute by its magic, otherwise the SPH header's stage bits."""
    if len(code) < 0x34:
        raise ValueError(f'{label} slct{si} program{pi} entry{ei}: code area is {len(code):#x} bytes, too short for an SPH header')
    if code[:4] == CS_MAGIC:
        return 'cs'
    if code[:4] != GFX_MAGIC:
        raise Unsupported(f'{label} slct{si} program{pi} entry{ei}: code area magic is {code[:4].hex()}, neither graphics nor compute')
    bit = (_u32(code, 0x30) >> 10) & 0xf
    st = _SPH_STAGE.get(bit)
    if st is None:
        raise Unsupported(f'{label} slct{si} program{pi} entry{ei}: SPH stage bits {bit} are not a known stage')
    return st
