# report158 · A2a：真实 replay 消费者接线 + 生产 body CPU 验证（默认关闭，未启用）

日期：2026-10-22 12:1x（本机）· HEAD `1408257`（未变）· 授权：主管 A2a（60 分钟）。无 commit；
无 host build/执行、无 guest/gate/Metal/PSO/device/GPU/采样；7 接口未注册、无真实 producer、slots 未改；route 仍 **NO-GO**。

## 0 结果

- `nvn_mtl.m` 接入**真实 replay 消费者**：include、shadow/helper、`mtl_exec` 顶层诊断入口、主 switch **唯一** `OP_TF_DIAG` case。
- 新增 `TF_DIAG_REASON_BAD_RECORD`（尺寸/对齐错误时 mark unknown，且不读 payload）。
- 生产 body 的 CPU 提取测试：`test_a2` fails 0（normal + ASan/UBSan），两处 mutation 均**编译成功但运行失败**（mut1 7 FAIL / mut2 4 FAIL）。
- off/invalid 完全惰性：不初始化/不改 shadow、不计数、不复制 payload、不读哨兵指针（`tf_diag_case(40,(void*)1)` 安全）。
- A1 off 对拍复核仍 identical（`test_off` 0 FAIL）；未改录制路径。

## 1 变更（只允许文件）

| 文件 | 变更 | SHA256 |
|---|---|---|
| `nvn_mtl.m` | +160 行：include、consumer 块（A2A markers）、`mtl_exec` enter/leave、唯一 case | `b8cdde76846baf0ef3ec097ef50f49412131eee79475109624fe66bb020e5b71` |
| `nvn_tf_diag.h` | +`TF_DIAG_REASON_BAD_RECORD`（其余不变） | `016cced44cf564d07331c7d4d8f0b9454d4fd44ecf8794f5bc9363a12e8212ee` |
| `hle_nvn.c` | **未改**（沿用 A1 的 `dm_tf_diag_get_mode`） | `36863fc4cc56cba3fe969766c094a204e5640abe7d81b7b77ffba09a5b29258b` |
| `nvn_obj.h` | 未改（编号冻结 42） | `8e9f93e2742d0e634c2451c1f6c8583bc262c253c56679c3b87cb1c8efb3221f` |

`git diff --stat`：`nvn_mtl.m +160`、`nvn_obj.h +1/−1`（A1），其余未变。

## 2 接线语义

- **mode 守卫**：每个入口先 `dm_tf_diag_get_mode()`；非 `TF_DIAG_MODE_ON` 立即 return——不初始化、不改 shadow、不计数、不复制 payload、不打日志、不查 key。A1 默认 OFF 且无 startup enable → 真实 producer 不可达。
- **顶层 submission**：`mtl_exec` 入口 `tf_diag_enter()`，用 `g_tf_diag_depth`（`mtl_exec` 递归深度，OP_CALL 是唯一内部重入）判定 depth==0；仅此时 `tf_diag_init`（unknown）+ 清事件计数。
  嵌套 `OP_CALL` 继承 caller 状态；`OP_BEGIN`/`OP_END` 不重置；两处出口（OP_END 的 `return`、循环结束）都 `tf_diag_leave()`。
  这是**观测模型**的保守 reset，不称 NVN reset 语义。
- **case**：`case OP_TF_DIAG: tf_diag_case(h.size, a); break;`——先验 `h.size==40 && a 8 对齐`，再 `memcpy` 32 B 到本地；尺寸/对齐错时**不读 payload**、mark unknown + `BAD_RECORD`；合法时恰一次 copy + 一次 apply。off 即使遇到该 op 也不读 payload、不改状态。
- **snapshot**：`dm_tf_diag_snapshot()` 只读，供 CPU 测试；标 observed replay intent；本轮到 gs-res/kd 输出**未加**任何字段，现有 matcher 不受影响。
- 不泛改 stream 安全/递归逻辑；不向 GPU 产生任何工作。

## 3 CPU 验证（生产 body 提取）

`extract_a2.py` 从 `nvn_mtl.m` 切出并验证：consumer `36a5e7c1…`、OP_END/OP_BEGIN `70b3ccf0…`、OP_CALL `4ff23e24…`
（原文切片；harness 只 stub `g_exec_cur/g_hoist_n/g_ret/g_ret_n/g_nrest/g_fz/fz_unskip/MLOG/dm_tf_diag_get_mode`，循环脚手架是 harness 的，已披露）。
case 位置：`OP_RENDER_COND < OP_TF_DIAG < default`，且 `OP_TF_DIAG` case 唯一。

`test_a2`（fails 0）：

| 场景 | 结果 |
|---|---|
| off / invalid + 哨兵 payload 指针 1 | state memcmp 不变、copies/events=0、无读取 |
| on 单事件 | copies=1、events=1、seq=1、一次 apply |
| hsize 32/39/48/0 | 拒绝、zero copy、unknown + `BAD_RECORD` |
| hsize 40 | 正常 copy 一次 |
| E1 顶层 A → CALL `[End]` → 继续 | 调用后 inactive，继续 Begin 后 active、`begin=0xB0`、events=3 |
| E2 CALL `[Bind0]` | 继承 active、`begin_addr` 不变、bound0=0x2000/0x100 |
| E3 同一子列表 A/U/I 入口 | inactive / unknown / unknown（入口依赖） |
| E4 两次顶层 submission | active → **unknown**（新 submission 重置） |
| E5 skip draw | 状态 inactive、events=2（draw 不 apply TF） |
| E6 无 TF 事件 | unknown |
| E7 嵌套显式 fault | unknown（`INVALID_OPAQUE`），不解引用任何无效指针 |

