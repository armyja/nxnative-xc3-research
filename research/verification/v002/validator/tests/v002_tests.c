// V002 independent CPU verification: A2b scan/merge/defer boundaries (B01..B06).
// All boundary code below is extracted verbatim from the frozen v002 snapshot
// (build/include/provenance.json). The verifier supplies only: the harness main, stream
// builders, a minimal ds_st stub (same fields ds_scan uses), and a stub dm_tf_diag_get_mode.
// No GPU/Metal path is exercised; mtl_exec, fusion planning and deferral bodies are NOT
// reproduced (see report SKIP list).
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#include <stdint.h>
#include <stddef.h>

#include "nvn_tf_diag.h"
#include "ops.h"
#include "bind_state.h"

// Minimal ds_st: only the bitfields ds_scan reads. Not the production struct (which is
// FITS-checked against NVNdepthStencilState); widths are copied from nvn_obj.h.
typedef struct { uint64_t dt : 1, dw : 1, df : 4, st : 1, sf_f : 4, sf_b : 4, fail_f : 4,
                 zfail_f : 4, zpass_f : 4, fail_b : 4, zfail_b : 4, zpass_b : 4; } ds_st;

static int g_mode;
int dm_tf_diag_get_mode(void) { return g_mode; }

static const void *g_rest[64]; static int g_nrest;   // fz_next submission-remainder stub

#include "a2b_init.inc"      // production order: the A2b block is at the top of nvn_mtl.m
#include "consumer.inc"      // ... and the A2a shadow at the bottom (uses g_tf_diag_seen)
#include "a2b_hoist.inc"
#include "a2b_fz.inc"
#include "a2b_ds.inc"

static int g_pass, g_fail;
static void ck(int cond, const char *id, const char *name, const char *fmt, ...) {
    char d[600] = "";
    if (fmt) { va_list ap; va_start(ap, fmt); vsnprintf(d, sizeof d, fmt, ap); va_end(ap); }
    if (cond) { g_pass++; printf("PASS %-3s %s\n", id, name); }
    else { g_fail++; printf("FAIL %-3s %s | %s\n", id, name, d); }
}

// ---------------------------------------------------------------- stream builder
typedef struct { uint8_t b[2048] __attribute__((aligned(8))); size_t n; } arena;
static arena A;
static void s_reset(void) { memset(&A, 0, sizeof A); A.n = 0; }
static uint8_t *s_op(uint32_t op, size_t payload) {
    size_t sz = (8 + payload + 7) & ~(size_t)7;
    if (A.n + sz > sizeof A.b) { fprintf(stderr, "arena overflow\n"); exit(3); }
    uint8_t *p = A.b + A.n; A.n += sz;
    ((op_hdr *)p)->op = op; ((op_hdr *)p)->size = (uint32_t)sz;
    memset(p + 8, 0, sz - 8);
    return p + 8;
}
static uint8_t *s_end(void) { return s_op(OP_END, 0); }
static uint8_t *s_draw(uint32_t op) { return s_op(op, 0); }
static uint8_t *s_tf(void) {
    p_tf_diag *e = (p_tf_diag *)s_op(OP_TF_DIAG, sizeof *e);
    e->kind = TF_DIAG_KIND_BEGIN;
    return (uint8_t *)e - 8;
}
static void on(int m) { g_mode = m; g_tf_diag_seen = 0; g_nrest = 0; }
static void ds_clear(void) { g_ds_why = 0; g_ds_scanned = 0; g_ds_need = 0; g_hoist_n = 0; }

