# report91 · SBuf `flags` ABI 与写权限误判：pinned enum 证据、45 sbuf 全量交叉表、host 影响范围、最小修复建议

日期：2026-10-21 22:35–22:50（本机）
证据目录：`/path/to/external-drive/xc3/work/experiments/ssbo-flagsabi/`
HEAD `cac7c6f`；本轮无代码/库/lock/host 变更、无 guest、无 commit。

---

## 0 结论摘要

1. **pinned ABI 已确认**：`Program.cs:143` 把 `p.Info.SBuffers[i].Flags` 直接 `(int)` 序列化；该属性类型是 `BufferUsageFlags`（`[Flags] enum : byte`），**`Write = 1 << 0`**（仓库内 vendored Ryujinx 1.3.2 源码；DLL sha256 与 lock 的 sha16 一致）。
2. **`dmsh_build.py:369` 的 `flags & 2` 是错的位**：应看 bit0（`flags & 1`）。当前 45 条 sbuf 的 `rw` 全部为 false。
3. **45 条 sbuf 全量交叉表**：`flags=1` 恰 7 条（6 VS + 1 PS），全部是非 const `device` 指针且有 store/atomic；`flags=0` 恰 38 条，全部 `const device` 且 0 store/atomic。分离完全一致，无例外。
4. **`8c8d676f2d2bab80` 是直接写者**：MSL 第 30–33 行四次 store（`_m0[0..3]`），而 response `flags=1` 被误读成 `rw=false`。候选库/host 因此**不能**用于新的 PS guest 观测。
5. **host 影响范围比字面小，但风险真实**：`rw` 在 host 的两处消费是（a）`USE(...)` 的 usage 参数——`USE` 宏当前 `(void)(u)`，`res_check` 也不使用 usage，且全文件没有 `useResource:` 调用（驻留用 `MTLResidencySet`），所以今天不改变 Metal 权限；（b）`rt_range_bindings_ro` 的 RO 准入——它额外要求 `msl_type` 以 `const device ` 开头，而 7 个写者都是非 const，因此即使 rw 错也不会被误准入；`rt_range` 默认关闭（`DM_NVN_RT_RANGE=1` 才开）。其余消费是 `[sbuf-final] rw=` 与 `B … rw/ro` 日志。**元数据仍然是错的**，且 `USE` 的 usage 是潜在路径。
6. **最小修复**：`dmsh_build.py:369` 改成 `flags & 1`。该文件在 `dmsh_chain.FILES` 中，改动会生成新 chain、需要 fresh CAS/out 重建与 host 重建；**未获单独授权前不改**，也不允许手改 JSON/旧库冒充新链。回归期望：chain + 恰好 7 条 rw 翻转，MSL/metallib 645/645 不变，sbuf reg/tex/samp/img/drv 不变。

---

## 1 pinned ABI 证据（源码 + 元数据，无需 helper）

序列化点：

[Fenced excerpt omitted from the shareable research record.]

类型链：

[Fenced excerpt omitted from the shareable research record.]

语义（译器自己怎么置位）：

[Fenced excerpt omitted from the shareable research record.]

即：**bit0 = 该 slot 被写过**；`None=0`，没有其它位。

pinned 一致性：

| 项 | 值 |
|---|---|
| `Ryujinx.Graphics.Shader.dll` sha256 | `011c50cb1c08e44fa2a5d65fafe58d1e482c70c4f5c77f51a920083a3055449c`（前缀 `011c50cb1c08e44f` = `dmsh_chain.lock` 的 sha16） |
| `dmsh_xlate.dll` sha256 | `a7f696bb0dbf1ac0ea4044ab18d261be2dbe4b0321903da6e2ef4f977924d678` |
| `BufferUsageFlags.cs` sha256 | `e02fbe338d658331ddccd46181c65f9cb6b1c89043c8fd027795cc18641e233f` |
| `BufferDescriptor.cs` sha256 | `db6e5f75da8cba2b911a54a48e8b7ce7e9842a715c0c3d88c684dbf36a6c0c16` |
| `ResourceManager.cs` sha256 | `35f9da40216adcad512d49b00ed329e03d10c421a5ab10459808daa2902f2620` |
| `ShaderProgramInfo.cs` sha256 | `d687002287b46240375a234dea9275980fb6566955c27696db6254748f737668` |
| `dmsh_xlate/Program.cs` sha256 | `027e9d79a7f9b54b76c3c0dd080c1d325fd471f913ce13b5b209218e0b77427a` |
| 源码 / DLL mtime | 均 `2026-10-21 00:35:24`；`dm/third_party/ryujinx/README.md`：vendored Ryujinx 1.3.2 子集 |

