# TileLang：计算块级程序与编译期布局推导 {#tilelang}

Triton 把布局交给后端，代价是表达受限；CuTe 把布局写成类型，代价是作者必须写出确定方案。TileLang 走第三条路：使用者声明计算块与存储层级，保留在块层写“搬运—计算”数据流的自由，而把线程绑定、片布局、张量化与流水阶段交给一套可被注解覆盖的推导。原始设计把这件事概括为把调度空间从数据流中解耦（Wang et al. 2025）。

它选择的技术路线也决定了它与本书其他栈的关系：宿主是 TVM 的 TIR 谱系上的表示（本版本已迁到 TIRX），语言层是 Python，编译期是 C++ 分析与模板代码生成，目标侧通过后端注册表分派到 CUDA、ROCm、Metal、Ascend 等。因此它既是 DSL 前端，也是复用 TVM 基础设施的多后端编译栈。

## 一条内核走过的地方 {#tilelang-structure}

从一段 Python 内核到可执行代码，TileLang 把它分成五段，每段都有独立的入口和可检查的产物：

| 段 | 入口 | 这一段决定什么 | 产物 |
|---|---|---|---|
| 语言层 | `tilelang/language/` | 用哪组图块原语表达数据流与存储层级 | `tl.tileop.*` 调用组成的 `IRModule` |
| 算子接口 | `src/op/operator.h` 与 `src/op/*.cc` | 每个图块算子提出什么约束、怎样降低 | 布局约束与访问区域 |
| 布局与流水 | `src/transform/layout_inference/`、`pipeline_planning.cc` | 线程—寄存器映射、缓冲版本与同步点 | 冻结的布局表与流水结构 |
| 降低 | `src/transform/lower_tile_op.cc` 及其后的通用 pass | 循环、向量化、共享内存与屏障 | 设备级 IR |
| 后端 | `tilelang/backend/` 与 `tilelang/{cuda,rocm,metal,ascend}/` | 目标代码与运行时绑定 | CUDA／HIP／Metal 源、Ascend 代码、机器码 |

这条链的独特之处在第三段。语言层并不比其他 DSL 更简洁，后端也没有比 LLVM 更成熟；真正决定它能否既好用又跑得快的，是“布局作为编译期约束、由推导而不是由使用者写死”这一步。它把原本属于专家的两类工作——给每个寄存器块指定线程布局、给每段搬运选版本与屏障——变成了编译期的求解问题。代价随之出现：求解可能失败、结果可能不合预期、默认目标并不等于实测最优，于是注解、代价模型与调试工具成为这套设计的必要配套，而不是可选附加。

接下来的四节按这条链展开：语言层登记了什么、推导求解的是什么、Pass 顺序为什么这样排、多后端复用到哪一层为止。

{{include:tilelang/language.md}}

{{include:tilelang/layout-inference.md}}

{{include:tilelang/pipeline.md}}

{{include:tilelang/backends.md}}