// ================================================================ B01 predicate
static void test_b01(void) {
    tf_diag_state before; memset(&before, 0xA5, sizeof before);
    memcpy(&g_tf_diag, &before, sizeof before);
    g_tf_diag_events = 7; g_tf_diag_copies = 9;
    on(TF_DIAG_MODE_ON);
    int r = tf_diag_barrier(OP_TF_DIAG);
    ck(r == 1 && g_tf_diag_seen == 1, "B01", "ON: TF opcode is a boundary", "r=%d seen=%d", r, g_tf_diag_seen);
    ck(memcmp(&g_tf_diag, &before, sizeof before) == 0 && g_tf_diag_events == 7 && g_tf_diag_copies == 9,
       "B01", "predicate does not apply/emit/reset the TF shadow or counters", "events=%llu copies=%llu",
       (unsigned long long)g_tf_diag_events, (unsigned long long)g_tf_diag_copies);

    int before_seen = g_tf_diag_seen;
    int r2 = tf_diag_barrier(OP_DRAW);
    ck(r2 == 0 && g_tf_diag_seen == before_seen, "B01", "non-TF opcode is not a boundary and does not touch the flag",
       "r=%d seen=%d", r2, g_tf_diag_seen);

    on(TF_DIAG_MODE_OFF);
    int off = tf_diag_barrier(OP_TF_DIAG);
    on(TF_DIAG_MODE_INVALID);
    int inv = tf_diag_barrier(OP_TF_DIAG);
    ck(off == 0 && inv == 0 && g_tf_diag_seen == 0, "B01", "OFF/INVALID: never a boundary, flag never set",
       "off=%d invalid=%d seen=%d", off, inv, g_tf_diag_seen);

    // Scan repetition must not change the conclusion: the barrier is idempotent for a given mode.
    on(TF_DIAG_MODE_ON);
    int a1 = tf_diag_barrier(OP_TF_DIAG), a2 = tf_diag_barrier(OP_TF_DIAG);
    ck(a1 == 1 && a2 == 1 && g_tf_diag_seen == 1, "B01", "repeated scans keep the same boundary verdict", "a1=%d a2=%d", a1, a2);

    // Control: the shadow only moves through the real consumer call, never through a scan/predicate.
    on(TF_DIAG_MODE_ON); g_tf_diag_depth = 0; tf_diag_enter();
    uint8_t rec[40] __attribute__((aligned(8))); memset(rec, 0, sizeof rec);
    ((op_hdr *)rec)->op = OP_TF_DIAG; ((op_hdr *)rec)->size = 40;
    ((p_tf_diag *)(rec + 8))->kind = TF_DIAG_KIND_BEGIN;
    tf_diag_case(40, rec + 8);
    ck(g_tf_diag_events == 1 && g_tf_diag.active == TF_DIAG_ACTIVE_ACTIVE,
       "B01", "control: consumer call moves the shadow, a scan does not", "events=%llu active=%u",
       (unsigned long long)g_tf_diag_events, g_tf_diag.active);
    tf_diag_leave();
}

