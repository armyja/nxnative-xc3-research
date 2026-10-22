# V005 复验报告：D02 失败→不发布 ON；D04 显式 HIT guard

只读冻结 v005；CPU；未改 repo/candidate/实现方代码；无 commit/push。

## 0. 身份

- manifest `c320d468…4334f`、vs-v004.diff `0a856174…4671`（匹配）
- 仅 `hle_nvn.c 029efe76…`、`nvn_mtl.m ee708ad5…` 变化；其余 5 文件同 v004

| 契约 | 结果 |
|---|---|
| V5.1 失败与发布 | **PASS** |
| V5.2 D04 truth table | **PASS**（21 组：仅 HIT+ON 输出 1） |
| V5.3 失败安装→observer 同进程 | **PASS** |
| V5.4 继承 | **PASS**（按 body SHA） |
| mutation | **2/2 被抓**，均 compile_rc=0 |

## 1. V5.1 失败与发布（执行）

同一份逐字提取的 `tf_diag_install_adapters`/`tf_diag_activate`/`nvn_init_slots`（hle 71–144），
验证方提供槽表/名表/section stub/LOG。每个 env×表组合跑独立进程：

| 组合 | 结果 |
|---|---|
| 请求 ON + 7 名齐全 | 7/7 安装，**发布后** getter ON |
| 请求 ON + 缺 1 名 | **0 slot 写入**，effective **OFF**，日志 "not enabled, effective mode OFF" |
| 请求 ON + 某名被占用 | 同上 |
| absent / "" / 0 / 01 / 2 | 不安装、无新日志、getter OFF |

- 发布时机：在 installer 的**成功日志处**读取 getter 仍为 OFF（说明 publish 在 install 之后）；
  失败日志处读取 getter 也为 OFF（说明失败未提前发布）。
  该观测点由验证方的 LOG stub 提供，已披露；生产代码未改。
- 发布后改 env 再调用 init：mode 与安装集合都不变（static done + fixed）。
- 失败时 `tf_diag_barrier(OP_TF_DIAG)==0`：consumer/barrier 看不到 ON。

## 2. V5.2 D04 truth table（执行）

7 个 result × {ON, OFF, INVALID}，用真实 `kd_tf_intent_wanted` + 共享 emit 尾部：

- **ON**：仅 `KDR_HIT` 输出 1 条；target-not-obtained / no-geometry-source / identity-unavailable /
  gs-key-mismatch / invalid-config / diagnostic-error 全部 **0 条**（V004 的缺陷已闭合）；
- OFF / INVALID：21 组全 0；
- gs-res 正常行仍输出、`closed` 仍只置一次（原逻辑未受影响）。

边界：HIT+格式化失败的“只 diagnostic-error”路径在 guard 之前，本次按静态核对，未构造 8192 溢出；
`kd_res_line` 入口（GSRES off/closed）仍未执行，按既有边界保留。

## 3. V5.3 失败安装 → observer（同一进程）

同一 fixture 内：请求 ON + 缺名/占用 → effective OFF → 直接走 `KDR_HIT` emit → **0 条 intent**；
随后在同一进程用真实 installer+activate 在全名表上安装 → ON → `KDR_HIT` emit → **恰好 1 条**。
（成功对照直接调用 `tf_diag_activate`，因为 `nvn_init_slots` 有 static done；仅此一处披露，不改生产算法。）

## 4. V5.4 继承（body SHA）

| body | v004→v005 | 处置 |
|---|---|---|
| `tf_diag_barrier`、`ds_scan`、`hoist_try`、`fz_next`、`defer_try`、`sdx_decide`、`frz_op`、`fz_prefilter`、`tf_diag_enter`、`tf_diag_case`、`kd_tf_intent_line`、hle `tf_diag_emit` | 相同 | 继承 V004/V003/V002-S 限定证据 |
| hle `nvn_init_slots`、`tf_diag_install_adapters`、`tf_diag_activate` | 变化 | 本报告 V5.1/V5.3 重测 |

D01（一次 fixed）：initializer 变了，代表 case 已重测（init 前 OFF、ON 后固定、改 env 无效、INVALID 也不启用）。

## 5. 观察项

**V005.F1（info）**：INVALID 现在被 activate 折叠为 effective OFF（getter 返回 OFF 而非 INVALID）。
所有消费者只区分 ON/非 ON，本轮未观测到行为差异；仅提示 INVALID 枚举值不再可从 getter 观察。
anchor：`hle_nvn.c tf_diag_activate`。

## 6. mutation

| mutant | compile_rc | run_rc | 结果 |
|---|---|---|---|
| m1 去掉 HIT guard（`r && tf_diag_on()`） | 0 | 1 | V5.2 ON 表失败（非 HIT 又输出） |
| m2 失败仍发布 ON | 0 | 1 | V5.1 失败用例（mode=1、barrier 误判） |

## 7. 限制

- init 并发仍未证（static done 非原子），不写 thread-safe；PROF/big 转发体、完整 `kd_res_line` 入口、
  日志落盘、GPU/Metal/guest/gate 均未覆盖；V001.F3（size≠内存边界）保留；
- 本报告只说明抽离路径成立，不称真实运行；route 继续 NO-GO。
