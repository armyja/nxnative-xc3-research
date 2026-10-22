# report161 · A2c-impl：启动固定 mode + 条件 slot 安装 + 独立 TF 意图 observer（候选，未验收）

日期：2026-10-22 13:4x（本机）· HEAD `1408257`（未变）· 授权：主管 A2c-impl（90 分钟），实现方角色。
无 commit/push/PR；无 host build/链接/执行、无 shader/Metal/PSO/device/GPU/guest/gate/采样；profile/库/lock/chain 未动。
未改 `nvn_slots.tsv`、`nvn_obj.h`、`encode_args_`/dummy、AGENTS/XC3-SETUP、V001-3 快照与 validator 目录。route 仍 **NO-GO**。

## 0 结果

- **C01**：mode 在 `nvn_init_slots()` 内**只解析一次**（`DM_NVN_TF_DIAG`，仅字面 `"1"` 为 ON；absent/empty/`"0"` OFF；其它 invalid 按 OFF），`dm_tf_diag_get_mode()` 在固定前返回 OFF、固定后不可变；`dm_tf_diag_set_mode` **已删除**（`grep` 无引用，生产无 runtime toggle）。
- **C02**：仅 ON 时把 7 个 typed adapter 装到对应 slot；先解析/校验全部 7 个名字（必须存在且仍为 `nvn_unimpl_entry`），**all-or-none** 安装；任何缺失/占用 → 拒绝诊断、全部保持原状；`g_nsem`/`nvn_real`/`nvn_big_real`/其它 slot 未动；日志明确 “diagnostic intent only; TF is not implemented”。
- **C03**：记录路径未改（仍 40 B、`rec`+`cmd_alloc`，plural 只 opaque、不读 ranges）；未新增 TF 写入/DrawTF draw。
- **C04**：`kd_res_line` 在 `KDR_HIT` 且 gs-res 行成功输出之后、TF mode ON 时输出一条 `[tf-intent]`；字段用同一 `r.frame/r.pass/r.vs/r.ps` + 配置的 `g_gsres.gs_hex`，不重复 hash/query、不 materialize program；所有 `kdr_append` 检查，溢出只输出 `[tf-intent] diagnostic-error`；失效字段 `bound0=none` 不冒充已知 binding。
- **C05**：A2a 生命周期不变（顶层 unknown、嵌套继承、`OP_BEGIN/END` 不 reset）；`tf_diag_gate_allows` 未接入真实 route。
- 语法检查：`nvn_mtl.m` rc=0 / 0 error；`hle_nvn.c` rc=0 / 0 error。CPU smoke（真实 install/formatter 切片）：7 项断言组全过。**均不构成验收。**

## 1 SHA

pre-A2c（`/path/to/external-drive/xc3/work/experiments/tf-diag-a2c/pre-a2c/`）：`hle_nvn.c 36863fc4…`、`nvn_mtl.m 2ba9af1a…`、`nvn_tf_diag.h 578957c7…`。

| 文件 | SHA256 |
|---|---|
| `hle_nvn.c` | `de46fccbb3fee56b7754a3acdd585a190e1ddd7c12611b8387dc862b44a28b84` |
| `nvn_mtl.m` | `a3e43b03095dff46f74b8e89f2070160c0a145ef4dbf879abe7387c754f7eaf4` |
| `nvn_tf_diag.h` | `b27fb321eb78f3aee678c3a72cf9de3cc7ba37744350a2682b02ef08688008ba` |
| `nvn_obj.h` | `8e9f93e2…`（未变） |

修改函数：`hle_nvn.c`: `nvn_init_slots`（固定 mode + 条件安装）、`tf_diag_install_adapters`（新）、`dm_tf_diag_get_mode`（新，替代 setter/getter 对）、`tf_diag_emit`（改用固定 getter）；`nvn_mtl.m`: `kd_tf_intent_line`（新）、`kd_res_line`（调用点）、前向声明块；`nvn_tf_diag.h`: `tf_diag_reason_name`（只读枚举名）。

## 2 7-slot 安装流程与 OFF 保留点

