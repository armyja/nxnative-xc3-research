# report130 · prepare-only harness v2：sampler/契约/预算/guard 修复

日期：2026-10-22 08:00–08:35（本机）
HEAD `14082571ea0a1ea515be64b963e4f4d7c39a3097`（未变）；仅 SSD；无 dispatch/queue/command buffer/encoder/GPU；无生产/库/guard 改动、无 gate/guest/资源采样、无 commit。
注：本轮有 metal/metallib 与 ObjC harness 重编译；report129 的“无 build”仅指无生产/host/shader 翻译 build。

---

## 0 结果

- 旧 prepare 证据保留（`prepare.v1.log`/`prepare_gs.v1.m`），不声称旧版已满足。
- v2 harness：device/allocation **之前**完成固定六 section 契约、SHA、范围、重叠、必要值、预算校验；失败打印
  `pre-device-refused` 且 rc 非0，直接调用 exe 不能绕过 shell wrapper。
- 合法 fixture 通过后只运行一次 prepare-only：PSO ok；`sampler.supportArgumentBuffers=1`；三个 argument buffer
  encoded_length 32/24/8；六个资源完整 guard 校验全过；累计分配 **69852 B < 16 MiB**；无 queue/command buffer/
  encoder/dispatch。

## 1 P1 修复

1. **sampler**：`sd.supportArgumentBuffers=YES`，并在日志记录实际值；旧 prepare 未设置，不能作为兼容性证据。
2. **契约校验前置**：
   - 固定六 section：`vb_info 0/1056, cbuf 1056/65536, vertex_output 66592/20, geometry_vb 66612/80, geometry_ib 66692/20, trb 66712/4`；
   - 每个 offset/length 必须是 NSNumber 整数（拒 bool/float/string/负/超大），精确匹配；
   - 非重叠、在 fixture 66716 B 内；用 `len<=size`、`off<=size-len` 减法检查，避免加法溢出；
   - fixture SHA `9da34cd8…`、manifest SHA `0eed087c…` 固定期望（不现算 expected）；必要 counts/cbuf/vertex_output/trb/
     geometry zero/expected positions/index/pointsize 与已审 fixture 一致。
   - `--validate` 与正常 prepare 都先走同一校验；错误在 `MTLCreateSystemDefaultDevice` 前。
3. **预算**：固定估算 + 运行时 `budget_add`；每个 buffer/argument buffer/encoder 长度在分配前累加检查，硬上限
   16 MiB；合法 prepare 实际 69852 B。
4. **guard**：256 B 两侧逐字节检查（非首尾采样）；正常 prepare 六资源 `guard_full=1`；`--self-test` 注入中间 guard
   字节使校验失败，纯 CPU、无 GPU。
5. **负例**：缺 offset/length、负/string/float/bool/超大、越界/溢出/重叠/错长度、expected 改值、manifest SHA、
   fixture SHA、`--dispatch` 均 device 前拒绝 rc 非0；`--self-test` 覆盖预算超限。合法 fixture 仅一次 prepare。

## 2 证据

- v2 source `f123fdc7…`，binary `c2c35135…`；build.v2.log；fixture/manifest 未改（`9da34cd8…`/`0eed087c…`）。
- `harness/prepare.v2.log`（sha `4e378b84…`）：
  - `prepare-only: kernel=main0 pso=ok TEW=32 maxThreads=1024 sampler.supportArgumentBuffers=1`
  - argument buffers 32/24/8；六资源 `guard_full=1`；`allocated=69852 budget=16777216`
  - `command_queue=NOT_CREATED command_buffer=NOT_CREATED encoder=NOT_CREATED dispatch=NOT_CREATED`
- `self_test.log`：`guard_self_test valid=1 corrupted=0`、`budget_self_test cap=16777216 refused_over=1`。
- `negative.v2.log`：fixture SHA/bad library/bad kernel rc1；`valid fixture --validate` rc0。
- 静态 grep queue/commandBuffer/computeEncoder/dispatch **0 命中**；`--dispatch` rc2 在 device 前拒绝。
- **未构造受控 PSO-failing metallib**；v2 代码 `!pso` 时 refuse/rc非0，但该路径未执行验证，不称已证。

## 3 边界

- 仍是 **GS-only prepare-only**：不证明 VS→GS、GPU 执行、dispatch/indirect/sync、像素/数值。
- PointSize=1.0 是 fixture synthetic；position oracle 是 fixture 代数（texture0.5/cbuf2,0.5/vertex1,2,3,4），不是 GPU 结果。
- argument buffer id 按 MSL 实际 id，不抄 SPV binding；host 绑定/重绑/长度仍只在本 harness 的 prepare 层。
- 未改 MSL/SPV/metallib/fixture；未创建 command queue/encoder/dispatch。

## 4 文档/状态

- report129 §7 追加 sampler/契约/guard/“无 build”澄清；INDEX/EXPERIMENTS 加 exp134（prepare v2/evidence-only）；
  request 134 归档。
- HEAD `1408257`；`git status` 仅既有未跟踪 `XC3-SETUP.md`；AGENTS.md/XC3-SETUP.md/共享 host/旧证据未动。
- 45 分钟内完成；停止 review，无自动 dispatch/后续。
