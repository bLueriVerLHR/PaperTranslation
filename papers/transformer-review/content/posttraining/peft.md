### 参数高效适配与持续使用

全量微调为每个任务更新与基座同等规模的参数。任务数增加时，梯度、优化器状态和任务模型副本分别扩大训练与维护成本。参数高效适配以较小的可变部分编码任务差异，保留共享基座；其节约首先出现在更新状态与任务增量上，整个模型的规模保持不变。[7, 19]

#### LoRA 约束的是增量

设原权重 W₀ 的形状为 dₒ×dᵢ，LoRA 用秩 r 的分解表示增量，并冻结 W₀：[19]

<math display="block"><mi>h</mi><mo>=</mo><msub><mi>W</mi><mn>0</mn></msub><mi>x</mi><mo>+</mo><mi>s</mi><mi>B</mi><mi>A</mi><mi>x</mi><mo>,</mo><mspace width="1em"/><mi>A</mi><mo>∈</mo><msup><mi>ℝ</mi><mrow><mi>r</mi><mo>×</mo><msub><mi>d</mi><mi>i</mi></msub></mrow></msup><mo>,</mo><mspace width="1em"/><mi>B</mi><mo>∈</mo><msup><mi>ℝ</mi><mrow><msub><mi>d</mi><mi>o</mi></msub><mo>×</mo><mi>r</mi></mrow></msup></math>

原版缩放 s=α/r。增量 BA 的秩至多为 r，但 W₀+sBA 仍可以是满秩矩阵；适配只把增量限在低秩，原模型的秩不变。可训练参数由 dₒdᵢ 减为 r(dₒ+dᵢ)，只有 r 足够小时才有明显节约。论文以适配增量的低内在秩作为假设，并在所研究任务中给出证据；其他任务的最优更新是否低秩要另行检验。[19]

若某个理想单矩阵更新具有奇异值 σ₁≥σ₂≥…，其最佳秩 r 近似的平方 Frobenius 误差为尾部平方和：

<math display="block"><munder><mi mathvariant="normal">min</mi><mrow><mi mathvariant="normal">rank</mi><mo>(</mo><mi>Δ</mi><mo>)</mo><mo>≤</mo><mi>r</mi></mrow></munder><msubsup><mrow><mo>‖</mo><msup><mi>Δ</mi><mo>*</mo></msup><mo>−</mo><mi>Δ</mi><mo>‖</mo></mrow><mi>F</mi><mn>2</mn></msubsup><mo>=</mo><munder><mo>∑</mo><mrow><mi>j</mi><mo>&gt;</mo><mi>r</mi></mrow></munder><msubsup><mi>σ</mi><mi>j</mi><mn>2</mn></msubsup></math>

截断奇异值分解的前 r 项可以达到这个误差。其下界也来自子空间容量：任意秩 r 近似的列空间至多 r 维，令 P 为该空间的正交投影，则近似无法恢复 (I−P)Δ*。平方误差至少为 Δ* 的总平方能量减去该子空间捕获的能量。将 P 放到左奇异向量基中，其对角权重各在零与一之间、总和至多为 r；对递减的平方奇异值加权，最多捕获前 r 项的能量，余下尾部因此不可消除。

若重要变化集中在少数方向，低秩限制可以保留主要增量；若尾部仍很大，限制就会排除一部分变化。网络损失衡量的是输出差异，该关系讲的是表示约束，尾部误差与任务性能之间还隔着别的环节。

#### 初始化决定第一步梯度流向

原版 LoRA 随机初始化 A、将 B 初始化为零，使初始增量为零。[19] 对一层、一个样本，记输出梯度为 g，则：

<math display="block"><mfrac><mrow><mo>∂</mo><mi>ℓ</mi></mrow><mrow><mo>∂</mo><mi>B</mi></mrow></mfrac><mo>=</mo><mi>s</mi><mi>g</mi><msup><mrow><mo>(</mo><mi>A</mi><mi>x</mi><mo>)</mo></mrow><mi>T</mi></msup><mo>,</mo><mspace width="1em"/><mfrac><mrow><mo>∂</mo><mi>ℓ</mi></mrow><mrow><mo>∂</mo><mi>A</mi></mrow></mfrac><mo>=</mo><mi>s</mi><msup><mi>B</mi><mi>T</mi></msup><mi>g</mi><msup><mi>x</mi><mi>T</mi></msup></math>

B 为零时，A 的初始梯度为零，B 则可以利用随机 A 产生的特征开始更新；随后 A 也获得梯度。若两者都为零，两个数据损失梯度都为零，这条乘积分支无法由普通梯度开始学习。零增量与非零可学习路径因此需要同时安排。

#### 训练状态、合并与多任务服务

冻结权重不需要自己的参数梯度与优化器矩，但前向仍要执行基座计算，梯度也可能经过冻结层传向更早的可训练模块。激活、基座权重和生成 KV 仍存在。少量可训练参数主要缩小训练更新状态和每任务检查点，总显存不会按同一比例下降。

线性增量可以合并为 W=W₀+sBA，让单任务部署保留原矩阵乘结构。[19] 多任务并发若各自使用不同增量，共享一份已合并权重就不再足够；未合并的动态分支保留任务选择，却引入增量计算和批内路由。论文也指出这一合并与多任务批处理之间的取舍。

其他参数高效路线改变不同对象：适配器在表示路径中增加小模块，连续提示或前缀向计算提供可训练条件，LoRA 改变既有权重的增量。[19] 模块参数很少仍可能处于串行关键路径；可训练前缀还增加被注意力访问的状态。训练参数数目、前向形状和任务共享方式共同决定成本。
