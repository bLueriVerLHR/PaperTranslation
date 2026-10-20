### 量化：压缩表示与控制输出误差

量化把连续数值塞进有限网格。以仿射量化为例，整数 <math><mi>q</mi><mo>=</mo><mi mathvariant="normal">round</mi><mo>(</mo><mi>w</mi><mo>/</mo><mi>s</mi><mo>)</mo><mo>+</mo><mi>z</mi></math>，随后被截断到允许区间；解码时算回 s(q−z)。步长 s 决定分辨率，零点 z 决定网格落在哪。取一个具体例子：权重范围 [−0.5, 0.5]、4 比特、z=0，可用整数是 −8 到 7，于是 s=0.5/8=0.0625，未截断时最近舍入的单元素误差不超过 s/2=0.03125。缩小范围能让大部分数值变细，同时把离群值截断得更狠——截断误差没有 s/2 这个界，“位数相同”因此说明不了误差相同。

权重、激活和 KV 量化分别作用于固定参数、当前中间量和随请求增长的状态。原始权重从 16 位降到 4 位，理想情况下数据量减到四分之一，尺度、零点、分组信息、未量化层和执行缓冲照旧占地方。W4A16 也不保证矩阵乘在所有硬件上跑四位整数：运行时往往先解包、反量化，再做高精度乘法。GPTQ 原论文明确区分“减少读取成本”与“拿到低位乘法硬件加速”这两件事。[26]

#### 只缩小权重误差还不够

对线性层 Y=WX，令量化误差 E=Ŵ−W，输出误差就是 EX。按 Frobenius 范数展开，其平方等于：

<math display="block"><msubsup><mrow><mo>‖</mo><mi>E</mi><mi>X</mi><mo>‖</mo></mrow><mi>F</mi><mn>2</mn></msubsup><mo>=</mo><mi mathvariant="normal">tr</mi><mo>(</mo><mi>E</mi><mi>X</mi><msup><mi>X</mi><mi>T</mi></msup><msup><mi>E</mi><mi>T</mi></msup><mo>)</mo></math>

同样大的权重偏差，落在高频激活方向上和落在低频方向上，造成的输出偏差不一样；不同输入维度的误差还可能互相抵消。最近舍入只做逐元素的最小网格距离，完全没看这些方向和相关性。GPTQ 于是改用少量校准输入建立逐层重建目标，最小化 WX 与 ŴX 的差，把“权重接近”换成“输出接近”。[26]

#### 二阶补偿的局部推导

看单个输出行，把它写成列向量 w，尚未固定的坐标贡献的二次误差是 δᵀHδ/2，其中 H=2XXᵀ；为了可逆和数值稳定，可以加一个正的对角阻尼。现在把第 q 个权重摁到网格值上，偏移 <math><mi>e</mi><mo>=</mo><mi mathvariant="normal">quant</mi><mo>(</mo><msub><mi>w</mi><mi>q</mi></msub><mo>)</mo><mo>−</mo><msub><mi>w</mi><mi>q</mi></msub></math>，其余坐标允许连续调整。约束写成 <math><msubsup><mi>u</mi><mi>q</mi><mi>T</mi></msubsup><mi>δ</mi><mo>=</mo><mi>e</mi></math>，u_q 是第 q 个单位向量。Lagrange 一阶条件给出 Hδ=λu_q，代回约束解出：

<math display="block"><mi>δ</mi><mo>=</mo><mfrac><mi>e</mi><msub><mrow><mo>(</mo><msup><mi>H</mi><mrow><mo>−</mo><mn>1</mn></mrow></msup><mo>)</mo></mrow><mrow><mi>q</mi><mi>q</mi></mrow></msub></mfrac><msup><mi>H</mi><mrow><mo>−</mo><mn>1</mn></mrow></msup><msub><mi>u</mi><mi>q</mi></msub><mo>,</mo><mspace width="1em"/><msub><mi>Δ</mi><mi mathvariant="normal">min</mi></msub><mo>=</mo><mfrac><msup><mi>e</mi><mn>2</mn></msup><mrow><mn>2</mn><msub><mrow><mo>(</mo><msup><mi>H</mi><mrow><mo>−</mo><mn>1</mn></mrow></msup><mo>)</mo></mrow><mrow><mi>q</mi><mi>q</mi></mrow></msub></mrow></mfrac></math>

一次舍入的误差因此可以沿输入相关方向分摊到还没量化的权重上，这就是原论文所用逆 Hessian 补偿的来源。要注意它解的是当前这个连续补偿子问题，后面的坐标仍得落到离散网格上；它给不出全网络量化的全局最优，也保证不了下游质量。

原始 OBQ 逐行挑选贪心顺序，GPTQ 改成所有行共用一套列顺序。逐行重建共享同一份 X，剩余坐标的 Hessian 也一样，逆矩阵信息就能复用。块内逐列处理，跨块的更新延后合并成矩阵操作，低计算密度的更新因此跑得动；Cholesky 重写与阻尼应对反复消元积累的数值误差。这三处改动各自解决重复工作、访存效率和稳定性，用一句“二阶量化更准确”概括不掉。算法细节见原论文 §§3–4。[26]

校准数据限定了哪些激活方向被重视。短文本上重建风险低，长上下文、专业词汇和严格工具参数上的误差完全可能更大；逐层的局部补偿也管不住层间误差传播。困惑度、任务质量、峰值状态因此在三条轴上分别评价。低位方案的收益来自张量表示与匹配内核的组合，输入分布和实际执行路径都会改变结论。[7, 26]