- 仓库内有源码，因此**没有**编译 reflection helper、没有 `dotnet` 调用、没有安装/联网，也没有动 lock。
- 观察到的 response `flags` 只有 0 与 1 两种值，与 `Write=1` 的定义一致。

---

## 2 45 条 sbuf 全量交叉表（report82 的 27 res，覆盖库内全部 45 sbuf）

全表在 `ssbo-flagsabi/cross_tab.txt`；判据：

- `flags`：res.json `sbufs[].flags`（不是 `index`/`binding`/`slot`，也不是 `buffer0..indices`）；
- `const`：由 `_b.metal` 的参数声明 `(const )?device T* <msl_name> [[id(` 判定；
- `stores` / `atomics`：对该参数名的 `(*spvDescriptorSet0.<name>)._m0[...] =` 赋值（排除 `==`）与 `atomic_` 调用计数。

| 类别 | 数量 | const | store>0 | atomic>0 | 结论 |
|---|---|---|---|---|---|
| `flags=1` | **7** | 0 | 6 | 2（其一仅 atomic） | 全部是写者 |
| `flags=0` | **38** | 38 | 0 | 0 | 全部只读 |

- `flags=0` 中非 const 的：0 条；`flags=1` 中 const 的：0 条。
- 45 条 = 库内全部 sbuf（645 keys 总计 45 条），所以“受影响的写者”就是这 7 条，没有遗漏。

### 2.1 7 条写者明细（MSL 原文）

| key | stage | binding | cb_offset | 候选 reg | MSL 声明 | store/atomic |
|---|---|---|---|---|---|---|
| `0871803a7d1236e8` | vs | 1 | 68 (0x110) | 0 | `device _47* vp_s0 [[id(14)]];`（L44） | 30 stores（首条 L744） |
| `122eece754abf575` | vs | 1 | 68 (0x110) | 0 | `device _47* vp_s0 [[id(14)]];`（L44） | 30 stores（首条 L750） |
| `36710e69a07e849d` | vs | 2 | 68 (0x110) | 0 | `device _23* vp_s0 [[id(2)]];`（L32） | 24 stores（首条 L157） |
| `5f6491f9bda5ae4d` | vs | 2 | 68 (0x110) | 0 | `device _21* vp_s0 [[id(1)]];`（L35） | 1 atomic（L69，CAS） |
| `c0882609d8f91561` | vs | 3 | 68 (0x110) | 0 | `device _23* vp_s0 [[id(2)]];`（L36） | 2 stores + 1 atomic（L71/L377/L683） |
| `cea273f9f0936f5b` | vs | 1 | 76 (0x130) | 2 | `device _15* vp_s0 [[id(0)]];`（L25） | 8 stores（首条 L50） |
| `8c8d676f2d2bab80` | **ps** | 1 | 324 (0x510) | 0 | `device _15* fp_s0 [[id(0)]];`（L25） | **4 stores**（L30–33） |

`8c8d676f2d2bab80_b.metal` 第 25、30–33 行原文：

[Fenced excerpt omitted from the shareable research record.]

`5f6491f9bda5ae4d` 的写是原子 CAS（无普通 store）：

[Fenced excerpt omitted from the shareable research record.]

### 2.2 flags=0 的真只读对照（`9b770cf888d729bd`，即 report88 的目标 VS）

[Fenced excerpt omitted from the shareable research record.]

- 这说明“声明 `device` 指针”本身不等于写：`9b770` 是 `const device`，且只有 load；而 7 条写者都是非 const `device` 且有 store/atomic。
- MSL 的 `const` 与否是译器自己的 codegen 信号，与 `flags` 位完全同向；两者都可作为证据，但 `flags` 是 ABI 层、MSL 是代码层。

---

