# report157 · A1：TF 诊断事件录制契约 + 纯 CPU 模型检查点（未接线）

日期：2026-10-22 11:4x–12:0x（本机）· HEAD `1408257`（未变）· 授权：主管 A1（60 分钟，仅 repo working-tree 编辑 + CPU 测试）。
无 commit/amend/push/PR；无 host build/执行、无 shader build/translate、无 Metal/PSO/device/GPU、无 guest/gate/采样。
`nvn_mtl.m` **完全未改**（SHA 与 pre-A1 基线一致）；真实 route 继续 **NO-GO**。

## 0 结果

- 新增 `dm/gfx/nvn/nvn_tf_diag.h`（payload/开关/保守影子模型，纯 C 可 include 测试）。
- `nvn_obj.h` 仅在 `OP_RENDER_COND` 与 `OP_COUNT_` 之间 append 一个 `OP_TF_DIAG`；实测 **OP_RENDER_COND=41、OP_TF_DIAG=42、OP_COUNT_=43**，既有 opcode 数值不变（extract.py 对 baseline 逐名比对通过）。
- `hle_nvn.c` 仅在 `rec` 附近新增 1 个 record helper + 7 个按 `nvn_protos.h` 签名的 typed 适配函数；**未用 NVN 宏注册、未改 nvn_init_slots/slot 选择、未改 nvn_slots.tsv**，真实进程不可达。
- 纯 CPU 测试两枚，`-Wall -Wextra -fsanitize=address,undefined`：`test_off` fails 0、`test_model` fails 0。
- off/invalid 与 pre-A1 序列**逐字节一致**（长度 96/96，memcmp identical，alloc 4/4）；on 模式产生 8 条 40 B 记录（含 header）。

## 1 变更与基线

pre-A1 基线（含当时 dirty 状态，非 HEAD 替代）：`/path/to/external-drive/xc3/work/experiments/tf-diag-a1/baseline/` +
`baseline.sha`：`hle_nvn.c 9194c782…`、`nvn_obj.h 852a61f0…`、`nvn_mtl.m faf06a9b…`、`nvn_kd_res.h 9956f931…`。

A1 后：

| 文件 | 变更 | SHA256 |
|---|---|---|
| `dm/gfx/nvn/nvn_tf_diag.h` | 新增 | `532087a2dc1c4c6f0d7d6d915debf90958796911d8e61dca14b5bed4a9305462` |
| `dm/gfx/nvn/nvn_obj.h` | +1 opcode（2 行内 diff） | `8e9f93e2742d0e634c2451c1f6c8583bc262c253c56679c3b87cb1c8efb3221f` |
| `dm/gfx/nvn/hle_nvn.c` | +26 行（include 1 + block 25） | `4d1276c67cbc9382475649a678e0c161772dc7ee0ae39f30fb04abf84c56e705` |
| `dm/gfx/nvn/nvn_mtl.m` | **未改** | `faf06a9b840d98de480ccc599e5ba3f849e3e6c814af6249518c9fc0e3669ec8`（=基线） |
| `dm/gfx/nvn/nvn_kd_res.h` | 未改（既有 dirty） | `9956f931b3a25eb10c82a08fb926a0b5dd27789b315b55860e33ba26aaab4642` |

`git status`：`M hle_nvn.c`、`M nvn_mtl.m`（既有 gsres）、`M nvn_obj.h`、`?? nvn_tf_diag.h`、`?? nvn_kd_res.h`、`?? XC3-SETUP.md`。
`git diff --stat`：hle_nvn.c +26、nvn_obj.h +1/−1、nvn_mtl.m +120（全部为既有 gsres 改动，本轮未触碰）。

## 2 契约

payload（32 B，8 对齐，`sizeof`/`offsetof` 静态断言在 header 内）：

| off | 0 | 4 | 8 | 12 | 16 | 24 |
|---|---|---|---|---|---|---|
| 字段 | `kind:u32` | `flags:u32`(0) | `index:i32` | `count:i32` | `addr:u64` | `size:u64` |

- kinds：`BIND=0`、`BIND_PLURAL_OPAQUE=1`、`BEGIN=2`、`END=3`、`PAUSE=4`、`RESUME=5`、`DRAW_OPAQUE=6`、`INVALID_OPAQUE=7`。
- 单条记录 = `op_hdr{op=42,size=40}` + 32 B payload；header+payload 40 B、8 对齐。
- `DRAW_OPAQUE`：`index` = `NVNdrawPrimitive`，`addr` = API 的 `NVNbufferAddress`，`size=0`。
- `BIND_PLURAL_OPAQUE`：只记 `first/count`，**不解引用 ranges、不写输出、不读 guest 内存**，不声称 bound 已知。
- 开关：`DM_NVN_TF_DIAG` 仅字面 `"1"` 启用；absent/empty/`"0"` 关闭；其它 invalid → 按关闭处理。A1 只提供 `tf_diag_parse_mode()`，**无 lazy getenv**。

