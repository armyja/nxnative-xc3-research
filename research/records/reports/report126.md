# report126 · allocator 修正后的 VS/GS 两次独立 asCompute 探针

日期：2026-10-22 05:32–05:58（本机）
HEAD `14082571ea0a1ea515be64b963e4f4d7c39a3097`（未变）；仅 SSD；无生产/lock/profile/facts/库/host/guard 改动、无 gate/guest/资源采样、无 commit。

---

## 0 结果

- 修正 probe-only allocator：set0 动态 binding 从 **2** 开始，避开 asCompute 预留 set0 0/1；CB/SB/tex/image 共用同一递增计数并支持 array count；坏 count 拒绝。
- 纯逻辑 self-test：CB=2, SB=3, tex 3 项=4..6, image 2 项=7..8, next=9；0 count 拒绝；不同 set 相同 binding 不冲突（allocator 只分配 set0）。`alloc_self_test: ok`。
- 两次**独立** `Translate(true)` 成功（先 VS，后 GS；无 combined context）：
  - VS SPV 9364 B，sha `28c62126…`；GS SPV 22932 B，sha `4da87947…`；两者 GLCompute，`LocalSize=32,32,1`。
  - VS reservations：input 133 words / output 5 words；GS：input 5 / output 5。stride 相等，但**内容布局不做相等断言**。
  - `SetVertexOutputMapForGeometryAsCompute` 在 VS `Translate(true)` **之后**、GS `Translate(true)` 之前取 map；已记录。
  - 无 `Translate(other,true)`、无第二条件 fallback、无 FP64 fallback、无 `Generate*Passthrough`；`uses_float64=false`。
- **binding 冲突已消失**：GS `vb_info` set0/b1，原纹理 `gp_t_tcb_8` 重分配到 set0/**b2**，原 cbuf `gp_c3` set0/**b3**；同 module 无重复 `(set,binding)`。这不证明库本身支持/不支持 asCompute，只说明 report125 的冲突来自普通 wrapper allocator 从 b1 分配、未避开预留。
- 仍无 SPIR-V validator/Metal/dispatch/GPU 证据；raw 成功 ≠ 合法/可执行。

## 1 allocator 证据

- 原 probe allocator：`_binding=1` 且所有动态资源 set0；asCompute 预留 support0/vb_info1 未告知 allocator，导致纹理/`vb_info` 同 set0/b1。
- 新 allocator（实验 helper，仅本次）：
  - 单递增 `_next`，初始 2；
  - `Next(count,what)` 拒绝 count<=0，按 count 整段预留；
  - CB/SB 每次 1，tex/image 按 count 跨度；
  - 只分配 set0；set1/set2 预留资源不参与，因此“不同 set 同 binding”不被误判冲突。
- 实际 GS 动态资源：texture b2、cbuf b3；VS 无原动态资源（只有 reserved `ib_data` set2/b0、`vb_data0` set2/b2）。
- 预留计数归属：`ReservedConstantBuffers=2` → set0 b0(support)/b1(vb_info)；`ReservedStorageBuffers=3` → set1 b0/b1/b2；
  `ReservedTextures=34` → set2 b0(index)/b1(trb)/b2..b33(vb_data)，**不是 set0 保留 34 项**。

## 2 两份 SPV

| | VS asCompute | GS asCompute |
|---|---|---|
| ExecutionModel | GLCompute | GLCompute |
| LocalSize | 32,32,1 | 32,32,1 |
| size/sha | 9364 / 28c62126… | 22932 / 4da87947… |
| LD/ST/imageFetch | 122/89/5 | 359/269/1 |
| Emit/End | 0/0 | 0/0 |
| set0 | support0, vb_info1 | support0, vb_info1, texture2, cbuf3 |
| set1 | vertex_output0 | vertex_output0, geometry_vb1, geometry_ib2 |
| set2 | ib_data0, vb_data0 at2 | trb_data1 |

- VS `vb_data0` set2/b2、`ib_data` set2/b0 来自 VS compute 的顶点/索引 texture buffer；GS 只用 `trb_data` set2/b1 与 set1 输出 buffer。
- 同一 `(set,binding)` 在不同 module 合法（例如两者都有 support0/vb_info1/vertex_output set1b0）；不能据此说内容/布局自动一致，host 需显式绑定/重绑。
- VS output 5 words 与 GS input 5 words 对齐；只证 stride 相等，成员顺序/内容映射未由该比较证明。

## 3 证明边界

- 仅证明：allocator 修正后，VS/GS 各自一次 asCompute Translate 可产出 GLCompute SPV；同 module 无重复 set/binding；Emit/End 已降级；公开 reservations 可读。
- 不证明：SPIR-V validator 合法性（未装 spirv-val）、Metal 支持/执行、host buffer 布局/绑定、dispatch/indirect/sync、GPU/像素/数值；也不证明 combined `Translate(other,true)` 可用。两次独立请求 ≠ 合并 Translate。

## 4 D：下一次可定义几个请求

- 现在可以定义 **2 个独立的 asCompute 请求**（VS 一次、GS 一次），各自 module；不能把它们称为 combined 请求。
- 仍不能定义 `Translate(other,true)` 的组合请求；无调用者、无共享 layout 契约，且本探针未覆盖。
- host 仍需：按 module 绑定/重绑全部 set0/1/2 资源，处理 VS→GS 的 `vertex_output` 共享、trb/索引、dispatch/count/sync；这些是执行前置，不是本轮 raw 翻译前置。

## 5 文档/状态

- report125 §6 追加 allocator 因果限界与“2stage 独立 ≠ 合并 Translate”澄清。
- INDEX/EXPERIMENTS 加 exp130（allocator fix/2-stage probe/evidence-only）；request 130 归档。
- HEAD `1408257`；`git status` 仅既有未跟踪 `XC3-SETUP.md`；AGENTS.md/XC3-SETUP.md/共享 host/旧证据未动。
- 45 分钟内完成；停止 review，无自动后续。
