# Round 35: the owner's list has no type-2 record among those that pass; one record is filtered and its type is unobserved

**HEAD `7be6d27`**, no commit. Static reading plus one read-only probe run. No fix, no production change.

Evidence strength corrected first: last round I had no probe at the initialiser's entry, so "the initialiser was
never called" was overreach — only "those two points did not execute". This round adds the **entry** probe
(`main:e6a0ac`), so the statement below is now supported for this run. "Only caller" is also qualified: `0xe69d84` is
the only **direct `bl`** in the scanned image; indirect calls are not excluded.

## 1. What the predicates actually test
Both take the record and look at `[rec+8]` (a pointer to an object), then call `0x5c060` (a state accessor):
[Fenced excerpt omitted from the shareable research record.]
Record layout used by the loop: `+0x08` object pointer, `+0x10` **type** (`w8 = [rec+0x10] - 1`), `+0x14` **id**
(passed as `w1` to the handlers). `[rec+0]` is a word compared against -1 in predicate A.

Loop (`0xe69c48`), per 24-byte record in `[owner+8, owner+0x10)`:
[Fenced excerpt omitted from the shareable research record.]
The init branch does `0xe869b0(owner->[0x148]+0x20, id, 2)` and then calls `0xe6a0ac(owner, id, rec)`, which is the only
place the `+0x100` field is written on this cluster.

## 2. The run (owner 0x7d80058890, thread 1001)
Probes at `e69ca8` (every record entering the predicates), `e69cc8` (records that passed both), `e6a0ac` (initialiser
entry), `e6a0fc` (the store), `e6a194` (user entry), `e6a2b4` (the null read). Order, per record:

| # | record | type seen at `cmp` (`x8`+1) | passed predicates | dispatched |
|---|---|---|---|---|
| 1 | 0x7d8b125ad0 | 1 | yes | type 1 |
| 2 | 0x7d8b125ae8 | 1 | yes | type 1 |
| 3 | 0x7d8b125b00 | 1 | yes | type 1 |
| 4 | 0x7d8b125b18 | **not observed** | **no** (no `cmp` hit) | — |
| 5 | 0x7d8b125b30 | 8 | yes | type 8 → `0xe6a194` |

Then: `0xe6a194` (user, owner = 0x7d80058890) → `0xe6a2b4` reads `[owner+0x100]` → `CRASH pc=main+0x10141ac`.

**`0xe6a0ac` (initialiser entry) and `0xe6a0fc` (store) did not fire anywhere in the run**, i.e. **no owner dispatched
a type-2 record** in this run — this is now backed by the entry probe, not just the store.

So for this owner: the list contains five records, three are type 1, one is type 8 (the one that crashes), one was
**filtered by the predicates before its type was read**, and **no record reached the type-2 branch**.

## 3. Where the chain stops, precisely
- The owner's `+0x100` is null, and the type-8 handler consumes it without a null check.
- The field would only be filled by the type-2 branch, which did not run for this owner.
- Whether the list *contains* a type-2 record is **not determined**: the single filtered record (#4) never reached
  `cmp`, so its `+0x10` was never read. "Record missing" and "record present but filtered" are therefore still
  indistinguishable with the data captured.

## 4. The one missing value, and how to get it with the existing facility
**The type and id of the filtered record** (and, for completeness, of every record including filtered ones).
`DM_PROBE` already supports a memory suffix — `main:e69ca8@x20+0x10` prints 16 bytes at `rec+0x10`, i.e. the type
(`u32`) and the id (`u32`) for **every** record, filtered or not, at a point that is safe (the instruction there is
`mov x0,x20`, not PC-relative). That single change to the probe spec distinguishes:
- a type-2 record that was filtered out (its state failed `2 or 4`), from
- a list that simply has no type-2 record at all.

No new observation facility, no rewriter gate and no production change is needed for that.

## 5. Background, still not attributed
`save` clone `errno=45`, `nvnTextureWriteTexelsStrided` unimplemented and the exception-stack getter were not needed
by this chain and are not claimed as related.

## 6. Run facts
One run, host `dmhost-oe`, same profile/patches/library/map, 5 s cap, stopped by the same SIGSEGV at 2.80 s (exit 139),
log 51,674 bytes, no new dumps (both shaders already in the map). No player input, no second launch, no commit.
Artifacts: `work/experiments/first-runtime-pair-integrated/runs/20261021-095107/`.