## 3 off/inert 验收（关键）

方法：`extract.py` 从 **pre-A1 baseline 与新树**分别切出真实 `rec()` body（sha `8a3f9608…`，两者逐字节相同），
并从新树切出真实 TF 适配块（sha `933525f5…`）；harness 用确定性 fake `cmd_alloc`（bump + 计数）+ 固定字节 buffer，
回放同一条既有命令序列（`OP_BEGIN`/`OP_BIND_TEX`/`OP_DRAW`/`OP_END`）。

| 场景 | 长度 | memcmp | alloc 调用 | 结果 |
|---|---|---|---|---|
| pre-A1 序列（无 TF 调用） | 96 | — | 4 | 基线流 `109cfee3…` |
| A1 off + 7 个 TF 适配调用穿插 | 96 | **identical** | 4 | 同 `109cfee3…` |
| A1 invalid（`"1x"` 等） | 96 | **identical** | 4 | 同 `109cfee3…` |
| A1 on | 416 | 不同（预期） | 12 | `28369229…`，8 条 40 B 记录 |

- off/invalid 下 `alloc_calls` 与基线相同（0 条新增 alloc），plural 适配器传哨兵指针 `1` 未读取（无崩溃）。
- 三次独立运行结果稳定（off_old/off_new SHA 相同）。
- **边界**：这证明的是“同一 fake 命令内存器 + 同一 rec body 下 off 不改变字节流”，不是真实 host 全标题回归。

## 4 CPU 模型（observed replay intent）

`test_model` 覆盖（全部通过，`reason` 逐条核对）：

| case | 序列 | 结果 |
|---|---|---|
| C1 | 无事件 | unknown，gate 拒绝 |
| C2 | Begin→（观测点）→End | inactive，gate 允许 |
| C3 | End 无 Begin | unknown（`END_WITHOUT_BEGIN`），**非** inactive |
| C4 | Pause 无 Begin | unknown（`PAUSE_WITHOUT_ACTIVE`） |
| C5 | Begin/Pause/Resume/End | inactive；含“paused 中重复 Begin → invalid/unknown” |
| C6a/b/c | 子列表 `L=[End]`，入口 active/unknown/inactive | inactive / unknown / unknown（`END_WHILE_INACTIVE`） |
| C6d | 子列表 `L2=[Bind0]`，入口 active | 继承 active/running，bound0 valid（CALL 不清零） |
| C7 | DrawOpaque | unknown（`DRAW_OPAQUE`） |
| C8 | off 期录制的流（无事件） | unknown（不补 inactive） |
| C9 | 显式 fault 事件 | unknown 且 bound0 失效 |
| C10 | skip 的 draw 无事件；顺序敏感 | 状态保持；End 之后再来 opaque → unknown |

其它：flags≠0/addr+size 溢出/bind size=0/count≠1/index=5/kind=99/plural → 全部 fail-closed（`BAD_PAYLOAD`/`INDEX_UNSUPPORTED`/`PLURAL_OPAQUE`）；
seq 饱和（u64 不回绕）→ unknown + `SEQ_SATURATED`；`sizeof(p_tf_diag)==32`、`offsetof(addr)==16` 静态断言通过。

**模型 vs 生产边界**：`test_model` 的 stream executor 只解释 `OP_BEGIN/CALL/END/TF` 作为模型，**不是** `mtl_exec`；
A1 不宣称真实嵌套 CALL / NVN 语义已证；“Begin→running”仍是命名假设；`inactive` 只是观测模型结论，不是 TF 写入/GPU 语义证明。

## 5 未做（A2，需主管另派）

1. replay 接线：主 switch `OP_TF_DIAG` case（注意 `default: break` 会静默跳过）+ 影子状态 apply。
2. 15 处扫描/优化点逐处 barrier（`fz_next`/`ds_scan`/`sdx_walk`/defer 两处/hoist/`frz_op`/cmdstat/allocprof/预编译），全部**待实际验收**。
3. 7 个 TF 函数在真实 slot 表的安装（off 保留原 stub、on 显式安装），`nvn_init_slots` 选择与 `nvn_slots.tsv` 变更审批。
4. submission 边界 reset 语义（置 unknown）与 `mtl_exec` 实际递归/无效 handle 行为核对。
5. observer 记录字段（`tf=`/`tf_bound0`/`tf_begin_addr`，默认关）。
6. 真实 95bf 观测仍 NO-GO：A1 只是录制契约，不证明 TF 实际 active/inactive，也不产生 GPU TF 写入。

