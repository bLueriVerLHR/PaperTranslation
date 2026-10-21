### RetNet：给状态加一层与内容无关的衰减

核化线性注意力的状态只增不减，长上下文里旧信息会挤占容量。RetNet 的保留机制（retention）先把衰减补上：状态在每次更新前按一个固定比例缩小，缩小的幅度逐头不同，并且允许并行训练与递推推理两种等价写法。[40]（§2.1）

#### 从状态递推到带衰减的并行形式

从一个一般的线性递推出发，状态 sₙ 由转移矩阵 A、键 Kₙ 与值 vₙ 更新，输出由查询 Qₙ 读出：

<math display="block"><msub><mi>s</mi><mi>n</mi></msub><mo>=</mo><mi>A</mi><msub><mi>s</mi><mrow><mi>n</mi><mo>−</mo><mn>1</mn></mrow></msub><mo>+</mo><msubsup><mi>K</mi><mi>n</mi><mi>T</mi></msubsup><msub><mi>v</mi><mi>n</mi></msub><mo>,</mo><mspace width="1em"/><msub><mi>o</mi><mi>n</mi></msub><mo>=</mo><msub><mi>Q</mi><mi>n</mi></msub><msub><mi>s</mi><mi>n</mi></msub><mo>=</mo><munderover><mo>∑</mo><mrow><mi>m</mi><mo>=</mo><mn>1</mn></mrow><mi>n</mi></munderover><msub><mi>Q</mi><mi>n</mi></msub><msup><mi>A</mi><mrow><mi>n</mi><mo>−</mo><mi>m</mi></mrow></msup><msubsup><mi>K</mi><mi>m</mi><mi>T</mi></msubsup><msub><mi>v</mi><mi>m</mi></msub></math>

把 A 对角化成 <math><mi>A</mi><mo>=</mo><mi>Λ</mi><mo stretchy="false">(</mo><mi>γ</mi><msup><mi>e</mi><mrow><mi>i</mi><mi>θ</mi></mrow></msup><mo stretchy="false">)</mo><msup><mi>Λ</mi><mrow><mo>−</mo><mn>1</mn></mrow></msup></math>，再把它吸收进 Q、K 的投影，转移矩阵就变成一个逐位置的复数因子；把 γ 取成实标量，输出写成相对距离上的显式衰减：

<math display="block"><msub><mi>o</mi><mi>n</mi></msub><mo>=</mo><munderover><mo>∑</mo><mrow><mi>m</mi><mo>=</mo><mn>1</mn></mrow><mi>n</mi></munderover><msup><mi>γ</mi><mrow><mi>n</mi><mo>−</mo><mi>m</mi></mrow></msup><mrow><mo stretchy="false">(</mo><msub><mi>Q</mi><mi>n</mi></msub><msup><mi>e</mi><mrow><mi>i</mi><mi>n</mi><mi>θ</mi></mrow></msup><mo stretchy="false">)</mo></mrow><msup><mrow><mo stretchy="false">(</mo><msub><mi>K</mi><mi>m</mi></msub><msup><mi>e</mi><mrow><mi>i</mi><mi>m</mi><mi>θ</mi></mrow></msup><mo stretchy="false">)</mo></mrow><mo>†</mo></msup><msub><mi>v</mi><mi>m</mi></msub></math>

指数项 <math><msup><mi>e</mi><mrow><mi>i</mi><mi>n</mi><mi>θ</mi></mrow></msup></math> 与位置成正比，随距离衰减的 <math><msup><mi>γ</mi><mrow><mi>n</mi><mo>−</mo><mi>m</mi></mrow></msup></math> 只依赖相对位置。两者合成一个矩阵，就得到与自注意力同形的并行写法：

<math display="block"><mi mathvariant="normal">Retention</mi><mo stretchy="false">(</mo><mi>X</mi><mo stretchy="false">)</mo><mo>=</mo><mo stretchy="false">(</mo><mi>Q</mi><msup><mi>K</mi><mi>T</mi></msup><mo>⊙</mo><mi>D</mi><mo stretchy="false">)</mo><mi>V</mi><mo>,</mo><mspace width="1em"/><msub><mi>D</mi><mrow><mi>n</mi><mi>m</mi></mrow></msub><mo>=</mo><msup><mi>γ</mi><mrow><mi>n</mi><mo>−</mo><mi>m</mi></mrow></msup><mspace width="0.3em"/><mo stretchy="false">(</mo><mi>n</mi><mo>≥</mo><mi>m</mi><mo stretchy="false">)</mo></math>

D 同时承担因果掩码与相对位置衰减。写成这样之后，训练可以按 <math><mi>O</mi><mo stretchy="false">(</mo><msup><mi>N</mi><mn>2</mn></msup><mi>d</mi><mo stretchy="false">)</mo></math> 的并行形式做，推理则用递推形式每步只读写一个 <math><msub><mi>d</mi><mi>v</mi></msub></math>×<math><msub><mi>d</mi><mi>k</mi></msub></math> 的状态，复杂度与历史长度无关。

分块形式把两者接起来：块内按并行形式算出 <math><mi>Q</mi><msup><mi>K</mi><mi>T</mi></msup><mo>⊙</mo><mi>D</mi></math> 那一项，块间的历史贡献只用 <math><mo stretchy="false">(</mo><mi>Q</mi><mo>·</mo><msub><mi>S</mi><mi>past</mi></msub><mo stretchy="false">)</mo></math> 与一个跨块衰减因子相乘，两部分相加得到块输出。[40]（§2.1、图 4）这与核化线性注意力的分块折中是同一套结构，区别只在块间传递的状态带衰减。

#### 逐头衰减给出不同的有效记忆长度

RetNet 把 γ 设成逐头不同的常数，第 h 个头取 <math><msub><mi>γ</mi><mi>h</mi></msub><mo>=</mo><mn>1</mn><mo>−</mo><msup><mn>2</mn><mrow><mo>−</mo><mn>5</mn><mo>−</mo><mi>h</mi></mrow></msup></math>。[40]（Eq.8）这个取值把“每个头看多长的历史”由公式直接定下，不需要再当超参数调：让不同头覆盖不同记忆跨度就是这一取值的设计意图。对 γ 接近 1 的情形，半衰期约为 <math><mi mathvariant="normal">ln</mi><mn>2</mn><mo>/</mo><mo stretchy="false">(</mo><mn>1</mn><mo>−</mo><mi>γ</mi><mo stretchy="false">)</mo></math>：h=1 时约 44 步，h=8 时约 5,680 步，头序号每加一，有效记忆长度翻一倍。

#### 固定衰减补了一半

衰减解决了“状态只增不减”，却没有让写入变得可纠错，也没有让衰减随内容变化。每一步按同一比例缩小的做法对待所有历史一视同仁：需要忘掉的噪声与需要保留的证据按同一个速率衰减，键值关联写错之后也没有撤除手段。这两点分别由 delta 规则与门控补上，而它们最终被合进同一个更新式。
