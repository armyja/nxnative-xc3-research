# report140 · 95bf 实验接线缺口与去补丁方案（只读审计）

日期：2026-10-22 14:25–15:05（本机）
HEAD `14082571ea0a1ea515be64b963e4f4d7c39a3097`（未变）；仅 SSD/CPU 只读；无实现/build/翻译/GPU/guest、无生产/库/lock/guard 改动、无 commit。

---

## A. 去手工 PointSize 补丁

### 现状证据

- `EmitterContext.EmitStart`（`EmitterContext.cs:84-89`）只有 `Stage == Vertex` 写 `IoVariable.PointSize`；
  `VertexAsCompute` 分支不写。`Translator.EmitOutputsInitialization`（`Translator.cs:207-210`）只对 `Stage == Vertex`
  调 `InitializeVertexOutputs`；geometry 不初始化 PointSize。
- `ResourceReservations.FillIoOffsetMap`（`ResourceReservations.cs:98-103`）无条件把 Position4 + PointSize 放进
  layout，因此 asCompute GS output 固定 5 words；95bf 的 SASS 只写 Position `0x70..0x7c`，不写 PointSize。
- 95bf SPH：`GpPassthrough=0`、`OutputTopology=7`（TriangleStrip）、`MaxOutputVertexCount=4`、
  `StreamOutMask=1`、`DoesGlobalStore=0`、`StoreReqStart=StoreReqEnd=0`（`gs-sph-decode/six-gs.json`）。
  `StreamOutMask` 非零不能单独证明 TF 正在消费 PointSize；需 host 的 TF enabled/输出表才能确认。
- PS2e16 没有 PointSize 输入（PointSize 不是普通 varying）；triangle strip 的光栅不使用 PointSize。native GS
  路径仍在 `EmitterStart` 走 `Stage == Geometry`，没有默认写入；不能拿 native 的“可能 undefined”当安全证明。
- 结论：`PointSize=1` 是 fixture patch 的 synthetic 值，**不是 NVN/GS 真实默认**。现有合成测试还主动读取该 word，
  所以那里的 1 是测试契约，不是“不可观察 padding”的 compiler refinement。

### 两个可实施选项

**选项 A：GS-asCompute 入口定义未写 PointSize（首选设计）**

- 在 `EmitShader` 的 main/`initializeOutputs` 分支（`Translator.cs:205-210` 附近）为
  `vertexAsCompute && stage == Geometry` 增加一次输出初始化；不要在 `EmitterContext.EmitStart` 的无条件路径重复写。
- 写 `IoVariable.PointSize`，值来源必须明确：`Definitions.PointSize` 是 `GpuGraphicsState.PointSize`，不能假设 NVN 默认；
  若只是不可观察 refinement，可用固定值但必须在设计里标注“任意、非语义”。
- 影响：写的 GS 后续覆盖，无行为变化；PointList（若 PointSize 影响 raster）或 TF 实际输出 PointSize 时可观察；
  native GS 不共享此修复；host 若读取 geometry_vb word4，也会观察。
- 充分条件（全部满足才能当 refinement）：
  1) 实际 topology 不是 PointList；95bf=TriangleStrip（满足，但仅此 key）；
  2) 无实际 TF 消费 PointSize；95bf 的 StreamOutMask/StoreReq 只说明“需要进一步读 host TF 状态”，未证明（不满足）；
  3) PS/raster 不消费该 word；triangle strip + PS 无 PointSize（面值满足，但仍需 host/ABI 不读）；
  4) 输出 ABI 消费者不读 word4；真实 host 若读 5-word ABI/做校验则不满足。
- 因为 (2)(4) 未证，**不能把 A 直接投入 guest**；可作为隔离 feature flag 的下一步验证。

**选项 B：ABI 排除/不复制确定不被消费字段**

- 在 `FillIoOffsetMap` 条件性省略 PointSize，或在 GS 输出 copy 中省略 word4；需要新增 `PointSizeWritten`/消费方可用性
  跟踪（当前 `IoUsage` 只有 ClipDistancesWritten，`ResourceReservations.cs:105`），并改变 `OutputSizePerInvocation`
  从 5 到 4。
