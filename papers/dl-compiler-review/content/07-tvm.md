# TVM：计算与调度分离之后 {#tvm}

TVM 把“算什么”和“怎么算”当作两件可以分开处理的事，并围绕这个分离搭出一整套基础设施（Chen et al. 2018）：一套图级 IR、一套张量层 IR 与调度体系、一个自动调优框架，以及一列把表示逐级推向目标代码的变换。本章按这条链的顺序走，重点放在每个环节各自承担什么、检查在什么时候发生，以及分离带来的代价落在哪里。

{{include:tvm/ir-stack.md}}

{{include:tvm/schedule.md}}

{{include:tvm/autotuning.md}}

{{include:tvm/lowering.md}}
