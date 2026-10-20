## 调度：把“怎么算”写成可检查的决策 {#tvm-schedule}

张量表达式这一层描述值怎么算出来，调度描述这份计算落到设备上以后怎么组织。同一份表达式配上不同调度，生成的代码可以差出数倍，因为调度决定了三个互相牵制的量：计算切成多大的块、块与块按什么次序执行、每个元素由哪个线程负责。

调度在实现上是一串按序施加的原语，每个原语改写块结构与循环结构。`src/s_tir/schedule/primitive/` 下的目录名就是这份清单：`compute_at`、`compute_inline`、`cache_read_write`、`loop_transformation`、`layout_transformation`、`reduction`、`blockize_tensorize`、`for_kind`、`rolling_buffer` 等。原语施加的顺序会影响后续哪些原语仍然可用，这一点在后面讲自动调优时还会出现。

每个原语在改写之前检查前提是否成立，不成立就抛出带上下文的调度错误。`compute_at` 要求被搬动的块的全部生产者或消费者都位于目标循环之下，否则构造 `NotAllRequiredBlocksAreVisitedError`：

```cpp
// 编者定位：repos/tvm · 2bb1a553be19 · src/s_tir/schedule/primitive/compute_at.cc:51-61
// 类 NotAllRequiredBlocksAreVisitedError 的 FastErrorString 与 DetailRenderTemplate
  ffi::String FastErrorString() const final {
    return "ScheduleError: Not all required blocks are under the loop scope";
  }

  ffi::String DetailRenderTemplate() const final {
    ffi::String relation = is_consumer ? "consumer(s)" : "producer(s)";
    std::ostringstream os;
    os << "The primitive requires all the " << relation
       << " of the given block to be present under the target loop. However, there are "
       << num_not_visited_ << " " << relation << " not satisfying the constraint. List of the "
       << relation << ":";
```

这段错误文本把约束讲得很具体：把生产者搬进使用者的循环体，等于要求这次移动在依赖结构上自洽。检查点是调度阶段而不是代码生成阶段，所以报错时能指出是哪一类块、缺了几个。同一目录下 `compute_inline.cc:129` 的 `BodyAnalysisError` 也是同样形态，它的 `FastErrorString`（同文件 `:133`）说明内联要求循环体形态满足条件。

调度的必要性随目标变化。架构文档写得很直白：CPU 目标不做调度也能生成合法代码并执行，只是性能很低；GPU 目标若没有调度，就无法生成合法的线程绑定（`docs/arch/index.rst:90`）。原因在线程绑定的性质——它规定哪个线程负责哪些元素，而没有调度之前，生成的循环里没有任何可依附的结构来表达这件事。

代价也随之固定下来。原语各有前置条件，意味着一个调度方案是一串必须逐条自洽的决策，顺序不同，可行集合就不同。手工写出好调度需要同时懂算法、懂硬件、懂这些原语的副作用，这正是下一节那套基础设施要接管的工作。
