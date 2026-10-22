# TF-DIAG A1 + A2a 独立验证报告（V001）

验证方会话：DSH 验证会话（独立于实现方）；仅验证，未修改 repo / 候选 / 实现方产物。
时间：2026-10-22（本机 UTC+8）；本轮在 75 分钟预算内完成 CPU 可覆盖项后冻结。

## 0. 结论摘要

| 项 | 结果 |
|---|---|
| 候选身份（manifest + 7 文件 SHA256） | **匹配**，`2ba2f76a…c995`，7/7 |
| repo 工作树现状 | 验证期间（10:49）**已漂移** 2 文件（`nvn_tf_diag.h`、`nvn_mtl.m`）；身份只认 snapshot |
| C01–C07 CPU 契约 | **54/54 断言 PASS**（普通 + ASan/UBSan 各一遍） |
| 静态契约（编号/签名/注册/生产者/stub/接线缺失） | **19/19 PASS** |
| 独立变异（6 个，先编译后运行） | **6/6 被抓**，全部 `compile_rc=0` |
| C08 未接线项目 | **SKIP**：无法在此环境证明；**route 仍 NO-GO** |
| 发现 | 1 项 medium（未来开启风险）+ 3 项 info/limitation；无本轮限定合同的 FAIL |

A2a 的限定目标（真实 replay 上下文中的消费端点 + 保守 shadow 模型 + 默认关闭）
在 CPU 层面成立；这**不等于** TF feature 完成，也不构成 route 放行依据。

## 1. 候选身份（只读快照）

- snapshot：`/path/to/external-drive/xc3/work/experiments/tf-diag-verification/v001/candidate/`
- manifest：`…/v001/candidate.json`，SHA256 `2ba2f76a15ff5e565e33caef2474e342a9f079abcb06a5259ebf13fbfa83c995`
- repo：`/path/to/user/projects/nxnative-xc3`，branch `xc3`，HEAD `1408257…3097`（**HEAD 不是候选身份**）

| 文件 | SHA256（manifest，7/7 与 snapshot 一致） |
|---|---|
| dm/gfx/nvn/nvn_tf_diag.h | 016cced44cf564d07331c7d4d8f0b9454d4fd44ecf8794f5bc9363a12e8212ee |
| dm/gfx/nvn/nvn_obj.h | 8e9f93e2742d0e634c2451c1f6c8583bc262c253c56679c3b87cb1c8efb3221f |
| dm/gfx/nvn/hle_nvn.c | 36863fc4cc56cba3fe969766c094a204e5640abe7d81b7b77ffba09a5b29258b |
| dm/gfx/nvn/nvn_mtl.m | bc0a209565b17823884df3501f659e91ddd99f5a3dab7b78541f3997e0749d25 |
| dm/gfx/nvn/nvn_kd_res.h | 9956f931b3a25eb10c82a08fb926a0b5dd27789b315b55860e33ba26aaab4642 |
| dm/gfx/nvn/nvn_protos.h | a3750327d0ccbc535d3b4d30c326a84bdc972be33bca43cdf3b78a0b6737968d |
| AGENTS.md | d356064effe993211e6993559fcfbe94c2aff5d7c759ee17b5d8d94d3b3b0e56 |

**repo 漂移（验证期间发生，非本会话写入）**：`nvn_tf_diag.h` 11621→11996B（`578957c7…f77`，mtime 10:49:33）、
`nvn_mtl.m` 826280→828748B（`64ba5054…701`）。证据：`evidence/identity.json`。
=> 后续 review / 复验必须重新取快照并复算 manifest；不得用 repo 现状代表本候选。

## 2. 方法（独立 oracle，未复制实现方断言）

从 snapshot **逐字提取**并记录行号/SHA（`evidence/provenance.json`）：

| 提取物 | 来源 | 行 |
|---|---|---|
| 模型头 `nvn_tf_diag.h` | 原文件逐字 | 1–end |
| opcode 编号 + `op_hdr` | `nvn_obj.h` | 95–104 |
| 录制适配器（mode/emit/8 个） | `hle_nvn.c` | 779–796 |
| A2a 消费块 | `nvn_mtl.m`（A2A 标记内） | 7695–7728 |

