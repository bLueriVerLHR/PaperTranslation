## 自建 IR：借用算法，自建表示 {#ir-own}

TVM 在源码里提到 MLIR 的地方只有三处，而这三处恰好说明了它借用什么、不借用什么。第一处是 pass 基础设施的设计来源：

```cpp
// 编者定位：repos/tvm · 2bb1a553be19 · include/tvm/ir/instrument.h:23
 * This file introduces a pass instrument infrastructure, inspired by LLVM and MLIR.
```

后两处在整数集求解上，代码直接标出了算法来源与可切换的实现：

```cpp
// 编者定位：repos/tvm · 2bb1a553be19 · src/sym/presburger_set.h:22
 * \brief Integer set based on MLIR Presburger set
```

```cpp
// 编者定位：repos/tvm · 2bb1a553be19 · src/sym/presburger_set.cc:46
#if defined(TVM_MLIR_VERSION) && TVM_MLIR_VERSION >= 150
```

把这三处放在一起，TVM 的姿态就很清楚：**设计与算法可以借鉴，IR 本体与基础设施自己保有**。它自己实现 pass 管理（`include/tvm/ir/instrument.h` 所在的 `tvm/ir`）、自己实现整数集求解（`src/sym/`），并在编译开关允许时把后者换成 MLIR 的实现。收益是语义可以按需要设计——`tirx` 里的 tile 原语、执行作用域与 `RegionStmt` 都是一般 IR 不预设的东西；代价是调试器、FFI、pass 基础设施这一整套都要自己维护。

这一点在依赖清单上能看出来：`3rdparty/` 下除第三方算子库（`cutlass`、`libflash_attn`、`tensorrt_llm`）之外，还有 `tvm-ffi`——把跨语言调用层单独拆出来维护。而“不用 MLIR 做 IR”并不妨碍接它的生态：`python/tvm/relax/frontend/` 下的五个前端里就有 `stablehlo`，也就是 MLIR 生态的交换格式，另外四个是 `nn`、`onnx`、`tflite` 与 `torch`。图可以从别的格式翻译进来，不必经由同一种 IR。

MindSpore 的情况更朴素：它有一套自己的图表示（`mindspore/core/ir/anf.cc` 与 `func_graph.cc`，ANF 形式的函数图）与可序列化的格式（`mindspore/core/load_mindir/` 与 `mindspore/core/proto/`）。整个 `ccsrc` 里只有一处提到 MLIR，而且那处把 MLIR 列成了一个可选项：

```cpp
// 编者定位：repos/mindspore · c91ca93fd5b37e4f61b0db00994573da86127c5e · mindspore/ccsrc/include/runtime/hardware_abstract/kernel_base/graph_fusion/graph_kernel_flags.h:228-232
  /**
   * Kernel Generator.
   * The generator used to compile kernels, AKG or MLIR or DVM.
   */
  std::string kernel_generator{"AKG"};
```

字段名是 `kernel_generator`，默认值 `"AKG"`，同行的注释列出另外两个候选 MLIR 与 DVM。这说明，在这一栈里图由 MindSpore 自己的表示承载，MLIR 只承担**内核生成后端的候选之一**：走到设备侧时，再选择由谁来把它变成内核。这与昇腾那一章看到的边界一致——前端与选择在开源仓里，内核生成在仓库之外，而生成器的种类是可以配置的。
