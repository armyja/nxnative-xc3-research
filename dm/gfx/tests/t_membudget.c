// Guest physical-memory budget: the accounting the SVCs and GetInfo share (dm/host/membudget.c).
// Small numbers, no mprotect, no guest, no game files; the VM-effect half is t_membudget_vm.c.
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include "../../host/membudget.h"

static int fails;
#define CHECK(c) do { if (!(c)) { printf("FAIL %s:%d %s\n", __FILE__, __LINE__, #c); fails++; } } while (0)
#define PAGE 4096ull
static mb_result r;
static int map(uint64_t o, uint64_t s) { return mb_map(o, s, NULL, NULL, &r); }
static int unmap(uint64_t o, uint64_t s) { return mb_unmap(o, s, NULL, NULL, &r); }
static int heap(uint64_t s) { return mb_set_heap(s, NULL, NULL, &r); }

int main(void) {
    const uint64_t CAP = 64 * 1024 * 1024, BUDGET = 16 * 1024 * 1024, FIXED = 2 * 1024 * 1024;

    mb_init(CAP, BUDGET, FIXED);
    CHECK(map(0, 4 * PAGE) == MB_OK && r.new_bytes == 4 * PAGE && r.used_after == FIXED + 4 * PAGE);
    CHECK(map(0, 4 * PAGE) == MB_OK && r.new_bytes == 0 && mb_alias() == 4 * PAGE);          // duplicate: free
    CHECK(map(2 * PAGE, 4 * PAGE) == MB_OK && r.new_bytes == 2 * PAGE && mb_alias() == 6 * PAGE);  // overlap: only new
    CHECK(unmap(1 * PAGE, 2 * PAGE) == MB_OK && r.new_bytes == 2 * PAGE && mb_alias() == 4 * PAGE);
    CHECK(unmap(1 * PAGE, 2 * PAGE) == MB_OK && r.new_bytes == 0 && mb_alias() == 4 * PAGE);  // repeat: no negative
    CHECK(unmap(1000 * PAGE, 8 * PAGE) == MB_OK && r.new_bytes == 0 && mb_alias() == 4 * PAGE);
    CHECK(map(1 * PAGE, 2 * PAGE) == MB_OK && r.new_bytes == 2 * PAGE && mb_alias() == 6 * PAGE);  // remap charged

    // range errors: refused before any accounting, and distinguishable from budget errors
    mb_init(CAP, BUDGET, FIXED);
    CHECK(map(0, 4 * PAGE) == MB_OK);
    uint64_t a0 = mb_alias(), u0 = mb_used();
    CHECK(map(CAP + PAGE, PAGE) == MB_E_RANGE);            // off beyond the region
    CHECK(map(CAP - PAGE, 2 * PAGE) == MB_E_RANGE);        // end beyond the region (size > cap - off)
    CHECK(map(0, UINT64_MAX) == MB_E_RANGE);               // size would wrap any off+size
    CHECK(map(UINT64_MAX - PAGE, PAGE) == MB_E_RANGE);
    CHECK(map(0, 0) == MB_E_RANGE);                        // empty
    CHECK(map(1, PAGE) == MB_E_RANGE);                     // unaligned offset
    CHECK(map(0, PAGE + 1) == MB_E_RANGE);                 // unaligned size
    CHECK(unmap(CAP + PAGE, PAGE) == MB_E_RANGE);
    CHECK(unmap(0, UINT64_MAX) == MB_E_RANGE);
    CHECK(unmap(0, 0) == MB_E_RANGE);
    CHECK(mb_alias() == a0 && mb_used() == u0);            // nothing changed

    // exactly the budget succeeds; one more page is refused and changes nothing
    mb_init(CAP, BUDGET, FIXED);
    uint64_t room = BUDGET - FIXED;
    CHECK(map(0, room) == MB_OK && mb_used() == BUDGET);
    CHECK(map(room, PAGE) == MB_E_BUDGET && r.new_bytes == PAGE && r.used_after == BUDGET);
    CHECK(mb_alias() == room && mb_used() == BUDGET);
    CHECK(unmap(0, PAGE) == MB_OK);
    CHECK(map(room, PAGE) == MB_OK && r.new_bytes == PAGE);

    // a fully mapped range succeeds even when the budget is exhausted
    mb_init(CAP, BUDGET, FIXED);
    CHECK(map(0, room) == MB_OK && mb_used() == BUDGET);
    CHECK(map(0, room) == MB_OK && r.new_bytes == 0 && mb_used() == BUDGET);

    // the snapshot carries the heap before and after, which is what decides "is this a growth" for the log
    mb_init(CAP, BUDGET, FIXED);
    CHECK(r.heap_before == 0 && heap(8 * 1024 * 1024) == MB_OK && r.heap_before == 0 && r.heap_after == 8 * 1024 * 1024);
    CHECK(heap(4 * 1024 * 1024) == MB_OK && r.heap_before == 8 * 1024 * 1024 && r.heap_after == 4 * 1024 * 1024);
    CHECK(heap(4 * 1024 * 1024) == MB_OK && r.heap_before == 4 * 1024 * 1024 && r.heap_after == 4 * 1024 * 1024);

    // heap and alias share the pool
    mb_init(CAP, BUDGET, FIXED);
    CHECK(heap(8 * 1024 * 1024) == MB_OK && mb_used() == FIXED + 8 * 1024 * 1024);
    CHECK(map(0, 6 * 1024 * 1024) == MB_OK && mb_used() == BUDGET);
    CHECK(heap(9 * 1024 * 1024) == MB_E_BUDGET && mb_heap() == 8 * 1024 * 1024);
    CHECK(heap(4 * 1024 * 1024) == MB_OK);                  // shrink releases budget
    CHECK(map(6 * 1024 * 1024, 4 * 1024 * 1024) == MB_OK && mb_used() == BUDGET);
    mb_set_heap_cap(16 * 1024 * 1024);
    CHECK(heap(32 * 1024 * 1024) == MB_E_CAP && mb_heap() == 4 * 1024 * 1024);

    // a fixed usage already over the pool must refuse rather than wrap
    mb_init(CAP, 1 * 1024 * 1024, 2 * 1024 * 1024);
    CHECK(map(0, PAGE) == MB_E_BUDGET && mb_alias() == 0);

    printf("membudget: %s\n", fails ? "FAILED" : "ok");
    return fails ? 1 : 0;
}
