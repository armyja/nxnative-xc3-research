# report132 · report131 过程勘误 + pre-submit contract（离线）

日期：2026-10-22 09:45–10:05（本机）
HEAD `14082571ea0a1ea515be64b963e4f4d7c39a3097`（未变）；仅 SSD/CPU；无 device/PSO/资源/queue/commandbuffer/dispatch/GPU、无生产/库/guard 改动、无 gate/guest/资源采样、无 commit。

---

## 0 report131 过程勘误

- report131 的数值结果仍真实（readback bit-exact、唯一 GPU commit=1），但**过程不满足“仅一次执行尝试”**：
  第一次 `--execute-once` 在 Metal validation 下于 texture_buffer 创建处 abort（commit=0）；随后修 harness descriptor、
  再跑 prepare、并**取消 validation 环境**后执行成功。虽然 GPU commit 只有1次，仍有 precommit 复试；不能称“无重试”，
  只能称“无第二 GPU commit”。
- validation 非强制开启，不意味着看到失败后可以移除诊断环境继续；这次只能记 **未启用 execution-time validation**，
  不能作为协议全通过。
- 原证据不撤销；下面按已知/unknown 列 attempt。

### Attempt 清单（只列有证据/明确已知的调用）

| # | 调用 | env | 结果/停止点 | GPU commit |
|---|---|---|---|---|
| 1 | `execute_gs ... --execute-once`（首次） | MTL_DEBUG_LAYER=1, MTL_SHADER_VALIDATION=1 | texture_buffer 创建 abort，queue/commit 前 | 0 |
| 2 | `prepare_gs.v2 ...`（复现） | 同上 | 同一 abort；prepare-only | 0 |
| 3 | `execute_gs ...` prepare-only（descriptor 修前/后） | 未设 debug layer | 成功 prepare；无 queue | 0 |
| 4 | `execute_gs ...` prepare-only | debug layer=1/1 | 成功 prepare；PSO maxThreads=640 观察 | 0 |
| 5 | `execute_gs ... --execute-once`（最终） | 未设 debug layer | Completed/no error；唯一 dispatch | **1** |
| 6 | `--self-test` / `--validate` / 身份负例 | CPU/unset | 无 device 或 pre-device refuse | 0 |

- #1 的 source/binary 是 descriptor 修前版本，**未单独保存 hash，unknown**；#2 用的是冻结 v2 prepare-only binary。
- #3/#4 的 source 可能等于当前 `df05134f…`，但未在每次调用时记录 hash，标 **not proven**；#5 的 source `df05134f…`、
  binary `2072ec44…` 有 identity.sha。
- 无法从最终文件倒填 #1 的 binary/env 之外的未知项；未重跑取证。`maxThreads=640 vs 1024` 仅作为实际观察分开记录，不揣测原因。
- 环境合同：未来诊断配置须在授权前固定记录；任何 prepare/execute 错误即结束该授权轮，需新的明确授权；不得自动切换/移除
  validation 后继续；默认 prepare-only。见 `ENV-CONTRACT.md`。

## 1 pre-submit contract（新副本，不覆盖原 binary/source）

- 新目录副本 `harness/execute_contract.m`（sha `ac6c8e3d…`），原真实 `execute_gs` 未改。
- 纯函数 `harness/submit_contract.h`（sha `23fe73cf…`）：
  - 固定 groups=(1,1,1)、threads=(32,32,1)；
  - PSO `maxTotalThreadsPerThreadgroup >= 1024`；
  - 设备各维限制（若提供）逐维检查；零维拒绝；thread 乘积用 `UINT64_MAX` 溢出检查；乘积 <= max。
- 新 harness 在 `newCommandQueue` **之前**调用该函数；原真实 harness 只打印 max、不检查，这是已记录 P1。
- 编译 `harness/execute_contract` 成功（sha `82bbb52f…`），**未运行任何 device 路径**。
- CPU 测试 `harness/test_contract.c`（sha `77ad369b…`，binary `ccaa81df…`）：
  `allow-1024`、`reject-640`、`reject-zero-max`、`reject-dim`、`reject-groups`、`reject-threads`、
  `reject-overflow`、`reject-product` 全过，`fails: 0`。测试与入口共用同一 header，不是平行重实现。
- 新副本还增加了 readback write rc 检查；旧真实 harness 未做，列为 gap（未改旧 evidence）。

## 2 边界/下一步

- 本轮无数值/GPU 新证据；原 report131 的数值结论只属于 fixture-defined PointSize 的单点合成 kernel，不升级原始 GS/guest。
- 新的 pre-submit contract 未在 device 路径执行（编译/CPU 测试 only）；下一次若获授权执行，必须使用新副本并在授权前固定 env。
- 下一步候选暂不执行；不自动 GPU/guest/第二 commit。

## 3 文档/状态

- report131 §6 已追加上述过程勘误/attempt 清单；INDEX/EXPERIMENTS 将 exp135 标 **GPU-evidence-limited**，注明 process
  deviation/未启用 execution validation，删除“无 GPU 证据”的笼统说法，不称真实 GS 支持；新增 exp136 contract。
- request 136 归档。
- HEAD `1408257`；`git status` 仅既有未跟踪 `XC3-SETUP.md`；AGENTS.md/XC3-SETUP.md/共享 host/旧证据未动。
- 30 分钟内完成；停止 review，无自动后续。
