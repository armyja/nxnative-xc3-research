#!/usr/bin/env python3
"""Extract the real replay switch adjacency and verify the SSBO/IMG/draw wiring by compiling and running it.

The block is copied from nvn_mtl.m at generation time: DRAW, DRAW_IDX, the independent IMG/SSBO cases and the whole
grouped label chain (SCISSOR ... COPY_STRIDE). A second, mutated build moves the SSBO case into the middle of the group;
that build must fail, which proves the check catches fallthrough instead of only looking right statically.
Scope: call order and label routing only (stubs); the inertness of the diagnostic when off is covered by the extracted
wrapper test, not here.
"""
import os, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '..', 'nvn_mtl.m')
lines = open(SRC).read().splitlines()
start = next(i for i, l in enumerate(lines) if l.startswith('void mtl_exec(const uint8_t *p) {'))
first = next(i for i in range(start, len(lines)) if lines[i].strip().startswith('case OP_DRAW:'))
# the contiguous block ends at the first state_op...break; after the grouped labels
j = next(i for i in range(first, len(lines)) if lines[i].strip().startswith('state_op(h.op, a); break;'))
while 'break;' not in lines[j]: j += 1
block = [l for l in lines[first:j + 1]]
print('extracted lines %d-%d' % (first + 1, j + 1))

OPS = ['OP_SCISSOR', 'OP_BIND_PROGRAM', 'OP_BIND_STATE', 'OP_BIND_VATTR', 'OP_BIND_VSTREAM', 'OP_BIND_VBUF',
       'OP_BIND_UBO', 'OP_BIND_TEX', 'OP_BIND_SAMP', 'OP_STENCIL', 'OP_POLY_OFFSET', 'OP_VIEWPORTS',
       'OP_DEPTH_RANGE', 'OP_DEPTH_CLAMP', 'OP_BLEND_COLOR', 'OP_COPY_STRIDE', 'OP_DRAW', 'OP_DRAW_IDX',
       'OP_BIND_IMG', 'OP_BIND_SSBO']

stubs = r'''
#include <stdio.h>
#include <stdint.h>
#include <string.h>
typedef struct { unsigned op, size; } op_hdr;
enum { OPS_HERE };
static int state_calls, state_op_seen, bind_calls, img_bind_calls, obs_calls, draw_calls, skip_calls, imgskip_calls;
static int order_bad;
static struct { int skips; } g_so;
static const uint8_t *p; static void *a; static const uint8_t *g_exec_next; static int g_rc_skip;
static int state_op(unsigned op, const void *x) { (void)x; state_calls++; state_op_seen = (int)op; return 0; }
static void draw(const void *x, const void *y) { (void)x; (void)y; if (!obs_calls) order_bad = 1; draw_calls++; }
static void imgdiag_draw(void) {}
static void imgdiag_draw_skipped(void) { imgskip_calls++; }
static void imgdiag_bind(const void *x) { (void)x; img_bind_calls++; }
static void ssbo_obs_draw(void) { obs_calls++; }
static void ssbo_obs_draw_skipped(void) { skip_calls++; }
static void ssbo_obs_bind(const void *x) { (void)x; bind_calls++; }
static void reset(void) { state_calls = bind_calls = img_bind_calls = obs_calls = draw_calls = skip_calls = imgskip_calls = 0; state_op_seen = -1; order_bad = 0; }
static void run(unsigned op) {
    reset();
    op_hdr h = { op, 1 }; const uint8_t *q = (const uint8_t *)&h; p = q; a = (void *)(q + 8);
    switch (h.op) {
BODY
    default: break;
    }
}
static int fails;
#define CK(c, m) do { if (!(c)) { printf("FAIL %s\n", m); fails++; } else printf("ok   %s\n", m); } while (0)
int main(void) {
CHECKS_HERE
    printf("fails: %s\n", fails ? "yes" : "none");
    return fails ? 1 : 0;
}
'''

