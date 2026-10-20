### 缩放点积注意力、多头注意力与交叉注意力

一个位置要看全部历史，就需要一次可微的、权重随输入变化的加权平均。注意力用三个投影把这件事拆开：一个投影决定“我在找什么”，一个决定“我有什么可供匹配”，一个决定“匹配上之后我给出什么”。对输入 <math><mi>X</mi><mo>∈</mo><msup><mi>ℝ</mi><mrow><mi>N</mi><mo>×</mo><mi>d</mi></mrow></msup></math>，单头自注意力先做三次投影：[6]

<math display="block"><mi>Q</mi><mo>=</mo><mi>X</mi><msub><mi>W</mi><mi>Q</mi></msub><mo>,</mo><mspace width="1em"/><mi>K</mi><mo>=</mo><mi>X</mi><msub><mi>W</mi><mi>K</mi></msub><mo>,</mo><mspace width="1em"/><mi>V</mi><mo>=</mo><mi>X</mi><msub><mi>W</mi><mi>V</mi></msub></math>

再用键维度 <math><msub><mi>d</mi><mi>k</mi></msub></math> 归一化点积，加可见性掩码，按行 softmax，最后汇聚值：

<math display="block"><mi>S</mi><mo>=</mo><mfrac><mrow><mi>Q</mi><msup><mi>K</mi><mi>T</mi></msup></mrow><msqrt><msub><mi>d</mi><mi>k</mi></msub></msqrt></mfrac><mo>+</mo><mi>M</mi><mo>,</mo><mspace width="1em"/><msub><mi>A</mi><mrow><mi>i</mi><mi>j</mi></mrow></msub><mo>=</mo><mfrac><mrow><mi mathvariant="normal">exp</mi><mo>(</mo><msub><mi>S</mi><mrow><mi>i</mi><mi>j</mi></mrow></msub><mo>)</mo></mrow><mrow><munder><mo>∑</mo><mi>t</mi></munder><mi mathvariant="normal">exp</mi><mo>(</mo><msub><mi>S</mi><mrow><mi>i</mi><mi>t</mi></mrow></msub><mo>)</mo></mrow></mfrac><mo>,</mo><mspace width="1em"/><mi>Y</mi><mo>=</mo><mi>A</mi><mi>V</mi></math>

掩码在可见位置取零、不可见位置取负无穷，softmax 之后这些位置的权重正好是零。每行至少有一个有效键时，权重非负且和为 1，输出落在值向量的凸组合里。权重本身依赖输入，整个映射因此随输入变化，注意力与固定卷积核的分工正在这里。

#### 缩放项处理的是方差量级

原始 Transformer 用点积的方差解释这个除以根号的操作。[6] 假设查询和键的各分量相互独立、均值为零、方差为一，点积是 <math><msub><mi>d</mi><mi>k</mi></msub></math> 个独立乘积之和，方差随维度线性增长：

<math display="block"><mi mathvariant="normal">Var</mi><mo>(</mo><msup><mi>q</mi><mi>T</mi></msup><mi>k</mi><mo>)</mo><mo>=</mo><msub><mi>d</mi><mi>k</mi></msub><mo>,</mo><mspace width="1em"/><mi mathvariant="normal">Var</mi><mo>(</mo><mfrac><mrow><msup><mi>q</mi><mi>T</mi></msup><mi>k</mi></mrow><msqrt><msub><mi>d</mi><mi>k</mi></msub></msqrt></mfrac><mo>)</mo><mo>=</mo><mn>1</mn></math>

代入具体数字更直观：<math><msub><mi>d</mi><mi>k</mi></msub><mo>=</mo><mn>64</mn></math> 时点积的标准差是 8，比单个分量大一个量级；<math><msub><mi>d</mi><mi>k</mi></msub><mo>=</mo><mn>128</mn></math> 时是 11 左右。分数拉开之后，softmax 会把大部分质量堆到最大的那个分量上，一行 softmax 的分量 <math><msub><mi>a</mi><mi>j</mi></msub></math> 的导数说明了后果：

<math display="block"><mfrac><mrow><mo>∂</mo><msub><mi>a</mi><mi>j</mi></msub></mrow><mrow><mo>∂</mo><msub><mi>s</mi><mi>t</mi></msub></mrow></mfrac><mo>=</mo><msub><mi>a</mi><mi>j</mi></msub><mo>(</mo><msub><mi>δ</mi><mrow><mi>j</mi><mi>t</mi></mrow></msub><mo>−</mo><msub><mi>a</mi><mi>t</mi></msub><mo>)</mo></math>

当某个权重逼近 1、其余逼近 0 时，这些导数一起趋向零，改动多数分数几乎挪不动分配结果，梯度就此变得稀疏而弱。除以 <math><msqrt><msub><mi>d</mi><mi>k</mi></msub></msqrt></math> 把初始量级拉回 1，缓解的是这个饱和倾向。训练之后的查询与键可以高度相关，上述独立假设随之失效，因此缩放只解决初始化的量级问题，最终分布仍由尺度、归一化和训练共同决定。

#### 多头在投影子空间里分工

多头注意力分别计算每头的输出，拼接后再做一次输出投影：

<math display="block"><mi mathvariant="normal">MHA</mi><mo>(</mo><mi>X</mi><mo>)</mo><mo>=</mo><mi mathvariant="normal">Concat</mi><mo>(</mo><msub><mi>Y</mi><mn>1</mn></msub><mo>,</mo><mo>…</mo><mo>,</mo><msub><mi>Y</mi><mi>H</mi></msub><mo>)</mo><msub><mi>W</mi><mi>O</mi></msub></math>

单头对每个查询给出一组位置权重，多个头允许不同子空间采用各自的分配，再各自携带汇聚到的值；输出投影负责把这些通道重新混合。容量来自可学习的差异：若所有头用同一套投影、产生同一份结果，拼起来只是把同一个向量重写一遍，头数增加带不来额外信息。参数总量固定时，增加头数会减小每头维度，同时改变硬件上的计算形状，因此头数存在实际的最优点。

#### 可见性与信息来源各管一件事

自注意力的查询、键、值来自同一条序列；交叉注意力让查询来自目标表示、键与值来自源表示。目标长度 T、源长度 S 时，交叉注意力的权重矩阵形状是 T×S，它学习的是目标位置如何挑选源信息，两侧位置之间不需要一一对应。[6]

因果自注意力再加一层限制：第 i 个位置只能读不晚于它的位置。这条约束针对条件依赖，与“信息来自哪一侧”互不干涉。把两者组合起来，就有了常见配置的差异：BERT 双向编码文本，翻译解码器用因果自注意力处理已生成部分、再用交叉注意力读源端，CLIP 用因果文本编码器配合图文匹配目标。[1, 4, 6] 模型最终做生成还是做匹配，取决于输出接口与目标函数，与注意力本身的结构无关。
