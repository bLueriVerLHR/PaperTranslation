### 数据准备：有效分布、过滤与训练课程

数据准备决定训练目标在哪个分布上求期望。Zhao 等的 LLM 综述将其组织为来源、预处理与调度，讨论去重、质量过滤、隐私处理、数据混合和课程安排。[17] 对语言语料而言，这些操作不仅改变可用文件，也改变内容在参数更新中出现的频率和顺序；视觉与其他模态则按各自的样本结构建立相应分布。

#### 重复改变了经验风险的加权

设互不相同的内容 xᵢ 在数据集中重复 mᵢ 次，给定该内容时对输入扰动等随机因素取平均的损失为 ℓᵢ。均匀采样文件或记录时，对应的经验风险为：

<math display="block"><mover><mi>R</mi><mo>^</mo></mover><mo>=</mo><mfrac><mrow><munder><mo>∑</mo><mi>i</mi></munder><msub><mi>m</mi><mi>i</mi></msub><msub><mi>ℓ</mi><mi>i</mi></msub></mrow><mrow><munder><mo>∑</mo><mi>i</mi></munder><msub><mi>m</mi><mi>i</mi></msub></mrow></mfrac></math>

重复内容的权重由重复次数增大，并未按同样比例增加独立证据。模板或转载页面大量出现时，训练预算会反复作用于相近关系。文档级、句子级和近似去重分别针对不同重复来源，粒度也影响哪些差异被保留。[17]

去重与领域覆盖之间存在真实取舍。两版业务规则可能只改变一个日期、阈值或否定词，表面高度相似却具有不同适用条件；相同术语也可能在不同语境中表达不同关系。去重策略因此要区分内容冗余与关键差异，相似度高推不出信息价值低。

#### 过滤改变支持范围，隐私是另一项条件

若原始分布为 P(x)、保留概率为 f(x)，并且平均保留概率非零，则过滤后的分布为：

<math display="block"><msub><mi>P</mi><mi mathvariant="normal">filtered</mi></msub><mo stretchy="false">(</mo><mi>x</mi><mo stretchy="false">)</mo><mo>=</mo><mfrac><mrow><mi>f</mi><mo stretchy="false">(</mo><mi>x</mi><mo stretchy="false">)</mo><mi>P</mi><mo stretchy="false">(</mo><mi>x</mi><mo stretchy="false">)</mo></mrow><mrow><msub><mi>𝔼</mi><mi>P</mi></msub><mo stretchy="false">[</mo><mi>f</mi><mo stretchy="false">(</mo><mi>X</mi><mo stretchy="false">)</mo><mo stretchy="false">]</mo></mrow></mfrac></math>

质量规则在移除噪声的同时，对数据分布重新赋权；若某类内容总被过滤，它会从可学习的支持范围中消失。语言、领域和表达形式的覆盖因此可能随过滤条件变化。去重控制重复权重，质量过滤控制保留内容，隐私处理限制可使用的信息，三者解决不同问题。[17]

#### 混合权重决定目标，课程还改变更新路径

不同来源的分布为 Pₖ、混合权重为 wₖ，权重非负且和为一时，总体风险与梯度分别为：

<math display="block"><mi>R</mi><mo stretchy="false">(</mo><mi>θ</mi><mo stretchy="false">)</mo><mo>=</mo><munder><mo>∑</mo><mi>k</mi></munder><msub><mi>w</mi><mi>k</mi></msub><msub><mi>R</mi><mi>k</mi></msub><mo stretchy="false">(</mo><mi>θ</mi><mo stretchy="false">)</mo><mo>,</mo><mspace width="1em"/><mi>∇</mi><mi>R</mi><mo stretchy="false">(</mo><mi>θ</mi><mo stretchy="false">)</mo><mo>=</mo><munder><mo>∑</mo><mi>k</mi></munder><msub><mi>w</mi><mi>k</mi></msub><mi>∇</mi><msub><mi>R</mi><mi>k</mi></msub><mo stretchy="false">(</mo><mi>θ</mi><mo stretchy="false">)</mo></math>

较小但重要的专业集合可以通过混合权重获得更多更新机会，同时会改变通用与专业目标的相对作用。当不同来源的梯度方向冲突时，权重改变就会改变合成更新方向；容量有限时，改善一个来源的风险未必同时改善全部来源。

课程进一步改变来源在什么阶段出现。即使两种安排各使用一次来源 A 和 B，有限步优化也未必到达相同参数。以相同步长 η 的两次普通梯度更新为例，在初始 θ 处记梯度为 gₐ、gᵦ，Hessian 为 Hₐ、Hᵦ。若损失足够光滑、邻域中的相应导数有界，Taylor 展开给出：

<math display="block"><msub><mi>θ</mi><mi mathvariant="normal">AB</mi></msub><mo>−</mo><msub><mi>θ</mi><mi mathvariant="normal">BA</mi></msub><mo>=</mo><msup><mi>η</mi><mn>2</mn></msup><mo>(</mo><msub><mi>H</mi><mi mathvariant="normal">B</mi></msub><msub><mi>g</mi><mi mathvariant="normal">A</mi></msub><mo>−</mo><msub><mi>H</mi><mi mathvariant="normal">A</mi></msub><msub><mi>g</mi><mi mathvariant="normal">B</mi></msub><mo>)</mo><mo>+</mo><mi>O</mi><mo stretchy="false">(</mo><msup><mi>η</mi><mn>3</mn></msup><mo stretchy="false">)</mo></math>

原因是第二步梯度在第一步更新后的参数处求值。这个局部分析说明数据顺序可以改变学习路径，而不据此确定哪一种课程最优。混合比例、课程和领域继续训练分别控制目标权重、更新顺序与分布变化，最终还要结合旧能力保持和目标任务表现解释。[17]
