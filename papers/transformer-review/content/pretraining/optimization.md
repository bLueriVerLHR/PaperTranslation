### 优化、训练稳定性与规模扩展

目标函数定义学习方向，优化过程决定有限预算内怎样接近它。模型深度、序列长度、批大小和数据分布共同改变梯度、状态与每步成本。BERT、ViT、MAE 和 CLIP 的结果都包含具体训练配方；这些配方是方法产生结果的组成条件，与架构名称同样重要。[1–4]

#### 批大小降低哪些随机性

设 B 个独立同分布样本的梯度估计具有相同均值 g 和有限协方差 Σ，则批平均梯度满足：

<math display="block"><mover><mi>g</mi><mo>^</mo></mover><mo>=</mo><mfrac><mn>1</mn><mi>B</mi></mfrac><munderover><mo>∑</mo><mrow><mi>i</mi><mo>=</mo><mn>1</mn></mrow><mi>B</mi></munderover><msub><mi>g</mi><mi>i</mi></msub><mo>,</mo><mspace width="1em"/><mi mathvariant="normal">Cov</mi><mo>(</mo><mover><mi>g</mi><mo>^</mo></mover><mo>)</mo><mo>=</mo><mfrac><mi>Σ</mi><mi>B</mi></mfrac></math>

协方差缩减来自独立交叉项为零。一个序列中的 token 共享上下文，重复文档也相互相关，因此把 token 数或重复次数直接代入 B 会误解这一关系。CLIP 中候选集合还随批大小改变，每个样本损失不再只是独立的固定任务；增大批次同时改变随机性与对比问题本身。

固定训练 token 或样本预算下，更大的批次意味着更少的参数更新。单步估计更平稳与更新次数更少同时发生，吞吐提高也可能来自矩阵形状和并行度；这些因素不能由方差公式单独判定。梯度累积可以形成较大的有效批次，但仍保留微批执行的时间和通信安排。

#### 学习率控制的是局部变化尺度

对梯度在相应邻域中具有 L-Lipschitz 连续性的可微风险 R，下降引理给出普通梯度步的上界：

<math display="block"><mi>R</mi><mo>(</mo><mi>θ</mi><mo>−</mo><mi>η</mi><mi>∇</mi><mi>R</mi><mo>(</mo><mi>θ</mi><mo>)</mo><mo>)</mo><mo>≤</mo><mi>R</mi><mo>(</mo><mi>θ</mi><mo>)</mo><mo>−</mo><mi>η</mi><mo>(</mo><mn>1</mn><mo>−</mo><mfrac><mrow><mi>L</mi><mi>η</mi></mrow><mn>2</mn></mfrac><mo>)</mo><msubsup><mrow><mo>‖</mo><mi>∇</mi><mi>R</mi><mo>(</mo><mi>θ</mi><mo>)</mo><mo>‖</mo></mrow><mn>2</mn><mn>2</mn></msubsup></math>

在梯度步仍处于该邻域、且 0<η<2/L 时，上界中的减小项非负。推导来自对参数位移的一阶展开与二阶余项界：步长太大时，曲率项可以抵消沿负梯度方向的收益。深网络中的有效曲率、随机梯度和参数尺度随训练变化，这个局部结论说明学习率与稳定性之间的联系，非凸训练能否达到全局最优是另一个问题。

BERT 与 ViT 使用学习率 warmup，让初期步长逐渐增加；二者报告的相应训练设置包含 10,000 步 warmup。[1, 2] 这段过程限制早期位移，同时允许表示与优化器统计形成。随后衰减学习率则减小后期更新尺度。具体长度与峰值学习率依赖批次、目标和模型，不能从一个局部曲率界直接算出统一配方。

#### 自适应统计与裁剪处理不同因素

Adam 以梯度的一阶、二阶指数移动统计调节各坐标更新。[18] 令 t 为步数、逐元素平方为 gₜ²，统计从零初始化，两个衰减系数均在 [0,1) 内，其统计与偏差修正为：

<math display="block"><msub><mi>m</mi><mi>t</mi></msub><mo>=</mo><msub><mi>β</mi><mn>1</mn></msub><msub><mi>m</mi><mrow><mi>t</mi><mo>−</mo><mn>1</mn></mrow></msub><mo>+</mo><mo>(</mo><mn>1</mn><mo>−</mo><msub><mi>β</mi><mn>1</mn></msub><mo>)</mo><msub><mi>g</mi><mi>t</mi></msub><mo>,</mo><mspace width="1em"/><msub><mi>v</mi><mi>t</mi></msub><mo>=</mo><msub><mi>β</mi><mn>2</mn></msub><msub><mi>v</mi><mrow><mi>t</mi><mo>−</mo><mn>1</mn></mrow></msub><mo>+</mo><mo>(</mo><mn>1</mn><mo>−</mo><msub><mi>β</mi><mn>2</mn></msub><mo>)</mo><msubsup><mi>g</mi><mi>t</mi><mn>2</mn></msubsup></math>

<math display="block"><msub><mover><mi>m</mi><mo>^</mo></mover><mi>t</mi></msub><mo>=</mo><mfrac><msub><mi>m</mi><mi>t</mi></msub><mrow><mn>1</mn><mo>−</mo><msubsup><mi>β</mi><mn>1</mn><mi>t</mi></msubsup></mrow></mfrac><mo>,</mo><mspace width="1em"/><msub><mover><mi>v</mi><mo>^</mo></mover><mi>t</mi></msub><mo>=</mo><mfrac><msub><mi>v</mi><mi>t</mi></msub><mrow><mn>1</mn><mo>−</mo><msubsup><mi>β</mi><mn>2</mn><mi>t</mi></msubsup></mrow></mfrac></math>

零初始化会使初期统计偏小，例如恒定平均梯度 ḡ 下有 E[mₜ]=(1−β₁ᵗ)ḡ。修正抵消这一初始化因素，随后更新沿 m̂ₜ/(√v̂ₜ+ε) 进行逐坐标缩放。其中 ε 是正的数值稳定项。一阶统计平滑方向，二阶统计提供相对幅度；二阶量是未经中心化的平方矩，与减去均值后的方差相差一个均值平方项。逐坐标缩放与前述普通梯度步的整体学习率不同，因此其稳定性也不能直接由同一个欧氏下降界确定。[18]

全局范数裁剪则在梯度过大时按共同系数缩小向量：g←g·min(1,c/‖g‖₂)，零梯度保持不变。它限制送入后续步骤的梯度范数，与优化器的逐坐标缩放分工不同。ViT 的 ImageNet 设置使用全局范数阈值 1 的裁剪；该取值属于 ViT 的原始配方，换模型规模要重新确定。[2]

#### 扩大规模同时扩大哪些成本

参数容量增加需要足够数据与优化机会才能被利用。ViT 在较小数据设置中受泛化与正则化影响，较大的预训练集合使大模型容量更充分发挥；原文的对照还包含训练时长和具体配方。[2] 重复曝光增加优化次数，但不会等量增加新的原始场景；随机掩码可以生成更多条件组合，也仍依赖相同图像或文档。

长序列扩大注意力交互和激活，较宽模型扩大投影、前馈与状态。BERT 先大量使用较短序列，再用较长序列学习更长位置范围；MAE 则以减少编码器可见图块改变每步工作量。[1, 3] 这两种安排分别改变训练阶段的输入长度与单样本计算图。规模收益、每步成本和有限预算内的更新次数由此相互制约，资源更大同时改变多项量。
