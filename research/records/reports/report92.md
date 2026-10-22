# report92 · 最小修复 SBuf Write 位 + 回归 + XC3 645 隔离库/host 重建（纯离线）

日期：2026-10-21 23:00–23:20（本机）
仓库：`/path/to/user/projects/nxnative-xc3`，HEAD **`f5a3cbb`**（父 `cac7c6f`），仅本地追加提交，未 amend/push/PR。
实验目录：`/path/to/external-drive/xc3/work/experiments/ssbo-writeflag-correct645/`
Host：`/path/to/external-drive/xc3/work/experiments/linkcheck/dmhost-ssbo-writeflag`

---

## 0 结果摘要

- `dmsh_build.py` 的 rw 掩码从 `flags & 2` 改为 `flags & 1`，并在邻近英文注释注明 pinned Ryujinx `BufferUsageFlags.Write = 1 << 0`；无其它行为改动（diff 仅 1 行代码 + 2 行注释）。
- 新增 `dm/gfx/tests/test_reflect_sbuf_rw.py`：用 AST 抽取生产 `reflect()` 驱动，合成 MSL/res，5 个用例全过；旧 mask2 下 `flags=1` 用例失败（已用 `git show cac7c6f:...` 的旧源码实测复现）。
- 新 chain **`b52eb825b741`**（旧 `a0829f60e7af`、`26c9ad81719f`），真实计算；`dmsh_chain.lock` 未动、未 `--update-lock`；header 仅写入隔离 profile。
- 新库 `b-b52eb825b741`：645/645 ok，包 645/645 与原库 byte 相同，JSON 除 `chain` 外**恰好 7 条 `rw` false→true**（正是 report91 的 7 个写者：6 VS + 1 PS），其余 38 sbuf 保持只读；MSL/metallib 645/645 byte 相同。
- 新 host `dmhost-ssbo-writeflag` sha256 `b3ba3d18…`；新 chain 出现 1 次，`a0829f60e7af`/`26c9ad81719f`/`012cc15f1405` 均 0 次；旧 host 与共享 `dmhost` 未动。
- 无 guest/GPU smoke；未改 launcher；未扩观测。其它 12+TotK profile 的 chain 重建**未做**，列为未验证边界。

---

## 1 仓库改动（提交 `f5a3cbb`）

[Fenced excerpt omitted from the shareable research record.]

`dmsh_build.py` 的实质 diff：

[Fenced excerpt omitted from the shareable research record.]

- 未硬编码任何 XC3 key；未按 MSL `device` 字符串推断 rw；未动其它 kind/UBOP 条件/driver/base 逻辑/host `USE`/Metal 权限/translator/lock。
- 提交作者 `armyja <546323405@qq.com>`，提交信息：
  `dmsh_build: read storage-buffer rw from the pinned BufferUsageFlags.Write bit`（正文说明 ABI 与 7/45 写者）。
- 仅提交工具与测试；资产、profile、生成的 header、库、host 全部留在 SSD，不入 repo。

---

## 2 回归测试

文件：`dm/gfx/tests/test_reflect_sbuf_rw.py`（104 行，`python3` + `unittest`，无游戏资产）。

做法：

- 用 `ast.parse` 从 `dm/gfx/tools/dmsh_build.py` 取生产 `reflect()` 的源码段，`exec` 进命名空间（`re` + `SSBO={'vs':0x110,'ps':0x510,'cs':0}`）；**不 import dmsh_build**（导入会启动构建）。
- 合成 `struct spvDescriptorSetBuffer0 { ... }` MSL 与合成 `res['sbufs']`，驱动真实函数。
- 独立预期来自 pinned ABI 常量 `WRITE = 1  # BufferUsageFlags.Write`，并明确注释 bit1 未定义；测试不镜像实现里的掩码表达式（实现若改回 `& 2`，用例失败）。

5 个用例：

1. `test_write_bit_comes_from_flags_not_msl_text`：flags `0/1/2/3` × MSL body（无写、store、atomic 三种）→ 期望 `{0:False, 1:True, 2:False, 3:True}`，并断言 rw 是 `bool`；MSL 文本不参与 rw。
2. `test_flags_one_is_a_writer`：`flags=1` → rw True（旧 mask 的反例）。
3. `test_binding_sorted_index_and_reg`：res 的 binding 顺序 [3,1,2] → 排序后 index 0/1/2 对应 binding 1/2/3，reg 0/1/2，rw 按各自 flags；
4. `test_rw_is_independent_of_slot_resolution`：可解析 reg 的读者 rw False、`cb_slot=1` 无 reg 的写者 rw True；
5. `test_missing_metadata_keeps_previous_semantics`：MSL `_s2` 超出 res 列表 → reg None、rw False（保持原语义）。

结果：

[Fenced excerpt omitted from the shareable research record.]

旧 mask 反例（用父提交的真实源码，非测试内镜像）：

