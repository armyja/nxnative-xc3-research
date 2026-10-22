// V002-S S01: executable store-lookahead fallback chain.
// sdx_decide() and its ledger types are extracted verbatim from the frozen v002 snapshot;
// sdx_bucket() is a disclosed verifier stub (single bucket) and sd_finish()'s decision part
// (4 lines) is transcribed without the Metal set*StoreAction calls.
#include <stdio.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include <stdarg.h>

#include "nvn_tf_diag.h"
#include "ops.inc"

static int g_mode;
int dm_tf_diag_get_mode(void) { return g_mode; }

#include "a2b_init.inc"
#include "hoist.inc"
#include "sd_att.inc"
#include "sd_need.inc"
#include "sdx_core.inc"
#include "sdx_op_state.inc"
#include "g_exec_cur.inc"

// Stub: the real sdx_bucket() is a 2048-entry open-addressing hash over texture serials.
// The decide() body only needs "this serial has a bucket"; all events go to bucket 0 here.
static int sdx_bucket(uint64_t ser, int add) { (void)ser; (void)add; return 0; }
#include "sdx_decide.inc"

static int g_pass, g_fail;
static void ck(int c, const char *id, const char *name, const char *fmt, ...) {
    char d[400] = ""; if (fmt) { va_list ap; __builtin_va_start(ap, fmt); vsnprintf(d, sizeof d, fmt, ap); __builtin_va_end(ap); }
    if (c) { g_pass++; printf("PASS %s %s\n", id, name); } else { g_fail++; printf("FAIL %s %s | %s\n", id, name, d); }
}

// Transcribed from sd_finish(): the decision only. sd_need(...,6) is the code path taken when
// sdx_decide() returns 0 ("index unavailable -> always write back").
static int finish_dead(void) {
    uint8_t nst[9];
    for (int i = 0; i < g_nsd; i++) { g_sd[i].state = 0; g_sd[i].why = 0; }
    if (sdx_decide(nst)) { for (int i = 0; i < g_nsd; i++) if (nst[i] == 2) g_sd[i].state = 2; else sd_need(&g_sd[i], nst[i] >> 2); }
    else for (int i = 0; i < g_nsd; i++) sd_need(&g_sd[i], 6);
    return g_sd[0].state == 2;   // dead == MTLStoreActionDontCare
}

static uint8_t op0[8];
static sdx_ev g_idx[8];
static const uint8_t *g_optab[8];
static void setup(sdx_ev *ev, int n, int ok) {
    memset(g_sd, 0, sizeof g_sd); g_nsd = 1; g_sd[0].ser = 0xABC; g_sd[0].lv = 0; g_sd[0].sl = 0; g_sd[0].idx = 0;
    g_sdx_ok = ok; g_exec_seq = 1; g_exec_cur = op0; g_optab[0] = op0; g_sdx_op = g_optab; g_sdx = g_idx;
    memset(g_sdx_bst, 0, sizeof g_sdx_bst); g_sdx_bst[0] = 0; g_sdx_bst[1] = (uint32_t)n;
    for (int i = 0; i < n; i++) g_sdx[i] = ev[i];
    g_hoist_n = 0; g_mode = TF_DIAG_MODE_ON;
}

int main(void) {
    setvbuf(stdout, NULL, _IONBF, 0);
    static sdx_ev ev[4];

    // 1. Control: a CLEAR after the pass ended makes the attachment redundant -> the harness
    //    really reaches a discard candidate (otherwise a "keep" test would have no power).
    memset(ev, 0, sizeof ev);
    ev[0] = (sdx_ev){0, 0 /*rtseq == P*/, 0xABC, NULL, 0, 0, SDX_CLEAR, 0, 0, 0};
    setup(ev, 1, 1);
    int dead = finish_dead();
    ck(dead == 1 && g_sd[0].state == 2, "S01", "control (index valid, CLEAR at P): decide -> redundant, discard reached", "dead=%d state=%d", dead, g_sd[0].state);

    // 2. TF boundary invalidates the index (g_sdx_ok=0, as sdx_walk does) -> decide returns 0
    //    -> sd_need(...,6) -> store. This is the fallback chain, not a string inference.
    setup(ev, 1, 0);
    dead = finish_dead();
    ck(dead == 0 && g_sd[0].state == 1 && g_sd[0].why == 6, "S01", "TF-invalidated index: full-store fallback (why=6) keeps the attachment", "dead=%d state=%d why=%d", dead, g_sd[0].state, g_sd[0].why);

    // 3. A READ event still forces a store on a valid index (sanity of the same harness).
    memset(ev, 0, sizeof ev);
    ev[0] = (sdx_ev){0, 0, 0xABC, NULL, 0, 0, SDX_READ, 0, 0, 1};
    setup(ev, 1, 1);
    dead = finish_dead();
    ck(dead == 0 && g_sd[0].why == 1, "S01", "valid index + READ: store with why=1", "dead=%d why=%d", dead, g_sd[0].why);

    // 4. A hoist-skipped event cannot be used as discard evidence inside decide().
    memset(ev, 0, sizeof ev);
    ev[0] = (sdx_ev){0, 0, 0xABC, op0, 0, 0, SDX_CLEAR, 0, 0, 0};
    setup(ev, 1, 1);
    g_hoist_skip[0] = op0; g_hoist_n = 1;
    dead = finish_dead();
    ck(dead == 0 && g_sd[0].why == 5, "S01", "event on a hoist-skipped op is ignored -> undecided(5) -> store", "dead=%d why=%d", dead, g_sd[0].why);

    // 5. TF boundary with an otherwise-discardable ledger: still keep.
    memset(ev, 0, sizeof ev);
    ev[0] = (sdx_ev){0, 0, 0xABC, NULL, 0, 0, SDX_CLEAR, 0, 0, 0};
    setup(ev, 1, 1);
    g_sdx_ok = 0;    // what sdx_walk does when it meets OP_TF_DIAG
    dead = finish_dead();
    ck(dead == 0, "S01", "discardable ledger + TF-invalidation cannot discard (conservative keep)", "dead=%d", dead);

    printf("RESULT pass=%d fail=%d\n", g_pass, g_fail);
    return g_fail ? 1 : 0;
}
