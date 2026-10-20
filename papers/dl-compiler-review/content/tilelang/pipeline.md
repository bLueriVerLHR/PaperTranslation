## Pass 顺序：流水规划必须先于布局推导 {#tilelang-pipeline}

编译顺序不是实现细节，它决定某个 pass 能看到什么形状的程序。同样一个 `T.copy`，在单缓冲的串行循环里和在三级流水里要满足的布局条件并不相同：流水把它拆成多个版本，每个版本有自己的缓冲、屏障与访问时机，这些都会改变“一次内存事务覆盖多少元素”的判断。TileLang 因此把流水规划放在布局推导之前，并把这条顺序写进显式的管线函数：

```python
# 编者定位：repos/tilelang · 876a59e6eb80 · tilelang/cuda/pipeline.py:127-144
    # Run pipeline planning and software-pipeline rewriting before layout
    # inference so inferred layouts see the final pipelined structure directly.
    mod = tilelang.transform.PipelinePlanning()(mod)
    mod = tilelang.transform.InjectSoftwarePipeline()(mod)
    mod = tilelang.transform.Simplify()(mod)

    # Infer memory layouts for fragments and shared memory
    mod = tilelang.transform.LayoutInference()(mod)
    # Plan physical storage/communication for reducer v2 epochs and
    # materialize the first-class reducer ops. Loop layouts are frozen at
    # this point; the planner only reads them.
    mod = tilelang.transform.ReducerPlanAndMaterialize()(mod)
    # Visualize the layout
    LayoutVisual(mod)
    # Lower high-level tile operations to low-level operations
    mod = tilelang.transform.LowerTileOp()(mod)
    # Assert no reducer v2 construct survived materialization
    mod = tilelang.transform.VerifyReducerConsumed()(mod)
```

若顺序反过来，布局要按未被改写的原形求解，随后又被流水改写成多版本结构，只能重新推导或容忍不一致；把流水提到前面，推导看到的就是最终的循环与缓冲结构。

同一段管线里还有两处顺序上的取舍。其一，warp 特化在更早处执行：生产者（搬运）与消费者（计算）按 warp 分工后，两侧的访问模式不同，布局要分别满足。在计算块层完成这次切分，比在 lowering 之后拆分线程级代码容易得多——后者要在已经展开的循环与寄存器分配之间做手术。其二，布局推导之后紧跟 `LowerTileOp`，此后所有图块算子按冻结的布局表生成线程级语句，再往下才是向量化、共享内存合并、线程同步与机器码生成。这个“先冻结、再展开”的次序解释了为什么布局冲突总在编译期出现，而不可能拖到运行时。

流水本身要付两项代价。`num_stages` 每增加一级，同一块共享内存就多一份副本，占用率随之下降，屏障也更多；深度过大时，重叠收益会被占用率与同步开销抵消。warp 特化则把线程分成角色固定的组，调度更确定，但角色间负载不均时会有 warp 空转，且需要额外的寄存器与屏障预算。`T.Pipelined` 提供两个入口：`num_stages` 让编译器推断阶段划分，`order`／`stage` 由作者直接指定每条语句属于哪一级。后者把推断权收回作者，也把“哪一步必须早于哪一步”的正确性责任一并收回。

与 Triton 的流水一节并列看，两者在同一个问题上分工相反。Triton 把流水与 warp 特化写在后端固定管线里，作者只能通过 `tl.range` 的参数提请求；TileLang 把同一批 pass 暴露成可检查的步骤，并提供 `order`／`stage` 作为手工排布入口。前者减少了使用者能犯的错，后者扩大了能调的空间，代价是调试要落到 pass 序列上，而不能只看源码。
