### 线性注意力与低秩压缩

线性注意力、序列低秩压缩、权重低秩近似都会出现“低秩”这个词，改的对象却不一样：权重近似动的是模型参数，序列压缩动的是可供访问的键值表示，核化注意力改的是相似性表达与求和顺序。高效 Transformer 综述把这些路线放在可交叠的分类里，读实现时仍要回到各自的代数前提。[10]

#### 从核函数到可累计状态

设相似性能用有限维特征写开，<math><mi>κ</mi><mo>(</mo><mi>q</mi><mo>,</mo><mi>k</mi><mo>)</mo><mo>=</mo><msup><mi>φ</mi><mi>T</mi></msup><mo>(</mo><mi>q</mi><mo>)</mo><mi>φ</mi><mo>(</mo><mi>k</mi><mo>)</mo></math>，特征维度 r。配上正的归一化分母，位置 i 的输出就可以把只依赖查询的项提到对键的求和之外：

<math display="block"><msubsup><mi>y</mi><mi>i</mi><mi>T</mi></msubsup><mo>=</mo><mfrac><mrow><munder><mo>∑</mo><mi>j</mi></munder><msup><mi>φ</mi><mi>T</mi></msup><mo>(</mo><msub><mi>q</mi><mi>i</mi></msub><mo>)</mo><mi>φ</mi><mo>(</mo><msub><mi>k</mi><mi>j</mi></msub><mo>)</mo><msubsup><mi>v</mi><mi>j</mi><mi>T</mi></msubsup></mrow><mrow><munder><mo>∑</mo><mi>j</mi></munder><msup><mi>φ</mi><mi>T</mi></msup><mo>(</mo><msub><mi>q</mi><mi>i</mi></msub><mo>)</mo><mi>φ</mi><mo>(</mo><msub><mi>k</mi><mi>j</mi></msub><mo>)</mo></mrow></mfrac><mo>=</mo><mfrac><mrow><msup><mi>φ</mi><mi>T</mi></msup><mo>(</mo><msub><mi>q</mi><mi>i</mi></msub><mo>)</mo><mi>R</mi></mrow><mrow><msup><mi>φ</mi><mi>T</mi></msup><mo>(</mo><msub><mi>q</mi><mi>i</mi></msub><mo>)</mo><mi>z</mi></mrow></mfrac></math>

式中的 <math><mi>R</mi><mo>=</mo><munder><mo>∑</mo><mi>j</mi></munder><mi>φ</mi><mo>(</mo><msub><mi>k</mi><mi>j</mi></msub><mo>)</mo><msubsup><mi>v</mi><mi>j</mi><mi>T</mi></msubsup></math> 是特征与值的外积之和，<math><mi>z</mi><mo>=</mo><munder><mo>∑</mo><mi>j</mi></munder><mi>φ</mi><mo>(</mo><msub><mi>k</mi><mi>j</mi></msub><mo>)</mo></math> 累积归一化统计；值向量按列向量定义，输出公式给出它的行表示。这一步能做的原因是 φ(qᵢ) 不参与对 j 的求和，交换求和顺序因此合法。

因果情形只对当前位置及历史求和，两个统计量可以增量更新：

<math display="block"><msub><mi>R</mi><mi>i</mi></msub><mo>=</mo><msub><mi>R</mi><mrow><mi>i</mi><mo>−</mo><mn>1</mn></mrow></msub><mo>+</mo><mi>φ</mi><mo>(</mo><msub><mi>k</mi><mi>i</mi></msub><mo>)</mo><msubsup><mi>v</mi><mi>i</mi><mi>T</mi></msubsup><mo>,</mo><mspace width="1em"/><msub><mi>z</mi><mi>i</mi></msub><mo>=</mo><msub><mi>z</mi><mrow><mi>i</mi><mo>−</mo><mn>1</mn></mrow></msub><mo>+</mo><mi>φ</mi><mo>(</mo><msub><mi>k</mi><mi>i</mi></msub><mo>)</mo></math>

代入数字看规模：特征维度 r=128、值维度 dᵥ=64 时，状态是 128×64+128=8320 个元素，与历史长度无关；同一模型若存显式 KV 缓存，8192 个历史位置需要 8192×64=524,288 个元素，相差约 63 倍。每步的更新与读取量也不再随历史增长，总工作量因此可以随序列长度线性增长。提高 r 以换取精度、或者特征构造本身较贵时，这部分的代价需要重新估计。

#### 有限维特征装不下指数点积矩阵

标准注意力用指数点积核，再按查询归一化。有限维特征给出的未归一化相似性矩阵是 <math><mi>Φ</mi><mo>(</mo><mi>Q</mi><mo>)</mo><msup><mi>Φ</mi><mi>T</mi></msup><mo>(</mo><mi>K</mi><mo>)</mo></math>，秩至多为 r。指数点积矩阵的秩上界要高得多：在维度为一、缩放为一时取 <math><msub><mi>q</mi><mi>i</mi></msub><mo>=</mo><mi>i</mi><mo>−</mo><mn>1</mn></math>、<math><msub><mi>k</mi><mi>j</mi></msub><mo>=</mo><mi mathvariant="normal">log</mi><msub><mi>t</mi><mi>j</mi></msub></math>，各 <math><msub><mi>t</mi><mi>j</mi></msub></math> 互异且为正，分数矩阵就是一个 Vandermonde 矩阵：

<math display="block"><msub><mi>B</mi><mrow><mi>i</mi><mi>j</mi></mrow></msub><mo>=</mo><mi mathvariant="normal">exp</mi><mo>(</mo><msub><mi>q</mi><mi>i</mi></msub><msub><mi>k</mi><mi>j</mi></msub><mo>)</mo><mo>=</mo><msubsup><mi>t</mi><mi>j</mi><mrow><mi>i</mi><mo>−</mo><mn>1</mn></mrow></msubsup><mo>,</mo><mspace width="1em"/><mi mathvariant="normal">det</mi><mo>(</mo><mi>B</mi><mo>)</mo><mo>=</mo><munder><mo>∏</mo><mrow><mn>1</mn><mo>≤</mo><mi>i</mi><mo>&lt;</mo><mi>j</mi><mo>≤</mo><mi>N</mi></mrow></munder><mo>(</mo><msub><mi>t</mi><mi>j</mi></msub><mo>−</mo><msub><mi>t</mi><mi>i</mi></msub><mo>)</mo><mo>≠</mo><mn>0</mn></math>

行列式非零，矩阵满秩。按行除以正的行和相当于左乘一个可逆对角矩阵，秩不变。于是序列长度超过固定特征维度 r 时，这个标准 softmax 注意力矩阵写不成该有限维特征分解。反例证明的是“对任意输入、任意长度都等价”这个说法不成立；换到特定输入分布上，近似核或别的核照样可以训出有效模型。[10]

#### 状态压缩与序列低秩压缩的取舍

可累计状态把过去的键和值压进几个统计量，查询只能通过这些统计量访问历史。序列低秩方法换一条路：把多个位置投影成较少的键值表示，查询再去访问压缩结果，归一化形式可以保留，压缩是否够用同样取决于任务。两条路都在缩小历史表示的规模，丢信息的方式不同。

完整 KV 缓存保留每个历史位置的独立键值，用更大的存储与读取换取逐位置可寻址的选择能力；固定大小的累计状态省空间，代价是拿不回同样的寻址粒度。长上下文里的精确证据检索与持续状态建模，因此可能偏好不同的表示。判断一种线性结构适合什么任务，需要把渐近复杂度、历史访问方式和训练目标放在一起看。
