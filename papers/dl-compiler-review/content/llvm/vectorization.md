## 自动向量化 {#vectorization}

### Loop Vectorizer 的迭代打包

```c
void saxpy(float *restrict y, const float *restrict x,
           float a, int n) {
    for (int i = 0; i < n; ++i)
        y[i] = a * x[i] + y[i];
}
```

在 VF=4 的简化模型中，向量主体可表示为：

```text
X = load <4 x float> x[i:i+4]
Y = load <4 x float> y[i:i+4]
Y = splat(a) * X + Y
store Y
 i += 4
```

这里 `splat` 是把一个标量广播到各 lane。不是启动四个线程，不是保证生成某条特定 SIMD 指令，也不意味着可擅自融合乘加。是否形成 FMA 另受浮点 contraction 语义和后端选择约束。

- **VF（vectorization factor）：** 一次向量操作覆盖多少标量迭代；可为 fixed 或 scalable ElementCount。
- **IC（interleave count）：** 一轮向量循环有多少组向量工作，粗略相当于向量主体再作一定展开。
- **每轮覆盖量：** 在普通模型下为 VF×IC 次标量迭代；可伸缩向量的实际 lane 数还与运行时 vscale 有关。

以 VF=4、IC=2 为例，一轮处理两组 4 个元素。它可能增加独立访存与计算，隐藏延迟，但也增加同时活跃的向量临时值。

### 源码设计的三层分工

| 层 | 核心源码 | 分析内容 |
|---|---|---|
| 合法性 | `llvm-project/llvm/lib/Transforms/Vectorize/LoopVectorizationLegality.cpp` | 这个循环能否安全转成向量 |
| 规划与成本 | `llvm-project/llvm/lib/Transforms/Vectorize/LoopVectorize.cpp` | 哪个 VF、IC、尾部方案值得选 |
| 计划表示、变换与执行 | `llvm-project/llvm/lib/Transforms/Vectorize/VPlan.h`、`llvm-project/llvm/lib/Transforms/Vectorize/VPlan.cpp`、`llvm-project/llvm/lib/Transforms/Vectorize/VPlanTransforms.cpp` | 如何在不提前破坏 IR 的前提下表示候选 |

主入口 `LoopVectorizePass::processLoop` 在本提交的 `LoopVectorize.cpp:7639`。它先看 hints，再创建 PredicatedScalarEvolution 和 LoopVectorizationLegality；`canVectorize` 失败则报告并退出。之后才进入成本和规划。

当前代码由 `LoopVectorizationPlanner::plan` 构建候选，围绕 VPlan 评估、选择，并由 `executePlan` 实施；与较老版本把主要逻辑归结为 `selectVectorizationFactor` 的导读相比，阅读本地源码应以本版本规划器为准。

### 控制流、指令与 PHI 的合法性

在 `LoopVectorizationLegality::canVectorizeInstrs` 中，header PHI 要能解释为诱导变量、归约或其他支持的递推模式。一个未知的跨迭代状态并不能自动扩成向量。

循环中的函数调用也要有安全和可向量化的解释：目标是否有向量版本、是否可展开或标量化、副作用和访问语义如何。不能把任意 `foo(i)` 同时执行四份。

条件分支可通过 if-conversion 转成掩码/选择：

```c
if (a[i] > 0)
    b[i] = expensive(a[i]);
```

教学图是先生成 `mask = A > 0`，再对活跃 lane 执行。**普通 select 并不能让前面的非法 load 或有副作用调用变得安全**：如果两个候选值已经先执行，未选中的危险操作仍然发生。必须证明推测执行安全，或使用支持的 masked / predicated 运算，必要时标量化。

本提交还出现 uncountable early exit 的专门检查与开关，因此“所有提前退出循环均不支持”过于绝对。具体支持条件由退出形状、副作用和相应开关共同决定。

### 跨 lane 重排的内存条件

`canVectorizeMemory` 使用 LoopAccessAnalysis。关键要判断的是所有可能冲突是否安全，“有没有 store”本身说明不了问题。

典型结果有四种：

1. 静态证明访问独立，直接继续。
2. 有距离约束，可以限制最大安全 VF。
3. 存在可动态判定的别名，规划 runtime checks 与 scalar fallback。
4. 无法证明、无法经济地检查或存在不支持的依赖，拒绝。

连续 load/store 通常具有较直接的目标实现；结构体交错访问可能组成 interleaved access，不规则访问可能需要 gather/scatter，部分指令则按 lane 标量化。不同方式的成本依赖目标能力；gather/scatter 和标量化可能增加开销，因此 IR 中出现向量类型并不直接证明端到端收益。

**interleaved memory access** 与 **IC** 描述不同对象：前者针对 `RGBRGB...` 等交错地址布局的访问分组，后者表示每轮执行多少组向量迭代。

### 第三关：怎样选 VF 和 IC

