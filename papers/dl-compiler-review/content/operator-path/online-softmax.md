## 先把算法的代价算清楚 {#online-softmax}

标准写法里，注意力先算 `S = QK^T`，再对每一行做 softmax 得到 `P`，最后算 `O = PV`。假定序列长度 `n = 4096`、头维度 `d = 128`、数值用 16 位浮点，那么 `S` 是一个 4096×4096 的矩阵：`4096² = 16,777,216` 个元素，每个 2 字节，合计 32 MiB。这只是单个头、单个批次中的一份中间结果，而它存在的意义只是被立刻做一次归约。

融合写法把 `S` 拆成块，边算边归约，不落盘。对每一行维护三个量：当前最大分值 `m_i`、指数和 `l_i`、以及未归一化的输出 `acc`。处理第 `j` 个键块时依次做三件事：

<math display="block"><msub><mi>m</mi><mi mathvariant="normal">new</mi></msub><mo>=</mo><mi mathvariant="normal">max</mi><mo stretchy="false">(</mo><msub><mi>m</mi><mi>i</mi></msub><mo>,</mo><msub><mrow><mi mathvariant="normal">max</mi></mrow><mi>j</mi></msub><msub><mi>S</mi><mrow><mi>i</mi><mi>j</mi></mrow></msub><mo stretchy="false">)</mo></math>

<math display="block"><mi mathvariant="normal">acc</mi><mo>←</mo><mi mathvariant="normal">acc</mi><mo>·</mo><mi mathvariant="normal">exp</mi><mo stretchy="false">(</mo><msub><mi>m</mi><mi>i</mi></msub><mo>−</mo><msub><mi>m</mi><mi mathvariant="normal">new</mi></msub><mo stretchy="false">)</mo><mo>+</mo><mi mathvariant="normal">exp</mi><mo stretchy="false">(</mo><msub><mi>S</mi><mrow><mi>i</mi><mi>j</mi></mrow></msub><mo>−</mo><msub><mi>m</mi><mi mathvariant="normal">new</mi></msub><mo stretchy="false">)</mo><msub><mi>V</mi><mi>j</mi></msub></math>

<math display="block"><mi>l</mi><mo>←</mo><mi>l</mi><mo>·</mo><mi mathvariant="normal">exp</mi><mo stretchy="false">(</mo><msub><mi>m</mi><mi>i</mi></msub><mo>−</mo><msub><mi>m</mi><mi mathvariant="normal">new</mi></msub><mo stretchy="false">)</mo><mo>+</mo><munder><mo>∑</mo><mi>j</mi></munder><mi mathvariant="normal">exp</mi><mo stretchy="false">(</mo><msub><mi>S</mi><mrow><mi>i</mi><mi>j</mi></mrow></msub><mo>−</mo><msub><mi>m</mi><mi mathvariant="normal">new</mi></msub><mo stretchy="false">)</mo></math>

递推的关键在第一行与随之而来的缩放。先前累计的 `acc` 与 `l` 是按旧的 `m_i` 归一化的，一旦出现更大的分值，它们必须整体重标定，乘上 `exp(m_i − m_new)`。这一步让“先看完全部键再归一化”变成“边看边修正估计”，也正是它使块内计算成为可能。

空间占用随之改变。块大小取 128×128，一个分值块只占 `128 × 128 × 2 B = 32 KiB`，与那个 32 MiB 的完整矩阵相差 1024 倍。占用从“与序列长度平方成正比”变成“与块大小平方成正比加上输出本身”，这是融合带来的主要收益。

收益之外还有新增的计算。每次遇到新的键块，`acc`（尺寸为查询块行数 × `d`）要被重标定一次。按查询块大小为 128 计，总的重标定次数是 `(n/128) × (n/128)` 次块操作，每次作用于 128×128 个元素，于是额外的乘加量约为 `n²d / 128`；而两次矩阵乘本身的乘加量约为 `2n²d`。两者相除得到 `1/(2 × 128) ≈ 0.39%`。用不到半个百分点的额外计算换掉一个按平方增长的中间矩阵，这项交换在长序列上通常成立。

代价不止这些。为了让块内计算能连续执行，键与值的块需要在片上缓冲里排队，这带来多缓冲与同步；`exp` 的计算落到了向量单元上，`m` 与 `l` 的重标定依赖前一块的结果，于是块之间形成一条串行链，流水线要围绕这条链安排。这些约束解释了下一节的现象：同一个算法，不同栈交给使用者的那部分并不相同。
