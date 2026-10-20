## 生成：从图到循环，再到设备代码 {#pytorch-inductor}

`torch.compile` 默认的编译器后端是 Inductor，入口是 `torch/_inductor/compile_fx.py:3133` 的 `compile_fx`。它的文档字符串交代了它在整条链上的位置：

```text
编者定位：repos/pytorch · 92f43bbed42c61d2553a49cbd85bc8b5078b1cf0 · torch/_inductor/compile_fx.py:3143-3148

    Main entry point for compiling given FX graph.  Despite the fact that this
    lives in :mod:`torch._inductor`, this function is responsible for calling
    into AOT Autograd (and we will eventually get a callback to
    ``inner_compile`` to perform actual compilation.  In other words, this
    function orchestrates end-to-end compilation for the inductor backend when
    you use :func:`torch.compile`.
```

同一个文档字符串还有一句提醒：这个函数取得输入 `model_` 的所有权，可能就地修改它（`:3154-3155`）。后端入口直接改动传入的图模块，是这类“在图上下手”的编译器的常见约定。

把 FX 图降到 Inductor IR 的是 `GraphLowering`，它的文档字符串说明了做法与职责（`torch/_inductor/graph.py:390-399`）：逐结点遍历图，物化输入、输出与常量，把每个调用分派给对应的 lowering，累积生成的 IR 结点；它同时持有整个图的状态（符号尺寸、调度器输入、设备与 dtype 跟踪、wrapper 代码），最后驱动 `codegen()` 产出 wrapper 与内核模块。降到这一层之后，算子已经变成带索引表达式的循环与缓冲区读写，与前一章的循环级 IR 处在同一抽象高度。

接下来要决定哪些结点能合进同一个内核，这是性能的关键。判据不只是数据依赖，还包括生成代码的形态。`Scheduler` 里的一段融合判定给出一个具体例子：

```python
# 编者定位：repos/pytorch · 92f43bbed42c61d2553a49cbd85bc8b5078b1cf0 · torch/_inductor/scheduler.py:4584-4599
    def can_fuse_with(self, other: BaseSchedulerNode):
        if self.has_strict_reduction() or other.has_strict_reduction():
            return False
        # Limit tl.load() count in the fused RSPLIT loop to avoid register
        # spills. See https://github.com/pytorch/pytorch/issues/179423
        max_reads = config.triton.mix_order_reduction_max_reads
        if max_reads > 0:
            all_reads: OrderedSet[str] = OrderedSet()
            for sn in itertools.chain(self.get_nodes(), other.get_nodes()):
                for dep in sn.read_writes.reads:
                    if isinstance(dep, MemoryDep):
                        all_reads.add(dep.name)
            if len(all_reads) > max_reads:
                # pyrefly: ignore [bad-assignment]
                metrics.rejected_mix_order_reduction_fusion += 1
                return False
```

这里拒绝融合的理由是寄存器压力：融合后的循环里 `tl.load()` 的数量超过配置上限就可能溢出寄存器，代码注释直接把依据指向一个 issue 编号。会溢出寄存器的融合不会更快，因此这类判据来自工程经验与实测，而不是从计算量推出来的。被拒绝的融合还会记一次指标（`metrics.rejected_mix_order_reduction_fusion`），说明这类判定在维护中是被观测的。

最后一跳是代码生成。`torch/_inductor/codegen/` 下按目标分为 `triton.py` 与 `cpp.py` 两条主线，前者产出 Triton 内核，后者产出 C++ 与向量化循环；与矩阵运算相关的部分走模板，例如 `cpp_gemm_template.py`、`cpp_flex_attention_template.py`、`cpp_micro_gemm.py`。生成的设备内核又要经过一次编译与调优，这层衔接由 `torch/_inductor/runtime/triton_heuristics.py` 一类模块承担——Triton 自己的自动调优在这里被复用。整条链因此出现两次编译：一次把图变成内核源码，一次把内核源码变成可加载的二进制。
