// Two threads must not both fit into the same remaining budget. The gate is a C11 atomic, not a volatile.
#include <pthread.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include "../../host/membudget.h"
#define PAGE 4096ull
static atomic_int go, done;
static int rc[2];
static void *worker(void *arg) {
    long which = (long)arg;
    while (!atomic_load(&go)) { }                      // both threads start together
    mb_result r;
    rc[which] = mb_map(which * 1024 * PAGE, 512 * PAGE, NULL, NULL, &r);   // 2 MiB each, distinct ranges
    atomic_fetch_add(&done, 1);
    return NULL;
}
int main(void) {
    int bad = 0;
    for (int i = 0; i < 500; i++) {                    // many interleavings
        uint64_t budget = 2 * 1024 * 1024 + PAGE;      // room for one 2 MiB map plus one page
        mb_init(64 * 1024 * 1024, budget, 0);
        atomic_store(&go, 0); atomic_store(&done, 0);
        pthread_t a, b;
        pthread_create(&a, NULL, worker, (void *)0);
        pthread_create(&b, NULL, worker, (void *)1);
        atomic_store(&go, 1);
        pthread_join(a, NULL); pthread_join(b, NULL);
        int ok = (rc[0] == MB_OK) + (rc[1] == MB_OK);
        if (ok != 1 || mb_used() > mb_budget()) {
            printf("FAIL iteration %d: rc0=%d rc1=%d used=%llu budget=%llu\n", i, rc[0], rc[1],
                   (unsigned long long)mb_used(), (unsigned long long)mb_budget());
            bad = 1; break;
        }
    }
    printf("race: %s (last: rc0=%d rc1=%d used=%llu budget=%llu)\n", bad ? "FAILED" : "ok", rc[0], rc[1],
           (unsigned long long)mb_used(), (unsigned long long)mb_budget());
    return bad;
}
