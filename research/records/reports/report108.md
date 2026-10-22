# report108 · d3c fout{3:uint} 645 候选 + host + smoke + pipeline 越过旧拒绝

日期：2026-10-22 01:36–01:42（本机）
目录：`/path/to/external-drive/xc3/work/experiments/fout-d3c-uint3-correct645/`
Run：`/path/to/external-drive/xc3/work/experiments/fout-d3c-pipeline-final-plan/run-20261022-013913/`
HEAD `36bba17c0f45d22c78ce987dcfe177f2860d81cc`（未变）；无 tracked 改动、无 commit/push。

---

## 0 范围与输入

- 从 `fout-531d-uint2-correct645` 复制到新目录；唯一新事实行 `d3c541d46f389225 {"attr":{},"fout":{"3":"uint"},
  "img":{},"pc_missing":true,"tex":{}}`；4bae/531d 行逐字节保留，其它 profile/map/pairs/pkg 不变；facts sha
  `d9cc9ce73f7549ed42a8987aacdaf6f0c6c79311cf241175d0cd144763a4e826`。
- provenance：`provenance-fout-d3c-uint3.md`（report107 原始 slots/context + `nvn.h:398/408/460` +
  `nvn_fmt_mtl.c` 92/10/53 + MSL 颜色声明；单 pass、`pc_missing:true`、其它 target 用途 unknown）。
- 生产验证：map 645/0、pairs 90/0、package_verify 645/645；目标 d3c pixel/`ps_shd_lgt_s7p1.bin` len 13240
  sha `52d75f06…`；VS a620 vertex/`vs_shd_lgt_s7p1.bin` len 2488 sha `7eba89af…`；程序 `shd_lgt#7:1` 有序 vs→ps，无 GS。

## 1 645 候选库

- 真实 `dmsh_chain.py`：`35de4665bff4`（新链，非手写）；check-tools rc0；header 重生成；fresh cas/out/work、J=1、
  显式 645 keys 单次 rc0。摘要：645 ok、variant 72、Metal 105 reused/540 compiled、未解码 0、driver 2(c0)。
- 验收对照 `fout-531d-uint2-correct645/b-c26257ff13a8`：
  - JSON 深 diff **仅 chain 字段，645/645**；
  - metal/metallib **仅 `d3c541d46f389225` 不同**（含 531d、f64e 在内的其它 644 个逐字节相同）；
  - sbuf 45（7 rw）、img 9、tex/samp `reg=None` 0、driver readers/`drv_unfillable` 与上一候选逐项相等；
  - c1_guard 真实生成 `# chain b-35de4665bff4 …`、`not proven bounded: 0`（list 语义，非安全证明）。
- d3c MSL：`float4 color0/1/2`，`uint4 color3`；结构（标识符掩码）diff 恰 34 行，全部是 color3 声明、三处零初始化
  `0.0→0u`、最终 `as_type<float>`/`uint` 赋值，无其它结构差异；另用一对一 LCS 映射（1913 条、0 冲突、双射）核对，
  行级 diff 受块重排影响很大，不能据此声称语义等价——数值语义仍未验证；未手改 MSL/JSON。

## 2 matching host + PSO smoke

- `linkcheck/dmhost-fout-d3c-uint3-645` sha256
  **`06f7902ae22d8a3ad1fa96ad1e6f2b6d1432636d54e34777583c70b3723a8e52`**；新 generated headers 在 repo gen 之前；
  compileline `df1c8c03…`、build.log `237bbc2b…`、rc `93ff7811…`，rc0/0 errors；strings 新链 1、旧链 `c26257ff13a8`/
  `8c02a1137b0d` 0、`tex-final`/`sbuf-final` 保留；未运行；旧/共享 host 未覆盖。
- PSO smoke（无 guest/无 draw/无 command buffer）：颜色 `92/92/10/53`、depth/stencil `260`，sampleCount=1 与顶点布局
  为诊断选择；`PSO OK`。只证明 Metal 接受该 PSO。

## 3 合并授权运行（pipeline-final）

- 计划 `fout-d3c-pipeline-final-plan`：strict preflight + 7 组 no-guest 测试全过后启动；1 gate / 1 guest / 0 retry。
- Gate：11 样本 `0.000→10.171`（span 10.171≥10），min available **3310 MiB**，`launch_at=10.186`。
- 唯一链（`boot.log` 234/310/333，`chain.txt`）：

[Fenced excerpt omitted from the shareable research record.]

- 同 frame **1509** / pass **3139**；实际 VS a620（按本次记录，不预设）；`K st0` **absent**，明确只有两处 VS 来源
  （kd/d），缺第三来源；目标 pair 无 pipeline/load 错误；`pso_user.tsv` 第 **478/479** 行为同 pair R 记录。
- 时序/资源：launch_at 10.186 → first 62.755 → term 62.758 → gone 62.859，exit=0（guest≈52.57 s）；211 样本
  min available 1990 MiB、max RSS 920224 kB（≈898.66 MiB）；log 41011 B、shdump 640 KiB；两条原内容 GS 豁免
  （62.476，hash 一致）；无残留 child。
- 停止原因：`pipeline-final: complete pass=3139 vs=a6201ef91b12f9e2_b k0=absent`。

## 4 证明与不证明

**证明（编码期）**：d3c pair 在新 facts 库下越过旧 pipeline 拒绝；同 frame/pass kd→K st1→d，d 的 VS/PS 与 kd 一致；
PSO 有同 pair R 记录（第二来源）。K st0 缺失，不声称三来源一致。

**不证明**：GPU 执行/内容/像素；bitcast/`uint()` 数值语义；其它 6 个 RG32 pair；NVN→MTL 语义；不把 d 日志称为
GPU draw 提交。

## 5 文档与状态

- INDEX/EXPERIMENTS 加入 exp110（full-candidate + run）；实验 README 写就；request 109 补 relay
  `codex-xc3-d3c-psort-batch-43811cdd2c10401dba3f977092953e90` 与 `accepted:true`；request 110 原样归档
  （local id `xc3-d3c-pipeline-110`；relay id 未提供 unknown）。
- HEAD `36bba17`；`git status` 仅既有未跟踪 `XC3-SETUP.md`；AGENTS.md/XC3-SETUP.md/共享 host/旧证据未动。
- 本轮 guest 后无自动下一轮/其它 shader 修复授权；停止等 review。
