// Read-only diagnostic: one snapshot of the fragment image state at the first draw whose fragment program carries a
// given shader key. Off unless DM_NVN_IMGBIND names exactly 16 hex digits. Nothing here changes render state, creates
// GPU resources or reads texel data; the record is built in one buffer and written with a single log call.
#pragma once
#include <stddef.h>
#include <stdint.h>

#define IMGDIAG_SLOTS   32
#define IMGDIAG_MAXKEYS  6
#define IMGDIAG_REC     4096

typedef struct {
    uint64_t handle;      // raw value from S.img[stage][slot]
    uint64_t serial;      // pool-handle -> object serial, same reader the renderer uses (0 when unknown)
    uint32_t registered;  // the texture id resolved in the registry (descriptor scalars valid)
    uint32_t fmt, w, h, depth, type;
    uint64_t write_frame, write_cmd;   // last real OP_BIND_IMG that wrote this slot (0 = never in this run)
    int32_t  write_first, write_count, write_stage;
} imgdiag_slot;

typedef struct {
    uint64_t frame, pass, draw, cmd;   // replay/guest counters, not claims about GPU execution
    int nkeys, hit_index, keys_cached; // keys_cached: 0 when the program's key cache was not ready
    uint8_t keys[IMGDIAG_MAXKEYS][8];
    imgdiag_slot slot[IMGDIAG_SLOTS];
} imgdiag_snapshot;

// 16 hex digits -> 8 bytes. Returns 1 on success, 0 on anything else (empty, short, long, non-hex).
int imgdiag_parse_key(const char *s, uint8_t out[8]);
// Index of the target among n keys, -1 when absent.
int imgdiag_find_key(const uint8_t keys[][8], int n, const uint8_t target[8]);
// "no-image-state" (every slot zero), "unique-candidate" (exactly one non-zero), "ambiguous" (more than one).
const char *imgdiag_classify(const imgdiag_snapshot *s);
// One complete record line. Returns the length written, or 0 when the buffer is too small.
size_t imgdiag_format(char *buf, size_t n, const imgdiag_snapshot *s, const uint8_t target[8], const char *target_src);

// Arm from DM_NVN_IMGBIND (once). 1 = armed, 0 = off or invalid (invalid is logged once and permanently disabled).
int  imgdiag_arm(void);
int  imgdiag_armed(void);
void imgdiag_disarm(void);
// Copy of the armed target key (zeroed when not armed).
void imgdiag_target(uint8_t out[8]);
// Forget the parsed decision (tests / re-initialisation only).
void imgdiag_reset(void);
// Per-slot source metadata, filled only while armed (bounded: 32 slots, no queue).
void imgdiag_note_bind(int stage, int first, int count, uint64_t frame, uint64_t cmd);
void imgdiag_copy_sources(imgdiag_slot *slots);
void imgdiag_note_skipped(void);
uint64_t imgdiag_skipped(void);
