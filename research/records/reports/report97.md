# report97 · tex27 匹配 host + 高槽纹理目标计划（纯离线；无 gate/guest）

日期：2026-10-22 00:12–00:30（本机）
目录：`/path/to/external-drive/xc3/work/experiments/tex27-highslot-final-plan/`
HEAD `f5a3cbbfad1eeb683a6b431d944b4512e2807ef2`（未变）；无 tracked 改动、无 commit/push；无 gate、无 guest、无 host 运行。

---

## 1 新实验 host（已构建，未运行）

- 源码 HEAD `f5a3cbb`（无诊断代码改动）；用 `tex27-writeflag-correct645/gen/010074F013262000` 头，实验 include 在
  repo `gen/` 之前；输出 `linkcheck/dmhost-tex27-writeflag`。
- sha256 **`d34b4d094a13c026a26cbde4bc160936e066e3c8ed26d80453348410004bd2d1`**；构建 rc 0、`error:` 0。
- 证据：`dmhost-tex27-writeflag.compileline` sha `e33e307d14d45c78606667fa3b024d251931f041b9ae8cfad93c4fc3e0beeda3`；
  `build.log` sha `6e9bcedd…`；`build.rc` sha `93ff7811…`。
- strings：新 chain `8c02a1137b0d` **1** 次；`b52eb825b741`、`a0829f60e7af`、`26c9ad81719f` 均 **0** 次；`sbuf-final` 1 次。
- 宏：TEX base 0x20 / slots 27、SSBO stage0 0x110 / stage1 0x510 / CS 0、IMG 0x120 slots 1。
- 旧 host `dmhost-ssbo-writeflag`（`b3ba3d18…`）与 `dmhost-vs110-ps510-sbuffinal`（`6dd3ee95…`）未动；共享 `dmhost` 未动。

## 2 目标选择（只读现有日志）

在 20 个 tex27 keys 中选 **`4f30af45c2f40e25`**（pixel）。理由：最短路径——17 个 `tex`、唯一的 `reg>=16` 绑定
`fp_t_tcb_28`（slot 16），无 sbuf/img；且在已有日志中有多次**program-load 尝试**。

- 来源包（map 行 371）：`ps_runtime_4f30af45c2f40e25.bin	0	pixel	4f30af45c2f40e25	recovered#4f30af45c2f40e25`。
- 日志（主）：`ssbo-vs110-final-plan/run-20261021-213817/boot.log:531-532`：

[Fenced excerpt omitted from the shareable research record.]

- 同样两行见于 `imgdiag-run3/run-20261021-171600:588-589`、`run-triple-…:568-569`、`run-psort-…:539-540`、
  `run-foutuint-…:541-542`、`ssboobs-run-plan/run-20261021-203413:563-564`；`boot215/runs/push3-153453:836` 为
  “not in the shader map”形式。
- **没有任何 draw 记录**（无 `d … fs=4f30af45c2f40e25`，也无 `K … st1 key=4f30…`）；目标只是被请求并在 reflection 处被拒，
  尚未绘制。不假定 pair；实际 VS 只能由将来该次 run 的 `[kd]`/`d` 给出。

目标全部 texture reg（tex27 reflection）：`fp_t_tcb_8→0, A→1, C→2, E→3, 10→4, 12→5, 14→6, 16→7, 18→8,
1A→9, 1C→10, 1E→11, 20→12, 22→13, 24→14, 26→15, 28→16`（17 tex + 17 samp_tex 同 reg）；另有 `cbuf fp_c4 reg1`、
`cbuf fp_c3 reg0`、`c1 fp_c1 bank1`；`drv_reads {}`、无 sbuf、无 image；`raster.colors` 0..4。

## 3 日志顺序（源码确认）与可证明/不可证明

`nvn_mtl.m`：

- TEX 的 PASSDUMP 行 `PD("B … tex reg%d tid=%d %s …")` 在 **3854** 行；
- 类型适配/alpha 替换/`if (!t) { t = dummy_tex(…) }` 在 **3860** 行；
- `[bind]` 在 **3870** 行，之后于 fallback，但只由 `DM_NVN_BINDAUDIT`（**3861**）门控，且打印 `rid`/尺寸而非最终 `real/dummy`；
- `slots[aid] = trid` 是最终参数槽写入；对 `NVN_RB_TEX` **没有**任何日志打印它（无 `tex-final`）。

