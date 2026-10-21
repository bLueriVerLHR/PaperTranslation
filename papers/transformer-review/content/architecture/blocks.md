### 残差连接、归一化与前馈网络

注意力沿位置轴搬运信息，前馈网络沿特征轴变换每个位置，残差和归一化把这两类子层拼成可训练的深栈。这两种子层放在哪里，输出尺度与梯度经过的算子都会不同：原始 Transformer 先加残差再归一化，ViT 把 LayerNorm 放到子层之前。[2, 6]

#### 残差提供恒等通路，归一化改写特征尺度

对一个位置的向量 <math><mi>x</mi><mo>∈</mo><msup><mi>ℝ</mi><mi>d</mi></msup></math>，LayerNorm 沿特征维取均值和方差：

<math display="block"><mi>μ</mi><mo>=</mo><mfrac><mn>1</mn><mi>d</mi></mfrac><munder><mo>∑</mo><mi>r</mi></munder><msub><mi>x</mi><mi>r</mi></msub><mo>,</mo><mspace width="1em"/><msup><mi>σ</mi><mn>2</mn></msup><mo>=</mo><mfrac><mn>1</mn><mi>d</mi></mfrac><munder><mo>∑</mo><mi>r</mi></munder><msup><mrow><mo stretchy="false">(</mo><msub><mi>x</mi><mi>r</mi></msub><mo>−</mo><mi>μ</mi><mo stretchy="false">)</mo></mrow><mn>2</mn></msup></math>

<math display="block"><mi mathvariant="normal">LN</mi><mo stretchy="false">(</mo><mi>x</mi><mo stretchy="false">)</mo><mo>=</mo><mi>γ</mi><mo>⊙</mo><mfrac><mrow><mi>x</mi><mo>−</mo><mi>μ</mi><mi mathvariant="normal">1</mi></mrow><msqrt><mrow><msup><mi>σ</mi><mn>2</mn></msup><mo>+</mo><mi>ε</mi></mrow></msqrt></mfrac><mo>+</mo><mi>β</mi></math>

统计量取自单个位置自身的特征，一个批里不同序列的同一特征不会相互混入，这一点让它在变长序列和小批量下都能用。可学习的 γ 与 β 把归一化后的特征重新缩放、平移，模型因此不必被迫接受单位方差。残差则把旧表示原样留下，让子层只学一个增量：子层输出为零时，未归一化的那条通路直接把输入送到下一层。

用 F 表示注意力或前馈子层，两种常见放置的映射是：

<math display="block"><msub><mi>y</mi><mi mathvariant="normal">pre</mi></msub><mo>=</mo><mi>x</mi><mo>+</mo><mi>F</mi><mo stretchy="false">(</mo><mi mathvariant="normal">LN</mi><mo stretchy="false">(</mo><mi>x</mi><mo stretchy="false">)</mo><mo stretchy="false">)</mo><mo>,</mo><mspace width="1em"/><msub><mi>y</mi><mi mathvariant="normal">post</mi></msub><mo>=</mo><mi mathvariant="normal">LN</mi><mo stretchy="false">(</mo><mi>x</mi><mo>+</mo><mi>F</mi><mo stretchy="false">(</mo><mi>x</mi><mo stretchy="false">)</mo><mo stretchy="false">)</mo></math>

在可微点上用链式法则，两者的雅可比因子顺序不同：

<math display="block"><msub><mi>J</mi><mi mathvariant="normal">pre</mi></msub><mo>=</mo><mi>I</mi><mo>+</mo><msub><mi>J</mi><mi>F</mi></msub><msub><mi>J</mi><mi mathvariant="normal">LN</mi></msub><mo>,</mo><mspace width="1em"/><msub><mi>J</mi><mi mathvariant="normal">post</mi></msub><mo>=</mo><msub><mi>J</mi><mi mathvariant="normal">LN</mi></msub><mo stretchy="false">(</mo><mi>I</mi><mo>+</mo><msub><mi>J</mi><mi>F</mi></msub><mo stretchy="false">)</mo></math>

各式中的雅可比在对应中间变量处求值。Pre-LN 的恒等支路不必先穿过归一化的雅可比；Post-LN 的两条支路相加之后一起过归一化。这个差别可以直接从因式分解看出来，而训练稳不稳还取决于深度、初始化、学习率和其他组件，[9] 把雅可比顺序当成稳定性的充分解释会走得太远。

归一化还有一个容易忽略的性质：对任意标量 c，<math><mi mathvariant="normal">LN</mi><mo stretchy="false">(</mo><mi>x</mi><mo>+</mo><mi>c</mi><mi mathvariant="normal">1</mi><mo stretchy="false">)</mo><mo>=</mo><mi mathvariant="normal">LN</mi><mo stretchy="false">(</mo><mi>x</mi><mo stretchy="false">)</mo></math>。因为均值同样增加了 c，中心化之后完全抵消，该方向上的导数恒为零。落到模型上，这意味着沿各位置共同偏移的方向（例如“所有 token 都更倾向于某类语义”）在归一化处被抹掉，要找回来只能靠后面的可学习仿射或其他子层。残差与归一化的相对位置，决定了哪些信息先被合并、哪些方向先被消去。

#### 前馈层在特征维上扩展再压缩

逐位置前馈网络写成：

<math display="block"><mi mathvariant="normal">FFN</mi><mo stretchy="false">(</mo><mi>x</mi><mo stretchy="false">)</mo><mo>=</mo><mi>φ</mi><mo stretchy="false">(</mo><mi>x</mi><msub><mi>W</mi><mn>1</mn></msub><mo>+</mo><msub><mi>b</mi><mn>1</mn></msub><mo stretchy="false">)</mo><msub><mi>W</mi><mn>2</mn></msub><mo>+</mo><msub><mi>b</mi><mn>2</mn></msub></math>

第一层把 d 维输入打到通常更宽的中间空间，非线性在这里做特征选择，第二层再收回残差需要的维度。去掉非线性，两次线性变换可以合并成一个仿射映射，中间宽度就失去意义。按原始 Transformer 的配置 d=512、d_ff=2048 算参数：W₁ 是 512×2048、W₂ 是 2048×512，两层各约 105 万参数，合计是这个块里最大的权重项；注意力的四个投影 Q、K、V、O 合计 4×512²≈105 万，与前馈的两层相当，但在长序列下注意力的算术量会反超。

原始 Transformer 用 ReLU，ViT 用 GELU。[2, 6] 以 ReLU 为例，每个中间单元先判断一个线性组合是否为正，再决定输出多少；最终结果由被激活的那些特征重新组合。注意力把别处的信息搬到当前位置，前馈层对搬来的信息重新编码。它不扩大位置之间的可见范围，只提升每个位置处理信息的能力，代价是计算与激活占用随序列长度线性增长。
