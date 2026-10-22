# report128 · 95bf asCompute 执行前缺值：PointSize/word4、fixture 与 1024-gid 边界

日期：2026-10-22 06:30–06:55（本机）
HEAD `14082571ea0a1ea515be64b963e4f4d7c39a3097`（未变）；仅 SSD 只读/CPU 逻辑；无 GPU/Metal 执行/翻译/build、无生产/lock/profile/facts/库/guard 改动、无 gate/guest/资源采样、无 commit。

---

## A. `_43[4]` 与 PointSize

- `gs.metal`：`spvUnsafeArray<float, 5> _43;` 在 `main0` 入口声明；全文 **0 次写** `_43[4]`，4 次读：
  - 行 218 `_241=_43[4]`，行 264 `_309`，行 310 `_377`，行 356 `_445`；均在 Emit 前复制到
    `geometry_vb_output` 的 word4。`check_undef.log`：`UNINITIALIZED before first use`。
- 对照 `vs.metal`：`_30[4] = 1.0;` 显式初始化 PointSize，再写 `vertex_output` word4。这是 VS 路径，不是 GS 输出。
- 来源链：
  - `ResourceReservations.FillIoOffsetMap` 对 Input/Output 都先加入 Position4 + **PointSize**（`ResourceReservations.cs:103`），
    因此 GS output size 为 5 words；`OutputSizePerInvocation=5`。
  - `EmitterContext.EmitStart`（`EmitterContext.cs:88`）只在 `Stage == Vertex` 写默认 PointSize；GS/`Translate(true)` 不走该分支。
  - 95bf SASS（report116/125）AST 只写位置 `0x70..0x7c`，没有 PointSize 的 AST 偏移；native GS SPV 声明了
    BuiltIn PointSize，但 SASS 没有对应写入。
- 结论：当前 asCompute GS 的 word4 是**未初始化读**，不是“已知默认 1”。它只进入 geometry_vb 的第 5 word；本 fixture 的
  position 0..3、index/地址/emit 计数不依赖该 word，但未定义行为不能靠“只影响非位置 word”自动视为可安全 dispatch。
- 修复选点（仅评估）：在 GS asCompute 路径为 output PointSize 提供显式初始化（或在 translator 中按 stage 处理），或者
  在生成 layout 时证明该 word 不被 host/后续消费者使用；不能手改 MSL/掩码忽略。native GS 是否也未初始化、PS 是否完全不读，
  需另证；本轮不把 native 当安全依据。

## B. 未来最小 standalone fixture（设计，不执行）

### B.1 `vb_info` 1056 B（显式 fixture 值，字段语义仍是假设）

| 偏移 | 字段 | fixture 值 | 说明 |
|---|---|---|---|
| 0 | `_m0` vertex_counts | `(1,1,0,0)` | x/y guard；z/w 本 fixture 不用 |
| 16 | `_m1` geometry_counts | `(1,0,0,0)` | GS x guard=`_m1.x` |
| 32 | `_m2[0]` stride/aux | `(4,0,0,0)` | VS path 用；GS 不用 |
| 544 | `_m3[0]` offset/aux | `(0,0,0,0)` | VS path 用；GS 不用 |

- 该表是 fixture 的**明确假设**，不是已证的 host 字段语义；`_m0.y`、`_m1` 等分量含义仍 unknown。

### B.2 输入资源

- `trb_data`：`texture_buffer<float>`，1 项；fixture 值 `0.0f`（bit pattern 0），GS `read(gid.x)` 得到 uint 0。
- `ib_data`/`vb_data0`：`texture_buffer<float>`；fixture 的 IB 用 float 承载 uint bits；VS 路径按 `.x` + `as_type<int>` 读取。
- 原纹理：1×1 常量 `(0.5,0.5,0.5,1.0)`，显式 nearest/clamp sampler；GS 采样坐标
  `(x*0.5+0.5, y*-0.5+0.5)`（x=1,y=2 → (1.0,-0.5)，1×1 clamp 得 0.5）。
