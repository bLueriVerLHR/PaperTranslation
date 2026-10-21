#### 像素重建：非对称计算与条件均值

MAE 把遮挡安排在编码器之前：随机移除图块，较大的编码器只处理可见子集，再将带位置的掩码 token 补入较轻的解码器。解码器恢复完整位置集合并预测被遮挡图块。[3] 与 BERT 用替换 token 维持完整输入长度相比，MAE 同时改变了学习任务和较重模块的计算规模。

图像相邻区域通常具有空间冗余，较少遮挡时可能通过局部纹理延续完成预测。MAE 作者据此提高遮挡比例，使任务更依赖分散的可见区域及整体关系，并在其设置下发现 75% 遮挡有效。[3] 比例进一步增大，又会减少用于区分多个可能图像的证据。这是可见信息与预测难度之间的取舍，最佳比例由实验确定。

设被遮挡图块集合为 M，每个目标图块有 q 个像素分量，像素均方误差为：

<math display="block"><msub><mi>ℒ</mi><mi mathvariant="normal">MAE</mi></msub><mo>=</mo><mfrac><mn>1</mn><mrow><mo>|</mo><mi>M</mi><mo>|</mo><mi>q</mi></mrow></mfrac><munder><mo>∑</mo><mrow><mi>i</mi><mo>∈</mo><mi>M</mi></mrow></munder><msubsup><mrow><mo>‖</mo><msub><mover><mi>x</mi><mo>^</mo></mover><mi>i</mi></msub><mo>−</mo><msub><mi>x</mi><mi>i</mi></msub><mo>‖</mo></mrow><mn>2</mn><mn>2</mn></msubsup></math>

只监督缺失图块使直接误差集中于恢复未知内容。可见图块作为条件仍参与梯度传播，但不需要在该损失中重复承担复制自身像素的任务。原文把这个选择带来的识别收益交给实验结果判断，推广到其他去噪目标要另行验证。[3]

##### 均方误差为何可能产生平均化预测

固定可见条件 c，把缺失像素向量记为随机变量 X，且假定条件二阶矩有限。令 μ(c)=E[X|c]，模型输出为 a。展开平方并利用 E[X−μ(c)|c]=0，可得：

<math display="block"><mi>𝔼</mi><mo stretchy="false">[</mo><msubsup><mrow><mo>‖</mo><mi>X</mi><mo>−</mo><mi>a</mi><mo>‖</mo></mrow><mn>2</mn><mn>2</mn></msubsup><mo>|</mo><mi>c</mi><mo stretchy="false">]</mo><mo>=</mo><mi>𝔼</mi><mo>[</mo><msubsup><mrow><mo>‖</mo><mi>X</mi><mo>−</mo><mi>μ</mi><mo stretchy="false">(</mo><mi>c</mi><mo stretchy="false">)</mo><mo>‖</mo></mrow><mn>2</mn><mn>2</mn></msubsup><mo>|</mo><mi>c</mi><mo>]</mo><mo>+</mo><msubsup><mrow><mo>‖</mo><mi>a</mi><mo>−</mo><mi>μ</mi><mo stretchy="false">(</mo><mi>c</mi><mo stretchy="false">)</mo><mo>‖</mo></mrow><mn>2</mn><mn>2</mn></msubsup></math>

第一项是给定可见内容后仍剩下的不确定性，第二项在 a=μ(c) 时最小。因而，无容量限制的平方误差预测器选择条件均值；若同一可见区域允许多个不同补全，最优均值可以位于这些补全之间，并不一定对应一幅自然图像。这个数学性质说明重建误差、视觉逼真度与语义识别各自衡量不同的量；有限网络的实际结果还受模型和数据限制。

##### 目标归一化改变被奖励的像素差异

MAE 还比较按图块均值和标准差归一化的目标。[3] 省略数值稳定项，并假定图块方差非零时，目标为 z=(x−μ)/σ。若整块像素变为 ax+b，其中 a>0，则均值变为 aμ+b、标准差变为 aσ，归一化目标保持不变。这使目标降低对图块共同亮度与正尺度变化的敏感性，而保留图块内部的相对结构。

这种不变性属于重建目标，不自动扩展为整个编码器的光照不变性：输入仍可包含原始亮度，位置与上下文也继续影响表示。预训练后移除重建解码器，用编码器完成识别；其价值需要在这一迁移接口上评估，而不由像素损失的最小化单独确定。