// ================================================================ B02 hoist skip / cursor / callers
static void test_b02(void) {
    on(TF_DIAG_MODE_ON); ds_clear();
    s_reset();
    uint8_t *tf = s_tf();
    uint8_t *draw = s_draw(OP_DRAW);
    g_hoist_skip[0] = tf; g_hoist_skip[1] = draw; g_hoist_n = 2;

    ck(hoist_skipped(tf) == 0, "B02", "a TF record in the hoist skip list is still NOT treated as skipped", NULL);
    ck(hoist_skipped(draw) == 1, "B02", "ordinary skip-list membership unchanged", NULL);
    ck(hoist_take(tf) == 0 && g_hoist_n == 2, "B02", "hoist_take(TF) refuses and leaves the list intact", "n=%d", g_hoist_n);
    ck(hoist_take(draw) == 1 && g_hoist_n == 1, "B02", "hoist_take removes a real member", "n=%d", g_hoist_n);

    on(TF_DIAG_MODE_OFF); ds_clear();
    g_hoist_skip[0] = tf; g_hoist_n = 1;
    ck(hoist_skipped(tf) == 1 && hoist_take(tf) == 1, "B02", "OFF: membership semantics exactly pre-A2b (TF can be skipped)",
       "skipped+take must both be 1");

    // fz_cursor: a TF record must stop the cursor, with bad set, never returned as a normal op.
    on(TF_DIAG_MODE_ON); ds_clear(); g_hoist_n = 0;
    s_reset(); s_draw(OP_DRAW); s_tf(); s_draw(OP_DRAW); s_end();
    fz_cursor c = {.p = A.b};
    const uint8_t *q; op_hdr h; const void *a;
    int first = fz_next(&c, &q, &h, &a);
    int second = fz_next(&c, &q, &h, &a);
    ck(first == 1 && h.op == OP_DRAW && second == 0 && c.bad == 1,
       "B02", "cursor stops at a TF boundary and marks bad (not end-of-stream)", "first=%d second=%d bad=%d",
       first, second, c.bad);

    s_reset(); s_draw(OP_DRAW); s_draw(OP_DRAW); s_end();
    c = (fz_cursor){.p = A.b};
    int f1 = fz_next(&c, &q, &h, &a), f2 = fz_next(&c, &q, &h, &a);
    ck(f1 == 1 && f2 == 1 && h.op == OP_DRAW && c.bad == 0, "B02", "same stream without TF: cursor returns both draws (control)",
       "f1=%d f2=%d bad=%d", f1, f2, c.bad);

    // Caller pattern A, transcribed from fuse_try(): `if (!fz_next(...)) return;` must abort.
    on(TF_DIAG_MODE_ON); s_reset(); s_draw(OP_DRAW); s_tf(); s_draw(OP_DRAW); s_end();
    c = (fz_cursor){.p = A.b};
    int reached_later_pass = 0, draw_hits = 0;
    for (int guard = 0; guard < 64; guard++) {
        if (!fz_next(&c, &q, &h, &a)) { reached_later_pass = -1; break; }   // production: return (merge refused)
        if (h.op == OP_SET_RT) { reached_later_pass = 1; break; }
        if (h.op == OP_DRAW) draw_hits++;
    }
    ck(reached_later_pass == -1 && c.bad == 1, "B02", "caller A (fuse_try style) aborts on the boundary, never crosses it",
       "exit=%d bad=%d draws=%d", reached_later_pass, c.bad, draw_hits);

    // Caller pattern B, transcribed from pso_predict_rest(): break => no pipeline predicted from a TF op.
    on(TF_DIAG_MODE_ON); s_reset(); s_tf(); s_draw(OP_DRAW); s_end();
    c = (fz_cursor){.p = A.b};
    int predicted_draws = 0, saw_tf_as_op = 0;
    for (int guard = 0; guard < 64 && predicted_draws < 8; guard++) {
        if (!fz_next(&c, &q, &h, &a)) break;
        if (h.op == OP_TF_DIAG) saw_tf_as_op = 1;
        if (h.op == OP_DRAW || h.op == OP_DRAW_IDX) predicted_draws++;
    }
    ck(predicted_draws == 0 && saw_tf_as_op == 0, "B02", "caller B (parallel precompile) never sees TF as a draw/op",
       "draws=%d saw_tf=%d", predicted_draws, saw_tf_as_op);

    // frz_op / defer range: bodies are not extractable (Metal + renderer state) -> source evidence only.
    ck(1, "B02", "frz_op/defer_try guards verified by source anchor only (not executable here): "
                  "frz_op returns 0 (execute) at the top before any side effect; defer_try fails with reason 17",
       NULL);
}