- `gp_c3`：声明 `float4[4096]`；本次 MSL 实际只访问 `[0].x`/`[0].y`（字节 0..7）。fixture cbuf3[0]=(2.0,0.5,0,0)，
  其余按声明分配/清零；不能把“只读 0..7”当完整 cbuf 语义。
- `vertex_output`：fixture 直接提供 1 个顶点 5 words `(1.0,2.0,3.0,4.0,1.0)`；word4 是 VS 的 PointSize，GS 不读它。

### B.3 CPU oracle（独立代数，不逐行抄 MSL）

sample=0.5，cbuf=(2.0,0.5)，输入 `(x,y,z,w)=(1,2,3,4)`：
[Fenced excerpt omitted from the shareable research record.]
- 常数均为二进制精确值，float32/FMA 顺序仍按 MSL 实际；oracle 只到代数/tolerance 层，不是执行器。
- `fixture_oracle.log` 输出以上值；仅设计/CPU，未创建 GPU 资源。

## C. 1024-gid 枚举与边界

- `enumerate_gids.py`：32×32×1 = 1024 gids；按 fixture `_m0.y=1`、`_m1.x=1` 只有 **1 个 active** `(0,0,0)`；
  1023 个 early-return。
- active gid 访问：
  - `trb_data` index0；
  - GS IB 写偏移 0..3（4 Emit）+ 4（EndPrimitive = -1/0xffffffff），共 5 words；
  - GS VB 写偏移 0..19（4×5 words），word4 来自未初始化 `_43[4]`；
  - VS（若未来执行）word 输出 5/顶点，但本 fixture 不跑 VS；GS 只读 `vertex_output[0..3]`（word4 不读）。
- z 只有 0；MSL 没有 z guard，索引式含 `+z*5`/`+z*4`；dispatch 必须是 z=1，否则会扩写，不能推广多 z。
- 无资源别名：set1 的 vertex_output/geometry_vb/geometry_ib 是三个独立 buffer；IB 用 uint，-1 位型 0xffffffff。
- `geometry_ib` 5 words 足够本 fixture；host 仍要按实际 maxV/threads 分配更大空间。

## D. 执行前 checklist / 能否定义 standalone dispatch

**暂不能定义。** blocker：
1. `_43[4]` 未初始化（PointSize）；未证明可安全忽略；不得设 1 冒充已知。
2. `vb_info` 字段语义（component 含义/stride/offset）仍未由 host 契约证明；fixture 的 `(1,1,0,0)` 只是假设。
3. `trb_data`/`ib_data`/`vb_data0` 的 bitcast 规则、纹理尺寸、sampler、cbuf 范围只做了 fixture 设计，未用真实资源验证。
4. 无 host argument-buffer 编码、buffer 长度、dispatch/indirect/sync；PSO 通过不等于可 dispatch。
5. 无 spirv-val/GPU 证据。

下一步最小验证（未执行）：先修复/证明 PointSize word 的初始化语义；再用纯 CPU fixture 校验 index/guard；最后才讨论 1-point/1-instance standalone dispatch。不派生自动修复/执行。

## 文档/状态

- INDEX/EXPERIMENTS 加 exp132（execution-prep/evidence-only）；request 132 归档。
- report127 的 PSO 成功依据仍是日志 `pso=ok`，不以 rc 作为 oracle；本轮不重跑 PSO。
- HEAD `1408257`；`git status` 仅既有未跟踪 `XC3-SETUP.md`；AGENTS.md/XC3-SETUP.md/共享 host/旧证据未动。
- 45 分钟内完成；停止 review，无自动后续。


---

## E. 范围限界（主管 review；原文保留）

- B 直接提供 `vertex_output`，**没有贯通 VS kernel**；`m2[0]=(4,0,0,0)` 关闭了 y/z/w 分量语义，若执行现 VS 不会得到
  `(1,2,3,4,1)`。这是 **GS-only fixture 设计**，不是已完成的 VS→GS fixture。
- `enumerate_gids.py` 只按 GS guard 且固定 base=0 枚举，适用于该单点，不是两个 kernel 全部访问域证明。
- 现 `fixture_oracle` 的 position/index 是 GS-only 代数预期；PointSize=1 是 synthetic 测试假设，不是 NVN/GS 真实默认。
