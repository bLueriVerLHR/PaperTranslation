## 流水、线程分工与新一代存储层次 {#triton-schedule}

循环里的加载与计算如果严格顺序执行，硬件会在等内存的时段空转。解决办法是把循环展开成多个阶段，让第 i 次迭代的计算与第 i+1 次迭代的加载同时进行，这就是软件流水。Triton 把它拆成三步接续的 pass，出现在 8.x 与 9.x 的分支里：

```python
# 编者定位：repos/triton · ebdd5b6b4856 · third_party/nvidia/backend/compiler.py:333-336
        nvidia.passes.hopper.add_hopper_warpspec(pm, opt.num_stages, dump_enabled)
        passes.ttgpuir.add_assign_latencies(pm, opt.num_stages)
        passes.ttgpuir.add_schedule_loops(pm)
        passes.ttgpuir.add_pipeline(pm, opt.num_stages, dump_enabled)
```

三步各有职责：`assign_latencies` 给需要跨迭代提前发起的操作标注延迟预算（这里直接取 `num_stages`），`schedule_loops` 决定循环内操作的次序与分组，`pipeline` 按计划真正改写循环结构。实现集中在一个子目录里，文件名即分工：`Pipeliner/AssignLatencies.cpp`、`Pipeliner/Schedule.cpp`、`Pipeliner/ScheduleLoops.cpp`、`Pipeliner/SoftwarePipeliner.cpp`、`Pipeliner/PipelineExpander.cpp`，另有面向前沿硬件的 `MMAv5PipelineUtility.cpp`、`TMAStoresPipeline.cpp`、`WGMMAPipeline.cpp`。

`num_stages` 这个参数在此处显形：它是多缓冲的级数，级数越大，重叠越充分，同时占用的共享内存与寄存器越多。使用者能调整它，却写不出缓冲分配本身——分配由后端按调度结果计算，这也解释了为什么占用率问题往往要通过调这个数来解决。

硬件换代时管线变化最大的地方在线程分工。8.x 与 9.x 用 `add_hopper_warpspec`，10.x 的分支换成另一组：`add_optimize_accumulator_init`、`add_hoist_tmem_alloc`、`add_promote_lhs_to_tmem`、`add_warp_specialize`、`add_optimize_partition_warps`，收尾再来一次 `add_hoist_tmem_alloc`，参数为真表示允许把分配移出条件分支，然后 `add_remove_tmem_tokens`（`:341-352`）。这里的核心变化是张量内存（TMEM）成为一种需要显式管理的资源：分配要被提升到循环外以便复用，用完之后还要把记账用的 token 清掉。warp 专门化则把这批资源分给不同角色的 warp 组——加载、矩阵运算、收尾各占一组，用栅栏彼此同步，从而在不牺牲单一角色效率的前提下重叠起来。

代价集中在三处。级数提升要占共享内存，TMEM 分配要占新硬件上的专用容量，warp 专分化引入额外的同步与屏障。三者都与“把流水做得更深”这一目标竞争同一种稀缺资源，于是调参变成一个在多维约束下找可行点的问题，这也把话题带到下一节：谁来试这些组合。
