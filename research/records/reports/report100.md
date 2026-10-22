# report100 · 高槽 TEX 目标单次授权运行：目标 PS 4f30 的 tex-final real triple

日期：2026-10-22 00:29–00:34（本机）
Run：`/path/to/external-drive/xc3/work/experiments/tex27-highslot-final-plan/run-20261022-002933/`
HEAD `36bba17c0f45d22c78ce987dcfe177f2860d81cc`（未变）；无 tracked 改动、无 commit/push。

---

## 0 授权与次数

- 授权：一次 gate 尝试、门控通过后一次 guest launch；实际 **1 次 gate、1 次 guest、0 retry**；取得 triple 后 supervisor 自行停止。
- 启动前身份全部复核通过（`prelaunch-20261022-002925/`）：
  - host `dmhost-tex27-texfinal` sha256 `4552318d911aa16a69c2a5b7594f37909c34e789592b2994d3f6e0e1a882592e`；
  - `supervise9.py 48204a250a4093316f94131a33ca2a2ecb844dba2aa89d4c2639f02d967f9fc6`；
  - `run-highslot.sh a8f5a992ef988dd2327366b3e9a63db5a376d82ef196f04abb2bb85debe2831b`；
  - `preflight.py 3700b2aa388ff11ea6567a9ed6433e11eb6ccd2543b1c0e08d9f3ce5600f0f1e`；
  - `exempt.json 844029072907f30d833f3ba05764f701ef9c10e0484e806e6d7731d62a7500c3`；
  - patched `main ace9e8fe…` / `sdk e5b336a9…` / `subsdk0 57e50f0e…`（report95 baseline）；
  - gen headers `game_profile.h dc4403fe…`、`dmsh_chain.h e30caf47…`（chain `8c02a1137b0d`）。
- preflight 实际输出：`host_sha 4552318d…`、`keys 645`、`pairs 90`、`libdir …/b-8c02a1137b0d`、`c1 # chain b-8c02a1137b0d`、
  `patched_sha 47985583… (want 同)`、`target tex_reg 16 sampler_reg 16`、`preflight ok`。
- 环境仅 reviewed `env -i` 白名单：`DM_NVN_KEYDUMP=4f30af45c2f40e25:1`、PSO/SHDUMP/MEMSTAT 绝对新路径、六原输入、
  en-GB/audio0/headless；无 IMGBIND/PSOFAIL_RT/SSBO_OBS/BINDAUDIT/skip/override/test。

## 1 Gate

`gate.csv`：11 个样本，`elapsed` 0.000 → 10.120（有效 completion span **10.120 s ≥ 10 s**），最小 available **2888 MiB**
（≥2800）；`launch_at=10.134`。无预轮询/第二 gate。

## 2 Triple（`boot.log` 行号；`triple.txt` 原文）

[Fenced excerpt omitted from the shareable research record.]

- kd、K st0、K st1、tex-final、d 同 frame **F4595** / pass **553282**；`[kd]` 与 `d` 的 fs 都是目标 PS。
- **`K st0` 存在**（563）：VS `229737d29027e77b_b`，与 `[kd]`、`d` 三方一致（不是 c013，也不是预造 pair）。
- 全日志 `[kd]` header 1 条、`tex-final` 1 条（只有目标 reg16 绑定）。
- `tex-final` 字段：`reg16 aid33 tid6032 sser=11509 sres=1 fb=0 fit=0 afr=0 fallback=0 actual=real slot=0x25a
  fmt=130 1024x1024x1 type=2`。`sser` 是注册对象 serial（不是 final view 身份）；`slot=0x25a` 是 Metal 资源 id，
  不是 CPU/GPU buffer 地址。
- 同段 `B … tex reg16 tid=6032 real ser=11509 fmt=130 1024x1024x1 view_lv=0+11`（616）为目标绑定；`d` 的 scalars：
  `vc=6 inst=1 blend=0 cull=2 st=1`。

## 3 PSO / 错误记录

- `pso_user.tsv` 第 1568/1569 行是目标 pair（`vs=229737d29027e77b_b fs=4f30af45c2f40e25_b`）的 R 记录。
- 目标 pair **无** `failed to load` / `failed to create render pipeline` / reflection 拒绝；全日志 69 条 `[RED]` 均为既有
  其它类别（unimplemented、其它 pair pipeline 等），与目标无关。

## 4 时序、资源、回收

`timing.txt` 原文：

[Fenced excerpt omitted from the shareable research record.]

- 同一单调时基：`launch_at 10.134` → `first_at 166.159` → TERM `166.164` → gone `166.684`；guest 时间 ≈ **156.03 s**；
  总 166.7 s < 180 s。`launch=0.000` 是 legacy 字段，不作真实时间。
- `samples.csv` 640 个样本：运行期最小 available **1593 MiB**（≥1 GiB），最大 RSS **1226240 kB ≈ 1197.5 MiB**（≤2 GiB）；
  footprint 未采样（unknown）。
- 日志 88,296 B（<64 MiB）；`shdump` 1664 KiB（<32 MiB）。
- 豁免：两条固定内容 GS（62.930 s，ctl/code sha 与既有豁免一致）；无其它 complete dump stop。
- 输入：六步全部触发（frame 1500/2100/2700/3200/3700/4200）；目标 draw 在 F4595。
- child 回收：`exit=0`，TERM 后 0.52 s 消失；`pgrep dmhost-tex27-texfinal` 无残留；finally 只回收自身 child。
- 停止原因：`tex-final: complete pass=553282 actual=real fallback=0 slot=0x25a sser=11509 vs=229737d29027e77b_b`。

## 5 证明与不证明

**证明（编码期）**：该 forced draw 的目标 PS 在 `[tex-final]` 处，最终写入参数槽的纹理选择是 `actual=real`、
`fallback=0`、`slot=0x25a`；源注册对象 serial `11509`、源已解析、三个替换均未发生；最终 texture 为 fmt 130、
1024x1024x1、type 2；同 frame/pass 的 `[kd]`/`K st0`/`d` 三方 VS 一致。

**不证明**：
- `slot` 是 Metal 资源 id，不是 CPU guest 或 GPU buffer 地址，不能跨 run 比较 serial/slot；
- 不证明 sampler/采样、GPU 执行或内容/像素正确；
- 不证明 TEX27/base20/真实 title 表/stride、SSBO110/510、IMG120 的映射；
- 不涉及其它 19 个 tex27 keys；
- 目标 pair 的 pipeline 未失败不等于内容正确。

## 6 文档与状态

- INDEX/EXPERIMENTS 将加入本次 run（evidence-run/validated-limited）；实验 README 追加结果；request 100 补真实 relay
  `codex-xc3-texmatcher-p1-10f9f168694b428ebd8b6b1b8f18c5ee` 与 `accepted:true`；request 101 原样归档
  （local id `xc3-texfinal-run-101`；relay id 未提供，unknown）。
- 纯运行未改 tracked/未提交/push；HEAD `36bba17`；AGENTS.md/XC3-SETUP.md/共享 host/旧库证据未动。
- 停止等 review；不自动后续。
