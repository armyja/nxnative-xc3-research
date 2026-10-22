# V006-PREFIX-S：真实 MLOG 前缀增量验证

只读冻结 v006 候选与 V005 源；未执行 host（`--help` 也未跑）；父 report/result/证据未改。

## 1. 来源（真实包装，来自 V005 源码）

- `MLOG` 定义（v005 `nvn_mtl.m:72`）：
  `#define MLOG(...) do { fprintf(stderr, "[dm] [nvn-mtl] " __VA_ARGS__); fputc('\n', stderr); } while (0)`
  body SHA `478ff8d0…8707`
- D04 发射（`nvn_mtl.m:5674-5681`）：`kd_tf_intent_line(...)` 成功 → `MLOG("%s", tfl)`，
  `tfl` 以 `[tf-intent] ` 开头 → 实际行 `[dm] [nvn-mtl] [tf-intent] frame=…`。
  context SHA `42b55dc0…2cb5`
- gs-res 同样经 `MLOG("%s", line)` → `[dm] [nvn-mtl] [gs-res] …`（base parser 已支持该前缀）。
- KD 头是 `fprintf(stderr, "[kd] F…")`，**裸**、无 MLOG 前缀。

## 2. 结果（6 项，5 FAIL）

| 用例 | 结果 |
|---|---|
| P1 裸 `[tf-intent]` 对照 | **PASS**：链完成 `hit` |
| P2 真实 `[dm] [nvn-mtl] [tf-intent]` | **FAIL**：链 `result=None`，不完成也不报错（一直等待） |
| P3 真实行是否保留在 `chain.raw` | **FAIL**：`raw=[]` |
| P4 `parse_tf_intent` 直接解析真实行 | **FAIL**：`not a tf-intent line` |
| P5 supervisor 是否保留该行 | **FAIL**：`.lines` 只有 kd+gs 两条 |
| P6 supervisor 是否完成 | **FAIL**：`validated=0`、`intent_obtained=0`、`terminal=None` |

结论（按源码证据，不采用主管猜测）：真实前缀**不是** `[tf-intent]` 裸行，而是 `[dm] [nvn-mtl] [tf-intent]`；
候选只识别裸行，导致真实 capture 的 TF 行被静默丢弃——既不完成也不终止，也不保留 raw。

## 3. F1 finally 是否越过 child 清理

控制流：coverage/stop 写入位于 `finally:` 内的 `try/except OSError`（`supervise_tfintent.py:282-290`）；
KeyError 不是 OSError → 直接抛出 finally 块，随后同块内的 child TERM/KILL/wait（291-297）与 timing.txt（299）
都被跳过。已有合成证据：S1/S2/S5 exit 1 且无 stop.json。未产生真实残留（也不需要）。

## 4. 证据

- `prefix-supplement/result.json`、`report.md`、`evidence/prefix.json`、`logs/prefix.log`
- reproducer：`python3 prefix-supplement/prefix_test.py`

## 5. 限制

CPU、合成；无真实 host/capture；父证据未回写；route NO-GO。
