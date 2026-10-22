# report162 · A2c-fix：observer 显式 KDR_HIT 守卫 + 安装结果/发布顺序（候选，未验收）

日期：2026-10-22 14:0x · HEAD `1408257`（未变）· 授权：A2c-fix（25 分钟），实现方角色。
无 commit/push；未改模型/格式/barriers/slots 表/obj/profile/库/lock/chain；未 hostbuild/执行/guest/GPU/gate/采样；未改 validator 或冻结 candidate。route NO-GO。

## 0 两项修复

- **F1/D04**：共享 `emit:` 出口显式加 `r.result == KDR_HIT` 短路——新增 `kd_tf_intent_wanted(r)`（`r && r->result == KDR_HIT && tf_diag_on()`），`kd_res_line` 用该守卫替换裸 `tf_diag_on()`。
  non-hit（diagnostic-error / target-not-obtained / gs-key-mismatch）走到该出口也不会 snapshot/format/intent 输出；原 gs-res 原文与 one-shot（`g_gsres.closed = 1`）逻辑未动。不声称 MLOG 落盘已校验。
- **F2/D02**：`tf_diag_install_adapters()` 返回 `int`（1 成功 / 0 失败）；新增 `tf_diag_activate(int requested)`：先安装，**安装完成后**才发布 `g_tf_diag_mode` 与 `g_tf_diag_mode_fixed`；getter 在发布前恒返回 OFF；仅 7 个全部成功才 effective ON；失败时一次 `[tf-intent] diagnostic not enabled: installation failed, effective mode OFF` 并保持原 slot。
  `nvn_init_slots` 改用局部 `tf_requested` 调 activate，只调用一次、无 retry、无 runtime setter。
  **准确区分**：缺陷不是 partial slot writes（写入仍是全部校验后 all-or-none），而是“失败/进行中时 mode 发布顺序与失败语义不明确”；本次修的是返回值+发布顺序+失败日志。

## 1 SHA

pre-fix：`tf-diag-a2c-fix/pre-a2c-fix/` → `hle_nvn.c de46fccb…`、`nvn_mtl.m a3e43b03…`。

| 文件 | SHA256 |
|---|---|
| `hle_nvn.c` | `029efe768623a7753be3bfd9bd365a9ca2cff62821343e3f8a002ba3bdedfcdb` |
| `nvn_mtl.m` | `ee708ad5143889302ae91e38a73f4bb1e73e07e7282d1f11ba1abd44b24f3105` |
| `nvn_tf_diag.h` | `b27fb321…`（未变） |

修改函数：`hle_nvn.c`：`tf_diag_install_adapters`（返回 int）、`tf_diag_activate`（新）、`nvn_init_slots`（局部 requested + activate）；`nvn_mtl.m`：`kd_tf_intent_wanted`（新）、`kd_res_line`（守卫）。

## 2 检查（基本，非验收）

- 语法：`nvn_mtl.m` rc=0 / 0 error；`hle_nvn.c` rc=0 / 0 error（日志在 `tf-diag-a2c-fix/`）。
- A2c 既有 smoke（真实 install/formatter 切片）仍 fails 0：S1 7/7 安装、S2 占用全不装、S3 缺名全不装、O1–O3 字段/绑定/溢出。
- **gap**：本轮新增的 `tf_diag_activate` / `kd_tf_intent_wanted` 两处辅助面的 CPU smoke 未完成（harness fake 环境改到一半超时，已回退到 A2c smoke，不含这两个 case）。它们只经生产文件语法检查，行为未由 CPU 用例覆盖；不声称已验证。

## 3 未测项

- `tf_diag_activate` 的 ON 成功/失败/发布顺序 CPU 用例；`kd_tf_intent_wanted` 的 HIT/非HIT×ON/OFF 用例（均缺，见 §2）。
- 并发初始化线程安全、`DM_NVN_PROF` 包装交互、F3 stream 内存边界、真实 producer/observer、V005 独立验收：未动/未测。
- 未声称日志写盘成功；未声称整体通过。

## 4 边界

仅 working tree 实现；候选冻结供主管 V005 snapshot；不自行验收、不启用 host、不启动下一步。
