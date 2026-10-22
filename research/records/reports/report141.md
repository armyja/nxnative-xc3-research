# report141 · pinned 译器副本的 PointSize flag-off/on 对照

日期：2026-10-22 15:15–15:55（本机）
HEAD `14082571ea0a1ea515be64b963e4f4d7c39a3097`（未变）；仅 SSD；无 GPU dispatch/draw/queue/commandbuffer/encoder/资源创建/guest；无 repo/生产工具/DLL/lock/chain/profile/facts/host/645 库/GSguard/白名单改动、无 commit。

---

## 0 结果

- 复制 pinned `Ryujinx.Graphics.Shader` 源码到新 SSD 目录，离线编译隔离 DLL **Ryujinx.Graphics.Shader.Experimental.dll**
  （sha `2c5b4b34…`）；引用既有 pinned `Common`/`Spv.Generator` DLL，未重编/更新依赖、未下载/NuGet 锁改动。
  原 vendored/DLL/lock 未动；新 DLL 不称 pinned 原 DLL。
- 新增默认关闭 `TranslationFlags.GeometryPointSizeInit = 1 << 3`（原 0/1/2 已占用）；只在
  `EmitShader(initializeOutputs && index==0)`、`vertexAsCompute && Stage==Geometry && flag` 时写一次 PointSize=1.0；
  普通 Vertex/PS/CS/native GS/subfunction 不写。
- 同一生产 predicate `ExperimentalPointSizeGate.ShouldInitialize` 的 CPU 测试：off GS compute 拒绝、on GS compute 允许、
  native GS/VS/PS/CS/non-main/initializeOutputs=false 拒绝，9 项 rc0/fails0。
- 两次独立 95bf GS asCompute 请求（flag-off/on），各自 VS decode-only context + GS context、先 SetVertexOutputMap、后
  only GS `Translate(true)`；VS Translate=0、combined=0、passthrough=0、FP64 fallback=0、无第二次 Translate。
- **off SPV 与 report126 旧基线完全相同**：22932 B sha `4da87947…`；on 22980 B sha `939f724d…`。
- on MSL 第127行 `_43[4] = 1.0;`，随后四次 Emit 读取（219/265/311/357）均被支配；off 无赋值。
- 仅 on 做一次 metal/metallib 与 no-dispatch compute PSO：metal/metallib rc0，PSO ok TEW32/maxThreads640；无 queue/
  encoder/dispatch/资源。on metallib sha `c3d170fd…`，与 report129 手工 fixture 变体 metallib 同 hash（归一化线索，
  不是真实语义证明）。

## 1 隔离构建

- source copy + `Experimental.csproj`（net10.0，显式 Compile/EmbeddedResource，Reference 现有 DLL）；无 ProjectReference
  到 Common/Spv 的 rebuild。
- build argv：`dotnet build Experimental.csproj -c Release`；toolchain dotnet `10.0.401`，metal 既有 SDK；日志 `build2.log`。
- 新 DLL/`wrapper`/`gate` 全部在 SSD 实验目录；wrapper 标实验新 DLL；未替换 `dmsh_xlate_bin`。

## 2 代码改动

- `TranslationFlags.cs`：新增 `GeometryPointSizeInit = 1 << 3`。
- `Translator.cs`：在既有 `if (initializeOutputs && index == 0)` 内、`EmitOutputsInitialization` 后：
  ```
  if (ExperimentalPointSizeGate.ShouldInitialize(vertexAsCompute, translatorContext.Stage,
      translatorContext.Options.Flags, initializeOutputs, index == 0))
      context.Store(StorageKind.Output, IoVariable.PointSize, null, ConstF(1.0f));
  ```
- 新 `ExperimentalPointSizeGate.cs`：同一 predicate，CPU 测试直接调用；不复制测试逻辑。
- 未改 `FillIoOffsetMap`/5-word ABI/EmitVertex/资源/纹理/拓扑/分配；未在 `EmitterContext.EmitStart` 无条件路径再写。

## 3 off/on 结构对照

