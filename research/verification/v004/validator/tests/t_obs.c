// D04/D05: observer emit gate and the tf-intent formatter.
// mtl_fmt.inc / mtl_emit.inc / mtl_consumer.inc are verbatim v004 bodies; the verifier supplies
// the log sink, the gs-res config struct and the mode variable. The `emit:` label is dropped
// (the tail is inlined into emit_tail); nothing else in the tail changed.
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>

#include "nvn_tf_diag.h"
#include "nvn_kd_res.h"
#include "ops.inc"

static char g_log[16384]; static size_t g_log_n; static int g_log_lines;
static void MLOG(const char *fmt, ...) {
    va_list ap; va_start(ap, fmt);
    int n = vsnprintf(g_log + g_log_n, sizeof g_log - g_log_n, fmt, ap); va_end(ap);
    if (n > 0) { g_log_n += (size_t)n; g_log_lines++; if (g_log_n < sizeof g_log - 1) g_log[g_log_n++] = '\n'; }
}
static int count_has(const char *needle) {
    int c = 0; const char *p = g_log;
    while ((p = strstr(p, needle))) { const char *bol = p; while (bol > g_log && bol[-1] != '\n') bol--; if (!strncmp(bol, needle, strlen(needle))) c++; p++; }
    return c;
}

static struct { int on, valid, closed; char gs_hex[32]; } g_gsres;
static int g_mode = TF_DIAG_MODE_OFF;
int dm_tf_diag_get_mode(void) { return g_mode; }

#include "mtl_consumer.inc"
#include "mtl_fmt.inc"

static void emit_tail(kdr_record r) {
#include "mtl_emit.inc"   // production tail; ends at g_gsres.closed = 1
}

static int g_pass, g_fail;
static void ck(int c, const char *id, const char *name, const char *fmt, ...) {
    char d[400] = ""; if (fmt) { va_list ap; va_start(ap, fmt); vsnprintf(d, sizeof d, fmt, ap); va_end(ap); }
    if (c) { g_pass++; printf("PASS %s %s\n", id, name); } else { g_fail++; printf("FAIL %s %s | %s\n", id, name, d); }
}
static void fresh(const char *gs) {
    memset(g_log, 0, sizeof g_log); g_log_n = 0; g_log_lines = 0;
    g_gsres.on = 1; g_gsres.valid = 1; g_gsres.closed = 0;
    snprintf(g_gsres.gs_hex, sizeof g_gsres.gs_hex, "%s", gs ? gs : "aabbccdd");
    memset(&g_tf_diag, 0, sizeof g_tf_diag); tf_diag_init(&g_tf_diag);
    g_tf_diag_events = 0; g_tf_diag_copies = 0; g_tf_diag_depth = 0;
}
static kdr_record rec_of(kdr_result res) {
    kdr_record r; memset(&r, 0, sizeof r);
    r.result = res; r.frame = 7; r.pass = 3; r.drawkind = 1; r.prim = 4;
    r.count = 6; r.instances = 1; r.base_instance = 0;
    snprintf(r.vs, sizeof r.vs, "vs-key");
    snprintf(r.ps, sizeof r.ps, "ps-key_b");
    snprintf(r.ps_style, sizeof r.ps_style, "_b");
    return r;
}

