# V002 补充独立覆盖（V002.F3 追加）

针对主管对 V002 的裁决（F1 必修 mode-gating、F2 必修 latch、F3 待补充覆盖），本文件只做**追加**：
已 review 的 `report.md` / `result.json` / `evidence/sha256sums.txt` 保持冻结、未改一字节。

## 1. 新增可执行覆盖（B02 控制流）

`tests/supplemental.c` 用**同一份**逐字提取的 `fz_next` / `hoist_*`（v002 4055–4081、4129），
驱动验证方构造的最小流，全部 6 项 PASS：

| 用例 | 结果 |
|---|---|
| 嵌套 CALL：子列表内的 TF 让游标停止 | PASS |
| CALL/return：子列表正常返回后，在调用方 TF 处停止 | PASS |
| JUMP 跳到 TF：跳转后边界仍生效 | PASS |
| `g_rest` 剩余 handle 遍历中遇 TF：边界生效 | PASS |
| TF 在 hoist skip 列表中：游标仍不跳过它 | PASS |
| OFF 对照：同一嵌套流无边界、TF 作为普通 op 可见 | PASS |

这条补齐了 V002 报告里“共享游标只测了线性流”的缺口：返回栈、跳转、剩余 handle 三条路径的
boundary 语义现在都是**可执行证据**，不只是源码阅读。

## 2. 不可执行站点的机器核对（23/23）

`src/static_guards.py` 对 8 个 `tf_diag_barrier` 调用点做结构化事实核对（不是执行替代）：

- 8 个站点各自位于预期函数内（hoist_skipped / fz_next / hoist_take / sdx_walk / defer_try×3 / frz_op）；
- `frz_op`、`fz_prefilter`、`hoist_skipped`、`hoist_take` 的 guard 是函数体内**第一条语句**（之前无副作用）；
- `defer_try` 主扫描：barrier 在 hoist-skip 与 switch 之前；Q 复查：barrier 在采样冲突判定之前；
- `defer_try` 的 `goto fail` 落在 fail 标签，随后 return，不会接受该候选；
- `ds_scan` 的 TF case 仍然**没有 mode gate**（把 V002.F1 再固化为可复查的事实）。

明确边界：这些是放置/方向事实，不等于执行过 `defer_try` / `frz_op` / `sdx_decide`。

## 3. 可达性口径（按主管裁决）

“模型输入可达”与“生产入口可达”拆开记录，避免把反例复现误读成 producer 已启用：

| 发现 | 模型输入可达 | 生产入口可达 | 说明 |
|---|---|---|---|
| V002.F1 OFF 下 ds_scan 结论改变 | 是（构造流） | **否** | 需要流中存在 TF 记录；当前无 producer |
| V002.F2 seen latch / 扫描顺序 | 是 | **否** | 需要 ON 模式 TF 记录 |
| V001.F3 size≠边界 | 是（短 payload 记录） | **否** | 不构成“stream 生命周期已保证”的结论 |
| V001.F1 mode 中途切换 depth 泄漏 | 是 | **否** | 需要运行时开关，A2b 未启用 |

生产侧事实：`dm_tf_diag_set_mode` 仅 1 处定义、0 处调用；适配器未注册、无调用点；生产不产生 OP_TF_DIAG 记录。
因此上述反例是**模型输入可达**，不是生产入口可达。

## 4. 契约净效果

B01/B03/B06 不变；B02 由“线性流 + caller 模式”扩展为“控制流全路径可执行”，仍 PASS；
B04 仍为唯一契约偏差（V002.F1）；B05 仍 PASS 并保留 F2 必修项；route 继续 NO-GO。

## 5. 产物（均未覆盖已 review 的冻结文件）

- `tests/supplemental.c`、`build/supplemental`
- `src/static_guards.py`、`evidence/static_guards.json`
- `evidence/supplemental_run.log`、`results-supplemental.json`
- `evidence/supplemental-sha256sums.txt`