**mutation**（编译成功、运行失败，非编译失败）：
- mut1 删 `tf_diag_apply` → compile rc 0、run rc 1（7 FAIL）
- mut2 把 apply 移到尺寸校验之前 → compile rc 0、run rc 1（4 FAIL，`BAD_RECORD` 用例被抓）

A1 off 对拍复跑：`test_off` 0 FAIL，off/invalid 仍 96 B identical、alloc 4/4（本轮未改录制路径，属复核而非重做全套）。

## 4 未做 / A2b、A2c（未授权）

- 15 处扫描/优化点（`fz_next`/`ds_scan`/`sdx_walk`/defer/hoist/`frz_op`/cmdstat/allocprof/预编译）**未改**，A2b 未开始；本文的 rg/清单不是运行证明。
- 7 个 TF 接口安装、slots/`nvn_slots.tsv`、observer 字段、真实 producer 均未做（A2c/另审）。
- 真实 route 仍 NO-GO：CPU consumer 通过不证明 TF 实际 inactive、不证明 GPU 写入，也不构成 NVN 语义证明。
- 无 host build/执行；不更新旧 host identity，不重生成库 chain。

## 5 时间/缺口

60 分钟内完成接线、提取、两套 CPU 测试、mutation、SHA/日志。未做：A2b/A2c、真实进程验证（禁止）、
以及把事件与真实 95bf draw 关联的 observer 输出（A2c）。

---

## 6 勘误（追加，旧原文保留；A2a CPU 证据修正）

1. **OP_TF_DIAG case 现在是提取的**：旧 `test_a2.c` 在 harness switch 里手写了该行，不能称“生产 case 提取”。现在
   `extract_a2.py` 切出真实 case 文本（`a2_case_tf.inc`，sha `9a5f30f2…`）并 include；新增 **case 级 mutation**：
   - `mut_nocall`（删 consumer 调用）：compile 0 / run 1（7 FAIL）
   - `mut_relabel`（把 case 挪到 `case 200:`）：compile 0 / run 1（7 FAIL）
   即“标签路由”本身被测试，而不是只 mutate helper。helper 级两处 mutation 保留（noapply 8 FAIL / applyfirst 4 FAIL）。
2. **E5 勘误**：旧 E5 没有 `OP_DRAW` case，靠 `default:` 忽略 draw，不是生产 skip 证明。现在提取真实
   `OP_DRAW`/`OP_DRAW_IDX` body（`a2_cases_draw.inc`，sha `272ef998…`），只 stub draw/imgdiag/ssbo/`g_exec_next`，`g_rc_skip` 分支原文保留：
   - `skip=0`：DRAW/IDX 各调用一次，顺序 1,2；`snap=2`（现有 draw/obs hook 调用计数）
   - `skip=1`：draws=0、snap=0；前后 TF 事件仍 apply（events=2，inactive）
   注意：本轮**未**在生产 draw 里加 TF snapshot hook，所以这里验证的是“现有 draw/obs hook 的调用计数”，
   **不**声称 TF snapshot 路由已被测；"snapshot" 一词在此仅指 hook 计数。
3. **计数器饱和**：`g_tf_diag_events/copies` 改为 `uint64_t` + `tf_diag_count()` 饱和递增（不 wrap）；copy 只在真正 `memcpy` 后计数；
   getter 返回 `uint64_t`。测试置 `MAX-1` 连做两次仍 `MAX`（E8）；饱和计数不代表覆盖完整。
4. **off 覆盖 enter/leave**：`E9` 预置 shadow 0x5a、depth=7、counters 非零，OFF/INVALID 下依次 `tf_diag_enter()/tf_diag_case(40,哨兵1)/tf_diag_leave()`
   → state/depth/counters 全部 memcmp 不变。`E10` 断言正常顶层、嵌套、连续两次顶层后 depth 均回 0。
   同时删除 `mtl_exec` 循环后**不可达**的 `tf_diag_leave()`（唯一正常出口是 OP_END 的 return，其中已 leave）；
   极端 longjmp/crash 退出会留下 elevated depth，**未覆盖**，列为 gap。

### 6.1 新 SHA（旧值作废）

| 文件 | SHA256 |
|---|---|
| `nvn_mtl.m` | `bc0a209565b17823884df3501f659e91ddd99f5a3dab7b78541f3997e0749d25` |
| `nvn_tf_diag.h` | `016cced44cf564d07331c7d4d8f0b9454d4fd44ecf8794f5bc9363a12e8212ee`（未变） |
| `hle_nvn.c` | `36863fc4…`（未变） |
| `nvn_obj.h` | `8e9f93e2…`（未变） |
| 提取件 | consumer `0b54b6d4…`、draw `272ef998…`、case_tf `9a5f30f2…` |

`test_a2` normal+ASan/UBSan fails 0；`test_off` 未受本轮影响（录制路径未改），A1 对拍仍 identical。
未做：A2b/A2c、真实 producer、生产 TF snapshot hook、host 编译；旧冻结 host 未变，新 source 不冒充旧 identity。