- 期望值全部来自合同文本与独立推演，未从实现方 test/报告复制 `expected`。
- replay 执行器是 `mtl_exec` 的**独立子集**（仅 OP_END/OP_JUMP/OP_BEGIN/OP_CALL/OP_DRAW/OP_DRAW_IDX/OP_TF_DIAG/default，删去全部渲染/GPU 工作）。**不是完整 mtl_exec**，不能据此声称真实 replay 行为。
- 允许范围内执行：仅 `cc` 本机编译 + 运行 + ASan/UBSan。未 hostbuild/链接运行、未触 shader/translator/Metal/PSO/GPU/guest/gate、未做资源采样、未联网。
- 命令：`./build.sh`（生成 include + 编译 plain/ASan）→ `./build/tfv_tests`；`python3 src/static_checks.py`；`python3 src/mutate.py`；`./build/probes <name>`。

## 3. 逐契约结果

| ID | 结果 | 要点与证据 |
|---|---|---|
| C01 格式 | **PASS** | `sizeof(p_tf_diag)=32`、`_Alignof=8`、offset 0/4/8/12/16/24、`sizeof(op_hdr)=8`、8+32→40、`OP_TF_DIAG=42`、`OP_COUNT_=43`（编译期断言）；候选 enum = 基线 enum + 新增 1 项，`OP_COUNT_` 42→43；7 个适配器参数类型与 `nvn_protos.h` typedef 逐一对齐；`nvn_init_slots()` 无 TF 项、无 `nvn_impl e_*` 段注册；无任何生产者调用适配器；7 个 NVN TF 入口仍走 `nvn_unimpl_entry`（与基线一致）。证据 `logs/tfv_tests` C01 行 + `evidence/static_checks.json`。 |
| C02 off/invalid | **PASS** | off/`invalid(2)`：8 个适配器均不 alloc、不写命令字节；同一旧命令序列（含适配器插入）与基线录制 **bytes 完全相同**；`rec()` 实现体 SHA 与 pre-A1 基线**逐字相同**；consumer `enter/case/leave` 不改 state/depth/counters，payload 放在 `PROT_NONE` 页也不被读。 |
| C03 on 消费 | **PASS**（含限制 F3） | 仅 `hsize==40` 且 `a&7==0` 才 `memcpy` 32B 并 apply 一次；32/48/39 与错位均 `BAD_RECORD`，不读 payload、不 apply（`last_index` 保持哨兵）、`copies` 不增；flags≠0 / kind>7 / index / count / size0 / addr+size 溢出全部 fail-closed；诊断计数器饱和不回绕。**注意**：`hsize` 是流内自述字段，不是内存边界校验（见 F3）。 |
| C04 保守模型 | **PASS** | 初始 unknown；Bind 只改 range、绝不造 active；Begin→active/running（observed intent）；完整 Begin→End→inactive 且 gate 允许；重复 Begin（running/paused 两种）、unmatched End、End-while-inactive、Pause/Resume 失配、plural/opaque Draw/Invalid、index≠0、坏 payload、溢出 → 全部 unknown 且 gate 拒绝；重复/异常序列不能产出可放行 inactive。 |
| C05 饱和 | **PASS** | seq 从 `MAX-1` → `MAX` 不饱和，下一次 tick 饱和并 sticky unknown、gate 拒绝；之后 End/Bind/Begin 均不能恢复（仍 unknown、bound 失效、seq 停在 MAX）；events/copies 在 MAX 不再增加。 |
| C06 replay 关联 | **PASS**（子集执行器） | 顶层 enter 重置 unknown，两次提交不残留 known（第二次 NO_EVENT/events=0）；nested CALL 继承父状态；同一子列表 `[End]` 从 active/unknown/inactive 三种入口得到 inactive / END_WITHOUT_BEGIN / END_WHILE_INACTIVE 三种不同 exit；`OP_BEGIN` 不误 reset；`OP_JUMP` 跳过的 TF 记录不被消费；depth 回到 0。 |
| C07 路由 | **PASS**（CPU/源码层） | 源码中 `case OP_TF_DIAG` 恰好 1 处、单次调用并 break，无 label 串联；子集执行器里 g_rc_skip=1 时 DRAW/DRAW_IDX 不绘制而 TF 事件仍按序生效；每条记录恰好消费一次（events=copies=记录数）；未知 opcode 不干扰。**生产 snapshot hook 不存在**，未测不存在的功能。 |
| C08 未接线 | **SKIP** | 见 §5。 |

