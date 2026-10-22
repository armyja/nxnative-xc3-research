// V002 supplemental independent coverage (V002.F3): control-flow paths of the shared
// fz_cursor (nested CALL/return, JUMP, submission remainder) across a TF boundary.
// fz_next/hoist_* are extracted verbatim from the frozen v002 snapshot; the harness only
// builds streams and drives the real cursor.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stddef.h>
#include <stdarg.h>

#include "nvn_tf_diag.h"
#include "ops.h"

static int g_mode;
int dm_tf_diag_get_mode(void) { return g_mode; }
static const void *g_rest[64]; static int g_nrest;

#include "a2b_init.inc"
#include "a2b_hoist.inc"
#include "a2b_fz.inc"

static int g_pass, g_fail;
static void ck(int cond, const char *id, const char *name, const char *fmt, ...) {
    char d[500] = "";
    if (fmt) { va_list ap; va_start(ap, fmt); vsnprintf(d, sizeof d, fmt, ap); va_end(ap); }
    if (cond) { g_pass++; printf("PASS %-4s %s\n", id, name); }
    else { g_fail++; printf("FAIL %-4s %s | %s\n", id, name, d); }
}

typedef struct { uint8_t b[1024] __attribute__((aligned(8))); size_t n; } arena;
static void s_reset(arena *a) { memset(a, 0, sizeof *a); }
static uint8_t *s_op(arena *a, uint32_t op, size_t payload) {
    size_t sz = (8 + payload + 7) & ~(size_t)7;
    uint8_t *p = a->b + a->n; a->n += sz;
    ((op_hdr *)p)->op = op; ((op_hdr *)p)->size = (uint32_t)sz;
    memset(p + 8, 0, sz - 8);
    return p + 8;
}
static void s_tf(arena *a) { p_tf_diag *e = (p_tf_diag *)s_op(a, OP_TF_DIAG, sizeof *e); e->kind = TF_DIAG_KIND_BEGIN; }
static void s_call(arena *a, const uint8_t *target) { uint8_t *p = s_op(a, OP_CALL, 8); const uint8_t *t = target; memcpy(p, &t, 8); }
static void s_jump(arena *a, const uint8_t *target) { uint8_t *p = s_op(a, OP_JUMP, 8); const uint8_t *t = target; memcpy(p, &t, 8); }
static void s_end(arena *a) { s_op(a, OP_END, 0); }
static void on(int m) { g_mode = m; g_tf_diag_seen = 0; g_nrest = 0; g_hoist_n = 0; }

int main(void) {
    setvbuf(stdout, NULL, _IONBF, 0);
    static arena P, CH, REST;
    const uint8_t *q; op_hdr h; const void *a;

    // 1. TF inside a nested CALL: the cursor enters the sub-list and stops at the TF.
    on(TF_DIAG_MODE_ON);
    s_reset(&CH); s_op(&CH, OP_DRAW, 0); s_tf(&CH); s_op(&CH, OP_DRAW, 0); s_end(&CH);
    s_reset(&P); s_call(&P, CH.b); s_op(&P, OP_DRAW, 0); s_end(&P);
    fz_cursor c = (fz_cursor){.p = P.b};
    int n = 0, ok = 1;
    while (fz_next(&c, &q, &h, &a)) { n++; if (n == 1 && h.op != OP_DRAW) ok = 0; if (n > 8) break; }
    ck(n == 1 && ok && c.bad == 1, "B02s", "nested CALL: cursor stops at a TF inside the sub-list", "n=%d bad=%d", n, c.bad);

    // 2. Return from a clean sub-list continues in the caller, then stops at the caller's TF.
    on(TF_DIAG_MODE_ON);
    s_reset(&CH); s_op(&CH, OP_DRAW, 0); s_end(&CH);
    s_reset(&P); s_call(&P, CH.b); s_tf(&P); s_op(&P, OP_DRAW, 0); s_end(&P);
    c = (fz_cursor){.p = P.b};
    int first = fz_next(&c, &q, &h, &a);          // draw in the child
    int second = fz_next(&c, &q, &h, &a);         // caller's TF -> boundary
    ck(first == 1 && h.op == OP_DRAW && second == 0 && c.bad == 1,
       "B02s", "CALL/return: cursor returns to the caller and stops at its TF", "first=%d second=%d bad=%d", first, second, c.bad);

    // 3. JUMP landing on a TF: cursor stops at the target.
    on(TF_DIAG_MODE_ON);
    s_reset(&P);
    { const uint8_t *target = P.b + 16;          // first byte after the 16-byte JUMP record
      s_jump(&P, target); }
    s_tf(&P); s_op(&P, OP_DRAW, 0); s_end(&P);
    c = (fz_cursor){.p = P.b};
    int jumped = fz_next(&c, &q, &h, &a);
    ck(jumped == 0 && c.bad == 1, "B02s", "JUMP onto a TF: boundary honoured after the jump", "r=%d bad=%d", jumped, c.bad);

    // 4. Submission remainder (g_rest) containing a TF: boundary honoured after OP_END.
    on(TF_DIAG_MODE_ON);
    s_reset(&REST); s_op(&REST, OP_DRAW, 0); s_tf(&REST); s_end(&REST);
    s_reset(&P); s_end(&P);
    g_rest[0] = REST.b; g_nrest = 1;
    c = (fz_cursor){.p = P.b};
    int r1 = fz_next(&c, &q, &h, &a);             // draw from the remainder
    int r2 = fz_next(&c, &q, &h, &a);             // remainder's TF -> boundary
    ck(r1 == 1 && h.op == OP_DRAW && r2 == 0 && c.bad == 1,
       "B02s", "remainder handles: boundary honoured in g_rest traversal", "r1=%d r2=%d bad=%d", r1, r2, c.bad);

    // 5. A TF listed in the hoist skip list must still stop the cursor (no skip).
    on(TF_DIAG_MODE_ON);
    s_reset(&P); s_op(&P, OP_DRAW, 0); uint8_t *tfp = (uint8_t *)P.b + P.n; s_tf(&P); s_end(&P);
    g_hoist_skip[0] = tfp; g_hoist_n = 1;
    c = (fz_cursor){.p = P.b};
    int h1 = fz_next(&c, &q, &h, &a), h2 = fz_next(&c, &q, &h, &a);
    ck(h1 == 1 && h2 == 0 && c.bad == 1, "B02s", "hoist skip list cannot make the cursor jump over TF", "h1=%d h2=%d bad=%d", h1, h2, c.bad);

    // 6. OFF control on the same nested stream: no boundary, all ops visible.
    on(TF_DIAG_MODE_OFF);
    s_reset(&CH); s_op(&CH, OP_DRAW, 0); s_tf(&CH); s_op(&CH, OP_DRAW, 0); s_end(&CH);
    s_reset(&P); s_call(&P, CH.b); s_end(&P);
    c = (fz_cursor){.p = P.b};
    int off_n = 0, off_tf = 0;
    while (fz_next(&c, &q, &h, &a) && off_n < 16) { off_n++; if (h.op == OP_TF_DIAG) off_tf = 1; }
    ck(off_n == 3 && off_tf == 1 && c.bad == 0, "B02s", "OFF control: no boundary in the nested stream", "n=%d tf=%d bad=%d", off_n, off_tf, c.bad);

    printf("RESULT pass=%d fail=%d\n", g_pass, g_fail);
    return g_fail ? 1 : 0;
}
