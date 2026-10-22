# V002-S 补测报告（S01–S03）

只读冻结 v002 candidate；产物全在 `v002/validator/supplement/`；父级 result/report 未改。60 分钟 CPU 预算。

## 0. 结论

| 项 | 结果 |
|---|---|
| S01 sdx 索引失效 → decide → fallback | **PASS（已执行）**：真实 `sdx_decide()` + `sd_need`；`sdx_bucket` 为单桶 stub |
| S02 defer 候选路径 | **PASS（片段已执行）/ SKIP（主扫描与 Q 主体）**：empty-pass 内扫描逐字提取并执行 |
| S03 FALSE≠流末 / merge 路径 | **PASS**：9 个 caller 全部归类 + 反事实可执行对照 |
| mutation | **2/2 被抓**，均 `compile_rc=0`、`run_rc=1` |
| 身份 | manifest `4cf79789…b5f2`、`nvn_mtl.m 64ba5054…`、`nvn_tf_diag.h 578957c7…`（冻结核对） |

## 1. S01 真实 fallback 链（不是字符串推断）

执行的代码：`sdx_decide()`（4590–4607 逐字）+ `sd_finish()` 的决策部分（4 行转写，去掉 Metal 调用）+
`sd_need()`（4161 逐字）。`sdx_bucket()` 用单桶 stub（真实实现是 2048 项哈希），索引内容由测试构造。

| 用例 | expected | actual |
|---|---|---|
| 有效索引 + CLEAR@P | 可 discard（state=2） | discard |
| TF 使索引失效（`g_sdx_ok=0`，即 `sdx_walk` 的行为） | 全量 store，why=6 | why=6、dead=0 |
| 有效索引 + READ | store why=1 | why=1 |
| 事件命中 hoist-skipped op | 无法作为 discard 证据（why=5） | why=5 |
| 本可 discard 的账本 + TF 失效 | 保守 keep | keep |

第一行是**区分力证明**：同一 harness 确实能走到 discard 候选，后面的 keep 才有意义。

## 2. S02 defer 的空 pass 证明（片段）

逐字提取 5061–5067 的循环（`e/ec/empty` 初始化按生产代码搬入；`break` 改为 `return empty`，已披露）。

| 用例 | expected | actual |
|---|---|---|
| 下一条是 SET_RT | empty=1（不当作 Q） | 1 |
| 有 draw | empty=0 | 0 |
| ON + 范围内有 TF | 证明中断 → empty=0 | 0 |
| OFF 对照（同流） | TF 被跳过 → empty=1 | 1 |
| OP_END 无续接 | empty=0 | 0 |
| JUMP 到 SET_RT | empty=1 | 1 |

caller 后果（源码锚点，未执行）：empty=0 → 该 SET_RT 成为 Q 候选（`q = r; qop = p; goto q_found`）；
Q 复查在 5080 有自己的 boundary，遇到同一 TF → `reason=17` → `goto fail`，defer 失败。empty=1 → 继续扫描、不取 Q。
**未执行**：defer 主扫描循环、Q 复查主体、`defer_q_superset`/`defer_prog_hits`/快照机制。

## 3. S03 去掉粗 prefilter latch 后的成功路径

静态（`src/callers.py`）：9 个 `fz_next` 站点全部归类，0 个 UNKNOWN——5 个 `return`（中止 caller）、
2 个 `break`（停止收集）、2 个循环条件（提前结束收集）。merge 激活 `g_fz.active = 1`（5234）位于
`planned:`（5205）与最后一次计划用 `fz_next`（5209）之后；`fz_prefilter` 在 latch 置位时返回 0（无候选，5112）。

可执行反事实（使用真实 `fz_next`）：

| 用例 | expected | actual |
|---|---|---|
| 生产形状 vs “FALSE 当流末即接受”，流 `[draw, TF, SET_RT]` | 生产拒绝、反事实会接受 | prod=0、buggy=1 |
| 无 TF 对照 | 两者都到达后续 pass | 1 / 1 |
| 普通流末（OP_END 无续接） | 也是 FALSE → 拒绝 | 0 |
| precompile 收集遇边界 | 只 1 个 draw | 1 |

结论：FALSE 在两种语义下都不是“成功证据”；去掉 latch 后，成功仍必须穿过 `fz_next` 的局部 boundary
或（S02 情形）Q 复查的 boundary。**发现遗漏只报**：未发现“FALSE 被当成功”的 caller；但
`pso_predict_rest`/ixc/wide 的 `break` 只是停止收集，属提前放弃预取，不构成正确性风险，也没有成功语义。

## 4. mutation

| mutant | compile_rc | run_rc | 结果 |
|---|---|---|---|
| m1 删除 `sdx_decide` 的索引有效性守卫 | 0 | 1 | S01 2 项失败（TF 失效后仍 discard） |
| m2 删除 `fz_next` 的 boundary | 0 | 1 | S03 2 项失败（生产形状跨 TF） |

## 5. 限制与继承

- 无 GPU/Metal/PSO/device/hostbuild/guest/gate/资源采样；不宣称 renderer/GPU 语义。
- S01 的索引构造、S02 的 defer 主体、S03 的完整计划均未执行，已在 result.json 明确列出。
- 继承规则：v003 仅在对应函数 SHA 不变时继承本补测——
  `nvn_mtl.m` 4590–4607（sdx_decide）、5061–5067（defer empty scan）、4059–4081（fz_next）、35–44（barrier/seen）。
  任何一段被改，对应 S 项作废重测。

## 6. 产物

`result.json`、`report.md`、`src/{gen3,callers,mutate}.py`、`tests/{s01_sdx,s02_defer_empty,s03_callers}.c`、
`build/include/provenance.json`、`evidence/*`（运行日志、callers.json、mutants.json、sha256sums.txt）。
