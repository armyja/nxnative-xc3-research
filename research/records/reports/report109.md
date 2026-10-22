# report109 · 剩余 6 个整数 RT pair 的只读归类 + 有界批量 psort 设计

日期：2026-10-22 01:44–01:55（本机）
HEAD `36bba17c0f45d22c78ce987dcfe177f2860d81cc`（未变）；无代码/构建/翻译/host/guest/gate、无 profile/facts/库/lock 改动、无提交。
证据目录：`/path/to/external-drive/xc3/work/experiments/posttex-6pair-classify/`

---

## 0 范围

- 固定 6 个 report101 剩余 pair（均 lgt Slct5 的不同 program）：`f9cb/06f1`、`493d/c9d7`、`43a0/885b`、`c189/1581`、
  `2862/4b9a`、`d2fd/aadd`。
- 只读使用现有候选库 `fout-d3c-uint3-correct645/out/b-35de4665bff4` 的 MSL/reflection 与 report101 原始日志；
  未新增 NVSD parser、未全容器扫描；缺值写 unknown。

## 1 六 pair 证据表（紧凑）

| pair (VS/PS) | program / package | MSL 颜色 | 绑定（实际用） | discard/depth | 输出模式 | MSL sha12 | RT 证据分类 |
|---|---|---|---|---|---|---|---|
| f9cb… / 06f1dcc9c37acf00 | lgt#5:83:1 / s5p83 | color0/1 float4 | img0 `fp_i_cb2_48_r32ui`；tex3/samp3 | 0 / 无 | color0 全 0；color1 `as_type<float>(_89)` 广播 | 22fde3f85e50 | 仅 Metal 错误：≥1 RG32Uint，logical slot unknown |
| 493d… / c9d762917edfee9f | lgt#5:109:1 / s5p109 | color0/1 float4 | img0 only | 0 / 无 | color0 0；color1 四个 `as_type<float>(_124..130)` | 000d2778c643 | 仅 Metal 错误：≥1 RG32Uint，slot unknown |
| 43a0… / 885bb4caecc378cf | lgt#5:119:1 / s5p119 | color0/1 float4 | img0；tex3/samp3 | 0 / 无 | 同 06f1 家族（`_89` 广播） | 883d1a2b3742 | 仅 Metal 错误：≥1 RG32Uint，slot unknown |
| c189… / 15816d836842bfb5 | lgt#5:75:1 / s5p75 | color0/1 float4 | img0；tex3/samp3 | 0 / 无 | 同 06f1 家族 | 396de79b85ce | 仅 Metal 错误：≥1 RG32Uint，slot unknown |
| 2862… / 4b9a4e60d5ee5f16 | lgt#5:77:1 / s5p77 | color0/1 float4 | img0；tex3/samp3 | 0 / 无 | 同 06f1 家族 | b3e81bca59d0 | 仅 Metal 错误：≥1 RG32Uint，slot unknown |
| d2fd… / aadd1c2efa076cc3 | lgt#5:1:1 / s5p1 | color0/1 float4 | img0 only | 0 / 无 | **与 c9d7 MSL 逐字节相同**（hash/skeleton） | 000d2778c643 | 仅 Metal 错误：≥1 RG32Uint，slot unknown |

- **没有任何一个 pair 有独立 RT 观测**（无该 key 的 psort 记录）；因此 “已独立观测 RT” 为空。
- **也不是完全 unknown**：每个 pair 的 Metal 错误已点名至少一个 `RG32Uint`；但**哪个 logical 颜色、其它附件格式**仍 unknown。
- 聚类：`c9d7/aadd` 是 MSL 完全相同的 2-key 代码簇（reflection 绑定不同：c9d7 有 tex/samp，aadd 没有；代码未用它们）；
  其余 4 个是“color0=0、color1 广播、img0、tex/samp”家族但 MSL hash/skeleton 各不相同——只是候选相容性线索，不作语义等价。
- 6 个都是不同 lgt Slct5 program/package（逐包/key/source 校验）；**不以共同 Slct 推同输出语义**。
- 共同点：`color0/1` 是唯一颜色输出、无 discard、无 depth、都写一个 `uint` image；但这些不推出 RT 类型或 slot。

