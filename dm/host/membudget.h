// Guest physical-memory budget shared by MapPhysicalMemory, UnmapPhysicalMemory, SetHeapSize and GetInfo.
//
// The Horizon-compatible kernel charges MapPhysicalMemory only for the pages that are not already mapped and keeps
// that charge in the process's physical-memory reservation until they are unmapped; SetHeapSize comes out of the
// same application pool. A host that reports the heap alone (and never refuses a mapping) lets a title map tens of
// GiB of alias pages and then still allocate a heap. This unit owns that one number so the SVCs and GetInfo agree.
//
// Reference for the semantics (read, not copied): Atmosphere kern_k_page_table_base.cpp MapPhysicalMemory computes
// already-mapped bytes, succeeds outright when nothing is new, and otherwise reserves (size - already_mapped) from
// PhysicalMemoryMax, failing with ResultLimitReached; kern_k_process.cpp derives the used sizes from that reservation.
#ifndef DM_MEMBUDGET_H
#define DM_MEMBUDGET_H
#include <stdint.h>

// budget = the application pool; fixed_bytes = what the profile counts as already used (mem_used + module bss)
void mb_init(uint64_t alias_cap, uint64_t budget, uint64_t fixed_bytes);
void mb_set_fixed(uint64_t fixed_bytes);
void mb_set_heap_cap(uint64_t cap);

// 0 = mapped (counted), 1 = ResultLimitReached (nothing changed). new_bytes/used_after are filled when non-NULL.
int  mb_map(uint64_t off, uint64_t size, uint64_t *new_bytes, uint64_t *used_after);
// never negative: only pages actually mapped are released
void mb_unmap(uint64_t off, uint64_t size, uint64_t *cleared_bytes, uint64_t *used_after);
// 0 = accepted, 1 = ResultLimitReached (heap unchanged), 2 = above the heap region (heap unchanged)
int  mb_set_heap(uint64_t size, uint64_t *used_after);

uint64_t mb_alias(void);      // unique alias bytes currently mapped
uint64_t mb_heap(void);
uint64_t mb_used(void);       // fixed + heap + alias: what GetInfo reports and what the budget checks
uint64_t mb_budget(void);
#endif
