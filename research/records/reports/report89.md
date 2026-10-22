# report89 · 两个 PS program 的 NVSD 只读元数据，与 candidate PS base 0x510 / stride 16 的一致性

日期：2026-10-21 22:09–22:25（本机）
目录：`/path/to/external-drive/xc3/work/experiments/ssbo-ps-nvsd/`
HEAD `cac7c6f`，本轮无 tracked 改动、无 commit、无 push。

---

## 0 授权边界与本轮实际动作

- 只读离线：无 guest、无新 translator 请求、无 MSL/Metal/host/library 构建；仅按授权用缓存 registry 以 `cargo build --offline --locked` 编译了一个 NVSD metadata helper。
- 无 profile/base/facts/translator/lock/生产代码变更；未写 PS base 0x510；未扩 TEX27/GS/fout/其它 image；未加任何 guest 授权。
- 只读两个 program：`shd_post.wishp` slct146/program0、`shd_lgt.wishp` slct0/program17；第三个 program（`shd_layout.wishp` slct10/program2）**直接复用 report83 已落盘的输出**，未重新编译、未重新扫描。
- 不新增解析器：身份校验用的全是现有生产工具 `dm/gfx/tools/spch.py`（容器读取）与 `dm/gfx/tools/dmsh_refill.py`（key/stage/package 校验）；本目录的 `verify.py` 只是把两者与已落盘的 res.json/NVSD 文本拼在一起的胶水。
- 原有 profile 库、报告证据、`AGENTS.md`、`XC3-SETUP.md`、共享 `dmhost` 均未改动（见 §9）。

---

## 1 工具、容器与产物固定

### 1.1 helper（新目录内，离线编译）

| 项 | 值 |
|---|---|
| 源 | `ssbo-ps-nvsd/src/main.rs`，sha256 `44f9f41b43f1978d26e1933edec6689536ae693f29d91d60ccbc04b6f059a726` |
| Cargo.toml | sha256 `18e15e80950eb26cb1ffe18e6f0a8d4ac64b98cbb0a8a99a43b6e347fa75272d` |
| Cargo.lock | sha256 `27b1bc1212044ecfe531693597a2a646c4d2c1edccb5f6d8c7f8b7b0fa0efbde`（与 report83 的 pinned lock 前缀 `27b1bc1212044ecfe531` 相同，逐字节复制，无更新） |
| 依赖 | `xc3_lib 0.21.0`（`default-features=false`）、`binrw 0.15`、`anyhow 1`、`sha2 0.10`；全部来自 `/path/to/external-drive/xc3/proto/cargo-home` 缓存 |
| 构建 | `CARGO_HOME=/path/to/external-drive/xc3/proto/cargo-home cargo build --offline --locked`，rc 0；`build.log` sha256 `4aa46ba722b671783b38cbb5466c69e6fb9edc92c42be19b5619118b9db1ab9f` |
| 工具链 | cargo 1.99.1 (5f94df478 2026-08-27)、rustc 1.99.1 (58cf8f9c3 2026-10-13) |
| 产物 | `target/debug/spch_enum`，sha256 `56fa930b8a569ffc53164862488d2abe8d4ab5b5a252303e27f9910eaf9e4a99` |
| 读路径 | `Spch::read → slct_offsets[si].read_slct → programs[pi].read_nvsd`（与 report83 完全相同） |

运行（两次，rc 0，stderr 空）：

[Fenced excerpt omitted from the shareable research record.]

### 1.2 容器哈希

| 容器 | 字节 | sha256 |
|---|---|---|
| `shd_post.wishp` | 6,918,144 | `48b9098e6ca42241ce203b81a25d1218fd26115837ecb8744923ec6dea2d38fe` |
| `shd_lgt.wishp` | 6,139,904 | `bf512f79f8ec30da0a90aae1f325f3362054e368e34025abe89901c013c0b63a` |
| `shd_layout.wishp`（复用，未读） | 3,162,112 | 见 report83（sha 前缀 `6931c8e24b84e2a6fed915cc`） |

### 1.3 输出与胶水

| 文件 | 字节 | sha256 |
|---|---|---|
| `out_post.txt` | 925 | `75e5dd289e609b4df93252546cb661e15bf493bba4fa9cd28e884dabab20db06` |
| `out_lgt.txt` | 100,773 | `1f21b98cb8b54e32592a9f3098b2c8ae7a01689b8ef35fd6dc04882dabe29511` |
| `verify.py` | — | `4a2661e3ff809c50163da4a8bbfcdc3a3503590dc978f94a56fcc2769d63c968` |
| `analysis.txt` | — | `177248eb95a0eb0e19651065eac01ac489f68636c1534adaae2b63375ae34f38` |
| `identity.json` | — | `3409f7e63b204a85ac6b12ed25fb1f3da99ea658e889b8363bcff33431c100ff` |