`LoopVectorizationCostModel::computeMaxVF` 给出候选边界；`LoopVectorizationPlanner::plan` 和相关候选成本逻辑在这个边界内选择计划。TTI 给出运算、内存、shuffle、掩码等估价。

教学上可比较“每批成本 / 本批标量迭代数”，但真实判断还需要：

- 外围检查和最低可获益 trip count。
- scalar remainder 或向量 epilogue。
- scalarization、extract/insert、reduction 收尾成本。
- 固定与 scalable VF 的目标支持。
- profile、优化体积政策、用户 hints。
- 寄存器使用估计。

本提交 `selectInterleaveCount` 使用 `calculateRegisterUsageForPlan`，不是完全忽略寄存器压力的“越宽越好”。但中端的估计仍不是最终分配：目标合法化、指令选择和调度还会改变临时值和生命周期。

扩大 VF/IC 既可能减少同形工作的执行与控制开销，也可能增加 shuffle 和资源需求。成本选择需要比较完整方案的净收益，而不只是选取硬件支持的最大宽度。

### VPlan：先表示方案，再改写真实程序

在分析过程中直接改写真实 IR，会使候选比较与回退更复杂。VPlan 用专门的计划图表示控制结构和数据流，使变换与成本比较先在计划层完成，再执行选定方案。

- `VPValue` / `VPUser` 表示计划的数据关系。
- VP basic block / region 表示计划控制流。
- **recipe** 描述如何生成 widened、replicated、reduction 或其他 IR。
- 计划可以保留标量工作，不要求每个 recipe 都变成一条 SIMD 指令。

recipe 的实现位于 `llvm-project/llvm/lib/Transforms/Vectorize/VPlanRecipes.cpp`，计划级改写位于 `llvm-project/llvm/lib/Transforms/Vectorize/VPlanTransforms.cpp`。分析其生成结果时，需要先区分输入代表 VF 个 lane 的值，还是单一标量值，再对照实际生成的 IR。

本提交的普通入口断言说明：非 VPlan-native 外循环路径时主要处理最内层循环；外层向量化还有条件与限制。不能由“代码包含外循环逻辑”推论“任意嵌套自动一起向量化”。

### 尾部：n 不是 VF 的倍数怎么办

三类常见办法：

1. **标量尾循环：** 主体处理完整向量，剩余元素标量执行。
2. **较小 VF 的向量尾部：** 用另一个方案覆盖余量，再视需要处理最后几个元素。
3. **tail folding：** 最后一批也进入向量循环，用 active-lane mask 只访问合法元素。

掩码运算不能越界产生未定义行为；目标的 masked load/store 支持与成本非常重要。tail folding 能减少额外尾循环，也可能增加每轮掩码和谓词成本。

向量类型只表明部分指令的表示。完整方案还包括 guard、runtime check、vector body、epilogue 和 scalar fallback；将这些部分放在同一 CFG 中，才能分析快路径的适用输入及额外成本。

### SLP：不用循环，也能自动 SIMD

```c
out[0] = a[0] + b[0];
out[1] = a[1] + b[1];
out[2] = a[2] + b[2];
out[3] = a[3] + b[3];
```

SLP（Superword Level Parallelism）从局部同形标量指令组寻找 SIMD。实现核心在 `llvm-project/llvm/lib/Transforms/Vectorize/SLPVectorizer.cpp` 的 `BoUpSLP`：

```text
寻找 root / 相邻 stores / 可组合值
  → buildTree：从结果向上匹配同形 operand bundles
  → 检查依赖和调度可行性，选择 lane 顺序
  → getTreeCost：向量收益减去 pack / shuffle / extract 等成本
  → vectorizeTree：生成向量代码，修复外部标量使用
```

名字叫 tree，但共享值和外部使用让真实结构不必是纯树。不是遇到四个 add 就可以合并：若中间 store 与 load 可能别名、指令不能共同调度，或输出必须频繁提取回标量，可能不划算。

该提交的 SLP 源码包含 may-alias runtime-check 的规划接口。这表明实现具备相关规划能力，但候选能否成功 version 仍需结合具体路径和条件检查，不能从接口存在推断所有情况均受支持。

**Loop Vectorizer 与 SLP 的协作：** 循环展开把跨迭代同形指令显式摆出来，SLP 可能再组合；但 LV 通常直接以迭代为单位规划。两者存在相互作用，不能简单视为互斥开关。

### 未向量化与未加速的阶段诊断

SAXPY 未生成向量代码时，首先需要定位实际接受分析的函数和循环。内联可能使原函数消失，hints 或管线配置也可能使 Pass 不运行。确认执行入口后，合法性诊断可以进一步区分别名、递推、副作用和浮点语义等限制。

合法性通过仍可能因成本不足而保留标量方案。反过来，IR 中存在向量操作也不意味着机器码高效：目标降低可能引入标量化或大量 shuffle，寄存器分配可能产生 spill，运行时又可能受访存带宽限制。将诊断、IR、机器码和性能观测对应到各自阶段，才能确定问题发生在候选生成、方案选择还是最终执行。
