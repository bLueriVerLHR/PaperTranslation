## 停在循环级，交出源码 {#ir-source-as-output}

Inductor 有 IR，但它停在循环这一层。`torch/_inductor/ir.py` 有一万多行，定义的是循环级结点：`IRNode`（`:622`）、`Operation`（`:989`）、`Loops`（`:1090`）、`Pointwise`（`:1252`）、`Scatter`（`:1293`）、`Reduction`（`:1431`），归约之下还有 `MultiOutputReduction`（`:2437`）、`OnlineSoftmaxReduction`（`:2609`）与 `WelfordReduction`（`:2791`）。

`OnlineSoftmaxReduction` 这个结点名值得停一下：贯穿对照那一章那个“边看边修正估计”的递推，在这条栈里被做成了一类一等结点。算法层面的一个数值技巧，最终以 IR 结点类型的形式固定下来，这是“IR 决定能看见什么”的直接例子——编译器认得出在线 softmax，才谈得上为它专门安排计算与内存。

链条的下一跳落在源码上：`torch/_inductor/codegen/triton.py` 与 `codegen/cpp.py` 把循环级 IR 变成 Triton 内核或 C++ 循环，再交给下游编译器。寄存器分配、指令选择、调度这些工作因此都不用自己做。

这条路换来两类成本。一类是表达受限：生成的 Triton 源码能表达的东西受 Triton 语言与它的旋钮限制，想用某个指令而 Triton 没暴露，就只能等上游或换后端。另一类是缓存要管两级——图级缓存按图结构与守卫哈希（PyTorch 那一章的 `FxGraphCache`），内核级缓存由下游的编译缓存承担，两级的键与失效条件各自独立。PyTorch 那一章里“一次编译、两次编译”的说法指的是同一件事：图变成源码，源码再变成二进制。

把 Inductor 与 CuTe 并排放，可以看到两种“把机器码交出去”的姿态。CuTe 的中间表示是 C++ 类型，求值发生在编译期，检查也发生在编译期；Inductor 的中间表示是运行期构造的 Python 对象，检查发生在构造过程与后续的守卫里。前者把错误推向编译期，后者把灵活性留在运行期——两种取向对应两类用户：库作者与框架用户。
