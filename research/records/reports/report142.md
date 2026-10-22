# report142 · 95bf 真实资源 observer 设计（只读/CPU，未实现）

日期：2026-10-22 16:00–16:40（本机）
HEAD `14082571ea0a1ea515be64b963e4f4d7c39a3097`（未变）；仅 SSD 只读/CPU；无 build/raw/cross/metal/PSO/device/GPU/guest、无生产/库/lock/guard 改动、无 commit。

---

## A. report141 次数/artifact 勘误

- report141 §6 已追加完整 attempt 表：实际 **4 次 GS raw/4 SPV、2 套 air+metallib、2 次 PSO**（初版 off/on、final off/on）。
- 超界原因：为接生产 predicate 做非语义 gate refactor 后重发 final pair；初版不能当“build-validation”扣除。
- 最终证据 pair 是 final-off/final-on：off SPV `4da87947…`（同旧基线），on `939f724d…`；初版 #1/#2 仅保留历史 artifact。
- 初版 pre-refactor DLL/source identity **unknown**，不重跑补证；on/on-final metallib `c3d170fd…` 与 report129 fixture 变体逐字节相同，是 **artifact identity**，可关联历史 synthetic GPU 测试，不是 NVN 语义/通用 flag 正确。
- 后续先定 predicate/测试接线再消耗限定 probe；耗尽即交缺口；不为非语义 refactor 自动重发。

## B. 触发与 stage 事实

- 现有触发是 `kd_draw`（`nvn_mtl.m:5509`）：`DM_NVN_KEYDUMP` 的 key 前缀匹配 **PS** `pr->sh[1]->key`；`kd_geom_line` 在 `:5521`。
- observer 计划放在 `kd_geom_line` 之后、`kd_draw` 返回前；原 draw 调用在 `:6471`（`g_kd_force = kd_draw(...)`），不改变返回值/不抛异常，所以失败仍可达 draw。
- 目标：PS2e16 + GS95bf；先复用 `kdg_build`/`kdg_cached_probe` 的 lookup-only identity，扫描 `S.bst[2]` 的 nstage/key，不把 keys 列表 index1 当 stage。
- **stage 2 的来源**：`S.bst[2]` 由 `OP_BIND_PROGRAM`（`:4225`）的 `p_bind_program.stages` 经 `bind_stages`（`:3212`）按 bit 写入；bit 0=vertex、1=fragment、2=geometry（`p_bind_program` 定义 `nvn_obj.h:114`；`S.bst` 注释 `:3168`）。这是实际 state op/bit mapping，不是只引 `shader_split` 注释。
- off 零额外工作：`kd_draw` 在 `left<=0`/PS key 不匹配时已 return；observer 只在其后调用。目标 GS 不匹配时只做一次 key 扫描并记 `knownskipped`，不进入资源读取。

## C. candidate 映射与记录范围

仅按当前转换规则记录 **candidate**，不是独立 title-base 证据：

- `gp_c3`：`dmsh_build.reflect`（`:342-344`）将 `*_cN` 映射 `reg=N-3`；`c3→0`。候选真实状态 `S.ubo[2][0]`（geometry stage，`nvn_stage=2`）。
- `gp_t_tcb_8`：`decode_tex`（`:308-320`）用 `TEX_BASE=0x20`、8 B/slot；handle 8 的 byte 0x20 → candidate slot0；候选 `S.tex[2][0]`。这不是 native res handle8 直接当 slot。
- sampler：combined handle 的 `>>20`；`reflect` 的 `samp_tex`；候选从 `S.tex[2][0]>>20` 取，**不假设独立 `S.samp[2][0]`**；若同时有 `S.samp` 值，另记 raw，不合并。
- 记录范围（有界）：
  - `ubo`: 16 槽非零 mask；slot0 的 raw `addr/size`；**不读内容**。
  - `tex`: 128 槽非零 mask/count + 前若干非零 slot 的 raw handle/tid/ser；slot0 必列。
  - `samp`: 128 槽非零 mask/count；slot0 raw（若有）；不 dump 全表。
  - draw: primitive/count/instances/base_instance/drawkind/R.rt count。
- **lastbind 不存在**：`S.ubo` 是 `OP_BIND_UBO`（`:4244`）写入的当前状态；没有 bind 事件序列/时间戳。observer 只能标 `bind_source=current_S_state`，不能编造“同 bind/sametime”。

## D. cbuf 前 8B 的安全读取

- `S.ubo[2][0]` 是 `p_bind_buf {stage,index,addr,size}`（`nvn_obj.h:119`）；raw 地址。
- 现有 `mtl_addr`（`:431`）可做 guest addr→MTL buffer 映射，但它先 `pc_get`/`pool_find`，在 `g_mu` 下 `pool_res` 后**解锁再返回指针**；没有 pin/生命周期保证，也可能与 pending writes/alias 交互。**不能据此直接解引用 8B 当安全内容**。
- `mtl_gpu_addr`、`arena_alloc`/`g_cur_arena`/argument slots 是 GPU address/合成 c0 路径，不能与真实 guest cbuf 混用；observer 初期只记 `addr/size`，标 `contents=unavailable`。
- 未来 contents 最小前置：范围落单一 pool/page、buffer 有 pin/retain、在锁内复制 8B、检查 `pend_hits`/alias/CPU-write generation、不触发 upload；若任一不能证明，继续 unavailable，不新增 HLE/映射。
- 不调用 `mtl_gpu_addr`/`tex_mtl`/`tex_fast_rid`/`samp_fast` 或创建对象。

## E. texture/sampler/TF

