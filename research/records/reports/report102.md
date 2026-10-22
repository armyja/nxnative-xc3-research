# report102 · 单目标 integer-RT psort 计划与 no-guest 测试（无 gate/guest/host 执行）

日期：2026-10-22 00:52–01:12（本机）
HEAD `36bba17c0f45d22c78ce987dcfe177f2860d81cc`（未变）；无生产代码/配置/facts/库/build/翻译变化、无提交。
计划目录：`/path/to/external-drive/xc3/work/experiments/integer-rt-531d-psort-plan/`
证据基线：`tex27-writeflag-correct645`（active 有限检查点保留）。

---

## 1 report101 勘误（追加，不改旧文）

- “12 个 pipeline 失败中 8 个”更正为 **8 个唯一整数 pair / 9 次 integer 失败**（`f64e/531d` 出现两次），加
  **3 次 interface 失败** = 12 条 pipeline 失败。
- 现有 `DM_NVN_PSOFAIL_RT` 是**单个 16-hex 目标**，第一次目标 fragment pipeline 失败后记录一次即 disarm；不能在
  一个 run 内覆盖 8 个 pair。psort 的 pass 附件快照**不是** `pso_user.tsv` 的内容。本轮只做单目标，不扩诊断范围。

## 2 目标与只读身份

- 目标 PS `531d637463e53486`（历史 run 行 270；VS `f64e061d85e6f3a5`，程序 `shd_post#44:0`，包
  `ps_shd_post_s44p0.bin`，MSL `color0..3 float4`，Metal 报 `R8Uint`）。这只是**最早重复失败 pair**；新 run 不假定
  同 VS 或同 RT。
- 复用 host `dmhost-tex27-texfinal` sha256
  `4552318d911aa16a69c2a5b7594f37909c34e789592b2994d3f6e0e1a882592e`，chain `8c02a1137b0d`，tex27 profile；
  **未重建 host、未加 hook、未重复实现 psort**。
- preflight 只读确认：host 二进制含 `[psort]` 与 `DM_NVN_PSOFAIL_RT`；map 645/0、pairs 90/0、json+metal+metallib
  完整、c1 链名、patched 树/三模块基线；目标 stage pixel、包/source 身份、MSL 恰好 color0..3 四个 float4；
  程序 `shd_post#44:0` 仅 VS+PS（无 GS），目标为 PS、历史 VS 为 VS。
- 实际输出：`host_sha 4552318d…`、`keys 645`、`pairs 90`、`c1 # chain b-8c02a1137b0d`、`patched 47985583…`、
  `target {key 531d…, stage ps, package ps_shd_post_s44p0.bin, source shd_post#44:0:1:ps, colours [0,1,2,3]}`、
  `preflight ok`。

## 3 计划与 matcher（`supervise10.Psort`）

- 沿用 reviewed 单进程监督/gate/guard/cleanup/env/阈值/两条 GS 内容豁免/六输入；launcher 默认 preflight-only。
- 唯一成功：目标 psort **header**（fs 全 key 或 `_b`）→ **map** → **slot0..slot7 恰好依序各一次** → **done** 同 key
  （canonical）、同 pass、同 assoc、`slots=8`，且 map 已出现。
- `assoc=mismatch` → terminal `psort-unassociated`（不用于结论）；`cached failure` → `psort-cached`（无 descriptor
  record）；`diagnostic-error` → `psort-diagnostic-error`；disabled/错 key 的 switch → `psort-invalid-switch`。
- 重复 header/map/slot、slot 乱序、缺槽后 done、错 pass/key、done 无 header → terminal invalid；之后的“好记录”不能
  补救；arm 行仅信息，不是快照；`_bf` 不匹配；bare/`_b` canonical。
- 成功写 `psort.txt`：完整 header（cfmt/ctx 等）、map、8 条 slot 原文、done；terminal 写 `psort-terminal.txt`
  （已有部分证据）。物理 slot 不当作 logical location；`map enabled=0` 仅在日志显式 identity 时这样解释。

