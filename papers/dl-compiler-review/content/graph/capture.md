## 图从哪里来：捕获的四种形态 {#graph-capture}

**字节码改写。** PyTorch 的 Dynamo 在 Python 帧的执行层截获代码，把字节码解释成图（`torch/_dynamo/convert_frame.py:2562` 起，具体工作在 `symbolic_convert.py:1489` 的 `InstructionTranslatorBase` 与 `:5758` 的实现里）。这条路的代价全部集中在“假设”上：图是按某一次执行记录下来的，记录时成立的条件必须被守卫住。守卫模块的文档字符串把这件事说得很直接——它检测程序状态、张量属性或控制流的变化，从而决定什么时候必须重新编译（`torch/_dynamo/guards.py:13-15`）。重新编译有上限（`torch/_dynamo/config.py:121` 的 `recompile_limit = 8` 与 `:124` 的 `accumulated_recompile_limit = 256`），到顶之后停止为该代码生成新版本。

**JIT 前端管线。** MindSpore 把捕获做成了一条正式的编译管线：`mindspore/ccsrc/frontend/jit/ps/` 下 `action.cc`、`pass.cc`、`pipeline.cc` 对应动作、变换与管线三层，无法编译的构造则被替换成执行 Python 的结点（`fallback.h:40-44` 的 `CreatePyExecuteCNode`）。与 Dynamo 的差别在于“假设”的表达方式：Dynamo 用守卫在运行期检查，MindSpore 把不能编译的部分留在图内，让它在运行期照常执行。

**显式导出。** 把捕获从执行过程里剥离出来，单独得到一个可序列化的图：PyTorch 一侧是 `torch/export/`（该包里提供把模块导出为图的能力），MindSpore 一侧是 MindIR 及其加载器（`mindspore/core/load_mindir/`、`mindspore/core/proto/`）。离线导出让图可以被保存、检查与推迟编译，代价是导出之后不再有原来的运行时可供回退：导出时覆盖不到的东西，之后也不会出现。

**前端导入。** TVM 的图是翻译来的：`python/tvm/relax/frontend/` 下有 `nn`、`onnx`、`stablehlo`、`tflite` 与 `torch` 五个入口。这条路没有“捕获”问题，取而代之的是翻译覆盖率问题——源格式里的一种写法若没有对应表达，就要在导入阶段决定是报错还是近似。

四种形态背后有一个共同点：**图的边界就是编译器的边界**。落在边界内的一切可以被整体优化，落在边界外的只能按原样执行。

Triton 与 CuTe 在这个坐标里处在端点：它们没有图层。Triton 的 `lib/` 下只有 `Analysis`、`Conversion`、`Dialect`、`Target`、`Tools` 五个目录，编译单位是一段块级程序；CuTe 编译的是模板实例化。没有图就意味着没有“记录下来的执行”，也就没有守卫与图断裂这两种负担——代价是算子之间的融合与内存复用也一并交给了使用者。
