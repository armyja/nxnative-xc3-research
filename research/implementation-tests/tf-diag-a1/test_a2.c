// A2a: CPU verification of the REAL replay consumer and the REAL OP_END/OP_BEGIN/OP_CALL case bodies, sliced out of
// nvn_mtl.m by extract_a2.py. External renderer environment is stubbed and disclosed: g_exec_cur/g_hoist_n/g_ret/g_ret_n/
// g_nrest/g_fz/fz_unskip/MLOG and dm_tf_diag_get_mode are harness stand-ins; the switch scaffolding inside mtl_exec is the
// harness's own loop. Nothing here is production mtl_exec and nothing proves NVN semantics.
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include "nvn_tf_diag.h"

#define OP_END 0
#define OP_BEGIN 2
#define OP_CALL 3
#define OP_DRAW 25
#define OP_DRAW_IDX 26
#define OP_TF_DIAG 42
_Static_assert(OP_TF_DIAG == 42, "opcode numbering frozen by A1");

typedef struct { uint32_t op, size; } op_hdr;

// ---- disclosed stubs of the renderer environment ----
static const uint8_t *g_exec_cur;
static int g_hoist_n, g_ret_n, g_nrest;
static const uint8_t *g_ret[16];
static struct { int active; } g_fz;
static void fz_unskip(void) {}
#define MLOG(...) ((void)0)
static int g_mode = TF_DIAG_MODE_OFF;
static int g_rc_skip;
static const uint8_t *g_exec_next;
static int g_draw_calls, g_draw_idx_calls, g_snap_calls, g_draw_mark[8];
static void imgdiag_draw(void) { g_snap_calls++; }
static void ssbo_obs_draw(void) {}
static void ssbo_obs_draw_skipped(void) {}
static void imgdiag_draw_skipped(void) {}
static void draw(const void *a, const void *b) { g_draw_mark[g_draw_calls++] = a ? 1 : 2; if (!a && b) g_draw_idx_calls++; }
int dm_tf_diag_get_mode(void) { return g_mode; }

// ---- real code from nvn_mtl.m ----
#ifndef CONSUMER_INC
#define CONSUMER_INC "a2_consumer.inc"
#endif
#include CONSUMER_INC

static void mtl_exec(const uint8_t *p) {           // harness loop; the case bodies below are verbatim production text
    tf_diag_enter();
    for (;;) {
        op_hdr h; memcpy(&h, p, sizeof h);
        const void *a = p + 8;
        switch (h.op) {
#include "a2_cases_end_begin.inc"
#include "a2_cases_call.inc"
#include "a2_cases_draw.inc"
#ifndef TF_CASE_INC
#define TF_CASE_INC "a2_case_tf.inc"
#endif
#include TF_CASE_INC
        default: break;
        }
        p += h.size;
    }
    // harness: the only normal exit is OP_END's return (real code has no second exit either)
}

// ---- stream builder ----
static uint8_t mem[65536]; static size_t mlen;
static void put(uint32_t op, const void *pl, size_t n) {
    op_hdr h = {op, (uint32_t)((8 + n + 7) & ~(size_t)7)};
    memcpy(mem + mlen, &h, 8); if (pl) memcpy(mem + mlen + 8, pl, n); else memset(mem + mlen + 8, 0, h.size - 8);
    mlen += h.size;
}
static void s_begin(void) { put(OP_BEGIN, NULL, 0); }
static void s_end(void) { put(OP_END, NULL, 0); }
static void s_call(const void *t) { uint64_t v = (uint64_t)t; put(OP_CALL, &v, 8); }
static void s_draw(void) { int32_t d[2] = {0, 2304}; put(OP_DRAW, d, sizeof d); }
static void s_draw_idx(void) { int32_t d[2] = {0, 2304}; put(OP_DRAW_IDX, d, sizeof d); }
static void s_tf(uint32_t kind, int32_t idx, int32_t cnt, uint64_t addr, uint64_t size) {
    p_tf_diag e; memset(&e, 0, sizeof e); e.kind = kind; e.index = idx; e.count = cnt; e.addr = addr; e.size = size;
    put(OP_TF_DIAG, &e, sizeof e);
}
static int fails;
static void ck(int cond, const char *what) { if (!cond) { printf("FAIL %s\n", what); fails++; } }

