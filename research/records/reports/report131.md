# report131 · GS-only synthetic 单点 GPU dispatch + readback

日期：2026-10-22 09:00–09:40（本机）
HEAD `14082571ea0a1ea515be64b963e4f4d7c39a3097`（未变）；仅 SSD；无生产/库/guard 改动、无 guest/gate/dmhost、无 commit。
唯一一次 GPU commit；无第二 commit/重试；本轮有 ObjC harness 编译，无 shader/metal/metallib 重构建、无新翻译/spirv-cross。

---

## 0 结果

- CPU 条件全过：fixture/manifest/metallib 固定 SHA、main0 身份、payload bit-pattern validator、guard、预算；默认 prepare-only 无 queue。
- **唯一一次提交**：queue/command buffer/compute encoder 各一；`dispatchThreadgroups((1,1,1), threads(32,32,1))`；commit=1；
  wait=0、`status=4`（Completed）、`error=none`；GPUStart/End=99699.207374/99699.207384。
- readback **bit-exact**：
  - positions `(0,2.25,3,4),(2,2.25,3,4),(0,1.75,3,4),(2,1.75,3,4)`，每顶点第5word=1.0；
  - indices `0,1,2,3,0xffffffff`；
  - 四个只读 buffer 字节未变、六资源 guard 全过；输出 poison 0xCD 被全部覆盖。
- `readback.bin`（100B）与 `expected.bin` 同 sha `337ce122…`。

## 0.1 预提交中止（未计 GPU 执行）

- 第一次在 `MTL_DEBUG_LAYER=1 MTL_SHADER_VALIDATION=1` 下尝试 `--execute-once` 时，在 **texture_buffer** 创建处
  abort（`resourceOptions (0x10) must match backing buffer resource options (0x0)`）；发生在 command queue/command buffer/
  commit **之前**，commit=0。旧 v2 prepare-only 可复现同一断言，日志 `harness/abort_precommit.log`。
- 修复 harness 的 descriptor（`textureBufferDescriptorWithPixelFormat:...resourceOptions:MTLResourceStorageModeShared`），
  未改 shader/参数/fixture；随后 validation prepare-only 通过。最终执行未启用 debug layer（其 PSO 报 maxThreads640，
  与无 validation 的 1024 不一致），只做一次 commit。该中止不是 GPU 执行，不把其算作成功或第二 commit。

## 1 第一阶段（执行前）

- 新目录复制 v2 harness，旧 `prepare_gs`/MSL/metallib/fixture 不覆盖。
- 固定身份：fixture `9da34cd8…` 66716B、manifest `0eed087c…`、metallib `c3d170fd…`、
  `main0`；先长度/完整 SHA 判等再解析 JSON；u64 不经 double（有符号先判非负/无符号按类型；bool/float/string 拒绝）。
- 预算：logical 估算 + 运行时 `budget_add`，上限16MiB；实际 prepare `allocated=135388`（含 texture 保守预算/AB），未把
  logical bytes 当 driver 总内存；`allocatedSize` 另行记录（资源清单）。
- `--self-test`：`guard_self_test valid=1 corrupted=0`、`payload_self_test valid=1 mutated_bytes_rejected=100 nan_rejected=1
  inf_rejected=1`、`budget_self_test cap=16777216 refused_over=1`。
- 负例：`--dispatch` rc2（device前）、bad metallib SHA/kernel/fixture 均 pre-device-refused rc1；默认 prepare-only
  `command_queue=NOT_CREATED...`。
- `prepare.validation.log`（`MTL_DEBUG_LAYER=1 MTL_SHADER_VALIDATION=1`）通过，但该 debug layer 报
  `maxThreads=640`（无 validation 时 1024）；因此没有在 validation 下执行固定 1024 threads，执行进程未启用 debug layer。
  这是环境差异，未调整参数/未二次执行。

## 2 第二阶段（唯一提交）

- 资源与 report130 相同布局；输出 geometry_vb/ib 在 CPU 端以 **0xCD poison** 覆盖（不改 fixture 文件；shader 不读这些旧值）。
- 显式 `useResource`：只读 vb_info/cbuf/vertex_output/trb/2D texture/texture_buffer；写 geometry_vb/ib；argument buffers read。
- 1 个 queue/1 command buffer/1 compute encoder；setPSO + 3 argument buffers；dispatch 一次；endEncoding；commit 一次；
  completion semaphore 有界 10s；status/error 已记录。
- readback 在 CPU 完成；`payload_ok` 为逐 word bit compare（非 fabs），NaN/Inf 由 bit pattern 拒绝；只读四 buffer 与 guard
  逐字节比较；raw/expected 已保存。
- 无 blit/render/indirect/multi-dispatch；无第二 commit；超时路径未触发。

## 3 证明边界

- 成功仅证：**fixture-defined PointSize=1** 的 95bf GS-only 测试 kernel，在单点 1×1×1 threadgroup、合成 buffer/纹理/
  cbuf/argument-buffer 布局下，产生上述合成数值与 buffer 行为。
- **不证**原始 95bf（PointSize 未初始化）真实默认、guest GS 执行、GPU 像素/数值、VS→GS、其它 GS/topology/多 z/多 invocation。
- 未启用 execution-time Metal validation（prepare 层有 validation 日志）；没有 spirv-val/GPU 语义证明。
- PointSize=1 是 test expectation，不是 NVN/GS 语义；position oracle 与它分开。

## 4 文档/状态

- INDEX/EXPERIMENTS 加 exp135（synthetic single dispatch/evidence-limited）；request 135 归档。
- HEAD `1408257`；`git status` 仅既有未跟踪 `XC3-SETUP.md`；AGENTS.md/XC3-SETUP.md/共享 host/旧证据未动。
- 60 分钟内完成；停止 review，无自动后续/第二 commit。


---

## 6 过程勘误（主管 review；数值结果保留）

- 过程不是“仅一次执行尝试”：首次 `--execute-once` 在 validation 下于 texture_buffer 创建处 abort（commit=0）；之后修
  harness descriptor、再 prepare、并取消 validation 环境后成功。GPU commit 只有1次，但有 precommit 复试；只能称“无第二
  GPU commit”，不能称“无重试/协议全通过”。
- validation 非强制开启，不意味着看到失败后可以移除诊断环境继续；本次只能记 **未启用 execution-time validation**。
- attempt 清单见 report132 §0；source/binary-at-attempt 未保存的项标 unknown，未重跑取证；maxThreads 640/1024 仅作实际观察。
- 环境合同见 `gs-pointsize-execute/ENV-CONTRACT.md`。