- `S.tex[stage][slot]` 为 64-bit raw handle（state_op `OP_BIND_TEX` `:4246`）；低20 tid。`h_ser`（`:4462`）只查 `g_tser[tid]` atomic serial；`g_treg[tid]` 的 `t.d`（`nvn_texdesc` target/format/width/height/depth/samples）、`ok`、`serial` 在 `g_rmu`（`:2635`）下复制 scalar；**不把 serial 当 final resource**，不读 view/不调用 lookup构建。
- sampler：`S.samp`（state_op `:4247`）；combined source 的 `sid=handle>>20`；在 `g_rmu` 下检查 `g_sreg_ok[sid]` 并复制 `samp_par`（`nvn_obj.h:48`；min/mag/wrap/lod/border）；缺项记 unknown。
- `S.tex`/`S.samp` 当前状态可直接读（submit thread），注册表需 `g_rmu`；`h_ser` atomic 只用于 serial hint。记录 `raw handle`、`tid`、`h_ser`、`registered/ok`、`d.*`、`sid`、`samp_ok`；不创建 MTLTexture/MTLSamplerState。
- TF：host 只有 NVN 原型/名字（`nvn_protos.h:359-375`），没有 Begin/End/Bind 状态保存；**TF unknown**，不能由 `StreamOutMask=1` 或未见日志推 TF off。PS2e16 资源/RT 仅作为后续独立 snapshot 需求，不在本次 observer 扩多目标。

## F. 可直接接线的 observer 设计

### F.1 原型/调用

- 新诊断头 `dm/gfx/nvn/nvn_kd_res.h`（纯 helper + 固定 line 格式），在 `nvn_mtl.m` 的 `kd_geom_line` 后调用
  `kd_res_line(pr, dw, di)`；不改变 `kd_draw` 返回、不 early return、不分配。
- 触发条件：PS key 精确 `2e16c536b845ea0e`；`S.bst[2]` 的 lookup-only key 列表含 `95bfab6122539993`；一次性 static。
- 匹配失败分四类输出：`hit`（目标+资源可读）、`identityunknown`（GS/PS 无 key/缺 state）、
  `knownskipped`（PS 目标但 GS 非 95bf）、`notreached`（无 KEYDUMP/未到该 draw）；每类一行，最长 1024B。
- `unavailable` 作为字段状态（`ubo_contents`, `tex_registry`, `sampler_registry`, `tf`），不把缺项写成 0。

### F.2 字段表（实现按此接线）

| field | type | source | lock/range | absence | claim |
|---|---|---|---|---|---|
| ps_key | char[17] | `pr->sh[1]->key` | submit thread | identityunknown | identity only |
| gs_key_match | bool | `S.bst[2]` key list via `prog_key_cached` | lookup-only, nstage≤6 | identityunknown | identity only |
| stage | u32 | `S.bst[2]` / `OP_BIND_PROGRAM` bit2 | submit thread | notreached | state fact |
| draw | 5×i32+kind | `kd_draw` args `dw`/`di` | submit thread | notreached | state fact |
| ubo_mask | u16 | `S.ubo[2][0..15].size/addr` | submit thread | unavailable | current state |
| ubo0_addr/size | u64×2 | `S.ubo[2][0]` (`p_bind_buf`) | submit thread | unbound | raw current state |
| ubo0_content | 2×u32 | **not read initially** | none | unavailable | absent |
| tex_mask/count | u128/u32 | `S.tex[2][0..127]` | submit thread | unavailable | current state |
| tex0_raw | u64 | `S.tex[2][0]` | submit thread | unbound | current handle |
| tex0_tid/ser | u32/u64 | low20; `h_ser` | tid<1M; atomic | unknown | serial hint |
| tex0_desc | 7×i32/u32 | `g_treg[tid].t.d` | `g_rmu`; tid<g_ntreg && ok | registryunknown | registered scalar |
| samp_mask | u16 | `S.samp[2][0..127]` nonzero | submit thread | unavailable | current state |
| samp0_sid | u32 | `S.tex[2][0]>>20`; optional `S.samp` | submit thread | unknown | candidate |
| samp0_par | 11×u8/f32 | `g_sreg[sid]` + `g_sreg_ok` | `g_rmu` | samplerunknown | registered scalar |
| tf | enum | no host state | none | unknown | not inferable |
| rt_count | u32 | `R.rt.n` | submit thread | unavailable | summary only |

- Bounded sizes: ubo 16 masks + slot0 only; tex/samp 128-bit masks + at most first 8 nonzero slots; no full PASSDUMP; no dynamic allocation; line cap.

### F.3 结果/回归

- 纯 CPU helper 测试（`t_kd_res.c`，不 device）：hit、identityunknown、knownskipped、notreached、one-shot、无 KEYDUMP 零调用、缺 ubo/tex/samp/TF 的 absence、line cap。预测器/真实 case 接线回归在后续 host 诊断编译 + guest 单独授权；本设计不执行。
- 下一实现 scope：诊断源码 + 实验 host 编译（不改正常 draw/GS guard/生产 profile）；guest snapshot 必须另授权。
- checkpoint：本设计（完成）→ observer 实现/CPU 测试（诊断源码，无 guest）→ guest 只读快照（单独授权）→ 实验 route（生产源码/lock/chain + guest/GPU，最大）。
- 现有 synthetic GPU checkpoint 冻结，不重跑；生产 flag 不启用。

## 状态

- INDEX/EXPERIMENTS 加 exp146（observer 设计/read-only）；request 146 归档。
- HEAD `1408257`；`git status` 仅既有未跟踪 `XC3-SETUP.md`；AGENTS.md/XC3-SETUP.md/共享 host/旧证据未动。
- 45 分钟内完成；停止 review，无自动实现/guest/GPU。