def build(block_lines, tag, outdir):
    body = '\n'.join(block_lines)
    checks = []
    for op in OPS:
        checks.append(f'        run({op});')
        if op in ('OP_DRAW', 'OP_DRAW_IDX'):
            checks.append(f'        CK(state_calls == 0 && draw_calls == 1 && obs_calls == 1 && !order_bad, "{op}: snapshot once before draw, no state_op");')
            continue
        checks.append(f'        CK(state_calls == 1 && state_op_seen == {op}, "{op}: state_op once with its own opcode");')
        if op == 'OP_BIND_SSBO':
            checks.append('        CK(bind_calls == 1 && img_bind_calls == 0 && obs_calls == 0, "BIND_SSBO: only the SSBO bind diagnostic");')
        elif op == 'OP_BIND_IMG':
            checks.append('        CK(img_bind_calls == 1 && bind_calls == 0 && obs_calls == 0, "BIND_IMG: only the imgdiag bind");')
        elif op in ('OP_DRAW', 'OP_DRAW_IDX'):
            checks.append('        CK(obs_calls == 1 && draw_calls == 1 && !order_bad, "%s: snapshot once, before draw");' % op)
        else:
            checks.append('        CK(bind_calls == 0 && img_bind_calls == 0 && obs_calls == 0, "%s: no observation event");' % op)
    checks.append('        g_rc_skip = 1; run(OP_DRAW); CK(skip_calls == 1 && draw_calls == 0 && obs_calls == 0, "DRAW skip: skip hook only, no draw");')
    checks.append('        g_rc_skip = 1; run(OP_DRAW_IDX); CK(skip_calls == 1 && draw_calls == 0 && obs_calls == 0, "DRAW_IDX skip: skip hook only, no draw");')
    checks.append('        g_rc_skip = 0;')
    src = stubs.replace('OPS_HERE', ', '.join('%s = %d' % (o, 100 + i) for i, o in enumerate(OPS))).replace('CHECKS_HERE', '\n'.join(checks)).replace('BODY', body)
    src = src.replace('BODY', body)
    d = os.path.join(outdir, tag); os.makedirs(d, exist_ok=True)
    c = os.path.join(d, 'wiring.c'); open(c, 'w').write(src)
    r = subprocess.run(['clang', '-O1', '-Wall', '-Wextra', '-o', os.path.join(d, 'wiring'), c], capture_output=True, text=True)
    if r.returncode: return r.returncode, None, 'compile failed: ' + r.stderr[-400:], c
    run = subprocess.run([os.path.join(d, 'wiring')], capture_output=True, text=True)
    return 0, run.returncode, run.stdout, c

out = os.environ.get('SSBOOBS_OUT') or tempfile.mkdtemp(prefix='wiring_')
os.makedirs(out, exist_ok=True)
crc, rrc, log, c = build(block, 'normal', out)
print('normal compile_rc=%d run_rc=%s' % (crc, rrc)); print((log or '')[:0]); print(log[-1200:] if log else '')
if crc != 0 or rrc != 0: sys.exit('normal build/run failed')
# Mutation: really MOVE the one independent SSBO case between the group labels (before the shared body).
ssbo_line = next(l for l in block if l.strip().startswith('case OP_BIND_SSBO:'))
mut = [l for l in block if not l.strip().startswith('case OP_BIND_SSBO:')]
gl = next(i for i, l in enumerate(mut) if 'case OP_BIND_STATE:' in l)          # insert after this label line
mut = mut[:gl + 1] + [ssbo_line] + mut[gl + 1:]
# structural check: every opcode label still present, counts unchanged, only the SSBO position differs
import re as _re
def labels(txt):
    return _re.findall(r'case (OP_[A-Z_]+)', '\n'.join(txt))
ln, lm = labels(block), labels(mut)
assert sorted(ln) == sorted(lm), 'mutation changed the label multiset'
assert ln.count('OP_BIND_SSBO') == lm.count('OP_BIND_SSBO') == 1, 'mutation must keep exactly one SSBO case'
assert ln.index('OP_BIND_SSBO') != lm.index('OP_BIND_SSBO'), 'mutation did not move the SSBO case'
print('label multiset unchanged, SSBO moved from label position %d to %d' % (ln.index('OP_BIND_SSBO'), lm.index('OP_BIND_SSBO')))
mcrc, mrrc, mlog, mc = build(mut, 'mutated', out)
open(os.path.join(out, 'mutated_wiring.c'), 'w').write(open(mc).read())
open(os.path.join(out, 'mutated_stdout.txt'), 'w').write(mlog or '')
print('mutated compile_rc=%d run_rc=%s' % (mcrc, mrrc)); print((mlog or '')[-900:])
assert mcrc == 0, 'mutated block must still compile; a compile failure would not test fallthrough'
assert mrrc != 0, 'mutation test did not fail at run time'
assert 'FAIL' in mlog, 'mutation did not fail through a runtime assertion'
assert any(tag in mlog for tag in ('OP_SCISSOR', 'OP_BIND_PROGRAM', 'OP_BIND_STATE')), \
    'mutation failure does not include an upstream group label routing error'
print('out dir:', out)
sys.exit(0)
