// Two threads must not both fit into the same remaining budget.
#include <pthread.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <unistd.h>
#include "../../host/membudget.h"
#define PAGE 4096ull
static volatile int arrived;
static int rc1, rc2;
static void *worker(void *arg) {
    long which = (long)arg;
    __sync_add_and_fetch(&arrived, 1);
    while (arrived < 2) sched_yield();           // both threads reach the map call together
    uint64_t nb, used;
    int r = mb_map(which * 1024 * PAGE, 512 * PAGE, &nb, &used);   // 2 MiB each, distinct ranges
    *(which ? &rc2 : &rc1) = r;
    return NULL;
}
int main(void) {
    // pool room = 2 MiB + 1 page: only one of the two 2 MiB maps fits
    uint64_t BUDGET = 2 * 1024 * 1024 + PAGE;
    mb_init(64 * 1024 * 1024, BUDGET, 0);
    pthread_t a, b;
    pthread_create(&a, NULL, worker, (void *)0);
    pthread_create(&b, NULL, worker, (void *)1);
    pthread_join(a, NULL); pthread_join(b, NULL);
    int ok = (rc1 == 0) + (rc2 == 0);
    printf("race: rc1=%d rc2=%d successes=%d alias=%llu used=%llu budget=%llu\n",
           rc1, rc2, ok, (unsigned long long)mb_alias(), (unsigned long long)mb_used(), (unsigned long long)mb_budget());
    int bad = ok != 1 || mb_used() > mb_budget();
    printf("race: %s\n", bad ? "FAILED" : "ok");
    return bad;
}