[Fenced excerpt omitted from the shareable research record.]

现有 Python 工具测试（非本次改动引入）：

- `test_spch.py` 26 OK；`test_dmsh_stage.py` 9 OK；`test_dmsh_build_entry.py` 4 OK。
- `test_tbdr_budget.py` 需要环境变量 `DM_GAME`（否则 5 个用例因 `[RED] DM_GAME is not set` 失败，与本改动无关）；设 `DM_GAME=0100000000010000` 后 5 OK。

---

## 3 chain 与 header（真实计算）

- `dmsh_chain.py --check-tools`：**rc 0**（无 `[RED]`）。
- 真实 chain：**`b52eb825b741`**（相对 `a0829f60e7af`/`26c9ad81719f` 变化，原因：`dmsh_build.py` 在 `dmsh_chain.FILES` 的字节哈希内）。
- `dmsh_chain.py --header` 写 `profile/010074F013262000/dmsh_chain.h`，再复制到 `gen/.../profile/dmsh_chain.h`；`game.py header` 生成 `gen/.../game_profile.h`。
- header 仅存在于该隔离目录；**没有**改任何 repo profile 的 header，也没有生成“有 header 无对应库”的伪就绪状态。
- `dmsh_chain.lock` 未改，未跑 `--update-lock`（工具二进制未换）。
- 宏与 PS510 相同：stage0 `0x110`、stage1 `0x510`、stage5 `0`、其余 `-1`；TEX slots 16、IMG base `0x120` slots 1。

---

## 4 新库构建（`ssbo-writeflag-correct645`）

- 输入从 `ssbo-vs110-ps510-correct645` 复制：645 包、`shader_map.tsv`、`shader_map.tsv.conflicts.tsv`、`shader_pairs.tsv`、`shader_facts.tsv`、`game.tsv`；`game.tsv` 所有 value 字节不变（vs110/ps510/cs0、IMG120/slots1、TEX16、单一 fout 行）。
- fresh `cas/`、`out/`、`work/`；`J=1`；显式 645 keys；一次运行 **rc 0**；无 `IOSOUT`/`DMSH_PREFILL`；未重命名旧链。
- 构建摘要（原文）：

[Fenced excerpt omitted from the shareable research record.]

- 失效/复用统计：fresh CAS → `shader cache: hit 0, rebuilt 645`；MSL 未变（见 §5），Metal 编译缓存 `mac 105 reused, 540 compiled`；variant `72 generated / 1 hit / 71 rebuilt / 71 compiled`。
- 产物：`out/b-b52eb825b741` 251 MB、`cas` 616 MB；645 `_b.json` + 645 `_b.metal` + 645 `_b.metallib` + 72 `_bf.metallib` + `_b_build.json`（645 项全 `ok`）。
- `c1_guard` 真实生成：`# chain b-b52eb825b741 2026-10-21T23:08:05+08:00`，`not proven bounded: 0 shaders`（不构成内存安全结论）。

---

## 5 验收（对 `ssbo-vs110-ps510-correct645` 的 `b-a0829f60e7af`）

| 项 | 结果 |
|---|---|
| 包 | 645/645 `package_verify` 通过；`pkg_manifest.sha256` 与源（相对路径形式）逐字节一致；设置时逐件 `cmp` 一致 |
| 表 | `shader_map.tsv`/conflicts/pairs/facts/game.tsv 与源相同；map 645 行 645 唯一 key（VS 284 / PS 361）；pairs 90、90 唯一、两端在 map |
| JSON 差异 | 仅 `chain`（645）+ `bindings[i].rw`（**7**）；**无其它字段** |
| rw 变化的 key | `0871803a7d1236e8`、`122eece754abf575`、`36710e69a07e849d`、`5f6491f9bda5ae4d`、`c0882609d8f91561`、`cea273f9f0936f5b`、`8c8d676f2d2bab80`（与 report91 的 7 个写者集合相等） |
| sbuf | 45 条：`rw=true` **7**，`false` **38**；`reg` 分布与 PS510 相同（VS 0×16/1×1/2×2；PS 0×9/1×8/2×7/3×1/4×1）；`index`/`arg_id` 不变 |
| 其它 kind | `tex`/`samp_tex` 各 2270，`reg=None` 87/87（20 keys）；`img` 9 全 `reg0`；`cbuf`/`c1`/`support`/`drvcb` 数量不变 |
| drv | `drv_reads` 2 keys（`0104…` c0+0x510、`16653b…` c0+0x520）与 PS510 相同；`drv_unfillable` 仍为 0 |
| MSL/metallib | **645/645 metal 相同，645/645 metallib 相同**（实比 sha256） |
| 每 key 产物 | 645 组 `_b.json`/`_b.metal`/`_b.metallib` 齐全；72 个 `_bf.metallib` 另列（`verify/variants.tsv`） |

