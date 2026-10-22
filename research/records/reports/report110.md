# report110 · 有界 batch psort 诊断实现 + host + 测试（无 guest/gate）

日期：2026-10-22 02:00–02:35（本机）
HEAD **`4ca03256b3b329fcda01d9ead8202bd28e4b14c5`**（本地诊断提交，父 `36bba17`）；无 guest/gate、无 profile/facts/库/译器/lock 改动。

---

## 0 文档更正（主管 review）

- report109/evidence-table/README/pairs.tsv 已更正：6 个 MSL 均声明 `texture2d<uint>`，各仅一次 `.read(...).x`，**无 `.write`**；
  此前“都写 uint image”错误。不能从 image kind/uint 声明推写；RT 未知结论不变。

## 1 实现（诊断专用）

- 新文件 `dm/gfx/nvn/nvn_psort_multi.h`：纯 C 的固定 key 解析、签名/去重/配额状态（生产 helper，测试直接 include）。
- `nvn_mtl.m`：
  - `DM_NVN_PSOFAIL_RT_MULTI` 接受 **1–6 个完整小写 16-hex**；重复/非法/超限整体拒绝并一次日志；absent/empty 关闭。
  - 与单目标 `DM_NVN_PSOFAIL_RT` 同时非空 → 明确 conflict、两者 disabled，不静默覆盖；单目标格式/日志/行为保持不变。
  - 复用真实 `rp_begin` 之后的 color/depth/stencil/sample 快照与真实 `pso_get_` 失败路径；每 key 独立状态，**不全局
    disarm**；不重新读 `R.rt`、不物化 shader、不 cache clear/重编。
  - signature = `cfmt[8] + map_enabled + lmap[8]`（identity 单独编码，不含 serial/尺寸）；每 key 独立去重、不跨 key 合并。
  - 每 key 最多 2 个签名、全局最多 12 条完整记录；每条 header/map/8 slots/done 都带 `[psort] batch=1 rec=N key=...` 前缀，
    保留 actual VS/frame/pass/snap/assoc/context。
  - 重复签名静默去重、不关 key；cached failure 每 key 最多一条 note，**不关闭 key、不占第二签名**；首次 cached 无快照时
    不伪造记录；第三签名一条 `signature-limit coverage-capped` 后该 key 终局；mismatch 记录保留但 assoc=mismatch、
    消耗一条配额且不算 valid；格式化错误 `diagnostic-error` 不耗配额、该 key 终局；全局 12 条上限有确定界。
  - 未改 `g_pso`/`g_pso_fail`、PSO/cache/格式/选择行为。
- `psort_arm()` 只在 `rp_begin_ex_` 调用（真实 pass 路径），不在 prewarm/predictor/no-pass 路径。

## 2 测试（无 guest）

- `integer-batch-pilot/tests/test_psort_multi.c` 直接 include 生产 helper：off/empty/single-only/conflict/dup/大写/短串/
  7key/6key、bare/_b/_bf 查找、首记录/重复/第二签名/第三限一次/跨 key 同签名不合并、cached 只 note 一次且不关 key/
  其后第二签名可收、全局 12 条与 global note、非法/上限有界。`fails: 0`。
- 主机编译验证接线；**未运行 host**，因此集成运行时行为仍未测（能力限制如实声明）。
- 测试日志/校验：`tests/run.log` sha `da6e89c6…`；`impl.diff` sha `fd31d231…`；helper sha `b5c97edf…`。

## 3 Host

- `linkcheck/dmhost-batch-psort-multi` sha256
  **`11c32dd231997b18099de5eb38da46563a29912a09afb6de379241ab97654ca9`**；用 `fout-d3c-uint3-correct645` 链
  `35de4665bff4` 的 generated headers，rc0/0 errors；strings 新链 1、`batch=1` 15 处；旧/共享 host 未覆盖。
- `dmsh_chain.py`：诊断源码不在 chain FILES，chain 仍 `35de4665bff4`；check-tools 首次因本 shell 未设
  `DOTNET_ROOT` 报 translator 启动失败，设置后 rc0；未改工具/lock。

## 4 Batch supervisor/launcher 设计（仅文字，不实现）

