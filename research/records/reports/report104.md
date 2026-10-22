# report104 · PS 531d fout{2:uint} 两 key 候选构建 + 无 draw PSO smoke（纯离线）

日期：2026-10-22 01:02–01:20（本机）
目录：`/path/to/external-drive/xc3/work/experiments/fout-531d-uint2-candidate/`
HEAD `36bba17c0f45d22c78ce987dcfe177f2860d81cc`（未变）；无生产 profile/工具/lock/源代码改动、无 guest/gate/host 编译、无提交。

---

## 0 范围与输入

- 从 `tex27-writeflag-correct645` 完整复制 profile/pkg 到新 SSD 目录；唯一数据差异是在
  `shader_facts.tsv` 新增一行：

[Fenced excerpt omitted from the shareable research record.]

- 保留原 `4bae5b8abd3bec7f` 的 `fout {"0":"uint","1":"uint"}` 与所有其它 facts；color0/1/3 保持默认；绝不四输出全 uint。
- 其它 profile 文件与 pkg 逐字节相同；tex27 目录的 facts sha `5ae41c2d…` 未变，新 facts sha `3e34a5e2…`。
- profile 所有值（TEX27/base20、SSBO110/510/0、IMG120/slots1、单 fout）不变；旧目录未改名复用。
- 依据：`provenance-fout-531d-uint2.md`（run 238–248 完整原文 + MSL 颜色声明 + `nvn.h:400/407/434` 与
  `nvn_fmt_mtl.c` 表）；单 pass 观测、`pc_missing:true`、非 PC 反射、其它 float-target 用途 unknown。

## 1 目标身份与结构（只读核对）

- PS `531d637463e53486`：pixel，`ps_shd_post_s44p0.bin`，len 4536，sha `b88de1f829033549…`；VS `f64e061d85e6f3a5`：
  vertex，`vs_shd_post_s44p0.bin`，len 2744，sha `2f116097d50c43cb…`。
- `shd_post` Slct44/program0 条目有序 `:0:vs f64e…` → `:1:ps 531d…`，**不含 GS**；ctl 2176，code 512/2304。
- `validate_map` 645 keys / 0 problems；`validate_pairs` 0 problems；check-tools rc0。

## 2 构建（真实工具，非手写 chain）

- chain：facts 表属于 chain 输入，实际由 `dmsh_chain.py` 算出 **`8c02a1137b0d → c26257ff13a8`**；先 `--header`
  写新目录 header，再单次构建。
- `build.cmd`/`build.env`：cwd repo、`DM_GAMES_DIR=<新目录>/profile`、`DM_GAME=010074F013262000`、
  `DOTNET_ROOT=/opt/homebrew/opt/dotnet/libexec`、`J=1`、`DMSH_CAS=<新目录>/cas`、`WORK=<新目录>/work`（已存在）、
  XLATE 默认 1/1、无 IOSOUT/PREFILL；**仅显式两个 key** `531d637463e53486 f64e061d85e6f3a5`。
- 单次运行 rc0：`shaders 2: ok 2`、`shader cache rebuilt 2`、`Metal cache compiled 2`、未解码 binding 0、
  driver 读取 0；job `_b_build.json` 两条均 `st=ok`。
- 不 import 顶层 `dmsh_build`；未改其它 facts、未为通过而试凑译器。

## 3 验收：MSL/JSON 实际变化

- **JSON**：两个 key 相对 tex27 基线只有 `chain` 不同（`8c02a1137b0d → c26257ff13a8`）；bindings、driver reads 与
  VS 代码逐字节一致；VS MSL diff 0 行。见 `diff/json_diff.json`。
- **MSL（归一化标识符后）恰好 10 行差异**（`diff/msl_normalized_diff.txt`）：

[Fenced excerpt omitted from the shareable research record.]

- color0/1/3 仍为 `float4`；color2 变为 `uint4`，四个分量由同一 float 值 `as_type<uint>` 逐分量 bitcast（候选 MSL
  276–279 行）。**只记录赋值/bitcast 变化，不称语义证明**；未手改 MSL/JSON。
- 原始未归一化 diff 的其余约 448 行全部是标识符重编号（如 `m_47→m_49`、`_235→_237`、`_456→_458`），由 color2 类型改变
  引起的生成编号位移，无结构/语义变化；`diff/color_context.txt` 保留两版颜色声明与赋值原文。

## 4 可选 PSO smoke（无 guest/无 draw/无 command buffer）

- 复用/改写的 `psosmoke.m`：只加载候选 VS/PS metallib、创建一次 `MTLRenderPipelineState`；颜色格式按本 run
  `55/70/13/55`、depth/stencil `260`；`rasterSampleCount=1` 与顶点布局（MSL attribute(0) float4、stride 16）是
  **诊断选择**，不是 guest 证据；未为通过改颜色格式。
- 实际：`clang` 构建 rc0；运行 `PSO OK (colour 55/70/13/55, depth/stencil 260, samples=1 diagnostic)`。
- 这只说明 Metal 接受该 PSO（uint4 color2 + R8Uint 附件），**不**证明 GPU 执行/采样/内容/画面。

## 5 边界与状态

- 候选仅两 key、非全 645；未建 matching host、未跑 GPU 写/采样/截图；active `tex27-writeflag-correct645` 与
  `ssbo-writeflag-correct645` 不被替换。
- 本快照/构建不证明其它 float-target 用途、NVN 语义或其它 7 个整数 pair；不扩 facts、不改 fout 其它分量。
- 文档：INDEX/EXPERIMENTS 加入 exp106（fout-candidate/evidence-only）；实验 README 写就；request 105 补 relay
  `codex-xc3-531d-one-run-14ae9003203c400faf9b01247f245859` 与 `accepted:true`；request 106 原样归档
  （local id `xc3-fout-531d-106`；relay id 未提供 unknown）。
- HEAD `36bba17`；`git status` 仅既有未跟踪 `XC3-SETUP.md`；AGENTS.md/XC3-SETUP.md/共享 host/旧证据未动。停止等 review。