## 3 构建器侧的错位

`dmsh_build.py` 的 sbuf 映射（原文）：

[Fenced excerpt omitted from the shareable research record.]

- `flags` 是 `BufferUsageFlags` 的 `(int)`，`Write=1`；`flags & 2` 永远为 0（值只有 0/1），所以 **45 条全部 `rw=false`**，其中 7 条是真实写者。
- `nvn_refl.h:18` 对 `rw` 的定义更宽：`rw: storage buffer access is read_write / write / device`——即“未被证明只读”，不是单一 write 位；用位掩码时取 `Write=1` 才是源语义。
- 这**不是** `index`/`binding`/`slot` 的问题：`index` 只是 binding 排序后的位置，`flags` 是独立字段；`cb_offset`/`reg` 也不参与 rw。

---

## 4 host 里 `rw` 的消费与影响范围

| 位置 | 作用 | 是否受本次错误影响 |
|---|---|---|
| `nvn_refl.m:41` | `sbuf → r->rw = [b[@"rw"] boolValue]` | 读入错误值（7 条应为 1） |
| `nvn_refl.h:18` | `nvn_rbind.rw` 字段 | 同上 |
| `nvn_mtl.m:3908` | `USE(mb, b->rw ? Read\|Write : Read)` | 选择 usage，但被 `USE` 丢弃（见下） |
| `nvn_mtl.m:3779` | `#define USE(r,u) do { (void)(u); if (g_res_check_on) res_check(r, sh->key, reg); } while (0)` | `u` 被显式丢弃；`res_check` 只看驻留集合，不看 usage |
| 全文件 `useResource:` | **没有调用**；驻留通过 `MTLResidencySet`（`res_add` / `res_commit`） | 因此今天 Metal 权限/ hazard 声明不受该表达式影响 |
| `nvn_mtl.m:2821-2833` | `rt_range_bindings_ro`：要求每个 sbuf `rw` 为显式 false **且** `msl_type` 以 `const device ` 开头 | 7 条写者都是 `device`，即便 rw 错也被第二道 `const` 检查拒绝；`rt_range` 默认关（`DM_NVN_RT_RANGE=1` 才开） |
| `nvn_mtl.m:2796` | `if (rt_range_on()) o->range_ro = rt_range_bindings_ro(j);` | 同上，默认不执行 |
| `nvn_mtl.m:3163` | `image_write` 用的是 `NVN_RB_IMG` 的 rw | 不同 kind，不在本 scope |
| `nvn_mtl.m:3911` | `[sbuf-final] … rw=%d` | 会打印错误的 `rw=0` |
| `nvn_mtl.m:3917` | `B … sbufp … %s`（`rw`/`ro`） | 会打印错误的 `ro` |
| `dm/gfx/tests/t_refl.m:47` | 单测检查 JSON `rw` 解析 | 仅解析，不涉及构建器掩码 |

**结论（scope）**：
- 当前实际生效的差异：两条诊断字段打印错误（`[sbuf-final] rw=`、`B … rw/ro`）。
- 潜在风险：`USE` 的 usage 选择今天是死代码；一旦把 `USE` 接到真正的 `useResource:`（或有新的 hazard/权限消费者），7 条写者就会以只读 usage 提交；`rt_range` 的 RO 准入目前由 `const device` 二次保护，若将来放宽该检查，错误 rw 会误准入。
- 元数据本身必须修：JSON 的 `rw=false` 与真实 MSL 写入矛盾，任何按 rw 做权限/路由判断的代码都会被误导。

---

## 5 scope 核对：是否还有别的 flags

- 45 条 sbuf = 库内全部；`flags=1` 只有这 7 条（6 VS + 1 PS），没有第 8 条。
- `drvcb` / `ubo_ptr`（UBOP）：response 的 `cbufs` 只有 **binding/slot**，没有 flags；`ubo_ptr` 是构建器派生 kind，不带 flags。因此它们**不在**本 flags ABI 内，本轮不扩。
- `textures` / `images`：`TextureDescriptor.Flags` 是**另一个** `TextureUsageFlags` 枚举，Program.cs 亦 `(int)` 序列化，但与本 sbuf 的 `BufferUsageFlags` 无关；按指示不扩 tex/img。
- 其它 kind（c1/cbuf/support/drvcb）没有 flags 字段。

