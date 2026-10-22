# V004 验证报告：A2c（一次 mode / 条件安装 / TF-intent observer）

只读冻结 v004；全部 CPU；未改 repo/candidate/实现方代码；无 commit/push。

## 0. 身份与结论

- manifest `ba064c2d…a90a2e`、vs-v003.diff `4e6dc6cc…c0bb2`（均匹配）
- 变化 3 文件：`nvn_tf_diag.h b27fb321…`、`hle_nvn.c de46fccb…`、`nvn_mtl.m a3e43b03…`；
  `nvn_obj.h`/`nvn_kd_res.h`/`nvn_protos.h`/`AGENTS.md` 同 v003
- 执行：init/安装 8 项 ×7 组 env/variant 全 PASS；observer/formatter 13 PASS / **6 FAIL**（均 D04 契约项）
- mutation 2/2 被抓（均 `compile_rc=0`）

| 契约 | 结果 |
|---|---|
| D01 一次 mode | PASS（并发前提未证，见限制） |
| D02 all-or-none 安装 | PASS（安装）/ **发现 F2**：部分安装时 observer 仍放行 |
| D03 OFF 继承 / ON 记录 | PASS（记录）；PROF/big 路径 **SKIP** |
| D04 observer gate | **FAIL**（非 HIT 结果也输出 tf-intent） |
| D05 formatter | PASS |
| D06 父缺陷 | 限定通过：F1 运行期触发移除；F3 保留；A2b 按 body SHA 继承 |

## 1. 方法（提取，不重写）

| 提取物 | 来源 |
|---|---|
| A2c mode + installer + `nvn_init_slots` | `hle_nvn.c` 58–59、71–134 |
| 录制适配器 | `hle_nvn.c` 824–838 |
| A2a consumer（snapshot/events/copies/depth） | `nvn_mtl.m` 7753–7781 |
| `kd_tf_intent_line` | `nvn_mtl.m` 5554–5569 |
| emit 尾部（`emit:` 标签内联化，其余逐字） | `nvn_mtl.m` 5671–5679 |

验证方自写：槽表/名称表/`getsectiondata`/`LOG`/`die` stub、mock command buffer、日志 sink、
`g_gsres` 结构；所有替换均在此列出。`nvn_kd_res.h` 原样包含（与 v003 SHA 相同）。

## 2. D01 一次 mode（PASS）

独立进程 fixture（`t_init`，每个 env 组合一次运行）：

| env | 结果 |
|---|---|
| 未设置 / `""` / `0` | OFF，0 安装 |
| `1` | **ON，7/7 安装** |
| `01` / `2` | INVALID，0 安装 |

- init 之前 getter 一律 OFF；
- init 后把 env 改成 `1` 再调用 init：mode 不变（fixed）；`static done` 使重复 init 为 no-op；
- 不再有 `dm_tf_diag_set_mode`（源码无该符号）。

限制：`static int done` 与 `g_tf_diag_mode_fixed` 都非原子，**未验证并发**；不写 thread-safe。

## 3. D02 条件 all-or-none（PASS + 发现）

- 7 个名字全部存在且都是 `nvn_unimpl_entry` → 全部安装；
- 缺 1 个名字 → **0 安装**（先整表解析后写入，验证了顺序性质）；
- 某名字已被占用（非 stub）→ **0 安装**；
- 其余 slot 一律不动；`g_nsem` 保持 3（语义实现数不受影响）；
- installer 由真实 `nvn_init_slots` 调用，不是孤立函数。

**F2（medium）**：安装失败时 mode 仍为 ON，而 observer 的唯一门是 `tf_diag_on()`，
没有任何 "installed" 状态可查（源码无该量），因此仍会输出 intent 行。
reproducer：`./build/t_init 1 missing`（mode=1、installed=0）→ `./build/t_obs`（mode ON 时输出 intent）。

## 4. D03 记录与 OFF 继承（PASS；PROF/big SKIP）

