#### 配对判别：相对竞争与跨模态对齐

图文描述包含大量细节、表达方式和措辞差异，逐词复现描述要求模型同时解决视觉理解与文本生成。CLIP 选择另一种代理任务：判断整段文本与哪幅图像配对，让双塔表示直接服务于跨模态匹配。[4] 原文比较了生成、词袋预测与对比目标的零样本迁移效率；其结果对应这些具体设置，机制上的变化则在于监督从复现全部文字转向区分候选关系。

对 B 个图文对，投影后单位向量为 uᵢ、vⱼ，分数 sᵢⱼ=αuᵢᵀvⱼ，其中正尺度 α 采用指数参数化。图像到文本的概率与对称损失为：

<math display="block"><msubsup><mi>p</mi><mrow><mi>i</mi><mi>j</mi></mrow><mrow><mi>I</mi><mo>→</mo><mi>T</mi></mrow></msubsup><mo>=</mo><mfrac><mrow><mi mathvariant="normal">exp</mi><mo>(</mo><msub><mi>s</mi><mrow><mi>i</mi><mi>j</mi></mrow></msub><mo>)</mo></mrow><mrow><munder><mo>∑</mo><mi>k</mi></munder><mi mathvariant="normal">exp</mi><mo>(</mo><msub><mi>s</mi><mrow><mi>i</mi><mi>k</mi></mrow></msub><mo>)</mo></mrow></mfrac><mo>,</mo><mspace width="1em"/><mi>ℒ</mi><mo>=</mo><mo>−</mo><mfrac><mn>1</mn><mrow><mn>2</mn><mi>B</mi></mrow></mfrac><munder><mo>∑</mo><mi>i</mi></munder><mo>(</mo><mi mathvariant="normal">log</mi><msubsup><mi>p</mi><mrow><mi>i</mi><mi>i</mi></mrow><mrow><mi>I</mi><mo>→</mo><mi>T</mi></mrow></msubsup><mo>+</mo><mi mathvariant="normal">log</mi><msubsup><mi>p</mi><mrow><mi>i</mi><mi>i</mi></mrow><mrow><mi>T</mi><mo>→</mo><mi>I</mi></mrow></msubsup><mo>)</mo></math>

反向概率按固定文本对所有图像归一化，即对分数矩阵的列归一化。两个方向同时约束检索关系，输出是一组相对候选分数，供检索与排序使用。

##### 负候选为什么改变表示学习

仅要求配对向量接近时，把所有输入映射到同一向量也可以满足相似性要求。对比分类加入候选竞争：对单行损失 ℓᵢ，查询单位向量的导数为：

<math display="block"><mfrac><mrow><mo>∂</mo><msub><mi>ℓ</mi><mi>i</mi></msub></mrow><mrow><mo>∂</mo><msub><mi>u</mi><mi>i</mi></msub></mrow></mfrac><mo>=</mo><mi>α</mi><mo>(</mo><munder><mo>∑</mo><mi>j</mi></munder><msub><mi>p</mi><mrow><mi>i</mi><mi>j</mi></mrow></msub><msub><mi>v</mi><mi>j</mi></msub><mo>−</mo><msub><mi>v</mi><mi>i</mi></msub><mo>)</mo></math>

高概率错误候选对更新影响较大，梯度不仅拉向正确配对，还反映当前竞争分布。这里把归一化后的 uᵢ 视为中间变量；传回归一化前特征时，还要经过 L2 归一化的雅可比，更新受到单位球面约束。

全部表示相同时，每行概率均为 1/B，损失为 log B。作为损失空间中的对照，把各样本嵌入视为可独立选择的向量。若嵌入维度至少为 B，并令每对图文使用同一组相互正交的单位向量，正配对分数为 α，其他分数为零，单行损失成为：

<math display="block"><mi>ℓ</mi><mo>=</mo><mi mathvariant="normal">log</mi><mo>(</mo><mn>1</mn><mo>+</mo><mo>(</mo><mi>B</mi><mo>−</mo><mn>1</mn><mo>)</mo><msup><mi>e</mi><mrow><mo>−</mo><mi>α</mi></mrow></msup><mo>)</mo><mo>&lt;</mo><mi mathvariant="normal">log</mi><mi>B</mi></math>

该构造在 B>1、α>0 时说明目标偏好可区分的匹配。这是损失几何的比较；优化能否逃离所有坍塌状态要另行论证；完全相同的表示仍可能形成特殊驻点，实际学习依赖初始化、参数化和数据。

##### 归一化、尺度与候选组成相互作用

L2 归一化去除向量长度对点积分数的直接影响，使模型主要通过方向表达关系；α 则集中控制 softmax 的竞争强度。对一个查询，记余弦为 cᵢⱼ，有：

<math display="block"><mfrac><mrow><mo>∂</mo><msub><mi>ℓ</mi><mi>i</mi></msub></mrow><mrow><mo>∂</mo><mi>α</mi></mrow></mfrac><mo>=</mo><munder><mo>∑</mo><mi>j</mi></munder><msub><mi>p</mi><mrow><mi>i</mi><mi>j</mi></mrow></msub><msub><mi>c</mi><mrow><mi>i</mi><mi>j</mi></mrow></msub><mo>−</mo><msub><mi>c</mi><mrow><mi>i</mi><mi>i</mi></mrow></msub></math>

正确配对比竞争候选更相似时，增加尺度可让分类更确信；若高分候选反而错误，扩大尺度会放大相应损失。尺度与向量方向共同更新，固定尺度和学习尺度因而具有不同的优化过程。[4]

批内其他配对承担负候选角色，但这个标签来自配对索引，与现实中语义是否相互排斥无关。两段描述可以指向相近内容，一幅图像也可能适配多种文本；重复或近义样本会改变候选竞争。批大小既决定梯度估计，也改变每个查询面对的候选集合，因此不能仅以独立样本平均的逻辑解释其全部影响。
