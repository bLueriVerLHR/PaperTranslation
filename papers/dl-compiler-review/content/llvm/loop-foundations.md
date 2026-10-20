## 循环优化的理论基础 {#loop-foundations}

### 循环首先是一种控制流结构

LLVM 的普通 LoopInfo 主要识别自然循环：header 支配循环内各块，回边回到 header。支配的意思是从函数入口到该块的所有路径都经过支配者。不是所有任意 CFG 环都能直接当作这种 Loop 处理。

为了让变换有统一入口，编译器常整理出：

- **preheader：** 循环外唯一准备入口，适合放检查和外提代码。
- **header：** PHI 与循环控制的汇合点。
- **latch：** 回边所在块。
- **dedicated exits：** 退出块不同时接受无关的循环外边。
- **LCSSA：** 循环内定义、循环外使用的值经退出 PHI 输出，像给循环加上清晰的数据接口。

阅读路径：`llvm-project/llvm/lib/Transforms/Utils/LoopSimplify.cpp`、`llvm-project/llvm/lib/Transforms/Utils/LCSSA.cpp`、`llvm-project/llvm/include/llvm/Analysis/LoopInfo.h`。

规范化为各类优化提供相对统一的输入，降低处理 CFG 特例的复杂度。孤立运行某个 Pass 与默认管线可能得到不同结果，其中一个原因就是前置形式和分析条件不同。

### ScalarEvolution 的递推抽象

考虑：

```c
for (int i = 0; i < n; ++i)
    a[i] = b[i] + 1;
```

IR 用 PHI、add、icmp 与 GEP 分别表达状态合流、更新、比较和地址计算。SCEV（Scalar Evolution）尝试把 `i` 抽象为相对于某个 Loop 的递推 `{0,+,1}`，把地址抽象为基址、步长与迭代号的组合。`SCEVAddRecExpr` 是这种递推的核心表示之一。

这种抽象支持多类分析：

- 回边执行次数，以及迭代次数的常量、上界与已知倍数。
- 地址间距离、连续访问与等步长关系。
- 表达式相对于循环的不变性。
- 递推规律依赖的额外谓词及其成立条件。

回边次数与迭代次数采用不同的计数定义。对于至少执行一次的简单循环，迭代数通常是回边次数加一；零次迭代、多个退出和不同计数定义要额外处理。溢出同样重要：数学整数上的 `i+1` 与有限位宽、可能 wrap 的 IR 运算不是同一回事，`nuw` / `nsw` 等事实和证明条件会影响推导。

路径：`llvm-project/llvm/lib/Analysis/ScalarEvolution.cpp`，以及 `llvm-project/llvm/include/llvm/Analysis/ScalarEvolutionExpressions.h`。向量化入口使用 `PredicatedScalarEvolution`：某些结论依赖运行时可检查的谓词，不是凭空假定不溢出。

### 内存依赖与执行顺序

对相同内存位置，重要的三类关系是：

| 依赖 | 原执行顺序 | 重排风险 |
|---|---|---|
| RAW / true dependence | 写后读 | 读不到应读的新值 |
| WAR / anti-dependence | 读后写 | 写提前覆盖应读旧值 |
| WAW / output dependence | 写后写 | 最终留下错误的一次写 |

两个读之间通常没有这种内存顺序约束。依赖还分**循环内**与**循环携带**：后者跨不同迭代。

```c
// 跨迭代 RAW，距离 1
for (int i = 1; i < n; ++i)
    a[i] = a[i - 1] + b[i];

// 若 a、b 不重叠，各迭代可独立
for (int i = 0; i < n; ++i)
    a[i] = b[i] + 1;
```

第一段要求迭代 i 在 i−1 更新以后读取，因此不能直接让两个线程无约束同时执行，也不能直接把相邻四次迭代当独立 lane。它可以保序展开；某些特殊递推可以用专门变换处理，但不是普通独立迭代打包。

再看距离 4：

```c
for (int i = 4; i < n; ++i)
    a[i] = a[i - 4] + 1;
```

在满足其他条件时，以 4 为宽度分批、批之间保序，批内可能没有 RAW 链；更大宽度则可能把生产者和消费者放进同一批。这说明**存在循环携带依赖不等于所有 SIMD 都不可能**，还要看方向、距离、访问顺序和 VF。线程级任意调度的证明往往要求更强。