- ON：Bind 适配器写恰好 1 条 40B `OP_TF_DIAG`（op/size 正确）；
- OFF/INVALID：适配器 0 字节、0 次分配（保持原 stub 行为）；
- plural：range 指针指向 `PROT_NONE` 页也不解引用，只写 first/count（addr/size=0）。

SKIP：`DM_NVN_PROF` 会在 init 之后用 `nvn_prof_entry` 包住所有已安装 slot（`hle_nvn.c:1174`）；
其转发体属 host/汇编路径，未执行。`nvn_big_entry` 只作用于非 `nvnCommandBuffer*`，TF 名字不在其中，也未执行。
不把 fn 指针被 wrapper 替换后的行为称为"生产路径已验证"。

## 5. D04 observer gate（FAIL）

预期：仅 `result=KDR_HIT` 且 TF ON 时输出 1 条 intent；其余情况不得取 snapshot / 输出。

实际（`t_obs`，TF ON，逐 result 驱动共享出口）：

| result | 期望 | 实际 |
|---|---|---|
| hit | 1 行 | 1 行 ✓ |
| target-not-obtained | 0 | **1 行** ✗ |
| no-geometry-source | 0 | **1 行** ✗ |
| identity-unavailable | 0 | **1 行** ✗ |
| gs-key-mismatch | 0 | **1 行** ✗ |
| invalid-config | 0 | **1 行** ✗ |
| diagnostic-error | 0 | **1 行** ✗ |

机制：emit 尾部只 gate `tf_diag_on()`，从不检查 `r.result`；而 5587–5599 的非 HIT 分支
`goto emit` 到同一出口（注释"不会到达"没有被代码保证）。anchor：`nvn_mtl.m:5674`。
通过的子项：HIT+ON 恰好一条、TF OFF 零条、一条后 close（one-shot）。
GSRES off/closed 的早退在 `kd_res_line` 入口（5572），静态核对成立，但该入口未执行。

## 6. D05 formatter（PASS）

- `final_pass_association=none`、`interpretation=observed-replay-intent`；
- active/pause/reason/seq(UINT64_MAX)/events/copies/depth 正确；`depth=-3`、`reason=none` 不越域；
- `bound0_valid=0` → `bound0=none`，绝不打印成 valid；valid 时 addr/size 正常；
- begin/end/draw 作为独立字段，不暗示当前 binding；
- `_b`/`_bf`/otherPS 的 key 原样打印；
- 短 buffer / NULL → 返回 0（调用方转 diagnostic-error，无半截正常行）。

限制：格式化成功 ≠ 日志落盘保证；MLOG 在 harness 里是 sink，未验证 flush。

## 7. D06 父缺陷与继承

- V001.F1：运行期触发条件已移除（无 setter、mode 一次固定、init 前 OFF）；但**原 leave 逻辑没有被证明通用安全**；
- V001.F3：size ≠ 内存边界保护，继续保留（consumer body 未变）；
- A2b 局部 barrier：与 v003 **body 相同**（见 `evidence/inheritance.json`），继承 V002/V003 已限定的证据；
- 整文件 hash 变化不作为重跑理由；变化的只有 hle init/installer/adapters、header（新增 reason_name）、emit/fmt。

## 8. mutation

| mutant | compile_rc | run_rc | 结果 |
|---|---|---|---|
| m1 emit gate 改为 `if (1)` | 0 | 1 | TF OFF 用例失败（多出 intent 行） |
| m2 删除 `g_tf_diag_mode_fixed = 1` | 0 | 1 | D01 ON 用例失败（getter 仍 OFF） |

## 9. 限制

- 无 host/GPU/Metal/PSO/guest/gate/真实采样；PROF/big 未执行；observer 入口 `kd_res_line` 未执行（仅 emit 尾部）；
- init 并发未证；日志落盘未证；只覆盖本报告列出的执行/继承项；
- route 继续 NO-GO；A2c 是否放行由主管裁决。
