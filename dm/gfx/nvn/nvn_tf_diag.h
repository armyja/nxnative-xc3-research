// Default-off transform-feedback diagnostic events: record payload, switch parsing and a conservative shadow model.
// A1 checkpoint: this is a recording-adapter format plus a CPU model of "observed replay intent". There is no replay
// wiring, no producer in the real process, and nothing here executes or implements transform feedback. A state value is
// never proof of NVN semantics, GPU writes or actual stream-out content; unprovable input becomes unknown (fail-closed).
#ifndef NVN_TF_DIAG_H
#define NVN_TF_DIAG_H
#include <stdint.h>
#include <stddef.h>
#include <string.h>

#define TF_DIAG_PAYLOAD 32u

typedef enum {
    TF_DIAG_KIND_BIND = 0,               // index/addr/size of one bound transform-feedback buffer
    TF_DIAG_KIND_BIND_PLURAL_OPAQUE = 1, // first/count only; ranges are never read, so no bound is claimed
    TF_DIAG_KIND_BEGIN = 2,              // the API's NVNbufferAddress in addr
    TF_DIAG_KIND_END = 3,                // the API's NVNbufferAddress in addr; the only source of "inactive"
    TF_DIAG_KIND_PAUSE = 4,
    TF_DIAG_KIND_RESUME = 5,
    TF_DIAG_KIND_DRAW_OPAQUE = 6,        // NVNdrawPrimitive in index, the API's address in addr; semantics not modelled
    TF_DIAG_KIND_INVALID_OPAQUE = 7      // explicit fault event (bad handle/depth/anomaly), never a dereference
} tf_diag_kind;

// One OP_TF_DIAG payload: exactly 32 bytes, naturally 8-byte aligned. Reserved fields are written as 0 and a non-zero
// reserved field makes the event invalid (the model then goes unknown instead of guessing).
typedef struct {
    uint32_t kind;    // tf_diag_kind
    uint32_t flags;   // reserved, must be 0
    int32_t index;    // Bind: buffer index (model supports 0 only); BindPlural: first; Draw: NVNdrawPrimitive
    int32_t count;    // Bind: always 1; BindPlural: range count; others: 0
    uint64_t addr;    // Bind: buffer address; Begin/End/Pause/Resume/Draw: the API's NVNbufferAddress
    uint64_t size;    // Bind: buffer size in bytes; others: 0
} p_tf_diag;

#if defined(__cplusplus)
#define TF_DIAG_ASSERT(c, m) static_assert(c, m)
#elif defined(__STDC_VERSION__) && __STDC_VERSION__ >= 201112L
#define TF_DIAG_ASSERT(c, m) _Static_assert(c, m)
#else
#define TF_DIAG_ASSERT(c, m) typedef char tf_diag_assert_##__LINE__[(c) ? 1 : -1]
#endif
TF_DIAG_ASSERT(sizeof(p_tf_diag) == TF_DIAG_PAYLOAD, "p_tf_diag must be 32 bytes");
TF_DIAG_ASSERT(offsetof(p_tf_diag, kind) == 0, "kind offset");
TF_DIAG_ASSERT(offsetof(p_tf_diag, flags) == 4, "flags offset");
TF_DIAG_ASSERT(offsetof(p_tf_diag, index) == 8, "index offset");
TF_DIAG_ASSERT(offsetof(p_tf_diag, count) == 12, "count offset");
TF_DIAG_ASSERT(offsetof(p_tf_diag, addr) == 16, "addr offset");
TF_DIAG_ASSERT(offsetof(p_tf_diag, size) == 24, "size offset");

// DM_NVN_TF_DIAG: only the literal "1" enables; absent/empty/"0" is off; anything else is invalid and behaves as off.
enum { TF_DIAG_MODE_OFF = 0, TF_DIAG_MODE_ON = 1, TF_DIAG_MODE_INVALID = 2 };
static inline int tf_diag_parse_mode(const char *v) {
    if (!v || !*v) return TF_DIAG_MODE_OFF;
    if (v[0] == '0' && v[1] == 0) return TF_DIAG_MODE_OFF;
    if (v[0] == '1' && v[1] == 0) return TF_DIAG_MODE_ON;
    return TF_DIAG_MODE_INVALID;
}
static inline int tf_diag_mode_on(int mode) { return mode == TF_DIAG_MODE_ON; }

