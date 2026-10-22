// A1 off/inert verification: the real rec() body and the real TF adapter block are sliced out of the repo sources by
// extract.py (rec.inc / tf_block.inc). Recording the same pre-existing command sequence with and without the seven TF
// adapter calls, in off and invalid mode, must produce byte-identical streams and no extra allocations.
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include "nvn_tf_diag.h"

typedef struct NVNcommandBuffer NVNcommandBuffer;
typedef uint64_t NVNbufferAddress;
typedef struct { NVNbufferAddress address; uint64_t size; } NVNbufferRange;
typedef enum { NVN_DRAW_POINTS = 0 } NVNdrawPrimitive;

typedef struct { uint8_t *base; size_t cap, cur; int alloc_calls; } fake_cmd;
#define CB(c) ((fake_cmd *)(c))
static void put_hdr(uint8_t *p, uint32_t op, uint32_t size) { memcpy(p, &op, 4); memcpy(p + 4, &size, 4); }
static void *cmd_alloc(fake_cmd *o, uint32_t size) {
    o->alloc_calls++;
    size_t at = (o->cur + 7) & ~(size_t)7;
    if (at + size > o->cap) { fprintf(stderr, "fake command memory full\n"); exit(2); }
    o->cur = at + size;
    return o->base + at;
}

// Same signatures as nvn_protos.h: the extracted adapter block asserts these with _Generic at compile time.
typedef void (*NVNT_nvnCommandBufferBindTransformFeedbackBuffer)(NVNcommandBuffer*, int, NVNbufferAddress, size_t);
typedef void (*NVNT_nvnCommandBufferBindTransformFeedbackBuffers)(NVNcommandBuffer*, int, int, const NVNbufferRange*);
typedef void (*NVNT_nvnCommandBufferBeginTransformFeedback)(NVNcommandBuffer*, NVNbufferAddress);
typedef void (*NVNT_nvnCommandBufferEndTransformFeedback)(NVNcommandBuffer*, NVNbufferAddress);
typedef void (*NVNT_nvnCommandBufferPauseTransformFeedback)(NVNcommandBuffer*, NVNbufferAddress);
typedef void (*NVNT_nvnCommandBufferResumeTransformFeedback)(NVNcommandBuffer*, NVNbufferAddress);
typedef void (*NVNT_nvnCommandBufferDrawTransformFeedback)(NVNcommandBuffer*, NVNdrawPrimitive, NVNbufferAddress);

#define OP_TF_DIAG 42   /* nvn_obj.h: OP_RENDER_COND=41, OP_TF_DIAG=42, OP_COUNT_=43 (extract.py asserts) */
#include "rec.inc"
#include "tf_block.inc"


// Same compile-time signature checks as hle_nvn.c, applied to the extracted (real) adapter bodies.
_Static_assert(_Generic(&dm_tf_diag_bind, NVNT_nvnCommandBufferBindTransformFeedbackBuffer: 1, default: 0), "test bind signature");
_Static_assert(_Generic(&dm_tf_diag_bind_plural, NVNT_nvnCommandBufferBindTransformFeedbackBuffers: 1, default: 0), "test plural signature");
_Static_assert(_Generic(&dm_tf_diag_begin, NVNT_nvnCommandBufferBeginTransformFeedback: 1, default: 0), "test begin signature");
_Static_assert(_Generic(&dm_tf_diag_end, NVNT_nvnCommandBufferEndTransformFeedback: 1, default: 0), "test end signature");
_Static_assert(_Generic(&dm_tf_diag_pause, NVNT_nvnCommandBufferPauseTransformFeedback: 1, default: 0), "test pause signature");
_Static_assert(_Generic(&dm_tf_diag_resume, NVNT_nvnCommandBufferResumeTransformFeedback: 1, default: 0), "test resume signature");
_Static_assert(_Generic(&dm_tf_diag_draw, NVNT_nvnCommandBufferDrawTransformFeedback: 1, default: 0), "test draw signature");

