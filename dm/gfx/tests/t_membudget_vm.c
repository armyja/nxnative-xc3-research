// The budget transaction against real (small) protected mappings, through the production VM adapters
// (dm/host/membudget_vm.c) — not a copy. 1 MiB alias region + 1 MiB heap region, no guest, no game files.
#include <mach/mach.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <unistd.h>
#include "../../host/membudget.h"
#include "../../host/membudget_vm.h"

#define PAGE 4096ull
#define REGION (1024 * 1024)
static uint8_t *alias_base, *heap_base;
static mb_vm_ctx ctx;
static int fails;
#define CHECK(c) do { if (!(c)) { printf("FAIL %s:%d %s\n", __FILE__, __LINE__, #c); fails++; } } while (0)

static int prot_of(void *p) {
    vm_address_t a = (vm_address_t)p; vm_size_t sz = 0; vm_region_basic_info_data_64_t info;
    mach_msg_type_number_t cnt = VM_REGION_BASIC_INFO_COUNT_64; mach_port_t obj = MACH_PORT_NULL;
    if (vm_region_64(mach_task_self(), &a, &sz, VM_REGION_BASIC_INFO_64, (vm_region_info_t)&info, &cnt, &obj) != KERN_SUCCESS) return -1;
    return info.protection;
}
static int rw(void *p) { return prot_of(p) == (VM_PROT_READ | VM_PROT_WRITE); }
static int none(void *p) { return prot_of(p) == VM_PROT_NONE; }

// A wrapper that holds the transaction open for the deterministic interleaving, then delegates to the production
// heap adapter: the repair under test is not duplicated here.
static atomic_int inside, release_hold, hold_enabled;
static int heap_probe(void *c, uint64_t old_size, uint64_t new_size, int map) {
    if (atomic_load(&hold_enabled)) {
        atomic_store(&inside, 1);
        while (!atomic_load(&release_hold)) { }        // A sits inside the transaction, holding the lock
        atomic_store(&hold_enabled, 0);
    }
    return mb_vm_heap(c, old_size, new_size, map);     // production adapter
}

static int bad_calls;
static int fail_fx(void *c, uint64_t o, uint64_t s, int m) { (void)c;(void)o;(void)s;(void)m; bad_calls++; return -1; }

static atomic_int go, done;
static uint64_t grow_to = 16 * PAGE;
static void *grower(void *a) { (void)a; while (!atomic_load(&go)) {} mb_result r; mb_set_heap(grow_to, heap_probe, &ctx, &r); atomic_store(&done, 1); return NULL; }
static void *shrinker(void *a) { (void)a; mb_result r; mb_set_heap(8 * PAGE, mb_vm_heap, &ctx, &r); atomic_store(&done, 2); return NULL; }

int main(void) {
    alias_base = mmap(NULL, REGION, PROT_NONE, MAP_PRIVATE | MAP_ANON, -1, 0);
    heap_base = mmap(NULL, REGION, PROT_NONE, MAP_PRIVATE | MAP_ANON, -1, 0);
    if (alias_base == MAP_FAILED || heap_base == MAP_FAILED) { printf("mmap failed\n"); return 1; }
    ctx.alias = alias_base; ctx.heap = heap_base;

    // alias map/unmap through the production adapter
    mb_init(REGION, 64 * PAGE, 0);
    mb_result r;
    CHECK(mb_map(0, 4 * PAGE, mb_vm_alias, &ctx, &r) == MB_OK && r.new_bytes == 4 * PAGE);
    CHECK(rw(alias_base));
    CHECK(mb_unmap(0, 4 * PAGE, mb_vm_alias, &ctx, &r) == MB_OK && r.new_bytes == 4 * PAGE);
    CHECK(none(alias_base));

    // an injected failing effect commits nothing (map and heap)
    bad_calls = 0;
    CHECK(mb_map(0, 4 * PAGE, fail_fx, NULL, &r) == MB_E_EFFECT && bad_calls == 1 && mb_alias() == 0 && none(alias_base));
    CHECK(mb_map(0, 4 * PAGE, mb_vm_alias, &ctx, &r) == MB_OK && rw(alias_base));

    // heap grow/shrink through the production adapter, permissions and counters together
    mb_init(REGION, 64 * PAGE, 0);
    CHECK(mb_set_heap(16 * PAGE, mb_vm_heap, &ctx, &r) == MB_OK && mb_heap() == 16 * PAGE);
    CHECK(rw(heap_base) && rw(heap_base + 15 * PAGE) && none(heap_base + 16 * PAGE));
    CHECK(mb_set_heap(8 * PAGE, mb_vm_heap, &ctx, &r) == MB_OK && mb_heap() == 8 * PAGE);
    CHECK(rw(heap_base + 7 * PAGE) && none(heap_base + 8 * PAGE) && none(heap_base + 15 * PAGE));
    CHECK(mb_used() == 8 * PAGE);                       // GetInfo's number
    // a failing grow leaves heap, permissions and counters alone
    CHECK(mb_set_heap(32 * PAGE, fail_fx, NULL, &r) == MB_E_EFFECT && mb_heap() == 8 * PAGE && none(heap_base + 8 * PAGE));

    // deterministic interleaving: A sits inside its transaction, B must not commit behind its back
    mb_init(REGION, 64 * PAGE, 0);
    for (int i = 0; i < 200; i++) {
        mb_init(REGION, 64 * PAGE, 0);
        mprotect(heap_base, 32 * PAGE, PROT_NONE);
        atomic_store(&inside, 0); atomic_store(&release_hold, 0); atomic_store(&hold_enabled, 1); atomic_store(&done, 0);
        grow_to = 16 * PAGE;
        pthread_t a; pthread_create(&a, NULL, grower, NULL);
        atomic_store(&go, 1);
        while (!atomic_load(&inside)) { }                // A is inside the transaction now
        atomic_store(&done, 0);
        pthread_t b; pthread_create(&b, NULL, shrinker, NULL);
        for (int spin = 0; spin < 100000 && atomic_load(&done) == 0; spin++) { }
        int blocked = atomic_load(&done) == 0;           // B must still be waiting for the lock
        atomic_store(&release_hold, 1);
        pthread_join(a, NULL); pthread_join(b, NULL);
        if (!blocked) { printf("FAIL iteration %d: shrinker entered while the grower held the transaction\n", i); fails++; break; }
        // A grew to 16, then B shrank to 8: pages 8..15 must be gone, not left read-write
        if (!(mb_heap() == 8 * PAGE && rw(heap_base) && none(heap_base + 8 * PAGE) && none(heap_base + 15 * PAGE)
              && mb_used() == 8 * PAGE)) {
            printf("FAIL iteration %d: heap=%llu prot8=%d prot15=%d used=%llu\n", i,
                   (unsigned long long)mb_heap(), prot_of(heap_base + 8 * PAGE), prot_of(heap_base + 15 * PAGE),
                   (unsigned long long)mb_used());
            fails++; break;
        }
        atomic_store(&go, 0);
    }

    printf("membudget_vm: %s\n", fails ? "FAILED" : "ok");
    return fails ? 1 : 0;
}
