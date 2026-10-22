# report90 · PS base 0x510 全候选库（correct645）+ 匹配实验 host（纯离线，无 guest）

日期：2026-10-21 22:09–22:32（本机）
目录：`/path/to/external-drive/xc3/work/experiments/ssbo-vs110-ps510-correct645/`
Host：`/path/to/external-drive/xc3/work/experiments/linkcheck/dmhost-vs110-ps510-sbuffinal`
HEAD `cac7c6f`，无 tracked 改动、无 commit、无 push。

---

## 0 授权边界与结果摘要

- 纯离线：无 guest、无 GPU smoke、无新 diag/生产代码、无 translator/lock 变化、无提交；未改当前 ready launcher、未安排任何 launch。
- 从 `ssbo-vs110-correct645` 完整复制审计 645 包 / map / 90 pairs / facts；唯一非注释 profile 差异是 `nvn_ssbo_bases ps=0 → ps=0x510`（VS 0x110、CS 0 保持；IMG 0x120 / slots 1 / TEX 16 / 单一 fout 行不变）。
- 真实 `dmsh_chain.py --check-tools` rc 0；真实 chain **`a0829f60e7af`**（相对 `26c9ad81719f` 变化，见 §2）；新 header 只写在本目录。
- 单次 `J=1`、显式 645 keys、fresh CAS/out 构建 **rc 0**：645/645 ok；45 sbuf 全部有 reg（PS 26 条由 None 变为 0..4，分布 `0:9, 1:8, 2:7, 3:1, 4:1`）；VS 19 条 regs 不变；87/87 tex/samp 仍缺 reg（20 keys）；9 img 仍 reg0；MSL/metallib **645/645 byte-identical**。
- 匹配 host 用 `cac7c6f` 的 reviewed `[sbuf-final]` 源码构建，实验 include 在 repo gen 之前：新 chain 出现 **1** 次、旧 chain **0** 次；旧 host 与共享 `dmhost` 未动。
- 待测边界与候选 host 的 c0 填充效应见 §6/§8；下一次观测草案见 §9（不授权实现或 launch）。

---

## 1 输入与唯一 profile 差异

### 1.1 从 `ssbo-vs110-correct645` 复制

| 项 | 结果 |
|---|---|
| `pkg/` | 645 个 `.bin`；逐件 `cmp` 与源目录一致（`pkg_diff=0`）；`verify/pkg_manifest.sha256` 与源 manifest 逐字节一致（sha256 `79f7b4c8cc007a3da8f50c5f127842015df309f57a79a5f96f51667c46521c96`） |
| `shader_map.tsv` | 49859 B，sha `1319a77dbb514cb1b26a474b2ac3692ec0db41d349261bfff2e4347f767fd60d`（=源） |
| `shader_map.tsv.conflicts.tsv` | sha `a59b054e8ef7a3a30bbc7135d8060cd4fad8572b6ef2332669f9798870f86caa`（=源） |
| `shader_pairs.tsv` | sha `6734c6564e622b6fafadaf0e1f20548a302d0b91119f8643873ed140758d011c`（=源） |
| `shader_facts.tsv` | sha `5ae41c2d2aa8db42653425096645ba13450551ee7c6a0b7f8ee76f147c404e0a`（=源，单一 fout 行 `4bae5b8abd3bec7f`） |
| `shader_pairs.provenance.tsv` | 复制，未参与构建 |

源目录未改：`ssbo-vs110-correct645` 的 `game.tsv` sha 仍为 `3ee4296500f103c64eabefcd1f6a9904eb42b19ccfc139e694cbdfd36f7c0030`，其 `dmsh_chain.h` 仍为 `26c9ad81719f`，mtime 未变。

### 1.2 `game.tsv` 的差异

源 sha `3ee42965…` → 新 sha `8a188b5769a5c7daa8778ad3fff962dcc86846cd24f54a77ace1dc0a8a2377d0`。非注释行逐行 diff：

[Fenced excerpt omitted from the shareable research record.]

其余非注释行完全相同。另加的注释说明：PS 0x510 来自 report89 的条件约束而非测量（`shd_post` slct146 p0 单 sbuf@0x510 且 NVSD 唯一 storage buffer handle0；`shd_lgt` slct0 p17 的 0x510/0x520/0x530 对 handles 0/1/2；复用的 `shd_layout` slct10 p2 PS 0x510/0x520 对 handles 0/1/2、同 program VS 0x130 对 handle2 under vs=0x110）；NVSD handle → NVN register 仍未实测；runtime-only `304f1f866df79c3a`（offsets 0x510..0x550）没有 SPCH 来源/NVSD，只被公式覆盖；非 production、非 title-wide、不借 Mario 评论、CS 保持 0。