因此现有日志只能证明：
1. 目标曾被请求（program-load 尝试），并在修复前于 reflection 被拒；
2. 若开启 PASSDUMP，可看到**pre-fallback**的绑定状态/解析对象（`real/dummy`），但这不是最终选择；
3. **最终参数选择无法用现有日志证明**——这是明确缺口，不把 pre-fallback real 当 final real。

## 4 计划（design-only；未实施 matcher/hook）

`tex27-highslot-final-plan/`：

- `preflight.py`：只读身份与目标校验（host sha、chain、TEX 27/base20、map/pairs、每 key `_b.json`/`_b.metallib`、c1、
  target 17 tex/max reg 16、patched sha、env whitelist）。实际结果：

[Fenced excerpt omitted from the shareable research record.]

- `run-highslot.sh`：默认 preflight-only，打印 child DM 配置（KEYDUMP=4f30…:1、PSO/SHDUMP/MEMSTAT、六输入、en-GB/audio 0）；
  `--launch` **拒绝**（rc 5，提示 final TEX selection 未在 fallback 后记录，design-only，未加 hook），不创建 run 目录。
- `plan.md`：允许的有限结局——target-not-obtained（无 kd 或首个 kd 的 fs 不同）、更早的 non-exempt complete dump /
  目标 pipeline 或 load 失败 / 资源/时限/信号/CRASH；可选 binding-state 记录（仅“该时刻解析对象”）；**最终选择为缺口**，
  未来若授权可加最小 `tex-final`（在 `slots[aid]=trid` 之后打印 reg/tid/ser/resolved/actual/slot），再按 sbuf-final 同规则
  设计 matcher；本轮未加。
- 资源/门控/阈值/豁免/输入/cleanup 形状沿已 review 计划（2800 MiB ≥10 s、1 GiB/2 GiB/180 s/32 MiB/64 MiB、两条固定 GS、
  `env -i` 白名单），本计划不执行。

测试（no-guest，`tests/run.log`）：

- `t_preflight.py`：身份 + target 17 tex/max reg 16，rc0。
- `t_source_order.py`：TEX PD 行 3854 < fallback 3860；`[bind]` 3870 > fallback 且 BINDAUDIT 3861 门控；无 `tex-final`。
- `t_launch_default.py`：默认 preflight-only rc0、打印 KEYDUMP；`--launch` rc5 拒绝且无 run 目录。

## 5 边界

- 本轮未运行 host、未 gate、未 guest；`--launch` 不可用是设计结论，不是授权状态。
- 计划不声称真实/dummy 最终选择，不把 PASSDUMP pre-fallback 的 real 当最终；不预造 pair/VS；不新增 hook。
- 不要求为得到 real 延长/重试/扩 GS/加 fout；目标更早失败按原规则结束。
- 旧计划 `ssbo-ps-writer-final-plan` 未被覆盖；active 库仍为 `ssbo-writeflag-correct645`（validated-limited checkpoint），
  tex27 仍为 candidate，均不自动替换 ready launcher。

## 6 文档与状态

- 新 plan/README 已写；INDEX/EXPERIMENTS 加入 exp97（plan/evidence-only）与 host `dmhost-tex27-writeflag`。
- report96 的 request 档案补 `relay_request_id codex-xc3-tex27-offline-862413e0429f4ec8bd966ae0b953a7e2` 与
  `accepted:true`（正文不改）。
- request 097 原样归档（`rounds/097-request.md`；local_archive_id `xc3-highslot-plan-097`；relay id 未在消息中提供，记 unknown）。
- HEAD `f5a3cbb` 未变；`git status` 仅既有未跟踪 `XC3-SETUP.md`；无 commit/push；AGENTS.md/XC3-SETUP.md/共享 dmhost/
  旧 profile 库/证据未动。无 gate、无 launch、无自动下一轮。

---

## 7 追加勘误（主管 review；原文保留）

- §4 的 preflight 描述把“patched_sha 只计算/打印”“只校验 json+metallib”“pairs 只跑生产 validate”当成了已完成的检查；实际当时没有对固定 baseline 判等、没有 90 行断言、没有 metal 三件套校验。report98 已补齐这些检查并用副本负例验证；本勘误不回写当时的成功记录。
- 目标校验当时只凭 `max tex reg=16`；report98 改为明确 `fp_t_tcb_28`（tex）与 `fp_t_tcb_28Smplr`（samp_tex）各自 reg16，并校验 stage ps。
- 源码顺序补充：反馈替换（feedback）在 PASSDUMP 行**之前**，tex_fit/alpha 与 dummy fallback 在**之后**；不能统称“所有替换都在 PD 后”。report98 按实际顺序记录。
