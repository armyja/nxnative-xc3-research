// V003 CPU revalidation of the F1/F2 fixes.
// Extracted verbatim from the frozen v003 snapshot: tf_diag_barrier (pure), hoist skip,
// fz_next, ds_scan. The hoist "caller" below is a MINIMAL fragment: only the TF arm text is
// verbatim; the other arms are stubs that mark "a hoistable clear was reached". It is not hoist_try.
#include <stdio.h>
#include <stdarg.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>

#include "nvn_tf_diag.h"
#include "ops.inc"

typedef struct { uint64_t dt : 1, dw : 1, df : 4, st : 1, sf_f : 4, sf_b : 4, fail_f : 4,
                 zfail_f : 4, zpass_f : 4, fail_b : 4, zfail_b : 4, zpass_b : 4; } ds_st;

static int g_mode;
int dm_tf_diag_get_mode(void) { return g_mode; }
static const void *g_rest[64]; static int g_nrest;

#include "consumer.inc"   // tf_diag_enter/leave (needed for the order test)
#include "bind_state.inc"
#include "init.inc"
#include "hoist.inc"
#include "fz.inc"
#include "ds.inc"

static int g_pass, g_fail;
static void ck(int c, const char *id, const char *name, const char *fmt, ...) {
    char d[400] = ""; if (fmt) { va_list ap; va_start(ap, fmt); vsnprintf(d, sizeof d, fmt, ap); va_end(ap); }
    if (c) { g_pass++; printf("PASS %-4s %s\n", id, name); } else { g_fail++; printf("FAIL %-4s %s | %s\n", id, name, d); }
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

// ---------------------------------------------------------------- V3.1: ds_scan, 3 modes
static int ds_on_stream(const uint8_t *p, int mode, ds_st *ds) {
    g_mode = mode; g_ds_why = 0; g_ds_scanned = 0; g_ds_need = 0; g_hoist_n = 0;
    return ds_scan(p, ds, 0);
}
static void test_v31(void) {
    static arena A; ds_st ds = {0}; ds.dt = 1; ds.dw = 1; ds.st = 1;
    s_reset(&A); s_tf(&A); s_op(&A, OP_SET_RT, 8); s_op(&A, OP_END, 0);

    int on = ds_on_stream(A.b, TF_DIAG_MODE_ON, &ds);
    int on_why = g_ds_why;
    int off = ds_on_stream(A.b, TF_DIAG_MODE_OFF, &ds);
    int off_why = g_ds_why;
    int inv = ds_on_stream(A.b, TF_DIAG_MODE_INVALID, &ds);
    int inv_why = g_ds_why;

    ck(on == DS_USED && on_why == (int)OP_TF_DIAG, "V3.1", "ON: original counterexample [TF,SET_RT,END] keeps depth/stencil",
       "r=%d why=%d", on, on_why);
    ck(off == DS_FREE && off_why == 0, "V3.1", "OFF: same stream restores pre-A2b verdict DS_FREE (no why side effect)",
       "r=%d why=%d", off, off_why);
    ck(inv == DS_FREE && inv_why == 0, "V3.1", "INVALID: same as OFF (mode-gated case, not a new default)", "r=%d why=%d", inv, inv_why);

    // Control: without TF all three modes must agree (the gate only adds the ON case).
    s_reset(&A); s_op(&A, OP_SET_RT, 8); s_op(&A, OP_END, 0);
    int a = ds_on_stream(A.b, TF_DIAG_MODE_ON, &ds), b = ds_on_stream(A.b, TF_DIAG_MODE_OFF, &ds), c = ds_on_stream(A.b, TF_DIAG_MODE_INVALID, &ds);
    ck(a == DS_FREE && b == DS_FREE && c == DS_FREE, "V3.1", "control without TF: all modes DS_FREE", "%d/%d/%d", a, b, c);

    // A TF record that is NOT reached before SET_RT (i.e. after it) must not change OFF behaviour.
    s_reset(&A); s_op(&A, OP_SET_RT, 8); s_tf(&A); s_op(&A, OP_END, 0);
    ck(ds_on_stream(A.b, TF_DIAG_MODE_OFF, &ds) == DS_FREE, "V3.1", "OFF: TF after the pass boundary is irrelevant", NULL);
}

// ---------------------------------------------------------------- V3.2: hoist arm, caller-visible
// Minimal fragment: scan forward until a hoistable clear is reached. The TF arm is the real
// v003 line; other arms are stubs (return/continue) sufficient to observe abort-vs-continue.
static int hoist_scan_fragment(const uint8_t *p, int mode) {
    g_mode = mode;
    for (int guard = 0; guard < 1000; guard++) {
        op_hdr h; memcpy(&h, p, sizeof h); const void *a = p + 8;
        switch (h.op) {
            case OP_END: case OP_CALL: case OP_COPY_T2T: case OP_COPY_B2T: case OP_COPY_T2B: case OP_CLEAR_TEX: case OP_DISPATCH: case OP_RENDER_COND: return 0;
            case OP_TF_DIAG: if (tf_diag_barrier(h.op)) return 0; break;   // <-- verbatim v003 branch
            case OP_JUMP: { const uint8_t *t; memcpy(&t, a, 8); p = t; continue; }
            case OP_DRAW: case OP_DRAW_IDX: break;
            case OP_CLEAR_COLOR: case OP_CLEAR_DS: return 1;               // stub: a hoistable clear was reached
            default: break;
        }
        p += h.size;
    }
    return 0;
}
static void test_v32(void) {
    static arena A; s_reset(&A); s_tf(&A); s_op(&A, OP_CLEAR_COLOR, 8); s_op(&A, OP_END, 0);
    int on = hoist_scan_fragment(A.b, TF_DIAG_MODE_ON);
    int off = hoist_scan_fragment(A.b, TF_DIAG_MODE_OFF);
    int inv = hoist_scan_fragment(A.b, TF_DIAG_MODE_INVALID);
    ck(on == 0, "V3.2", "ON: hoist candidate scan aborts at TF (no cross-boundary candidate)", "found=%d", on);
    ck(off == 1 && inv == 1, "V3.2", "OFF/INVALID: falls through like the pre-A2b default and reaches the clear", "off=%d inv=%d", off, inv);

    s_reset(&A); s_op(&A, OP_CLEAR_COLOR, 8); s_op(&A, OP_END, 0);
    int a = hoist_scan_fragment(A.b, TF_DIAG_MODE_ON), b = hoist_scan_fragment(A.b, TF_DIAG_MODE_OFF);
    ck(a == 1 && b == 1, "V3.2", "control without TF: all modes reach the clear", "%d/%d", a, b);

    // hoist_take: a TF record that ended up in the skip list must still not be consumed.
    s_reset(&A); uint8_t *tf = (uint8_t *)A.b + A.n; s_tf(&A); s_op(&A, OP_DRAW, 0); s_op(&A, OP_END, 0);
    g_mode = TF_DIAG_MODE_ON; g_hoist_skip[0] = tf; g_hoist_n = 1;
    int took = hoist_take(tf), skipped = hoist_skipped(tf);
    ck(took == 0 && skipped == 0 && g_hoist_n == 1, "V3.2", "hoist skip list still refuses to hide/consume a TF record",
       "take=%d skipped=%d n=%d", took, skipped, g_hoist_n);
    g_hoist_n = 0;
}

// ---------------------------------------------------------------- V3.3: barrier purity / order
static void test_v33(void) {
    // Purity: same input -> same verdict, no hidden history.
    g_mode = TF_DIAG_MODE_ON;
    int r1 = tf_diag_barrier(OP_TF_DIAG), r2 = tf_diag_barrier(OP_TF_DIAG), r3 = tf_diag_barrier(OP_DRAW);
    ck(r1 == 1 && r2 == 1 && r3 == 0, "V3.3", "predicate is pure: repeated scans give the same verdict", "%d/%d/%d", r1, r2, r3);

    // Scan order: a pre-index scan before tf_diag_enter, and a lookahead after it, must not change
    // the verdict for the same stream (there is no latch to prime any more).
    g_tf_diag_depth = 0;
    (void)tf_diag_barrier(OP_TF_DIAG);          // "pre-index scan"
    tf_diag_enter();                             // top-level reset (now only resets the shadow)
    int during = tf_diag_barrier(OP_TF_DIAG);    // "lookahead during execution"
    tf_diag_leave();
    g_tf_diag_depth = 0; tf_diag_enter();
    int fresh = tf_diag_barrier(OP_TF_DIAG);
    tf_diag_leave();
    ck(during == 1 && fresh == 1, "V3.3", "scan order (pre-index -> enter -> lookahead) cannot change the boundary verdict",
       "during=%d fresh=%d", during, fresh);

    // The latch itself must be gone: a non-TF scan cannot influence a later TF verdict.
    g_mode = TF_DIAG_MODE_ON;
    (void)tf_diag_barrier(OP_DRAW);
    int after_non_tf = tf_diag_barrier(OP_TF_DIAG);
    ck(after_non_tf == 1, "V3.3", "no latch: a preceding non-TF scan does not suppress/alter the boundary", "%d", after_non_tf);

    // Local scanner still stops at the boundary (fz_next body unchanged in v003).
    static arena A; s_reset(&A); s_op(&A, OP_DRAW, 0); s_tf(&A); s_op(&A, OP_DRAW, 0); s_op(&A, OP_END, 0);
    g_nrest = 0; g_hoist_n = 0;
    fz_cursor c = {.p = A.b}; const uint8_t *q; op_hdr h; const void *a;
    int f1 = fz_next(&c, &q, &h, &a), f2 = fz_next(&c, &q, &h, &a);
    ck(f1 == 1 && f2 == 0 && c.bad == 1, "V3.3", "local scanner still refuses to cross TF (no reliance on the removed prefilter latch)",
       "f1=%d f2=%d bad=%d", f1, f2, c.bad);

    // Control: the shadow still only moves through the consumer call, not through predicates.
    unsigned char rec[40] __attribute__((aligned(8))); memset(rec, 0, sizeof rec);
    ((op_hdr *)rec)->op = OP_TF_DIAG; ((op_hdr *)rec)->size = 40;
    ((p_tf_diag *)(rec + 8))->kind = TF_DIAG_KIND_BEGIN;
    g_mode = TF_DIAG_MODE_ON; g_tf_diag_depth = 0; tf_diag_enter();
    tf_diag_case(40, rec + 8);
    ck(dm_tf_diag_events() == 1 && dm_tf_diag_snapshot()->active == TF_DIAG_ACTIVE_ACTIVE,
       "V3.3", "consumer path unchanged: a scan-free consumer call still applies the event once",
       "events=%llu active=%u", (unsigned long long)dm_tf_diag_events(), dm_tf_diag_snapshot()->active);
    tf_diag_leave();
}

int main(void) {
    setvbuf(stdout, NULL, _IONBF, 0);
    test_v31(); test_v32(); test_v33();
    printf("RESULT pass=%d fail=%d\n", g_pass, g_fail);
    return g_fail ? 1 : 0;
}
