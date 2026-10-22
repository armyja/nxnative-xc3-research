# report103 · 单目标 integer-RT psort 授权运行：目标 PS 531d 的 pass 附件快照

日期：2026-10-22 00:57–01:00（本机）
Run：`/path/to/external-drive/xc3/work/experiments/integer-rt-531d-psort-plan/run-20261022-005709/`
HEAD `36bba17c0f45d22c78ce987dcfe177f2860d81cc`（未变）；无 tracked 改动、无 commit/push。

---

## 0 授权与身份

- 授权：一次 gate + 门控通过后一次 guest launch；实际 **1 gate / 1 launch / 0 retry**，取得完整 psort 记录后 supervisor 自行停止。
- 启动前身份（`prelaunch-20261022-005706/identity.sha`，preflight `preflight ok`）：host
  `4552318d…`；`supervise10.py cf2e4234…`；`run-psort.sh f47ef438…`；`preflight.py 9b92d901…`；
  `exempt.json 84402907…`；profile tex27 `game.tsv 557e139e…`、map `1319a77d…`、pairs `6734c656…`、c1 `add45204…`、
  chain header `e30caf47…`；manifests `1be1c897…`/`79f7b4c8…`/`ce164106…`；gen headers `dc4403fe…`/`e30caf47…`；
  patched modules `ace9e8fe…`/`e5b336a9…`/`57e50f0e…`。
- 环境仅 `env -i` 白名单：`DM_NVN_PSOFAIL_RT=531d637463e53486`、PSO/SHDUMP/MEMSTAT 新绝对路径、en-GB/audio0、六原输入；
  无 KEYDUMP/IMGBIND/SSBO_OBS/BINDAUDIT/skip/override/test。

## 1 Gate

`gate.csv`：11 样本，`elapsed` 0.000 → 10.166（**span 10.166 s ≥ 10 s**），最小 available **3140 MiB**（≥2800）；
`launch_at=10.183`。无等待/轮询/第二 gate。

## 2 记录（`boot.log` 行号 238–248；`psort.txt` 原文）

[Fenced excerpt omitted from the shareable research record.]

- 触发原因在同段前一行（237）：
  `[RED] failed to create render pipeline (vertex f64e061d85e6f3a5_b fragment 531d637463e53486_b): output of type float4 is not compatible with a MTLPixelFormatR8Uint color attachment.`
- 本次实际 VS 为 `f64e061d85e6f3a5_b`（与历史一致，但按本次记录，不假定固定）；frame 1508 / pass 3126；
  `snap=valid/3126`、`assoc=same-pass`（生产 assoc 为准；两个计数器不强加相等）。
- `map enabled=0` 明示 identity，因此 logical colour index = physical slot index；这是日志显式 identity 才采用。

## 3 字段逐项（NVN 原格式 / 附件 view / 最终 MTL 分开）

| logical | NVN raw fmt | tgt | flags | NVN dims | cview | view fmt | attached | final MTL | MTL 名称（本机 SDK 枚举） |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 0xa | 1 | 0xc | 480x272x1 x0 | 1 (setfmt=1) | 0xa | 1 | 55 | MTLPixelFormatR32Float |
| 1 | 0x25 | 1 | 0xc | 480x272x1 x0 | 1 (setfmt=1) | 0x25 | 1 | 70 | MTLPixelFormatRGBA8Unorm |
| 2 | 0x3 | 1 | 0xc | 480x272x1 x0 | 1 (setfmt=1) | 0x3 | 1 | 13 | **MTLPixelFormatR8Uint** |
| 3 | 0xa | 1 | 0xc | 480x272x1 x0 | 1 (setfmt=1) | 0xa | 1 | 55 | MTLPixelFormatR32Float |
| 4-7 | 0 | 0 | 0 | 0x0x0 x0 | 0 | - | 0 | 0 | unattached |

- header `cfmt=55,70,13,55,0,0,0,0` 与各 slot 的最终 MTL 值一一对应（未附着槽为 0）。
- 目标 PS 的 MSL 输出仍是 `color0..3 float4`（tex27 库）；**第一处冲突的 logical 颜色是 2**：MSL color2 为 float4，
  而该附件最终 MTL 格式为 `13 = R8Uint`（Metal 错误也只点名 R8Uint）。依据：MSL 输出类型 + slot2 的 attached mtl=13 +
  同段 Metal 错误；**不**从 Metal 错误推 color0，**不**预先赋 fout，**不**因 color0/1/3 也非 4x 匹配就把四个输出全改 uint。
