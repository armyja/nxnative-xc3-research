#include "membudget.h"
#include <pthread.h>
#include <stdlib.h>
#include <string.h>

#define PAGE 4096u

static pthread_mutex_t g_lock = PTHREAD_MUTEX_INITIALIZER;
static uint64_t *g_bits;          // one bit per guest page of the alias region
static uint64_t g_pages, g_words;
static uint64_t g_cap, g_budget, g_fixed, g_heap_cap, g_heap, g_alias;

static void ensure(uint64_t pages) {
    if (pages <= g_pages) return;
    uint64_t words = (pages + 63) / 64;
    uint64_t *nb = realloc(g_bits, words * sizeof *nb);
    if (!nb) abort();
    memset(nb + g_words, 0, (words - g_words) * sizeof *nb);
    g_bits = nb; g_words = words; g_pages = pages;
}

void mb_init(uint64_t alias_cap, uint64_t budget, uint64_t fixed_bytes) {
    pthread_mutex_lock(&g_lock);
    ensure(alias_cap / PAGE + 1);
    g_cap = alias_cap; g_budget = budget; g_fixed = fixed_bytes; g_heap = 0; g_alias = 0; g_heap_cap = alias_cap;
    if (g_words) memset(g_bits, 0, g_words * sizeof *g_bits);
    pthread_mutex_unlock(&g_lock);
}
void mb_set_fixed(uint64_t fixed_bytes) { pthread_mutex_lock(&g_lock); g_fixed = fixed_bytes; pthread_mutex_unlock(&g_lock); }
void mb_set_heap_cap(uint64_t cap) { pthread_mutex_lock(&g_lock); g_heap_cap = cap; pthread_mutex_unlock(&g_lock); }

// pages in [off, off+size) that are not set yet; caller holds the lock
static uint64_t count_clear(uint64_t off, uint64_t size) {
    uint64_t p = off / PAGE, e = (off + size + PAGE - 1) / PAGE, n = 0;
    if (e > g_pages) e = g_pages;
    for (; p < e; ) {
        uint64_t sh = p & 63, k = 64 - sh < e - p ? 64 - sh : e - p;
        uint64_t m = (k == 64 ? ~0ull : ((1ull << k) - 1) << sh);
        n += __builtin_popcountll(~g_bits[p >> 6] & m);
        p += k;
    }
    return n;
}
static void set_bits(uint64_t off, uint64_t size, int on) {
    uint64_t p = off / PAGE, e = (off + size + PAGE - 1) / PAGE;
    if (e > g_pages) e = g_pages;
    for (; p < e; ) {
        uint64_t sh = p & 63, k = 64 - sh < e - p ? 64 - sh : e - p;
        uint64_t m = (k == 64 ? ~0ull : ((1ull << k) - 1) << sh);
        if (on) g_bits[p >> 6] |= m; else g_bits[p >> 6] &= ~m;
        p += k;
    }
}
static uint64_t count_set(uint64_t off, uint64_t size) {
    uint64_t p = off / PAGE, e = (off + size + PAGE - 1) / PAGE, n = 0;
    if (e > g_pages) e = g_pages;
    for (; p < e; ) {
        uint64_t sh = p & 63, k = 64 - sh < e - p ? 64 - sh : e - p;
        uint64_t m = (k == 64 ? ~0ull : ((1ull << k) - 1) << sh);
        n += __builtin_popcountll(g_bits[p >> 6] & m);
        p += k;
    }
    return n;
}

int mb_map(uint64_t off, uint64_t size, uint64_t *new_bytes, uint64_t *used_after) {
    if (off + size < off) return 1;                        // range overflow: refuse rather than wrap
    pthread_mutex_lock(&g_lock);
    uint64_t pages = count_clear(off, size), need = pages * PAGE;
    if (need && g_fixed + g_heap + g_alias + need > g_budget) {   // check before any state changes
        pthread_mutex_unlock(&g_lock);
        if (new_bytes) *new_bytes = need;
        if (used_after) *used_after = g_fixed + g_heap + g_alias;
        return 1;
    }
    set_bits(off, size, 1);
    g_alias += need;
    if (new_bytes) *new_bytes = need;
    if (used_after) *used_after = g_fixed + g_heap + g_alias;
    pthread_mutex_unlock(&g_lock);
    return 0;
}

void mb_unmap(uint64_t off, uint64_t size, uint64_t *cleared_bytes, uint64_t *used_after) {
    pthread_mutex_lock(&g_lock);
    uint64_t pages = count_set(off, size), freed = pages * PAGE;
    set_bits(off, size, 0);
    g_alias = g_alias >= freed ? g_alias - freed : 0;       // never negative
    if (cleared_bytes) *cleared_bytes = freed;
    if (used_after) *used_after = g_fixed + g_heap + g_alias;
    pthread_mutex_unlock(&g_lock);
}

int mb_set_heap(uint64_t size, uint64_t *used_after) {
    pthread_mutex_lock(&g_lock);
    int rc = 0;
    if (size > g_heap_cap) rc = 2;
    else if (g_fixed + size + g_alias > g_budget) rc = 1;   // same pool as the alias mappings
    else g_heap = size;
    if (used_after) *used_after = g_fixed + g_heap + g_alias;
    pthread_mutex_unlock(&g_lock);
    return rc;
}

uint64_t mb_alias(void) { pthread_mutex_lock(&g_lock); uint64_t v = g_alias; pthread_mutex_unlock(&g_lock); return v; }
uint64_t mb_heap(void) { pthread_mutex_lock(&g_lock); uint64_t v = g_heap; pthread_mutex_unlock(&g_lock); return v; }
uint64_t mb_used(void) { pthread_mutex_lock(&g_lock); uint64_t v = g_fixed + g_heap + g_alias; pthread_mutex_unlock(&g_lock); return v; }
uint64_t mb_budget(void) { return g_budget; }
