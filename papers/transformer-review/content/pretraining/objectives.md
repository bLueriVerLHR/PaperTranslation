### 目标函数与监督信号

预训练把数据中的某种关系转化为可优化的预测任务，再用学到的参数或表示支持其他任务。原始 ViT 主要利用类别标签，BERT 预测被扰动的 token，MAE 重建缺失图块，CLIP 判断图文配对。[1–4] 这些方法共享表示学习的目的，却选择了不同的条件信息、预测对象和误差度量。目标函数因此规定了怎样计算损失，也规定了哪些差异会推动参数更新。

#### 条件预测决定模型需要保留的信息

把模型可见的信息记为 C、预测对象记为 Y。对离散目标，条件交叉熵的总体风险为：

<math display="block"><mi>R</mi><mo stretchy="false">(</mo><mi>θ</mi><mo stretchy="false">)</mo><mo>=</mo><msub><mi>𝔼</mi><mrow><mi>C</mi><mo>,</mo><mi>Y</mi></mrow></msub><mo stretchy="false">[</mo><mo>−</mo><mi mathvariant="normal">log</mi><msub><mi>p</mi><mi>θ</mi></msub><mo stretchy="false">(</mo><mi>Y</mi><mo>|</mo><mi>C</mi><mo stretchy="false">)</mo><mo stretchy="false">]</mo></math>

固定一个条件 c，设数据条件分布为 P，模型分布为 Q，并假定 Q 在 P 的支持上为正。加减数据分布自身的对数，可将该条件下的风险展开为：

<math display="block"><mo>−</mo><munder><mo>∑</mo><mi>y</mi></munder><mi>P</mi><mo stretchy="false">(</mo><mi>y</mi><mo>|</mo><mi>c</mi><mo stretchy="false">)</mo><mi mathvariant="normal">log</mi><mi>Q</mi><mo stretchy="false">(</mo><mi>y</mi><mo>|</mo><mi>c</mi><mo stretchy="false">)</mo><mo>=</mo><mi>H</mi><mo stretchy="false">(</mo><mi>P</mi><mo stretchy="false">(</mo><mo>·</mo><mo>|</mo><mi>c</mi><mo stretchy="false">)</mo><mo stretchy="false">)</mo><mo>+</mo><mi mathvariant="normal">KL</mi><mo stretchy="false">(</mo><mi>P</mi><mo stretchy="false">(</mo><mo>·</mo><mo>|</mo><mi>c</mi><mo stretchy="false">)</mo><mo>‖</mo><mi>Q</mi><mo stretchy="false">(</mo><mo>·</mo><mo>|</mo><mi>c</mi><mo stretchy="false">)</mo><mo stretchy="false">)</mo></math>

熵项由数据和条件决定；KL 项非负，其非负性可由对数不等式 log u ≤ u−1 得到。在模型能够表达相应分布的理想条件下，最小风险对应恢复数据的条件分布；输出一个确定答案在一般情况下会抬高风险。有限容量和有限样本下，模型则在可表达的分布族内逼近这个目标。

这个分解也解释了可见性的重要性：条件中若已经包含真实答案，任务可以通过读取答案完成；条件删除了全部相关线索，剩下的又可能只是无法进一步降低的条件不确定性。有价值的预训练任务在两者之间组织信息，使预测需要利用可迁移的关系。类别监督、缺失内容预测和配对判别分别要求保留不同关系，没有一种损失天然覆盖全部下游需求。[1–4]

#### 自回归目标与双向表征的不同条件

自回归语言模型按链式规则建立序列概率，并最大化真实序列的似然：[17]

<math display="block"><msub><mi>ℒ</mi><mi mathvariant="normal">AR</mi></msub><mo>=</mo><mo>−</mo><munder><mo>∑</mo><mi>t</mi></munder><mi mathvariant="normal">log</mi><msub><mi>p</mi><mi>θ</mi></msub><mo stretchy="false">(</mo><msub><mi>x</mi><mi>t</mi></msub><mo>|</mo><msub><mi>x</mi><mrow><mo>&lt;</mo><mi>t</mi></mrow></msub><mo stretchy="false">)</mo></math>

每个位置的目标是下一个真实 token，条件只包含其前缀。共享参数必须在不同前缀上预测不同后续内容，因此语法、事实关联和篇章规律都可能成为降低损失的资源；这些能力来自数据中的可预测关系，似然目标只提供优化方向。因果掩码让训练时的可见条件与生成时对应，已知目标序列又允许训练并行计算各位置的损失。

BERT 改变的是条件：预测缺失 token 时可以同时读取左、右上下文。[1] 这为理解任务提供不同的信息结构，但多个掩码位置的条件预测并不直接等于上述顺序联合概率分解。两类目标的区别由所学习的条件关系决定，与损失函数叫什么名字无关。

对以 softmax 输出词表概率的单个目标，若正确 token 为 y、logit 为 z，交叉熵导数为：

<math display="block"><mfrac><mrow><mo>∂</mo><mi>ℓ</mi></mrow><mrow><mo>∂</mo><msub><mi>z</mi><mi>j</mi></msub></mrow></mfrac><mo>=</mo><msub><mi>p</mi><mi>j</mi></msub><mo>−</mo><msub><mi>𝟙</mi><mrow><mi>j</mi><mo>=</mo><mi>y</mi></mrow></msub></math>

更新降低预测分布与目标指示之间的差异。损失在哪些位置计算、预测时能读哪些输入、各目标以多大权重出现，分别决定梯度的来源、条件和相对强度；后续几种预训练设计正沿这些因素展开。
