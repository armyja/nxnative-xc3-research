# report107 · d3c 单目标 psort 授权运行：目标 PS 的 pass 附件快照

日期：2026-10-22 01:28–01:31（本机）
Run：`/path/to/external-drive/xc3/work/experiments/integer-rt-d3c-psort-plan/run-20261022-012847/`
HEAD `36bba17c0f45d22c78ce987dcfe177f2860d81cc`（未变）；无 tracked 改动、无 commit/push。

---

## 0 授权与次数

- 合并授权：准备/测试全部通过后无需回执，一次 gate、通过后一次 guest。
- 实际：**1 gate / 1 guest / 0 retry**；7 组 no-guest 测试通过后才启动；无生产代码/host/库/facts/格式/阈值改动。
- 启动前身份（`prelaunch-20261022-012843/identity.sha`，`preflight ok`）：host `a6ded1fc…`；`supervise12.py
  a94786c3…`；`run-d3c.sh d9f9c353…`；`preflight.py 7b585133…`；`exempt.json 84402907…`；facts `3e34a5e2…`；
  chain `c26257ff13a8`；patched 三模块、gen headers、c1 按固定值。
- 环境仅 `DM_NVN_PSOFAIL_RT=d3c541d46f389225`、PSO/SHDUMP/MEMSTAT 新绝对路径、六原输入、en-GB/audio0/headless；
  无 KEYDUMP/IMGBIND/SSBO_OBS/BINDAUDIT/skip/override/test。

## 1 Gate

`gate.csv`：11 样本，`elapsed` 0.000 → 10.171（**span 10.171 s ≥ 10 s**），最小 available **3330 MiB**（≥2800）；
`launch_at=10.187`。无等待/轮询/第二 gate。

## 2 记录（`boot.log` 235–245；`psort.txt` 原文）

[Fenced excerpt omitted from the shareable research record.]

- 实际 VS 为 `a6201ef91b12f9e2_b`（按本次记录；历史仅用于包来源，不作成功门槛）；frame 1508 / pass 3136；
  `snap=valid/3136`、`assoc=same-pass`；`map enabled=0` 明示 identity，才把 physical slot 当 logical。

## 3 字段逐项（NVN 原格式 / view / 最终 MTL 分开）

| logical | NVN raw | NVN 名称（nvn.h） | cview | attached | final MTL | MTL 名称（本机 SDK） |
|---|---|---|---|---|---|---|
| 0 | 0x3f | NVN_FORMAT_R11G11B10F | 1 (setfmt=1) | 1 | 92 | MTLPixelFormatRG11B10Float |
| 1 | 0x3f | NVN_FORMAT_R11G11B10F | 1 (setfmt=1) | 1 | 92 | MTLPixelFormatRG11B10Float |
| 2 | 0x1 | NVN_FORMAT_R8 | 1 (setfmt=1) | 1 | 10 | MTLPixelFormatR8Unorm |
| 3 | 0xb | NVN_FORMAT_R32UI | 1 (setfmt=1) | 1 | 53 | **MTLPixelFormatR32Uint** |
| 4-7 | 0 | — | 0 | 0 | 0 | unattached |

- header `cfmt=92,92,10,53,0,0,0,0` 与各槽 final MTL 一一对应；`dfmt/sfmt=260`、ctx 全 0。
- 目标 MSL 仍是 `color0..3 float4`；**第一处冲突的 logical 颜色是 3**：MSL color3 为 float4，而该附件 final MTL 为
  `53 = R32Uint`（Metal 错误也只点名 R32Uint）。依据：MSL 输出类型 + slot3 attached mtl=53 + 同段 Metal 错误；
  不擅自赋 fout、不改格式，不因为 log 记录把其它颜色改 uint；NVN→MTL 映射表身份只作离线核对。
- `ser` 为对象 serial，不跨 run 比较；slot 是物理槽，identity map 才等于 logical。

## 4 时序、资源、回收

`timing.txt`：

[Fenced excerpt omitted from the shareable research record.]

- guest 时长 ≈ **51.88 s**（first−launch）；TERM 后 0.089 s 消失；legacy `launch=0` 忽略。
- `samples.csv` 209 样本：运行期最小 available **1946 MiB**（≥1 GiB），最大 RSS **851792 kB ≈ 831.83 MiB**（≤2 GiB）。
- 日志 35,631 B（<64 MiB）；`shdump` 640 KiB（<32 MiB）；两条原内容 GS 豁免（61.767 s，hash 与既有豁免一致），
  无第一个非豁免完整 dump 停止。
- child `exit=0`；`pgrep dmhost-fout-531d-uint2-645` 无残留；`pso_user.tsv` 中该 pair 无 R 记录（pipeline 建失败），
  仅有 2 处 S 关联行 — 不重跑补证。
- 停止原因：`psort: complete pass=3136 assoc=same-pass slots=8`。

## 5 证明与不证明

**证明（编码期）**：该失败 pipeline 的 pass 附件快照完整（header ctx/cfmt/snap、identity map、8 槽、done same-pass
slots=8）；logical 3 的 final MTL 为 R32Uint，与 MSL float4 输出及 Metal 错误一致。

**不证明**：GPU 执行/内容/像素；NVN 语义或 NVN→MTL 正确性；其它 logical/其它 pair；sampler；不把 slot 当 logical
（除显式 identity）；本轮未改 fout/格式，不推广其它 6 个 RG32 pair。

## 6 文档与状态

- INDEX/EXPERIMENTS 加入本次 run（evidence-run/validated-limited）；实验 README 写就；request 108 补 relay
  `codex-xc3-531d-batched-acceptance-85e223be162746d68fc106854bc4e898` 与 `accepted:true`；request 109 原样归档
  （local id `xc3-d3c-psort-run-109`；relay id 未提供 unknown）。
- HEAD `36bba17`；`git status` 仅既有未跟踪 `XC3-SETUP.md`；AGENTS.md/XC3-SETUP.md/共享 host/旧证据未动。
- 本轮 guest 后无自动离线修复授权；停止等 review。
