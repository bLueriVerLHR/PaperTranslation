# Triton：块级程序与布局驱动的后端 {#triton}

Triton 把表达权收窄到一个块级程序：写代码的人给出每个程序实例覆盖的块形状与块上做什么计算，布局、共享内存分配、循环流水与线程分工留给后端。收窄表达换来的东西是可分析性——后端能对一份受限的程序做较强的推理，并在推理结果上做优化。这套以块为单位编程、把布局选择交给编译器的模型来自 Triton 的原始设计（Tillet et al. 2019）。本章沿着编译的每个阶段看这件交换具体落在哪里，代价又出现在哪里。

{{include:triton/pipeline.md}}

{{include:triton/layout.md}}

{{include:triton/schedule.md}}

{{include:triton/autotune.md}}