int main(void) {
    const tf_diag_state *st;
    // A) off/invalid: state untouched, sentinel payload never read, no counters
    g_mode = TF_DIAG_MODE_OFF;
    tf_diag_state before; memset(&before, 0x5a, sizeof before);
    memcpy(&g_tf_diag, &before, sizeof before);
    tf_diag_case(40, (const void *)1);              // pointer 1: any payload read would crash
    ck(memcmp(&g_tf_diag, &before, sizeof before) == 0, "off state unchanged");
    ck(dm_tf_diag_copies() == 0 && dm_tf_diag_events() == 0, "off counters untouched");
    g_mode = TF_DIAG_MODE_INVALID; memcpy(&g_tf_diag, &before, sizeof before);
    tf_diag_case(40, (const void *)1);
    ck(memcmp(&g_tf_diag, &before, sizeof before) == 0, "invalid state unchanged");
    // B) on: exactly one copy and one apply per event
    g_mode = TF_DIAG_MODE_ON; tf_diag_init(&g_tf_diag);
    p_tf_diag e = {TF_DIAG_KIND_BEGIN, 0, 0, 0, 0x1000, 0};
    tf_diag_case(40, &e);
    ck(dm_tf_diag_copies() == 1 && dm_tf_diag_events() == 1, "on one copy/one apply");
    st = dm_tf_diag_snapshot(); ck(st->active == TF_DIAG_ACTIVE_ACTIVE && st->seq == 1, "on applied once");
    // C) bad record sizes: rejected, zero copy, payload never read
    const uint32_t bad[4] = {32, 39, 48, 0};
    for (int i = 0; i < 4; i++) {
        tf_diag_init(&g_tf_diag); uint32_t c0 = dm_tf_diag_copies();
        tf_diag_case(bad[i], &e);
        st = dm_tf_diag_snapshot();
        ck(dm_tf_diag_copies() == c0, "bad size zero copy");
        ck(st->active == TF_DIAG_ACTIVE_UNKNOWN && st->reason == TF_DIAG_REASON_BAD_RECORD, "bad size unknown+bad-record");
    }
    tf_diag_init(&g_tf_diag); uint32_t c1 = dm_tf_diag_copies(); tf_diag_case(40, &e);
    ck(dm_tf_diag_copies() == c1 + 1, "size 40 copies once");

    // D) real executor: OP_BEGIN/CALL/END from production text
    g_mode = TF_DIAG_MODE_ON;
    static uint8_t sub[1024];
    size_t sl = 0;
    { op_hdr h = {OP_TF_DIAG, 40}; memcpy(sub + sl, &h, 8); p_tf_diag x = {TF_DIAG_KIND_END, 0, 0, 0, 0xA0, 0}; memcpy(sub + sl + 8, &x, 32); sl += 40; }
    { op_hdr h = {OP_END, 8}; memcpy(sub + sl, &h, 8); sl += 8; }
    mlen = 0; s_begin(); s_tf(TF_DIAG_KIND_BEGIN, 0, 0, 0xA0, 0); s_call(sub); s_tf(TF_DIAG_KIND_BEGIN, 0, 0, 0xB0, 0); s_end();
    mtl_exec(mem);
    st = dm_tf_diag_snapshot();
    printf("E1 top->CALL[End]->continue: active=%s begin=%#llx events=%llu\n", tf_diag_active_name(st->active),
           (unsigned long long)st->begin_addr, dm_tf_diag_events());
    ck(st->active == TF_DIAG_ACTIVE_ACTIVE && st->begin_addr == 0xB0, "E1 call then continue");
    // E2: CALL [Bind0] must not reset active
    mlen = 0; { op_hdr h = {OP_TF_DIAG, 40}; memcpy(sub, &h, 8); p_tf_diag x = {TF_DIAG_KIND_BIND, 0, 0, 1, 0x2000, 0x100}; memcpy(sub + 8, &x, 32);
                h.op = OP_END; h.size = 8; memcpy(sub + 40, &h, 8); }
    mlen = 0; s_begin(); s_tf(TF_DIAG_KIND_BEGIN, 0, 0, 0xA0, 0); s_call(sub); s_end();
    mtl_exec(mem); st = dm_tf_diag_snapshot();
    printf("E2 CALL[Bind0]: active=%s bound=%s/%#llx\n", tf_diag_active_name(st->active), st->bound0_valid ? "valid" : "none",
           (unsigned long long)st->bound0_addr);
    ck(st->active == TF_DIAG_ACTIVE_ACTIVE && st->begin_addr == 0xA0 && st->bound0_valid && st->bound0_addr == 0x2000, "E2 bind inherits active");
    // E3: same sub-list with entry A / U / I gives different results
    { op_hdr h = {OP_TF_DIAG, 40}; memcpy(sub, &h, 8); p_tf_diag x = {TF_DIAG_KIND_END, 0, 0, 0, 0xA0, 0}; memcpy(sub + 8, &x, 32);
      h.op = OP_END; h.size = 8; memcpy(sub + 40, &h, 8); }
    mlen = 0; s_begin(); s_tf(TF_DIAG_KIND_BEGIN, 0, 0, 0xA0, 0); s_call(sub); s_end();    // entry A
    mtl_exec(mem); int a_act = dm_tf_diag_snapshot()->active;
    mlen = 0; s_begin(); s_call(sub); s_end();                                             // entry U
    mtl_exec(mem); int u_act = dm_tf_diag_snapshot()->active;
    mlen = 0; s_begin(); s_tf(TF_DIAG_KIND_BEGIN, 0, 0, 0xA0, 0); s_tf(TF_DIAG_KIND_END, 0, 0, 0xA0, 0); s_call(sub); s_end();  // entry I
    mtl_exec(mem); int i_act = dm_tf_diag_snapshot()->active;
    printf("E3 entry A/U/I -> %s/%s/%s\n", tf_diag_active_name(a_act), tf_diag_active_name(u_act), tf_diag_active_name(i_act));
    ck(a_act == TF_DIAG_ACTIVE_INACTIVE && u_act == TF_DIAG_ACTIVE_UNKNOWN && i_act == TF_DIAG_ACTIVE_UNKNOWN, "E3 entry-dependent");
    // E4: two top-level submissions -> new unknown each time
    mlen = 0; s_begin(); s_tf(TF_DIAG_KIND_BEGIN, 0, 0, 0xA0, 0); s_end(); mtl_exec(mem);
    int first = dm_tf_diag_snapshot()->active;
    mlen = 0; s_begin(); s_end(); mtl_exec(mem);
    int second = dm_tf_diag_snapshot()->active;
    printf("E4 two submissions: %s then %s\n", tf_diag_active_name(first), tf_diag_active_name(second));
    ck(first == TF_DIAG_ACTIVE_ACTIVE && second == TF_DIAG_ACTIVE_UNKNOWN, "E4 new submission unknown");
    // E5: real OP_DRAW/OP_DRAW_IDX bodies: skip=0 draws once each in order; skip=1 draws nothing; TF events still apply
    g_rc_skip = 0; g_draw_calls = g_draw_idx_calls = g_snap_calls = 0; memset(g_draw_mark, 0, sizeof g_draw_mark);
    mlen = 0; s_begin(); s_tf(TF_DIAG_KIND_BEGIN, 0, 0, 0xA0, 0); s_draw(); s_tf(TF_DIAG_KIND_END, 0, 0, 0xA0, 0); s_draw_idx(); s_end();
    mtl_exec(mem); st = dm_tf_diag_snapshot();
    printf("E5a skip=0: draws=%d idx=%d snap=%d order=%d,%d active=%s events=%llu\n", g_draw_calls, g_draw_idx_calls, g_snap_calls,
           g_draw_mark[0], g_draw_mark[1], tf_diag_active_name(st->active), (unsigned long long)dm_tf_diag_events());
    ck(g_draw_calls == 2 && g_draw_idx_calls == 1 && g_snap_calls == 2 && g_draw_mark[0] == 1 && g_draw_mark[1] == 2, "E5a draw order/count");
    ck(st->active == TF_DIAG_ACTIVE_INACTIVE && dm_tf_diag_events() == 2, "E5a TF applied around draws");
    g_rc_skip = 1; g_draw_calls = g_draw_idx_calls = g_snap_calls = 0;
    mlen = 0; s_begin(); s_tf(TF_DIAG_KIND_BEGIN, 0, 0, 0xA0, 0); s_draw(); s_tf(TF_DIAG_KIND_END, 0, 0, 0xA0, 0); s_draw_idx(); s_end();
    mtl_exec(mem); st = dm_tf_diag_snapshot();
    printf("E5b skip=1: draws=%d snap=%d active=%s events=%llu\n", g_draw_calls, g_snap_calls, tf_diag_active_name(st->active),
           (unsigned long long)dm_tf_diag_events());
    ck(g_draw_calls == 0 && g_snap_calls == 0, "E5b skip draws nothing");
    ck(st->active == TF_DIAG_ACTIVE_INACTIVE && dm_tf_diag_events() == 2, "E5b TF applied despite skip");
    g_rc_skip = 0;
    // E6: no TF events -> unknown
    mlen = 0; s_begin(); s_end(); mtl_exec(mem);
    ck(dm_tf_diag_snapshot()->active == TF_DIAG_ACTIVE_UNKNOWN, "E6 no events unknown");
    // E7: explicit fault event in a nested list (no invalid pointer is ever dereferenced)
    { op_hdr h = {OP_TF_DIAG, 40}; memcpy(sub, &h, 8); p_tf_diag x = {TF_DIAG_KIND_INVALID_OPAQUE, 0, 3, 0, 0, 0}; memcpy(sub + 8, &x, 32);
      h.op = OP_END; h.size = 8; memcpy(sub + 40, &h, 8); }
    mlen = 0; s_begin(); s_call(sub); s_end(); mtl_exec(mem); st = dm_tf_diag_snapshot();
    ck(st->active == TF_DIAG_ACTIVE_UNKNOWN && st->reason == TF_DIAG_REASON_INVALID_OPAQUE, "E7 nested fault -> unknown");

    // E8: saturating counters never wrap
    g_mode = TF_DIAG_MODE_ON; tf_diag_init(&g_tf_diag);
    g_tf_diag_events = UINT64_MAX - 1; g_tf_diag_copies = UINT64_MAX - 1;
    p_tf_diag ce = {TF_DIAG_KIND_BEGIN, 0, 0, 0, 0x10, 0};
    tf_diag_case(40, &ce); tf_diag_case(40, &ce);
    printf("E8 counters: events=%llu copies=%llu\n", (unsigned long long)dm_tf_diag_events(), (unsigned long long)dm_tf_diag_copies());
    ck(dm_tf_diag_events() == UINT64_MAX && dm_tf_diag_copies() == UINT64_MAX, "E8 saturating counters");

    // E9: off/invalid must leave shadow, depth and counters untouched for enter/case/leave
    for (int m = 0; m < 2; m++) {
        g_mode = m ? TF_DIAG_MODE_INVALID : TF_DIAG_MODE_OFF;
        memset(&g_tf_diag, 0x5a, sizeof g_tf_diag);
        g_tf_diag_events = 0x123456789abcdef0ull; g_tf_diag_copies = 0x0fedcba987654321ull; g_tf_diag_depth = 7;
        tf_diag_state sb; memcpy(&sb, &g_tf_diag, sizeof sb);
        uint64_t e0 = g_tf_diag_events, c0 = g_tf_diag_copies; int d0 = g_tf_diag_depth;
        tf_diag_enter(); tf_diag_case(40, (const void *)1); tf_diag_leave();
        ck(memcmp(&g_tf_diag, &sb, sizeof sb) == 0 && g_tf_diag_events == e0 && g_tf_diag_copies == c0 && g_tf_diag_depth == d0,
           m ? "invalid inert (enter/case/leave)" : "off inert (enter/case/leave)");
    }
    // E10: depth returns to 0 after a normal top-level and after a nested run, and two consecutive submissions do too
    g_mode = TF_DIAG_MODE_ON; g_tf_diag_depth = 0;
    mlen = 0; s_begin(); s_end(); mtl_exec(mem);
    ck(dm_tf_diag_depth() == 0, "E10 depth 0 after top-level");
    mlen = 0; s_begin(); s_call(sub); s_end(); mtl_exec(mem);
    ck(dm_tf_diag_depth() == 0, "E10 depth 0 after nested");
    mlen = 0; s_begin(); s_end(); mtl_exec(mem); mlen = 0; s_begin(); s_end(); mtl_exec(mem);
    ck(dm_tf_diag_depth() == 0, "E10 depth 0 after two submissions");
    printf("fails: %d\n", fails);
    return fails ? 1 : 0;
}
