# report112 · 六 key 最小 facts 候选 + 645 隔离构建 + 6 PSO + 代表 06f1 运行

日期：2026-10-22 02:10–02:24（本机）
候选：`/path/to/external-drive/xc3/work/experiments/fout-six-lgt-correct645/`
Run：`/path/to/external-drive/xc3/work/experiments/fout-six-lgt-pipeline-final-plan/run-20261022-022112/`
HEAD `af094f470c43133016a899527b06a4c598677fce`（未变）；无生产代码/facts 变更、无提交。

---

## 0 输入与 facts

- 从 `fout-d3c-uint3-correct645` 复制；保留原 3 行（4bae/531d/d3c）逐字节；新增 6 行，每行只含
  `{"fout":{"0":"uint","1":"uint"}}`，`pc_missing:true`，attr/img/tex 空；共 **9 PS facts**，仅实验候选。
- `generate_facts.py` 严格解析 `run-20261022-020510/batch-records.txt`：要求 6 key 各恰好一条、assoc=same-pass、snap=valid、
  cfmt 103,53、identity map、slot0/1 MTL 103/53；否则拒绝、原子写入。`provenance-six-fout.tsv` 逐 key 记录 rec、record
  sha256、actual pair、NVN/cview/MTL、lmap；不跨 key 复制证明。
- profile TEX27/base20、SSBO110/510/0、IMG120/slots1 不变；pkg 与 map/pairs 生产校验通过（645/90）。

## 1 645 构建

- 真实 chain **`c7c374c3eb34`**；check-tools rc0；fresh CAS/out/work、J=1、显式 645 keys 单次 rc0；variant 72、
  Metal 106 reused/539 compiled。
- 验收对照 `fout-d3c-uint3-correct645/b-35de4665bff4`：
  - JSON 深 diff **仅 chain，645/645**；bindings/45 sbuf（7 rw）/9 img/tex-samp regs/driver readers/unfillable 不变。
  - metal/metallib **仅 6 个目标 PS 变化**，其余 639 个逐字节相同；VS 全同。
  - 六个 PS 均 `uint4 color0 + uint4 color1`；标识符掩码结构 diff 分别 52/36/52/52/52/36 行，逐项过滤后全部为
    color 声明/零初始化/最终赋值，无非颜色结构变化；**不称语义等价**。
  - c1_guard 真实新链 `# chain b-c7c374c3eb34`、not proven bounded 0（list 语义）。

## 2 六个 no-draw PSO smoke

- 实际 pair：f9cb/06f1、493d/c9d7、43a0/885b、c189/1581、2862/4b9a、d2fd/aadd；各自加载/创建，未省略。
- 颜色 `103/53`、depth/stencil `260`（由记录）；sampleCount=1、顶点布局为诊断选择；六对全部 `PSO OK`。
- 仅兼容性，不证明语义/GPU/像素。

## 3 matching host

- `linkcheck/dmhost-six-lgt-645` sha256
  **`3ec26079300ede5f1ac6a97cb0830e177a1348fb8d8832e4604c55dd80241540`**；新 generated headers 优先，rc0/0 errors；
  strings 新链 `c7c374c3eb34` 1、旧链 0、`batch=1` 15、`tex-final`/`sbuf-final` 保留；未运行前不覆盖旧/共享 host。

## 4 代表 06f1 运行（1 gate + 1 guest）

- 计划 `fout-six-lgt-pipeline-final-plan`：preflight + 7 组 no-guest 测试全过后启动；gate 11 样本 span 10.108≥10、
  min 3737 MiB、launch_at 10.122。
- 唯一链（`boot.log` 477/489/491/498）：`[kd] F4593 pass 553302` VS f9cb → `K st0` f9cb → `K st1` 06f1 → `d` 同 VS/PS；
  **K st0 present**（第三来源一致）；目标无 pipeline/load 错误；`pso_user.tsv` R 1864/1865 为同 pair。
- 时序/资源：launch 10.122 → first 165.260 → term 165.263 → gone 165.463，exit 0（guest≈155.14 s）；628 样本
  min available 1514 MiB、max RSS 1167936 kB（≈1140.6 MiB）；log 73715 B、dump 1664 KiB；两条原 GS 豁免（62.081/
  62.292，hash 一致）；无残留 child。
- 停止原因：`pipeline-final: complete pass=553302 vs=f9cb32fab57fd5f8_b k0=present`。

## 5 证明与不证明

- 证明：06f1 这一代表 pair 在新 facts 库下越过旧 pipeline 拒绝，编码路径到达 kd→K st1→d；其余 5 个仅有自身附件观测
  与离线 PSO 通过，**不称运行已验**。
- 不证明：GPU/内容/像素、数值/bitcast 语义、其它 float-target 用途、其它 5 key 的运行行为、NVN→MTL 语义；facts 未
  回写/未自动推广；PC missing 仍未答。

## 6 文档与状态

- INDEX/EXPERIMENTS 加入 exp114（six-facts candidate）与 exp115（representative run）；候选/计划 README 写就；
  request 114 补 relay `codex-xc3-batch-rt-conditional-run-41e89c1cf60c4b1ba75ee258f1335a17` 与 `accepted:true`；
  request 115 原样归档（local id `xc3-six-lgt-run-115`；relay id 未提供 unknown）。
- HEAD `af094f4`；`git status` 仅既有未跟踪 `XC3-SETUP.md`；AGENTS.md/XC3-SETUP.md/共享 host/旧证据未动。
- 结束交 review，不自动下一步。


---

## 7 追加事实/勘误（主管 review；原文保留）

- 同 run `pso_user.tsv` R 解码：1864/1865 f9cb/06f1、1870/1871 493d/c9d7、1876/1877 43a0/885b、1882/1883 c189/1581、
  1888/1889 2862/4b9a、1894/1895 d2fd/aadd。源码 R 用户记录只在真实 `pso_get_` 成功分支（3561/3562）。因此**其余 5 个
  不再只是“离线 PSO”**：本次 run 都有 runtime PSO 创建证据；但没有各自 K/d，不升级为 GPU/像素/已提交 draw 证明。
- 最终 `shdump` 有 4 个完整的非豁免 GS：`ef6ec0914d348ad3` ctl2176/code256、`4c0a9c8e53f088cb` 2176/11520、
  `eafdbb5a5af2a6dd` 2176/14336、`7a7eb30dfb6187b5` 2176/6144；各 `ctl+0x704 == code size`。原文“无非豁免 dump”与最终
  目录矛盾，更正为：**在线停止判定没有因它们停（kind=pipeline-final），最终目录里有 4 个完整非豁免 GS**。
  仅凭文件最终存在不能倒推它们在停止检查前一定完整；没有单调时间锚，落盘时刻 unknown；不篡改停止原因、不重跑。
- 完整日志 500/502/506/508 也有 missing 请求；原报告未提，现补记。