static uint8_t buf_a[65536], buf_b[65536], buf_c[65536], buf_d[65536];
static fake_cmd mk(uint8_t *b) { fake_cmd o; memset(&o, 0, sizeof o); o.base = b; o.cap = 65536; return o; }
static void op_begin(fake_cmd *o) { uint8_t *p = cmd_alloc(o, 8); put_hdr(p, 2, 8); }     // OP_BEGIN, as hle_nvn.c:714
static void op_end(fake_cmd *o) { uint8_t *p = cmd_alloc(o, 8); put_hdr(p, 0, 8); }       // OP_END, as hle_nvn.c:720
static void op_draw(fake_cmd *o) {                                                         // OP_DRAW via REC(), as hle_nvn.c:876
    struct { int32_t prim, first, n, instances, base_instance; uint64_t ind; } *d =
        (void *)rec((NVNcommandBuffer *)o, 25, sizeof(struct { int32_t prim, first, n, instances, base_instance; uint64_t ind; }));
    d->prim = 0; d->n = 2304; d->instances = 1;
}
static void op_tex(fake_cmd *o) {                                                          // OP_BIND_TEX via REC(), fixed payload
    struct { int32_t stage, first, n; uint64_t h[2]; } *b = (void *)rec((NVNcommandBuffer *)o, 21, sizeof *b);
    b->stage = 2; b->first = 0; b->n = 1; b->h[0] = 0x10100316ull;
}
static void seq_old(fake_cmd *o) { op_begin(o); op_tex(o); op_draw(o); op_end(o); }
static void seq_new(fake_cmd *o) {   // same sequence with the seven TF adapters interleaved (off/invalid must add nothing)
    op_begin(o);
    dm_tf_diag_bind((NVNcommandBuffer *)o, 0, 0x7d838a1c00ull, 0x120a8ull);
    dm_tf_diag_bind_plural((NVNcommandBuffer *)o, 0, 1, (const NVNbufferRange *)1);   // pointer 1: any read would crash
    dm_tf_diag_begin((NVNcommandBuffer *)o, 0x7d838a1c10ull);
    dm_tf_diag_pause((NVNcommandBuffer *)o, 0x7d838a1c10ull);
    dm_tf_diag_resume((NVNcommandBuffer *)o, 0x7d838a1c10ull);
    dm_tf_diag_draw((NVNcommandBuffer *)o, NVN_DRAW_POINTS, 0x7d838a1c10ull);
    dm_tf_diag_invalid((NVNcommandBuffer *)o, 7, 0);
    dm_tf_diag_end((NVNcommandBuffer *)o, 0x7d838a1c10ull);
    op_tex(o);
    op_draw(o);
    op_end(o);
}
int main(void) {
    int fails = 0;
    fake_cmd a = mk(buf_a); dm_tf_diag_set_mode(TF_DIAG_MODE_OFF); seq_old(&a);
    fake_cmd b = mk(buf_b); dm_tf_diag_set_mode(TF_DIAG_MODE_OFF); seq_new(&b);
    int same = a.cur == b.cur && memcmp(buf_a, buf_b, a.cur) == 0;
    printf("off: old len=%zu new len=%zu memcmp=%s alloc old=%d new=%d\n", a.cur, b.cur, same ? "identical" : "DIFF", a.alloc_calls, b.alloc_calls);
    if (!same || a.alloc_calls != b.alloc_calls) fails++;
    fake_cmd c = mk(buf_c); dm_tf_diag_set_mode(TF_DIAG_MODE_INVALID); seq_new(&c);
    int same_inv = a.cur == c.cur && memcmp(buf_a, buf_c, a.cur) == 0;
    printf("invalid: len=%zu memcmp=%s alloc=%d\n", c.cur, same_inv ? "identical" : "DIFF", c.alloc_calls);
    if (!same_inv || c.alloc_calls != a.alloc_calls) fails++;
    fake_cmd d = mk(buf_d); dm_tf_diag_set_mode(TF_DIAG_MODE_ON); seq_new(&d);
    int tf_records = 0, bad = 0;
    for (size_t at = 0; at + 8 <= d.cur;) {
        uint32_t op, sz; memcpy(&op, buf_d + at, 4); memcpy(&sz, buf_d + at + 4, 4);
        if (sz == 0 || at + sz > d.cur) { bad++; break; }
        if (op == 42) {
            if (sz != 40) { printf("bad tf size %u\n", sz); bad++; }
            p_tf_diag e; memcpy(&e, buf_d + at + 8, sizeof e);
            if (e.flags != 0) bad++;
            if (tf_records == 0 && !(e.kind == TF_DIAG_KIND_BIND && e.index == 0 && e.count == 1 && e.size == 0x120a8ull && e.addr == 0x7d838a1c00ull)) { printf("bad bind payload\n"); bad++; }
            tf_records++;
        }
        at += sz;
    }
    printf("on: len=%zu alloc=%d tf_records=%d bad=%d\n", d.cur, d.alloc_calls, tf_records, bad);
    if (d.cur <= a.cur || tf_records != 8 || bad) fails++;
    FILE *f = fopen("off_old.bin", "wb"); fwrite(buf_a, 1, a.cur, f); fclose(f);
    f = fopen("off_new.bin", "wb"); fwrite(buf_b, 1, b.cur, f); fclose(f);
    f = fopen("on_new.bin", "wb"); fwrite(buf_d, 1, d.cur, f); fclose(f);
    printf("fails: %d\n", fails);
    return fails ? 1 : 0;
}
