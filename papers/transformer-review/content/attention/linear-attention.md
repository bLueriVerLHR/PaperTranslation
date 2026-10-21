### 核化线性注意力：把求和顺序换过来

MQA、GQA 与 MLA 都在改“存什么、存多少”，键值仍然逐位置保存，随机访问的能力没有变化。核化线性注意力改写的是求和顺序本身：把相似性写成有限维特征的内积，只依赖查询的项就能提到对键的求和之外，历史因此被压成几个统计量，逐位置键值不再保留。[38]（§3）

#### 从核函数到可累计状态

设相似性能用有限维特征写开，<math><mi>κ</mi><mo stretchy="false">(</mo><mi>q</mi><mo>,</mo><mi>k</mi><mo stretchy="false">)</mo><mo>=</mo><msup><mi>φ</mi><mi>T</mi></msup><mo stretchy="false">(</mo><mi>q</mi><mo stretchy="false">)</mo><mi>φ</mi><mo stretchy="false">(</mo><mi>k</mi><mo stretchy="false">)</mo></math>，特征维度 r。配上正的归一化分母，位置 i 的输出就可以把只依赖查询的项提到对键的求和之外：

<math display="block"><msubsup><mi>y</mi><mi>i</mi><mi>T</mi></msubsup><mo>=</mo><mfrac><mrow><munder><mo>∑</mo><mi>j</mi></munder><msup><mi>φ</mi><mi>T</mi></msup><mo stretchy="false">(</mo><msub><mi>q</mi><mi>i</mi></msub><mo stretchy="false">)</mo><mi>φ</mi><mo stretchy="false">(</mo><msub><mi>k</mi><mi>j</mi></msub><mo stretchy="false">)</mo><msubsup><mi>v</mi><mi>j</mi><mi>T</mi></msubsup></mrow><mrow><munder><mo>∑</mo><mi>j</mi></munder><msup><mi>φ</mi><mi>T</mi></msup><mo stretchy="false">(</mo><msub><mi>q</mi><mi>i</mi></msub><mo stretchy="false">)</mo><mi>φ</mi><mo stretchy="false">(</mo><msub><mi>k</mi><mi>j</mi></msub><mo stretchy="false">)</mo></mrow></mfrac><mo>=</mo><mfrac><mrow><msup><mi>φ</mi><mi>T</mi></msup><mo stretchy="false">(</mo><msub><mi>q</mi><mi>i</mi></msub><mo stretchy="false">)</mo><mi>R</mi></mrow><mrow><msup><mi>φ</mi><mi>T</mi></msup><mo stretchy="false">(</mo><msub><mi>q</mi><mi>i</mi></msub><mo stretchy="false">)</mo><mi>z</mi></mrow></mfrac></math>

式中的 <math><mi>R</mi><mo>=</mo><munder><mo>∑</mo><mi>j</mi></munder><mi>φ</mi><mo stretchy="false">(</mo><msub><mi>k</mi><mi>j</mi></msub><mo stretchy="false">)</mo><msubsup><mi>v</mi><mi>j</mi><mi>T</mi></msubsup></math> 是特征与值的外积之和，<math><mi>z</mi><mo>=</mo><munder><mo>∑</mo><mi>j</mi></munder><mi>φ</mi><mo stretchy="false">(</mo><msub><mi>k</mi><mi>j</mi></msub><mo stretchy="false">)</mo></math> 累积归一化统计；值向量按列向量定义，输出公式给出它的行表示。这一步成立的唯一条件是 φ(qᵢ) 不参与对 j 的求和，交换求和顺序因此合法，不依赖核的任何近似性质。

因果情形只对当前位置及历史求和，两个统计量可以增量更新：

<math display="block"><msub><mi>R</mi><mi>i</mi></msub><mo>=</mo><msub><mi>R</mi><mrow><mi>i</mi><mo>−</mo><mn>1</mn></mrow></msub><mo>+</mo><mi>φ</mi><mo stretchy="false">(</mo><msub><mi>k</mi><mi>i</mi></msub><mo stretchy="false">)</mo><msubsup><mi>v</mi><mi>i</mi><mi>T</mi></msubsup><mo>,</mo><mspace width="1em"/><msub><mi>z</mi><mi>i</mi></msub><mo>=</mo><msub><mi>z</mi><mrow><mi>i</mi><mo>−</mo><mn>1</mn></mrow></msub><mo>+</mo><mi>φ</mi><mo stretchy="false">(</mo><msub><mi>k</mi><mi>i</mi></msub><mo stretchy="false">)</mo></math>

代入数字看规模：特征维度 r=128、值维度 <math><msub><mi>d</mi><mi>v</mi></msub></math>=64 时，状态是 128×64+128=8,320 个元素，与历史长度无关；同一模型若存显式 KV 缓存，8,192 个历史位置需要 8,192×64=524,288 个元素，相差约 63 倍。每步的更新与读取量也不再随历史增长，总工作量随序列长度线性增长。提高 r 以换取精度、或者特征构造本身较贵时，这部分的代价需要重新估计。原文用的具体特征是把 ELU 加一，取正值的目的是让分母为正；这一选择只保证归一化稳定，不保证与指数核等价。

