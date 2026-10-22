// V002-S S03: FALSE-from-cursor vs end-of-stream, executed with the real fz_next.
// The production shape (fuse_try step one: `if (!fz_next(...)) return;`) is compared with a
// counterfactual "treat FALSE as normal end -> accept" shape to show the distinction is
// load-bearing, not vacuous. The caller shapes are transcribed, not the full fuse_try.
#include <stdio.h>
#include <stdarg.h>
#include <stdint.h>
#include <string.h>
#include <stddef.h>

#include "nvn_tf_diag.h"
#include "ops.inc"

static int g_mode;
int dm_tf_diag_get_mode(void) { return g_mode; }
static const void *g_rest[64]; static int g_nrest;

#include "a2b_init.inc"
#include "hoist.inc"
#include "fz_next.inc"

static int g_pass, g_fail;
static void ck(int c, const char *id, const char *name, const char *fmt, ...) {
    char d[400] = ""; if (fmt) { va_list ap; va_start(ap, fmt); vsnprintf(d, sizeof d, fmt, ap); va_end(ap); }
    if (c) { g_pass++; printf("PASS %s %s\n", id, name); } else { g_fail++; printf("FAIL %s %s | %s\n", id, name, d); }
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
static void s_tf(arena *a) { p_tf_diag *x = (p_tf_diag *)s_op(a, OP_TF_DIAG, sizeof *x); x->kind = TF_DIAG_KIND_BEGIN; }

// Production shape, transcribed from fuse_try() step one: FALSE aborts the caller.
static int prod_step_one(const uint8_t *start) {
    fz_cursor cur = {.p = start}; const uint8_t *p = NULL; op_hdr h; const void *a;
    int reached_later_pass = 0;
    for (int guard = 0; guard < 200000 && !reached_later_pass; guard++) {
        if (!fz_next(&cur, &p, &h, &a)) return 0;              // production: return (no merge)
        if (h.op == OP_SET_RT) { reached_later_pass = 1; break; }
    }
    return reached_later_pass;
}
// Counterfactual: FALSE treated as "reached the end normally" -> merge accepted.
static int buggy_step_one(const uint8_t *start) {
    fz_cursor cur = {.p = start}; const uint8_t *p = NULL; op_hdr h; const void *a;
    int reached_later_pass = 0;
    for (int guard = 0; guard < 200000; guard++) {
        if (!fz_next(&cur, &p, &h, &a)) { reached_later_pass = 1; break; }   // the mistake under test
        if (h.op == OP_SET_RT) { reached_later_pass = 1; break; }
    }
    return reached_later_pass;
}

int main(void) {
    setvbuf(stdout, NULL, _IONBF, 0);
    static arena A;
    g_mode = TF_DIAG_MODE_ON; g_nrest = 0; g_hoist_n = 0;

    // Stream: draw ... TF ... SET_RT. A boundary stops the plan before the later pass.
    s_reset(&A); s_op(&A, OP_DRAW, 0); s_tf(&A); s_op(&A, OP_SET_RT, 8); s_op(&A, OP_END, 0);
    int prod = prod_step_one(A.b), buggy = buggy_step_one(A.b);
    ck(prod == 0 && buggy == 1, "S03", "production shape refuses across TF; 'FALSE==end' would have accepted",
       "prod=%d buggy=%d", prod, buggy);

    // Control without TF: both reach the later pass.
    s_reset(&A); s_op(&A, OP_DRAW, 0); s_op(&A, OP_SET_RT, 8); s_op(&A, OP_END, 0);
    int prod2 = prod_step_one(A.b), buggy2 = buggy_step_one(A.b);
    ck(prod2 == 1 && buggy2 == 1, "S03", "control without TF: both shapes reach the later pass", "prod=%d buggy=%d", prod2, buggy2);

    // Genuine end-of-stream (OP_END with no continuation) also returns FALSE: the production
    // shape refuses there too, i.e. FALSE is not an acceptance signal either way.
    s_reset(&A); s_op(&A, OP_END, 0);
    ck(prod_step_one(A.b) == 0, "S03", "ordinary end-of-stream also yields FALSE -> refused (no success evidence)", NULL);

    // Second caller shape (pso_predict_rest): FALSE merely stops collecting; it must not
    // predict a pipeline from the boundary record itself.
    s_reset(&A); s_op(&A, OP_DRAW, 0); s_tf(&A); s_op(&A, OP_DRAW, 0); s_op(&A, OP_END, 0);
    { fz_cursor cur = {.p = A.b}; const uint8_t *q; op_hdr h; const void *a; int draws = 0;
      while (fz_next(&cur, &q, &h, &a) && draws < 8) { if (h.op == OP_DRAW) draws++; }
      ck(draws == 1, "S03", "precompile collection stops at the boundary (one draw, not two)", "draws=%d", draws); }

    printf("RESULT pass=%d fail=%d\n", g_pass, g_fail);
    return g_fail ? 1 : 0;
}
