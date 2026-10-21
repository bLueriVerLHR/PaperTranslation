### SSM 与 RWKV：同一套状态演化的另外两条入口

递推这条路不止从注意力改写而来。状态空间模型（State Space Model，SSM）从连续时间系统出发，RWKV 从线性注意力的通道衰减出发，两者最后落在与 GDN 同形的更新式上：一个对角衰减加一个秩一项。把它们并排看，能看清“门控的形状”与“状态大小”各自决定什么。

#### 从连续时间系统到选择性扫描

S4 用四个参数 (Δ, A, B, C) 定义一个序列到序列的变换，先把连续参数离散化：

<math display="block"><mover><mi>A</mi><mo>¯</mo></mover><mo>=</mo><mi mathvariant="normal">exp</mi><mo>(</mo><mi>Δ</mi><mi>A</mi><mo>)</mo><mo>,</mo><mspace width="1em"/><mover><mi>B</mi><mo>¯</mo></mover><mo>=</mo><mo>(</mo><mi>Δ</mi><mi>A</mi><msup><mo>)</mo><mrow><mo>−</mo><mn>1</mn></mrow></msup><mo>(</mo><mi mathvariant="normal">exp</mi><mo>(</mo><mi>Δ</mi><mi>A</mi><mo>)</mo><mo>−</mo><mi>I</mi><mo>)</mo><mo>·</mo><mi>Δ</mi><mi>B</mi></math>

再按递推算出隐藏状态 hₜ 与输出 yₜ：<math><msub><mi>h</mi><mi>t</mi></msub><mo>=</mo><mover><mi>A</mi><mo>¯</mo></mover><msub><mi>h</mi><mrow><mi>t</mi><mo>−</mo><mn>1</mn></mrow></msub><mo>+</mo><mover><mi>B</mi><mo>¯</mo></mover><msub><mi>x</mi><mi>t</mi></msub></math>，<math><msub><mi>y</mi><mi>t</mi></msub><mo>=</mo><mi>C</mi><msub><mi>h</mi><mi>t</mi></msub></math>。这里的参数不随输入变化，因此整段序列等价于一次固定的卷积，可以并行算出。[45]（§2）

Mamba 的改动只有一句：让 Δ、B、C 随输入变化，使得模型能按当前 token 决定放行还是遗忘。[45]（§3.1）代价是固定卷积的形式消失了，只能用带扫描的并行算法重写前缀计算，这也解释了为什么选择性 SSM 的实现必须与内核一起设计。原文报告 3B 规模在语言建模上超过同规模 Transformer、追平两倍规模的 Transformer，以及相对 Transformer 约 5 倍的生成长度吞吐。

#### Mamba2 把递推与二次计算做成对偶

Mamba2 把 A 从对角结构进一步简化成标量乘单位矩阵，并对每个头取更大的头维 P（常取 64 或 128），于是同一层有两种等价算法：递推形式沿序列线性，二次形式写成

<math display="block"><mo>(</mo><mi>L</mi><mo>∘</mo><mi>Q</mi><msup><mi>K</mi><mi>T</mi></msup><mo>)</mo><mo>·</mo><mi>V</mi><mo>,</mo><mspace width="1em"/><msub><mi>L</mi><mrow><mi>i</mi><mi>j</mi></mrow></msub><mo>=</mo><munderover><mo>∏</mo><mrow><mi>k</mi><mo>=</mo><mi>j</mi><mo>+</mo><mn>1</mn></mrow><mi>i</mi></munderover><msub><mi>a</mi><mi>k</mi></msub><mspace width="0.3em"/><mo>(</mo><mi>i</mi><mo>≥</mo><mi>j</mi><mo>)</mo></math>

其中 aₖ 是取值在 [0,1] 的输入相关标量。与标准注意力相比，它去掉了 softmax，把归一化换成逐位置的衰减累积。[46]（§2.4）两种形式的选择只看形状：短序列用二次形式，矩阵乘的并行度高；长序列用递推，算术量少。线性注意力与 SSM 在代数上同源：1-SS 矩阵的乘法就是累积乘积和，Mamba2 的分块算法在这层等价上做调度。[46]（§3.2、§5）

#### RWKV：把衰减放到通道上

RWKV-4 的出发点是带位置偏置的注意力，把偏置限制成只依赖相对距离的通道向量：<math><msub><mi>w</mi><mrow><mi>t</mi><mo>,</mo><mi>i</mi></mrow></msub><mo>=</mo><mo>−</mo><mo>(</mo><mi>t</mi><mo>−</mo><mi>i</mi><mo>)</mo><mi>w</mi></math>，w 非负，因此 <math><msup><mi>e</mi><msub><mi>w</mi><mrow><mi>t</mi><mo>,</mo><mi>i</mi></mrow></msub></msup><mo>≤</mo><mn>1</mn></math>、时间上单调衰减。[47]（§2.2、Eq.10）这样改写之后，原来对全体的加权求和变成对单个状态的递推，训练可以按并行形式做，推理每步只读写一个状态。

