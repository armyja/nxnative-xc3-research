# report95 · PS-writer 单次授权运行：目标 PS 8c 的 same-pass triple 取得（real）

日期：2026-10-21 23:47–23:56（本机）
Run：`/path/to/external-drive/xc3/work/experiments/ssbo-ps-writer-final-plan/run-20261021-234906/`
HEAD `f5a3cbbfad1eeb683a6b431d944b4512e2807ef2`（未变）；无 tracked 改动、无 commit/push/PR。

---

## 0 授权与次数

- 授权：一次 gate 尝试、至多一次 guest launch；`run-ps-writer.sh --launch` 执行一次。
- 实际：**1 次 gate、1 次 guest、0 次 retry**；gate 通过后启动，取得 triple 后 supervisor 自行停止，未触发 180 s 上限。
- 启动前检查 owner 暂停/冲突：`proto/out` 与计划目录无 pause/stop/owner 文件；本轮指令即为当前授权。
- 无 pre-launch 资源轮询；身份/哈希读取在启动前完成并保存。

## 1 启动前身份留档（`prelaunch-20261021-234859/`）

`preflight.txt`（原文）：

[Fenced excerpt omitted from the shareable research record.]

- `identity.sha` 记录：host `b3ba3d18…`；`game.tsv 8a188b57…`；`shader_map.tsv 1319a77d…`；conflicts `a59b054e…`；
  pairs `6734c656…`；facts `5ae41c2d…`；`c1_full.tsv 32af0e09…`；`dmsh_chain.h 68b5840c…`；lib/pkg manifests
  `8be691da…`/`79f7b4c8…`；`supervise8.py 7f6dc743…`；`run-ps-writer.sh 7550cdde…`；`preflight.py b9767a65…`；
  `exempt.json 84402907…`。
- `patched.sha`（Round-21 baseline 前缀全部吻合）：
  `main ace9e8feca3b96574f19d3bfec700b34bb14023f5962e5bea586dd15b904c23d`、
  `sdk e5b336a9934c36db68e62249e790a981516a70b12a8d42fa789f42cce53a26b2`、
  `subsdk0 57e50f0e8f2f2e1b82e0ddf62d21986f682415ce7dedbb84bc7d03abc98b12c4`。
- 白名单 env（`env.txt`）：仅 launcher 列出的 `DM_ROMFS/DM_SAVE/DM_TEMP/DM_MSL_DIR/DM_NVN_SHMAP/DM_NVN_SHDUMP/
  DM_PSO_RECORD/DM_MEMSTAT/DM_NVN_KEYDUMP/DM_KEYS/DM_LANG/DM_AUDIO` + 系统键；未带 `DM_NVN_IMGBIND`、
  `DM_NVN_PSOFAIL_RT`、`DM_NVN_SSBO_OBS`、任何 skip/override/testing 开关。
- 任何身份不符都会在 preflight 拒绝；本轮 preflight ok 后才进入 gate。

## 2 Gate

`gate.csv`：11 个样本，`elapsed` 0.000 → 10.159（有效 span **10.159 s ≥ 10 s**），最小 available **2911 MiB**
（≥2800）。`launch_at=10.174`。无 pre-launch 资源轮询。

## 3 Triple（`boot.log` 行号；`triple.txt` 原文）

[Fenced excerpt omitted from the shareable research record.]

同段紧邻记录（非成功条件）：

[Fenced excerpt omitted from the shareable research record.]

- `[kd]` 锚点（244）的 `target yes`，vs/fs 即实际 pair；`d`（253）的 fs 与之一致。
- **没有 `K 3204 st0`**（该 pass 的 VS K 记录为 0 条）→ 实际 VS 只有 `[kd]` 与 `d` 两个来源，两者一致（`c013…_b`）；
  报告为“没有第二来源”，未捏造结构配对。
- 全日志 `sbuf-final` 仅 1 条（251）。
- 字段：`reg0 aid0 u=1 addr=0x7e0381d300 rawsize=16 size=16 resolved=1 actual=real slot=0x151c6f9300 rw=1`；`real`+`resolved1`
  完整；无 slot0 异常。`rawsize` 事实为 16（与 NVSD size 16 相符，但未据此筛选或推断写值）。
- `D` 的目标为 `960x544`，`prim=0`、`vc=1`、`inst=1`、`dt=0`、`df=3`。

## 4 同段 PSO / load / RED