未变：`nvn_img_base 0x120`、`nvn_img_slots 1`、`nvn_tex_base 0x20`、`nvn_tex_slots 16`、单一 fout 行、facts 表内容。

---

## 2 真实工具与 chain

| 项 | 结果 |
|---|---|
| `dmsh_chain.py --check-tools` | **rc 0**，输出为空（无 `[RED]` 行）；`checktools.txt` sha `e3b0c442…`（空文件）、`checktools.rc` = `0` |
| chain（真实计算） | **`a0829f60e7af`**（`dmsh_chain.version()`，非手写）；相对旧 `26c9ad81719f` 变化的原因：`version()` 把 `GAME.rows` 中 `nvn_*`/`shader_*` 键值计入哈希，`nvn_ssbo_bases` 的 ps 值改了 |
| header | `dmsh_chain.py --header` 写 `profile/010074F013262000/dmsh_chain.h`，再复制到 `gen/010074F013262000/profile/dmsh_chain.h`；两处 sha 均 `18a55a3ec373a25b0dd4d16aae616d883a9523a558af7120af27e2f8c1ef8acb` |
| `game_profile.h` | 真实 `dm/games/game.py header 010074F013262000 …` 生成，sha `5c92ebe3c4f0bbd949f336f577b3e81635e630b9f81d646483de3f33788cb51a` |
| `c1_full.tsv` | 真实 `c1_guard.py out/b-a0829f60e7af …` 生成：`not proven bounded: 0 shaders`；文件 sha `b1ddb8f1a9891cc3047802a6e06f8bcb5e94f138ac22bc961a88b8c0288fc8e1`，header `# chain b-a0829f60e7af 2026-10-21T22:27:38+08:00`，列表 0 行 |

生成宏（`gen/010074F013262000/game_profile.h`）：

[Fenced excerpt omitted from the shareable research record.]

即 stage0 VS 0x110、stage1 PS 0x510、其余 graphics stage `-1`、stage5 CS 0；IMG/TEX 与原一致。

---

## 3 构建（单次、J=1、显式 645 keys、fresh CAS/out）

命令（`build.cmd` 原文）：

[Fenced excerpt omitted from the shareable research record.]

- fresh：`cas/`、`out/`、`work/` 均为空目录起步；未设 `IOSOUT`、`DMSH_PREFILL`；未安装/未改默认 facts；645 个 key 显式列出（来自新 profile 的 `shader_map.tsv` 第 4 列）。
- 单次运行，`build.rc` = `0`；`build.log` sha `9b9e26d6a351b19b99292a1897480be2ebe68c98fa097023bf2943df5aba7efd`。
- 结尾摘要原文：

[Fenced excerpt omitted from the shareable research record.]

- 产物：`out/b-a0829f60e7af` 251 MB；`cas` 616 MB；`pkg` 81 MB。
- 文件清单：645 `_b.json` + 645 `_b.metal` + 645 `_b.metallib` + 72 `_bf.metallib` + 1 `_b_build.json` = 2008 个文件；baseline per-key 三件套 0 缺失。
- `_b_build.json` 是构建状态清单（645 项，全部 `"st": "ok"`），不是 per-key 反射。

---

## 4 Schema 验收（对照 `ssbo-vs110-correct645`）

### 4.1 总量与 sbuf

| 项 | 旧 `26c9ad81719f` | 新 `a0829f60e7af` |
|---|---|---|
| bindings 总数 | 6061 | 6061（同键值分布） |
| sbuf | 45（VS 19 / PS 26） | 45（VS 19 / PS 26） |
| sbuf `reg=None` | 26 | **0** |
| VS sbuf regs | 0×16, 1×1, 2×2 | 0×16, 1×1, 2×2（不变） |
| PS sbuf regs | 26×None | **0×9, 1×8, 2×7, 3×1, 4×1** |
| tex / samp_tex `reg=None` | 87 / 87（20 keys） | 87 / 87（20 keys，不变） |
| img | 9，全 reg0 | 9，全 reg0（不变） |
| drvcb | 2 | 2（不变） |
| drv_reads | 2 keys：`0104…` c0+0x510、`16653b…` c0+0x520 | 完全相同 |
| drv_unfillable | 2 keys（同上） | **0** |

### 4.2 26 条 PS reg 变化（9 keys；`index/arg_id/rw` 不变）