- 环境仅 `DM_NVN_PSOFAIL_RT_MULTI=<6 固定 key>`；KEYDUMP/PSOFAIL_RT/IMGBIND/SSBO_OBS/BINDAUDIT/skip/override/test 不继承；
  PSO/SHDUMP/MEMSTAT、六输入/enGB/audio0/headless、gate 2800/10s、180s、两 GS、完整 dump 优先不变。
- supervisor 按 `batch=1 rec=N key=...` 分组，严格 header/map/8 slots/done；同 key 每条独立结算；`same-pass + snap=valid`
  才算 valid；mismatch 标 unassociated 不算 valid；cached note/diagnosticerror/limit note 只作 coverage 记录。6 key 各
  至少 1 valid 可停，第二签名只在预算内提前出现时收；部分集合如实报告，缺 key 即缺证据，不传播 facts、不补跑。
- 本轮不实现该 supervisor，也不 launch。

## 5 边界

- 仅编码期 pass 附件快照；不证明 GPU/内容/像素、数值/bitcast 语义；不推断 NVN→MTL；不推广其它 pair。
- 12 条上限/每 key 2 签名可能漏掉后续用途；首失败记录有偏差；无失败则无 slot；cached/limit 只说明覆盖不足。
- 未改 profile/facts/库/工具/lock/GS/TF；active d3c 检查点保留。

## 6 用户提供的资源（待主管评估）

用户列出以下 XC3 渲染逆向资源，问主管是否可加速研究流程（我未据此做任何实现或外部访问）：

- ScanMountGoat `xc3_lib`（文件格式/着色器分析工具集）：https://github.com/ScanMountGoat/xc3_lib
- `xc3_wgpu`（同仓库，wgpu 渲染器）：https://github.com/ScanMountGoat/xc3_lib
- `xc3_shader`（shader 提取/反编译）：https://github.com/ScanMountGoat/xc3_lib/blob/main/xc3_shader/README.md
- `xc3_gltf` / 架构说明：https://github.com/ScanMountGoat/xc3_lib/blob/main/ARCHITECTURE.md
- Xenoblade Rendering Research（GBuffer/纹理/材质等）：https://scanmountgoat.github.io/xenoblade-rendering-research/
- CEDEC+KYUSHU 2022 笔记（NPR/超采样）：https://zhuanlan.zhihu.com/p/588630949
- URP 复刻 Mio 讨论：https://zhuanlan.zhihu.com/p/588630949
- 火焰时钟特效复刻：http://www.80aj.com/
- yuzu 2022-08 进度报告与 XC3 兼容页：https://yuzu-mirror.github.io/
- CB0 对齐修复提交（8/16-bit load/store）：https://git.duckduckwhale.com/
- Xenoblade Data Hub：https://xenobladedata.github.io/
- World Tree Research Discord（社区）

请主管评估：其中是否有可用于本项目（例如 shader/GBuffer/材质/格式对照、已知对齐修复线索）的加速点，以及是否值得
在后续离线分析/诊断设计中引入；我不会自行访问或改变 scope。

## 7 文档与状态

- INDEX/EXPERIMENTS 加入 exp112（diagnostic+host/evidence-only）；实验 README 写就；request 111 补 relay
  `codex-xc3-integer-batch-pilot-design-ff7dd29ad75448568551d72e03241c81` 与 `accepted:true`；request 112 原样归档
  （local id `xc3-batch-pilot-impl-112`；relay id 未提供 unknown）。
- HEAD `4ca03256…`（本地提交，未 amend/push）；`git status` 仅 `XC3-SETUP.md`；AGENTS.md/XC3-SETUP.md/共享 host/旧证据未动。
- 未 guest/gate、未实施 batch supervisor/launcher；停止等 review。


---

## 8 追加勘误与修复（主管 review；原文保留）

- **duplicate cap bug**：旧 `psm_accept` 先查配额后查重，A/B 两个签名后再 A 会返回 -1 并 done。已改为**先对所有已存
  签名去重，再查 per-key/global 配额**；两个签名已满后重复 A/B 返回 0、不 done、不 note；global 12 满后重复已存签名
  也返回 0、无 global note；只有真正的新第三签名才一次 `coverage-capped`。
