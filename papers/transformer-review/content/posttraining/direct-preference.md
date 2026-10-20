#### DPO：从最优策略到直接偏好损失

奖励建模加策略优化把偏好拟合与模型更新分成两个阶段。DPO 利用受 KL 约束目标的解析关系，把奖励差重新参数化为策略的对数概率比，直接在固定偏好对上学习。[21] 它省掉的是训练中的显式奖励模型和在线策略采样循环，数据收集与参考模型计算照旧。

##### 受约束目标为什么具有指数加权解

固定输入 x，在参考策略支持内考虑回答分布，设 β>0、奖励有限且配分函数 Z(x) 有限。定义：

<math display="block"><msup><mi>π</mi><mo>*</mo></msup><mo>(</mo><mi>y</mi><mo>|</mo><mi>x</mi><mo>)</mo><mo>=</mo><mfrac><mn>1</mn><mrow><mi>Z</mi><mo>(</mo><mi>x</mi><mo>)</mo></mrow></mfrac><msub><mi>π</mi><mi mathvariant="normal">ref</mi></msub><mo>(</mo><mi>y</mi><mo>|</mo><mi>x</mi><mo>)</mo><mi mathvariant="normal">exp</mi><mo>(</mo><mfrac><mrow><mi>r</mi><mo>(</mo><mi>x</mi><mo>,</mo><mi>y</mi><mo>)</mo></mrow><mi>β</mi></mfrac><mo>)</mo></math>

将其对数代入前节的奖励减 KL 目标，得到：

<math display="block"><msub><mi>J</mi><mi>x</mi></msub><mo>(</mo><mi>π</mi><mo>)</mo><mo>=</mo><mi>β</mi><mi mathvariant="normal">log</mi><mi>Z</mi><mo>(</mo><mi>x</mi><mo>)</mo><mo>−</mo><mi>β</mi><mi mathvariant="normal">KL</mi><mo>(</mo><mi>π</mi><mo>(</mo><mo>·</mo><mo>|</mo><mi>x</mi><mo>)</mo><mo>‖</mo><msup><mi>π</mi><mo>*</mo></msup><mo>(</mo><mo>·</mo><mo>|</mo><mi>x</mi><mo>)</mo><mo>)</mo></math>

第一项与待优化的 π 无关，第二项在两分布相等时为零，其他情形非正，因此 π* 是该分布空间中的最优解。参考概率保留原分布的基准，指数项按奖励重加权；β 相对奖励尺度越大，重加权越弱。这个证明针对给定奖励和分布空间，参数化网络未必能表达其精确解。

##### 配分函数为何从成对比较中消失

反解奖励可得 r(x,y)=βlog[π*(y|x)/πref(y|x)]+βlog Z(x)。同一输入下两回答的奖励相减时，最后一项消失。代入 Bradley–Terry 偏好模型，再用 πθ 表示待学习策略，定义：

<math display="block"><msub><mi>δ</mi><mi>θ</mi></msub><mo>=</mo><mi>β</mi><mo>[</mo><mi mathvariant="normal">log</mi><mfrac><mrow><msub><mi>π</mi><mi>θ</mi></msub><mo>(</mo><msub><mi>y</mi><mo>+</mo></msub><mo>|</mo><mi>x</mi><mo>)</mo></mrow><mrow><msub><mi>π</mi><mi mathvariant="normal">ref</mi></msub><mo>(</mo><msub><mi>y</mi><mo>+</mo></msub><mo>|</mo><mi>x</mi><mo>)</mo></mrow></mfrac><mo>−</mo><mi mathvariant="normal">log</mi><mfrac><mrow><msub><mi>π</mi><mi>θ</mi></msub><mo>(</mo><msub><mi>y</mi><mo>−</mo></msub><mo>|</mo><mi>x</mi><mo>)</mo></mrow><mrow><msub><mi>π</mi><mi mathvariant="normal">ref</mi></msub><mo>(</mo><msub><mi>y</mi><mo>−</mo></msub><mo>|</mo><mi>x</mi><mo>)</mo></mrow></mfrac><mo>]</mo><mo>,</mo><mspace width="1em"/><msub><mi>ℒ</mi><mi mathvariant="normal">DPO</mi></msub><mo>=</mo><mo>−</mo><msub><mi>𝔼</mi><mi>D</mi></msub><mi mathvariant="normal">log</mi><mi>σ</mi><mo>(</mo><msub><mi>δ</mi><mi>θ</mi></msub><mo>)</mo></math>

训练只需计算优选与非优选回答在策略和参考模型中的序列对数概率，不需要枚举全部回答估计 Z。原始序列概率是各 token 条件概率的乘积，对数后为求和；改成按长度平均会改变这一目标及其推导关系。

##### 更新强调尚未满足的相对偏好

单对样本损失的边际导数为：

<math display="block"><mfrac><mrow><mo>∂</mo><mi>ℓ</mi></mrow><mrow><mo>∂</mo><msub><mi>δ</mi><mi>θ</mi></msub></mrow></mfrac><mo>=</mo><mi>σ</mi><mo>(</mo><msub><mi>δ</mi><mi>θ</mi></msub><mo>)</mo><mo>−</mo><mn>1</mn><mo>=</mo><mo>−</mo><mi>σ</mi><mo>(</mo><mo>−</mo><msub><mi>δ</mi><mi>θ</mi></msub><mo>)</mo></math>

校正后的相对排序错误时，梯度权重较大；已经具有很大正间隔时，权重减小。SFT 只拟合示范回答，DPO 则比较两条完整回答，并以参考策略校正初始概率关系。它约束相对变化，不保证每次共享参数更新都单独提高优选回答的绝对概率。

DPO 的联系依赖偏好模型、参考支持和数据覆盖。固定数据方便优化，也可能缺少新策略会产生的错误或优质回答；标注冲突和分布偏移还会影响可拟合关系。在线 RLHF 与离线 DPO 的区别在采样反馈链、计算状态和拟合对象，在有限数据上把偏好损失压到最小，与在所有真实任务上表现最佳是两回事。