// Scan/optimization boundary predicate: pure, payload-free, no guest memory, no resource lookup. A2b callers use it to
// treat an OP_TF_DIAG record as a hard candidate boundary. `mode` must be the A1 startup mode; anything but ON is inert.
static inline int tf_diag_is_boundary(uint32_t op, uint32_t tf_op, int mode) {
    return op == tf_op && mode == TF_DIAG_MODE_ON;
}

enum { TF_DIAG_ACTIVE_UNKNOWN = 0, TF_DIAG_ACTIVE_INACTIVE = 1, TF_DIAG_ACTIVE_ACTIVE = 2 };
enum { TF_DIAG_PAUSE_UNKNOWN = 0, TF_DIAG_PAUSE_RUNNING = 1, TF_DIAG_PAUSE_PAUSED = 2 };

typedef enum {
    TF_DIAG_REASON_NONE = 0,
    TF_DIAG_REASON_NO_EVENT,             // initial state / nothing applied yet
    TF_DIAG_REASON_END_WITHOUT_BEGIN,
    TF_DIAG_REASON_END_WHILE_INACTIVE,
    TF_DIAG_REASON_BEGIN_WHILE_PAUSED,     // repeated Begin while the model is active and paused
    TF_DIAG_REASON_BEGIN_WHILE_ACTIVE,     // repeated Begin while the model is active (running or pause unknown)
    TF_DIAG_REASON_PAUSE_WITHOUT_ACTIVE,
    TF_DIAG_REASON_RESUME_WITHOUT_PAUSE,
    TF_DIAG_REASON_INDEX_UNSUPPORTED,    // bound index other than 0 (NVN's limit is not guessed)
    TF_DIAG_REASON_PLURAL_OPAQUE,
    TF_DIAG_REASON_DRAW_OPAQUE,
    TF_DIAG_REASON_INVALID_OPAQUE,
    TF_DIAG_REASON_BAD_PAYLOAD,          // reserved bits, per-kind field rules, or addr+size overflow
    TF_DIAG_REASON_BAD_RECORD,           // record size/alignment wrong: the payload was never read
    TF_DIAG_REASON_BAD_KIND,
    TF_DIAG_REASON_SEQ_SATURATED
} tf_diag_reason;

typedef struct {
    uint8_t active;        // TF_DIAG_ACTIVE_*
    uint8_t pause;         // TF_DIAG_PAUSE_*
    uint8_t reason;        // last tf_diag_reason that made a field invalid or unknown (0 when clean)
    uint8_t saturated;     // the sequence counter saturated; state is unknown from then on
    uint8_t has_bound0;    // an event referred to slot 0 at least once (valid or not)
    uint8_t bound0_valid;  // slot 0 currently holds a well-formed bound (addr/size)
    int32_t last_index;
    int32_t last_count;
    uint64_t bound0_addr, bound0_size;
    uint64_t begin_addr, end_addr, draw_addr;
    uint64_t seq;          // saturating event counter (u64), never wraps
} tf_diag_state;

static inline void tf_diag_init(tf_diag_state *s) {
    if (!s) return;
    memset(s, 0, sizeof *s);
    s->reason = (uint8_t)TF_DIAG_REASON_NO_EVENT;
}

static inline void tf_diag_mark_unknown(tf_diag_state *s, int reason) {
    if (!s) return;
    s->active = TF_DIAG_ACTIVE_UNKNOWN;
    s->pause = TF_DIAG_PAUSE_UNKNOWN;
    s->bound0_valid = 0;
    s->reason = (uint8_t)reason;
}

// After the sequence counter saturates the model is sticky unknown: every later apply/tick keeps unknown/pause unknown,
// an invalid bound and TF_DIAG_REASON_SEQ_SATURATED, and seq stays at UINT64_MAX. The rule for the event snapshot is
// explicit: last_index/last_count keep the values of the last event seen before saturation and are not updated afterwards.
static inline void tf_diag_sticky_saturated(tf_diag_state *s) {
    if (!s || !s->saturated) return;
    s->active = TF_DIAG_ACTIVE_UNKNOWN;
    s->pause = TF_DIAG_PAUSE_UNKNOWN;
    s->bound0_valid = 0;
    s->reason = (uint8_t)TF_DIAG_REASON_SEQ_SATURATED;
    s->seq = UINT64_MAX;
}
static inline void tf_diag_tick(tf_diag_state *s) {
    if (!s) return;
    if (s->seq != UINT64_MAX) { s->seq++; return; }
    s->saturated = 1;
    tf_diag_sticky_saturated(s);
}