- **map canonicalization**：`map_enabled=0` 时签名固定为零/identity，未启用的 lmap 字节不参与签名；enabled=1 仍区分
  八个真实值。
- **missing-snapshot note 无界**：改为生产 helper `psm_snapshot_gate` 每 key 一次 note，不关闭 key、不占配额；重复
  missing 静默，之后有效 snapshot 仍可记录（测试覆盖）。
- **diagnostic-error 配额语义**：旧实现 `psm_accept` 在格式化前已 `nrec++/global++`，`psm_error` 只 done，实际会消耗
  一次配额。现明确为**保守 record-attempt 预算**：`nattempts/global_attempts` 重命名；format-error 消耗一次 attempt，
  但不计 valid/complete；上限 12 仍是 attempt 上限。报告/字段/日志统一为 attempt 语义，不宣称尝试数等于完整记录数。
- **actual frame/pass**：batch header 现在打印**当前失败尝试**的 `frame/pass`（`g_cur_frame`/`g_stat_pass`），
  snapshot 的 frame/pass 单独放在 `snapframe/snappass`；done 用同一 actual pass；`assoc` 仍按生产 serial+cfmt，不把
  snapshot pass 冒充当前 pass。测试覆盖 current!=snap。
- **测试能力边界**：helper/wrapper 逻辑（parse/accept/gate/fields/cached/limits）已测；host 只做编译链接验证，未运行
  renderer，因此 off 零复制、capture 接线、真实 report 输出仍属“未运行验证”，不称已运行证明。
- 旧 host 身份：同名 `dmhost-batch-psort-multi` 的旧二进制 `11c32dd2…` 已被本次重建的 `03c93b09…` **覆盖**；旧 binary
  未另存，旧 hash/报告留存，不声称旧 host 全保留（不为恢复旧 binary 另编）。
- 新 host：`linkcheck/dmhost-batch-psort-multi` sha256
  **`03c93b09f450b138078263e6496de85a9ccb43aec3335083e8a3b7f28ba25477`**（原 35de4665bff4 头，rc0/0 errors，batch=1
  15 处、snapframe 1 处）；chain 仍 `35de4665bff4`，check-tools rc0；提交 **`af094f47`**（父 4ca03256）。
- 回归测试 `fails: 0`（覆盖 A/B 后重复 A/B、global cap 重复、map0 lmap 差异、current!=snap、missing 一次/后续有效、
  format-error 消耗 attempt）。旧证据保留。

## 9 主管对用户资源的评估（摘要，供附文档参考；不授权安装/换锁）

- **优先采用** `xc3_lib`/`xc3_shader`/`xc3_wgpu` 作为外部对照：`xc3_shader` 的输入→GBuffer 依赖图可用于追
  albedo/normal/packed 通道，胜过按文件名猜材质；wgpu 的显式 pipeline/sampler 可对照 pass 语义，但其自述偏
  portable/readable、非原机精确，**不可当 groundtruth，也不能抄 binding 号当 NVN slot**。保持 pinned 0.21.0，未来
  引用固定 commit。
- **Xenoblade Rendering Research**：作者原始研究，高层 GBuffer/材质/通道解释可作命名/分析线索；作者自写 unknown，
  类型/句柄真值仍以本项目 shader+descriptor 为准；texture 名只是约定，按 shader 用途判通道。
- **yuzu Aug2022 报告**：可列历史故障线索（SPIR-V 声明/空 image view/vertex format fallback），不能用旧兼容性状态推
  当前 Metal 问题。**CB0 线索**已定位 Ryujinx 提交 `476b4683cf` / PR3897（8/16-bit LDG/STG 地址对齐，曾修 XC3 视频
  像素化）；不是 NVN table base/SSBO110/integer RT 输出问题；可留 future 源码对照任务（当前 vendored 是否已含、
  自建 accessor 是否同条件），本轮不改译器/lock。
- `xc3_gltf` 适合资产/通道人工对照，非 runtime renderer 替代；DataHub 低优先；CEDEC/NPR 复刻仅视觉意图参考（所给知乎
  两条同 URL 且本次取不到，不当硬件证据）；80aj 首页未定位火焰钟文章、duckduckwhale 仅首页、Discord 无公开 thread，
  均不采用/不抓取。无新资产导出或第三方安装授权。