| key | 旧 `(index,reg,arg_id)` | 新 `(index,reg,arg_id)` |
|---|---|---|
| `0104dd056a3b1902` | (0,None,6)(1,None,7)(2,None,8) | (0,1,6)(1,0,7)(2,2,8) |
| `137ce44f89713990` | (0,None,5)(1,None,6)(2,None,7) | (0,1,5)(1,0,6)(2,2,7) |
| `16653b901bfc4560` | (0,None,3)(1,None,4) | (0,0,3)(1,1,4) |
| `304f1f866df79c3a` | (0,None,6)(1,None,7)(2,None,8)(3,None,9)(4,None,10) | (0,0,6)(1,4,7)(2,3,8)(3,1,9)(4,2,10) |
| `41b8d91fda40bc91` | (0,None,6)(1,None,7)(2,None,8) | (0,1,6)(1,0,7)(2,2,8) |
| `54a10199bda27be5` | (0,None,5)(1,None,6)(2,None,7) | (0,1,5)(1,0,6)(2,2,7) |
| `7455aafdb1aeeb94` | (0,None,5)(1,None,6)(2,None,7) | (0,1,5)(1,0,6)(2,2,7) |
| `8724493ecfe89b12` | (0,None,6)(1,None,7)(2,None,8) | (0,1,6)(1,0,7)(2,2,8) |
| `8c8d676f2d2bab80` | (0,None,0) | (0,0,0) |

- `304f1f866df79c3a` 的 5 条 reg `0,4,3,1,2` 对应其 offsets `0x510,0x550,0x540,0x520,0x530`：这是**公式覆盖**（该 key 没有 SPCH 来源/NVSD，只有审计过的 runtime BTCD 包 `ps_runtime_304f1f866df79c3a.bin@0`），不是 metadata 支持。
- 旧 response 里 4 个 3-sbuf key 的 `index 0/1/2` 分别落在 offset `0x520/0x510/0x530` → reg `1/0/2`，与新 schema 一致（即 binding 顺序不等于 reg，也不是 handle）。

### 4.3 JSON 全量差异（deep diff，645 keys）

| 类别 | 数量 | 说明 |
|---|---|---|
| `chain` | 645 | `26c9ad81719f` → `a0829f60e7af` |
| `bindings[i].reg`（sbuf） | 26 | §4.2 的 9 keys；其余 `index/arg_id/rw/msl_name` 不变 |
| `drv_unfillable` | 2 | `0104…` `['c0+0x510']→[]`；`16653b…` `['c0+0x520']→[]` |
| **其它** | **0** | 无 drv_reads、c1、notes、raster、vertex_inputs 等任何变化 |

`drv_unfillable` 的 2 处变化是候选配置的直接效果：host 的 c0 填充表从 PS base 0x510 起，两个 c0 读偏移 0x510/0x520 落入可填范围（`drv_reads` 本身未变）。这是配置效果，不是“真实 base 已被读回验证”。

### 4.4 包 / 表 / 产物完整性

- `dmsh_refill.package_verify` 对 map 的 645 行全部通过（`verify_ok=645`，`bad=[]`）；map 645 行、645 个唯一 key（VS 284 / PS 361）；pairs 90 条、90 个唯一对、两端都在 map 内。
- `verify/pkg_manifest.sha256` 与源 manifest 逐字节一致。
- `verify/base_artifacts.tsv`：645 行，每行 `key / _b.json sha / _b.metal sha / _b.metallib sha`；`variants.tsv`：72 行（`_bf.metallib` 的 sha 与大小）。
- MSL 与 metallib 实际 hash 核对：**645/645 metal 相同，645/645 metallib 相同**（与旧 chain 比）。
- 库文件总数 2008（见 §3）。

---

## 5 构建器统计与 schema 分开看

- 构建器打印的 `shaders with a binding whose slot was not decoded 20` 是**按 shader 计数**（任一 binding 未解码即计入），并且下面的 tex/samp 名单只列了前 4 个名字（各 20/18/12/11 条），不是全部。
- schema 的完整度量是：tex 87 条 + samp 87 条 `reg=None`，分布在 20 个 key、11 个名字（28/2A/2C/2E/30/32/34/36/38/3A/3C 及对应 Smplr），两组数字不混用。
- 旧的 `29` → 新的 `20` 正好是 9 个“只有 sbuf 未解码”的 PS key 被解析；这 20 个 tex/samp key 与 9 个 PS sbuf key **没有交集**（已核对），所以 tex/samp 的 87/87 不变。
- `queries without a PC answer 645` 与 `no paired PC reflection` 是同一既有事实，不因本实验变化。

---

## 6 匹配实验 host