- 影响：geometry_vb stride/IB/offset/passthrough 5-word ABI 全部变化；host/缓存/manifest 都要新版本；TF/PointList
  仍可能需要该字段；比 A 更大、更易破坏真实 ABI。
- 结论：B 不是当前最小修复；除非证明字段永不被消费且愿意改 ABI，否则不选。

---

## B. 真实资源绑定：三个空间

`[kd-geom]` 现有日志（`kdgeom-plan/run-20261022-041419/boot.log:240-241`）只有
`[kd] F1508 pass3168 vs=... fs=... prim0 vertices2304 instances1 ...` 和
`[kd-geom] ... nstage=3 cached=3/3 keys=[d165...,95bf...,2e16...]`；**没有 cbuf3/texture/sampler 的实际绑定值**。

### 空间区分（静态源码）

1. **combined source/program 列表 index**：`[kd-geom]` 的 `keys` 顺序是 VS/GS/PS；`nstage=3`、GS 在列表 index1。
   这不是 NVN stage，不能把 index1 当 geometry stage。
2. **NVN stage**：NVN stage 0=vertex、1=pixel、2=geometry、3=hull、4=domain、5=compute
   （`shader_split.py` 头部注释）。真实 GS 资源应读 `S.ubo[2][...]`/`S.tex[2][...]`，不是 stage1。
3. **shader constant bank / MSL 名字**：95bf MSL `gp_c3` 的 `c3` 是 constant segment 3；`dmsh_build.reflect`
   （`dmsh_build.py:342-344`）把 `*_cN` 映射为 `kind=cbuf, reg=N-3`，所以 `c3` → NVN uniform **reg0**；
   真实地址在 `S.ubo[2][0]`（stage geometry）。这不是“cbuf slot3”。
4. **texture handle 8**：`gp_t_tcb_8` 的 8 是 c[2] handle-table word；`decode_tex`（`dmsh_build.py:308-320`）
   用 `TEX_BASE`（profile `nvn_tex_base`，本游戏 0x20）+ 8 bytes/slot 解码：handle 8 的 byte 0x20 →
   **NVN texture slot0**，不是 slot8。`res.json` 里的 handle8 不能当 NVN slot；native res 也没给 slot。
5. **sampler**：`gp_t_tcb_8Smplr` 无独立 `cb`，`reflect` 走 `samp_tex reg=texture slot`；host
   （`nvn_mtl.m:3868-3872`）在 combined handle 情况从 `S.tex[stage][reg] >> 20` 取 sampler ID，
   没有单独 sampler bank 可假设。

### 需要什么直接证据

- 逐项缺：`S.ubo[2][0]` 的地址/size/前 8B（cbuf3 的 x/y）；`S.tex[2][0]` 的 handle/serial；
  该 handle 高位 sampler ID；`S.samp[2][...]` 是否被使用；GS 的实际 `nvn_stage=2`；draw 对应 target/viewport；
  PS2e16 的 CB/texture/sampler 绑定；TF enabled/输出表。
- 现有 `DM_NVN_CBDUMP`/`DM_NVN_BINDAUDIT` 可观察 draw-time 绑定，但不是 GS-keyed、会写磁盘/有 side channel；
  不能直接当本轮证据。

### 未来只读快照设计（不实现）

- 插入点：`[kd-geom]` 已确认源为 present、`S.bst[2]` 非空且 95bf key 命中后，draw 之前；单独 `kdg_res` helper。
- 只读：`S.ubo[2][0]`（地址/size/前 2 words）、`S.tex[2][0]`（handle/serial）、combined handle>>20、target/prim；
  仅 lookup-only `prog_key_cached`；失败/缺失只打 `unavailable`，仍让原 draw 路径继续；无 predictor 事件、无分配、
  无 Metal 调用、无 guest 内存写。需要未来 host 源码诊断改动 + guest run 授权；本轮不加。

---

## C. 实验接线最小路径

### 现有门

