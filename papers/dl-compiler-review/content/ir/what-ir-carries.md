## IR 要承载什么 {#ir-what-it-carries}

把一段计算交给设备执行，中间表示要装下五样东西：**类型与形状**（哪些维是常量、哪些是运行期符号）、**作用域**（这段代码属于线程、线程块还是整个设备）、**内存层次**（读写落在寄存器、共享内存还是全局内存）、**变换能力**（别人能不能写一条 pass 处理它）、以及**可打印性**（出问题时能不能读出来）。

前三样决定编译器的能力边界。第四样决定生态：一个只能由核心团队修改的 IR，与一个允许外部注册操作、类型与变换的 IR，长期演化方式完全不同。第五样决定工程成本——能打印的 IR 让性能问题可以定位到具体一层，不能打印的只能靠经验猜。

同一个注意力计算在本书六条路里落到 IR 上的形态并不相同：

| 栈 | 编译期的主要表示 | 层次 |
|---|---|---|
| TVM | `IRModule` 中的 `relax::Function` 与 `tirx::PrimFunc` | 图级 + 张量级（两套张量层并存，见 TVM 那一章） |
| Triton | TTIR → TTGIR → LLIR，对应 `Triton`／`TritonGPU`／`Gluon` 等方言 | 块级程序 → 目标代码 |
| TileLang | `tl.tileop.*` 调用组成的 TIR 级 `IRModule`，布局与流水以注解和推导结果附着其上 | 计算块级 → 目标源码（CUDA／HIP／Metal／Ascend）或 LLVM 对象 |
| LLVM | 函数级 LLVM IR（SSA、基本块、循环）→ Machine IR（虚拟寄存器、目标指令） | 中端事实 → 机器资源 |
| CuTe（C++） | 类型本身：`Layout`、`Tile`、原子特化 | 编译期求值，无运行期 IR |
| CuTe（DSL） | Python 程序 → MLIR | 块级程序 → 目标代码 |
| PyTorch | FX 图（Python 对象）→ Inductor 的循环级 IR → 生成的 Triton／C++ 源码 | 图级 + 循环级 |
| 昇腾 | MindSpore 的 ANF／`FuncGraph` 与 MindIR；设备侧另有 GE 的图 IR | 图级（开源部分）+ 设备编译器内部 |

这张表最需要留意的是“哪一层被写在纸面上”。TVM 与 MindSpore 的图会序列化成可读的产物（MindIR 有自己的 `core/load_mindir/` 与 `core/proto/`）；Triton 的每级降级都能 `dump` 出来；TileLang 的图块算子、推导出的布局与流水阶段都可打印与导出；LLVM 的每个 Pass 前后都能看 IR。CuTe 的 C++ 那一路在编译失败时给出的是一段模板实例化信息，能读但不友好。

可打印性不是美观问题。本书后面的所有对照都依赖一件事——出问题时能定位到哪一层。这也解释了为什么本书在每一处都给出仓库相对路径与真实行范围：IR 的价值有一半在于它能被指出来。