复用的 report83 输出：`ssbo-nvsd-offset130/out.txt`，1,431 B，sha256 `62a3caa591fc95b69bd8ef0538b373a978ff280bce425414f004c2672b96416c`（本轮未重读容器、未重编译其 helper）。

---

## 2 身份校验（spch + code/ctl hash + 审计 package 唯一匹配）

方法（全部现有生产工具）：

1. 生产解析器 `spch.shaders()` 走完整容器：`shd_post` 1,953 个 entry（944 ps / 997 vs / 12 其它），`shd_lgt` 648 个（321 ps / 321 vs / 6 其它）；按 `#SPCH#si:pi:ei:stage` 取目标 entry。
2. `dmsh_refill.skey(ctl, code)` 由 control + code 重算 key，必须等于目标 key；`dmsh_refill.code_stage(code)` 必须由 code 自身声明 `ps`（不看长度）。
3. 审计 package 取 `shader_map.tsv` 行（`file/offset/stage/key/source`），`offset=0`；`dmsh_refill.package_verify(blob, key, 'ps')` 校验 header、长度、control+0x704、key 重算、code stage，返回 `None` 即通过。
4. package 记录内的 control 与 code 必须与容器 entry 的 control、code **逐字节相等**；容器中按 key 重算匹配的 entry 必须**恰好 1 个**。

### 2.1 原文（`analysis.txt` 前 11 行；`package_verify=None` 表示无错误）

[Fenced excerpt omitted from the shareable research record.]

`shader_map.tsv` 对应两行原文：

[Fenced excerpt omitted from the shareable research record.]

### 2.2 结论

- `8c8d676f2d2bab80` = `shd_post` 第 146 slct 第 0 program 的 **entry 1**，stage 由 code 自身声明为 `ps`；control 2176 B、code area 256 B；容器内 key 重算唯一匹配 1。
- `0104dd056a3b1902` = `shd_lgt` 第 0 slct 第 17 program 的 **entry 1**，stage `ps`；control 2176 B、code area 10496 B；唯一匹配 1。
- 两个 package 的 `offset=0` 记录与容器 entry 逐字节相同；`package_verify` 均通过。entry 号、stage、key 都来自实际字节，不是尺寸推断。
- 同一 program 的 sibling VS 在审计 map 中也有行：`vs_shd_post_s146p0.bin 0 vertex c013625738b470f1 shd_post#146:0:0:vs`、`vs_shd_lgt_s0p17.bin 0 vertex 9db0109f3850843d shd_lgt#0:17:0:vs`——佐证 entry 编号 0=VS、1=PS。本轮未读这两个 VS 的 NVSD（授权只含两个 PS program）。

---

## 3 NVSD 原文

### 3.1 `shd_post` slct146 program0（目标 PS `8c8d676f2d2bab80`）

`out_post.txt` 全文（16 行）：

[Fenced excerpt omitted from the shareable research record.]

- `buffers1_count=0`：没有 uniform buffer（没有 c0/drvcb 侧 buffer 条目）；`buffers2_count=1`：**恰好一个** storage buffer。
- 唯一 SB：`FlickerObject`，`handle=0`，`vis=Fragment`，`size=16`，`uniform_count=1`/`start=0`/`unk3=192`，成员 `o_flickerInfo@0`；`buffers2_indices=[0]`。
- shader 前缀链：entry0（同 program 的 VS，fx=256）→ entry1（PS，vx=256/fx=256），与 entry1 是 PS 的事实一致。

### 3.2 `shd_lgt` slct0 program17（目标 PS `0104dd056a3b1902`）

`out_lgt.txt` 头部与 buffer 级元数据（成员表共 1,846 行，全量在 `out_lgt.txt`）：

[Fenced excerpt omitted from the shareable research record.]

