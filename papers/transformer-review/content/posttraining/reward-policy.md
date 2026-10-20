#### 奖励模型与受约束的策略优化

InstructGPT 先训练示范策略，再让标注者比较模型候选，用奖励模型预测偏好，最后通过 PPO 优化策略。[20] 这条链把难以直接求导的人类判断转为可用于学习的信号，同时引入奖励估计、策略采样和更新稳定性三个问题。

##### 相对偏好怎样变成奖励

对同一输入 x，优选回答为 y₊、较不受偏好的回答为 y₋。Bradley–Terry 模型用奖励差表示优选概率：[21]

<math display="block"><mi>P</mi><mo>(</mo><msub><mi>y</mi><mo>+</mo></msub><mo>≻</mo><msub><mi>y</mi><mo>−</mo></msub><mo>|</mo><mi>x</mi><mo>)</mo><mo>=</mo><mi>σ</mi><mo>(</mo><msub><mi>r</mi><mi>φ</mi></msub><mo>(</mo><mi>x</mi><mo>,</mo><msub><mi>y</mi><mo>+</mo></msub><mo>)</mo><mo>−</mo><msub><mi>r</mi><mi>φ</mi></msub><mo>(</mo><mi>x</mi><mo>,</mo><msub><mi>y</mi><mo>−</mo></msub><mo>)</mo><mo>)</mo></math>

其中 σ 是 logistic 函数。最大化比较数据的似然，使观测到的优选回答得到较高相对奖励。对某个输入，把全部奖励都加上相同常数不会改变比较概率；相对标签因此不能唯一确定绝对奖励基准。这个奖励只是偏好的代理，事实正确率与安全属性另有各自的度量。

固定奖励 r 与参考策略 πref，策略目标可写为：

<math display="block"><mi>J</mi><mo>(</mo><mi>π</mi><mo>)</mo><mo>=</mo><msub><mi>𝔼</mi><mrow><mi>x</mi><mo>∼</mo><mi>D</mi></mrow></msub><mo>[</mo><msub><mi>𝔼</mi><mrow><mi>y</mi><mo>∼</mo><mi>π</mi><mo>(</mo><mo>·</mo><mo>|</mo><mi>x</mi><mo>)</mo></mrow></msub><mi>r</mi><mo>(</mo><mi>x</mi><mo>,</mo><mi>y</mi><mo>)</mo><mo>−</mo><mi>β</mi><mi mathvariant="normal">KL</mi><mo>(</mo><mi>π</mi><mo>(</mo><mo>·</mo><mo>|</mo><mi>x</mi><mo>)</mo><mo>‖</mo><msub><mi>π</mi><mi mathvariant="normal">ref</mi></msub><mo>(</mo><mo>·</mo><mo>|</mo><mi>x</mi><mo>)</mo><mo>)</mo><mo>]</mo></math>

β>0 时，KL 项惩罚相对参考分布的偏离。它限制只为代理奖励而大幅改变原行为的激励，却不保证代理奖励本身正确。InstructGPT 还混入预训练似然更新，以缓和其报告的部分原任务退化；这是额外的能力保持目标，与 KL 约束作用不同。[20]

##### 为什么策略采样需要专门的梯度估计

对固定 x 与不依赖 θ 的奖励，若允许交换求和与微分，有：

<math display="block"><mi>∇</mi><msub><mi>𝔼</mi><mrow><mi>y</mi><mo>∼</mo><msub><mi>π</mi><mi>θ</mi></msub></mrow></msub><mi>r</mi><mo>(</mo><mi>y</mi><mo>)</mo><mo>=</mo><msub><mi>𝔼</mi><mrow><mi>y</mi><mo>∼</mo><msub><mi>π</mi><mi>θ</mi></msub></mrow></msub><mo>[</mo><mi>r</mi><mo>(</mo><mi>y</mi><mo>)</mo><mi>∇</mi><mi mathvariant="normal">log</mi><msub><mi>π</mi><mi>θ</mi></msub><mo>(</mo><mi>y</mi><mo>)</mo><mo>]</mo></math>

这来自 ∇π=π∇log π，避免对离散采样动作直接求导。减去只依赖条件的基线不改变期望梯度，因为概率总和的导数为零，却可以改变估计方差。多步任务进一步使用状态价值与优势估计，把动作相对其条件下常见结果的收益用于更新。[24] 此式只解释固定奖励部分，KL 等依赖策略的项还需按相应定义处理。

PPO 在旧策略采集的样本上优化替代目标，概率比 ρₜ=πθ(aₜ|sₜ)/πold(aₜ|sₜ) 修正当前与采样策略的动作概率差异。其裁剪目标为：[24]

<math display="block"><msub><mi>L</mi><mi mathvariant="normal">clip</mi></msub><mo>=</mo><mover><mi>𝔼</mi><mo>^</mo></mover><mo>[</mo><mi mathvariant="normal">min</mi><mo>(</mo><msub><mi>ρ</mi><mi>t</mi></msub><msub><mover><mi>A</mi><mo>^</mo></mover><mi>t</mi></msub><mo>,</mo><mi mathvariant="normal">clip</mi><mo>(</mo><msub><mi>ρ</mi><mi>t</mi></msub><mo>,</mo><mn>1</mn><mo>−</mo><mi>ε</mi><mo>,</mo><mn>1</mn><mo>+</mo><mi>ε</mi><mo>)</mo><msub><mover><mi>A</mi><mo>^</mo></mover><mi>t</mi></msub><mo>)</mo><mo>]</mo></math>

正优势样本的概率提高到比值上界后，这一项不再提供继续提高的收益；负优势样本的概率降低到下界后，也不再奖励继续降低。方向相反的恶化仍计入目标。裁剪作用在替代目标的激励上；实际概率比不因此被锁进区间，全局 KL 也没有硬保证。

πold 随采样批次更新，用于控制局部策略步；πref 通常固定为对齐前的参考模型，用于约束整体偏离。两种比较的时间尺度不同，即使都涉及概率比或 KL，也不承担同一职责。
