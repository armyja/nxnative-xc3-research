# report101 · post-tex 阻塞只读分诊（69 RED，无代码/配置/guest）

日期：2026-10-22 00:35–00:50（本机）
HEAD `36bba17c0f45d22c78ce987dcfe177f2860d81cc`（未变）；无代码/配置/facts/库/host 构建/翻译、无 guest/gate、无提交。
证据目录：`/path/to/external-drive/xc3/work/experiments/posttex-blocker-audit/`

---

## 1 RED 全量（69 块，可追溯）

`red.tsv` 列：`line,end,category,vs,fs,missing,mtl_format,keys,first_seen,count,raw`。提取器按行首 `[RED]` 起块，并把后续不以
`[` 开头的续行并入 `raw`（本 run 无续行，已支持）。按日志顺序（不是出现次数）分类：

| 类别 | 块数 | 首现行 |
|---|---|---|
| save transaction clone warning | 1 | 84 |
| nvnDeviceRegisterFastClearDepth（stub） | 1 | 95 |
| pipeline prewarm seed missing（warning） | 1 | 111 |
| nvnTextureWriteTexelsStrided（stub） | 1 | 141 |
| SetRasterizerDiscard on ignored | 1 | 259 |
| nvnCommandBufferClearColori（stub） | 11 | 260 |
| nvnCommandBufferBindTransformFeedbackBuffer（stub） | 11 | 261 |
| nvnCommandBufferBeginTransformFeedback（stub） | 11 | 262 |
| nvnCommandBufferEndTransformFeedback（stub） | 11 | 263 |
| shader not in the map（6 个均为 GS） | 6 | 265 |
| integer-RT pipeline failure | 9 | 270 |
| cross-stage interface pipeline failure | 3 | 272 |
| nvnColorStateGetBlendEnable（stub） | 1 | 498 |
| integer render target: blend not applied | 1 | 631 |

- PSO 预热是**无 draw 的 warning**；pipeline 失败是真实 draw 请求但无法建 pipeline；missing-GS 是 shader 加载尝试；
  unimplemented 调用在日志中没有 draw/pair 关联（unknown）。
- 未实现 API 的重复次数只作记录，不当作严重性。

## 2 整数 RT 失败（8 对，9 条）

`integer_rt.tsv`：全部是 **VS+PS** 程序（容器确认无 GS 项）：

| pair | program | Metal attachment | MSL 颜色输出 |
|---|---|---|---|
| f64e… / 531d… | shd_post#44:0 | R8Uint | color0..3 float4 |
| a620… / d3c5… | shd_lgt#7:1 | R32Uint | color0..3 float4 |
| f9cb… / 06f1… | shd_lgt#5:83 | RG32Uint | color0..1 float4 |
| 493d… / c9d7… | shd_lgt#5:109 | RG32Uint | 同上 |
| 43a0… / 885b… | shd_lgt#5:119 | RG32Uint | 同上 |
| c189… / 1581… | shd_lgt#5:75 | RG32Uint | 同上 |
| 2862… / 4b9a… | shd_lgt#5:77 | RG32Uint | 同上 |
| d2fd… / aadd… | shd_lgt#5:1 | RG32Uint | 同上 |

已知：Metal attachment 格式与 MSL 输出类型。**未知**：NVN color slot/format、view/`lmap`、哪一侧错误；本 run 没有
`psort`/`cview` 附件记录。不能从 Metal 错误推断 color0，也不能擅自断定 shader 应输出 uint。

## 3 GS / 接口 / TF

- `shd_post#83:0` 是 **VS+GS+PS**：VS `d7bec51f33a503a4`、GS `a841a5d995c26b26`、PS `ef5549568475fd20`。GS 缺失使 host
  直接配 VS+PS；PS 读 locn0/1/2，而 VS 只写 gl_Position → 该接口失败是 GS 缺失的后果，不是坏 pair。
