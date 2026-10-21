### 输入组织与计算复杂度

问一个 Transformer 块的时间花在哪，答案随形状变化。把所有耗时归到注意力的二次项上，会漏掉隐藏维度宽时的投影与前馈；只看参数量，又看不到长输入带来的交互与状态增长。原始 Transformer 的复杂度讨论和 ViT 对理论计算量与设备速度的对照，分别对应“数学工作量”与“实际执行”这两个层次。[2, 6]

#### 二次交互什么时候成为主项

设序列长度 N、隐藏维度 d，多头的查询／键总维度与值总维度都取 d，前馈中间维度 <math><msub><mi>d</mi><mi mathvariant="normal">ff</mi></msub></math>。忽略偏置、归一化、激活与 softmax 的逐元素开销，矩阵乘的乘加对数为：

<math display="block"><msub><mi>C</mi><mi mathvariant="normal">projection</mi></msub><mo>=</mo><mn>4</mn><mi>N</mi><msup><mi>d</mi><mn>2</mn></msup><mo>,</mo><mspace width="1em"/><msub><mi>C</mi><mi mathvariant="normal">pair</mi></msub><mo>=</mo><mn>2</mn><msup><mi>N</mi><mn>2</mn></msup><mi>d</mi><mo>,</mo><mspace width="1em"/><msub><mi>C</mi><mi mathvariant="normal">FFN</mi></msub><mo>=</mo><mn>2</mn><mi>N</mi><mi>d</mi><msub><mi>d</mi><mi mathvariant="normal">ff</mi></msub></math>

第一项是 Q、K、V 与多头输出四次投影，第二项是 QKᵀ 与 AV，第三项是前馈的扩展与收缩。换成一个具体配置：N=1024、d=512、d_ff=2048，三项分别约为 1.07×10⁹、1.07×10⁹、2.15×10⁹ 次乘加，总计 4.3×10⁹。此时成对交互只占四分之一，前馈一项独占一半。成对项与其他两项的比值是：

<math display="block"><mfrac><msub><mi>C</mi><mi mathvariant="normal">pair</mi></msub><mrow><msub><mi>C</mi><mi mathvariant="normal">projection</mi></msub><mo>+</mo><msub><mi>C</mi><mi mathvariant="normal">FFN</mi></msub></mrow></mfrac><mo>=</mo><mfrac><mi>N</mi><mrow><mn>2</mn><mi>d</mi><mo>+</mo><msub><mi>d</mi><mi mathvariant="normal">ff</mi></msub></mrow></mfrac></math>

代入上例即 <math><mn>1024</mn><mo>/</mo><mo stretchy="false">(</mo><mn>1024</mn><mo>+</mo><mn>2048</mn><mo stretchy="false">)</mo><mo>=</mo><mn>1</mn><mo>/</mo><mn>3</mn></math>。阈值就写在式子里：序列长度超过 <math><mn>2</mn><mi>d</mi><mo>+</mo><msub><mi>d</mi><mi mathvariant="normal">ff</mi></msub></math> 之后，成对交互开始占多数。取 d=512、d_ff=4d=2048，这个门槛是 3072；短于它的序列上，投影和前馈才是大头。这里是既定形状下的稠密算术比较，真实耗时还要看访存、并行度、融合和硬件原语。

若把乘加按两次浮点运算计，所有数字翻倍，比值不变。

#### 输入粒度决定成本涨在哪一项

ViT 中把图块边长减半，图像尺寸不变时序列长度变成四倍。代回上面三项：投影与前馈随 N 线性增长，涨到约四倍；成对交互随 N² 增长，涨到约十六倍。细化输入颗粒度因此要额外付出交互成本，把更多资源压到位置之间的交互上。[2]

MAE 走的是反方向。编码器之前先扔掉被遮挡的图块，编码器只看剩下的部分。设保留比例 ρ，序列长度按 ρ 缩放，投影与前馈约按 ρ 缩放，成对交互约按 ρ² 缩放；分类 token、固定开销和后面的解码器另计。[3] 这条关系解释了非对称编码器—解码器结构为什么能把主要表示学习集中到可见部分，但它只覆盖编码器这一段，全流程的加速比要看解码器占多少。

#### 算术与存储可以分开优化

直接保存各头注意力权重，中间状态包含与头数、序列长度平方成比例的元素；算术量则由成对项决定。以 N=8192、16 个头、2 字节为例，一份完整权重矩阵是 16×8192²×2 字节，约 2 GiB，需要落到显存里；FlashAttention 通过分块与在线归一化避免把这张矩阵整体写回主存；它改的是中间量的存储与搬运，稠密注意力的算术量没有变化，结果仍是精确注意力。这部分实现细节在框架章的 FlashAttention 小节展开。

局部窗口、序列压缩、线性累计状态和精确注意力内核，因此在资源图上各占一个位置：前三类改变的是可见连接或表示，后一类重排同样的计算。讨论效率时把三件事分开说清：计算对象是什么、状态有多大、信息怎么被访问；某种设计在缓解哪项压力、又留下哪些工作，也就可以判断了。
