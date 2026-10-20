# LLVM 中端：循环变换、向量化与并行 {#llvm-loops}

三个决定在上一部分已经就位：计算被切成多大（这里以循环嵌套与迭代域的形式出现）、块之间按什么次序执行（依赖与循环结构）、每个元素由谁负责（先由向量化与并行化决定，之后才落到线程与寄存器）。这一部分按这三次改写展开，每一处都保持同一个判据：合法性先于收益，收益先于成本模型的选择。

深度学习算子在这里与通用程序汇合。一次归约或一次逐元素前向在 LLVM 眼里就是一个循环；能不能向量化取决于依赖距离与浮点语义，能不能交换取决于别名与步长。上一章讨论的块级 DSL 之所以要把这些说清楚，正是因为下游这些分析只能使用 IR 里已有的事实。

{{include:llvm/loop-foundations.md}}

{{include:llvm/vectorization.md}}

{{include:llvm/unrolling.md}}

{{include:llvm/loop-structure.md}}

{{include:llvm/parallel-openmp.md}}

{{include:llvm/practice.md}}