## 4 Launcher / 环境

`run-psort.sh` 默认 preflight-only；`--launch`（未授权、本轮未执行）会 exec `supervise10.py`，设
`DM_NVN_PSOFAIL_RT=531d637463e53486`、PSO/SHDUMP/MEMSTAT、六原输入、en-GB/audio0、180 s 含 10 s/2800 MiB 采样锚定
gate、reviewed 运行阈值；不继承 KEYDUMP/IMGBIND/SSBO_OBS/BINDAUDIT 或其它 override/test。替身 supervisor 只验证
路由/env/gate/180 s/六输入，真实 host 不执行。

## 5 测试（no-guest，`tests/run.log` 全过）

- `t_preflight` / `t_preflight_negative`：host/chain/profile/map/pairs/三件套/c1/patched/target 颜色/程序结构；负例
  （假 patched、89 pairs、缺 metal、目标颜色数错）全部在 host 执行前拒绝。
- `t_psort`：success（bare/`_b`）、arm-alone、其它 fs/`_bf` 忽略、重复 header、slot 乱序/重复/8 后、done 太早/
  无 header/错 pass、重复 map、缺 map、assoc mismatch、cached、diagnostic-error、disabled、arm-wrong-key、
  cached/invalid 后好链不能补救。
- `t_gate`、`t_launch_guard`：gate 拒绝/signal 不启动 child；matcher smoke 成功。
- `t_launch_path`：真实 launcher 默认 preflight-only、无 run 目录；替身 `--launch` 路由 host/2800/10/180、
  PSOFAIL_RT、无冲突开关、PSO/SHDUMP/MEMSTAT、en-GB/audio0、六输入。
- `t_e2e`：synthetic child success/half-line/assoc/cached/diagnostic/bad-arm-then-good/done-early；成功写
  `psort.txt`，terminal 不写；child 回收。

## 6 产物哈希

| 文件 | sha256 |
|---|---|
| `supervise10.py` | `bcbd584ef4dfe790bcf8e3b4dbd8df94cc022c2feee23c1cd82415147963d8e6` |
| `run-psort.sh` | `f47ef4380a1a239d93f1c0caa39e694eb5c38249ebeda6490458c31d9df06e92` |
| `preflight.py` | `9b92d901014a7acd2c779255f40b563e62357c9a6b95a6dffb70045f56c620e9` |
| `exempt.json` | `844029072907f30d833f3ba05764f701ef9c10e0484e806e6d7731d62a7500c3` |
| `tests/t_psort.py` | `b77a302eac18bb433aaf6aa0d24dd74e2fc8d1c83a02a3ff995e3ed49332d378` |
| `tests/t_e2e.py` | `c79df5cdae191b361945b6a01909308eb4cce7ee58b8946b72f1e29cba3ee3c3` |
| `tests/run.log` | `f0b090078fb4b71a253a87914a6d237f07b66c33fdb6a4ef99f3b714cbc00ef6` |

## 7 边界与状态

- 未 gate、未 guest、未运行 host；未改生产代码/配置/facts/库、未翻译、未提交。
- psort 记录仅编码期 pass 附件快照（header/8 槽），不等于 `pso_user.tsv`，不证明 GPU 执行/内容/像素；不把物理 slot
  当 logical location；不假定新 run 的 VS/RT。
- 不扩诊断范围、不做多目标/8 pair/uint 候选比较；active tex27 检查点保留。
- 文档：INDEX/EXPERIMENTS 加入 exp103；计划 README/plan 写就；request 102 补 relay
  `codex-xc3-posttex-blocker-audit-91dca9b59dc1457691f034f56ee99793` 与 `accepted:true`；request 103 原样归档
  （local id `xc3-integerrt-psort-plan-103`；relay id 未提供 unknown）。
- HEAD `36bba17`；`git status` 仅既有未跟踪 `XC3-SETUP.md`；AGENTS.md/XC3-SETUP.md/共享 host/旧库证据未动。
- 停止等 review，不自动授权 launch。


