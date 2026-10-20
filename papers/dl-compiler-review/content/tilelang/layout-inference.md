## 布局推导：一次全局求解与三档约束 {#tilelang-layout}

“布局”在这里的含义与 Triton 一章相同：从逻辑计算块坐标到（线程，寄存器）位置的映射。它决定一次内存事务覆盖多少连续元素、矩阵指令能否直接消费寄存器里的值、跨层搬运要不要经过共享内存。两者的差别不在布局是什么，而在谁负责求解、按什么目标求解、求解失败时谁能介入。

TileLang 把求解拆成两个阶段，接口写在算子基类上：

```cpp
// 编者定位：repos/tilelang · 876a59e6eb80 · src/op/operator.h:183-199
class TileOperatorNode : public ffi::Object {
public:
  virtual tirx::Stmt Lower(const LowerArgs &lower_args,
                           arith::Analyzer *analyzer) const = 0;

  virtual LayoutMap InferLayout(const LayoutInferArgs &layout_args,
                                InferLevel level) const = 0;

  virtual TileOperator Clone() const = 0;

  virtual AccessRegions GetAccessRegions() const {
    AccessRegions result;
    for (const auto &access : access_regions_) {
      AppendAccessRegionByMask(access, &result.reads, &result.writes);
    }
    return result;
  }
```

`InferLayout` 只声明约束，`Lower` 才生成线程级代码，两个阶段之间隔着一次全局求解。这样安排是为了让“还没定布局”成为一种合法状态：`copy` 可以声明“我需要满足某种合并宽度的布局”，`gemm` 可以声明“我的 C 必须是某种矩阵指令片布局”，两者不必在源码里立刻达成一致，而由求解器统一裁决。`GetAccessRegions` 同时交出读集与写集，供依赖分析与后续流水规划使用。

求解本身由一个约束系统完成不了，原因是这些约束来自不同算子、可能互不相容，而且同一个缓冲可以接受多种布局。TileLang 因此按约束强度分三档依次放宽：

```cpp
// 编者定位：repos/tilelang · 876a59e6eb80 · src/transform/layout_inference/layout_inference.cc:606-620
    // step 1: infer strict layout
    for (int i = 0; i < num_infer; i++) {
      RunInferStep(i, InferLevel::kStrict, false, layout_map, strict_layout_map,
                   q, in_queue);
    }

    for (const auto &[buffer, layout] : layout_map) {
      strict_layout_map.Set(buffer, layout);
    }

    // step 2: infer common layout with BFS
    FinishInferQueue(InferLevel::kCommon, layout_map, strict_layout_map, q,
                     in_queue);
    // step 3: relax constraints to free and re-run
    InferInFreeMode(layout_map, strict_layout_map);
    // step 4: finalize alias layouts by Var
```

第一档 `kStrict` 收集硬约束，包括 `T.annotate_layout` 指定的布局；第二档 `kCommon` 以广度优先方式把相邻算子提出的布局合并到相容方案；第三档放宽到 `kFree`，对每个连通分量的候选根逐一尝试，再由代价模型挑选完整方案。三档分开的好处是失败可归因：若第一步就出现不可满足的冲突，问题在使用者的注解；若只能靠第三步搜出来，问题在算子之间的耦合。硬约束的地位在代码里是显式的，一个具体例子是归约片：更新循环推出的片布局与 `T.annotate_layout` 指定的不一致时，推导抛出 `LayoutConflictException`，把两侧布局都打印出来，而不是静默选一边。

第三档的选择标准是这套设计最容易被误读的地方。代价模型是可插拔的，默认实现以 fragment 占用的寄存器槽位为主指标；另有 I/O 感知模型把访问全局内存的语句按“带宽字节与发射等价字节取大”计费，需要通过 `tl.layout_cost_model="io-aware"` 显式开启。默认目标因此是“省寄存器且能通过验证”，与“实测最快”并非同一件事。一个用额外共享内存换合并访问的方案，在默认模型下可能不被选中；这正是注解与调参仍然必要的原因，也解释了为什么同一套语言在热点算子上仍要人工介入。

与 Triton 对照，差别在责任分配上。Triton 的 TTGIR 在固定管线里分配布局，随后反复插入与消除布局转换，使用者看到的是转换带来的共享内存流量；TileLang 把布局当成带注解的求解结果，使用者可以看推导过程、也可以用注解把某些决定钉死。前者把优化主动权留在后端，后者把它部分交还给使用者，代价是使用者要能读懂求解器的输出。