真实 45 条回归表：`verify/real_rw.tsv`（key/stage/index/binding/reg/rw/flags 证据/msl/stores/atomics），其中 rw 来自新库，flags/store/atomic 文本沿用 report91 的既有扫描（只作证据，未新写解析器）。7 条 writer 的 rw=1，38 条只读 rw=0。

`verify/verify.txt` 是完整输出；未发现非预期 diff。

---

## 6 新 host

- `linkcheck/dmhost-ssbo-writeflag`：sha256 `b3ba3d18e5a05b8dd6ca9f3a23d50861bf16061b554e26cb5bfff27d5e1264bc`，1922472 B；编译 rc 0，`error:` 0 条。
- 编译行：`dmhost-ssbo-writeflag.compileline`（sha `2fcaf139…`），实验 include（`<new>/gen/010074F013262000/` 与 `/profile`）在 repo `gen/` 之前；build log sha `6e9bcedd…`、rc 文件 sha `93ff7811…`。
- strings：新 chain `b52eb825b741` 出现 **1** 次；`a0829f60e7af`、`26c9ad81719f`、`012cc15f1405` 均 **0** 次；`sbuf-final` 出现 1 次（嵌在格式串中）。
- 宏与 PS510 相同（stage0 0x110、stage1 0x510、CS 0；IMG 0x120/slots1、TEX16）。
- 旧 host 未覆盖：`dmhost-vs110-ps510-sbuffinal` sha `6dd3ee95…`、`dmhost-vs110-sbuffinal` sha `70c76712…` 均保持；共享 `dmhost` 未动。
- 未改 ready launcher、未启动该 host、无 guest。

---

## 7 共享 chain 影响与未验证边界

- 按 `AGENTS.md`：改动 chain 覆盖的文件后，每个受影响 profile 都要走 chain 过程（header → 重建 shader → `c1_guard` → 重建 host）。
- 本轮只对 XC3 隔离实验做了该过程；**其它 12 个 playable profile + TotK 未重建**，也没有为它们生成新 header（避免“有 header 无对应库”）。它们仍指向各自的旧 chain/旧库；这是一条**未验证**边界，不能声称框架全标题回归完成。
- `dmsh_chain.lock` 未动；translator/spirv-cross/metal 未换；新 chain 仅由 `dmsh_build.py` 源字节变化产生。
- 旧链库/旧 host 原样保留：`26c9ad81719f`（vs110）、`a0829f60e7af`（PS510）及其 host 均在，未重命名/未覆盖。

---

## 8 未来 8c 观测的预期（本轮无 live 日志）

- 新库中 `8c8d676f2d2bab80` 的 sbuf `index0/reg0/arg_id0/rw=true`（`aid` 取 reflection 的 arg_id=0，不能照抄旧 VS 的 aid2；该 pair 的 VS `c013625738b470f1` 没有 sbuf）。
- 若将来单独授权观测，`[sbuf-final]` 的 `rw` 预期为 `1`；**本轮没有 guest，不能称已见 rw=1**。
- report86/88 中 `9b770cf888d729bd`（flags=0，只读）的单 draw 最终选择事实仍然有效，不因本修复撤销；但旧库不能冒充新 chain，旧 supervisor 的 rw0 验收不能复用于 writer。后续需单独改 plan 并审。

---

## 9 产物与哈希

| 文件 | sha256 |
|---|---|
| `build.cmd` | `68ac6488…` |
| `build.log` | `9f306d79a45edb1915da8744e13669374b292e2c41e016e12693472d5991f30e` |
| `build.rc` | `7cf0d962…`（内容 `build_rc=0`） |
| `chain.txt` | `41b14665…` |
| `checktools.rc` | `8074aee1…`（内容 rc 0） |
| `c1_guard.log` | `879b2df1…` |
| `profile/.../c1_full.tsv` | `32af0e09…` |
| `profile/.../dmsh_chain.h` / `gen/.../profile/dmsh_chain.h` | `68b5840c…`（`b52eb825b741`） |
| `gen/.../game_profile.h` | `21db9224…` |
| `profile/.../game.tsv` | `8a188b57…`（与 PS510 同字节） |
| `verify/verify.txt` | `de68403a…` |
| `verify/real_rw.tsv` | `0c642adc…` |
| `verify/diff.json` | `1fecc53f…` |
| `verify/pkg_manifest.sha256` | `79f7b4c8…`（与源 manifest 同） |
| `verify/lib_manifest.sha256`（2008 行） | `8be691da…` |
| `verify/base_artifacts.tsv`（645 行） | `22baa84a…` |
| `verify/variants.tsv`（72 行） | `67059390…` |
| 提交 | `f5a3cbb`（2 files, +107/−1） |

---

## 10 状态

HEAD `f5a3cbb`；`git status --porcelain` 仅既有未跟踪 `?? XC3-SETUP.md`；无 push/PR/amend。无 guest、无 GPU smoke、无 launcher 改动；资产/生成 header/库/host 均在 SSD。等待复核。