- `dmsh_stage.py` 在选中 key 上、cache 之前拒绝任何 `gs`；`shader_split.py` 明确 GS 链不生成 VS/PS pair；
  host `nvn_mtl.m` 只绑定 `pr->sh[0]`/`pr->sh[1]`，没有 geometry stage。
- 因此不能“让 GS 通过正常链”或删掉 guard。最小实验路由必须是**精确 allowlist 的独立 build/host route**：
  keys 恰为 `d1657e…`(VS)、`95bf…`(GS)、`2e16…`(PS)，primitive Points，draw 1 次；其他 GS 仍由现 guard 拒绝，
  不存在 VS/PS hardcode fallback 或跳过 GS。正常 stage/map/pair 规则不修改。

### ABI 差距

- compute GS 输出：`geometry_vb_output` set1/b1、`geometry_ib_output` set1/b2；report137 passthrough 读 set1/b0。
  路由必须把 GS VB 重绑到 b0；passthrough 的 VertexIndex 需对应 GS 展开顶点顺序；IB 是 GPU 生成的 uint32，
  TriangleStrip 4 个 sentinel；不能假设 guest IB 或 `indexCount=5`。
- 真实 PS2e16：需要原 cbuf/texture/sampler/RT 的 AB 与 pass attachment；report138 的固定 green test PS 不是真实 PS，
  不能沿用。
- 真实输入：guest VS 的 vb_info/vb/ib、GS 的 cbuf3/texture handle8/sampler、实例/base/draw、原 viewport/scissor/
  attachment；VS/GS compute resource 尺寸与 `geometry_vb`/`ib` 容量需从实际 draw 计算，不能复用 toy fixture。
- 需要：独立 route manifest（key/SHA/chain/primitive/resource map/expected ABI）、host scheduling exact-match、
  reflection/argument encoder、library cache 以新 chain 为键、失败 fail-closed。
- AGENTS 影响：`nvn_mtl.m`/`dmsh_build.py` 是 shared tool；AGENTS 要求 per-game profile 和每次 chain 变更跑所有受影响
  profile，且其它 title 走 profile/chain，不在 shared code 加例外。最小隔离应落在 XC3 profile/route allowlist + 新 chain，
  不改 global GS 支持；否则会影响其它 title/共享 host。

---

## D. 最小 checkpoint 与首选动作

1. **本审计（完成）**：只读，无需 guest/GPU。
2. **去补丁隔离译器验证**（首选 bounded 下一步）：在 pinned 源码**副本**加 feature flag/初始化分支，生成 95bf MSL/SPIR-V
   与未改版 diff；仅 SSD build，不改 vendored DLL/lock/生产工具，不跑 GPU/guest。需新的 build 授权，不需要 guest。
3. **真实 GS 资源只读快照**：在 host 诊断钩子读取 `S.ubo[2][0]`/`S.tex[2][0]`/sampler/target；需要生产源码诊断改动 +
   单独 guest run 授权；不 dispatch。
4. **实验 host route**：精确 allowlist + 新 chain/lock + 真实 PS/resources + 一次 guest/GPU；需生产源码、lock/chain、
   guest 和 GPU 多重授权，风险最大。

- 首选：**2**。它直接关闭 A 的 PointSize 缺值设计，不依赖 guest；B 的真实资源仍是阻塞，但应作为独立的第 3 步，
  不把 A/B/host 合成一次大改。
- 现有合成 GPU 证据（report135/138/139）足够支持 fixture/ABI/pixel 边界，不重跑；不能替代真实 95bf guest 资源/PS。

## E. future 日志要求/状态

- 新 harness 必须从实际参数/资源 spec 变量生成 `indexCount`、row、backing/payload 日志，禁止再复制旧硬编码打印串；
  report139 的 `indexCount5`/`payload544` 只是历史日志缺陷，不重跑。
- 文档：INDEX/EXPERIMENTS 加 exp144（95bf 接线/去补丁审计，read-only）；request 144 归档。
- HEAD `1408257`；`git status` 仅既有未跟踪 `XC3-SETUP.md`；AGENTS.md/XC3-SETUP.md/共享 host/旧证据未动。
- 45 分钟内完成；停止 review，无自动实现/guest/GPU。