- 目标 pair `c013625738b470f1_b` / `8c8d676f2d2bab80_b`：**没有** `failed to load shader`，**没有**
  `has no resolved slot`（旧 reflection 拒绝未出现），**没有** `failed to create render pipeline`。
- kd 前紧邻的 3 条 pipeline RED 属于别的 pair（`f64e…/531d…`、`a620…/d3c5…`、`d7be…/ef55…`），与目标无关。
- `pso_user.tsv` 第 590/591 行是目标 pair 的两条 `R` 记录（`vs=c013…_b fs=8c8d…_b`，432 B），说明该 pair 的 PSO 记录存在。
- 全日志 14 条 `[RED]`，均为既有类别（pipeline 其它 pair、unimplemented 等），目标 pair 无 RED；旧反射拒绝是否“跨过”：
  本轮没有出现该拒绝，shader 加载与 draw 编码均继续。

## 5 时序、资源、回收

`timing.txt` 原文：

[Fenced excerpt omitted from the shareable research record.]

- 客端存活 ≈ 53.3 s（launch 10.174 → TERM 63.503）；取得 triple 即停，未到 180 s。
- `samples.csv` 216 个样本：运行期最小 available **2018 MiB**（≥1024），最大 RSS **773712 kB ≈ 755.6 MiB**（<2 GiB）；
  footprint 未采样（unknown），不据此推断系统压力因果。
- 日志 35,522 B（<64 MiB）；`shdump` 640 KiB（<32 MiB）。
- 豁免：两条固定内容 GS（63.078，ctl/code sha 与既有豁免一致），无其它 complete dump stop；未扩豁免。
- child 回收：`exit=0`，TERM 后 0.076 s 消失（gone 63.579）；`pgrep dmhost-ssbo-writeflag` 无残留；finally 只回收自身 child。
- 停止原因精确为：`ps-writer-final: complete pass=3204 actual=real resolved=1 slot=0x151c6f9300 rawsize=16 vs=c013625738b470f1_b`。

## 6 输入触发情况

`DM_KEYS` 六步中，日志只有 `frame 1500.00 press 0x1 (hold 0.20 s)` 一条（第 228 行）；目标 draw 在 F1508 被 KD 记录并立即停止，
后续 f2100/f2700/f3200/f3700/f4200 未触发。未为补齐 inputs 继续运行。

## 7 证明与不证明

**证明（编码期）**：在这一个 forced draw 上，候选 host 最终写入参数槽的选择为 `slot=0x151c6f9300`（非零），
`addr=0x7e0381d300` 为客端地址，`rawsize=size=16`，`resolved=1 actual=real`，且 `rw=1` 被传入 `[sbuf-final]`/`B` 记录；
实际 VS 为 `c013625738b470f1_b`（kd 与 d 一致，无 K st0 第二来源）。

**不证明**：
- `rw=1` 只说明该字段进入编码路径；`nvn_mtl.m` 的 `USE` 当前丢弃 usage，**不能**称 Metal 写权限已启用；
- 没有 GPU 写入/结果/像素/16 B 内容正确性的证据；
- 不证明 PS base `0x510` 或 NVN reg 的真实性（metadata/候选假设）；
- `slot` 是 Metal GPU 地址、`addr` 是 CPU guest 地址，命名空间不同，不能跨 run 对同一对象比较；
- report80 的三槽 ambiguity 不因本 triple 自动消除；
- 不把 NVSD `size 16` 当作真实写值或筛选条件。

## 8 文档与状态

- INDEX/EXPERIMENTS 已加入本 run（`exp95-ps-writer-run`，role evidence-run，status validated-limited）；exp94 README 追加
  运行结果；request 094 档案补 `relay_request_id codex-xc3-pswriter-plan-6174e2d2ef1a4b24816e1c49ad122471` 与
  `accepted:true`（正文不改）。
- 未改程序、未 refill、未编译、未第二次运行；HEAD `f5a3cbb` 未变；无 commit/push；AGENTS.md/XC3-SETUP.md/共享 dmhost/
  旧 profile 库/证据未动。
- 一次结束，stop 等 review。


---

## 9 追加勘误（主管 review；原文保留）

- 上文 §3 的“没有第二来源”表述不准确：`[kd]`（244 行）与 `d`（253 行）已经是**两个互相一致的 VS 来源**；
  缺失的 `K st0` 只是缺少第三处记录，不是缺少第二来源。原记录与结论不变，仅此措辞更正。
