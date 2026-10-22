# report113 · 六 GS 最小路径可行性评估（纯只读）

日期：2026-10-22 02:26–02:40（本机）
HEAD `af094f470c43133016a899527b06a4c598677fce`（未变）；无代码/构建/翻译/guest/gate/profile/facts/库/工具/lock 改动、无提交。

---

## 0 固定集合与来源核对

六个 GS：原豁免 `95bfab6122539993`、`a841a5d995c26b26`，加最终 shdump 四个 `ef6ec0914d348ad3`、`4c0a9c8e53f088cb`、
`eafdbb5a5af2a6dd`、`7a7eb30dfb6187b5`。全部 ctl 2176、SPH stage bits=4（GS）、`ctl+0x704 == code size`；key 由
ctl/code 实际 hash 重算，非文件名推断。

| key | 来源（container/program） | ctl/code | ctl sha16 | code sha16 | VS/PS 结构 |
|---|---|---|---|---|---|
| a841a5d995c26b26 | `shd_post#83:0:1:gs` | 2176/1280 | 601359d648514f47 | 608f3da3932ee4a7 | 完整 VS d7be… + GS + PS ef55… |
| 95bfab6122539993 | `shd_post#92:0:1:gs` | 2176/768 | 4bb2164e54973d49 | a6f403edc3eb1696 | 完整 VS d165… + GS + PS 2e16… |
| ef6ec0914d348ad3 | `shd_lgt#3:1:1:gs` | 2176/256 | 3f21f6c7df666946 | bc9699fd02de5f0e | 完整 VS f5d9… + GS + PS abdad… |
| 4c0a9c8e53f088cb | 五个现有容器中未找到 | 2176/11520 | 9056e345e8b73b46 | 5dfd625dc7473405 | unknown（无 program 关系） |
| eafdbb5a5af2a6dd | 五个现有容器中未找到 | 2176/14336 | cbad4cb1ae10331e | d243f9cc350d8981 | unknown |
| 7a7eb30dfb6187b5 | 五个现有容器中未找到 | 2176/6144 | 2ee3b750bf732d6c | 45a049dabb1e9c32 | unknown |

- 三个确认的 **vs→gs→ps** 链（83:0、92:0、lgt3:1）；另三个只有 GS 本体，program 关系 unknown，不能按同类推。
- 现有 spch 解析器只给 stage/length/key/container 位置；**input primitive、output topology、max vertices、stream/TF、
  关键输出 varying 都没有可用解码器**（缺 GS/SPH 几何字段 decoder）。不猜、不从 code hash 反推语义。

## 1 当前拒绝点与支持面

- 构建期：`dmsh_stage.py` 明确“Metal backend 只编码 vs/ps，没有 geometry stage；选中的 gs 直接拒绝”，在 cache/输出之前。
- refill 期：`dmsh_refill.py` strict pairs 拒绝含 gs/hs/ds 的程序（`geometry stage in ...`）。
- 译器：`dmsh_xlate` 只处理 vs/ps/cs（GS 无路径）；host `nvn_mtl.m` 只绑定 `pr->sh[0]`/`pr->sh[1]`，无 GS 编码。
- Metal 侧：现有代码只有 render/compute/vertex 用法；**没有 mesh shader 代码路径**，也没有 compute 展开 GS 的实现。
  API 存在不等于本项目已实现；这里只确认“代码不存在”。
- 因此原生 stage 路径不可用；任何“忽略 GS 直接 VS+PS”或扩白名单都不是修复。

## 2 接口失败分层

- `d7be/ef55`（program 83:0）**确定 GS 链**：VS d7be + GS a841 + PS ef55；host 退化 VS+PS 导致 locn0/1/2 不匹配。
- 另两对 runtime-only（`6bab/a0d1`、`6bab/db1d`）无容器，是否有 GS 变体 unknown；不能与确认 GS 链混为一类，也不能
  用 vs_pad 补 GS 语义（vs_pad 只补缺省输出，不生成 GS 的多输出/邻接）。

## 3 六选一建议

**候选：`a841a5d995c26b26`**——唯一同时满足“完整 VS+GS+PS 程序、已知 container、已知接口失败（d7be/ef55）、代码量
最小（1280）”的 GS；语义上它比 95bf/ef6e 的未知用途更有可验证场景（能对照 d7be/ef55 的 locn0/1/2 输出）。

但**最小实现不是小改**：需要
1. 译器新增 GS→MSL（或 mesh/compute 展开）语义；
2. host 增加 GS 阶段的绑定/执行与 pipeline 连接；
3. 绑定/内置变量/输出 varying 的 ABI；4. 新的离线语义 oracle 与 guest 验证策略。
Metal 无 geometry stage，mesh/compute 替代都属结构性实现，工作量与风险都大；现有代码零基础。**本轮建议不实现**，先把
“GS 几何字段 decoder + a841 的输入/输出签名”作为下一步最小离线任务；若必须选实现对象，则 a841，但应按多轮结构性
项目评估，不能当例行修复。

成本/风险：decoder 小但缺规范、需要从 CTL/code 反推（中风险）；GS 实现大（译器+host+ABI+验证），且 PSO/编译通过
不能证明语义或画面；无 GUEST 语义 oracle。TF/ClearColori 仍是独立风险，不把 GS 缺失归因 TF。

## 4 状态

- 六 GS 只读核对完成；3 条 vs→gs→ps、3 条 unknown program；几何字段 unknown（缺 decoder）。
- 文档：INDEX/EXPERIMENTS 加入 exp116（GS feasibility/evidence-only）；本报告；request 115 补 relay
  `codex-xc3-six-fout-batched-buildrun-8c07075643644718967ce331cfe4d23b` 与 `accepted:true`；request 116 原样归档
  （local id `xc3-gs-feasibility-116`；relay id 未提供 unknown）。
- HEAD `af094f4`；`git status` 仅既有未跟踪 `XC3-SETUP.md`；AGENTS.md/XC3-SETUP.md/共享 host/旧证据未动。
- 结束停 review，无后续自动授权。


---

## 5 追加更正（主管 review；原文保留）

- “没有可用 decoder 定义”错误：pinned Ryujinx `ShaderHeader.cs`（sha `0c8ba060…`）已定义 GetCode(address,0x50) 及
  Stage/GpPassthrough/StreamOutMask/ThreadsPerInputPrimitive/OutputTopology/MaxOutputVertexCount 字段；本轮已按该定义解码
  （见 report114）。
- “a841 1280 最小”错误：全六中 `ef6e` 256 最小、`95bf` 768 次之；a841 1280 不是最小，只是“已知接口失败”代表。
  实解字段与重新选择见 report114。
