// Guest physical-memory budget shared by MapPhysicalMemory, UnmapPhysicalMemory, SetHeapSize and GetInfo.
//
// The Horizon-compatible kernel charges MapPhysicalMemory only for the pages that are not already mapped and keeps
// that charge in the process's physical-memory reservation until they are unmapped; SetHeapSize comes out of the
// same application pool. This unit owns that one number so the SVCs and GetInfo agree.
//
// Every operation is one transaction: the range check, the new-page count, the budget comparison, the VM effect
// (the caller's mprotect, run inside the lock) and the commit of the bitmap and the counters happen under one
// mutex. A caller therefore cannot observe or produce a state where the accounting and the page permissions
// disagree, and a failed effect commits nothing.
//
// Reference for the semantics (read, not copied): Atmosphere kern_k_page_table_base.cpp MapPhysicalMemory computes
// already-mapped bytes, succeeds outright when nothing is new, and otherwise reserves (size - already_mapped) from
// PhysicalMemoryMax, failing with ResultLimitReached; kern_k_process.cpp derives the used sizes from that reservation.
#ifndef DM_MEMBUDGET_H
#define DM_MEMBUDGET_H
#include <stdint.h>

enum { MB_OK = 0, MB_E_RANGE = 1, MB_E_BUDGET = 2, MB_E_EFFECT = 3, MB_E_CAP = 4 };

// The VM effect, called with the budget lock held, before anything is committed.
//   map == 1: alias map,     arg1 = offset in the alias region, arg2 = size
//   map == 0: alias unmap,   arg1 = offset, arg2 = size
//   map == 2: heap resize,   arg1 = heap size before this transaction (from the lock), arg2 = the new size
// Returns 0 when the pages really changed, non-zero when the platform refused; a refusal commits nothing.
typedef int (*mb_effect)(void *ctx, uint64_t off, uint64_t size, int map);

typedef struct {
    int rc;
    uint64_t new_bytes;     // pages this operation would add (map) or did release (unmap)
    uint64_t used_before, used_after, limit;
    uint64_t alias_after, heap_before, heap_after;   // heap_before: the committed heap inside this transaction
} mb_result;

void mb_init(uint64_t alias_cap, uint64_t budget, uint64_t fixed_bytes);
void mb_set_heap_cap(uint64_t cap);

int mb_map(uint64_t off, uint64_t size, mb_effect fx, void *ctx, mb_result *r);
int mb_unmap(uint64_t off, uint64_t size, mb_effect fx, void *ctx, mb_result *r);
int mb_set_heap(uint64_t size, mb_effect fx, void *ctx, mb_result *r);

uint64_t mb_alias(void);
uint64_t mb_heap(void);
uint64_t mb_used(void);      // fixed + heap + alias, the number GetInfo reports and the budget checks
uint64_t mb_budget(void);
#endif
