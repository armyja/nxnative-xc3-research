// Guest physical-memory budget: the accounting the SVCs and GetInfo share (dm/host/membudget.c).
// Small numbers throughout: no mprotect, no guest, no game files.
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include "../../host/membudget.h"

static int fails;
#define CHECK(c) do { if (!(c)) { printf("FAIL %s:%d %s\n", __FILE__, __LINE__, #c); fails++; } } while (0)
#define PAGE 4096ull

int main(void) {
    const uint64_t CAP = 64 * 1024 * 1024, BUDGET = 16 * 1024 * 1024, FIXED = 2 * 1024 * 1024;

    // map / unmap / used accounting
    mb_init(CAP, BUDGET, FIXED);
    uint64_t nb = 0, used = 0;
    CHECK(mb_map(0, 4 * PAGE, &nb, &used) == 0);
    CHECK(nb == 4 * PAGE);
    CHECK(used == FIXED + 4 * PAGE);
    CHECK(mb_alias() == 4 * PAGE);

    // duplicate map charges nothing, overlap charges only the new part
    CHECK(mb_map(0, 4 * PAGE, &nb, &used) == 0);
    CHECK(nb == 0 && mb_alias() == 4 * PAGE);
    CHECK(mb_map(2 * PAGE, 4 * PAGE, &nb, &used) == 0);       // pages 2..5, only 4 and 5 are new
    CHECK(nb == 2 * PAGE && mb_alias() == 6 * PAGE);

    // unmap a hole inside a mapped range: only the mapped part is released; a repeat releases nothing
    uint64_t clr = 0;
    mb_unmap(1 * PAGE, 2 * PAGE, &clr, &used);                 // pages 1,2 were mapped
    CHECK(clr == 2 * PAGE && mb_alias() == 4 * PAGE);
    mb_unmap(1 * PAGE, 2 * PAGE, &clr, &used);                 // already unset: must not go negative
    CHECK(clr == 0 && mb_alias() == 4 * PAGE);
    mb_unmap(1000 * PAGE, 8 * PAGE, &clr, &used);              // entirely unmapped
    CHECK(clr == 0 && mb_alias() == 4 * PAGE);

    // remap after unmap is charged again
    CHECK(mb_map(1 * PAGE, 2 * PAGE, &nb, &used) == 0);
    CHECK(nb == 2 * PAGE && mb_alias() == 6 * PAGE);

    // exactly to the budget succeeds; one more page is refused and changes nothing
    mb_init(CAP, BUDGET, FIXED);
    uint64_t room = BUDGET - FIXED;
    CHECK(mb_map(0, room, &nb, &used) == 0);
    CHECK(mb_alias() == room && mb_used() == BUDGET);
    uint64_t before_alias = mb_alias(), before_used = mb_used();
    CHECK(mb_map(room, PAGE, &nb, &used) == 1);
    CHECK(nb == PAGE);
    CHECK(mb_alias() == before_alias && mb_used() == before_used);
    // the refused page is still unmapped: freeing one page then mapping it succeeds
    mb_unmap(0, PAGE, &clr, &used);
    CHECK(mb_map(room, PAGE, &nb, &used) == 0 && nb == PAGE);

    // a fully mapped range succeeds even when the budget is exhausted
    mb_init(CAP, BUDGET, FIXED);
    CHECK(mb_map(0, room, &nb, &used) == 0 && mb_used() == BUDGET);
    CHECK(mb_map(0, room, &nb, &used) == 0 && nb == 0 && mb_used() == BUDGET);

    // heap and alias share the pool: heap growth refused, shrink frees room, then map works
    mb_init(CAP, BUDGET, FIXED);
    CHECK(mb_set_heap(8 * 1024 * 1024, &used) == 0);
    CHECK(mb_used() == FIXED + 8 * 1024 * 1024);
    CHECK(mb_map(0, 6 * 1024 * 1024, &nb, &used) == 0);       // 16 - 2 fixed - 8 heap = 6 MiB left
    CHECK(mb_used() == BUDGET);
    CHECK(mb_set_heap(9 * 1024 * 1024, &used) == 1);           // refused: alias + heap + fixed would exceed
    CHECK(mb_heap() == 8 * 1024 * 1024);
    CHECK(mb_set_heap(4 * 1024 * 1024, &used) == 0);           // shrink releases 4 MiB of budget
    CHECK(mb_map(6 * 1024 * 1024, 4 * 1024 * 1024, &nb, &used) == 0);
    CHECK(mb_used() == BUDGET);

    // heap above the region is refused without changing anything
    mb_set_heap_cap(16 * 1024 * 1024);
    CHECK(mb_set_heap(32 * 1024 * 1024, &used) == 2 && mb_heap() == 4 * 1024 * 1024);

    printf("membudget: %s\n", fails ? "FAILED" : "ok");
    return fails ? 1 : 0;
}
