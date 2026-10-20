## 捕获：把执行记录成图，再用守卫守住假设 {#pytorch-capture}

捕获由 `torch/_dynamo/` 完成。入口函数是 `convert_frame`（`torch/_dynamo/convert_frame.py:2562`），断言版本在 `:624`；真正把 Python 字节码变成图的是 `InstructionTranslator`——基类在 `torch/_dynamo/symbolic_convert.py:1489`，具体实现继承它（`:5758`）。名字里的 translator 说明了做法：逐条解释字节码，遇到张量运算就生成图结点，遇到控制流就在解释器层面处理。生成的图累积在 `OutputGraph` 里（`torch/_dynamo/output_graph.py:711`），由 `compile_subgraph`（`:2042`）交给后端并汇总结果。

记录下来的东西只有在假设成立时才有效，于是每个编译产物都带着一组守卫。守卫系统要解决什么问题，写在该模块的文档字符串里：

```text
编者定位：repos/pytorch · 92f43bbed42c61d2553a49cbd85bc8b5078b1cf0 · torch/_dynamo/guards.py:13-15

The guard system is critical for Dynamo's ability to efficiently reuse compiled code while
maintaining correctness by detecting when recompilation is necessary due to changes in
program state, tensor properties, or control flow.
```

复用与正确性在这里是同一件事的两面：守卫检查通过就复用编译结果，不通过就必须重新编译。守卫在每次调用时执行，因此它的成本进入每条路径的固定开销。

重新编译不能无限发生，框架给它设了上限，数值直接写在配置里：`recompile_limit = 8`（`torch/_dynamo/config.py:121`）、`accumulated_recompile_limit = 256`（`:124`），另有一个开关控制达到上限之后的行为（`:126`）。含义是同一个代码对象因守卫失败最多重编译 8 次；整个进程累计到 256 次之后，Dynamo 停止为相关代码生成新版本，让它按原样执行。这条上限把“编译失败”变成了一种可预期的状态，而不影响程序继续运行。

捕获失败的另一个后果是图被切开。遇到无法记录进图的语义时，当前图就此结束，剩余部分照常按解释执行，之后再重新开始捕获。每个片段各自生成编译产物、各自带守卫、各自可能重编译，这解释了为什么在含大量 Python 逻辑的模型里，编译收益常被切分的开销抵消。

把这一节与上一节对照可以看出取舍的边界：分发层保证任何算子都有实现可用，捕获层保证没有记录进来的东西仍然能跑。两者共同构成了“编译失败不等于程序失败”这条底线，而代价是编译决策被限制在能被安全记录的那部分程序上。
