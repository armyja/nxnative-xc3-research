#!/usr/bin/env python3
"""Extract the real replay switch cases for the SSBO observation from nvn_mtl.m and compile a stub harness.

The case bodies are copied from the production file at generation time (not hand-written), so a change in the real
switch text changes what is compiled here. Scope: only the label chain and the two draw cases; this is a wiring check,
not a renderer test.
"""
import os, re, subprocess, sys
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'nvn_mtl.m')
lines = open(SRC).read().splitlines()

def find(pred, what):
    for i, l in enumerate(lines):
        if pred(l): return i
    sys.exit(f'missing: {what}')

# Only inside the real replay entry: state_op has its own OP_* labels earlier in the file.
start = find(lambda l: l.startswith('void mtl_exec(const uint8_t *p) {'), 'mtl_exec')
gi = next(i for i in range(start, len(lines)) if 'case OP_BIND_UBO:' in lines[i] and 'case OP_BIND_SSBO' not in lines[i])
gend = gi
while 'state_op(h.op, a); break;' not in lines[gend]: gend += 1
bind = next(i for i in range(start, len(lines)) if lines[i].strip().startswith('case OP_BIND_SSBO:'))
draw = next(i for i in range(start, len(lines)) if lines[i].strip().startswith('case OP_DRAW:'))
drawi = next(i for i in range(start, len(lines)) if lines[i].strip().startswith('case OP_DRAW_IDX:'))
sel = sorted(set([bind, draw, drawi] + list(range(gi, gend + 1))))
print('extracted lines:', ', '.join(str(i + 1) for i in sel))
body = '\n'.join(lines[i] for i in sel)

harness = r'''
#include <stdio.h>
#include <stdint.h>
#include <string.h>
typedef struct { unsigned op, size; } op_hdr;
enum { OP_BIND_UBO = 10, OP_BIND_TEX, OP_BIND_SAMP, OP_STENCIL, OP_SSBO_PROBE, OP_DRAW, OP_DRAW_IDX, OP_BIND_SSBO, OP_POLY_OFFSET, OP_VIEWPORTS, OP_DEPTH_RANGE, OP_DEPTH_CLAMP, OP_BLEND_COLOR, OP_COPY_STRIDE, OP_SCISSOR, OP_BIND_PROGRAM, OP_BIND_STATE, OP_BIND_VATTR, OP_BIND_VSTREAM, OP_BIND_VBUF };
static int state_calls, state_op_seen, state_wrong_op, bind_calls, obs_calls, draw_calls, skip_calls, img_calls, imgskip_calls;
static int order_ok = 1, obs_then_draw = -1;
static struct { int skips; } g_so;
static const uint8_t *p; static void *a; static const uint8_t *g_exec_next; static int g_rc_skip;
static int state_op(unsigned op, const void *x) { (void)x; state_calls++; state_op_seen = (int)op; return 0; }
static void draw(const void *x, const void *y) { (void)x; (void)y; draw_calls++; obs_then_draw = obs_calls; }
static void imgdiag_draw(void) { img_calls++; }
static void imgdiag_draw_skipped(void) { imgskip_calls++; }
static void imgdiag_bind(const void *x) { (void)x; }
static void ssbo_obs_draw(void) { if (draw_calls) order_ok = 0; obs_calls++; }
static void ssbo_obs_bind(const void *x) { (void)x; bind_calls++; }

static void run(unsigned op) {
    op_hdr h = { op, 1 }; const uint8_t *pp = (const uint8_t *)&h; p = pp; a = (void *)(pp + 8);
    state_calls = bind_calls = obs_calls = draw_calls = skip_calls = img_calls = imgskip_calls = 0;
    state_op_seen = -1; state_wrong_op = 0; obs_then_draw = -1; order_ok = 1;
    switch (h.op) {
BODY
    default: break;
    }
}

/* predictor simulation: state_op called by lookahead must not produce observation events */
static void scan(void) { state_calls = bind_calls = obs_calls = draw_calls = 0; state_op(OP_SSBO_PROBE, a); }

static int fails;
#define CK(c, m) do { if (!(c)) { printf("FAIL %s\n", m); fails++; } else printf("ok   %s\n", m); } while (0)
int main(void) {
    run(OP_BIND_SSBO);
    CK(state_calls == 1 && state_op_seen == OP_BIND_SSBO, "BIND_SSBO: state_op once with the original opcode");
    CK(bind_calls == 1, "BIND_SSBO: bind diagnostic once");
    CK(draw_calls == 0 && obs_calls == 0, "BIND_SSBO: no draw or snapshot");
    run(OP_BIND_UBO); CK(state_calls == 1 && state_op_seen == OP_BIND_UBO && bind_calls == 0, "grouped UBO: state_op once, no bind diagnostic");
    run(OP_BIND_TEX); CK(state_calls == 1 && state_op_seen == OP_BIND_TEX && bind_calls == 0, "grouped TEX: state_op once, no bind diagnostic");
    run(OP_BIND_SAMP); CK(state_calls == 1 && state_op_seen == OP_BIND_SAMP && bind_calls == 0, "grouped SAMP: state_op once, no bind diagnostic");
    run(OP_STENCIL); CK(state_calls == 1 && state_op_seen == OP_STENCIL && bind_calls == 0, "grouped STENCIL: state_op once, no bind diagnostic");
    g_rc_skip = 0; run(OP_DRAW);
    CK(draw_calls == 1 && obs_calls == 1 && order_ok && obs_then_draw == 1, "DRAW: snapshot before draw, once");
    g_rc_skip = 0; run(OP_DRAW_IDX);
    CK(draw_calls == 1 && obs_calls == 1 && order_ok, "DRAW_IDX: snapshot before draw, once");
    g_rc_skip = 1; g_so.skips = 0; run(OP_DRAW);
    CK(draw_calls == 0 && obs_calls == 0 && g_so.skips == 1, "known skip: no draw, no snapshot, counter increments");
    g_rc_skip = 1; g_so.skips = 0; run(OP_DRAW_IDX);
    CK(draw_calls == 0 && obs_calls == 0 && g_so.skips == 1, "known skip (indexed): counter increments, still no draw");
    scan(); CK(bind_calls == 0 && obs_calls == 0 && draw_calls == 0, "predictor state_op: no observation events");
    printf("fails: %s\n", fails ? "yes" : "none");
    return fails ? 1 : 0;
}
'''
harness = harness.replace('BODY', body)
open('/tmp/switch_wiring.c', 'w').write(harness)
r = subprocess.run(['clang', '-O1', '-Wall', '-Wextra', '-o', '/tmp/switch_wiring', '/tmp/switch_wiring.c'], capture_output=True, text=True)
print(r.stderr[-800:] if r.returncode else 'compiled')
sys.exit(r.returncode)