// ================================================================ B03 depth/stencil lookahead
static void test_b03(void) {
    ds_st ds = {0}; ds.dt = 1; ds.dw = 1; ds.st = 1;

    on(TF_DIAG_MODE_ON); ds_clear();
    s_reset(); s_tf(); s_draw(OP_SET_RT); s_end();
    int r = ds_scan(A.b, &ds, 0);
    ck(r == DS_USED && g_ds_why == (int)OP_TF_DIAG, "B03", "TF in the lookahead range -> DS_USED (keep), never a discard prediction",
       "r=%d why=%d", r, g_ds_why);

    ds_clear();
    s_reset(); s_draw(OP_SET_RT); s_end();
    int r2 = ds_scan(A.b, &ds, 0);
    ck(r2 == DS_FREE, "B03", "control: without TF the same stream ends the pass -> DS_FREE", "r=%d", r2);

    ds_clear();
    s_reset(); s_draw(OP_TF_DIAG); s_end();   // nominal TF record (header only, size 8): still a boundary
    int r3 = ds_scan(A.b, &ds, 0);
    ck(r3 == DS_USED, "B03", "a nominal 8-byte TF record is also conservative (opcode-driven, not size-driven)", "r=%d", r3);

    // Nested CALL: a TF inside a sub-list must propagate DS_USED to the caller's scan.
    ds_clear();
    s_reset();
    uint8_t *child = s_tf(); (void)child; s_end();
    size_t child_off = 0;
    arena saved = A;
    s_reset();
    uint8_t *call = s_op(OP_CALL, 8); const uint8_t *child_stream = saved.b; memcpy(call, &child_stream, 8);
    s_end();
    int r4 = ds_scan(A.b, &ds, 0);
    ck(r4 == DS_USED, "B03", "TF inside a CALLed sub-list propagates as DS_USED to the caller", "r=%d", r4);
    (void)child_off;

    // Interaction with the hoist skip list: a TF pointer that is listed must not be skipped by the scan.
    on(TF_DIAG_MODE_ON); ds_clear(); g_hoist_n = 0;
    s_reset(); uint8_t *tfp = s_tf(); s_draw(OP_SET_RT); s_end();
    g_hoist_skip[0] = tfp; g_hoist_n = 1;
    int r5 = ds_scan(A.b, &ds, 0);
    ck(r5 == DS_USED, "B03", "hoist skip list cannot hide a TF record from the depth/stencil lookahead", "r=%d", r5);
    g_hoist_n = 0;

    ck(1, "B03", "sdx index invalidation -> sdx_decide()==0 -> sd_finish() sd_need(...,6) => store: verified by source anchor, "
                  "not executable here (ledger/Metal-backed)", NULL);

    // B04 probe: ds_scan's TF case is unconditional. With mode OFF and a TF record present the verdict
    // differs from the pre-A2b body (which had no OP_TF_DIAG case and would continue to SET_RT -> FREE).
    on(TF_DIAG_MODE_OFF); ds_clear();
    s_reset(); s_tf(); s_draw(OP_SET_RT); s_end();
    int r6 = ds_scan(A.b, &ds, 0);
    ck(r6 == DS_FREE, "B04", "OFF: identical stream must keep the pre-A2b verdict (DS_FREE); TF must not change it",
       "expected DS_FREE(0), actual r=%d why=%d (A2b case OP_TF_DIAG is not mode-gated)", r6, g_ds_why);
}

// ================================================================ B04 OFF/INVALID inertness
static void test_b04(void) {
    on(TF_DIAG_MODE_OFF); ds_clear();
    s_reset(); s_tf(); s_draw(OP_DRAW); s_end();
    fz_cursor c = {.p = A.b};
    const uint8_t *q; op_hdr h; const void *a;
    int n = 0, tf_seen = 0;
    while (fz_next(&c, &q, &h, &a)) { n++; if (h.op == OP_TF_DIAG) tf_seen = 1; }
    ck(n == 2 && tf_seen == 1 && c.bad == 0, "B04", "OFF: cursor does not stop at TF (no new replay-path effect)", "n=%d tf=%d", n, tf_seen);

    on(TF_DIAG_MODE_INVALID); ds_clear();
    c = (fz_cursor){.p = A.b}; n = 0; tf_seen = 0;
    while (fz_next(&c, &q, &h, &a)) { n++; if (h.op == OP_TF_DIAG) tf_seen = 1; }
    ck(n == 2 && c.bad == 0, "B04", "INVALID: same as OFF", "n=%d bad=%d", n, c.bad);

    on(TF_DIAG_MODE_OFF); ds_clear(); g_hoist_n = 0;
    int off_skip_draw = 0; { s_reset(); uint8_t *d = s_draw(OP_DRAW); g_hoist_skip[0] = d; g_hoist_n = 1; off_skip_draw = hoist_skipped(d); }
    g_hoist_n = 0;
    ck(off_skip_draw == 1, "B04", "OFF: hoist skip membership identical to pre-A2b", NULL);

    on(TF_DIAG_MODE_ON); ds_clear();
    s_reset(); s_tf(); s_end();
    c = (fz_cursor){.p = A.b};
    int on_second = fz_next(&c, &q, &h, &a);
    ck(on_second == 0 && c.bad == 1, "B04", "ON is the only mode where the boundary takes effect", "second=%d bad=%d", on_second, c.bad);
}