## 6 时间/缺口

60 分钟窗口内完成：header/枚举/适配器/两套 CPU 测试/off 字节流对拍/SHA 与基线记录。未做：A2 全部、
真实 host 编译验证（本轮禁止）、以及把模型 case 与真实 replay 流关联（需 A2）。

---

## 7 勘误（追加，旧原文保留；A1 复核两条 P1 修正）

复核发现两个模型缺口，已在 `nvn_tf_diag.h` 修正并加测试；旧 SHA 作废，新 SHA 见 §7.2。off/inert 对拍不变。

### 7.1 修正

1. **running 中重复 Begin 必须失效**：旧逻辑只在 `active && paused` 时失效，`Begin→Begin` 会静默保持 active。
   现改为 **active 的任一 pause 态**下再 Begin → unknown（paused 用 `BEGIN_WHILE_PAUSED`，running/未知用 `BEGIN_WHILE_ACTIVE`），
   其后 `End` 仍为 unknown（`END_WITHOUT_BEGIN`）、gate 0。正常 U/I 入口的 Begin 仍按模型假设处理，不新增 NVN 语义主张。
2. **饱和 sticky unknown**：旧逻辑饱和后后续合法事件可把状态改回 inactive。现 `tf_diag_apply` 在 `saturated` 时直接
   `tf_diag_sticky_saturated()` 返回：active/pause 保持 unknown、bound 失效、reason 固定 `SEQ_SATURATED`、seq 固定 `UINT64_MAX`；
   **last_index/last_count 冻结在饱和前最后一个事件**（明确规则，不再更新）。
3. **typed signature 编译期保证**：`hle_nvn.c` 适配块后新增 7 条 `_Static_assert(_Generic(&fn, NVNT_…))`（按 `nvn_protos.h` 原型，
   含 Bind 的 `size_t`、plural 的 `const NVNbufferRange*`）；**未注册、无运行时影响**。CPU harness 对切片出的真实适配体
   施加同样的 7 条断言（测试文件内声明同名 `NVNT_` typedef）。

### 7.2 新 SHA（旧值作废）

| 文件/产物 | SHA256 |
|---|---|
| `nvn_tf_diag.h` | `69d5d6ecebd149cba1f8d43d309ecb80b6278f7ceda5cfed418c7feaa942e039` |
| `hle_nvn.c` | `36863fc4cc56cba3fe969766c094a204e5640abe7d81b7b77ffba09a5b29258b` |
| `nvn_obj.h` | `8e9f93e2742d0e634c2451c1f6c8583bc262c253c56679c3b87cb1c8efb3221f`（未变） |
| `nvn_mtl.m` | `faf06a9b…`（未改） |
| off 流（old=new） | `109cfee3…`（与 A1 首版相同，off 对拍不受影响） |
| on 流 | `28369229…`（416 B / 8 条 40 B，未变） |

### 7.3 测试结果（normal + ASan/UBSan，fails 0）

- `test_off`：off/invalid 仍是 96 B、memcmp identical、alloc 4/4；哨兵指针未读；on 416 B、8 条记录；7 条签名断言编译通过。
- `test_model` 新增：
  - **C11a** `Begin→Begin`（running）：unknown、reason=`BEGIN_WHILE_ACTIVE`（修前此反例得到 active、gate 1）；
  - **C11b** 其后 `End`：仍 unknown（`END_WITHOUT_BEGIN`）、gate 0；
  - **C12** `seq=MAX-1`：第 1 个事件到 MAX（未饱和），第 2 个事件饱和 → unknown/`SEQ_SATURATED`；随后 `Begin/Bind(index 5)/Pause/Resume/End`
    逐个断言仍 unknown/unknown、bound 失效、reason 不变、seq=MAX、gate 0；`last_index` 冻结在饱和前值。
- 旧 C1–C10 全部保持通过；C5 的“paused 中重复 Begin”仍按 `BEGIN_WHILE_PAUSED` 失效。

**边界不变**：CPU 模型不是 `mtl_exec`；`inactive` 只是观测模型结论；A1 不证明 TF 实际状态或 GPU 写入；A2 未授权，route 继续 NO-GO。

## 8 时间/缺口（本轮 20 分钟）

完成：两条 P1 修正 + 7 条 signature 断言（生产块与 harness 两侧）+ 新 case C11/C12 + SHA/日志更新。
未做：A2 全部；未重跑旧 A1 证据以外的任何东西；旧 baseline/log 保留未覆盖。