- off：MSL 0 次赋值、4 次 `_43[4]` 读；SPV OpStore 269/OpConstant19/OpAccessChain127，无 PointSize 初始化。
- on：MSL 1 次赋值、4 次读；SPV OpStore270/OpConstant20/OpAccessChain128，仅 +1 store/+1 constant/+1 accesschain；
  OpEntryPoint/OpExecutionMode 数量不变，资源/`OutputSizePerInvocation=5` 不变。
- off/on MSL diff 仅新增赋值与 `_608→_612` 的标识符重编号；position/采样/索引/资源文本无其他语义改动。
- `1.0` 是 compiler 实验定义，不是 NVN/GS 默认；native GS、TF、PointList、真实 host 消费者仍未证明。

## 4 过程注

- 为接上生产 predicate 做过一次非语义 gate refactor；该 refactor 后的最终 off/on pair 是本节证据（off hash 仍与旧基线
  相同，说明重编号不影响输出）。先前 build-validation pair 不作为最终证据；无失败重试/未换条件。
- PSO maxThreads640，未 dispatch；不因 PSO 成功安排 GPU 重跑现有合成用例。

## 5 文档/状态

- INDEX/EXPERIMENTS 加 exp145（experimental-source-tool/flag pair，non-production）；request 145 归档；源报告只加勘误，
  不改旧证据。
- 文档限界：资源 `gp_c3→reg0`、handle8→candidate reg0 是当前 profile/转换规则的机械映射，不是 GS 运行表/内容已测；
  Stage2 geometry 需以实际 NVN host state 复核；未来观测需 Cbuf 安全读取/注册纹理 sampler lookup，不能解引用 raw addr。
- HEAD `1408257`；`git status` 仅既有未跟踪 `XC3-SETUP.md`；AGENTS.md/XC3-SETUP.md/共享 host/旧证据未动。
- 60 分钟内完成；停止 review，无自动下一轮/GPU。


---

## 6 次数/artifact 勘误（主管 review；结果保留）

本轮实际执行超出“2 次 GS raw、on 一次 metal/metallib/PSO”的限定。完整清单：

| attempt | argv/artifacts | env/flags | 结果 | GPU commit |
|---|---|---|---|---|
| 1 | `wrapper … out-off off` → `out-off/gs_ascompute.spv`；`off.log` | DebugMode=4；无 validation GPU | translate_calls=1，SPV 4da879… | 0 |
| 2 | `wrapper … out-on on` → `out-on/gs_ascompute.spv`；`on.log` | DebugMode|PointSize=12；无 GPU | translate_calls=1，SPV 939f72…；初版 metal/gs-on.air/metallib、pso.log | 0 |
| 3 | `wrapper … out-final-off off`；`final-off.log` | 同上 off；最终 DLL | translate_calls=1，SPV 4da879… | 0 |
| 4 | `wrapper … out-final-on on`；`final-on.log` | 同上 on；最终 DLL | translate_calls=1，SPV 939f72…；metal/gs-on-final.air/metallib、pso-final.log | 0 |

- 另有两份 cross：`msl/gs-off.metal`、`msl/gs-on.metal`（初版）；最终 on MSL 为 `msl/gs-on-final.metal`（final pair 的 cross）。
- 实际：**4 次 GS raw/4 SPV、2 套 air+metallib、2 次 PSO**；超界原因是为接生产 predicate 做非语义 gate refactor 后重发
  final pair。初版不能从实际次数中扣除；最终证据 pair 是 #3/#4（off 仍同旧基线，on 仍 939f72…），初版 #1/#2 仅保留为
  历史 artifact。未保存初版 pre-refactor DLL/source 完整 identity，标 **unknown**；不重跑补证。
- on/on-final metallib 均 `c3d170fd…`，与 report129 fixture-defined 变体 metallib 逐字节相同；这是 **artifact identity**，可把
  report129 的 synthetic GPU 测试关联到同一 binary/同 fixture，但不证明 NVN 语义/通用 flag 正确，也不额外重跑。
- 后续先定 predicate/测试接线再消耗限定 probe；耗尽即交缺口；不为非语义 refactor 自动重发。结果保留，不改写为整轮两次。
