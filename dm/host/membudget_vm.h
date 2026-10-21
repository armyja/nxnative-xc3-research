// The VM side of the budget transactions, shared by the host's SVC handlers and by the tests.
//
// Separated from hle_svc.c so the tests exercise the production adapters rather than a copy. The context carries the
// region pointers, so nothing here reads a global and a test can point it at a small mmap.
#ifndef DM_MEMBUDGET_VM_H
#define DM_MEMBUDGET_VM_H
#include <stdint.h>
#include <stddef.h>

typedef struct { uint8_t *alias; uint8_t *heap; } mb_vm_ctx;

// Alias pages: map = 1 applies PROT_READ|PROT_WRITE, map = 0 releases (madvise + PROT_NONE). Host pages are 16 KB
// and Horizon pages 4 KB: a map rounds out, an unmap only releases host pages wholly inside the range.
int mb_vm_alias(void *ctx, uint64_t off, uint64_t size, int map);

// Heap resize: map = 2, arg1 = the heap size before this transaction, arg2 = the size after it. Both come from the
// budget transaction's own lock, never from a shadow copy the caller updates later.
int mb_vm_heap(void *ctx, uint64_t old_size, uint64_t new_size, int map);
#endif