// Reserved fields must be zero; addr+size must not wrap. Per-kind field rules are checked in tf_diag_apply.
static inline int tf_diag_payload_ok(const p_tf_diag *e) {
    if (!e) return 0;
    if (e->flags != 0) return 0;
    if (e->kind > (uint32_t)TF_DIAG_KIND_INVALID_OPAQUE) return 0;
    if (e->addr != 0 && e->addr + e->size < e->addr) return 0;
    return 1;
}

// Conservative transition table (report156 §9.2): Bind only records a range; Begin is the only entry to active;
// End is the only entry to inactive and only from an observed active state; everything unprovable becomes unknown.
// "Begin implies running" is a naming assumption and is not a proof of NVN semantics.
static inline void tf_diag_apply(tf_diag_state *s, const p_tf_diag *e) {
    if (!s) return;
    if (s->saturated) { tf_diag_sticky_saturated(s); return; }   // sticky unknown: later events cannot make it valid again
    if (!e) { tf_diag_mark_unknown(s, TF_DIAG_REASON_BAD_PAYLOAD); tf_diag_tick(s); return; }
    s->last_index = e->index;
    s->last_count = e->count;
    if (!tf_diag_payload_ok(e)) { tf_diag_mark_unknown(s, TF_DIAG_REASON_BAD_PAYLOAD); tf_diag_tick(s); return; }
    switch (e->kind) {
    case TF_DIAG_KIND_BIND:
        if (e->count != 1 || e->size == 0) { tf_diag_mark_unknown(s, TF_DIAG_REASON_BAD_PAYLOAD); break; }
        if (e->index != 0) { tf_diag_mark_unknown(s, TF_DIAG_REASON_INDEX_UNSUPPORTED); break; }
        s->has_bound0 = 1;
        s->bound0_addr = e->addr;
        s->bound0_size = e->size;
        s->bound0_valid = 1;
        break;                                     // active/pause are untouched by a bind
    case TF_DIAG_KIND_BIND_PLURAL_OPAQUE:
        s->has_bound0 = 1;                          // it may have covered slot 0, but ranges are not read
        tf_diag_mark_unknown(s, TF_DIAG_REASON_PLURAL_OPAQUE);
        break;
    case TF_DIAG_KIND_BEGIN:
        if (e->index != 0 || e->count != 0 || e->size != 0) { tf_diag_mark_unknown(s, TF_DIAG_REASON_BAD_PAYLOAD); break; }
        if (s->active == TF_DIAG_ACTIVE_ACTIVE) {   // a repeated Begin is an invalid sequence in any pause state
            tf_diag_mark_unknown(s, s->pause == TF_DIAG_PAUSE_PAUSED ? TF_DIAG_REASON_BEGIN_WHILE_PAUSED
                                                                     : TF_DIAG_REASON_BEGIN_WHILE_ACTIVE);
            break;
        }
        s->active = TF_DIAG_ACTIVE_ACTIVE;
        s->pause = TF_DIAG_PAUSE_RUNNING;
        s->begin_addr = e->addr;
        s->reason = (uint8_t)TF_DIAG_REASON_NONE;
        break;
    case TF_DIAG_KIND_END:
        if (e->index != 0 || e->count != 0 || e->size != 0) { tf_diag_mark_unknown(s, TF_DIAG_REASON_BAD_PAYLOAD); break; }
        if (s->active == TF_DIAG_ACTIVE_ACTIVE) {
            s->active = TF_DIAG_ACTIVE_INACTIVE;
            s->pause = TF_DIAG_PAUSE_UNKNOWN;
            s->end_addr = e->addr;
            s->reason = (uint8_t)TF_DIAG_REASON_NONE;
        } else if (s->active == TF_DIAG_ACTIVE_INACTIVE) {
            tf_diag_mark_unknown(s, TF_DIAG_REASON_END_WHILE_INACTIVE);
        } else {
            tf_diag_mark_unknown(s, TF_DIAG_REASON_END_WITHOUT_BEGIN);
        }
        break;
    case TF_DIAG_KIND_PAUSE:
        if (e->index != 0 || e->count != 0 || e->size != 0) { tf_diag_mark_unknown(s, TF_DIAG_REASON_BAD_PAYLOAD); break; }
        if (s->active == TF_DIAG_ACTIVE_ACTIVE && s->pause == TF_DIAG_PAUSE_RUNNING) {
            s->pause = TF_DIAG_PAUSE_PAUSED;
            s->reason = (uint8_t)TF_DIAG_REASON_NONE;
        } else {
            tf_diag_mark_unknown(s, TF_DIAG_REASON_PAUSE_WITHOUT_ACTIVE);
        }
        break;
    case TF_DIAG_KIND_RESUME:
        if (e->index != 0 || e->count != 0 || e->size != 0) { tf_diag_mark_unknown(s, TF_DIAG_REASON_BAD_PAYLOAD); break; }
        if (s->active == TF_DIAG_ACTIVE_ACTIVE && s->pause == TF_DIAG_PAUSE_PAUSED) {
            s->pause = TF_DIAG_PAUSE_RUNNING;
            s->reason = (uint8_t)TF_DIAG_REASON_NONE;
        } else {
            tf_diag_mark_unknown(s, TF_DIAG_REASON_RESUME_WITHOUT_PAUSE);
        }
        break;
    case TF_DIAG_KIND_DRAW_OPAQUE:
        s->draw_addr = e->addr;
        tf_diag_mark_unknown(s, TF_DIAG_REASON_DRAW_OPAQUE);
        break;
    case TF_DIAG_KIND_INVALID_OPAQUE:
        tf_diag_mark_unknown(s, TF_DIAG_REASON_INVALID_OPAQUE);
        break;
    default:
        tf_diag_mark_unknown(s, TF_DIAG_REASON_BAD_KIND);
        break;
    }
    tf_diag_tick(s);
}

