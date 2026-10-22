# report116 · SASS 坐标修复与 95bf/a841 重解码

日期：2026-10-22 03:30–03:55（本机）
HEAD `af094f470c43133016a899527b06a4c598677fce`（未变）；无 raw译器/optimizer/SPIRV/MSL/Metal/host/library/guest/gate、无 repo/工具/lock/profile/facts 改动、无提交。
证据：`/path/to/external-drive/xc3/work/experiments/gs-sass-decode/`（旧 bug 文件保留）

---

## 0 结论先行

- 旧 helper 用 SPH-relative 地址做 control 判定，**漏掉 sass0x10/0x30/0x50/0x70/0x90 等指令**（S2r/Isberd 等），并把
  sass0x20/0x40/0x60 等 control word 解成 Invalid。report115 的签名结论 **SUPERSEDED**。
- 修复后：**pre-exit 区域没有 Invalid**；95bf/a841 都是 4 个 ALD、4 个 Emit + 1 Cut、1 个 Exit、1 个 Texs；
  95bf 只写位置，a841 还写 user attr0/1/2 的 x/y；静态 4 个 Emit 与 header maxv=4 一致，但动态/输入 topology 仍 unknown。

## 1 坐标与 fixture

- 三坐标：`sass_rel` 从 0；`sph_rel=0x50+sass_rel`；`dump=0x30+sph_rel=0x80+sass_rel`。
- control 只在 `sass_rel % 0x20 == 0` 跳过；首条真正 instruction 是 `sass_rel=8`（SPH 0x58，dump 0x88）。
- 旧 bug 规则（SPH 0x60 被当 control）在 fixture 中明确保留为反例；修复后：
  - sass0x00/0x20/0x40 control；sass0x10（SPH0x60）S2r；sass0x30（SPH0x80）Isberd。
  - 端到端 fixture：同一份 raw 中 control/instruction 槽分别放置，helper 输出按三列地址与 type 正确区分；旧规则会把
    sass0x10 当 control（fixture 断言该旧行为为反例）。
- fixture/字段测试 `fixtures.fixed.log` 全 ok；旧 `fixtures.log`、旧 `95bf.sass.tsv`/`a841.sass.tsv` 保留。

## 2 修复前后 counts

| | 95bf 旧 | 95bf 修复 | a841 旧 | a841 修复 |
|---|---|---|---|---|
| 线性行 | 60 | 80 | 108 | 144 |
| control 行 | 0（误并入） | 20 | 0 | 36 |
| pre-exit instr | 41 | **40** | 108 | **86** |
| pre-exit Invalid | 11 | **0** | 42 | **0** |
| post-exit 线性 | — | 20 行（含 18 零/padding + Bra） | — | 22 行 |
| ALD | 2 | **4** | 2 | **4** |
| AST | 12 | **16** | 27 | **40** |
| OUT | 3 | **5（4 Emit + 1 Cut）** | 3 | **5（4 Emit + 1 Cut）** |
| S2r / Isberd | 0 / 0 | 1 / 1 | 0 / 0 | 1 / 1 |
| Texs | 0 | **1** | 0 | **1** |

- 旧 “Invalid 18/42” 中大部分其实是 control word；修复后 pre-exit Invalid=0；post-exit 的零 word 只是线性尾部，不能
  当指令、也不能据此称资源/分支缺失。

## 3 修复后签名

### 95bfab6122539993
- S2r sass0x10（Dest1 SReg=InvocationInfo）→ Isberd sass0x30（Dest4 SrcA0 IBase0）→ ALD SrcB=4。
- ALD 4 条 offset `0x70/0x74/0x78/0x7c`（position 四分量）；AST 16 条同样只写 `0x70..0x7c`；**无 user attr**。
- OUT：Emit at 0xf0/0x128/0x158/0x190，Cut 0x198（共 5）；Exit 0x1a8（Pred7/Ccc=T，无条件）；0x1b0 Bra 自环在 Exit 后
  的线性尾部（不据此称主体循环）。
- Texs 1 条（sass0x70，raw 0xd820008ff0270102）：存在纹理指令依赖，binding/采样坐标未解（unknown）。
- 无 cbuf/SSBO/共享内存指令；无 pre-exit 分支。

### a841a5d995c26b26
- S2r sass0x10 → Isberd sass0x30（Dest8）→ ALD SrcB=8。
- ALD 4 条 `0x70..0x7c`；AST 40 条：位置 `0x70..0x7c` + user attr0/1/2 的 x/y（`0x80/0x84,0x90/0x94,0xa0/0xa4`）。
- OUT：Emit 0x210/0x290/0x308/0x378，Cut 0x388；Exit 0x390；0x398 Bra 自环（post-exit 线性尾部）。
- Texs 1 条（sass0x70）；无 cbuf/SSBO/共享内存；无 pre-exit 分支/循环。

## 4 修正后的比较/下一步

- 两者都是 **4 个 ALD position + 4 Emit + 1 Cut**；静态 4 Emit 与 header maxv=4 一致，但这不是“每输入固定 4 顶点”的
  证明；input primitive/topology 仍 unknown（wrapper 默认 Triangles，不能当真值），动态执行次数 unknown。
- 95bf 更窄：只写位置、无 user varying；a841 写 3 个 user attr（与 PS locn0/1/2 有对应线索）但输出更多。
- 两者都有 1 条 Texs，纹理依赖不能忽略；其 binding/坐标未解。
- **report114 基于旧 SASS 的“95bf 无资源/直线”选择撤回**；SPH 表仍有效（stage=GS、topo=TriangleStrip、maxv4/ef6e 1）。
- 下一最小动作：解 Texs 的 binding/采样语义 + 确认真实 input topology（95bf/a841 各一条），再决定是否做单 key raw GS
  诊断；本轮不实现。

## 5 文档与状态

- report115 已加 SUPERSEDED 说明；report114 §7 撤回 SASS 相关选择；旧 TSV/fixture 保留为 bug 证据。
- INDEX/EXPERIMENTS 加入 exp119（SASS coordinate fix/evidence-only）；request 118 补 relay
  `codex-xc3-gs-sass-signatures-7ca5f7abe63948a08c94876db7a8c616` 与 `accepted:true`；request 119 原样归档
  （local id `xc3-gs-sass-fix-119`；relay id 未提供 unknown）。
- HEAD `af094f4`；`git status` 仅既有未跟踪 `XC3-SETUP.md`；AGENTS.md/XC3-SETUP.md/共享 host/旧证据未动。
- 结束停 review，无后续自动实现/guest。
