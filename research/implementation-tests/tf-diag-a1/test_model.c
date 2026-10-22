// A1 CPU model cases: transition table, payload validation, switch parsing, sequence saturation and a small stream
// executor that interprets OP_BEGIN/CALL/END/TF events. This is a model of observed replay intent, NOT production
// mtl_exec and not NVN semantics: passing here proves the model's own rules only.
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include "nvn_tf_diag.h"

static int fails;
static void ck(int cond, const char *what) { if (!cond) { printf("FAIL %s\n", what); fails++; } }
static p_tf_diag ev(uint32_t k, int32_t i, int32_t c, uint64_t a, uint64_t s) {
    p_tf_diag e; memset(&e, 0, sizeof e); e.kind = k; e.index = i; e.count = c; e.addr = a; e.size = s; return e;
}
static void ap(tf_diag_state *s, p_tf_diag e) { tf_diag_apply(s, &e); }
static void show(const char *name, const tf_diag_state *s) {
    printf("%-8s active=%s pause=%s reason=%u bound0=%s addr=%#llx size=%llu gate=%d\n", name,
           tf_diag_active_name(s->active), tf_diag_pause_name(s->pause), s->reason,
           s->bound0_valid ? "valid" : "none", (unsigned long long)s->bound0_addr, (unsigned long long)s->bound0_size,
           tf_diag_gate_allows(s));
}
// CPU stream executor: BEGIN does nothing, CALL inherits the caller's state, END returns to the caller without resetting,
// TF events apply in order. Deliberately not production mtl_exec (no handles, no allocation, no barriers).
enum { I_BEGIN, I_CALL, I_END, I_TF };
typedef struct item { int op; const struct lst *sub; p_tf_diag e; } item;
typedef struct lst { const item *it; int n; } lst;
static void exec(const lst *l, tf_diag_state *s, int depth) {
    if (!l || depth > 8) return;
    for (int i = 0; i < l->n; i++) switch (l->it[i].op) {
    case I_BEGIN: break;
    case I_CALL: exec(l->it[i].sub, s, depth + 1); break;
    case I_END: return;
    case I_TF: tf_diag_apply(s, &l->it[i].e); break;
    }
}
int main(void) {
    // switch parsing
    ck(tf_diag_parse_mode(NULL) == TF_DIAG_MODE_OFF, "null off");
    ck(tf_diag_parse_mode("") == TF_DIAG_MODE_OFF, "empty off");
    ck(tf_diag_parse_mode("0") == TF_DIAG_MODE_OFF, "0 off");
    ck(tf_diag_parse_mode("1") == TF_DIAG_MODE_ON, "1 on");
    ck(tf_diag_parse_mode("01") == TF_DIAG_MODE_INVALID, "01 invalid");
    ck(tf_diag_parse_mode("true") == TF_DIAG_MODE_INVALID, "true invalid");

    tf_diag_state s;
    // C1: no events -> unknown, gate refused
    tf_diag_init(&s); show("C1", &s);
    ck(s.active == TF_DIAG_ACTIVE_UNKNOWN && !tf_diag_gate_allows(&s), "C1 unknown");

    // C2: Begin -> active/running, End -> inactive, gate allows
    tf_diag_init(&s);
    ap(&s, ev(TF_DIAG_KIND_BEGIN, 0, 0, 0x1000, 0));
    ck(s.active == TF_DIAG_ACTIVE_ACTIVE && s.pause == TF_DIAG_PAUSE_RUNNING && !tf_diag_gate_allows(&s), "C2 begin");
    ap(&s, ev(TF_DIAG_KIND_END, 0, 0, 0x1000, 0));
    show("C2", &s);
    ck(s.active == TF_DIAG_ACTIVE_INACTIVE && tf_diag_gate_allows(&s), "C2 end->inactive");

    // C3: End without Begin -> unknown (not inactive)
    tf_diag_init(&s); ap(&s, ev(TF_DIAG_KIND_END, 0, 0, 0x1000, 0)); show("C3", &s);
    ck(s.active != TF_DIAG_ACTIVE_INACTIVE && s.reason == TF_DIAG_REASON_END_WITHOUT_BEGIN, "C3 end-no-begin");

    // C4: Pause without Begin -> unknown
    tf_diag_init(&s); ap(&s, ev(TF_DIAG_KIND_PAUSE, 0, 0, 0x1000, 0)); show("C4", &s);
    ck(s.active == TF_DIAG_ACTIVE_UNKNOWN && s.reason == TF_DIAG_REASON_PAUSE_WITHOUT_ACTIVE, "C4 pause-no-begin");

    // C5: Begin/Pause/Resume/End
    tf_diag_init(&s);
    ap(&s, ev(TF_DIAG_KIND_BEGIN, 0, 0, 1, 0));
    ap(&s, ev(TF_DIAG_KIND_PAUSE, 0, 0, 1, 0));
    ck(s.active == TF_DIAG_ACTIVE_ACTIVE && s.pause == TF_DIAG_PAUSE_PAUSED, "C5 paused");
    ap(&s, ev(TF_DIAG_KIND_BEGIN, 0, 0, 1, 0));   // repeated Begin while paused -> invalid
    ck(s.active == TF_DIAG_ACTIVE_UNKNOWN && s.reason == TF_DIAG_REASON_BEGIN_WHILE_PAUSED, "C5 repeat begin");
    tf_diag_init(&s);
    ap(&s, ev(TF_DIAG_KIND_BEGIN, 0, 0, 1, 0));
    ap(&s, ev(TF_DIAG_KIND_PAUSE, 0, 0, 1, 0));
    ap(&s, ev(TF_DIAG_KIND_RESUME, 0, 0, 1, 0));
    ap(&s, ev(TF_DIAG_KIND_END, 0, 0, 1, 0));
    show("C5", &s);
    ck(s.active == TF_DIAG_ACTIVE_INACTIVE && tf_diag_gate_allows(&s), "C5 sequence");

    // C6: sublist L=[End] with three entry states; L2=[Bind0] inherits caller active
    item l_end_i[1] = {{I_TF, NULL, {0}}}; item l_bind_i[1] = {{I_TF, NULL, {0}}};
    l_end_i[0].e = ev(TF_DIAG_KIND_END, 0, 0, 9, 0);
    l_bind_i[0].e = ev(TF_DIAG_KIND_BIND, 0, 1, 0x2000, 0x100);
    lst L = {l_end_i, 1}, L2 = {l_bind_i, 1};
    item call_end[1] = {{I_CALL, &L, {0}}}, call_bind[1] = {{I_CALL, &L2, {0}}};
    lst M = {call_end, 1}, M2 = {call_bind, 1};
    tf_diag_init(&s); s.active = TF_DIAG_ACTIVE_ACTIVE; s.pause = TF_DIAG_PAUSE_RUNNING; exec(&M, &s, 0); show("C6a", &s);
    ck(s.active == TF_DIAG_ACTIVE_INACTIVE, "C6 entry active -> inactive");
    tf_diag_init(&s); exec(&M, &s, 0); show("C6b", &s);
    ck(s.active == TF_DIAG_ACTIVE_UNKNOWN && s.reason == TF_DIAG_REASON_END_WITHOUT_BEGIN, "C6 entry unknown -> unknown");
    tf_diag_init(&s); s.active = TF_DIAG_ACTIVE_INACTIVE; exec(&M, &s, 0); show("C6c", &s);
    ck(s.active == TF_DIAG_ACTIVE_UNKNOWN && s.reason == TF_DIAG_REASON_END_WHILE_INACTIVE, "C6 entry inactive -> unknown");
    tf_diag_init(&s); s.active = TF_DIAG_ACTIVE_ACTIVE; s.pause = TF_DIAG_PAUSE_RUNNING; exec(&M2, &s, 0); show("C6d", &s);
    ck(s.active == TF_DIAG_ACTIVE_ACTIVE && s.pause == TF_DIAG_PAUSE_RUNNING && s.bound0_valid, "C6 bind inherits active");

    // C7: opaque draw -> unknown
    tf_diag_init(&s); ap(&s, ev(TF_DIAG_KIND_DRAW_OPAQUE, 0, 0, 0x3000, 0)); show("C7", &s);
    ck(s.active == TF_DIAG_ACTIVE_UNKNOWN && s.reason == TF_DIAG_REASON_DRAW_OPAQUE, "C7 draw opaque");

    // C8: a stream recorded while off carries no events -> unknown
    tf_diag_init(&s); show("C8", &s);
    ck(s.active == TF_DIAG_ACTIVE_UNKNOWN && !tf_diag_gate_allows(&s), "C8 off stream unknown");

    // C9: explicit fault event invalidates a known bound
    tf_diag_init(&s);
    ap(&s, ev(TF_DIAG_KIND_BIND, 0, 1, 0x4000, 0x80));
    ck(s.bound0_valid == 1, "C9 bind valid");
    ap(&s, ev(TF_DIAG_KIND_INVALID_OPAQUE, 3, 0, 0, 0)); show("C9", &s);
    ck(s.active == TF_DIAG_ACTIVE_UNKNOWN && s.bound0_valid == 0, "C9 fault invalidates bound");

    // C10: skipped draw emits nothing; events apply in recorded order
    tf_diag_init(&s);
    ap(&s, ev(TF_DIAG_KIND_BEGIN, 0, 0, 5, 0));
    /* draw skipped by conditional rendering: no event, no model change */
    ck(s.active == TF_DIAG_ACTIVE_ACTIVE, "C10 skip keeps state");
    ap(&s, ev(TF_DIAG_KIND_END, 0, 0, 5, 0));
    ck(s.active == TF_DIAG_ACTIVE_INACTIVE, "C10 end after skip");
    ap(&s, ev(TF_DIAG_KIND_DRAW_OPAQUE, 0, 0, 5, 0));
    ck(s.active == TF_DIAG_ACTIVE_UNKNOWN, "C10 order matters");

    // payload / overflow / malicious fields
    tf_diag_init(&s);
    p_tf_diag bad = ev(TF_DIAG_KIND_BIND, 0, 1, 0x10, 0x10); bad.flags = 1; tf_diag_apply(&s, &bad);
    ck(s.active == TF_DIAG_ACTIVE_UNKNOWN && s.reason == TF_DIAG_REASON_BAD_PAYLOAD, "flags != 0");
    tf_diag_init(&s); ap(&s, ev(TF_DIAG_KIND_BIND, 0, 1, UINT64_MAX - 1, 4));
    ck(s.reason == TF_DIAG_REASON_BAD_PAYLOAD, "addr+size overflow");
    tf_diag_init(&s); ap(&s, ev(TF_DIAG_KIND_BIND, 5, 1, 0x10, 0x10));
    ck(s.reason == TF_DIAG_REASON_INDEX_UNSUPPORTED && s.bound0_valid == 0, "index 5 opaque");
    tf_diag_init(&s); ap(&s, ev(TF_DIAG_KIND_BIND, 0, 1, 0x10, 0));
    ck(s.reason == TF_DIAG_REASON_BAD_PAYLOAD, "bind size 0");
    tf_diag_init(&s); ap(&s, ev(TF_DIAG_KIND_BIND, 0, 7, 0x10, 0x10));
    ck(s.reason == TF_DIAG_REASON_BAD_PAYLOAD, "bind count 7");
    tf_diag_init(&s); ap(&s, ev(TF_DIAG_KIND_BIND_PLURAL_OPAQUE, 0, 3, 0, 0));
    ck(s.reason == TF_DIAG_REASON_PLURAL_OPAQUE && s.bound0_valid == 0, "plural opaque");
    tf_diag_init(&s); p_tf_diag k = ev(99, 0, 0, 0, 0); tf_diag_apply(&s, &k);
    ck(s.active == TF_DIAG_ACTIVE_UNKNOWN, "unknown kind");

    // saturation: never wraps, becomes unknown
    tf_diag_init(&s); s.seq = UINT64_MAX - 1;
    ap(&s, ev(TF_DIAG_KIND_BEGIN, 0, 0, 1, 0));
    ck(s.seq == UINT64_MAX && !s.saturated, "seq to max");
    ap(&s, ev(TF_DIAG_KIND_END, 0, 0, 1, 0));
    ck(s.saturated && s.active == TF_DIAG_ACTIVE_UNKNOWN && s.reason == TF_DIAG_REASON_SEQ_SATURATED, "seq saturates to unknown");

    // C11: repeat Begin while running -> invalid (previously it silently stayed active)
    tf_diag_init(&s);
    ap(&s, ev(TF_DIAG_KIND_BEGIN, 0, 0, 0x10, 0));
    ap(&s, ev(TF_DIAG_KIND_BEGIN, 0, 0, 0x10, 0)); show("C11a", &s);
    ck(s.active == TF_DIAG_ACTIVE_UNKNOWN && s.reason == TF_DIAG_REASON_BEGIN_WHILE_ACTIVE, "C11 double begin running");
    ap(&s, ev(TF_DIAG_KIND_END, 0, 0, 0x10, 0)); show("C11b", &s);
    ck(s.active == TF_DIAG_ACTIVE_UNKNOWN && !tf_diag_gate_allows(&s), "C11 end after double begin stays unknown");

    // C12: saturation is sticky: no later event can make the state valid again
    tf_diag_init(&s);
    ap(&s, ev(TF_DIAG_KIND_BIND, 0, 1, 0x4000, 0x80));
    s.seq = UINT64_MAX - 1;
    ap(&s, ev(TF_DIAG_KIND_BEGIN, 0, 0, 0x11, 0));   // seq -> MAX, still not saturated
    ck(!s.saturated && s.seq == UINT64_MAX, "C12 seq reaches max");
    ap(&s, ev(TF_DIAG_KIND_END, 0, 0, 0x11, 0));     // next tick saturates
    ck(s.saturated && s.active == TF_DIAG_ACTIVE_UNKNOWN && s.reason == TF_DIAG_REASON_SEQ_SATURATED, "C12 saturates to unknown");
    int32_t keep_index = s.last_index;
    p_tf_diag after[5];
    after[0] = ev(TF_DIAG_KIND_BEGIN, 0, 0, 0x22, 0);
    after[1] = ev(TF_DIAG_KIND_BIND, 5, 1, 0x30, 0x40);
    after[2] = ev(TF_DIAG_KIND_PAUSE, 0, 0, 0x22, 0);
    after[3] = ev(TF_DIAG_KIND_RESUME, 0, 0, 0x22, 0);
    after[4] = ev(TF_DIAG_KIND_END, 0, 0, 0x22, 0);
    for (int i = 0; i < 5; i++) {
        tf_diag_apply(&s, &after[i]);
        if (!(s.saturated && s.active == TF_DIAG_ACTIVE_UNKNOWN && s.pause == TF_DIAG_PAUSE_UNKNOWN &&
              !s.bound0_valid && s.reason == TF_DIAG_REASON_SEQ_SATURATED && s.seq == UINT64_MAX && !tf_diag_gate_allows(&s))) {
            printf("FAIL C12 sticky after event %d\n", i); fails++;
        }
    }
    show("C12", &s);
    ck(s.last_index == keep_index, "C12 last event snapshot frozen after saturation");

    tf_diag_init(&s);
    ck(sizeof(p_tf_diag) == 32 && offsetof(p_tf_diag, addr) == 16, "payload layout");
    printf("fails: %d\n", fails);
    return fails ? 1 : 0;
}
