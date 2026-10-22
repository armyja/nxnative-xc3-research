# Round 32: the pair runs in the guest — libraries loaded, PSO created, one draw observed, then a null `am` controller

**HEAD `3c1117e`**, no commit, no tracked change. One supervised run, 2 s, stopped by a crash (not by the clock).

## 1. The resource conclusion is withdrawn — the counter was wrong, not just the prose
The reflections have **no** `cbufs` / `sbufs` / `textures` / `images` fields at all; they carry a **`bindings`** array.
My previous count read the absent top-level fields and therefore always printed 0. Machine-generated list
(`first-runtime-pair/bindings.tsv`, produced from `bindings[].kind`):

| key | stage | kind | msl_name | reg | arg_id |
|---|---|---|---|---|---|
| `58e2e00d24c6f3ea` | vs | **cbuf** | `vp_c3` | 0 | 0 |
| `5d36d4144f49ec9a` | ps | — | — | — | — |

So **VS has one constant buffer at register 0 and PS has none**, and the generated MSL reads
`(*spvDescriptorSet0.vp_c3)._m0[0..3]` — a real matrix access. "Reflection all zero / no resource access" is
**withdrawn**. `drv_reads = {}` (no driver-segment reads) is a different dimension and still holds, as does the
absence of texture / image / SSBO bindings. This is not a driver-base problem: it is a uniform slot 0 that the
reflection already mapped, and what was missing was a measurement of its runtime binding — now obtained below.

## 2. Integration profile
`work/experiments/first-runtime-pair-integrated/profile/010074F013262000/` clones the two-key profile and overlays
**only** `mem_reserve 0x1100000000` and `mem_alias 0x1000000000` (stack and `app_pool` unchanged); the `nvn_*`/shader
keys and all four shader tables are untouched. Non-comment diff is exactly those two lines. The chain was recomputed
with the real tool and is **still `83e5bf7805f3`** — memory keys are not part of it — matching the built artifacts, so
no hand-written chain and no mismatch to explain. Baseline and wide-VA profiles untouched.

Host rebuilt from this profile into
`first-runtime-pair-integrated/dmhost`, sha256 prefix `74d35e7eaceafbb5`, compile-time
`DM_GAME_MEM_RESERVE=0x1100000000`, `DM_GAME_MEM_ALIAS=0x1000000000`, `DM_GAME_APP_POOL=0xcd500000`. Shared
`dmhost` untouched. `DM_MSL_DIR=first-runtime-pair/out` (the directory that directly holds `b-83e5bf7805f3`), map =
the two-key map.

## 3. The run (`runs/20261021-093906`)
Supervisor as in Round 29 (real 5 s wall clock, `unset DM_WINDOW` rather than 0, `DM_AUDIO=0`, RSS/free-memory
sampling of its own child, 32 MiB dump cap, TERM→KILL). Switches verified in the code before use:
`DM_PSO_RECORD=<path>` (`fopen "a"`), `DM_NVN_KEYDUMP=<fs-key>[:count]` (matches `pr->sh[1]->key` prefix),
`DM_NVN_SHDUMP=<dir>` (missing-key dumps only), `DM_MEMSTAT=<tsv>`.

Identity recorded by the supervisor: host `74d35e7eaceafbb5`, profile `d8e19ed5baecf938`, map 264 bytes, 2 entries,
metallib dir `…/first-runtime-pair/out/b-83e5bf7805f3`.

What happened, in order:

1. **Map and library path**: `shader route B … shader map 2 entries (…/integrated/…/shader_map.tsv), metallib
   directory …/first-runtime-pair/out/b-83e5bf7805f3` — the chain matched the artifacts.
2. **Library loads** (`pso.tsv` `S` records): `S 58e2e00d24c6f3ea_b 0`, `S 5d36d4144f49ec9a_b 1`.
3. **Pipeline created** (`R` record) for the pair.
4. **One draw observed** (the acceptance point):
   ```
   [kd] F4 pass 6 vs=58e2e00d24c6f3ea_b fs=5d36d4144f49ec9a_b prim 5 vertices 4 instances 1 … target yes
   [kd]   attr 0 format 0x22 offset 0 stream 0
   [kd]   attr 1 format 0x25 offset 12 stream 0
   [kd]   stream 0 stride 24 …  vertex uniform r0 addr=… size=64
   [kd]     +000000 0.00234375 0 0 -1 0 -0.00416667 0 1 0 0 2 -1 0 0 0 1
   [pass] … B 6 st0 cb reg0 addr=… size=64 pool=…
   ```
   So the **runtime combination is observed in a single draw**, the vertex uniform **exists, 64 bytes, and is
   bound** with a transform matrix, and the binding resolved to real pool data. The guest's vertex layout is
   `format 0x22 @0`, `0x25 @12`, stride 24 — which is **not** the two-`float4` default; the offline reflection's
   `float4/float4` guess and my smoke layout were diagnostic only and are now contradicted by evidence.
5. **Frame 1 completed**: `[longframe] frame 1 (0.93 s) … submit+present 0.6 ms, GPU 0.4 ms`.
6. **Crash** at 2 s, after the frame:
   ```
   CRASH sig=11 addr=0 pc=sdk+0x33b0f0 lr=sdk+0x33b0f0
   x0=0 x1=… x2=0x84 …
   ```
   The instruction is
   ```
   sdk+0x33b0ec bl PLT _ZN2nn2am17GetSelfControllerEv
   sdk+0x33b0f0 ldr x8, [x0]          ← x0 = 0
   ```
   **First real blocker: `nn::am::GetSelfController()` returns null**, so the SDK dereferences it. The host has no
   `am` takeover (the init list shows `aoc`, `oe`, `err`, `fs`, `pctl`, `diag`, `nndiag` but not `am`). Not fixed this
   round.

No new dumps: both shaders were in the map, so `shdump` stayed empty (0 files) — expected.

## 4. Evidence levels
- Route B with the two-key map: **observed** (log line + 2 entries).
- Library load for both keys: **observed** (`S` records).
- PSO for this combination: **observed** (`R` record).
- VS/PS used together in one draw: **observed** (single `[kd]` line naming both).
- Uniform slot 0 bound with 64 bytes: **observed**; whether the matrix is *correct* is not established (no pixel
  comparison, no display validation).
- "Rendering works": **not claimed** — a draw API reached with a created PSO is not a correct image.

## 5. Memory
RSS samples: 147,120 KB then 179,408 KB (peak ≈ 175 MiB) before the crash; `DM_MEMSTAT` did write a row (frame-1
timing), and the dump cap was never approached. Alias virtual volume is a separate quantity and is not derived here.

## 6. Not done
No new shader translation, no library rebuild, no `c1_full`/`pso_manifest` fabrication (the two `[RED]` warnings are
still warnings, not failures), no HLE/rewriter/sysres/memory-key/driver-base change, no tracked edit, no push/PR, no
input/keys, no second launch. The `am` controller is the next blocker and is left untouched.
