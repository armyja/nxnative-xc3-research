# report117 · 95bf/a841 Texs/位置数据流 + 95bf native GS raw 探针

日期：2026-10-22 04:00–04:35（本机）
HEAD `af094f470c43133016a899527b06a4c598677fce`（未变）；无 raw译器/optimizer/SPIRV/Metal/host/library/guest/gate、无 repo/工具/lock/profile/facts 改动、无提交。
证据：`/path/to/external-drive/xc3/work/experiments/gs-sass-decode/`（A）、`.../gs-raw-probe/`（B）

---

## A. Texs 字段与位置数据流

- 修复后的 helper 逐条解出 `InstTexs`（pinned `InstDecoders.cs:4873`）：
  - 95bf word `0xd820008ff0270102`：**Dest=2, SrcA=1, SrcB=2, TidB=8, Target=Texture2D, WMask=0, Dest2=255,
    Pred=7, PredInv=False**。
  - a841 word `0xd820008ff0570417`：**Dest=23, SrcA=4, SrcB=5, TidB=8, Target=Texture2D, WMask=0, Dest2=255,
    Pred=7, PredInv=False**。
- 坐标来源（pinned ALD/Ffma 位域 + 寄存器 def-use，非通用伪代码）：
  - 95bf：SrcA=r1=Ffma(ALD off 0x70, 常数) ; SrcB=r2=Ffma(ALD off 0x74, 常数)（r2 在 Texs 读取后被 Dest=2 覆盖）。
  - a841：SrcA=r4=Ffma(ALD off 0x70, 常数) ; SrcB=r5=Ffma(ALD off 0x74, 常数)。
- 四个 Emit 的位置依赖（AST 0x70/0x74 = Texs 结果经 Ffma + cbuf3 常数；0x78/0x7c = ALD 直接）：
  - 95bf Emit0-3：`x=Ffma(TexsDest2, cbuf3[0])`、`y=Ffma(TexsDest2, cbuf3[1])`；z/w 来自 ALD 0x78/0x7c。
  - a841 Emit0-3：同样 x/y 依赖 Texs Dest23 + cbuf3；z/w 来自 ALD。
  - 4 个 Emit 均 Pred=7（PT）、不反转；位置 AST 在每次 Emit 前写入，静态 4 次发射可证（正常 invocation 从入口到 Exit），
    但**每输入 primitive 的 invocation 数/真实 input topology 仍未测**。
- a841 user attr0/1/2（0x80/0x84、0x90/0x94、0xa0/0xa4）的依赖图**不含 Texs**（来自其它寄存器/ALD），只列已证部分。
- 纹理句柄：`TidB=8`；raw probe `.res.json` 同时给出 texture binding1/handle8/type3/array1，cbuf binding2/slot3；
  没有实测 NVN slot/base，**word vs byte/绑定表基址 unknown**；不把 TidB 当 NVN slot。

## B. 95bf native GS raw 探针（唯一一次）

- 输入：原 ctl/code 复制到 SSD，按 `job_for` 剥 packaging 0x30 得 SPH+instr（720 B，code sha
  `a6f403edc3eb169699cb8de95c0e725b631c68cdc2ac38f12f5393ed944c7e01`，sph sha `4c64701b…`）；c1 空；stage 字符串
  **gs**（不伪装 vs/cs）；tex/img/attr/fout 空；debug/reduced 默认。
- 调用现有 pinned binary `dmsh_xlate`（sha `69b0f8c7…`；wrapper Program.cs sha `027e9d79…`；lock `3fd3b3f6…`，
  Shader DLL `011c50cb1c08e44f`）一次：**rc=0, 1 ok, 0 failed**；job/argv/env/stdout/stderr 已留档。
- SPV（4360 B，sha `e50cf60d…`）：
  - `OpEntryPoint` ExecutionModel **3 Geometry**，name `main`。
  - ExecutionMode raw：**Triangles(22)**, Invocations(0)=1, **OutputTriangleStrip(29)**, **OutputVertices(26)=4**。
  - **4× OpEmitVertex，1× OpEndPrimitive**；interface IDs 33/37（Location/BuiltIn 未解，unknown）。
  - res：cbuf slot3/binding2；texture binding1/handle8/type3/array1；无 sbuf/image。
- **诊断假设**：wrapper `QueryGraphicsState` 默认 `InputTopology.Triangles`，生成 SPV 的 Triangles 不是真实 guest topology；
  未调用 asCompute；native Geometry SPV 不是 Metal 执行路径，不能上机。
- 与 SASS 签名对照：SASS 4 ALD/4 Emit+Cut/Texs ↔ SPV OutputVertices4/OutputTriangleStrip/4 Emit/1 End，**结构一致**；
  输入 topology 是默认假设，不是一致证据；interface 名称仍 unknown。

## C. 下一最小缺值

1. 真实 input topology / 每输入 invocation 数（目前 wrapper 默认 Triangles，需运行观测或可信 query；不猜）。
2. 纹理 handle 的 cbuf bank/word-byte 与 NVN slot（TidB=8 只是 handle；无 base 证据）。
3. SPV interface 33/37 的 Location/BuiltIn 解码（本机无工具安装，保留 unknown）。

不建议直接做 GS 生产实现；若继续，优先设计“真实 topology 观测 + 单 key raw 诊断”的离线/受控验证，而非扩白名单/忽略 GS。
TF/ClearColori 仍独立风险。

## D. 文档/状态

- INDEX/EXPERIMENTS 加入 exp120（Texs/dataflow + raw probe/evidence-only）；旧 bug TSV、report116 修复表保留；新表
  `*.dataflow.sass.tsv`、probe job/spv/res 不覆盖旧文件。
- request 119 补 relay `codex-xc3-gs-sass-address-fix-9199d596299e4ce988fc381c4fa53fe6` 与 `accepted:true`；
  request 120 原样归档（local id `xc3-gs-texs-raw-120`；relay id 未提供 unknown）。
- HEAD `af094f4`；`git status` 仅既有未跟踪 `XC3-SETUP.md`；AGENTS.md/XC3-SETUP.md/共享 host/旧证据未动。
- 结束停 review，无后续自动实现/guest。


---

## E. dataflow 限界更正（主管 review）

- 当前 `dataflow.py` 只找最近 Dest、递归 SrcA/B/C，**不完整建模 predicated 写入合流/多分量 register 写入/全 CFG**；
  `Mov` 分支只记说明不递归源。因此“a841 userattr 不依赖 Texs”应改为“该简化回溯已追踪路径未见；未证明全路径无依赖”。
- 正向已确认路径（Texs→Ffma→位置 AST/Emit）可引用；4 PT Emit + 无前置控制分支可限定正常 invocation 的发射数，不扩大
  每输入 primitive 解释。