int main(void) {
    setvbuf(stdout, NULL, _IONBF, 0);

    // D04: only a KDR_HIT line, with TF ON, may be followed by exactly one tf-intent line.
    const kdr_result all[] = { KDR_HIT, KDR_TARGET_NOT_OBTAINED, KDR_NO_GEOMETRY_SOURCE,
                               KDR_IDENTITY_UNAVAILABLE, KDR_GS_KEY_MISMATCH, KDR_INVALID_CONFIG, KDR_DIAG_ERROR };
    const char *names[] = { "hit", "target-not-obtained", "no-geometry-source", "identity-unavailable",
                            "gs-key-mismatch", "invalid-config", "diagnostic-error" };
    for (unsigned i = 0; i < sizeof all / sizeof *all; i++) {
        fresh("aabbccdd"); g_mode = TF_DIAG_MODE_ON;
        emit_tail(rec_of(all[i]));
        int tf = count_has("[tf-intent] frame=");
        int want = (all[i] == KDR_HIT) ? 1 : 0;
        ck(tf == want, "D04", all[i] == KDR_HIT ? "KDR_HIT + TF ON: exactly one tf-intent line"
                                                : "non-HIT result must not emit a tf-intent line",
           "result=%s tf_lines=%d want=%d", names[i], tf, want);
    }
    // TF OFF: gs-res line still emitted, no intent line.
    fresh("aabbccdd"); g_mode = TF_DIAG_MODE_OFF;
    emit_tail(rec_of(KDR_HIT));
    ck(count_has("[gs-res] result=hit") == 1 && count_has("[tf-intent]") == 0, "D04",
       "TF OFF: gs-res line present, zero tf-intent lines", "tf=%d", count_has("[tf-intent]"));

    // D05: formatter content and domains.
    fresh("aabbccdd"); g_mode = TF_DIAG_MODE_ON;
    tf_diag_state s; memset(&s, 0, sizeof s); tf_diag_init(&s);
    s.active = TF_DIAG_ACTIVE_ACTIVE; s.pause = TF_DIAG_PAUSE_PAUSED; s.reason = TF_DIAG_REASON_BEGIN_WHILE_PAUSED;
    s.seq = UINT64_MAX; s.bound0_valid = 0; s.begin_addr = 0; s.end_addr = 0; s.draw_addr = 0;
    memcpy(&g_tf_diag, &s, sizeof s); g_tf_diag_events = 2; g_tf_diag_copies = 2; g_tf_diag_depth = 0;
    char b[1024]; kdr_record rr = rec_of(KDR_HIT); int ok = kd_tf_intent_line(b, sizeof b, &rr);
    ck(ok == 1 && strstr(b, "final_pass_association=none") && strstr(b, "interpretation=observed-replay-intent"),
       "D05", "line names the association as none and the scope as observed replay intent", "%s", b);
    ck(strstr(b, "active=active") && strstr(b, "pause=paused") && strstr(b, "reason=begin-while-paused") &&
       strstr(b, "seq=18446744073709551615") && strstr(b, "events=2") && strstr(b, "copies=2") && strstr(b, "depth=0"),
       "D05", "active/pause/reason/seq(MAX)/events/copies/depth printed in their domains", "%s", b);
    ck(strstr(b, "bound0=none") && !strstr(b, "bound0=valid"), "D05", "invalidated binding is printed as none, never as valid", "%s", b);
    ck(strstr(b, "begin=0") && strstr(b, "end=0") && strstr(b, "draw=0") && strstr(b, "bound0=none"), "D05",
       "begin/end/draw are separate fields; no binding is implied", "%s", b);

    s.bound0_valid = 1; s.bound0_addr = 0xDEADBEEF; s.bound0_size = 42; memcpy(&g_tf_diag, &s, sizeof s);
    { kdr_record r2 = rec_of(KDR_HIT); ok = kd_tf_intent_line(b, sizeof b, &r2); }
    ck(ok == 1 && strstr(b, "bound0=valid addr=0xdeadbeef size=42"), "D05", "valid binding prints addr/size in hex/decimal", "%s", b);

    s.seq = 0; s.reason = TF_DIAG_REASON_NONE; memcpy(&g_tf_diag, &s, sizeof s);
    g_tf_diag_depth = -3;
    { kdr_record r2 = rec_of(KDR_HIT); ok = kd_tf_intent_line(b, sizeof b, &r2); }
    ck(ok == 1 && strstr(b, "depth=-3") && strstr(b, "reason=none"), "D05", "negative depth and reason=none stay in-domain", "%s", b);

    kdr_record r = rec_of(KDR_HIT); snprintf(r.ps, sizeof r.ps, "ps-key_bf");
    ok = kd_tf_intent_line(b, sizeof b, &r);
    ck(ok == 1 && strstr(b, "ps=ps-key_bf") && strstr(b, "vs=vs-key"), "D05", "key tokens (_b/_bf) are printed verbatim", "%s", b);

    { kdr_record r3 = rec_of(KDR_HIT); ok = kd_tf_intent_line(b, 40, &r3); }
    ck(ok == 0, "D05", "short buffer reports failure instead of a partial line", "ok=%d buf=%s", ok, b);
    { kdr_record r4 = rec_of(KDR_HIT); ok = kd_tf_intent_line(NULL, sizeof b, &r4); }
    ck(ok == 0, "D05", "null buffer is rejected", NULL);

    // D04 integration point: the emit tail closes the observer after one line (one-shot).
    fresh("aabbccdd"); g_mode = TF_DIAG_MODE_ON; emit_tail(rec_of(KDR_HIT));
    ck(g_gsres.closed == 1, "D04", "emit tail closes the observer after the line (one-shot)", "closed=%d", g_gsres.closed);

    // The exact _bf / otherPS failure shape: psstyle=2 => result TARGET_NOT_OBTAINED, still a shared exit.
    { kdr_record rb = rec_of(KDR_TARGET_NOT_OBTAINED);
      snprintf(rb.ps, sizeof rb.ps, "ps-key_bf"); snprintf(rb.ps_style, sizeof rb.ps_style, "_bf");
      char t[1024]; int ok2 = kd_tf_intent_line(t, sizeof t, &rb);
      ck(ok2 == 1 && strstr(t, "ps=ps-key_bf"), "D05", "otherPS/_bf shapes are printable verbatim", "%s", t); }

    printf("RESULT pass=%d fail=%d\n", g_pass, g_fail);
    return g_fail ? 1 : 0;
}