- 用 `cac7c6f` 的 reviewed `[sbuf-final]` 源码（`nvn_mtl.m`，未改）构建；实验 include（`<new>/gen/010074F013262000/` 与 `/profile`）放在 repo `gen/` **之前**。
- 编译行：`linkcheck/dmhost-vs110-ps510-sbuffinal.compileline`（sha `b6d8e0fe1492f8b29ae6efdeb113bcf95a42d912023569c1794abd88c72e5d12`）；build log sha `6e9bcedd1d69f1fef2de58da603cf751865048667e74e050136c2c373ed78d46`；`build.rc` = `0`（sha `93ff7811a209e2a8479230bbb9b6bc19f7f311d3af383ec350c1db2a7e7d5494`），`error:` 0 条。
- 二进制：`dmhost-vs110-ps510-sbuffinal`，1922480 B，sha256 `6dd3ee95ca8e3ccee1b85daecd1f7df52290e9a6859662a607a1b96c45e31ffd`。
- strings：新 chain `a0829f60e7af` 出现 **1** 次（整串）；旧 chain `26c9ad81719f` **0** 次；`012cc15f1405`、`9f73847b56ec` 均 0 次；`sbuf-final` 出现 1 次（嵌在格式串里）。
- 宏（来自新 header）：stage0 VS 0x110、stage1 PS 0x510、CS 0；IMG 0x120 / slots1、TEX 16 同原。
- 未覆盖：旧 host `dmhost-vs110-sbuffinal`（sha `70c76712…`，mtime 21:16）与共享 `dmhost`（sha `a1b10708…`）都未改；没有把任何 launcher 指向本 host，也没有运行它。
- 该 host 的 c0 填充表（DRV0）会随 PS base 0x510 改变：这是候选配置的效果，正是 `drv_unfillable` 清空的原因；**不能**把 host 之后读回的合成 c0 当作“真实 base 0x510”的独立证据。

---

## 7 产物与哈希

| 文件 | sha256 |
|---|---|
| `build.cmd` | （命令原文见 §3） |
| `build.log` | `9b9e26d6a351b19b99292a1897480be2ebe68c98fa097023bf2943df5aba7efd` |
| `build.rc` | `7cf0d9627d797238980dd2af938c370dbd0e36326ddb3dbf9edd0ef8174ba1e3` |
| `chain.txt`（3 行，含两次确认） | `62fdf13887dc90bc2136cc91c935bc8afa70257d93622a2a65616a57147aacc9` |
| `checktools.rc` | `0`（内容） |
| `c1_guard.log` | `879b2df126418be64b7a4380e587e84cb1c62bb0c50a727caeb970ce425a65fd` |
| `profile/.../game.tsv` | `8a188b5769a5c7daa8778ad3fff962dcc86846cd24f54a77ace1dc0a8a2377d0` |
| `profile/.../c1_full.tsv` | `b1ddb8f1a9891cc3047802a6e06f8bcb5e94f138ac22bc961a88b8c0288fc8e1` |
| `profile/.../dmsh_chain.h` / `gen/.../profile/dmsh_chain.h` | `18a55a3ec373a25b0dd4d16aae616d883a9523a558af7120af27e2f8c1ef8acb` |
| `gen/.../game_profile.h` | `5c92ebe3c4f0bbd949f336f577b3e81635e630b9f81d646483de3f33788cb51a` |
| `verify/pkg_manifest.sha256` | `79f7b4c8cc007a3da8f50c5f127842015df309f57a79a5f96f51667c46521c96` |
| `verify/lib_manifest.sha256`（2008 行） | `f509e1f50ecb3bd939b0e8634185ad992d3fadc63d439b02716876eaa139a88d` |
| `verify/base_artifacts.tsv`（645 行） | `6660d00b3abd76d1a61e9804d05645a8f9582db174f36e62a1a03fb1ddc30a12` |
| `verify/variants.tsv`（72 行） | `67059390deb3064bb7c0fadb2bac3769a0a2954c765ad57279800578e90e2135` |
| `verify/diff.json` | `490b30cbc08812d2cdceb675940fcba311b2b8d5d6da74a733e013da2d36c5b9` |
| `verify/verify_build.py` | `fb85f94b94fca772afebe67dff8069dcc95600518b7abb82b855ace71d9d4e9b` |
| host 二进制 / 编译行 / build log / rc | 见 §6 |

本目录之外只新增了 `linkcheck/dmhost-vs110-ps510-sbuffinal*`。

---

## 8 边界（明确不声称的事）

