# report96 · TEX_SLOTS=27 隔离候选库（纯离线，无 guest/host 编译）

日期：2026-10-22 00:00–00:10（本机）
目录：`/path/to/external-drive/xc3/work/experiments/tex27-writeflag-correct645/`
HEAD `f5a3cbbfad1eeb683a6b431d944b4512e2807ef2`（未变）；无 tracked 改动、无 commit/push/PR；无 guest、无 host 编译、无新诊断代码。

---

## 0 摘要

- 从 active `ssbo-writeflag-correct645` 复制输入；生产 validator：645 keys / 90 pairs / 0 problems；包 645/645。
- 用生产 `decode_tex`（AST 抽取，不 import dmsh_build）求出缺失集合：**20 keys、87 tex、87 samp_tex**，全部仅
  **上界失败**；handle 0x28..0x3C、byte 0xA0..0xF0、base 0x20/stride 8 下候选 reg 16..26。
- 唯一非注释 profile 改动 `nvn_tex_slots 16 → 27`；其余值 byte 不变。
- 真工具 check-tools rc 0；chain **`8c02a1137b0d`**；header 只写新目录；fresh CAS/out/work、J=1、显式 645 keys、单次构建
  rc 0；`WORK` 显式指向已存在 SSD 目录。
- 结果：87+87 全部由 `None` 解码为 16..26；JSON 与 active 的差异只有 `chain`（645）+ `tex.reg`（87）+ `samp_tex.reg`（87），
  **无其它字段**；MSL/metallib 645/645 byte 相同；variant 72；undecoded 20 → 0；sbuf 45/7 等不变；c1_guard 新链 0 shaders。
- 机械候选结果，不声称采样/画面正确或真实 title 表；未建 host、未替换 active、未授权 launch。

## 1 缺失集合（生产 decode_tex，AST 求值）

脚本 `verify/tex_missing.py` 从 `dmsh_build.py` 抽取 `decode_tex` 源码，注入 `TEX_BASE=0x20, TEX_SLOTS=16/27,
SAMP_BASE=0, IMG_BASE=0x120, IMG_SLOTS=1` 求值，不 import 模块（避免顶层构建副作用）。

`verify/tex_summary.txt`：

[Fenced excerpt omitted from the shareable research record.]

- 每个 binding 的逐行记录在 `verify/tex_missing.tsv`（174 数据行）：`key, kind, msl_name, arg_id, handle, byte, ty,
  t16, s16, t27, s27, cand_reg, reason`。示例：

[Fenced excerpt omitted from the shareable research record.]

- 失败类检查：`all_upper_bound=True`，无 base/对齐/其它失败；库内其它 `tex`/`samp_tex` `None` 集合为空
  (`other_none={}`)，集合完整。samp_tex 的 `reg` 取 `t`（combined handle，ty=0），不是 sampler 侧槽位。

## 2 隔离 profile

- 从 active 复制 `game.tsv`；唯一非注释改动：`nvn_tex_slots 16 → 27`。
- 其余值 byte 不变：`nvn_tex_base 0x20`、`nvn_ssbo_bases vs=0x110 ps=0x510 cs=0`、`nvn_img_base 0x120`、
  `nvn_img_slots 1`、单一 fout 行、facts/map/pairs；源目录 `game.tsv` 仍为 `8a188b57…`。
- 注释写明：这是覆盖已见最高公式 slot 26 的最小实验范围；20 个 key 没有 NVSD 支持；既有 base/stride 前提与连续性
  不构成真实 title table 证明；不借其它域常数、不扩 GS、不加 fout。
- 表差异（非注释）只有一行：

[Fenced excerpt omitted from the shareable research record.]

## 3 Chain 与构建

- `dmsh_chain.py --check-tools` rc 0（空输出）；真实 chain **`8c02a1137b0d`**（`nvn_tex_slots` 在 `GAME.rows` 的
  `nvn_*` 哈希内）；header 只写本实验 `profile/` 与 `gen/`；`game_profile.h` 的 TEX_SLOTS 为 27。
- 精确执行记录：`build.cmd`、`build.env`（cwd、DM_GAMES_DIR/DM_GAME/DOTNET_ROOT、J=1、DMSH_CAS、**WORK=`tex27…/work`**
  （已存在）、XLATE_DEBUG/REDUCED 未设即默认 1/1、IOSOUT/PREFILL 未设）。
- fresh `cas/`、`out/`、`work/`；J=1；显式 645 keys；单次运行 **rc 0**。摘要：

[Fenced excerpt omitted from the shareable research record.]

- `c1_guard` 真实生成：`# chain b-8c02a1137b0d 2026-10-22T00:05:39+08:00`，`not proven bounded: 0 shaders`。

## 4 验证（对照 active `b-b52eb825b741`）

| 项 | 结果 |
|---|---|
| 包 / 表 | 645/645 `package_verify`；pkg manifest 与 active 逐字节相同；map 645、pairs 90、0 problems |
| 每 key 产物 | 645 `_b.json`/`_b.metal`/`_b.metallib` 齐全；72 `_bf.metallib`；无缺 |
| JSON deep diff | 仅 `chain` 645、`tex.reg` 87、`samp_tex.reg` 87；**unexpected 0**；20 keys 与 §1 集合相同；new reg 全在 16..26 |
| 剩余 schema | `tex`/`samp_tex` `reg=None` 均 0（原 87/87）；`sbuf` 45（7 rw writers）、`img` 9、`drvcb` 2；`drv_reads` 与
  `drv_unfillable` 相对 active 不变（后者仍为空） |
| 代码产物 | MSL **645/645**、metallib **645/645** byte 相同（实比 sha256） |
| variant | 72（实报，不预设） |
| 构建器统计 | “slot not decoded” 由 20 降为 **0** |

- `verify/verify.txt` 完整输出；`verify/diff.json` 记录 chain/tex/samp 改动数与 key 集合；`verify/real_tex.tsv` 为逐 key
  `old_reg → new_reg` 列表；`verify/base_artifacts.tsv`、`variants.tsv`、`lib_manifest.sha256` 为产物清单。

## 5 边界

- 这是**机械候选库**：编译成功与 schema 解码正确不代表采样/画面/内容正确，也不证明真实 title 的 texture 表。
- 20 个 key 没有 NVSD 支持；`base 0x20 / stride 8 / slots 27` 是实验前提，连续性不是证明。
- 未构建 host；未替换 ready launcher 的 active 库；未授权 guest。
- 不借其它域常数、不扩 GS、不加 fout、不改工具/lock；未重试、未改值重试。
- 旧 active `ssbo-writeflag-correct645`（含 report95 的 validated-limited 运行）仍是当前 checkpoint；本库只是新 candidate。

## 6 文档与状态

- 新实验 README 已写（`tex27-writeflag-correct645/README.md`）；INDEX/EXPERIMENTS 加入 exp96（candidate，不替换 active）。
- request 096 归档：`rounds/096-request.md`（local_archive_id `xc3-tex27-plan-096`；relay_request_id 未在收到的消息中提供，记
  unknown，不自造）。
- HEAD `f5a3cbb` 未变；`git status` 仅既有未跟踪 `XC3-SETUP.md`；无 commit/push；AGENTS.md/XC3-SETUP.md/共享 dmhost/
  旧 profile 库/证据未动。无 gate、无 launch、无自动下一轮。
