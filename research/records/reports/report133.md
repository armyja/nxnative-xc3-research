# report133 · VS→GS synthetic fixture + prepare-only 双 kernel

日期：2026-10-22 10:10–10:40（本机）
HEAD `14082571ea0a1ea515be64b963e4f4d7c39a3097`（未变）；仅 SSD；无 dispatch/queue/command buffer/encoder/GPU/guest、无生产/库/guard 改动、无 commit。
本轮有 ObjC harness 编译；无 shader/metallib 重构建、无新翻译/spirv-cross。

---

## 0 结果

- 新 fixture（新 hash）把 `vertex_output` 改为 **VS 实际计算可产生**的输入契约；VS/GS 原 metallib 固定：
  VS `a286322f…`（report127）、GS `c3d170fd…`（report129 PointSize=1 变体）；不修改 shader。
- CPU self-test/validate 通过；一个合法 **prepare-only**（`MTL_DEBUG_LAYER=1 MTL_SHADER_VALIDATION=1`）完成：
  VS/GS PSO 创建、6 个 argument buffer、8 个资源、guard/预算均过；**无 queue/command buffer/encoder/dispatch**。
- 但该 validation 环境下两个 PSO 的 `maxTotalThreadsPerThreadgroup=640`；固定 1024-thread pre-submit contract 不满足，
  harness 返回 rc4，报 **不具执行条件**。按合同未移除 validation、未重跑、未执行任何 GPU commit。
- 因此本轮没有 VS→GS 数值/执行证据；`vertex_output` 仍为 poison，VS 未运行。

## 1 Fixture/资源

- `fixture.bin` 66736 B sha `7a1ab70c…`；manifest sha `9c601614…`。
- sections：
  - vb_info 0/1056：m0=(1,1,0,0)、m1=(1,0,0,0)、m2[0]=(4,1,1,1)、m3[0]=0；
  - cbuf 1056/65536：cbuf3[0]=(2.0,0.5)；
  - vertex_output 66592/20：poison（VS 输出目标，不预填 expected）；
  - geometry_vb 66612/80、geometry_ib 66692/20：poison；
  - trb 66712/4：float0→uint0；
  - ib_data 66716/4：float0→index0；
  - vb_data0 66720/16：float (1,2,3,4)。
- m2=(4,1,1,1) 明确 stride=4、y/z/w component enable=1；因此 VS 期望输出 `(1,2,3,4,1)`，不是用默认 w=1。
- 旧 report129 fixture/manifest/readback 未改；新 output 路径在 `gs-vsgs-prepare/out`（本轮未写 GPU readback）。

## 2 CPU oracle / MSL 映射

独立代数（`harness/oracle.log`）：
[Fenced excerpt omitted from the shareable research record.]
- 来自 MSL 的明确映射：VS `vertex_output` offset0..4 = Position.x/y/z/w + PointSize；GS 读同一 buffer offset0..3 作为
  Position，**不读 word4**；GS 的 PointSize 来自其 own output `_43[4]`（fixture-defined 1.0），不是从 VS word4 传递。
- 5-word stride 相同不等于内容/语义全同；GS output word4 与 VS input word4 是不同语义，不能写成“串联已证明”。

## 3 prepare-only 观察

`harness/prepare.log`（sha `5fa8b712…`，env `ENV-CONTRACT.md`）：

- AB：VS set0/1/2 = 8/8/16 B；GS set0/1/2 = 32/24/8 B；分别由各自 `main0` encoder 创建。
- 资源：vb_info 1568、cbuf 66048、vertex_output 532、geometry_vb 592、geometry_ib 532、trb 516、
  ib_data 516、vb_data0 528 B（含 256B guards）；`guard=1`；`allocated=136464 <16MiB`。
- `prepare-only: VS maxThreads=640 contract=PSO max threads 640 < 1024 GS maxThreads=640 contract=...`；
  `command_queue=NOT_CREATED command_buffer=NOT_CREATED encoder=NOT_CREATED dispatch=NOT_CREATED`。
- 未移除 validation，未改用无 validation 的 prepare；未创建 queue；无任何 GPU commit。

## 4 负例/身份

- `--execute`/`--execute-once` pre-device 拒绝 rc2；
- 缺 VS metallib rc1、fixture 长度/SHA 错 rc1；均 `pre-device-refused`；
- 新 harness 固定 VS/GS lib SHA + main0，不接受任意 library/kernel；
- 旧 readback 路径未被引用/覆盖；新 output 目录固定。

## 5 未来同步设计（未执行）

- 候选 A：同一 command buffer 顺序两个 compute encoder（各自 endEncoding），依赖 Metal 的 encoder 边界执行顺序；
  候选 B：同一 compute encoder 中显式 `memoryBarrierWithScope:MTLBarrierScopeBuffers`（或等价 API），保证 VS 写后 GS 读。
- VS 写 `vertex_output`、GS 读；两 stage 各自 argument buffers，set0/1/2 id 独立；共享 `vertex_output` 是唯一跨 stage buffer；
  `useResource` 需声明 VS 写/GS 读及 argument buffer 间接资源；CB/texture 不别名。
- 这些是计划，不是已测；本轮无 encoder/commit。需要后续单独授权与 session/validation 合同。

## 6 边界

- 本轮只证 fixture 新契约、CPU oracle、prepare 资源/AB/guard/预算与 **不具执行条件**（validation 下 max640）；
  不证 VS→GS 执行/数值/GPU/像素；不关闭 validation 规避 1024 cap，不重跑。
- 原始 95bf GS 的 PointSize 未初始化问题仍存在；fixture-defined GS PointSize=1 只是测试变体，不推广。

## 7 文档/状态

- INDEX/EXPERIMENTS 加 exp137（VS→GS prepare-only/evidence-only）；request 137 归档。
- HEAD `1408257`；`git status` 仅既有未跟踪 `XC3-SETUP.md`；AGENTS.md/XC3-SETUP.md/共享 host/旧证据未动。
- 45 分钟内完成；停止 review，无自动恢复 GPU/guest。
