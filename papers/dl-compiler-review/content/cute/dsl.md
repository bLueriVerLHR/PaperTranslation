## Python 前端与第二套编译入口 {#cute-dsl}

C++ 模板那条路的问题在上一节已经露出来：合法性检查依赖静态形状，失败信息埋在模板实例化里。仓库给出的第二个入口把同一套布局代数搬到 Python 上，编译改走 MLIR。前端位于 `python/CuTeDSL/cutlass/`，子包按职责分成 `base_dsl`、`core`、`cute`、`cutlass_dsl`、`memory` 与 `_mlir_helpers`。

编译器的对象结构说明这条路与模板实例化共用多少东西、又换掉多少。`python/CuTeDSL/cutlass/base_dsl/compiler.py:169` 的构造函数接收两个外部对象：

```python
# 编者定位：repos/cutlass · 0b55a2f691d6 · python/CuTeDSL/cutlass/base_dsl/compiler.py:169
  def __init__(self, passmanager: Any, execution_engine: Any) -> None:
```

一个 pass manager 与一个执行引擎，两者都由 MLIR 提供；`_mlir_helpers` 子包承担与它们对接的工作。编译入口有两条：`compile`（`:221`）产出编译结果，`compile_and_jit`（`:326`）在此基础上继续建立可调用的执行入口。围绕这条链还配了一组面向使用者的控制面——诊断异常的专门类型 `CompilerDiagnosticError`（`:122`）、编译选项基类 `CompileOption`（`:401`）、布尔与文件转储两种具体选项（`:446`、`:473`）、优化等级 `OptLevel`（`:496`）。把诊断与选项做成一级对象，是因为 MLIR 层面的失败需要可读的解释，而模板层没有这种余地。

这套 DSL 在仓库里按语言来教：`examples/python/CuTeDSL/` 下有 `dsl_tutorials`、`notebooks`，以及按架构分组的教程与示例，例如 `blackwell/tutorial_gemm`、`blackwell/tutorial_tma`、`blackwell/kernel/distributed`，另有 `experimental/task_scheduling` 一组任务调度练习。教程的自成体系程度说明它不是一层薄封装：使用者要学的是一套表达方式，包括显式写出布局、显式指定流水与线程角色。

两条入口并存带来的是分工，也带来维护面的扩大。同一套代数被实现两遍——一遍是 C++ 模板，一遍是 Python 与 MLIR——好处是可选：需要极致控制的场景留在模板层，需要更快迭代与更清楚报错的场景走 DSL。代价同样具体：语义要在两处保持一致，`python/pycute/layout.py` 这样的参照实现因此既是文档也是回归基准。
