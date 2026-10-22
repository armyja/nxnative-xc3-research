> **SUPERSEDED by report116（2026-10-22）**：本报告的 SASS 扫描使用了错误的 control 坐标（SPH-relative 而非
> SASS-relative），实际跳过了 sass0x10/0x30/0x50 等指令；下面的 OUT/ALD/AST/资源/结构结论全部作废。旧 TSV/fixture
> 保留为 bug 证据；修复见 report116。

# report115 · 95bf/a841 GS SASS 只读签名（pinned InstTable reflection）

日期：2026-10-22 03:00–03:25（本机）
HEAD `af094f470c43133016a899527b06a4c598677fce`（未变）；无 raw 译器/optimizer/SPIRV/MSL/Metal/library/host/guest/gate、无 repo/工具/lock/profile/facts 改动、无提交。
证据：`/path/to/external-drive/xc3/work/experiments/gs-sass-decode/`

---

## 0 更正

- report114/callgraph 的 DLL 身份按已核锁改为 `Ryujinx.Graphics.Shader.dll 011c50cb1c08e44f`，不再留问号。
- `ef6e` 的 `GpPassthrough=1` 只表示该 feature 位，不能据此称“不可修改输出/可省略 GS”；实际控制/输出仍未分析。
- report113 的“无 decoder 定义/ a841 最小”更正仍有效（report114 §0）。

## 1 helper 与解码路径

- SSD 小 C# helper（`GsSassDecode.csproj/Program.cs`）引用现有 pinned DLL，反射调用
  `InstTable.GetOp(ulong,ulong)`（pinned `InstTable.cs` line 380）；不调用 Emit/Translate。
- 按 pinned `Decoder.cs`：SASS 从 SPH+0x50 开始（dump 文件 offset 0x30+0x50=0x80）；每 32 字节在
  `address & 0x1f == 0` 处跳过 8 字节调度控制字；指令 8 字节。helper 从 address 0x50 起线性扫描，**线性扫描不是
  reachable CFG**。
- 构建/运行环境：`DOTNET_ROOT=/opt/homebrew/opt/dotnet/libexec`、net10 runtime；`build.log`/`fixtures.log` 保存。
  fixture 独立常量验证 ALD/AST/OUTR 字段、谓词与调度边界（`--fixtures` 全 ok）。

## 2 95bfab6122539993（code 768）

- 线性 60 行；pre-exit 41 行，其中 11 行 `Invalid`（未解/填充，保留 raw，不当指令）；有效：2 ALD、12 AST、3 OUT、1 EXIT。
- 输入：ALD Imm11 `0x70`/`0x78`（PositionX + 0x78），SrcB=4（primitive-vertex 索引来源寄存器）。
- 输出：AST Imm11 仅 `0x70/0x74/0x78/0x7c`（位置四个分量），**无 user attribute（>=0x80）写入**。
- OUT：0x178 Emit、0x1a8 Emit、0x1e8 Cut（3 个静态站点）；0x1f8 EXIT（Ccc=T，无条件）。
- 无 cbuf/纹理/SSBO/共享内存指令；无 branch/loop（除 EXIT 外无 BRA）。
- 静态 3 个 OUT ≠ 每输入 4 顶点；动态执行次数 unknown；输入 primitive unknown（runtime）。

## 3 a841a5d995c26b26（code 1280）

- 线性 108 行；42 行 `Invalid`（保留 raw）；有效：2 ALD、27 AST、3 OUT、1 自循环 BRA；**无 EXIT**。
- 输入：ALD `0x70`/`0x78`，SrcB=8（primitive-vertex 索引来源）。
- 输出：AST offsets `0x70,0x74,0x78,0x7c`（位置）、`0x80,0x84,0x90,0x94,0xa0,0xa4`（user attr0/1/2 的 x/y）。
  与 PS ef55 读 locn0/1/2 有对应线索，但 GS 实际控制流/是否每输入都写这些通道未证。
- OUT：0x358 Emit、0x3c8 Emit、0x3d8 Cut（3 静态站点，位于循环内）；0x3e8 BRA 目标 0x3e8（自循环，结束语义）。
- 无 cbuf/纹理/SSBO 指令；循环次数/动态 emit 数 unknown；输入 primitive unknown。

## 4 签名结论（只列已证/未知）

| 项 | 95bf | a841 |
|---|---|---|
| 读输入 attr | position 0x70/0x78 | position 0x70/0x78 |
| 写位置范围 | 0x70..0x7c | 0x70..0x7c |
| 写 user varying | 无 | 0x80/0x84, 0x90/0x94, 0xa0/0xa4 |
| cbuf/tex/SSBO | 无 | 无 |
| 静态 OUT 站点 | 3（Emit,Emit,Cut） | 3（Emit,Emit,Cut） |
| 结构 | 直线 + EXIT | 自循环 + 无 EXIT |
| 动态发射/输入 primitive | unknown | unknown |

- 不能由静态 3 OUT 推“每输入 3/4 顶点”；不能由 PS 无 user 输入推 GS 可省略；不能由默认 Triangles 当输入 primitive 真值。
- 95bf 的“点展开四边形”之类猜想没有证据，不写。

## 5 选择与下一步

- 95bf 是**更窄的真 GS 候选**：只写位置分量、无 user attr、直线+EXIT、无资源依赖；a841 写 3 个 user attr、循环且无 EXIT，
  语义更复杂但与已知接口失败对应。ef6e 仍是 GP passthrough 候选（feature 位，不等价）。
- 下一步最小缺值动作：确认 95bf 的真实输入 primitive/topology（wrapper 目前 `QueryGraphicsState` 默认 Triangles，未接
  runtime），并核对 3 个 OUT 的动态发射次数；在此之前不建议 raw GS 译器试验。若做单 key 诊断，仅 native SPIR-V 只读
  试验（未来授权），不改 guard/白名单。
- 成本/风险：SASS 字段解码已可复现；动态控制流/输入 topology 缺证据，GS 译器仍是结构性实现；不声称语义等价。

## 6 状态

- helper 源码/项目/构建/DLL SHA/输出/测试日志均在 SSD；原始 ctl/code 未改。
- 文档：INDEX/EXPERIMENTS 加入 exp118（GS SASS decode/evidence-only）；request 117 补 relay
  `codex-xc3-gs-pinned-header-analysis-e6f7c050244741be8620148a2c8a8dc1` 与 `accepted:true`；request 118 原样归档
  （local id `xc3-gs-sass-decode-118`；relay id 未提供 unknown）。
- HEAD `af094f4`；`git status` 仅既有未跟踪 `XC3-SETUP.md`；AGENTS.md/XC3-SETUP.md/共享 host/旧证据未动。
- 结束停 review，无后续自动实现/guest。


---

## 7 追加 SUPERSEDED 说明（主管 review）

- 证据：pinned `Translator.cs` HeaderSize0x50 → `Decoder.Decode(..., address+HeaderSize)`；Decoder 的 block.Address 从 0
  开始，control 判定 `(address & 0x1f)==0` 用 **SASS-relative** 偏移；取字节 `GetCode(startAddress+address)`。
- 本报告 helper 从 addr=0x50 起并按其 `%32` 跳过，误把 sass0x10/0x30/0x50 等指令当 control；SPH 0x60 的 S2r、
  SPH 0x80 的 Isberd 被丢弃，SPH0x70 的调度 word 被当 Invalid。旧 OUT 3/ALD 2/无资源/无分支等结论全部不可信。
- 修复后的结果见 report116；本报告旧表不再作为签名依据。