- NVN 原格式 0xa/0x25/0x3 与 view fmt 原样记录；其语义、NVN→MTL 映射正确性未由本快照证明（unknown）。
- `dfmt/sfmt=260`、ctx 全 0；`ser` 是对象 serial，不跨 run 比较；slot 是物理槽，identity map 才等于 logical。

## 4 时序、资源、回收

`timing.txt`：

[Fenced excerpt omitted from the shareable research record.]

- 同一单调时基：`launch_at 10.183` → `first_at 62.655`（guest 时长 ≈ **52.47 s**）→ TERM `62.659` → gone `62.903`；
  legacy `launch=0.000` 忽略。
- `samples.csv` 213 样本：运行期最小 available **1995 MiB**（≥1 GiB），最大 RSS **856848 kB ≈ 836.8 MiB**（≤2 GiB）。
- 日志 36,114 B（<64 MiB）；`shdump` 640 KiB（<32 MiB）；两条原内容 GS 豁免（62.297 s，hash 与既有豁免一致），
  首个非豁免完整 dump 未出现（记录先到）。
- child `exit=0`，TERM 后 0.24 s 消失；`pgrep dmhost-tex27-texfinal` 无残留；`pso_user.tsv` 有 2 行目标 pair 关联。
- 停止原因：`psort: complete pass=3126 assoc=same-pass slots=8`。

## 5 证明与不证明

**证明（编码期）**：目标 PS 失败 pipeline 的 pass 附件来源快照完整（header ctx/cfmt/snap、identity map、8 槽原文、done
same-pass slots=8）；本次该 pair 的附件中 logical 2 的最终 MTL 为 R8Uint，与 MSL float4 输出及 Metal 错误一致。

**不证明**：快照只是 pass 附件来源证据，不证明 GPU 执行/内容/像素正确；不证明 NVN 格式语义或 NVN→MTL 映射正确；
不证明其它 slot 或全部 8 pair；不证明 sampler；不把 slot 当 logical（除本次显式 identity）；不先赋 fout、不改格式。

## 6 文档与状态

- INDEX/EXPERIMENTS 加入本次 run（evidence-run/validated-limited）；实验 README 追加结果；request 104 补 relay
  `codex-xc3-psort-parser-fix-62ac0fa5cc924c2b904eb050c53f67af` 与 `accepted:true`；request 105 原样归档
  （local id `xc3-psort-run-105`；relay id 未提供 unknown）。
- 纯运行未改 tracked/未提交/push；HEAD `36bba17`；AGENTS.md/XC3-SETUP.md/共享 host/旧库证据未动。
- 无第二 launch、无后续离线修复自动授权；停止等 review。


---

## 7 追加：离线源码核对（主管 review 补充；不回写成运行测了 NVN 语义）

- `dm/gfx/nvn/include/nvn.h`：`NVN_FORMAT_R8UI = 0x3`（第 400 行）、`NVN_FORMAT_R32F = 0xA`（407）、
  `NVN_FORMAT_RGBA8 = 0x25`（434）。
- `dm/gfx/tex/nvn_fmt_mtl.c`：`[0x01] = E(R8Unorm), E(R8Snorm), E(R8Uint), E(R8Sint)`（29 行附近）、
  `[0x0A] = E(R32Float), E(R32Uint), E(R32Sint)`（31 行）、`[0x25] = E(RGBA8Unorm), E(RGBA8Snorm), E(RGBA8Uint), E(RGBA8Sint)`（39 行）；
  本次 slot 的 cview `setfmt=1` 且 view fmt 与原 format 相同，无格式类型改变。
- 因此本次 logical2 的冲突属于**整数输出类型 fact 缺失**的明确候选（PS 531d 的 color2 需要 uint），而不是本 host 的
  NVN→MTL kind 映射错误。该结论来自离线源码核对；原 §3 的 “NVN 语义/映射未由快照证明” 仍然成立——此处只补充映射表的
  静态身份，不声称运行测过 NVN 语义。
