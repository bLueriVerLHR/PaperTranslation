# 计算图：捕获、改写、分区与两级调度 {#graph}

深度学习编译与通用编译最大的差别在图这一层：通用编译器的输入已经是控制流与数据流，而模型的输入是一张算子图，图的边界、形状与中间结果的存活期都可以整体改写。前面几章各自展示了这套技术的一角，这一章把它拆成四件事——图从哪里来、怎么被改写、怎么被切开，以及图级与循环级两个调度层如何分工。

{{include:graph/capture.md}}

{{include:graph/rewrite.md}}

{{include:graph/partition.md}}

{{include:graph/two-levels.md}}
