#include "membudget.h"
#include <pthread.h>
#include <stdlib.h>
#include <string.h>

#define PAGE 4096u

static pthread_mutex_t g_lock = PTHREAD_MUTEX_INITIALIZER;
static uint64_t *g_bits;          // one bit per guest page of the alias region
static uint64_t g_pages;
static uint64_t g_cap, g_budget, g_fixed, g_heap_cap, g_heap, g_alias;

static void ensure(uint64_t pages) {
    if (pages <= g_pages) return;
    uint64_t words = (pages + 63) / 64;
    uint64_t *nb = realloc(g_bits, words * sizeof *nb);
    if (!nb) abort();
    memset(nb + (g_pages + 63) / 64, 0, (words - (g_pages + 63) / 64) * sizeof *nb);
    g_bits = nb; g_pages = pages;
}

void mb_init(uint64_t alias_cap, uint64_t budget, uint64_t fixed_bytes) {
    pthread_mutex_lock(&g_lock);
    ensure(alias_cap / PAGE + 1);
    g_cap = alias_cap; g_budget = budget; g_fixed = fixed_bytes; g_heap = 0; g_alias = 0; g_heap_cap = alias_cap;
    if (g_pages) memset(g_bits, 0, ((g_pages + 63) / 64) * sizeof *g_bits);
    pthread_mutex_unlock(&g_lock);
}
void mb_set_heap_cap(uint64_t cap) { pthread_mutex_lock(&g_lock); g_heap_cap = cap; pthread_mutex_unlock(&g_lock); }

// A range is valid when it is non-empty, page-aligned and inside the alias region, checked by subtraction so no
// off+size can wrap. Caller holds the lock.
static int range_ok(uint64_t off, uint64_t size) {
    if (!size) return 0;
    if ((off | size) & (PAGE - 1)) return 0;
    if (off > g_cap) return 0;
    if (size > g_cap - off) return 0;
    return 1;
}

static uint64_t count_bits(uint64_t off, uint64_t size, int set) {
    uint64_t p = off / PAGE, e = (off + size) / PAGE, n = 0;   // aligned, so this is exact
    for (; p < e; ) {
        uint64_t sh = p & 63, k = 64 - sh < e - p ? 64 - sh : e - p;
        uint64_t m = (k == 64 ? ~0ull : ((1ull << k) - 1) << sh);
        n += __builtin_popcountll((set ? g_bits[p >> 6] : ~g_bits[p >> 6]) & m);
        p += k;
    }
    return n;
}
static void set_bits(uint64_t off, uint64_t size, int on) {
    uint64_t p = off / PAGE, e = (off + size) / PAGE;
    for (; p < e; ) {
        uint64_t sh = p & 63, k = 64 - sh < e - p ? 64 - sh : e - p;
        uint64_t m = (k == 64 ? ~0ull : ((1ull << k) - 1) << sh);
        if (on) g_bits[p >> 6] |= m; else g_bits[p >> 6] &= ~m;
        p += k;
    }
}

static void snap(mb_result *r) {   // callers fill heap_before before the effect
    r->used_after = g_fixed + g_heap + g_alias;
    r->alias_after = g_alias; r->heap_after = g_heap; r->limit = g_budget;
}

int mb_map(uint64_t off, uint64_t size, mb_effect fx, void *ctx, mb_result *r) {
    mb_result tmp, *o = r ? r : &tmp;
    memset(o, 0, sizeof *o);
    pthread_mutex_lock(&g_lock);
    o->used_before = g_fixed + g_heap + g_alias; o->heap_before = g_heap;
    if (!range_ok(off, size)) { o->rc = MB_E_RANGE; snap(o); goto out; }
    uint64_t pages = count_bits(off, size, 0), need = pages * PAGE;   // pages <= cap/PAGE, no overflow
    o->new_bytes = need;
    // budget comparison by subtraction: need <= budget - used, no sum can wrap
    uint64_t used = g_fixed + g_heap + g_alias;
    if (used > g_budget || need > g_budget - used) { o->rc = MB_E_BUDGET; snap(o); goto out; }
    if (fx && fx(ctx, off, size, 1)) { o->rc = MB_E_EFFECT; snap(o); goto out; }   // nothing committed
    set_bits(off, size, 1);
    g_alias += need;
    o->rc = MB_OK; snap(o);
out:
    pthread_mutex_unlock(&g_lock);
    return o->rc;
}

int mb_unmap(uint64_t off, uint64_t size, mb_effect fx, void *ctx, mb_result *r) {
    mb_result tmp, *o = r ? r : &tmp;
    memset(o, 0, sizeof *o);
    pthread_mutex_lock(&g_lock);
    o->used_before = g_fixed + g_heap + g_alias; o->heap_before = g_heap;
    if (!range_ok(off, size)) { o->rc = MB_E_RANGE; snap(o); goto out; }
    uint64_t pages = count_bits(off, size, 1), freed = pages * PAGE;
    o->new_bytes = freed;
    if (fx && fx(ctx, off, size, 0)) { o->rc = MB_E_EFFECT; snap(o); goto out; }
    set_bits(off, size, 0);
    g_alias = g_alias >= freed ? g_alias - freed : 0;   // never negative
    o->rc = MB_OK; snap(o);
out:
    pthread_mutex_unlock(&g_lock);
    return o->rc;
}

int mb_set_heap(uint64_t size, mb_effect fx, void *ctx, mb_result *r) {
    mb_result tmp, *o = r ? r : &tmp;
    memset(o, 0, sizeof *o);
    pthread_mutex_lock(&g_lock);
    o->used_before = g_fixed + g_heap + g_alias; o->heap_before = g_heap;
    if (size > g_heap_cap) { o->rc = MB_E_CAP; snap(o); goto out; }
    uint64_t used = g_fixed + g_alias;                  // the heap part is replaced, not added
    if (used > g_budget || size > g_budget - used) { o->rc = MB_E_BUDGET; snap(o); goto out; }
    if (fx && fx(ctx, g_heap, size, 2)) { o->rc = MB_E_EFFECT; snap(o); goto out; }   // old size from this lock; refused: heap unchanged
    g_heap = size;
    o->rc = MB_OK; snap(o);
out:
    pthread_mutex_unlock(&g_lock);
    return o->rc;
}

uint64_t mb_alias(void) { pthread_mutex_lock(&g_lock); uint64_t v = g_alias; pthread_mutex_unlock(&g_lock); return v; }
uint64_t mb_heap(void) { pthread_mutex_lock(&g_lock); uint64_t v = g_heap; pthread_mutex_unlock(&g_lock); return v; }
uint64_t mb_used(void) { pthread_mutex_lock(&g_lock); uint64_t v = g_fixed + g_heap + g_alias; pthread_mutex_unlock(&g_lock); return v; }
uint64_t mb_budget(void) { return g_budget; }