衰减向量 w 逐通道取值，初始化按层与通道给出单调的安排：第 l 层、第 i 个通道取 <math><mo>−</mo><mn>5</mn><mo>+</mo><mn>8</mn><msup><mrow><mo>(</mo><mi>i</mi><mo>/</mo><mo>(</mo><mi>d</mi><mo>−</mo><mn>1</mn><mo>)</mo><mo>)</mo></mrow><mrow><mn>0.7</mn><mo>+</mo><mn>1.3</mn><mi>l</mi><mo>/</mo><mo>(</mo><mi>L</mi><mo>−</mo><mn>1</mn><mo>)</mo></mrow></msup></math>，[47]（附录）靠前的层衰减更快、靠后的层保留更久，通道之间也拉开差距。这与 RetNet 的逐头衰减是同一个设计思路，区别是衰减维度从“每头一个标量”变成“每通道一个值”。

RWKV-7 把更新式推广成广义 delta 规则：<math><msub><mi>S</mi><mi>t</mi></msub><mo>=</mo><msub><mi>S</mi><mrow><mi>t</mi><mo>−</mo><mn>1</mn></mrow></msub><mrow><mo>(</mo><mi mathvariant="normal">diag</mi><mo>(</mo><msub><mi>w</mi><mi>t</mi></msub><mo>)</mo><mo>+</mo><msubsup><mi>z</mi><mi>t</mi><mi>T</mi></msubsup><msub><mi>b</mi><mi>t</mi></msub><mo>)</mo></mrow><mo>+</mo><msubsup><mi>v</mi><mi>t</mi><mi>T</mi></msubsup><msub><mi>k</mi><mi>t</mi></msub></math>，其中 zₜ、bₜ 由同一把键派生（取 <math><msub><mi>z</mi><mi>t</mi></msub><mo>=</mo><mo>−</mo><msub><mover><mi>κ</mi><mo>^</mo></mover><mi>t</mi></msub></math>、<math><msub><mi>b</mi><mi>t</mi></msub><mo>=</mo><msub><mover><mi>κ</mi><mo>^</mo></mover><mi>t</mi></msub><mo>⊙</mo><msub><mi>a</mi><mi>t</mi></msub></math>），使“移除”与“写入”的键可以不同，写强度也从标量变成逐通道向量。[48]（§3）原文据此证明了该更新式在标准复杂度猜想下能表达 TC⁰ 之外的函数，并用常数层识别全部正则语言；这是表达力层面的结论，与语言建模的实测表现是两件事。

#### 七条更新式并排

把这些机制的状态演化写在一起，差别只在系数的形状与是否随输入变化：[48]（表 1，按本文记号整理）

| 机制 | 状态演化 | 衰减形状 | 是否含 delta |
|---|---|---|---|
| 线性注意力 | S(t) = S(t−1) + v(t)k(t)ᵀ | 无 | 否 |
| RetNet | S(t) = γS(t−1) + v(t)k(t)ᵀ | 每头标量、常数 | 否 |
| Mamba2 | S(t) = α(t)S(t−1) + v(t)k(t)ᵀ | 每头标量、输入相关 | 否 |
| DeltaNet | S(t) = S(t−1)(I − β(t)k(t)k(t)ᵀ) + β(t)v(t)k(t)ᵀ | 无 | 是，标量写强度 |
| GDN | S(t) = S(t−1)(α(t)(I − β(t)k(t)k(t)ᵀ)) + β(t)v(t)k(t)ᵀ | 每头标量、输入相关 | 是，标量写强度 |
| KDA | S(t) = (I − β(t)k(t)k(t)ᵀ)Diag(α(t))S(t−1) + β(t)k(t)v(t)ᵀ | 每通道、输入相关 | 是，标量写强度 |
| RWKV-7 | S(t) = S(t−1)(diag(w(t)) + z(t)ᵀb(t)) + v(t)k(t)ᵀ | 每通道、输入相关 | 是，向量写强度 |

表中的“是否随输入变化”决定了内核对状态量的依赖：常数衰减可以在编译期把因子折进分块调度，输入相关的衰减必须先把 αₜ 或 wₜ 算出来再进入三角求解，这也是 GDN 与 RWKV-7 都要重写分块算法的原因。状态大小由 P×N 或 dᵥ×dₖ 给出，与历史长度无关；能精确保留多少条互不干扰的关联，仍受 delta 规则给出的秩上限约束。
