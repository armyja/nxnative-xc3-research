// The budget transaction against a real (small) protected mapping: the page permissions that the caller's effect
// applies must always agree with the committed bitmap and usage, including under a forced interleaving, and an
// effect that fails must commit nothing. 1 MiB of anonymous memory; no guest, no game files.
#include <mach/mach.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <unistd.h>
#include "../../host/membudget.h"

#define PAGE 4096ull
#define REGION (1024 * 1024)
static uint8_t *base;
static int fails;
#define CHECK(c) do { if (!(c)) { printf("FAIL %s:%d %s\n", __FILE__, __LINE__, #c); fails++; } } while (0)

static int prot_of(void *p) {
    vm_address_t a = (vm_address_t)p; vm_size_t sz = 0; vm_region_basic_info_data_64_t info;
    mach_msg_type_number_t cnt = VM_REGION_BASIC_INFO_COUNT_64; mach_port_t obj = MACH_PORT_NULL;
    if (vm_region_64(mach_task_self(), &a, &sz, VM_REGION_BASIC_INFO_64, (vm_region_info_t)&info, &cnt, &obj) != KERN_SUCCESS) return -1;
    return info.protection;
}
// the production effect: the same two mprotect calls the SVC makes
static int fx(void *ctx, uint64_t off, uint64_t size, int map) {
    (void)ctx;
    if (map == 2) return 0;                       // heap: the real heap effect is exercised by the SVC build
    return mprotect(base + off, size, map ? (PROT_READ | PROT_WRITE) : PROT_NONE) ? -1 : 0;
}

static int bad_calls;
static int failing(void *ctx, uint64_t off, uint64_t size, int map) { (void)ctx;(void)off;(void)size;(void)map; bad_calls++; return -1; }
static int fail_heap(void *ctx, uint64_t off, uint64_t size, int map) { (void)ctx;(void)off;(void)size;(void)map; return -1; }

static atomic_int go;
static void *worker_map(void *a) { (void)a; while (!atomic_load(&go)) {} mb_result r; mb_map(0, 4 * PAGE, fx, NULL, &r); return NULL; }
static void *worker_unmap(void *a) { (void)a; while (!atomic_load(&go)) {} mb_result r; mb_unmap(0, 4 * PAGE, fx, NULL, &r); return NULL; }

int main(void) {
    base = mmap(NULL, REGION, PROT_NONE, MAP_PRIVATE | MAP_ANON, -1, 0);
    if (base == MAP_FAILED) { printf("mmap failed\n"); return 1; }

    // transaction vs. permissions, straight through
    mb_init(REGION, 64 * PAGE, 0);
    mb_result r;
    CHECK(mb_map(0, 4 * PAGE, fx, NULL, &r) == MB_OK && r.new_bytes == 4 * PAGE);
    CHECK(prot_of(base) == (VM_PROT_READ | VM_PROT_WRITE));
    CHECK(mb_unmap(0, 4 * PAGE, fx, NULL, &r) == MB_OK && r.new_bytes == 4 * PAGE);
    CHECK(prot_of(base) == VM_PROT_NONE);
    CHECK(mb_alias() == 0 && mb_used() == 0);

    // a failing effect commits nothing and leaves the pages untouched
    mb_init(REGION, 64 * PAGE, 0);
    bad_calls = 0;
    CHECK(mb_map(0, 4 * PAGE, failing, NULL, &r) == MB_E_EFFECT);
    CHECK(bad_calls == 1);
    CHECK(r.new_bytes == 4 * PAGE && mb_alias() == 0 && mb_used() == 0);
    CHECK(prot_of(base) == VM_PROT_NONE);
    CHECK(mb_map(0, 4 * PAGE, fx, NULL, &r) == MB_OK);       // the same range still maps afterwards
    CHECK(prot_of(base) == (VM_PROT_READ | VM_PROT_WRITE));

    // heap: a failing effect must not move the heap
    mb_init(REGION, 64 * PAGE, 0);
    CHECK(mb_set_heap(8 * PAGE, fx, NULL, &r) == MB_OK && mb_heap() == 8 * PAGE);
    CHECK(mb_set_heap(16 * PAGE, fail_heap, NULL, &r) == MB_E_EFFECT && mb_heap() == 8 * PAGE);

    // forced interleaving: map and unmap of the same range from two threads must leave permissions and bitmap equal
    for (int i = 0; i < 2000; i++) {
        mb_init(REGION, 64 * PAGE, 0);
        mprotect(base, 4 * PAGE, PROT_NONE);
        atomic_store(&go, 0);
        pthread_t a, c;
        pthread_create(&a, NULL, worker_map, NULL);
        pthread_create(&c, NULL, worker_unmap, NULL);
        atomic_store(&go, 1);
        pthread_join(a, NULL); pthread_join(c, NULL);
        int map_won = mb_alias() == 4 * PAGE;
        int prot = prot_of(base);
        if (!(map_won ? prot == (VM_PROT_READ | VM_PROT_WRITE) : prot == VM_PROT_NONE)) {
            printf("FAIL interleave %d: bitmap=%llu prot=%d\n", i, (unsigned long long)mb_alias(), prot); fails++; break;
        }
        if (!(map_won || mb_alias() == 0)) { printf("FAIL interleave %d accounting\n", i); fails++; break; }
    }

    printf("membudget_vm: %s\n", fails ? "FAILED" : "ok");
    return fails ? 1 : 0;
}
