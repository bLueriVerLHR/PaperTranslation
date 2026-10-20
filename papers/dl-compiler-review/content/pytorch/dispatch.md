## 分发：编译要接在哪一层 {#pytorch-dispatch}

`torch.add(x, y)` 这类调用并不直接落到某个算子实现上。它们先进入一个分发器，由它按张量携带的键挑选实现。`aten/src/ATen/core/dispatch/Dispatcher.h:67-71` 把这件事写在类的上方：

```cpp
// 编者定位：repos/pytorch · 92f43bbed42c61d2553a49cbd85bc8b5078b1cf0 · aten/src/ATen/core/dispatch/Dispatcher.h:67-71
/**
 * Top-level dispatch interface for dispatching via the dynamic dispatcher.
 * Most end users shouldn't use this directly; if you're trying to register
 * ops look in op_registration
 */
class TORCH_API Dispatcher final {
```

选择依据是一组键，键的取值空间定义在 `c10/core/DispatchKey.h:136` 的 `enum class DispatchKey : uint16_t`。设备类型、dtype、自动微分状态、以及各种模式（如追踪、函数化）各占若干键，张量上的一组键经过优先级排序后决定用哪个实现。算子的签名与分派规则本身是数据：`aten/src/ATen/native/native_functions.yaml` 用 13,649 行描述算子，构建期由 `torchgen/` 生成注册与转发代码，运行时由 `op_registration` 提供的接口把实现挂到键上。

这套结构给想加编译器的人留下两个接入点。一个是注册新的后端键，把整类算子交给外部实现，分发器照旧工作；昇腾适配层走的正是这条路（下一章会看到 `PrivateUse1` 这个为第三方设备预留的键）。另一个是在分发器之上拦截调用序列，把一段 Python 执行记录成图，再整体替换掉——PyTorch 自己的编译器走的是这条。

两条路的代价不同。走键的人不需要理解 Python 语义，但要为每个算子提供实现，覆盖不全时只能回退；走捕获的人不必逐个实现算子，但要处理语言层面的任意行为，并在捕获失败时保住正确性。后一种选择的全部难点在下一节。