1. `nvn_init_slots()`：先按原逻辑把全部 slot 初始化为 `nvn_unimpl_entry`，再由 `swnvn` 段填入语义实现并计 `g_nsem`（**原逻辑未改**）。
2. 末尾：`g_tf_diag_mode = tf_diag_parse_mode(getenv("DM_NVN_TF_DIAG")); g_tf_diag_mode_fixed = 1;`。
3. 仅 `mode == ON` 时调用 `tf_diag_install_adapters()`：
   - 逐个名字在 `nvn_names[]` 中定位；缺失 → 日志 `not installed: <name> is not in the name table` 并返回；
   - 该 slot 必须仍是 `nvn_unimpl_entry`；否则 → 日志 `not installed: <name> is not the red-reporting stub` 并返回；
   - 7 个全部校验通过后才逐个写入 `slot.fn`（初始化阶段单线程，不存在部分失败窗口）。
4. OFF/INVALID：**不调用**安装函数 → slot 数组、`unimpl_entry`、`g_nsem`、旧日志行为原样；不新增日志。
5. 未触碰：`g_nops` 表、`nvn_big_entry`/`nvn_prof_entry` 包装逻辑、`nvn_real`/`nvn_big_real`、`cnt`。

## 3 observer 格式与调用点

调用点：`kd_res_line()` 中 `MLOG("%s", line);` 之后、`g_gsres.closed = 1;` 之前；条件 `tf_diag_on()`（即启动 mode==ON）。
`KDR_HIT` 之外不会到达该点，`kdr_format` 失败会提前 `diagnostic-error` 并关闭 observer → 不会输出半行。

单行格式（示例来自 smoke，真实值运行时决定）：
[Fenced excerpt omitted from the shareable research record.]
- 字段：`active/pause/reason/seq/events/copies/depth`、`bound0=valid addr=… size=…` 或 `bound0=none`、`begin/end/draw`。
- 无 guest 内存读取、无资源内容、无 Metal 调用、无 hash/query；不重复 `[gs-res]` 的任何既有字段行为（不改其格式/one-shot/KEYDUMP）。
- 溢出 → 只输出 `[tf-intent] diagnostic-error`（smoke O3 覆盖）。

## 4 实际命令与日志

[Fenced excerpt omitted from the shareable research record.]
日志：`tf-diag-a2c/syntax-mtl.log`、`syntax-hle.log`、`smoke_a2c.log`、`install.inc`/`intent_fmt.inc`（提取件 SHA 见 `extract_a2c.py` 输出）。

smoke 覆盖：S1 全 stub → 7/7 安装、日志含 “diagnostic intent only”“not implemented”；S2 一个 slot 已占用 → 0 安装、原状保留；S3 名字缺失 → 0 安装；O1 字段/关联/失效 bound；O2 valid bound；O3 溢出拒绝半行。

## 5 未测路径（如实列出）

- `DM_NVN_PROF=1` 的 `nvn_prof_entry` 包装：本实现的安装发生在 `nvn_init_slots`，构造器随后会把非 stub slot 包成 prof entry（含这 7 个）→ 与 prof wrapper 的交互**未测**，按约束未改 prof 路径。
- `nvn_big_entry`：7 个名字都以 `nvnCommandBuffer` 开头，现有 big-stack 包装会跳过它们；未单独验证。
- 并发/多线程调用、`longjmp`/崩溃退出导致 depth 残留（A2a 已登记 gap）、command memory 生命周期（F3：size 检查≠内存边界保护）。
- 真实 producer 行为、ovserver 在真实 replay 中的输出、完整 renderer barriers、V004 独立验收：均未做。
- 未测：`nvn_names` 表中重复名或同名多索引的极端情况（当前按首个匹配处理，与既有 `nvn_nops_register` 一致）。

## 6 边界

- 本任务仅 working tree 实现；未启用真实诊断（mode 默认 OFF 且需启动 env），未提交、未 build host、未跑 guest。候选完成后冻结供主管 V004 snapshot；不自行宣布通过、不启动 A2d。
- `tf_diag_gate_allows` 仍未接入 route；真实 GS/TF route 继续 NO-GO。