1. **不是 production / 不是 title-wide**：PS 0x510 是候选假设；NVSD handle → NVN register 仍未实测；0x510 只是与三处静态约束条件相容。
2. **0x550 只有公式覆盖**：`304f1f866df79c3a` 没有 SPCH 来源/NVSD（只有审计过的 runtime BTCD 包），其新 reg `0,4,3,1,2` 是公式结果，不是 metadata。
3. **没有 GPU 侧证据**：本库和 host 都没有运行；JSON/库的 reg 是编码期反射结果，不代表 GPU 读取、内容或像素正确。
4. `drv_unfillable` 清空是候选配置的直接效果（c0 填充随 PS base 改变），不是真实 base 的独立验证。
5. 20 个 key 的 87/87 tex/samp 仍未解（既有问题，不在本轮范围）；9 img reg0、2 个 PS c0 reader 都存在且未消失。
6. c1_guard 的 `not proven bounded: 0 shaders` 只表示工具没有列出需要独占 bank 的 shader，不是内存安全结论。
7. 无 commit/push/PR；旧 profile 库、旧报告证据、`AGENTS.md`、`XC3-SETUP.md`、共享 `dmhost` 未动。

---

## 9 下一次观测草案（极短；不授权实现或 launch）

**已有日志核对（离线）**：
- `8c8d676f2d2bab80` 与 `c013625738b470f1` **确实被游戏请求过**：`boot212/runs/patchz-142528/boot.log:638-641` 是这两 key 的 load 失败（该 run 的 log 在 frame 430 / 16.18 s 之后；末尾到 frame 2487 / 84.66 s）；`patchz2-142736` 显示一个不同的旧 chain（`582ad4e2d205`）里曾有这两个 shader，而 host 期望 `bd9f613b23cd`；`boot22/A-111345:421-422` 是 dumper 的 “not in the shader map”。
- 没有任何已有 `boot.log`/`pso_user.tsv` 把这两个 key 放进**同一条**绘制/同一次 pass（同线检索为空）；所以“它们被同一 draw 使用”在现有日志里**未被记录**，不能假定。

**若将来单独授权一次观测**（本轮不实现、不 launch）：
- 现有开关即可：`DM_NVN_KEYDUMP=8c8d676f2d2bab80:1`（按 fragment key 匹配，无需新代码/开关）。
- 期望同一 pass：`K … st1 key=8c8d676f2d2bab80_b`；一条 `[sbuf-final] … st1 key=8c8d676f2d2bab80_b reg0 aid0 u=… resolved=… actual=real|dummy slot=… rw=0`；以及 `d` 行给出**实际**的 VS/PS。新 reflection 的这唯一 sbuf 是 `index0 / reg0 / arg_id0 / rw=false`（`aid` 取 arg_id=0，**不能**照抄旧 VS 的 aid2；该 pair 的 VS `c013625738b470f1` 没有任何 sbuf，所以不会出现 st0 记录）。
- `d` 行若显示 VS 不是 `c013625738b470f1`，就按实际 VS 报告，不要说成该 pair；`actual=dummy` 与 `real` 都是终态。
- 不需要 integer fout / GS / 其它未解 binding 的新 facts：该 PS 的 reflection 没有 color output（`raster.colors=[]`），唯一 fout facts 行属于 `4bae5b8abd3bec7f`，与本 key 无关；20 个 tex/samp 未解 key 与本 draw 无关。
- 本轮不改任何 ready launcher，不安排 guest。

---

## 10 状态

HEAD `cac7c6f`；`git status --porcelain` 仅既有未跟踪 `?? XC3-SETUP.md`；无 tracked 改动、无 commit、无 push/PR。无 guest、无 GPU smoke、无新 translator/diag/生产代码；仅新增本实验目录与 `linkcheck/dmhost-vs110-ps510-sbuffinal*`。等待复核。

---

## 11 追加勘误与限制（主管指示追加；上文原文与既有产物保留不改）

- report90 的“构建成功 / schema 差异符合预期”只说明构建与差异本身，**不说明权限元数据正确**：`8c8d676f2d2bab80` 的 MSL 明确写 SSBO（`_m0[1]=1065353216u; [0]=0u; [2]=0u; [3]=0u;`，第 30–33 行），而 response `flags=1` 经 `dmsh_build.py:369` 的 `flags & 2` 被解释成 `rw=false`。因此该候选库与该 host **不能**用于新的 PS guest 观测，直到 flags ABI 修复并重建（证据与建议见 report91）。
- 旧 host `dmhost-vs110-ps510-sbuffinal` 保留，但不得被 ready launcher 自动运行；本勘误不修改任何既有产物（库、JSON、host、旧报告）。
