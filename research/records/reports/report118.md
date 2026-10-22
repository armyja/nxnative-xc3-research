# report118 · keydump 命中 draw 的 GS 身份诊断 + host

日期：2026-10-22 04:40–05:05（本机）
HEAD `14082571ea0a1ea515be64b963e4f4d7c39a3097`（诊断提交）；无 guest/gate/GS 实现/译器改动/库重建/profile/facts/lock 变更、未 push。

---

## 0 report117 限界更正

- `dataflow.py` 只找最近 Dest、递归 SrcA/B/C，不完整建模 predicated 合流/多分量写入/全 CFG；Mov 只记说明不递归。
  “a841 userattr 不依赖 Texs”改为“简化回溯已追踪路径未见；未证明全路径无依赖”。正向 Texs→Ffma→位置路径与 4 PT Emit
  的发射数结论仍成立，不扩每输入 primitive 解释。

## 1 目标链 PS 完整 key（重算）

从既有 `shd_post.wishp` Slct92 program0 重新 hash，完整 key：
- VS `d1657e5077b26d1d`（#92:0:0）
- GS `95bfab6122539993`（#92:0:1）
- PS **`2e16c536b845ea0e`**（#92:0:2）

有序 VS/GS/PS 结构确认；这只是未来选择 PS 的依据，**不是运行时 GS 已绑定/已执行**的证明。

## 2 诊断实现（最小）

- 在 `kd_draw` 真正匹配 PS、`left` 消耗并打印原 `[kd]` 头之后，调用一次 `kd_geom_line(dw,di)`；head 不变，旧 parser 可忽略
  新行。off/不命中/超次数在到达该行前已 return，零 query。
- 只读 `S.bst[2]`（`bind_stages` 的 NVN geometry 位 2 来源），不读 `S.prog` 合成对象、不读 `pr->sh[2]`。
- 对 `gs->nstage` 的 input index `i`（仅 `i<nstage` 且 `i<6`）调用 `prog_key_cached` 的 lookup-only 适配器；不调用
  `prog_key/prog_get/shader_get`、不 hash、不读 control/data、不把 input index 当 stage。
- 输出：
  `[kd-geom] F… pass … source=present/<serial>|none nstage=N cached=H/N drawkind=direct|indexed prim=<raw>
   count=… instances=… base_instance=… indirect=0|1 keys=[16hex|unknown,...]`
  - nil source=`none`；nstage=0 或 >6=`keys=unavailable`；部分 cache 的未命中=`unknown`（不是 absent）。
  - indirect 时 count/instances/base_instance=`unavailable`，不读 GPU args/guest memory。
  - 所有 snprintf 返回值检查；溢出打印 `diagnostic-error` 并抑制 partial line，不静默称完整。
  - 未写死目标 95bf；cachedhit 由离线 matcher 判。
- 无分配/GPU lookup/物化/渲染状态修改。

## 3 测试

- `nvn_kd_geom.h` 生产 helper（构建/格式化）在 SSD `tests/test_kd_geom.c` 直接 include 测试，`cc -Wall -Wextra`：
  **fails 0**。覆盖 nil source、nstage0/7（零 query、unavailable）、partial cache（6 index、第6命中）、full keys、
  direct/indexed、indirect counts unavailable、off/not-hit 零 query、32B buffer overflow 明确拒绝。
- 测试只证 helper 与接线顺序，不称 renderer 已运行；真实 host 仅编译链接验证。

## 4 Host/身份

- 新独立 host `linkcheck/dmhost-six-lgt-kdgeom` sha256
  **`7b500780961084b02c3a5f1c9aac6954badbedfe4b6e334376af899c947afe8f`**；compileline/build.log/rc/strings 留档。
- 使用当前 `fout-six-lgt-correct645` 头/chain **`c7c374c3eb34`**；9 facts sha `492151bd…`、宏/profile 未变；chain 仍
  `c7c374c3eb34`，check-tools rc0；诊断头未进 chain FILES；未重建 645/未改锁；未运行 host、未运行 launcher/guest。
- 源码提交 `1408257`（`nvn_mtl.m` + `nvn_kd_geom.h`，armyja，未 amend/push）。

## 5 仍 unknown / 下一步

- 仍未观测真实 input topology；GS 是否在该 draw 真正执行、primitive 的实际含义、SPV interface 33/37 的 Location/BuiltIn
  仍 unknown（本轮未新开翻译/反汇编）。
- 下一最小动作：只运行一次该 host + KEYDUMP（未来授权）取得同一命中 draw 的 `cachedGS=95bf` 与 raw prim；若需 topology，
  另设计受控观测，不把默认 Triangles 当事实。不扩 KEYDUMP 解析器、不实现 GS、不动 guard/两豁免。

## 6 文档

- INDEX/EXPERIMENTS 加 exp121（kd-geom diagnostic / evidence-only）；request 120 补 relay
  `codex-xc3-gs-dataflow-raw95bf-df2c6e8e5fbb43ff8c2ca5502736cd72` 与 `accepted:true`；request 121 原样归档
  （local id `xc3-kdgeom-121`；relay id 未提供 unknown）。
- HEAD `1408257`；`git status` 仅既有未跟踪 `XC3-SETUP.md`；AGENTS.md/XC3-SETUP.md/共享 host/旧证据未动。
- 结束停 review，不实现 launcher、不启动 guest。
