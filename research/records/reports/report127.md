# report127 · asCompute VS/GS 两 kernel 的 MSL/Metal/PSO 离线 smoke

日期：2026-10-22 06:00–06:25（本机）
HEAD `14082571ea0a1ea515be64b963e4f4d7c39a3097`（未变）；仅 SSD；无生产/lock/profile/facts/库/host/guard 改动、无 gate/guest/资源采样、无 dispatch、无 commit。

---

## 0 四层结果

| 层 | VS | GS |
|---|---|---|
| SPIR-V 输入 | 9364 B / `28c62126…` | 22932 B / `4da87947…` |
| spirv-cross MSL | rc0, 191 行, `b0fa834e…` | rc0, 397 行, `da1d8ecd…` |
| metal -c AIR | rc0, 5536 B, `d6f2bdc2…` | rc0, 7088 B, `3aad83b2…` |
| metallib | rc0, 5515 B, `a286322f…` | rc0, 7067 B, `dd6fea40…` |
| PSO smoke | **ok** main0, TEW32/max1024, 1024 fits | **ok** main0, TEW32/max1024, 1024 fits |

- 输入 SPV 原样复制，零新增 raw 翻译、零 SPV 修改；每 stage 各一次 spirv-cross、一次 metal、一次 metallib。
- 工具：`/opt/homebrew/bin/spirv-cross`（sha `d9dc197f…`，version 输出 `Git commit:  Timestamp: 2026-09-16`）；Apple metal `32023.921`；metallib `AIR-LLD 32023.921`。
- 精确 flags：`--msl --msl-version 20300 --msl-argument-buffers --msl-texture-buffer-native --msl-pad-fragment-output`（compute 无 fragment output；未赋 fout/未做 GL depth/raster rewrite）；metal `xcrun -sdk macosx metal -c -fpreserve-invariance`。
- 无 iOS、无库合并、无旧产物覆盖、无 flags 重试；两 stage 均成功后继续。

## 1 MSL 资源映射（自动 argument-buffer 重排）

### VS `main0`
[Fenced excerpt omitted from the shareable research record.]
### GS `main0`
[Fenced excerpt omitted from the shareable research record.]
- **自动重排**：SPV 的 set0/b1,b2,b3 与 set2/b1 在 MSL 里被压成 argument buffer 内 id0..；例如 GS 原纹理 SPV b2 → MSL id2，原始 cbuf SPV b3 → id1，trb SPV b1 → id0。不能拿 SPV binding 号直接当 MSL id。
- `_17`（`vb_info`）：`uint4 _m0; uint4 _m1; uint4 _m2[32]; uint4 _m3[32];`，偏移 0/16/32/544，总 1056 B；字段语义仍以 source 为准（counts/strides/offsets），MSL 未增加语义。
- `_22`/`_28`：`float _m0[1];`（SPIR-V runtime_array f32）；`_35`：`uint _m0[1];`（runtime_array u32）。MSL 不编码实际 buffer 长度，host 必须按 5-word stride/元素数分配。
- VS/GS 代码内均出现 `spvUnsafeArray<float, 5>`（5 words 局部）；只是 stride/局部大小，不证明成员内容一致。
- `ib_data`/`vb_data0`/`trb_data` 落为 **`texture_buffer<float>`**；原 95bf 纹理落为 **`texture2d<float>` + 独立 sampler**。读写：VS 写 `vertex_output`，读 `vb_info`/`ib_data`/`vb_data0`；GS 读 `vb_info`/`vertex_output`/`trb_data`/原纹理，写 `geometry_vb_output`/`geometry_ib_output`/读 `gp_c3`。

## 2 PSO smoke（无 dispatch）

- 独立 ObjC 工具：`MTLCreateSystemDefaultDevice` → `newLibraryWithFile` → 只为 `MTLFunctionTypeKernel` 建 `newComputePipelineStateWithFunction:error:`；**没有** command queue/buffer/encoder/dispatch/buffer/texture 创建，没有 guest/内存读取。
- 结果：
  - VS `function=main0 type=kernel pso=ok threadExecutionWidth=32 maxTotalThreadsPerThreadgroup=1024 localSize=1024 fits=1`
  - GS 同：`main0`、TEW32、max1024、1024 fits。
- 这只证明两 kernel 在 Metal 可创建 compute PSO，不证明资源绑定完整/command 可执行/GPU 结果。

## 3 边界

- 四层（cross/metal/metallib/PSO）均成功；**没有** spirv-val，故不能称 SPIR-V 通过 validator；也没有 dispatch/GPU/Metal 执行/像素/数值。
- MSL 自动重排后的 argument buffer id 与 SPV set/binding 不是一一对应；host 必须用新 id 布局绑定；本报告不实现 host。
- `vb_info` 的字段语义、`vertex_output`/`geometry_*` 的 5-word 内容、纹理访问是否完整，仍未由该 smoke 证明；仅 stride/声明。
- 未调用 passthrough、未合并两 module、未做 combined Translate。

## 4 文档/状态

- INDEX/EXPERIMENTS 加 exp131（asCompute Metal/PSO smoke/evidence-only）；request 131 归档。
- HEAD `1408257`；`git status` 仅既有未跟踪 `XC3-SETUP.md`；AGENTS.md/XC3-SETUP.md/共享 host/旧证据未动。
- 45 分钟内完成；停止 review，无自动后续。