运行证据：`evidence/run_plain.log`（`RESULT pass=54 fail=0`）、`evidence/run_asan.log`（ASan+UBSan 同一结果）。

## 4. 反例 / 发现（只报证据，未修）

**F1（medium，未来开启风险）mode 中途切换导致 depth 泄漏、跨提交残留 known 状态**
- 触发：`tf_diag_leave()` 被 `tf_diag_on()` 守卫（`nvn_mtl.m:7711`）；若某次 enter 后 mode 变 OFF，leave 变空操作，`g_tf_diag_depth` 停留 1；下次 ON 时 enter 见 depth≥1 **不重新初始化**，上一提交的 `inactive` 残留，gate 可能放行陈旧状态。
- 复现：`./build/probes depth-leak` → 期望 depth=0 / 重新初始化；实际 `depth=1`、第二提交前后均 `inactive`。证据 `evidence/probe_depth_leak.log`。
- 今天是否可达：**不可达**——A1 启动后 `dm_tf_diag_set_mode` 仅定义未被调用（静态检查已证），mode 固定 OFF。A2b 若接运行期开关即为真实缺陷。

**F2（info）`TF_DIAG_REASON_BAD_KIND` 不可达**
- `tf_diag_payload_ok()` 先把 `kind>7` 判成非法 → `BAD_PAYLOAD`，switch 的 `default: BAD_KIND` 永远走不到。fail-closed 语义不受影响，但枚举值是死代码。
- 复现：`./build/probes bad-kind` → 期望 BAD_KIND，实际 `reason=12 (BAD_PAYLOAD)`，`evidence/probe_bad_kind.log`。
- anchor：`nvn_tf_diag.h` `tf_diag_payload_ok`/`tf_diag_apply` default 分支。

**F3（info / 明确限制）size 检查 ≠ 流/内存边界保护**
- 消费端信任记录头自述的 `size`；头部声称 40 而实际 payload 只有 16B 时，32B 拷贝会越界。ASan 复现：`heap-buffer-overflow READ of size 32`，栈帧 `tf_diag_case`。证据 `evidence/probe_oob.log`。
- 结论：合同 C03 的“不能因检查 size 就宣称完整 stream 安全”成立，报告与 review 不得把它当作边界校验。

**F4（info）sticky 守卫重复**
- `tf_diag_apply` 顶部与 `tf_diag_tick` 末尾都做 sticky unknown；只删前者时 6 个用例仍全绿（等价变异，未计入 6/6）。属纵深防御冗余，不是缺陷，但说明该守卫单点删除不可被现有用例区分。

## 5. 未覆盖 / 模型 vs 生产限制（route 仍 NO-GO）

- 全部结论仅 CPU、仅模型/消费端点：**无 GPU、无 Metal、无 PSO、无 device、无真实 replay 提交、无真实 TF 输出**。
- 无真实 producer：适配器未注册、无调用点；`dm_tf_diag_snapshot/events/copies` 只被定义、无生产 hook（静态检查已证）。
- 15 处 scanner/hoist/defer/frzbarrier 等改动点：本会话只对 `sdx_seq` / `hoist_take` / `defer_begin_q` / `frz_op` 代表点做了“无 TF 引用”检查，**未逐处审计 15 处**（时间/范围所限，列为 gap）。
- slot 安装、mode 启动固定、observer/真实 TF 输出均未接线 → 无法支持“on 真实 host”；**route 判定保持 NO-GO**。
- 不证明任何 NVN 语义、GPU 写入或 stream-out 内容；“Begin implies running” 仅为命名假设。
- 执行器是 mtl_exec 子集，未覆盖 `g_tf_diag` 与真实渲染状态机的交互（如崩溃/longjmp 导致 depth 抬高，源码已注明为已知 gap）。

## 6. 交回与冻结

- 结构化结果：`validator/result.json`；证据目录：`validator/evidence/`（含 SHA 清单 `evidence/sha256sums.txt`）。
- 本会话只新增 `validator/` 下内容；repo、candidate、`candidate.json`、实现方 harness/报告均未修改；无 commit / push / 合码。
- 状态：**冻结等待 review**，不领实现任务，不自行联系实现方。
