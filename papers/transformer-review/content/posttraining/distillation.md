#### 蒸馏：传递输出关系

教师可以是更大模型或模型集合，学生则具有不同容量和部署成本。Hinton 等把知识传递理解为输入到输出的映射：除了最高概率类别，其他类别的相对概率也反映教师学到的相似关系。[22] 蒸馏用这些关系训练学生，不要求两者具有相同内部参数或网络宽度。

##### 软目标比单个标签多提供什么

硬标签只标出一个正确类别，软分布还告诉学生教师容易混淆哪些候选。设教师与学生的 logits 分别为 v、z，温度为正数 T，软概率为 softmax(v/T) 和 softmax(z/T)。将它们记为 pT、qT，一个常见混合目标为：

<math display="block"><mi>ℒ</mi><mo>=</mo><mi>λ</mi><msup><mi>T</mi><mn>2</mn></msup><mi mathvariant="normal">KL</mi><mo>(</mo><msub><mi>p</mi><mi>T</mi></msub><mo>‖</mo><msub><mi>q</mi><mi>T</mi></msub><mo>)</mo><mo>+</mo><mo>(</mo><mn>1</mn><mo>−</mo><mi>λ</mi><mo>)</mo><mi mathvariant="normal">CE</mi><mo>(</mo><mi>y</mi><mo>,</mo><msub><mi>q</mi><mn>1</mn></msub><mo>)</mo></math>

教师保持固定、0≤λ≤1。KL 的教师熵不依赖学生，因此其学生梯度与软目标交叉熵相同；硬目标在温度一的分布上计算，使真实标签仍能影响学习。数据覆盖与教师误差同样被传递，软目标不会自动变成更可靠的真值。

##### 温度平方因子从哪里来

对软目标交叉熵，学生 logit 的导数为：

<math display="block"><mfrac><mrow><mo>∂</mo><msub><mi>ℒ</mi><mi mathvariant="normal">soft</mi></msub></mrow><mrow><mo>∂</mo><msub><mi>z</mi><mi>j</mi></msub></mrow></mfrac><mo>=</mo><mfrac><mn>1</mn><mi>T</mi></mfrac><mo>(</mo><msub><mi>q</mi><mi>j</mi></msub><mo>−</mo><msub><mi>p</mi><mi>j</mi></msub><mo>)</mo></math>

第一个 1/T 来自 logit 缩放的链式法则。若类别数为 K、教师和学生 logits 各自中心化，并且温度相对 logit 幅度足够高，指数的一阶展开给出 qⱼ≈1/K+zⱼ/(KT)，教师同理，于是：

<math display="block"><mfrac><mrow><mo>∂</mo><msub><mi>ℒ</mi><mi mathvariant="normal">soft</mi></msub></mrow><mrow><mo>∂</mo><msub><mi>z</mi><mi>j</mi></msub></mrow></mfrac><mo>≈</mo><mfrac><mrow><msub><mi>z</mi><mi>j</mi></msub><mo>−</mo><msub><mi>v</mi><mi>j</mi></msub></mrow><mrow><mi>K</mi><msup><mi>T</mi><mn>2</mn></msup></mrow></mfrac></math>

另一个 1/T 来自概率差随温度缩小。乘 T² 因而近似保持软目标梯度相对硬目标的尺度；这个近似只在相应温度范围内成立，换温度要重新校准尺度。[22] 高温极限接近匹配中心化 logits，有限温度则对不同候选赋予不同权重。

##### 生成模型中的两种传递接口

语言模型可以在给定前缀下匹配教师的词表分布，也可以利用教师生成的回答做监督训练。前者保留逐位置候选概率，要求对应输出空间与教师计算；后者只需文本样本，有限样本中没有逐位置保存完整软分布。两者共享教师信息来源，却有不同的数据对象和覆盖条件。[17]

学生容量有限时，多个目标关系可能需要取舍。蒸馏的价值来自任务相关关系能否以较低成本进入学生，评价则同时涉及任务结果、教师错误的继承和真实部署成本。低秩适配动的是任务增量，蒸馏动的是整个学生模型，两者作用对象不同。