---

## 6 最小修复建议与回归方案（仅建议，未执行）

### 6.1 修复

[Fenced excerpt omitted from the shareable research record.]

（等价写法 `& (1 << 0)`；不要用 `!= 0` 之外的猜测位。`BufferUsageFlags` 当前只有 `Write=1`，没有其它位。）

### 6.2 变更代价（必须先单独授权）

- `dmsh_build.py` 在 `dmsh_chain.FILES` 里：改动会让 `dmsh_chain.version()` 变化 → 新 chain、需 `--header`、fresh CAS/out、重新构建 645、重建 host；旧库 `a0829f60e7af` 不能“补丁式”复用。
- 共享 chain/CAS：新 chain 只影响使用新 header 的 host/构建；但同一工具被所有 profile 使用，属于共享工具变更，需按主管流程单独授权与回归。
- **lock 不需要更新**（`dmsh_chain.lock` 锁的是 translator/spirv-cross/metal，不是 dmsh_build.py）；不要跑 `--update-lock`。
- **不能**手改 JSON 的 `rw` 或 chain 字段：host 会校验 chain 与 `b-<V>` 目录，CAS 键也绑定内容。

### 6.3 回归期望（离线即可验证）

1. 新 chain 与 header；fresh CAS/out；645 keys 一次构建 rc0。
2. 逐 JSON deep diff（相对当前候选库）：只有 `chain` 与**恰好 7** 条 `bindings[i].rw` false→true；`reg`、`index`、`arg_id`、tex/samp/img/drv_reads 等全部不变。
3. MSL/metallib **645/645 byte-identical**（rw 只进 JSON，不改 codegen）。
4. 7 条必须与 §2.1 的 7 个 `(key, index)` 完全一致；38 条保持 false。
5. 重编 host：新 chain 出现 1 次、旧 chain 0 次；`[sbuf-final]` 对 `8c8d676f2d2bab80` 预期 `rw=1`（仍需 guest 才能看到，且只证明编码期字段，不证明 GPU 执行）。
6. `t_refl.m` 解析测试仍通过（rw true 的 round-trip）。
7. 可选：给构建器加一个单元级断言（flags 位 ↔ rw），但这是代码改动，需另行授权。

---

## 7 限制与未证明

- 没有安装 SPIR-V 反汇编工具；本轮用 **MSL 明确访问文本**（store/atomic/const 声明）作为代码层证据，加上 res.json 的 flags 与 pinned 源码/枚举作为 ABI 层证据。两者独立且完全一致。
- 未执行 GPU/guest：不能证明这些写在 GPU 上真的发生，也不能证明 NVN 的真实 bind 权限；但 `8c8d676f2d2bab80` 的 4 次 store 是**直接写证据**，足以否定“只读”元数据。
- 7 条写者的 `flags=1` 来自 report82 已落盘的 res.json（相同 ctl/code/c1/job，译器确定性）；本轮没有重新翻译，也没有改库。
- `flags=0` 的“只读”是 MSL 的 const+无 store/atomic 证据，不是 GPU 观测。

---

## 8 产物与状态

| 文件 | sha256 |
|---|---|
| `ssbo-flagsabi/evidence.txt` | `199a41c8711207768f8da6f16b621d0267e4e90679d5b226a9ee2f16e77e9d49` |
| `ssbo-flagsabi/cross_tab.txt` | `bf013905c7eea606d17c1f10c2c37abf3bd473931df1ac31b6fee535503d87ec` |
| `ssbo-flagsabi/sbuf_scan.tsv` | `b996b9cfccbbfbee1484a8078c8665ecc9a9ed71600742f6e061f4e158681004` |

- HEAD `cac7c6f`；`git status --porcelain` 仅既有未跟踪 `?? XC3-SETUP.md`；无 tracked 改动、无 commit/push。
- 本轮未改代码/工具/lock/库/host；未启动 guest；未扩 tex/fout/GS/img。
- report90 已追加勘误：候选库/host“可编译”但写 shader 的 rw 元数据错误，暂不可用于新 PS guest 观测；旧 host 保留、不得由 ready launcher 自动运行。
