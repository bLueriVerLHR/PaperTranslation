## 缓存与动态性：把复用条件写进键里 {#pytorch-cache}

编译一次的成本很高，因此编译结果要能跨次复用，甚至跨进程复用。Inductor 的图缓存把这件事写成了带条件的磁盘缓存：

```text
编者定位：repos/pytorch · 92f43bbed42c61d2553a49cbd85bc8b5078b1cf0 · torch/_inductor/codecache.py:2140-2150

    The overall strategy is as follows:
    - This cache stores entries on disk. When saving an entry, we can't
      serialize callables (that could be C++, Triton, etc.), so we serialize
      their own disk cache location. We then recreate the compiled artifact
      after fetching from disk.
    - For indexing the cache, we gather the fields relevant to identifying an
      FxGraph (the graph module, graph inputs, system settings etc.) into an
      FxGraphCacheDetails object, pickle it, and compute a hash for the key.
      See FxGraphCachePickler.
    - Among the metadata we store, we also include a guards expression that's
      appropriate for validating any symbols for Tensor arguments that have
```

第一段说明为什么缓存条目里放的是路径而不是代码：生成的产物本身可能是 C++ 或 Triton 编译结果，它们各自已经有磁盘缓存，图缓存只需要记住位置。第二段给出了键的构成——图模块、图输入、系统设置等参与标识这张图的信息被收集起来序列化后哈希（`FxGraphCache`，`torch/_inductor/codecache.py:2136`）。第三段最值得留意：缓存元数据里还带着一个守卫表达式，用来校验张量参数上的符号。守卫的范围因此从进程内的编译决策延伸到了跨进程的缓存复用。

动态形状由 `ShapeEnv` 处理（`torch/fx/experimental/symbolic_shapes.py:3957`）。符号形状让同一份编译产物可以覆盖一族形状：只要守卫能证明新形状落在已编译的取值范围内，就不必重编译。超出范围或触发新的特化时才生成新版本，此时前面那套键与守卫的组合开始起作用——键区分不同的特化，缓存承载跨进程的复用。

第三类问题是执行侧的开销。把多次内核启动压成一张 CUDA 图能减少启动开销，但复用同一块显存池会与中间结果的存活期冲突。仓库对这件事的解释是：

```text
编者定位：repos/pytorch · 92f43bbed42c61d2553a49cbd85bc8b5078b1cf0 · torch/_inductor/cudagraph_trees.py:19-25

* Previously, if you executed graph A, some non-CUDA graph code, and then
  graph B, after executing graph B, it was not safe to retain any references
  to intermediates produced by A.  With CUDA graph trees, we track if any
outputs of graph A are still live by the time graph B is run, and make
  sure graph B doesn't clobber there memory when reusing the CUDA graphs
  pool.  You'll get a separate recording of B depending on what tensors
  stay live or dead.
```

做法是跟踪跨图的活跃性：按运行时哪些张量还活着，决定图 B 是否可以复用图 A 留下的显存，代价是同一段代码可能对应多份录制。这类开销无法靠静态分析消除，因为它取决于调用方的使用方式。

把这一节的三件事放在一起看，PyTorch 这条路的成本结构就完整了：编译产物用守卫与键来界定适用范围，动态性用符号与特化来摊销，执行开销用图化来压缩；三者的共同前提都是“运行时能观察到的信息足够判断假设是否成立”。
