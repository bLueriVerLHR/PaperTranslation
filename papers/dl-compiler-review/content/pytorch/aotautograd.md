## 反向图与重算分区 {#pytorch-aotautograd}

训练场景下只有前向图没有用，反向也要一起编译，而且反向所需的中间值正是内存压力的来源。AOT Autograd 在编译期把前向与反向一起追踪成一张联合图，入口之一是 `torch/_functorch/aot_autograd.py:717` 的 `aot_function`。为了能对图做变换，带就地修改与别名的算子先被函数化：该文件引入了 `run_functionalized_fw_and_collect_metadata`（`:46`）与 `create_functionalized_fn`（`:77`），并在一处注释里点出别名关系必须被函数化机制正确理解（`:353`）。

联合图随后要被切成前向与反向两张。切法不是唯一的，因为反向既可以从零重算前向中间结果，也可以把前向算出来的值原样保留。这件事被写成一个分区问题：

```text
编者定位：repos/pytorch · 92f43bbed42c61d2553a49cbd85bc8b5078b1cf0 · torch/_functorch/partitioners.py:4186-4193

    Partitions the joint graph such that the backward recomputes the forward.
    Recomputing helps in trading off memory bandwidth with computation.

    To create the fwd and bwd graph, we copy the joint graph, manually set the
    outputs to just original forward or backward outputs. And then we run the
    resulting graphs through dead code elimination.
```

文档把权衡说清楚了：重算用计算换内存。实现路径是先复制联合图，把输出分别设为前向输出与反向输出，再各自跑一遍死代码消除（`partitioners.py:4178` 起的 `min_cut_rematerialization_partition`）。选择保留哪些中间值被表述成最小割问题，这决定了哪一批中间结果需要常驻内存。同文件另有不做重算的 `default_partition`（`:1618`），适用于不需要这类权衡的前向场景。

这一步的代价落在两处。分区决定了峰值显存与额外计算量的组合，而重算的代价只在反向执行时才体现出来；函数化虽然让图更规整，也改变了算子的写法，某些带副作用的算子因此难以进入这张图。