- 6 个 missing shader 全为 **GS**（`gs.tsv`）：2 个内容豁免（a841、95bf，62.93 s），4 个非豁免完整 dump 写于
  00:32:19（与 triple 同一秒）；supervisor 在该 poll 先处理成功记录、后扫描 complete dump，故这 4 个未在停止前评估。
  这是**顺序观察**，不是豁免扩大。
- 另两对接口失败（runtime recovered `6bab…` VS + `a0d1…`/`db1d…` PS）是普通 VS+PS：VS 写 locn0..11，PS 读
  locn12,13,14 / 12,13,15,16,17；两对不在 `shader_pairs.tsv`，`vs_pad` 未生效。runtime key 无容器，是否存在 GS 变体 unknown。
- ClearColori / Bind/Begin/EndTransformFeedback 各 11 次，均为 **unimplemented stub**（`dm/gfx/nvn` 无定义）；而
  SetRasterizerDiscard 是 log-and-ignore（无 discard 效果）、`nvnCommandBufferClearColor`（float）在 `hle_nvn.c:795` 已实现。
  日志无 draw/pair 关联 → 视觉影响 unknown；不能把 GS 缺失归因于 TF。

## 4 一页优先级

**选择：整数 RT 格式审计（下一步）**。

- 理由：12 个 pipeline 失败中 8 个是同一类，集中在 lighting/post 程序，缺的是一处证据（NVN color format/view），一次只读
  记录即可同时分类 8 对，不需要改行为。
- 用户可见影响/未知：这些 pass 的 draw 被跳过（pipeline 建失败）；具体缺哪些效果、像素是否正确 unknown（无 capture/diff）。
- 最小可证伪动作：复用现有 psort/pipeline 记录路径（`pso_user.tsv` 背后的机制），在这 8 对的 pipeline 创建处只读记录
  NVN color slot+format+view/`lmap` 与 shader 声明输出类型；随后逐对判定是格式解码错还是输出类型缺 facts。成本：一处小诊断 +
  一次授权运行；不做 GS、不改 fout、不改格式。
- 暂不选：GS 支持（结构性问题、范围大）；`vs_pad`/pair 修正（仅 3 对，其中一对是 GS 情形）；TF/Clear stubs（无
  draw/pair 证据，本轮信息增益低）。

## 5 边界与状态

- 全部只读：未改代码/配置/facts/库/host、未翻译、无 guest/gate、无提交；`red.tsv` 保留 69 条原文（含续行合并逻辑）。
- GPU/画面正确仍未证；本报告只分诊，不实现下一观测。
- 文档：INDEX/EXPERIMENTS 加入 exp102（audit/evidence-only）；实验 README 写就；request 101 补 relay
  `codex-xc3-tex27-one-run-2a6015bf6a054fa695dae4d6e2037ccf` 与 `accepted:true`；request 102 原样归档
  （local id `xc3-posttex-audit-102`；relay id 未提供 unknown）。
- HEAD `36bba17`；`git status` 仅既有未跟踪 `XC3-SETUP.md`；AGENTS.md/XC3-SETUP.md/共享 host/旧库证据未动。


---

## 6 追加勘误（主管 review；原文保留）

- 优先级句“12 个 pipeline 失败中 8 个”应为：**8 个唯一整数 pair / 9 次 integer 失败**（f64e/531d 出现两次），再加
  **3 次 interface 失败** = 12 条 pipeline 失败；不是“8 of 12 个失败”。
- 现有 `DM_NVN_PSOFAIL_RT` 只接受**单个 16-hex 目标**，且在同一 fragment pipeline 第一次失败时记录一次后即 disarm；
  它**不能在一个 run 内同时覆盖 8 个 pair**。psort 的附件快照（pass 建立时的 pd/NVN 对象）也**不等于** `pso_user.tsv`
  的内容。下一轮只做单目标，不为批量审计扩诊断范围。
