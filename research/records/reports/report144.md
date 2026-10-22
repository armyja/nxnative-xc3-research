# report144 · observer P1 修复 + actual-wrapper stub tests

日期：2026-10-22 17:40–18:25（本机）
HEAD `14082571ea0a1ea515be64b963e4f4d7c39a3097`（未变；repo 仅诊断文件未提交）；仅 SSD/CPU；无 guest/GPU/device/PSO/资源创建/翻译/raw/cross/metal、无 commit。

---

## 0 P1 修复

- **key 表示域统一**：`g_gsres` 同时保留 8B decoded key 与 canonical 16-lowerhex `gs_hex/ps_hex`；PS 比较用
  `pr->sh[1]->key` 的 16B ASCII 与 `ps_hex`，不再拿 ASCII 与 decoded 8B 做 16B memcmp。`kdr_parse_cfg` 只接受
  16 lowerhex:16 lowerhex；大写/短/坏 hex 拒绝。
- **query_calls 事实**：`kdr_gs_identity` 不再清零 `query_calls`；wrapper 累计真实 `prog_key_cached` 次数，日志与 stub
  调用次数一致（test 断言）。
- **PS style**：`kdr_ps_style` 验证完整 16 lowerhex；bare=16、`_b`=18、`_bf`=19；短/17/坏 hex→invalid。
  目标 base 但 `_bf` → target-not-obtained；**其它完整 PS（不同 base）也 target-not-obtained 并记录 actual PS，
  不读 GS 状态**；不再静默 return。
- **pass label**：日志 `pass_counter=N final_pass_association=none`，不冒充 final pass 关联。
- **registry**：`g_ntreg>0`/`g_nsreg>0` 先检查；tid/sid 索引前检查；`ok` 先判再复制 descriptor/sampler；`g_treg`/
  `g_sreg` NULL 拒绝；`sid64` 保持 u64 比较后才窄化；`S.samp` 独立 raw。
- **key 拷贝**：`r.vs`/`r.ps`/`r.ps_style` 的 snprintf 返回检查，截断→diagnostic-error+close，不当正常 record。

## 1 actual-wrapper stub tests

- `tests/wrapper_stub.c` 从修复后 `nvn_mtl.m` **原样提取** `gsres_init`/`kd_res_line`/相关 state，`prog_key_cached`、
  `MLOG`、`getenv`、registry、locks、h_ser 用可计数 stub；不是重新实现匹配器。
- ASan/UBSan rc0/fails0，覆盖：absent no-query/no-log；uppercase invalid once/closed；other PS 和 `_bf`
  target-not-obtained 且零 GS query；短 PS diagnostic；bare/_b hit；hit 一次后 closed；partial hit/nohit；
  full mismatch；nil GS；nstage0/7；index5；registry NULL；sid OOB；mask/omitted；query_calls 与 stub 调用相等。
- **index5 修正**：测试改为 `nstage=6/stub_nstage=6`，keys0..4 已知非目标，target 仅在 index5；断言 stub query=6、
  `nstage=6`、`gs_query_calls=6`，不再由 index0 目标误命中。
- **mutex 文本限界**：stub 提取 body 中有 4 处 `pthread_mutex_lock/unlock` 文本替换为计数 stub，不是 100% 原样；
  生产锁未变。其余匹配/格式化 body 原样；该限界已记录，不称“逐字全原样”。
- **未覆盖**：真实 renderer 调用、off non-nil 运行时、invalid once 的 host 运行时、实际 guest registry、TF、cbuf contents；
  它们是后续 guest/真实 wiring 缺口，不是本轮运行证明。

## 2 新 host

- `dmhost-gsres2`（sha `9f3df170…`）独立路径，active `fout-six-lgt-correct645`/chain `c7c374c3eb34` 头；compileline/
  log/identity 保存；编译 rc0（55 既有 warning、0 error），**未运行**。
- 旧 `dmhost-gsres`（sha `c8b7bd9f…`）保留为 **not guest-ready**（旧 ASCII/decoded 比较 bug）；旧 source/header/host/
  diff 在 `evidence-old/` 冻结。
- 旧 host 编译成功不证明 observer 可命中；新 host 也只到编译层。

## 3 剩余缺口/状态

- 8192B 有 per-append 检查与 masks/slot/omitted 测试；**未做所有字段同时最大的穷举容量测试**，记为 gap（设计保守
  估算仍 <4KiB，但未用实际最大 record 断言）。
- observer 仍默认关闭；无 guest/device/GPU；cbuf contents unavailable；TF unknown；descriptor/view/final resource 未观测；
  PS2e16 资源/RT 未扩。
- 工作树：`nvn_mtl.m` 修改 + 新 `nvn_kd_res.h` 未提交；其它 profile/库/lock/chain/旧 host 未改。
- 文档 INDEX/EXPERIMENTS 加 exp148（observer fix/actual-wrapper tests/experimental host2）；request 148 归档。
- 45 分钟内完成；停止 review，无自动 guest/GPU/下一步。
