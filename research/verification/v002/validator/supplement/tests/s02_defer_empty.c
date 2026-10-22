// V002-S S02: executable fragment of defer_try's empty-pass proof (the inner scan only).
// The loop is extracted verbatim (v002 nvn_mtl.m 5061-5067). Disclosure: the production code
// initialises e/ec from the current op and substitutes `break` (out of the switch) with
// `return empty` here; the loop body itself is unchanged. The rest of defer_try (main scan,
// Q recheck, candidate acceptance) is NOT executed -- see report S02 static part / SKIP.
#include <stdio.h>
#include <stdarg.h>
#include <stdint.h>
#include <string.h>
#include <stddef.h>

#include "nvn_tf_diag.h"
#include "ops.inc"

static int g_mode;
int dm_tf_diag_get_mode(void) { return g_mode; }
#include "a2b_init.inc"

static int g_pass, g_fail;
static void ck(int c, const char *id, const char *name, const char *fmt, ...) {
    char d[400] = ""; if (fmt) { va_list ap; va_start(ap, fmt); vsnprintf(d, sizeof d, fmt, ap); va_end(ap); }
    if (c) { g_pass++; printf("PASS %s %s\n", id, name); } else { g_fail++; printf("FAIL %s %s | %s\n", id, name, d); }
}

static const uint8_t *defer_cont(int *ci) { (void)ci; return NULL; }   // stub: no caller continuation

static int probe_empty(const uint8_t *e0, int ci) {
    const uint8_t *e = e0; int ec = ci, empty = 0;
#include "defer_empty_loop.inc"
    return empty;
}

typedef struct { uint8_t b[512] __attribute__((aligned(8))); size_t n; } arena;
static void s_reset(arena *a) { memset(a, 0, sizeof *a); }
static uint8_t *s_op(arena *a, uint32_t op, size_t payload) {
    size_t sz = (8 + payload + 7) & ~(size_t)7;
    uint8_t *p = a->b + a->n; a->n += sz;
    ((op_hdr *)p)->op = op; ((op_hdr *)p)->size = (uint32_t)sz;
    memset(p + 8, 0, sz - 8);
    return p + 8;
}
static void s_tf(arena *a) { p_tf_diag *x = (p_tf_diag *)s_op(a, OP_TF_DIAG, sizeof *x); x->kind = TF_DIAG_KIND_BEGIN; }

int main(void) {
    setvbuf(stdout, NULL, _IONBF, 0);
    static arena A;

    g_mode = TF_DIAG_MODE_ON;
    s_reset(&A); s_op(&A, OP_SET_RT, 8);
    int e1 = probe_empty(A.b, 0);
    ck(e1 == 1, "S02", "empty pass (next op is another SET_RT) -> proof holds (not taken as Q)", "empty=%d", e1);

    s_reset(&A); s_op(&A, OP_DRAW, 0);
    int e2 = probe_empty(A.b, 0);
    ck(e2 == 0, "S02", "draw present -> not empty", "empty=%d", e2);

    s_reset(&A); s_tf(&A); s_op(&A, OP_SET_RT, 8);
    int e3 = probe_empty(A.b, 0);
    ck(e3 == 0, "S02", "TF in the proof range (ON) stops the scan -> not proven empty", "empty=%d", e3);

    g_mode = TF_DIAG_MODE_OFF;
    int e4 = probe_empty(A.b, 0);
    ck(e4 == 1, "S02", "OFF control: same stream, TF is skipped, empty proof holds again", "empty=%d", e4);

    g_mode = TF_DIAG_MODE_ON;
    s_reset(&A); s_op(&A, OP_END, 0);
    int e5 = probe_empty(A.b, 0);
    ck(e5 == 0, "S02", "end of list without continuation -> not empty", "empty=%d", e5);

    // Control flow: JUMP over a draw to a SET_RT still yields the empty proof.
    s_reset(&A);
    { uint8_t *j = s_op(&A, OP_JUMP, 8); const uint8_t *t = A.b + A.n + 8; memcpy(j, &t, 8); }   // skip the 8-byte DRAW
    s_op(&A, OP_DRAW, 0);                 // skipped by the jump
    s_op(&A, OP_SET_RT, 8);               // jump target
    int e6 = probe_empty(A.b, 0);
    ck(e6 == 1, "S02", "JUMP to SET_RT: empty proof still holds", "empty=%d", e6);

    printf("RESULT pass=%d fail=%d\n", g_pass, g_fail);
    return g_fail ? 1 : 0;
}