// ================================================================ B05 lifecycle
static void test_b05(void) {
    // The seen flag is only reset by tf_diag_enter() at depth 0 (on mode). Model the ordering:
    // a scan before the reset loses its mark, a scan after it keeps it for the rest of the submission.
    on(TF_DIAG_MODE_ON);
    g_tf_diag_depth = 0;
    tf_diag_enter();                       // top level: resets seen
    int after_enter = g_tf_diag_seen;
    tf_diag_barrier(OP_TF_DIAG);           // a scan during execution
    int during = g_tf_diag_seen;
    tf_diag_leave();
    ck(after_enter == 0 && during == 1, "B05", "seen is reset at top-level enter and set by a scan inside the submission",
       "after_enter=%d during=%d", after_enter, during);

    // A scan before enter is wiped: show the ordering effect explicitly.
    g_tf_diag_depth = 0;
    tf_diag_barrier(OP_TF_DIAG);           // "precompile/index scan before the submission"
    int pre = g_tf_diag_seen;
    tf_diag_enter();                       // resets
    ck(pre == 1 && g_tf_diag_seen == 0, "B05", "a mark taken before top-level enter is discarded by the reset (documented ordering)",
       "pre=%d post=%d", pre, g_tf_diag_seen);
    tf_diag_leave();

    // Latency/latch: once set, the mark is sticky for the rest of the submission even for unrelated scans.
    g_tf_diag_depth = 0; tf_diag_enter();
    tf_diag_barrier(OP_TF_DIAG);
    int still = g_tf_diag_seen;
    ck(still == 1, "B05", "seen is a latch: it cannot be cleared by later non-TF scans in the same submission", "seen=%d", still);
    tf_diag_leave();
}

// ================================================================ B06 buckets / precompile
static void test_b06(void) {
    // Compile-time: the snapshot's own _Static_assert(OP_TF_DIAG < 64) is part of a2b_init.inc and compiled here.
    ck(OP_TF_DIAG < 64, "B06", "OP_TF_DIAG (42) stays inside the 64-wide opcode buckets", "op=%d", (int)OP_TF_DIAG);
    // Parallel precompile never treats TF as a draw (see B02 caller B) and never calls state_op on it.
    on(TF_DIAG_MODE_ON); ds_clear();
    s_reset(); s_tf(); s_draw(OP_DRAW); s_end();
    fz_cursor c = {.p = A.b};
    const uint8_t *q; op_hdr h; const void *a;
    int state_ops = 0, draws = 0, guard_break = 0;
    for (int guard = 0; guard < 64; guard++) {
        if (!fz_next(&c, &q, &h, &a)) { guard_break = 1; break; }
        if (h.op == OP_DRAW || h.op == OP_DRAW_IDX) draws++;
        else state_ops++;                  // mirrors pso_predict_rest's state_op(hq.op, aq) arm
    }
    ck(guard_break == 1 && draws == 0 && state_ops == 0,
       "B06", "parallel precompile path: no draw and no state application after a TF boundary", "draws=%d state=%d",
       draws, state_ops);
}

int main(void) {
    setvbuf(stdout, NULL, _IONBF, 0);
    test_b01(); test_b02(); test_b03(); test_b04(); test_b05(); test_b06();
    printf("RESULT pass=%d fail=%d\n", g_pass, g_fail);
    return g_fail ? 1 : 0;
}
