# report98 · 高槽 TEX 最小 tex-final 诊断 + 强制 preflight 校验（纯离线；无 gate/guest）

日期：2026-10-22 00:32–00:55（本机）
HEAD **`36bba17`**（父 `f5a3cbb`；仅 `dm/gfx/nvn/nvn_mtl.m`，+15/−4）；本地提交，无 amend/push/PR。
目录：`/path/to/external-drive/xc3/work/experiments/tex27-highslot-final-plan/`

---

## 1 代码 diff（最小诊断）

`nvn_mtl.m` TEX 分支（`kind == NVN_RB_TEX || NVN_RB_TEXU`）只加局部标记与一条 `[tex-final]`：

- 分支入口在 `t` 创建后加 `int tsrc = t != nil, tfb = 0, tfit = 0, tafr = 0, tdummy = 0;`；
- 在既有 feedback 替换、`tex_fit`、`tex_alpha_red`、dummy fallback 的分支体内仅加 `tfb/tfit/tafr/tdummy = 1;`
  （不改变条件/调用次数/顺序/对象创建）；
- 在 `slots[aid] = trid;` **之后**加：
  ```c
  if (g_kd_force && b->kind == NVN_RB_TEX && reg >= 16)
      MLOG("[tex-final] F%llu p%llu st%d key=%s reg%d aid%d tid%d sser=%llu sres=%d fb=%d fit=%d afr=%d fallback=%d actual=%s slot=%#llx fmt=%lu %lux%lux%lu type=%lu", …);
  ```
  字段：frame/pass/stage/key/reg/aid/tid；`sser` = 注册纹理的 serial（`g_treg[tid].t.serial`，`tid < g_ntreg` 保护；
  **不是**最终 view 身份）；`sres` = 替换前源是否解析；`fb/fit/afr` = 三个既有替换是否发生；`fallback` = 是否走 dummy；
  `actual=real|dummy` **按 fallback 定义**，不靠最终指针非 nil（dummy 也非 nil）；`slot` = 最终写入参数槽的值；
  最终 texture 的 fmt/尺寸/type。
- 只对 `NVN_RB_TEX`（不含 TEXU）、`reg>=16`、`g_kd_force`；不加 sampler-final、不加全库逐 draw 日志；现有
  PD/BINDAUDIT/USE/slots/feedback/fit/alpha/fallback 路径未改。

## 2 源码顺序（实际）

`nvn_mtl.m`（行号为当前 HEAD）：

| 顺序 | 行 | 内容 |
|---|---|---|
| 1 | 3850 | `t` 由 `tex_fast_rid` 取得 |
| 2 | 3852 | feedback 替换（同 pass snapshot） |
| 3 | 3855 | PASSDUMP `B … tex …`（pre-final） |
| 4 | 3861 | `tex_fit` / `tex_alpha_red` / dummy fallback |
| 5 | 3875 | `slots[aid] = trid;` 最终参数槽写入 |
| 6 | 3881 | `[tex-final]`（本轮新增） |

即 feedback 在 PD **之前**，fit/alpha/dummy 在 PD **之后**；不能统称“所有替换都在 PD 后”。`[tex-final]` 在最终槽写入后，
可证明编码期最终选择；仍不证明 GPU 执行/内容。

## 3 Host

- `linkcheck/dmhost-tex27-texfinal`，sha256
  **`4552318d911aa16a69c2a5b7594f37909c34e789592b2994d3f6e0e1a882592e`**，1922472 B；构建 rc 0、`error:` 0。
- 证据：`compileline` sha `e33e307d…`（沿用 tex27 include 顺序，仅输出名变）、`build.log` sha `6e9bcedd…`、
  `build.rc` sha `93ff7811…`。
- strings：新 chain `8c02a1137b0d` 1 次；`b52eb825b741` 0 次；`tex-final` 1 次；`sbuf-final` 1 次。
- 宏：TEX base 0x20 / slots 27、SSBO stage0 0x110 / stage1 0x510 / CS 0、IMG 0x120 slots 1。
- chain 未变：`nvn_mtl.m` 不在 `dmsh_chain.FILES`；构建前后真实 `dmsh_chain.py` 都是 `8c02a1137b0d`，
  `--check-tools` rc 0；未改 lock。旧 host（`dmhost-tex27-writeflag`、`dmhost-ssbo-writeflag` 等）与共享 `dmhost` 未动。

## 4 preflight 修正（已强制执行）

