# report164 · TF-PLAN-FIX：观测计划五项修复（实现 smoke，非独立验收）

日期：2026-10-22 15:4x · HEAD `1408257`（未变）· 仅改 `tf-intent-observe-plan/` 的 SSD 计划文件、自身测试与 identity；
未改生产源码、未重编 host、未触 v006 快照/validator 证据、无 commit/push；无 host 运行/GPU/guest/gate/采样。route NO-GO。

## 0 结果

V006 五项 findings 全部修复；`tests/test_fixes.py` 与 `tests/test_tf_next.py` 均 **fails 0**，preflight-only **PASS**。
基础 smoke 不是独立验收；状态 ready-for-independent-verification（V007）。

## 1 pre-fix 与 diff 范围

pre-fix 副本：`tf-intent-observe-plan/pre-tf-plan-fix/`（`pre-fix.sha`：parser `fc48655b…`、supervisor `2d0e7f64…`、
launcher `e41276cd…`、preflight `f222e63f…`、identity `3de49b98…`）。
改动仅：`tfintent_parser.py`、`supervise_tfintent.py`、`launcher.py`、`identity.json`、`tests/*`。
未触碰 `gsres_parser_base.py`（冻结原件仍 `cc7745e7…`）、`gsres-observe-plan/`、`tf-intent-host/`、`v006/`。

## 2 修复项

**F1（supervisor）**：coverage/stop 的 hdr 键改为 `pass_counter/ps/vertices`（原 `pass_/fs/count` 崩溃点）。新增
`_write_final` / `_reclaim` / `_finalize`：证据序列化在独立 try 中，**嵌套 finally 保证 TERM→2 s→KILL→wait 无条件执行**；
任何结构/写入异常 → `supervisor-error` + `evidence-write-failed: …`，并写一份最小 `stop.json`（`success:false`、`evidence_error`），
不假成功。deadline/信号/阈值/退出优先级未改。测试用 fake child + 强制 `_write_final` 抛错：`kind=supervisor-error`、`child.wait` 已调用、
stop.json `success=false`。

**F2（子行）**：链适配层在喂 base 前区分 `[kd]`：仅 `^\[kd\] F\d+ pass \d+ ` 视为 header；`[kd] F…` 但不成形 → `invalid (malformed [kd] header)`；
其余 `[kd]`（attr/stream/uniform/`+offset` 数据）**忽略并保留 raw**。重复完整 header 仍 `invalid`。
未改旧冻结 parser。

**F3（token）**：VS/PS 严格 `^[0-9a-f]{16}(?:_b|_bf)?$`（bare 允许）；GS 严格 16 lowerhex；去掉 endswith 宽匹配。
`_bf` 头仍按 GSRES 契约首 header 终局 `target-not-obtained`，未扩大准入；`_B`/`_bfx`/伪 hex 一律拒绝。

**F4（域）**：`depth` 显式 i32（`-2147483648..2147483647`）；`frame/pass/seq/events/copies/begin/end/draw` 与 bound `addr/size` 逐个校验 u64，
`bound0=valid` 时校验 `addr+size` 不溢出。仅字段域，不发明 GPU 状态约束。

**F5（run 路径）**：新增 `launcher.check_run_path()`，在**创建目录或启动 child 之前**执行：绝对路径、不存在、
最近存在祖先 `realpath` 必须位于 `/path/to/external-drive/xc3/work/experiments` 之下、且与根同 `st_dev`（防符号链接逃逸/跨卷）。
默认 preflight-only 仍不建 run/child。测试：相对、/tmp、已存在、symlink→/tmp 均拒绝；experiments 下 fresh 路径接受。
**不声称物理 SSD 硬件已测**；这是挂载路径/卷身份约束，不采样内存、不跑 df。

**日志包装兼容**：只接受裸 `[tf-intent] ` 与精确 `[dm] [nvn-mtl] [tf-intent] `；其它包含 `[tf-intent]` 的包装/前导空格 →
`invalid (non-exact tf-intent prefix)`，不做 substring 搜索；raw 保留。GSRES/KD 处理未退化（原 base 副本未动）。

## 3 实际结果

| 项 | 结果 |
|---|---|
| `tests/test_fixes.py` | **fails 0**（attr/stream 忽略、重复 header invalid、畸形 header invalid、bare token、`_bf` 契约、i32 边界 4 例、u64 溢出、前缀 4 例、证据异常清理、路径 5 例） |
| `tests/test_tf_next.py` | **fails 0**（原有链语义 + launcher 默认/拒绝 + 零真实 sysctl/vm_stat/ps） |
| `preflight.py`（preflight-only） | **PREFLIGHT-OK**（identity 已刷新：parser `f21ff9e7…`、supervisor `45765d91…`、launcher `d4e3cf43…`、matcher `f21ff9e7…`；host 与四源不变） |

## 4 SHA

| 文件 | SHA256 |
|---|---|
| `tfintent_parser.py` | `f21ff9e7bdb52a85188f7acc9633681767377ca90e1302f49c1173bf40e04d47` |
| `supervise_tfintent.py` | `45765d918c56673fa6329eb62d24d099aa66014b0d07858497b0899c04a7080b` |
| `launcher.py` | `d4e3cf43890f83e68c031fa76f18973e1bf9b087e596f09de802ee98ac7c67b7` |
| `identity.json` | `5599459e2179e7be10eb4be9e29f0769cae5051664402ae5b2f4c633e2d9bee1` |
| `preflight.py` | `f222e63f…`（未变） |
| `gsres_parser_base.py` | `cc7745e7…`（冻结原件未动） |

## 5 未做 / gap

- 未运行 host、未真实 `--launch`、无 gate/guest/GPU/采样；未重跑 V001–V006 套件。
- supervisor 完整 180 s 路径、signal/finally 实战、exemption/dump 分支仅由 fake child 覆盖，未湿跑。
- 路径检查只证明卷/挂载身份与符号链接约束，**不证明物理 SSD 硬件**；测试不采样内存、不跑 df。
- 未覆盖：并发初始化、PROF/big/fullkd、真实 producer 输出、日志落盘校验、F3 命令流边界。
- 验证方反例独立准备；未向其预置答案。