### 别名分析与依赖分析不是一回事

Alias Analysis 回答两次内存访问会不会碰到同一位置；Dependence / LoopAccessAnalysis 进一步问它们在不同迭代如何发生关系。

`a` 和 `b` 都是 `float *` 并不能证明它们不重叠。即使源码看起来写了两个变量，调用者仍可能传入 `a=b+1`。LLVM 会利用别名信息、SCEV 地址表达式、对象信息和访问关系综合分析。

路径：`llvm-project/llvm/lib/Analysis/BasicAliasAnalysis.cpp`、`llvm-project/llvm/lib/Analysis/DependenceAnalysis.cpp`、`llvm-project/llvm/lib/Analysis/LoopAccessAnalysis.cpp`。后者的 `MemoryDepChecker` 与 `RuntimePointerChecking` 直接连接到循环向量化。

`restrict` 是程序员的语义约定，不是免费性能按钮。若程序违反限制，不能指望编译器仍保持原本的偶然执行行为。错误的独立性声明是正确性 bug。

### 证明不够时：versioning 把不确定性变成条件

```text
        进入循环前
             |
    指针区间与 SCEV 条件检查
        /            \
  可证明安全       条件不成立
  快速向量循环      原标量循环
        \            /
            汇合
```

对于简化的连续访问模型，检查可以理解为判断两个半开地址区间是否重叠。实际实现还要处理访问分组、地址步长、溢出、检查数量及生成代码的成本，不能仅比较两个起始指针。

运行时检查不意味着每次迭代都检查；它通常是进入快路径前的开销。循环长时容易摊薄；短循环则可能不值得。路径：`llvm-project/llvm/lib/Transforms/Utils/LoopVersioning.cpp`、`llvm-project/llvm/lib/Transforms/Utils/LoopUtils.cpp`，以及前述 LoopAccessAnalysis。

这种设计组合静态证明、动态守卫与保守回退：静态信息不足时，编译器仍可在检查成立的输入上使用优化方案，在其他输入上保留原有执行路径。

### 归约：依赖可以转换

```c
float sum = 0;
for (int i = 0; i < n; ++i)
    sum += a[i];
```

这是 loop-carried recurrence，不是独立迭代。若运算允许结合重排，可维护多个局部累加器，最后归并。

- 整数模加法有结合性，但带有特定溢出语义或标志的 IR 仍需按其语义判断。
- 浮点加法通常不结合。`(large + small) + (-large)` 与 `large + (small - large)` 可能不同。
- min/max、乘法等也必须检查类型、NaN、符号零和具体运算语义。
- 某些目标和实现支持 ordered reduction，保持要求的顺序；不能说“没有 fast-math 就绝对不能向量化任何浮点归约”。

路径：`llvm-project/llvm/lib/Analysis/IVDescriptors.cpp`，其中 `RecurrenceDescriptor`、`InductionDescriptor` 识别这些模式；`llvm-project/llvm/lib/Transforms/Vectorize/LoopVectorizationLegality.cpp` 的 `canVectorizeFPMath` 检查相关合法性。

**归约识别的本质：** 找出一种可证明等价的状态重编码，而不是忽略依赖。

### 收益模型：理论上更并行，不保证机器上更快

简化成本模型可以把向量快路径分成启动检查、各向量批次和尾部处理，再考虑缓存、分支及资源竞争。LLVM 的 TTI 指令成本是目标相关估计，不是精确的实际耗时，也不能作为跨 CPU 通用的常数。

循环优化可能卡在三类瓶颈：

1. **依赖延迟：** 一个累加器的串行链限制吞吐，多累加器可帮助。
2. **执行吞吐：** 有足够独立指令，但执行端口饱和。
3. **访存带宽：** SIMD 和多线程都不能无限提高内存带宽；线程可能只增加争用。

分析时间同样受预算约束。内存访问的两两比较随访问数量增长，候选方案搜索也可能迅速扩大。保守上限限制整个程序的编译成本，同时可能使某些理论上可行的变换不进入实际搜索范围。
