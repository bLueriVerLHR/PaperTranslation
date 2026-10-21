#### 校准：正确决策与可信概率

分类正确率只关心最高分标签，概率质量还关心模型表达了多大的确信。Guo 等在图像与文档分类网络中观察到准确率与校准可以分离，并研究了后处理校准。[23] 这一框架解释概率的评价对象，不能直接把分类实验结论推广为生成答案的真实性保证。

##### 校准是分布上的频率关系

记预测标签为 Ŷ、其置信度为 Ĉ。理想的最高类置信度校准要求，在分布支持内相应条件成立：

<math display="block"><mi>P</mi><mo>(</mo><mover><mi>Y</mi><mo>^</mo></mover><mo>=</mo><mi>Y</mi><mo>|</mo><mover><mi>C</mi><mo>^</mo></mover><mo>=</mo><mi>p</mi><mo>)</mo><mo>=</mo><mi>p</mi></math>

例如，置信度接近 0.8 的一组预测应有接近 80% 正确；这一对应关系针对一组预测，单个样本的成败无法由此判断。有限样本常按置信度分箱，比较每箱正确率与平均置信度。仅计非空箱 Bₘ 时，经验 ECE 为：[23]

<math display="block"><mi mathvariant="normal">ECE</mi><mo>=</mo><munder><mo>∑</mo><mi>m</mi></munder><mfrac><mrow><mo>|</mo><msub><mi>B</mi><mi>m</mi></msub><mo>|</mo></mrow><mi>n</mi></mfrac><mo>|</mo><mi mathvariant="normal">acc</mi><mo stretchy="false">(</mo><msub><mi>B</mi><mi>m</mi></msub><mo stretchy="false">)</mo><mo>−</mo><mi mathvariant="normal">conf</mi><mo stretchy="false">(</mo><msub><mi>B</mi><mi>m</mi></msub><mo stretchy="false">)</mo><mo>|</mo></math>

分箱数量与样本组成改变估计，箱内平均还可能掩盖更细粒度差异。因此 ECE 是汇总近似，涵盖的概率关系以所选分箱为限。负对数似然又对错误真标签被赋予极低概率特别敏感，提供与最高类正确率不同的信息。

##### 温度缩放为什么可以不改变分类结果

固定模型 logits z，温度缩放只学习一个正参数 T，输出 softmax(z/T)。对任意两个类别，zᵢ>zⱼ 当且仅当 zᵢ/T>zⱼ/T，所以精确算术下 argmax 集合不变。概率幅度却随 T 改变，校准可以改善而分类标签完全相同。[23]

固定 logits 时，输出熵的温度导数为：

<math display="block"><mfrac><mrow><mi>d</mi><mi>H</mi></mrow><mrow><mi>d</mi><mi>T</mi></mrow></mfrac><mo>=</mo><mfrac><mrow><msub><mi mathvariant="normal">Var</mi><mrow><mi>q</mi><mo stretchy="false">(</mo><mi>T</mi><mo stretchy="false">)</mo></mrow></msub><mo stretchy="false">(</mo><mi>z</mi><mo stretchy="false">)</mo></mrow><msup><mi>T</mi><mn>3</mn></msup></mfrac><mo>≥</mo><mn>0</mn></math>

该式可由 H=log Z−E[z]/T 对 T 求导得到。温度增大使分布更平缓，但更平缓是否更符合真实正确率，仍由数据决定。Guo 等用保留验证集最小化负对数似然选择 T，假定相关数据来自相同分布；一个共享温度也不能任意修正每类或每个输入的特殊误差。

##### 分类温度、蒸馏温度与生成采样温度

蒸馏温度塑造教师提供的软目标，校准温度拟合概率与标签的关系，生成采样温度则改变实际输出的采样分布。形式相似，作用阶段与目标不同。分类 argmax 不变的性质，也不意味着采样生成得到相同回答。

语言模型的 token 概率表示给定前缀下某个 token 出现的概率；回答事实正确与否是另一事件。整段序列概率还受长度和表达方式影响，流畅的错误陈述可以具有高语言概率。生成任务中的可靠性因而需要明确评价事件、证据与目标分布，把任意 softmax 数值直接当作答案正确率会出现错位。
