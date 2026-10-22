// ---- TF-DIAG-A2A-BEGIN ----
// Observed replay intent only: this never writes buffers, never resolves resources and never logs per event. Every hook
// first reads the A1 mode getter; unless DM_NVN_TF_DIAG was literally "1" at startup the hooks do nothing at all (no
// state change, no payload read, no counting). The shadow belongs to the replay context: it is initialised to unknown
// once per top-level submission (mtl_exec depth 0) and is inherited across nested OP_CALL, never reset by OP_BEGIN/OP_END.
extern int dm_tf_diag_get_mode(void);   // defined in hle_nvn.c; A1 keeps it fixed at OFF with no startup enable
static tf_diag_state g_tf_diag;         // observed replay intent of the current submission
static uint64_t g_tf_diag_events;       // events consumed in this submission (saturating diagnostic counter, on-mode only)
static uint64_t g_tf_diag_copies;       // payload copies actually performed (saturating, on-mode only)
static int g_tf_diag_depth;             // mtl_exec recursion depth; 0 on entry means top level
static int tf_diag_on(void) { return dm_tf_diag_get_mode() == TF_DIAG_MODE_ON; }
static void tf_diag_count(uint64_t *c) { if (*c != UINT64_MAX) (*c)++; }   // saturating: never wraps
static int tf_diag_enter(void) {        // returns nonzero when this mtl_exec call is the top level of a submission
    if (!tf_diag_on()) return 0;
    if (g_tf_diag_depth++ == 0) { tf_diag_init(&g_tf_diag); g_tf_diag_events = 0; g_tf_diag_copies = 0; return 1; }
    return 0;
}
static void tf_diag_leave(void) { if (tf_diag_on() && g_tf_diag_depth > 0) g_tf_diag_depth--; }
static void tf_diag_case(uint32_t hsize, const void *a) {
    if (!tf_diag_on()) return;                           // off/invalid: no payload read, no state change, no counters
    tf_diag_count(&g_tf_diag_events);
    if (hsize != (uint32_t)(sizeof(op_hdr) + TF_DIAG_PAYLOAD) || (((uintptr_t)a) & 7u) != 0) {
        tf_diag_mark_unknown(&g_tf_diag, TF_DIAG_REASON_BAD_RECORD);   // bad size/alignment: never touch the payload
        tf_diag_tick(&g_tf_diag);
        return;
    }
    p_tf_diag e;
    memcpy(&e, a, sizeof e);                             // 32 bytes copied into a local; never cast the stream
    tf_diag_count(&g_tf_diag_copies);   // counted only after a real copy
    tf_diag_apply(&g_tf_diag, &e);
}
const tf_diag_state *dm_tf_diag_snapshot(void) { return &g_tf_diag; }   // read-only, for CPU tests: observed replay intent
uint64_t dm_tf_diag_events(void) { return g_tf_diag_events; }
uint64_t dm_tf_diag_copies(void) { return g_tf_diag_copies; }
int dm_tf_diag_depth(void) { return g_tf_diag_depth; }   // read-only for CPU tests
// ---- TF-DIAG-A2A-END ----