- UB（常量/驱动侧，与 sbuf 分开列）：`PntObj` handle1 size 12288（768 个 pointLights 成员）、`SptObj` handle2 size 16384（1024 个 spotLights 成员）、`U_BASE` handle0 size 640（`VertexFragment`，16 个成员：`invProj`、`gToonParm[0]`、`gSSAOParam`、`gLgtCol[0]` 等）；`buffers1_indices=[2, 0, 1]`。
- SB（storage）：`PointerList` handle0 size8（`offset/count`）、`U_Cluster` handle1 size48（`tileInfo/clusterDim/calcParams`）、`U_LightList` handle2 size1（`gLightList[0]`）；`buffers2_indices=[0, 1, 2]`。
- 注意：UB 的 handle 集合也是 `{0,1,2}`（顺序 1,2,0），与 SB 的 `{0,1,2}` 重叠（见 §6）。

---

## 4 原始 response（与 NVSD 分开列）

### 4.1 `8c8d676f2d2bab80`

[Fenced excerpt omitted from the shareable research record.]

`cb_offset` 单位是 word：324 × 4 = **0x510**；`flags=1`，按 builder 的 `rw = flags & 2` 规则仍为只读；无 cbuf、无 texture/image。

### 4.2 `0104dd056a3b1902`

[Fenced excerpt omitted from the shareable research record.]

即按 JSON 顺序：binding16 → 0x520、binding17 → 0x510、binding18 → 0x530；`slot` 是 0,1,2 的 **binding 顺序**，不是 offset 顺序。cbufs（常量/驱动侧）单独列在上一行，不与 sbuf 混算。

### 4.3 `16653b901bfc4560`（复用 report83 的 res.json 与 NVSD，未重读容器）

[Fenced excerpt omitted from the shareable research record.]

同 program 的 VS `ab5b6564e4add61c`：response `cb_offset=76`（0x130）、`slot=0`（report83 §4）。

### 4.4 明确未覆盖：`304f1f866df79c3a`

该 key 是 runtime-only（审计 package 为 `ps_runtime_…`，没有容器 program），其 response 的 5 个 sbuf offset 为 `0x510, 0x550, 0x540, 0x520, 0x530`（binding 9..13，slot 0..4）。本轮**没有**为它读任何 NVSD，也不扩其它 program 追答案；0x550 → candidate reg 4 只是算术，不是结论。

---

## 5 candidate PS base 0x510 + stride 16 会给哪些 reg

规则（与运行时同源）：`off = cb_offset*4`，`rel = off - 0x510`，当 `0 <= rel < 0x100` 且 `rel % 16 == 0` 时 `reg = rel / 16`。

| key | program | binding | off | res `slot` | cand reg | NVSD SB handles | reg 在 handle 集合内 |
|---|---|---|---|---|---|---|---|
| `8c8d676f2d2bab80` | post 146:0 | 1 | 0x510 | 0 | **0** | {0} | 是 |
| `0104dd056a3b1902` | lgt 0:17 | 17 | 0x510 | 1 | **0** | {0,1,2} | 是 |
| `0104dd056a3b1902` | lgt 0:17 | 16 | 0x520 | 0 | **1** | {0,1,2} | 是 |
| `0104dd056a3b1902` | lgt 0:17 | 18 | 0x530 | 2 | **2** | {0,1,2} | 是 |
| `16653b901bfc4560` | layout 10:2 | 2 | 0x510 | 0 | **0** | {0,1,2} | 是 |
| `16653b901bfc4560` | layout 10:2 | 3 | 0x520 | 1 | **1** | {0,1,2} | 是 |
| `ab5b6564e4add61c`（VS，复用） | layout 10:2 | 1 | 0x130 | 0 | **2**（vs base 0x110） | {0,1,2} | 是 |

- 全部 offset 都是 16 的整数倍，且 `rel` 都在 `[0, 0x100)` 内；没有出现越界或未对齐。
- **`slot` 不等于 candidate reg**：lgt 的 `slot=0,1,2` 与 reg `1,0,2` 不一致；post / layout 的 slot 与 reg 一致只是巧合（report82 已给出跨 key 的 slot 不一致反例）。因此本表只用 offset 推导，不用 slot。
- 条件性“钉住”base：若要求所有 binding 的 reg 都落在已声明 handle 编号内，则 lgt 的最高 offset 0x530 要求 `(0x530-b)/16 <= 2` → `b >= 0x510`，而可行窗口上限就是 0x510，故只能是 0x510；post 单条 0x510 且 handle 集合 {0} 同样只允许 0x510。layout 单独不能钉住（base 0x500 会给 1,2，仍在 {0,1,2} 内）。这只是“base 与 handle=reg 假设的联合自洽”，不是对任一者的独立证明。

---

## 6 与 metadata 的一致性与冲突

