# V003 复验报告：F1/F2 修复候选

只读冻结 v003；全部 CPU；未改 repo/candidate/实现方代码；无 commit/push。

## 0. 身份

- manifest `ee0d6137…7dd2`（匹配）、vs-v002.diff `6feecfd2…a28b`（匹配）
- 仅 `nvn_mtl.m` 变化：`2ba9af1a…78fd`；其余 6 项 SHA 与 v002 相同
- 提取件行号/SHA：`evidence/provenance.json`

## 1. V3.1 原 F1 反例（执行，PASS）

同一份逐字提取的 `ds_scan`（v003 4129–4151），同一条流 `[TF, SET_RT, END]`，三模式对照：

| mode | ds_scan | g_ds_why |
|---|---|---|
| ON | `DS_USED`（keep） | 42 (OP_TF_DIAG) |
| OFF | **`DS_FREE`**（恢复 pre-A2b） | 0（无副作用） |
| INVALID | **`DS_FREE`** | 0 |

expected 采用 v002 反例的原始预期（OFF/INVALID = DS_FREE），未改成现结果。
对照：流中无 TF 时三模式一致 `DS_FREE`；TF 在 pass 边界之后不影响 OFF。

## 2. V3.2 hoist 同类 case（片段执行，PASS；整函数 SKIP）

`hoist_try` 依赖 `R/S/rt_same/h_ser/MTLClearColor`，无法合理抽离，因此只提取 **真实 TF 分支文本**
并用最小扫描骨架观察 caller 可分辨行为（其余分支为 stub，明示）：

| mode | 到达可 hoist 的 clear |
|---|---|
| ON | 否（在 TF 处 `return`，不产生跨边界候选） |
| OFF | 是（`break` 继续扫描，与 pre-A2b default 等价） |
| INVALID | 是 |
| 无 TF 对照 | ON/OFF 都到达 |

另测 `hoist_take`/`hoist_skipped` 仍拒绝把 TF 记录当作可跳过项。**不把本片段称为 hoist 成功路径证明。**

## 3. V3.3 barrier 纯化与去 latch（执行，PASS）

- 重复扫描判定一致；非 TF 扫描不能影响后续 TF 判定；
- 顺序：`pre-index 扫描 → tf_diag_enter → lookahead` 与直接 lookahead 结论相同；
- 源码事实：`g_tf_diag_seen` 在 v003 中已不存在、`fz_prefilter` 无 seen guard、barrier 为单表达式；
- 仍存 10 个 barrier 调用点（8 个继承 + 2 个新增 mode gate：`ds_scan`、`hoist_try`）；
- 去掉粗 latch 后，局部 scanner 仍拒绝跨 TF（`fz_next` 返回 0、`bad=1`）；
- consumer 路径未变：一次 consumer 调用仍只 apply 一次。

## 4. V3.4 继承表（按 body SHA，不按整文件）

| 函数 | v002→v003 | 处置 |
|---|---|---|
| `fz_next` / `hoist_skipped` / `hoist_take` / `defer_try` / `sdx_decide` / `frz_op` / `tf_diag_case` | 相同 | 继承 V002 / V002-S 对应证据 |
| `tf_diag_barrier` | 变化 | V3.3 重测 |
| `ds_scan` | 变化 | V3.1 重测 |
| `hoist_try` | 变化 | V3.2 片段重测（整函数仍 SKIP） |
| `fz_prefilter` | 变化 | V3.3 caller + V002-S S03 复用 |
| `tf_diag_enter` | 变化 | V3.3 顺序测试 |

## 5. mutation

删除 `ds_scan` 的 TF mode gate（回到无条件 keep）：`compile_rc=0`、`run_rc=1`，V3.1 的 OFF/INVALID 两项失败（r=1、why=42）。

## 6. 限制（不升级结论）

- `hoist_try` 全函数、完整 `fuse_try` 计划、`defer_try` 主扫描、`sdx_walk` 索引构造、`frz_op` body 均未执行或仅继承；
- V002-S 的 SKIP 项保留（见 `v002/validator/supplement/result.json`）；
- 无 host/GPU/guest/gate/采样；不宣称 renderer/GPU/NVN 语义；
- mode/lifetime/stream 安全与真实 producer 仍未做；A2c 未开启；route NO-GO。

## 7. 结论

F1（ds/hoist 的 TF case mode 门控）在其原反例上成立；F2（latch 移除 + predicate 纯化）成立且未削弱局部 scanner。
但这只覆盖本报告列出的执行项，**不等于** A2b 所有路径已验证。