#### 三种计算形态的并行度与算术量

同一套公式有三种落地方式，差别在并行度和中间量的存储上。[41]（§2.1）设序列长度 L、每头维度 d：

- 并行形式 <math><mo stretchy="false">(</mo><mi>Q</mi><msup><mi>K</mi><mi>T</mi></msup><mo>⊙</mo><mi>M</mi><mo stretchy="false">)</mo><mi>V</mi></math> 与普通注意力同形，算术量 <math><mi>O</mi><mo stretchy="false">(</mo><msup><mi>L</mi><mn>2</mn></msup><mi>d</mi><mo>+</mo><mi>L</mi><msup><mi>d</mi><mn>2</mn></msup><mo stretchy="false">)</mo></math>，但可以一步算完。
- 递推形式是上面的增量更新，算术量 <math><mi>O</mi><mo stretchy="false">(</mo><mi>L</mi><msup><mi>d</mi><mn>2</mn></msup><mo stretchy="false">)</mo></math>，沿序列不能并行，逐步的矩阵—向量操作也用不上张量核心。
- 分块形式把序列切成每块 C 个位置，块内按并行形式算，块间按递推形式传状态，算术量 <math><mi>O</mi><mo stretchy="false">(</mo><mi>L</mi><mi>C</mi><mi>d</mi><mo>+</mo><mi>L</mi><msup><mi>d</mi><mn>2</mn></msup><mo stretchy="false">)</mo></math>，步数为 <math><mi>O</mi><mo stretchy="false">(</mo><mi>L</mi><mo>/</mo><mi>C</mi><mo stretchy="false">)</mo></math>，块内状态无需落盘。

C=L 退化为全并行，C=1 退化为纯递推，实现里通常取 64 或 128，在并行度与算术量之间折中。这条折中关系是后面所有状态模型共用的：RetNet、DeltaNet、GDN 与 Mamba2 的训练内核都在分块形式上实现，整段序列上的纯递推只出现在推导里。

#### 有限维特征装不下指数点积矩阵

标准注意力用指数点积核，再按查询归一化。有限维特征给出的未归一化相似性矩阵是 <math><mi>Φ</mi><mo stretchy="false">(</mo><mi>Q</mi><mo stretchy="false">)</mo><msup><mi>Φ</mi><mi>T</mi></msup><mo stretchy="false">(</mo><mi>K</mi><mo stretchy="false">)</mo></math>，秩至多为 r。指数点积矩阵的秩上界要高得多：在维度为一、缩放为一时取 <math><msub><mi>q</mi><mi>i</mi></msub><mo>=</mo><mi>i</mi><mo>−</mo><mn>1</mn></math>、<math><msub><mi>k</mi><mi>j</mi></msub><mo>=</mo><mi>log</mi><msub><mi>t</mi><mi>j</mi></msub></math>，各 <math><msub><mi>t</mi><mi>j</mi></msub></math> 互异且为正，分数矩阵就是一个 Vandermonde 矩阵：

<math display="block"><msub><mi>B</mi><mrow><mi>i</mi><mi>j</mi></mrow></msub><mo>=</mo><mi mathvariant="normal">exp</mi><mo stretchy="false">(</mo><msub><mi>q</mi><mi>i</mi></msub><msub><mi>k</mi><mi>j</mi></msub><mo stretchy="false">)</mo><mo>=</mo><msubsup><mi>t</mi><mi>j</mi><mrow><mi>i</mi><mo>−</mo><mn>1</mn></mrow></msubsup><mo>,</mo><mspace width="1em"/><mi mathvariant="normal">det</mi><mo stretchy="false">(</mo><mi>B</mi><mo stretchy="false">)</mo><mo>=</mo><munder><mo>∏</mo><mrow><mn>1</mn><mo>≤</mo><mi>i</mi><mo>&lt;</mo><mi>j</mi><mo>≤</mo><mi>N</mi></mrow></munder><mo stretchy="false">(</mo><msub><mi>t</mi><mi>j</mi></msub><mo>−</mo><msub><mi>t</mi><mi>i</mi></msub><mo stretchy="false">)</mo><mo>≠</mo><mn>0</mn></math>

行列式非零，矩阵满秩。按行除以正的行和相当于左乘一个可逆对角矩阵，秩不变。于是序列长度超过固定特征维度 r 时，这个标准 softmax 注意力矩阵写不成该有限维特征分解。反例证明的是“对任意输入、任意长度都等价”这个说法不成立；换到特定输入分布上，近似核或别的核照样可以训出有效模型。[10]

#### 加法写入的两个缺口

状态递推到此还很朴素：新来的键值对只是被加到状态上，旧关联没有任何删除途径。状态是 <math><msub><mi>d</mi><mi>v</mi></msub></math>×<math><msub><mi>d</mi><mi>k</mi></msub></math> 的矩阵，一旦有效关联条数超过它的秩，不同的键就会映射到相近的读出结果，后续工作把这种现象称为键碰撞。[41]（§2.2）这留下两个具体缺口：写入无法纠错，衰减也无法随内容变化。RetNet 补的是衰减这一项，DeltaNet 补的是写入这一项，两者后来被合成同一个更新式。