原 preflight（report97）只打印 patched_sha、只查 json+metallib、pairs 只跑生产 validate、target 只看 max reg=16。
现在全部改为**拒绝式**：

- **host sha** 必须等于固定 `4552318d…`；
- **patched**：树 sha 必须等于 report95 基线 `479855830f40b86b8af538c478cbf53c4f74558dbd5d5bc31b47a4f279bb0f70`，且
  `main/sdk/subsdk0.patched.bin` 三模块各自等于固定 SHA（不从未次计算值生成 expected）；
- **pairs**：生产 `validate_pairs` 之外断言 **90 个有效数据行**；
- **三件套**：每个 key 必须有 `_b.json` + `_b.metal` + `_b.metallib`（原来缺 metal）；
- **target**：`stage=ps`、`fp_t_tcb_28`（tex）与 `fp_t_tcb_28Smplr`（samp_tex）各自 `reg=16`，不是仅看 max=16；
- 另有 map 645/0、c1 链名、绝对路径、patched 目录存在等既有检查。

实际 `preflight.txt`：

[Fenced excerpt omitted from the shareable research record.]

负例（副本/替身，不改真实证据；全部在 host 执行前拒绝）：`patched`（假模块树）、`pairs-count`（89 行）、
`missing-metal`（symlink farm 缺一个 `_b.metal`）、`sampler-reg`（把 target sampler 改成 15）——四例 rc≠0 且报对应
`[RED]`。

## 5 测试（no-guest，`tests/run.log`）

- `t_preflight.py`：host sha、pairs 90、target tex/sampler reg16、patched want、`preflight ok`。
- `t_preflight_negative.py`：上述 4 个负例全部拒绝。
- `t_source_order.py`：TEX PD 3855 < fallback 3861；`[tex-final]` 3881 > `slots[aid]=trid` 3875；条件仅为
  `g_kd_force && b->kind == NVN_RB_TEX && reg >= 16`（不含 TEXU）；字段 `sser/sres/fb/fit/afr/fallback/actual/slot/fmt/type` 齐全。
- `t_launch_default.py`：默认 preflight-only rc0 且打印 `KEYDUMP=4f30af45c2f40e25:1`；`--launch` rc5 拒绝（matcher 未实现），
  无 run 目录。

## 6 边界

- `[tex-final]` 只证明**编码期最终纹理参数选择**（含 fallback 与最终 slot）；不证明 GPU 执行/采样/内容，不证明真实
  NVN 槽映射，也不证明 sampler（未加 sampler-final）。
- `TEX27/base20`、`SSBO110/510`、`IMG120` 仍是候选；fout/GS/输入/阈值/所有库值未动。
- matcher 未实现，`--launch` 仍拒绝；未 gate、未 guest、未运行 host；不新增通用观察框架。
- 旧 host/旧计划/旧证据未覆盖；AGENTS.md/XC3-SETUP.md/共享 dmhost 未动。

## 7 文档与状态

- report97 已追加勘误（当时 preflight 未真正做的检查、max=16 的弱校验、源码替换顺序），不回写历史成功记录。
- 计划 README/plan 已更新为当前 host/诊断/强制 preflight；INDEX/EXPERIMENTS 加入 exp98。
- request 097 补真实 relay `codex-xc3-tex27-host-plan-cf9e7a0e41824bee9fdcbba427a33b9c` 与 `accepted:true`；request 098
  原样归档（local id `xc3-texfinal-diag-098`；relay id 未提供，unknown）。
- HEAD `36bba17`；`git status` 仅既有未跟踪 `XC3-SETUP.md`；无 push/PR；一次结束，stop 等 review，无自动下一轮。


---

## 8 追加勘误（主管 review；原文保留）

- §3 的 compileline/build.log 哈希沿用了旧 host 的值，实际新 host `dmhost-tex27-texfinal` 为：
  compileline sha256 `43499dc9ec77a4c48de265c9fe0c764e5aeace5b9e3eda8d20ee07067208db63`；
  build.log sha256 `237bbc2bd55dd856971507b6aecddd0d0a39601cd7b57ce459a82560fb7ceda5`；
  build.rc 仍为 `93ff7811a209e2a8479230bbb9b6bc19f7f311d3af383ec350c1db2a7e7d5494`。正文不改，以此为准。
- `t_source_order.py` 曾用 `text[tf-200:tf+200]` 把行号当字符下标，不能证明条件不含 TEXU；已改为对 if/MLOG 相邻行切片做静态断言，并在报告中注明静态断言不等于运行分支测试。
