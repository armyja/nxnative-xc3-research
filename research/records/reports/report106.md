# report106 · 531d pipeline 越过旧拒绝：单次合并授权 gate+guest

日期：2026-10-22 01:23–01:26（本机）
Run：`/path/to/external-drive/xc3/work/experiments/integer-rt-531d-final-plan/run-20261022-012345/`
HEAD `36bba17c0f45d22c78ce987dcfe177f2860d81cc`（未变）；无 tracked 改动、无 commit/push。

---

## 0 授权与次数

- 合并授权：preflight/matcher/no-guest 测试全部通过且不需改生产代码/host/库/facts/阈值，则无需回执直接一次 gate、通过后一次 guest。
- 实际：**1 次 gate、1 次 guest、0 retry**；测试 7 组全部通过后才启动。
- 启动前身份（`prelaunch-20261022-012340/identity.sha`，`preflight ok`）：host `a6ded1fc…`；`supervise11.py
  80cc9a7e…`；`run-final.sh 82ca84e5…`；`preflight.py 9d3c350e…`；`exempt.json 84402907…`；facts `3e34a5e2…`；
  game/map/pairs/c1/chain、gen headers、patched 三模块均按固定值。
- 环境仅 `env -i` 白名单：`DM_NVN_KEYDUMP=531d637463e53486:1`、PSO/SHDUMP/MEMSTAT 新绝对路径、六原输入、
  en-GB/audio0/headless；无 PSOFAIL_RT/IMGBIND/SSBO_OBS/BINDAUDIT/skip/override/test。

## 1 Gate

`gate.csv`：11 样本，`elapsed` 0.000 → 10.095（**span 10.095 s ≥ 10 s**），最小 available **2832 MiB**（≥2800）；
`launch_at=10.109`。无等待/轮询/第二 gate。

## 2 唯一验收链（`chain.txt`；`boot.log` 行号 251/266/268/282）

[Fenced excerpt omitted from the shareable research record.]

- 同一 frame **1508** / pass **3127**：kd 目标 PS → K st1 目标 PS → d，d 的 VS/PS 与 kd 一致。
- **K st0 存在**（266）：VS `f64e061d85e6f3a5_b`，与 kd/d 三方一致；本次实际 VS 就是 f64e（不是预造，若不如此结论只限新 pair）。
- 目标 pair **无** `failed to create render pipeline` / `failed to load` / reflection 拒绝（`grep` 目标错误为空）。
- `pso_user.tsv` 第 460/461 行有同 pair 的 R 记录（vs `f64e…_b` / fs `531d…_b`）——PSO 第二来源存在。
- 旧计划的失败 psort **不再**作为 success 条件；本次成功条件是实际 draw 记录。
- K/d 为编码路径证据，不证明 GPU 执行/像素/bitcast 数值语义。

## 3 时序、资源、回收

`timing.txt`：

[Fenced excerpt omitted from the shareable research record.]

- 同一单调时基：guest 时长 ≈ **52.47 s**（first−launch）；TERM 后 0.2 s 消失；legacy `launch=0` 忽略。
- `samples.csv` 215 样本：运行期最小 available **2072 MiB**（≥1 GiB），最大 RSS **717776 kB ≈ 700.95 MiB**（≤2 GiB）。
- 日志 38,143 B（<64 MiB）；`shdump` 640 KiB（<32 MiB）；本次 `exemptions.txt` 无 GS 内容豁免条目（无完整 GS dump），
  未扩豁免；无第一个非豁免 dump 停止。
- child `exit=0`；`pgrep dmhost-fout-531d-uint2-645` 无残留。
- 停止原因：`pipeline-final: complete pass=3127 vs=f64e061d85e6f3a5_b k0=present`。

## 4 证明与不证明

**证明（编码期）**：新 facts 库下，目标 pair 越过了旧 pipeline 拒绝——pipeline 建立（PSO R 记录）并实际提交 draw；
同 frame/pass 的 kd/K st0/K st1/d 一致，K st0 提供第三处 VS 来源。

**不证明**：GPU 执行/采样/内容/像素；bitcast 数值语义；NVN 语义或其它 7 个整数 pair；不推广为“整数 RT 已修复”；
PSO 只证明 pipeline 兼容，不等于画面正确。

## 5 文档与状态

- INDEX/EXPERIMENTS 加入本次 run（evidence-run/validated-limited）；实验 README 写就；request 107 补 relay
  `codex-xc3-531d-full645-host-853547661215419595a8fe678aacf54f` 与 `accepted:true`；request 108 原样归档
  （local id `xc3-531d-pipeline-run-108`；relay id 未提供 unknown）。
- HEAD `36bba17`；`git status` 仅既有未跟踪 `XC3-SETUP.md`；AGENTS.md/XC3-SETUP.md/共享 host/旧证据未动。
- 无第二次 launch、无后续离线修复自动授权；停止等 review。


---

## 6 追加勘误（主管 review；原文保留）

- §2/§4 的 “实际提交 draw / draw 提交” 应限定为**编码路径到达 K/d**。`d` 日志位于后续 `enc_r_draw` 之前，
  只能证明 draw 记录已到达编码器，不能凭它证明命令缓冲/GPU 提交或执行。
- 有限检查点成立：PSO 创建成功、编码路径到达 K/d、旧目标拒绝消失；不证明 GPU 执行/像素/bitcast 数值语义。
