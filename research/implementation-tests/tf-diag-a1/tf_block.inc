// ---------- Transform-feedback diagnostic events (A1: recording adapters only, default off) ----------
// One OP_TF_DIAG record per NVN transform-feedback call; the 32-byte payload and the conservative CPU model live in
// nvn_tf_diag.h. Off or invalid mode returns before the command-buffer lookup and before any allocation, so an existing
// command sequence records byte-identically. These adapters are NOT registered in nvn_init_slots and nvn_mtl.m has no
// case for OP_TF_DIAG in A1: there is no producer in the real process and no replay behavior yet (A1 is not enabled).
// The plural adapter never reads the caller's ranges: it records first/count only and marks the bound opaque.
static int g_tf_diag_mode = TF_DIAG_MODE_OFF;
void dm_tf_diag_set_mode(int mode) { g_tf_diag_mode = mode; }
int dm_tf_diag_get_mode(void) { return g_tf_diag_mode; }
static void tf_diag_emit(NVNcommandBuffer *c, uint32_t kind, int32_t index, int32_t count, uint64_t addr, uint64_t size) {
    if (g_tf_diag_mode != TF_DIAG_MODE_ON || !c) return;
    p_tf_diag e; memset(&e, 0, sizeof e);
    e.kind = kind; e.flags = 0; e.index = index; e.count = count; e.addr = addr; e.size = size;
    p_tf_diag *o = (p_tf_diag *)rec(c, OP_TF_DIAG, sizeof *o);
    *o = e;
}
void dm_tf_diag_bind(NVNcommandBuffer *c, int index, NVNbufferAddress addr, size_t size) { tf_diag_emit(c, TF_DIAG_KIND_BIND, index, 1, (uint64_t)addr, (uint64_t)size); }
void dm_tf_diag_bind_plural(NVNcommandBuffer *c, int first, int n, const NVNbufferRange *r) { (void)r; tf_diag_emit(c, TF_DIAG_KIND_BIND_PLURAL_OPAQUE, first, n, 0, 0); }
void dm_tf_diag_begin(NVNcommandBuffer *c, NVNbufferAddress addr) { tf_diag_emit(c, TF_DIAG_KIND_BEGIN, 0, 0, (uint64_t)addr, 0); }
void dm_tf_diag_end(NVNcommandBuffer *c, NVNbufferAddress addr) { tf_diag_emit(c, TF_DIAG_KIND_END, 0, 0, (uint64_t)addr, 0); }
void dm_tf_diag_pause(NVNcommandBuffer *c, NVNbufferAddress addr) { tf_diag_emit(c, TF_DIAG_KIND_PAUSE, 0, 0, (uint64_t)addr, 0); }
void dm_tf_diag_resume(NVNcommandBuffer *c, NVNbufferAddress addr) { tf_diag_emit(c, TF_DIAG_KIND_RESUME, 0, 0, (uint64_t)addr, 0); }
void dm_tf_diag_draw(NVNcommandBuffer *c, NVNdrawPrimitive prim, NVNbufferAddress addr) { tf_diag_emit(c, TF_DIAG_KIND_DRAW_OPAQUE, (int32_t)prim, 0, (uint64_t)addr, 0); }
void dm_tf_diag_invalid(NVNcommandBuffer *c, int32_t index, int32_t count) { tf_diag_emit(c, TF_DIAG_KIND_INVALID_OPAQUE, index, count, 0, 0); }