---

## 8 追加勘误（主管 feed 反例；原文保留）

主管直接 feed 生产 `Psort` 复现：合法目标 header → `slot0 garbage … slot7 garbage` → 合法 map → done，旧 matcher 返回
`psort complete`；即使 map 在 slots 之后也 complete。原因：旧 `RE_PSLOT` 只认 `slot<N> ` 前缀、未要求 map 先于 slot、
未校验 slot/header 字段形状。旧版本 hash `bcbd584ef4dfe790bcf8e3b4dbd8df94cc022c2feee23c1cd82415147963d8e6`；旧失败证据见
`tests/old-version-counterexample.txt`（旧 run.log 已被通过的套件替换，故以该文件保留反例与旧 hash）。

**最小修复**（仅 matcher/tests）：
- header 必须完整匹配生产格式：fs/vs、frame/pass、`assoc=(same-pass|mismatch)`、`snap=(valid|missing)/<serial>`、
  **8 个 cfmt**、dfmt/sfmt、ctx `defer/fzchk/fz/phase/fsfn/ms/fzkind` 全到尾；目标 key 的截断/坏字段 → terminal invalid。
- map **恰好一条且在第一个 slot 之前**：只接受生产 `enabled=0` identity 原形，或 `enabled=1 physical->logical=` 恰 8 个
  lmap 值；garbage/截断/额外值/超 u32 → invalid；map 晚到或重复 → invalid。
- slot 行必须完整匹配生产的两种既有格式（`cview=0` ignored 分支与 `cview=1` 字段分支），字段缺失/截断/坏数字/超范围
  （nvn/attached/setfmt/setlv/setly 仅 0|1，hex ≤ 0xffffffff，ser uint64，dims/type/level/slice/dp 等 ≤ u32）→ invalid；
  slot 必须依序 0..7，`slot10`/乱序/重复 → invalid。
- done 完整匹配且 canonical key/pass/assoc/slots=8；目标 done 无 header → invalid。
- `same-pass` success 额外要求 `snap=valid`（生产 assoc 已含 `g_psort.valid`）。**源码核对**：`g_pass.serial` 与
  `g_stat_pass` 是 renderer 中两个独立计数器（`g_pass.serial` 在 rp_begin 递增，`g_stat_pass` 另行递增），未证明恒等；
  因此 matcher **不**强加 `snap serial == header pass`，保留生产 `assoc` 为主字段。
- `assoc` 只允许 same-pass/mismatch；垃圾 assoc 的 header 视为 truncated/malformed → invalid，不当作正常 unassociated。

**测试更新**：slot/header/map 全部改用真实生产格式；新增/覆盖 slot 前无 map、map 晚到、garbage slot、slot 中途截断、
`slot10`、坏 map、enabled1 八值 map、两种 cview 完整格式、cview1 截断/坏 flag、header 截断/坏 assoc/cfmt 溢出、
map 值溢出、snap=missing 与 same-pass 矛盾、bad-then-good 不补救；`t_e2e` 至少两个 invalid 经真实 supervisor 入口
（map-late、garbage-slot）证明 terminal、无 `psort.txt`、child 回收；gate/cleanup 未改、host 未重编。

新 hash：`supervise10.py cf2e4234e9979fa0d73d39861b0973a60278ffdd1f2bcb788f271be5541e79c9`、
`tests/t_psort.py 6e71f9dac08cb6b91ad4f5fc63b0c663cf71e117bbd4dba2630cd5e49acd5e6b`、
`tests/t_e2e.py b7362dbe8cdc13c4365b782863c661c809cd4d9b11503c189f5e9fad86aa9d35`、
`tests/t_launch_guard.py f2d5a3bad2a39fdadcd4a31c6cfbfea0d9121344c49e83224073f4a4f22c8a81`、
`tests/run.log 9e05af23a5a7f6bed6fb14d205a8418f5816edc484f64e7b0c57b530771e10bb`。