### 6.1 `8c8d676f2d2bab80`：唯一 handle0 → 静态相容性线索

- NVSD 该 program 只有 **1 个** storage buffer，且它 `handle=0`；response 也只有 **1 条** sbuf，off 0x510。
- 因此不存在“多 buffer 里任选首项”的歧义：candidate reg0 命中唯一候选，且其 handle 恰为 0。按事先约定的条件（“若唯一 handle0 才可称独立静态相容性线索”），这里**可以**称为一条独立静态相容性线索——但仅限“没有首个候选的歧义”，不代表 NVN reg 实测，也不代表 GPU 读取；NVSD 表仍是 program-wide。
- 语义上：`FlickerObject.o_flickerInfo`（16 B）是一个后处理/闪烁参数块，与 post 类 shader 相符；`buffers1_count=0`、无 sampler、无 cbuf，程序非常简单。

### 6.2 `0104dd056a3b1902`：handle 全集的一一覆盖 + slot≠reg

- candidate regs `{0,1,2}` 与 SB handles `{0,1,2}` 恰好一一对应（每个 handle 一次），无越界、无重复；语义上 `PointerList`/`U_Cluster`/`U_LightList`（offset/count、tile/cluster 参数、light list）是聚簇前向光照的典型三件套，与“2 个 PS c0 reader 之一”的定位相容。
- 但 response 里 **没有** 每条 sbuf 对应的 handle 字段；binding 号（16/17/18）也不是 NVSD handle，res `slot` 又是 binding 顺序。因此“binding16 = U_Cluster”这类具体对应**不能**由本 metadata 证明，只能说：在“reg=handle、base=0x510”下三条记录给出的 reg 集合与 handle 集合一致，不冲突。
- 这是本组里唯一能同时钉住 base 且给出三条不同 reg 的 program（见 §5 的条件性论证）。

### 6.3 `16653b901bfc4560`（复用 report83）：跨 stage 约束对照

- 同 program 三 SB：`DataBlock` h0 size4、`SecBlock` h1 size4、`U_SKIP` h2 size16；program-wide 的 `buffers2_indices=[0,1,2]`。
- PS：0x510→reg0、0x520→reg1；VS：0x130→reg2（vs base 0x110）。三个 reg `{0,1,2}` 被两个 stage **不重不漏**地分掉，PS 用 0/1、VS 用 2；`U_SKIP`（h2）只落在 VS 侧，与“skip buffer”命名相符。
- 这是“没有冲突”的跨 stage 静态对照；但**不能**由此自动证明 PS 用了 DataBlock/SecBlock（program-wide 表不编码 per-stage 选择），也不能证明 VS 用了 U_SKIP。
- 关键反例：三个 SB 的 `vis` 全是 `Fragment`，而同 program 的 VS 明明有一条 0x130 绑定 → **storage visibility 不可靠**（与源码 TODO 一致），不能拿 vis 做排除。

### 6.4 handle 语义仍是 TODO，且不是全局槽号

- `xc3_lib` 源码注释保留 `handle.handle + 3?` 的 TODO；本组又看到 **UB 与 SB 的 handle 编号重叠**：
  - lgt：UB handles `{1,2,0}` 与 SB handles `{0,1,2}`；
  - layout p2：UB `U_MENU` handle0 与 SB `DataBlock` handle0。
- 所以 handle 至少是 **per-list（或 per-bank）** 的编号，不能当作 program 全局唯一的槽号；把“binding-sorted 序号”或“res slot”当 handle 都是错的（§5 已给出 slot≠reg 的直接反例）。

### 6.5 尺寸与 16 字节 stride 无关

- c0 表项 16 字节是“指针/大小描述符”的间距；buffer 的 `size_in_bytes` 独立：post 16；lgt 8/48/1；layout 4/4/16。没有“size=16×n”的关系可用，也没有出现 size 与 offset 冲突。

---

## 7 剩余缺口（明确不做的事）

