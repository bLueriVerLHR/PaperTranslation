## 关键实现的控制流分析 {#source-walkthrough}

本章通过短实现片段分析合法性检查、并行候选收集和寄存器分配队列。摘录均来自固定提交，省略周边逻辑，不是可独立编译的完整函数；分析重点是输入事实、返回协议和状态更新如何连接后续执行。

### 向量化：hints 不能跳过合法性

位置：`llvm-project/llvm/lib/Transforms/Vectorize/LoopVectorize.cpp`，`LoopVectorizePass::processLoop`。

```cpp
LoopVectorizationRequirements Requirements;
LoopVectorizationLegality LVL(L, PSE, DT, TTI, TLI, F, *LAIs, LI, ORE,
                              &Requirements, &Hints, DB, AC,
                              /*AllowRuntimeSCEVChecks=*/!OptForSize, AA);
if (!LVL.canVectorize(EnableVPlanNativePath)) {
  LLVM_DEBUG(dbgs() << "LV: Not vectorizing: Cannot prove legality.\n");
  Hints.emitRemarkWithHints();
  return false;
}
```

构造参数与检查结果的含义如下：

- L 是当前循环；PSE 是带谓词的标量演化；DT/LI 给控制流结构；LAIs/AA 给内存访问与别名。
- TTI/TLI 使合法性也能考虑目标和库调用支持，不是纯数学数组模型。
- Requirements 记录所需语义条件；强制向量化提示不会自动满足这些条件。
- size 模式影响是否允许 runtime SCEV checks，因为 guard/版本化有代码体积成本。
- `canVectorize` 返回 false 后不进入后面的成本选择。收益高不能补救没有合法性证明。

这段控制流把合法性检查置于成本选择之前。`pragma vectorize(enable)` 影响策略，不能替代依赖证明或改变语言与 IR 语义；OpenMP simd 提供的语义承诺则属于另一层输入事实。

### 自动并行化：分析与降低是两步

位置：`llvm-project/mlir/lib/Dialect/Affine/Transforms/AffineParallelize.cpp`，`AffineParallelize::runOnOperation`。

```cpp
std::vector<ParallelizationCandidate> parallelizableLoops;
f.walk<WalkOrder::PreOrder>([&](AffineForOp loop) {
  SmallVector<LoopReduction> reductions;
  if (isLoopParallel(loop, parallelReductions ? &reductions : nullptr))
    parallelizableLoops.emplace_back(loop, std::move(reductions));
});
```

`PreOrder` 先访问外层循环，后续处理据此控制已有父并行区域数量。`parallelReductions` 决定是否请求归约识别，并不把任意递推都视为 reduction。候选收集之后，仍需检查 `maxNested`，再调用 `affineParallelize`。

该步骤收集候选并生成 parallel IR，后续 lowering 再选择运行时或目标。检测、IR 变换和运行时执行是不同阶段；这里的分析调用本身并不创建线程。

### Greedy 的局部顺序与全局优先级

位置：`llvm-project/llvm/lib/CodeGen/RegAllocGreedy.cpp`，`DefaultPriorityAdvisor::getPriority`。

```cpp
if (Stage == RS_Assign && !ForceGlobal && !LI.empty() &&
    LIS->intervalIsInOneMBB(LI)) {
  // ...
  if (!ReverseLocalAssignment)
    Prio = LI.beginIndex().getApproxInstrDistance(Indexes->getLastIndex());
  else {
    // ...
    Prio = Indexes->getZeroIndex().getApproxInstrDistance(LI.endIndex());
  }
} else {
  // ...
  Prio = Size;
  GlobalBit = 1;
}
```

省略的注释在完整文件中解释：原始 local range 按线性指令顺序安排；global 和 split range 按长到短。

Greedy 按区间结构采用不同排序策略。优先队列先取高优先级，因此默认 local 路径通过起点到函数末端的距离，使较早起点先被处理；global 路径则使用 Size。stage、hint 和寄存器类等信息还会编码到更高位。

这一优先级策略受分支条件限制：只有部分局部区间进入线性顺序路径，全局区间及切分范围另行处理。队列优先级仍不同于 spill weight。

### 延后切分与第二轮分配

位置：同文件，`RAGreedy::selectOrSplitImpl`。

```cpp
if (Stage < RS_Split) {
  ExtraInfo->setStage(VirtReg, RS_Split);
  LLVM_DEBUG(dbgs() << "wait for second round\n");
  NewVRegs.push_back(VirtReg.reg());
  return MCRegister();
}
```

把原来的 vreg 放进 `NewVRegs` 并不表示它已经被切成新值；在此处是告诉基类再安排一次。空 MCRegister 也不意味着立即报错。

进入此段之前已尝试 assign/evict，后续才进一步 split/spill。将原范围重新入队，使切分决策能利用其他范围占位后形成的压力信息。`selectOrSplit` 因此还具有延后处理的返回路径，函数名不能完整表达其状态协议。

### 新活跃范围的入队与后续处理

位置：`llvm-project/llvm/lib/CodeGen/RegAllocBase.cpp`，`allocatePhysRegs`。

```cpp
VirtRegVec SplitVRegs;
MCRegister AvailablePhysReg = selectOrSplit(*VirtReg, SplitVRegs);
```

后续在处理特殊失败返回后，若有可用物理寄存器会 `Matrix->assign`；然后遍历 SplitVRegs，剔除不再使用者，并将有效区间入队：

```cpp
LLVM_DEBUG(dbgs() << "queuing new interval: " << *SplitVirtReg << "\n");
assert(SplitVirtReg->reg().isVirtual() &&
       "expect split value in virtual register");
enqueue(SplitVirtReg);
++NumNewQueued;
```

切分、驱逐和溢出产生的有效范围由同一工作队列继续处理，因此分配过程并不在原始 N 个 vreg 处理完后结束。Stage、cascade 和预算约束后续尝试，限制反复驱逐、切分和重新入队的过程。

### 片段之间的调用关系

将局部控制流放回完整文件，可以得到以下主要关系：

```text
LoopVectorizePass::processLoop
  → LoopVectorizationLegality::canVectorize
  → LoopVectorizationPlanner::plan
  → 成本与 VF / IC 选择
  → LoopVectorizationPlanner::executePlan

RegAllocBase::allocatePhysRegs
  → RAGreedy::selectOrSplit
  → RAGreedy::selectOrSplitImpl
  → tryAssign / tryEvict / trySplit / spiller
  → Matrix.assign + 新范围入队
```

调用链中的每条边不仅连接函数，也传递分析事实、可修改状态和失败后的回退条件。对照这些接口，才能判断局部选择如何影响下一阶段，以及哪个状态变化触发重新分析或重新入队。
