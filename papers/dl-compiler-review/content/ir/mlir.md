## MLIR 在这些栈里的真实位置 {#ir-mlir}

MLIR 是一套用来造 IR 的基础设施：它提供方言机制（一套可扩展的操作与类型定义）、pass 管理器、以及把一种方言转换到另一种方言的框架。Triton 的每个方言都用自己的 TableGen 文件定义属性与类型（`include/triton/Dialect/TritonGPU/IR/TritonGPUAttrDefs.td`、`TritonGPUTypes.td` 等），转换代码单独放在 `lib/Conversion/` 下——这正是使用 MLIR 的典型形态：**新的一层用新方言表达，层与层之间用转换模式连接**。

按仓库里的提及规模看，这些栈与 MLIR 的关系差别很大：

| 栈 | 源码中提及 MLIR 的文件数 | 它把 MLIR 放在哪里 |
|---|---|---|
| Triton | 302（`lib/` 与 `include/`） | 编译主干的实现语言 |
| CuTe DSL | 149（`python/CuTeDSL/`） | 第二套前端与编译入口 |
| PyTorch／Inductor | 17（`torch/_inductor/`） | 若干可选后端 |
| TVM | 3（`src/` 与 `include/`） | 借用来的算法与设计 |
| MindSpore | 1（`mindspore/ccsrc/`） | 可选的内核生成器之一 |
| TileLang | 百量级（`src/` 与 `python/`） | 仅在 `cutedsl`／`ptodsl` 这类可选代码生成后端上经过 CuTe DSL 间接使用 |

Triton 这一栏需要配一句说明：LLVM／MLIR 不在它的仓库里，而是一个钉住版本的外部依赖。`cmake/llvm-info.json` 记着一个固定提交 `llvm_hash: b010a18d2b648cab83c83967ff26b8fde11acdc6`，并为各平台列出预编译包的 sha256（`almalinux-x64`、`almalinux-arm64` 等），另有 `FindLLVM.cmake` 与 `llvm-build-info.json`。接受 MLIR 的方言机制，同时也接受了它的版本节奏：换一次 MLIR 版本意味着跟进整套 API。

CuTe 的 Python 前端同样建在 MLIR 上，但用法更接近“自己拿一个编译器”：`python/CuTeDSL/cutlass/base_dsl/compiler.py:169` 的构造函数接收一个 pass manager 与一个执行引擎，编译入口分 `compile`（`:221`）与 `compile_and_jit`（`:326`）两条。

PyTorch 那一栏最能说明“提及不等于依赖”。Inductor 里提到 MLIR 的 17 个文件全部集中在带 `cutedsl`／`flydsl` 的路径与 `codegen/pallas.py` 上——也就是 CuTe DSL、FlyDSL 与 Pallas 三个可选后端（例如 `codegen/cutedsl/cutedsl_kernel.py`、`codegen/flydsl/flydsl_utils.py`、`runtime/cutedsl_cache.py`）。主干编译链（FX 图 → 循环级 IR → 生成的 Triton／C++ 源码）与 MLIR 无关。MLIR 因此是从**外部后端**进入 PyTorch 的，而不是从主干。

一个小结：MLIR 提供的是公共的可插层语法基础设施，它自己不规定任何一层该长什么样。用它换来的是一条可以在中间任意加层的管线，付出的代价是跟随它演化的成本，以及把编译期的一部分控制权交给这套框架的规则。