// Read-only name of the last reason that invalidated a field (formatter helper; no state is touched).
static inline const char *tf_diag_reason_name(int reason) {
    switch (reason) {
    case TF_DIAG_REASON_NONE: return "none";
    case TF_DIAG_REASON_NO_EVENT: return "no-event";
    case TF_DIAG_REASON_END_WITHOUT_BEGIN: return "end-without-begin";
    case TF_DIAG_REASON_END_WHILE_INACTIVE: return "end-while-inactive";
    case TF_DIAG_REASON_BEGIN_WHILE_PAUSED: return "begin-while-paused";
    case TF_DIAG_REASON_BEGIN_WHILE_ACTIVE: return "begin-while-active";
    case TF_DIAG_REASON_PAUSE_WITHOUT_ACTIVE: return "pause-without-active";
    case TF_DIAG_REASON_RESUME_WITHOUT_PAUSE: return "resume-without-pause";
    case TF_DIAG_REASON_INDEX_UNSUPPORTED: return "index-unsupported";
    case TF_DIAG_REASON_PLURAL_OPAQUE: return "plural-opaque";
    case TF_DIAG_REASON_DRAW_OPAQUE: return "draw-opaque";
    case TF_DIAG_REASON_INVALID_OPAQUE: return "invalid-opaque";
    case TF_DIAG_REASON_BAD_PAYLOAD: return "bad-payload";
    case TF_DIAG_REASON_BAD_RECORD: return "bad-record";
    case TF_DIAG_REASON_BAD_KIND: return "bad-kind";
    case TF_DIAG_REASON_SEQ_SATURATED: return "seq-saturated";
    default: return "unknown";
    }
}

// Observation output only: this names the model's state, it is not a TF implementation and not content.
static inline const char *tf_diag_active_name(int active) {
    return active == TF_DIAG_ACTIVE_ACTIVE ? "active" : active == TF_DIAG_ACTIVE_INACTIVE ? "inactive" : "unknown";
}
static inline const char *tf_diag_pause_name(int pause) {
    return pause == TF_DIAG_PAUSE_RUNNING ? "running" : pause == TF_DIAG_PAUSE_PAUSED ? "paused" : "unknown";
}
// The experimental gate may only proceed on a fully observed inactive state; everything else (including unknown)
// keeps it refused. Passing here does not prove NVN semantics.
static inline int tf_diag_gate_allows(const tf_diag_state *s) {
    return s && s->active == TF_DIAG_ACTIVE_INACTIVE && !s->saturated;
}
#endif