## 2 下一轮最小有界 batch psort（仅设计，不实现）

- **开关**：新增 `DM_NVN_PSOFAIL_RT_MULTI=k1,k2,...`（最多 6 个固定 16-hex，lowercase）；现有单目标开关保留，
  二者互不覆盖；off/空=零工作。
- **捕获**：复用现有 `psort_capture`/`psort_report` 的真实 pass 快照与 pso 失败路径；每 key 一个独立状态，不再全局
  disarm；每 key 首失败记录一次。
- **签名与上限**：record 签名 = canonical `cfmt[8]` + map（enabled/lmap）+ logical↔physical 关联；每 key 最多
  **2 个不同签名**，全局最多 **12 条完整记录**；不按 serial/尺寸重复记同类；每条保留完整 header（frame/pass/assoc/
  snap/cfmt/dfmt/sfmt/ctx）+ map + 8 slots + done。
- **语义**：`same-pass`+`snap=valid` 才是有效 RT 证据；`assoc=mismatch` 记录保留但标 unassociated；cached failure /
  diagnostic-error / 未关联 为该 key 终局非成功（不阻塞其它 key）；switch 非法则整体 disabled 并显式记录。
- **一次性/预算**：每 key×签名 one-shot；不延长 180s、不扩 GS、不重试；预算内可部分集合，未出现即缺证据；首个非豁免
  完整 dump 仍优先停止。
- **不做**：不新增 shader 物化、不做 guest 读取、不按矩阵猜格式；单条记录不能证明该 PS 从无其它 float-target 用途。

## 3 后续流水线约束（仅设计）

- 从每条真实记录的附件 type/logical location/map **直接生成最小 fout**；未观测颜色保持 unknown；候选矩阵只围绕真实
  矛盾，每行带 provenance（记录行号/hash）。
- 每 key 分别 compile/PSO；同类型约束类只选代表跑 guest，且只证明代表 key；其余不能称运行已验。
- 正式 facts 仍人工 review；不自动推广/生产回写；type 等价 ≠ 语义等价。
- 批量事实稳定后**一次**完整 chain 构建，不为每个 key 重建 645；生成/校验程序边界、输入输出/hash、失败即停写清即可，
  不做通用优化平台。

## 4 成本与最大风险

- 实现：现有 psort 路径内加每-key 数组与开关（约 200 行）+ 一个 supervisor/matcher + synthetic tests；**一次 host 重建**；
  库/facts 不变（无 645 重建）。
- 一次 batch run：10 s gate + ≤180 s guest，最多 12 条记录；可部分集合。
- 最大风险：每 key 2 签名上限可能漏掉后续不同 RT 用途；首失败记录有偏差；无失败则无 slot；附件类型兼容/PSO 通过
  ≠ 数值或画面正确；其它 float-target 用途仍需后续证据。

## 5 状态

- 当前 active `d3c` 候选有限检查点保留；pixel 正确性仍未知；本轮未实施方案/未 launch。
- 文档：INDEX/EXPERIMENTS 加入 exp111（classification/design-only）；证据表在
  `posttex-6pair-classify/evidence-table.md`；request 110 补 relay
  `codex-xc3-d3c-fout3-batched-060f97816b3c4b1db2deb3cf053ee7ea` 与 `accepted:true`；request 111 原样归档
  （local id `xc3-6pair-batch-design-111`；relay id 未提供 unknown）。
- HEAD `36bba17`；`git status` 仅既有未跟踪 `XC3-SETUP.md`；AGENTS.md/XC3-SETUP.md/共享 host/旧证据未动。停止等 review。


---

## 6 追加更正（主管 review；原文保留）

- 原文“都写一个 uint image”错误。复核 6 个 MSL：均声明 `texture2d<uint>`，各仅一次 `.read(...).x`，**没有任何
  `.write`**。不能从 image kind 或 `uint` 声明推写；RT 未知结论不变（logical slot 与其它附件仍 unknown）。
- 证据表/README/pairs.tsv 已同步追加该更正。
