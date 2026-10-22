# report143 · 默认关闭只读 GS 资源 observer 实现 + CPU/编译

日期：2026-10-22 16:45–17:35（本机）
HEAD `14082571ea0a1ea515be64b963e4f4d7c39a3097`（未变，工作树仅有本轮未提交诊断改动）；仅 SSD；无 guest/GPU/device/PSO/资源创建/翻译/raw/cross/metal、无 commit。

---

## 0 结果

- 实现默认关闭的 95bf-keyed 只读 observer：新 `dm/gfx/nvn/nvn_kd_res.h` + `nvn_mtl.m` 接线；无 cbuf 内容读取、
  无 MTL/guest 指针解引用、无对象创建、无 alloc。
- 修改后的 `nvn_mtl.m` 单文件编译 rc0；实验 `dmhost-gsres` 用 active `fout-six-lgt-correct645` profile
  （chain `c7c374c3eb34`）独立输出编译 rc0（55 个既有 warning，0 error），**未运行**。
- CPU helper tests（含 ASan/UBSan）rc0/fails0；覆盖 cfg/identity/index5/registry/format/small-buffer/mask/max/NaN bit。
- 旧 host/旧证据未覆盖；原 HEAD/DLL/profile/lock/chain 未改。

## 1 开关/触发

- `DM_NVN_GSRES=<16hexGS>:<16hexPS>`，目标由未来 env 传入（本轮不硬编码 XC3 key）；解析 once：
  absent → latch off、无日志；invalid → 一条日志后 close；valid → on。
- 只在现有 `kd_draw` 的 PS key 真实命中分支、`kd_geom_line` 之后调用；KEYDUMP 未命中/off/invalid/closed 时
  **不查 GS key、不复制 slot/state、不计数**。
- PS 精确 bare 或 `_b` 才继续；`_bf`/其它完整 PS 在 base key 匹配时记 `target-not-obtained`，不当常规命中；
  不扩大 KEYDUMP 次数、不改变 `kd_draw` 返回、不强迫 draw。
- GS 用 `S.bst[2]` + `prog_key_cached`，最多真实 capacity 6，不 materialize/hash/control-read：
  nil→`no-geometry-source`；nstage0/>6→`identity-unavailable`；partial 有 hit→hit；partial 无 hit→`identity-unavailable`；
  fully known 无 hit→`gs-key-mismatch`。**没有 knownskipped/notreached**；未调用/无 final record 只能由上层记
  `no-record-obtained`。记录在 draw 前/encoder 前，不声称 final-pass 关联。

## 2 记录

- geometry stage=2（`S.bst[2]` 来自 `OP_BIND_PROGRAM.stages` bit2 经 `bind_stages`；实际 state，不用注释）。
- UBO：16 槽 `addr||size` mask + slot0 addr/size；`contents=unavailable`；无 mtl_addr/mtl_gpu_addr/arena。
- tex/samp：各 128-bit mask（2×u64）、nonzero count；slot0 必列，至多 8 个其它非零 slot raw handle；`omitted` 明示。
- `bind_source=current_S_state`；无 lastbind，不造同绑定/时间；0 是已读值，另有 availability。
- tex0：raw handle、tid、`h_ser` hint（独立 atomic serial）与 registry serial 分开；`g_rmu` 内先检查
  `g_treg && tid>0 && tid<g_ntreg && ok`，再复制 `t.d` target/format/w/h/d/samples + serial；不返回裸对象。
- sampler：`sid64=rawhandle>>20` 先用 u64 检查再窄化；`g_rmu` 内 `g_sreg && g_sreg_ok && sid64<g_nsreg` 后复制
  `samp_par`；LOD/border 保留 32-bit 位型；`S.samp` 独立 raw state 另列，不冒充 combined sampler。
- TF=unknown（host 没有 Begin/End/Bind 状态）；不因 StreamOutMask/日志推 off。PS2e16 资源/RT 未扩。

## 3 有界输出

- `KDR_REC_CAP=8192`；每条 append 检查 `vsnprintf` 返回值；不足 → 一条 `[gs-res] diagnostic-error` 后 close，
  **不截断后发 normal done**。
- 最坏组成：keys ≤6×17、tex/samp 各 ≤9×~40、masks/desc/sampler 位型/固定文本；保守估算 <4 KiB，8192 足够；
  已用 small-buffer 测试验证失败路径。
- 最终任何 record（hit/mismatch/unknown/not-obtained）输出一次后 close；不逐帧/draw 等待。

## 4 CPU/编译层级

- helper tests `dm/gfx/nvn/nvn_kd_res.h` 直接编译（ASan/UBSan）：
  off/absent/invalid/valid cfg；partial/full/nil/nstage0/7/index5；UBO 相关为纯记录字段；tex/samp registry NULL/
  未注册/id==ntreg/sid越界；mask 0/63/64/127/max u64；NaN bit；small buffer；duplicate/omitted由 wiring 逻辑审查。
- **未覆盖**：真实 renderer 调用、off non-nil zero query/slotcopy 的运行时、invalid once/close 的运行时、实际 guest
  registry、TF、cbuf contents；这些是 wiring/guest 缺口，不冒称运行验证。
- 实验 host 编译：`dmhost-gsres` 独立路径，`-I$D/gen`（fout-six game_profile.h）在 repo gen 前，profile chain
  `c7c374c3eb34`；compileline/log/identity 保存；不改共享 dmhost、不运行。

## 5 剩余缺口/状态

- cbuf contents 仍 unavailable（无安全 pin/锁/alias 证明）；TF unknown；texture descriptor/view/final resource 未观测；
  PS2e16 资源/RT 未扩；无 guest 真实 case。
- 工作树改动：`dm/gfx/nvn/nvn_mtl.m`、新 `dm/gfx/nvn/nvn_kd_res.h`、`DM_NVN_GSRES` 接线；未 commit、未改
  profile/facts/chain/lock/库/旧 host。
- 文档 INDEX/EXPERIMENTS 加 exp147（observer implementation/CPU+experimental compile）；request 147 归档。
- 60 分钟内完成；停止 review，无自动 guest/GPU/下一步。


---

## 6 范围/接线勘误（主管 review；旧结果保留）

- “仅 SSD”不准确：本轮确有 repo 内 `dm/gfx/nvn/nvn_mtl.m` 修改与新未提交 `dm/gfx/nvn/nvn_kd_res.h`；产物/测试在 SSD，
  诊断源码未提交，其它生产 profile/库不改。
- 旧 `dmhost-gsres` 编译成功**不代表 observer 接线可命中**：旧版把 ASCII PS key 与 8 字节 decoded key 做 16B memcmp，真实目标
  会直接 return；旧 host 登记为 **not guest-ready**，不再使用。
- 旧 source/header/host 已冻结在 `gsres-observer-fix/evidence-old/`；新 host 为 `dmhost-gsres2` 独立路径。
