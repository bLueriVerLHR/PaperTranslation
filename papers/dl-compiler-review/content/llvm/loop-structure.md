## 循环结构优化 {#loop-structure}

### LICM 的外提、下沉与访问条件

```c
for (int i = 0; i < n; ++i)
    a[i] = b[i] * (p + q);
```

若 `p+q` 的 operands 在循环外定义、运算可安全执行，它可以进 preheader。路径：`llvm-project/llvm/lib/Transforms/Scalar/LICM.cpp`。

“地址不变”与“load 结果不变”不同：循环每轮从 `*p` 加载，若循环中任何 store 可能改 `*p`，就不能把 load 外提。MemorySSA、别名分析和副作用信息帮助回答这个问题；相关表示在 `llvm-project/llvm/lib/Analysis/MemorySSA.cpp`。

还要考虑零次迭代：原来不进入循环就不执行 load；外提之后若无条件访问坏指针，会改变语义。需要能安全推测执行，或原位置必定执行等充分条件。LICM 也可 sinking，或在证明允许时做内存 promotion，不能把它缩减成“把纯表达式搬出去”。

外提也会影响后端资源：结果需要贯穿更长路径时，live range 可能延长。减少重复计算与增加寄存器占用需要共同评价。

### LoopRotate 的入口检查与循环形状

简单 while 形状可教学性地变成入口 guard 加 do-while：

```c
if (n > 0) {
    do {
        body();
        ++i;
    } while (i < n);
}
```

入口 guard 保持零次执行语义，主体与 latch 更适合若干分析和优化。路径：`llvm-project/llvm/lib/Transforms/Scalar/LoopRotation.cpp`。它可能复制 header，所以不是免费的结构整理；`-Oz` 等体积政策会影响 header duplication。

### Unswitch 的循环选择与代码体积

```c
for (int i = 0; i < n; ++i) {
    if (mode) a[i] = b[i] + 1;
    else      a[i] = b[i] * 2;
}
```

若 mode 不变且语义允许，可以变成 `if(mode)` 选两个各自无该分支的循环。这样后续 LV 可能看到更简单的 body。路径：`llvm-project/llvm/lib/Transforms/Scalar/SimpleLoopUnswitch.cpp`。

代价是克隆循环。多个不变条件可能造成组合爆炸，因此 non-trivial unswitch 有收益、大小和预算限制。名称里的 Simple 不等于永远只做一个局部替换。

### LoopInterchange：用依赖约束换局部性

C 的二维连续数组通常行优先。以下按列访问：

```c
for (int j = 0; j < cols; ++j)
    for (int i = 0; i < rows; ++i)
        a[i][j] += 1;
```

在依赖与访问语义允许时，交换 i、j 可以使内层按行连续访问，改善缓存行利用并提供连续向量访存的机会。实际收益还取决于数组布局、工作集和目标实现。

理论上，对依赖从迭代点 x 指向 y，变换后的执行时间戳必须仍让 x 在 y 前。方向向量记录各维是 `<`、`=`、`>` 或不确定；交换维后，需要满足合法的字典序方向条件。距离向量 `(1,-1)` 原来第一维先正向，交换成 `(-1,1)` 就可能把消费者排在生产者前。

路径：`llvm-project/llvm/lib/Transforms/Scalar/LoopInterchange.cpp`。开头定义 `CharMatrix` 方向矩阵，并有 cache、指令顺序、向量化机会等收益规则；依赖来自 `llvm-project/llvm/lib/Analysis/DependenceAnalysis.cpp`，cache 估计来自 `llvm-project/llvm/lib/Analysis/LoopCacheAnalysis.cpp`。

循环交换需要分别检查 **重排合法性、IR 形状可变换性与收益**。PHI、归约或不规则 loop nest 可能超出当前实现支持的范围；即使能够构造等价源码，也不意味着该 Pass 能改写相应 IR。

### LoopDistribute 的依赖分区

```c
for (int i = 1; i < n; ++i) {
    a[i] = a[i - 1] + b[i];
    c[i] = d[i] * e[i];
}
```

若相关数组不冲突，两组工作之间也无其他依赖，可分成：

```c
for (int i = 1; i < n; ++i)
    a[i] = a[i - 1] + b[i];
for (int i = 1; i < n; ++i)
    c[i] = d[i] * e[i];
```

第一组串行，第二组可 SIMD。这相当于通过依赖图分区，把有环/递推的部分与独立部分分开。并不是拆掉所有依赖；必须保留分区之间所要求的顺序。

路径：`llvm-project/llvm/lib/Transforms/Scalar/LoopDistribute.cpp`。文件开头明确说主要目标是隔离依赖循环，使用 LoopAccessAnalysis，并特别照顾内存操作的 lexical order；还支持 runtime versioning。

分裂会增加循环控制，可能减少 producer-consumer cache reuse，并重复某些标量计算。对于共享中间数据的循环，SIMD 机会与局部性损失需要共同评价。

### Fusion、Flatten、Idiom 与强度削弱

**Fusion** 合并相邻循环，减少遍历或使生产结果更快被消费。若 `b[i]` 在第一个循环产生、第二个循环使用，融合可能改善局部性；若第二个循环需要尚未产生的 `b[i+1]`，直接交错执行就会破坏依赖顺序。路径：`llvm-project/llvm/lib/Transforms/Scalar/LoopFuse.cpp`。它不是“看到两个同上界循环就合并”。

**Flatten** 尝试把合适嵌套变成单个计数循环。理论上可令 `t=i*n+j`，但边界乘法溢出、索引恢复成本和循环间副作用都是限制。路径：`llvm-project/llvm/lib/Transforms/Scalar/LoopFlatten.cpp`；本版本有独立、默认关闭的管线开关。

**Idiom recognition** 识别 memset/memcpy 或其他特定计算模式，把细粒度循环改成目标可进一步优化的操作。路径：`llvm-project/llvm/lib/Transforms/Scalar/LoopIdiomRecognize.cpp`。库语义、重叠和访问条件仍必须满足，不能把任何字节拷贝循环都换成 memcpy。

**LoopStrengthReduce** 将部分反复乘法式地址计算重写成目标合适的递增地址/偏移表达。路径：`llvm-project/llvm/lib/Transforms/Scalar/LoopStrengthReduce.cpp`。它可能增加诱导变量数量，因此也与寄存器压力有关。

### Tiling 的迭代域分块

矩阵计算同时涉及三类局部性：数据在 cache 中复用、结果在寄存器中累积、线程处理相对独立的数据块。分块把大迭代域切成小块，块大小与 cache 和寄存器资源匹配。

普通 C 优化管线并不保证为任意矩阵乘自动寻找最优 blocking。更显式的高层结构通常在 MLIR affine/linalg 或 Polly 中处理。MLIR 分块路径之一：`llvm-project/mlir/lib/Dialect/Affine/Transforms/LoopTiling.cpp`；多面体路线见[自动并行化与 OpenMP](#parallel-openmp)。

结构变换改变后续 Pass 的输入和可用机会。完全展开可能消除可交换的 loop nest，分裂可能改善向量化条件却损失融合带来的局部性。因此，管线需要在相互影响的候选之间选择，并限制分析和代码体积预算；依次运行所有变换并不能保证最优结果。
