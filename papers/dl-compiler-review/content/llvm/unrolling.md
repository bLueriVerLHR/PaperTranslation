## 自动循环展开 {#unrolling}

### 保序展开的基本结构

```c
for (int i = 0; i < n; ++i)
    a[i] = a[i] * c + 1;
```

因子 U=4 的教学结构：

```c
// 示意：实际编译器还必须正确处理边界运算和溢出
for (; remaining >= 4; i += 4, remaining -= 4) {
    a[i]     = a[i]     * c + 1;
    a[i + 1] = a[i + 1] * c + 1;
    a[i + 2] = a[i + 2] * c + 1;
    a[i + 3] = a[i + 3] * c + 1;
}
for (; remaining > 0; ++i, --remaining)
    a[i] = a[i] * c + 1;
```

展开本身仍可保持所有原迭代的顺序，所以有 loop-carried dependence 也不必禁止。例如 `a[i]=a[i-1]+b[i]` 可以复制四次并保留串行链。只有进一步调度、打包或重关联才需要对应的独立性证明。

展开不等于并行化，也不保证增加有效 ILP。若各份循环体仍沿同一递推状态串行连接，复制后的计算仍受这条依赖链限制。

### 控制开销、调度窗口与常量暴露

1. **摊薄控制开销。** U 次工作只执行一次外层控制更新与跳转。
2. **扩大调度窗口。** 让多个独立 load 和运算同时可见，处理器与编译器能重叠延迟。
3. **暴露常量。** 完全展开小常数循环，使 `i` 每次变成常数，分支、地址和 lookup 可折叠。
4. **促进其他优化。** SLP、CSE、SROA、死代码消除能利用重复体的显式关系。
5. **在合法时增加累加器。** 拆短归约依赖链，但这不只是复制；必须满足归约重排的语义。

代价包括代码体积增长、指令缓存与解码压力、活跃值增多、spill、余数处理及编译时间。因此，收益可能随展开因子先增加后下降，不能假定 U 越大越好。

### 三种展开和一次 peeling

| 策略 | 条件 / 行为 | 典型适用点 |
|---|---|---|
| full unroll | 将有限次迭代显式列出，消除循环 | 小常量 trip count，常量传播收益明显 |
| partial unroll | 每轮复制 U 份，仍有循环 | 控制成本、吞吐改善 |
| runtime unroll | trip count 运行时才知道，构造分组和余数路径 | 能摊薄 setup 的长循环 |
| peeling | 剥离前几次或特定迭代，剩下循环保留 | 第一轮特殊行为、稳定后简化 |

peeling 与 unroll 都涉及克隆，但目的不同。剥离一轮后可能证明剩余 PHI 固定或分支条件稳定；展开则让一个新主体覆盖多次原迭代。

### 策略选择与 CFG 重建

入口和策略在 `llvm-project/llvm/lib/Transforms/Scalar/LoopUnrollPass.cpp`：

- `gatherUnrollingPreferences`：收集默认、优化级别、TTI、大小政策与用户覆盖。
- `tryToUnrollLoop`：整理分析、trip count、上界、倍数和 metadata，判断可选动作。
- `computeUnrollCount`：选择因子和 full / partial / runtime 的相关策略。
- 最后调用 `UnrollLoop` 实施。

真正的 CFG/SSA 重建在：

- `llvm-project/llvm/lib/Transforms/Utils/LoopUnroll.cpp`：`UnrollLoop`。
- `llvm-project/llvm/lib/Transforms/Utils/LoopUnrollRuntime.cpp`：运行时展开和余数处理。
- `llvm-project/llvm/lib/Transforms/Utils/LoopPeel.cpp`：peeling。

展开策略与 CFG/SSA 重建承担不同职责。前者通过启发式选择复制份数，后者必须使每个克隆的值、退出边和回边保持精确语义。

### 展开因子的成本估计

LLVM 使用 IR/目标成本估计，不是源码行数。常量迭代数、最大迭代数、已知倍数有不同用途：

- 精确 TripCount 小，可能全展开。
- 只知道上界，仍可能需要保留每轮退出条件，不能无条件执行到上界。
- 只知道迭代数是 k 的倍数，可以减少某些余数处理。
- 完全未知时，runtime unroll 需要额外计算和 CFG，成本更高。

`LoopUnrollPass.cpp` 中还有完整展开收益分析：估计复制后的常量化、可删除指令等，允许某些收益特别明显的情况提高可接受阈值。并非所有候选都做无限精细模拟；分析预算也是限制。

本提交可见默认阈值和 O3 aggressive 阈值等选项，但这些值不是“机器码最多多少字节”，也不是统一性能定律。TTI 和优化体积模式会调整。这些参数的层次和覆盖关系决定候选的实际阈值，分析时需要结合 TTI 与管线配置。

### 克隆后的值映射与控制流修复

以原 header PHI 为例：

```text
s_phi = phi(initial_s, s_next)
s_next = f(s_phi, a[i])
```

展开 U=2 后，第二份的输入必须是第一份的结果，不是再从 original PHI 读一遍；回边要连到最后一份。类似地：

- 每个克隆指令的 operand 要映射到正确的一份。
- 第 k 份的 induction value 对应原第 k 次迭代。
- 中途退出要保持原来该退出点可观察的状态。
- 外部使用要通过正确退出 PHI/LCSSA 获得结果。
- LoopInfo、支配关系和 SCEV 必须更新或失效。
- metadata 要避免错误地对新循环重复施加原 transformation request。

`UnrollLoop` 不仅克隆基本块，还需要完成值映射、回边连接、退出状态传递及分析维护。`CloneBasicBlock` 提供复制操作，后续接线和修复才使新 CFG 保持原语义。

### unroll-and-jam 的跨层重组

原来：

```c
for (int i = 0; i < m; ++i)
    for (int j = 0; j < n; ++j)
        y[i][j] = x[j] * scale[i];
```

外循环按 2 展开，再把两份内循环 jam：

```c
for (int i = 0; i + 1 < m; i += 2)
    for (int j = 0; j < n; ++j) {
        y[i][j]     = x[j] * scale[i];
        y[i + 1][j] = x[j] * scale[i + 1];
    }
// 外层余数另行处理
```

这里两个外迭代共享 `x[j]` 的读取，可能减少访存并制造 SLP 机会。但执行顺序从“整个第 i 行，再整个第 i+1 行”变成按列交错，故依赖证明比保序展开更强。数组间别名也会影响合法性。

路径：`llvm-project/llvm/lib/Transforms/Scalar/LoopUnrollAndJamPass.cpp`、`llvm-project/llvm/lib/Transforms/Utils/LoopUnrollAndJam.cpp`。本版本管线注释专门要求把 unroll-and-jam 放在普通 unroll 前，避免普通展开先破坏想处理的嵌套形状。

### 循环展开与寄存器分配的连接

假设未展开时只需维持一个地址、一个加载值和一个中间乘积；展开四份后，为了重叠 load，调度可能同时维持四组临时值。

```text
更多 ILP
   ↘
    更多同时活跃值 → 超过可用寄存器 → store/reload → 收益可能反转
   ↗
更大 VF / IC
```

展开并不必然增加寄存器压力：常量折叠与死值消除也可能减少工作，实际压力取决于最终调度下的活跃峰值。LLVM 中端与后端不是一次联合的全局最优化求解，评价展开收益需要继续检查最终机器码，而不只统计减少了多少循环控制指令。
