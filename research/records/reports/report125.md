# report125 · 95bf GS `Translate(true)` asCompute 探针

日期：2026-10-22 05:00–05:30（本机）
HEAD `14082571ea0a1ea515be64b963e4f4d7c39a3097`（未变）；仅 SSD；无生产/lock/profile/facts/库/host/guard 改动、无 gate/guest/资源采样、无 commit。

---

## 0 结果

- 隔离 probe-only helper 构建 rc0；VS `d1657e5077b26d1d` 只 decode，未 Translate；GS `95bfab6122539993` 在
  `SetVertexOutputMapForGeometryAsCompute(vsCtx)` 之后 **一次** `gsCtx.Translate(asCompute:true)`；无 `Translate(other,true)`、
  无第二 Translate、无 FP64 fallback（`uses_float64=false`）。
- 成功输出 **GLCompute** SPV：`LocalSize=(32,32,1)`，22932 B，sha `41fb9c1a…`；LD/ST 359/269，`OpImageFetch=1`，
  `OpEmitVertex/OpEndPrimitive=0`（已降为 buffer 写）。
- 公开 `GetResourceReservations()`：cb 2、sb 3、tex 34；input/output words per invocation 各 **5**；binding 见下表。
- **发现一个未解的 descriptor 冲突**：`vb_info` 为 set0/b1，而原 95bf 纹理 `gp_t_tcb_8` 也是 **set0/b1**；两者是
  Uniform 与 sampled image。当前 SPIR-V 中存在同 set/binding 冲突，host/backend 如何重映射 unknown；不能称该 SPV 可直接上机。

## 1 输入/身份

- VS：`shd_post#92:0:0`，code area 256 B → SPH+instr 208 B，sha `5f68c1cf…`；stage bits=0(VS)；c1 空；job 空
  tex/img/attr/fout，debug/reduced 原值。
- GS：95bf SPH+instr 720 B，sha `4c64701b…`（code `.code` sha `a6f403ed…`）；c1 空；stage gs；job 同 report117。
- 两者 job JSON 已存；实验源码/project/build.log/binary/parser/SPV 全 hash（`identity.sha`）。
- 实验 helper 的新 Main 是 probe-only，不能当生产 wrapper；生产仍固定 Triangles/无 asCompute。

## 2 公开 reservations / 实际 SPV 声明

| 资源 | reservations | 实际 SPV 声明 |
|---|---|---|
| support_buffer | cb binding0（预留） | set0/b0，Uniform，struct |
| vb_info | cb binding1 | set0/b1，Uniform，Block struct（counts/strides/offsets） |
| gp_c3（原 cbuf） | — | set0/b2，Uniform |
| vertex_output | sb binding0 | **set1/b0**，Uniform pointer→struct{runtime_array f32}，ArrayStride4/Block |
| geometry_vb_output | sb binding1 | set1/b1，同 runtime f32 |
| geometry_ib_output | sb binding2 | set1/b2，runtime i32 |
| trb_data | texture binding1 | set2/b1，UniformConstant sampled_image(dim=Buffer) |
| gp_t_tcb_8（原纹理） | — | **set0/b1**（与 vb_info 冲突） |
| 原 texture | binding1/handle8/type3/array1 | 同上 |

- reserved counts：`ReservedConstantBuffers=2`（support+vb_info）、`ReservedStorageBuffers=3`、`ReservedTextures=34`
  （index0、trb1、vb_data2..33）；`InputSizePerInvocation=OutputSizePerInvocation=5` words（20 B）。
- 95bf output size 5 words 说明本次 asCompute IO usage 实际只含 Position4+PointSize1（不含 Clip/Cull 写入）；native SPV
  接口里声明的 Clip[8]/Cull[1] 不是本次 compute 输出布局的全部。不能把 native interface 当 compute ABI。
- `geometry_ib_output` 的 runtime array 元素在 SPIR-V 中打印为 i32；源码定义是 uint；是否 signed 仅影响签名，不改变
  buffer 布局，但如实记录。
- 实际 SPV 无 EmitVertex/EndPrimitive；有 1 次 `OpImageFetch`（trb_data），359 loads/269 stores；没有 image write。
  这说明 Emit/End 已被降级为 buffer 写，但**不证明** host 能消费这些 buffer。

## 3 与 native Points 的机制差异

- native Points：Geometry，InputPoints19/array1，OutputTriangleStrip/OutputVertices4，Emit4/End1，资源 cbuf3/tex8。
- asCompute：GLCompute，LocalSize32×32×1，input/output 5 words，set1 vertex/geometry buffers + set2 trb，Emit/End 消失，
  出现 359/269 LD/ST；原 cbuf3/tex8 仍在 set0。
- 这是两种执行模型/ABI，不是数值等价；asCompute 结果只说明编译期路径可走，不证明 host 布局、Metal 支持、dispatch、
  每 guest primitive 发射或 GPU 像素。

## 4 D：1/2 stage 请求

- 本轮证明了 **1 个 GS asCompute 请求 + VS decode（不 Translate）** 在隔离 helper 中可行；VS 只需 `_program.GetIoUsage()`。
- **2 个 Translate(true) 请求**（VS+GS）仍未验证：`Translate(other,true)` 无调用者，组合 ResourceManager/IO map 的契约
  未定；且上面 set0/b1 冲突说明资源布局尚不能直接交给 host。
- 下一次可定义 **1 个 GS asCompute raw 请求**（VS decode-only）作为结构探针；2 stage 请求需先解决 descriptor 冲突与
  组合预算，不应现在声称可定义。

## 5 文档/状态

- INDEX/EXPERIMENTS 加 exp129（asCompute probe/evidence-only）；report124 §6 已加两项勘误（trb长度别混、D 分层）。
- request 129 归档。
- HEAD `1408257`；`git status` 仅既有未跟踪 `XC3-SETUP.md`；AGENTS.md/XC3-SETUP.md/共享 host/旧证据未动。
- 45 分钟内完成；停止 review，无自动后续。


---

## 6 追加：allocator 因果限界与 2-stage 澄清

- set0/b1 冲突的直接原因是 probe 继承普通 wrapper 的 `_binding=1` 且所有动态资源 set0；asCompute 预留 support0/vb_info1 未告知
  allocator。它不是 pinned 库不支持 asCompute 的证据；也不能据此断言两个独立 stage 翻译不可定义。
- 修正 allocator（set0 从 2 起）后，GS 原纹理重分配到 set0/b2、原 cbuf 到 set0/b3；同 module 无重复 `(set,binding)`。
- 两次**独立** `Translate(true)`（VS 一次、GS 一次）已在本轮探针成功；这与 `Translate(other,true)` 的合并路径是不同实验，
  后者继续不碰、未验证。独立 module 同 `(set,binding)` 合法，host 仍需显式绑定/重绑，不能自动假定语义一致。