1. **0x550 / runtime-only `304f1f866df79c3a` 未覆盖**：没有容器 program 与审计 package，本轮不为它读 NVSD；其 5 个 offset（含 0x550）在 candidate 下会给 reg 0..4，但这只是算术。
2. **NVN reg 未被实测**：0x510 仍是 candidate；本轮的“钉住”是条件性的（依赖 reg=handle），没有 c0 表实测、没有 GPU 侧观测。未把 PS base 0x510 写入任何 profile/base/facts。
3. **handle 语义未解**（源码 TODO + UB/SB 重叠），`buffers1_indices`/`buffers2_indices` 的语义在库中也没有文档（`[-1,-1,0]` 这类值本轮未解释）。
4. **program-wide 表不编码 per-stage/per-entry 选择**：三个 program 都不能证明“某条 sbuf 就是某个 NVSD buffer”，只能给出一致/不一致。
5. **storage visibility 不可靠**（§6.3 的 VS 反例），保留 TODO。
6. **没有 GPU 执行/内容证据**：本轮全是 metadata 与 res.json，不涉及提交、执行、像素。
7. 未扩 TEX27/GS/fout/其它 image；c1 的 `not proven bounded: 0 shaders` 语义不变（不是内存安全结论）。

---

## 8 对 report88 的勘误（按主管指示，report88 原文未改）

1. `slot=0x1516793a70` 的 **bit_length 是 37**（值 90,571,356,784；`2^36 = 68,719,476,736 <= v < 2^37 = 137,438,953,472`），不是 54。report88 §3 表中的“54 位”应读作“37 位”。
2. `u=1` 只表示 `p_bind_buf` 指针存在：`nvn_mtl.m:3905` 取 `u = reg < 16 ? &S.ssbo[stage][reg] : NULL`；`nvn_mtl.m:3913` 打印的是 `u != NULL`。它**不是** resolve 标志；解析成功由 `resolved=1`（`resolve_success`，`nvn_mtl.m:3907/3908`）表示。
3. 三个地址保持分开命名：`addr=0x7d9a95ba70` 是 **CPU guest addr**（`u->addr`）；`slot=0x1516793a70` 是**最终写入参数槽的 Metal GPU address**（`slots[aid] = gpu`，来自 `mtl_gpu_addr`）；两者都不是 texture rid / `ser`，也不得跨 run 比较。

---

## 9 仓库与文件状态

- HEAD `cac7c6f`；`git status --porcelain` 仅既有的未跟踪 `?? XC3-SETUP.md`（mtime 2026-10-21 01:59，早于本轮，未触碰）；无 commit、无 push、无 tracked 改动。
- profile 未动：`ssbo-vs110-correct645/profile/010074F013262000/game.tsv` mtime 20:58（本轮工作 22:09 之后），未写入 base。
- 本轮只新增 SSD 目录 `ssbo-ps-nvsd/`（helper、锁文件、build.log、两份 out、verify.py、analysis.txt、identity.json、target/）与本报告；无 guest 进程（`pgrep dmhost|nxnative` 为空）。
- `AGENTS.md`、`XC3-SETUP.md`、共享 `dmhost`、旧 profile 库与旧报告均未改动。

---

## 10 结论

- 两个 PS program 的身份均按“生产 spch 解析 + code/ctl 重算 key + code 自声明 stage + 审计 package 唯一匹配”复核通过；容器、entry、control/code 的完整 sha256 已记录。
- candidate `PS base 0x510 / stride 16` 在三个 program（两个新读 + 一个复用）上**没有冲突**：全部 offset 对齐、reg 落在声明 handle 集合内；post 是“唯一 handle0”的静态相容性线索；lgt 给出 handle 全集的一一覆盖并条件性钉住 0x510；layout 给出跨 stage 不重不漏的分割。
- 这些都不是 NVN reg 实测：handle 语义、program-wide 选择、storage visibility 仍是 TODO；0x550 的 runtime-only key 未覆盖；base 0x510 未写入任何 profile。
- 按授权到此为止：无 guest、无新 translator、无 MSL/Metal/host/library 构建、无提交；等待复核。

---

## 11 追加勘误（主管指示追加；上文原文与证据保留不改）

1. **`304f1f866df79c3a` 有审计过的 runtime BTCD 包**：`ps_runtime_304f1f866df79c3a.bin@0`（report82 的原始请求正是由这个包生成）。§4.4 与 §7 第 1 条里“没有审计 package”的表述不准确，应改为“没有已定位的 SPCH 来源/NVSD，但有审计过的 runtime BTCD 包”。本轮仍未读它的 NVSD，0x550 的 metadata 覆盖缺口不变。
2. **`buffers1_count=0` 的边界**：它只说明该 NVSD 没有 uniform-buffer 项，**不能**推出“没有保留的 c0/drvcb 读取”。`driver_reads` 是否存在、读了哪些偏移，应由真实 response / code / 反射判定，不能由 `buffers1_count` 推导；§6.1 中“程序非常简单”的措辞不构成 driver 读取结论。
