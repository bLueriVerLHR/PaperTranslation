### 序列表示、位置与输入组织

Transformer 拿到的输入是一个矩阵。设序列长度 N、隐藏维度 d，矩阵 <math><mi>X</mi><mo>∈</mo><msup><mi>ℝ</mi><mrow><mi>N</mi><mo>×</mo><mi>d</mi></mrow></msup></math> 的每一行是一个处理单位。文本 token、图像块、音频片段、时间观测都能占这个位置，划分规则决定了哪些细节先被合进同一个向量、哪些关系留给后面的层去学。[2, 6, 9]

#### 从离散单位到可学习表示

文本一侧的起点是词表。嵌入矩阵的每一行对应一个 token，取表示就是选行，再叠加位置和片段信息。BERT 用 WordPiece 切分，把 token 嵌入、位置嵌入、片段嵌入三者相加，两个文本片段用分隔 token 拼在同一条序列里，双向注意力可以直接在片段之间建立联系。[1] 同一 token 在不同位置得到不同表示，靠的是后续层的上下文交互——词表向量只是起点，不携带“这个词是什么意思”的固定定义。

视觉一侧的起点是连续像素。对高、宽分别为 <math><mi>H</mi></math>、<math><mi>W</mi></math>、通道数为 <math><mi>C</mi></math> 的图像，取边长 <math><mi>P</mi></math> 的不重叠图块，空间尺寸可整除时序列长度和图块向量为：[2]

<math display="block"><mi>N</mi><mo>=</mo><mfrac><mrow><mi>H</mi><mi>W</mi></mrow><msup><mi>P</mi><mn>2</mn></msup></mfrac><mo>,</mo><mspace width="1em"/><msub><mi>x</mi><mi>i</mi></msub><mo>∈</mo><msup><mi>ℝ</mi><mrow><msup><mi>P</mi><mn>2</mn></msup><mi>C</mi></mrow></msup><mo>,</mo><mspace width="1em"/><msub><mi>z</mi><mi>i</mi></msub><mo>=</mo><msub><mi>x</mi><mi>i</mi></msub><mi>E</mi><mo>+</mo><msub><mi>p</mi><mi>i</mi></msub></math>

代入 224×224 的输入和 16×16 的图块：序列长度是 <math><mn>224</mn><mo>×</mo><mn>224</mn><mo>/</mo><msup><mn>16</mn><mn>2</mn></msup><mo>=</mo><mn>196</mn></math>，每个图块向量 16×16×3=768 维，投影矩阵 E 的形状是 768×d。E 在图块之间共享，所以每个图块都用同一套局部特征提取规则，区分它们出现位置的是位置向量 pᵢ。把 P 减半，序列长度涨到四倍，后面每一层的交互成本随之变化；图块边界由网格决定，与对象边界无关，横跨两个图块的物体会被切开，需要在上下文里重新组合。

#### 置换等变性：顺序为什么会丢

不含位置信息、掩码或任何位置相关偏置的自注意力，对输入行的重排是等变的。设 <math><mi>Π</mi></math> 为置换矩阵，F 表示一层内容自注意力。线性投影共享，于是 <math><mi>Q</mi><mo>′</mo><mo>=</mo><mi>Π</mi><mi>Q</mi></math>，键与值同理，分数矩阵的行列被同时重排：

<math display="block"><mi>S</mi><mo>′</mo><mo>=</mo><mi>Π</mi><mi>S</mi><msup><mi>Π</mi><mi>T</mi></msup><mo>,</mo><mspace width="1em"/><mi mathvariant="normal">softmax</mi><mo>(</mo><mi>S</mi><mo>′</mo><mo>)</mo><mo>=</mo><mi>Π</mi><mi mathvariant="normal">softmax</mi><mo>(</mo><mi>S</mi><mo>)</mo><msup><mi>Π</mi><mi>T</mi></msup></math>

右式成立的理由是 softmax 按行归一化：重排列只改变求和项的顺序，重排行只改变哪条查询落在哪一行。再代入 <math><msup><mi>Π</mi><mi>T</mi></msup><mi>Π</mi><mo>=</mo><mi>I</mi></math>，得到

<math display="block"><mi>F</mi><mo>(</mo><mi>Π</mi><mi>X</mi><mo>)</mo><mo>=</mo><mi>Π</mi><mi>F</mi><mo>(</mo><mi>X</mi><mo>)</mo></math>

输入内容换个顺序，输出跟着换个顺序，网络无法仅凭数组下标获得新的顺序关系。逐位置共享的前馈层和归一化同样保持这一性质。在上述条件之外再加上对称池化（取平均、取最大这类聚合），连整体的置换不变性都出现了：打乱行得到的表示和原来完全一样。于是语言中的先后、图像中的空间布局必须显式进入计算。[6, 9]

加性位置嵌入的做法是改变这个对称性：只重排 token 时，<math><mi>Π</mi><mi>X</mi><mo>+</mo><mi>P</mi></math> 与 <math><mi>Π</mi><mo>(</mo><mi>X</mi><mo>+</mo><mi>P</mi><mo>)</mo></math> 一般不相等。相对位置方法换个入口，把位置差做进查询与键的匹配，表达的是“相距多远”。两者施加的结构不同：前者要求模型自己从绝对坐标里推关系，后者把关系直接写进打分。原始 ViT 用可学习的绝对位置向量，换分辨率时按二维图块布局对这些参数做插值。[2] 位置表示让模型有条件辨认布局，局部窗口与层级结构这类先验仍由后面的层负责。
