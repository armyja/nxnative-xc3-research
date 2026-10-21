#include "membudget_vm.h"
#include <sys/mman.h>
#include <unistd.h>

int mb_vm_alias(void *ctx, uint64_t off, uint64_t size, int map) {
    uint8_t *a = ((mb_vm_ctx *)ctx)->alias + off;
    uintptr_t pg = (uintptr_t)getpagesize(), lo = (uintptr_t)a, hi = lo + size;
    uintptr_t mlo = map ? lo & ~(pg - 1) : (lo + pg - 1) & ~(pg - 1);
    uintptr_t mhi = map ? (hi + pg - 1) & ~(pg - 1) : hi & ~(pg - 1);
    if (mhi <= mlo) return 0;
    if (map) return mprotect((void *)mlo, mhi - mlo, PROT_READ | PROT_WRITE) ? -1 : 0;
    madvise((void *)mlo, mhi - mlo, MADV_FREE);   // a partly covered host page may still be used next to it
    return mprotect((void *)mlo, mhi - mlo, PROT_NONE) ? -1 : 0;
}

int mb_vm_heap(void *ctx, uint64_t old_size, uint64_t new_size, int map) {
    uint8_t *h = ((mb_vm_ctx *)ctx)->heap;
    (void)map;
    if (!h || old_size == new_size) return old_size == new_size ? 0 : -1;
    if (new_size > old_size) return mprotect(h + old_size, new_size - old_size, PROT_READ | PROT_WRITE) ? -1 : 0;
    return mprotect(h + new_size, old_size - new_size, PROT_NONE) ? -1 : 0;
}
