### FlashAttention：减少注意力中间量的存储与搬运

#### 瓶颈常常出在矩阵乘之外

对一个注意力头，令查询、键和值分别为 Q、K、V，缩放系数为 s，掩码为 M。标准计算是：

<math display="block"><mi>S</mi><mo>=</mo><mi>s</mi><mi>Q</mi><msup><mi>K</mi><mi>T</mi></msup><mo>+</mo><mi>M</mi><mo>,</mo><mspace width="1em"/><mi>P</mi><mo>=</mo><msub><mi mathvariant="normal">softmax</mi><mi mathvariant="normal">row</mi></msub><mo>(</mo><mi>S</mi><mo>)</mo><mo>,</mo><mspace width="1em"/><mi>O</mi><mo>=</mo><mi>P</mi><mi>V</mi></math>

若将 S 和 P 完整写入高带宽显存（HBM），其元素数随查询长度与键长度的乘积增长。自注意力中两者都为 N 时，这两份中间矩阵是二次规模；Q、K、V 与输出则通常是长度乘头维度的规模。朴素多算子实现不仅要计算分数，还要把分数写出、为 softmax 读入、把概率写出，再为 PV 读入。张量核加快了矩阵乘，这些往返并不会自动消失。

[FlashAttention 原始论文](https://arxiv.org/abs/2205.14135)的关键是 IO 感知：把查询、键和值切块，利用片上共享内存和寄存器，只保留当前块及少量行统计量，不在 HBM 中物化完整的 S、P。它计算的仍是给定可见性下的稠密注意力，没有为了降成本删掉任何键。浮点计算顺序、低精度转换和近似指令会产生数值差异；“精确注意力”描述算法对象；与参考实现逐位一致是另一个要求。

这项技术适用于训练和推理，但收益条件不同。长序列训练需要消除巨大的概率矩阵及其保存成本；预填充也可受益于分块和融合；单个 token 解码没有同样大的查询维度，此时并行度、KV 读取及启动开销更突出。更换注意力算子不会同步解决优化器状态、服务排队或权重加载。

#### 前向算法：在线 softmax 保持的量

一行 softmax 的分母需要整行信息，却不必把整行分数保存下来。扫描过一部分键之后，维护三个状态：已见分数的最大值 m、以 m 为基准的指数和 ℓ，以及以同一基准加权的值向量和 u。u 尚未归一化，不应与最终输出 O 混用。

<math display="block"><mi>ℓ</mi><mo>=</mo><munder><mo>∑</mo><mrow><mi>j</mi><mo>∈</mo><mi>A</mi></mrow></munder><msup><mi>e</mi><mrow><msub><mi>S</mi><mi>j</mi></msub><mo>−</mo><mi>m</mi></mrow></msup><mo>,</mo><mspace width="1em"/><mi>u</mi><mo>=</mo><munder><mo>∑</mo><mrow><mi>j</mi><mo>∈</mo><mi>A</mi></mrow></munder><msup><mi>e</mi><mrow><msub><mi>S</mi><mi>j</mi></msub><mo>−</mo><mi>m</mi></mrow></msup><msub><mi>V</mi><mi>j</mi></msub></math>

新块 B 到来后，选择新的基准，并把旧状态换到这个基准：

<math display="block"><msup><mi>m</mi><mo>′</mo></msup><mo>=</mo><mi mathvariant="normal">max</mi><mo>(</mo><mi>m</mi><mo>,</mo><munder><mi mathvariant="normal">max</mi><mrow><mi>j</mi><mo>∈</mo><mi>B</mi></mrow></munder><msub><mi>S</mi><mi>j</mi></msub><mo>)</mo><mo>,</mo><mspace width="1em"/><mi>α</mi><mo>=</mo><msup><mi>e</mi><mrow><mi>m</mi><mo>−</mo><msup><mi>m</mi><mo>′</mo></msup></mrow></msup></math>

<math display="block"><msup><mi>ℓ</mi><mo>′</mo></msup><mo>=</mo><mi>α</mi><mi>ℓ</mi><mo>+</mo><munder><mo>∑</mo><mrow><mi>j</mi><mo>∈</mo><mi>B</mi></mrow></munder><msup><mi>e</mi><mrow><msub><mi>S</mi><mi>j</mi></msub><mo>−</mo><msup><mi>m</mi><mo>′</mo></msup></mrow></msup></math>

<math display="block"><msup><mi>u</mi><mo>′</mo></msup><mo>=</mo><mi>α</mi><mi>u</mi><mo>+</mo><munder><mo>∑</mo><mrow><mi>j</mi><mo>∈</mo><mi>B</mi></mrow></munder><msup><mi>e</mi><mrow><msub><mi>S</mi><mi>j</mi></msub><mo>−</mo><msup><mi>m</mi><mo>′</mo></msup></mrow></msup><msub><mi>V</mi><mi>j</mi></msub></math>

最后才计算 O＝u／ℓ，并保存 log-sum-exp（LSE）＝m＋ln ℓ。α 同时作用于分母和加权输出，是因为两者都使用同一指数基准。只缩放分母而不缩放 u，会改变不同块的相对权重。对查询方向也分块后，一个执行单元只需维护若干行的状态，而不需要保持全部 N 行。

下面是说明这一递推关系的伪代码，与 CUDA 实现对应但做了简化。`scores` 已包含缩放与掩码；全掩码行需要单独约定输出，不能直接计算负无穷减负无穷。

```python
for query_tile in query_tiles:
    m, denom, numerator = -inf, 0, zero_vector
    for kv_tile in visible_kv_tiles(query_tile):
        scores = scaled_qk(query_tile, kv_tile) + mask
        next_m = maximum(m, row_max(scores))
        alpha = exp(m - next_m)
        p_unnormalized = exp(scores - next_m)
        denom = alpha * denom + row_sum(p_unnormalized)
        numerator = alpha * numerator + p_unnormalized @ kv_tile.values
        m = next_m
    output = numerator / denom
    lse = m + log(denom)
```

`repos/flash-attention/flash_attn/cute/softmax.py` 的 `Softmax`、`SoftmaxSm100` 承担这些统计量的更新；`block_info.py` 和 `mask.py` 则确定可见块与块内边界。因果注意力可跳过完全位于未来的块，对完全可见的块省掉逐元素掩码，只在边界块处理坐标。但“对角线上方／下方”依赖矩阵坐标约定，应直接以查询和键的位置关系判断；图形里的上下方向不可靠。

#### 数值问题：全掩码、指数基准与低精度

全掩码行没有有效键。若 m 和新块最大值都是负无穷，重缩放中的差会变成 NaN。实现需要对这种行作安全基准处理，并在最终分母为零时按接口约定返回输出和 LSE。测试应明确覆盖空序列、局部窗口完全排除一行、变长边界与因果不等长输入；随机的方阵测试不足以暴露这些条件。

GPU 实现常利用以 2 为底的指数，通过缩放中的换底系数计算同一数学量。这样可以使用硬件指数指令及融合乘加，但不能把“使用 exp2”本身视为额外的算法近似；近似来自具体指令和精度。LSE 在前向保存与反向读取时必须约定对数的底，否则概率重构会出错。

`SoftmaxSm100` 的 `rescale_threshold` 路径会在条件满足时继续使用旧基准，并令重缩放因子为 1。旧基准不一定仍是最大值，但在实数运算中，只要分母和 u 始终用同一基准，归一化仍等价；变化主要在指数动态范围、舍入及实现成本。它与“忘掉新最大值、留下不一致统计量”是两回事。调节阈值应检查输出与梯度误差，耗时只是其中一个指标。

#### 反向算法：重算概率，避免保存二次规模张量

训练需要对 Q、K、V 求梯度。令 G 表示损失对 O 的梯度，以下先考虑没有 dropout、掩码不含可训练参数的单头注意力。反向利用前向保存的 LSE 重构当前块的概率，省去再作一次完整的 softmax 归约：

<math display="block"><msub><mi>P</mi><mrow><mi>i</mi><mi>j</mi></mrow></msub><mo>=</mo><msup><mi>e</mi><mrow><msub><mi>S</mi><mrow><mi>i</mi><mi>j</mi></mrow></msub><mo>−</mo><msub><mi mathvariant="normal">LSE</mi><mi>i</mi></msub></mrow></msup></math>

先由 O＝PV 得到 dV＝PᵀG、dP＝GVᵀ；softmax 的反向为逐行去掉概率加权均值：

<math display="block"><msub><mi>D</mi><mi>i</mi></msub><mo>=</mo><munder><mo>∑</mo><mi>j</mi></munder><msub><mi>P</mi><mrow><mi>i</mi><mi>j</mi></mrow></msub><msub><mi mathvariant="normal">dP</mi><mrow><mi>i</mi><mi>j</mi></mrow></msub><mo>=</mo><munder><mo>∑</mo><mi>r</mi></munder><msub><mi>G</mi><mrow><mi>i</mi><mi>r</mi></mrow></msub><msub><mi>O</mi><mrow><mi>i</mi><mi>r</mi></mrow></msub></math>

第二个等号来自展开 dP＝GVᵀ，再把对键的求和重新组合为 O＝PV，不需要错误地假定 G＝dP Vᵀ。因此 D 可以在预处理 kernel 中用已保存的输出和上游梯度作行内点积；它只有每行一个数。

{{include:../excerpts/flash-backward-d.md}}

预处理内核已经把 O 与 dO 的片段读入寄存器；这段无输出残差的分支先转换到 Float32，逐元素相乘并归约，后续代码再归约跨线程的部分和并写出每行统计。它在反向结构中的位置是“预处理 D 与必要统计 → 主循环重构 P 并计算梯度 → 合并／转换输出”；额外保存整张概率矩阵是它要避免的做法。

可以逐步拿掉这些选择来理解设计。若先形成所有 P 与 dP，再求行内和，数学仍可成立，却重新引入与序列长度平方相关的中间量；利用上面的恒等式，D 的这一步只读取已经需要的 O 与 dO。进一步若在每个键块都重新计算相同的 D，又会重复行归约；单独预处理让多个键块读取同一结果，但增加一次 kernel 调度和一份行统计缓冲。若删去 Float32 转换，则改变归约的舍入路径，必须重新做误差验证，不能因公式相同便判定低精度实现等价。

<math display="block"><mi mathvariant="normal">dS</mi><mo>=</mo><mi>P</mi><mo>⊙</mo><mo>(</mo><mi mathvariant="normal">dP</mi><mo>−</mo><mi>D</mi><mo>)</mo><mo>,</mo><mspace width="1em"/><mi mathvariant="normal">dQ</mi><mo>=</mo><mi>s</mi><mi mathvariant="normal">dS</mi><mi>K</mi><mo>,</mo><mspace width="1em"/><mi mathvariant="normal">dK</mi><mo>=</mo><mi>s</mi><msup><mi mathvariant="normal">dS</mi><mi>T</mi></msup><mi>Q</mi></math>

这里 D 按行广播，⊙ 表示逐元素乘；缩放 s 在 Q、K 梯度中都不能漏掉。反向主循环包含重算 QKᵀ、计算 GVᵀ、PᵀG、dSᵀQ 和 dS K，共五类矩阵乘；概率重构和 softmax 梯度是逐元素运算与归约，不应算成额外 GEMM。

这种计算多做了一次分数矩阵乘，却省掉前向保存与反向读取完整 P 的成本。前向保留 Q、K、V、O 以及行统计量，反向在片上重算每个概率块。具体路径还可能保存小规模辅助状态。dropout 路径必须重建相同随机掩码，不能重新抽取；若 LSE 参与损失，反向还多出相应梯度项。`flash_bwd_preprocess.py` 的文件头明确说明可将 D 替换为 D−dLSE，把这项并入主反向公式。

#### 反向的并行归约与确定性

前向按查询块并行容易让一个执行单元完成输出的一部分；反向既要沿查询方向累加 dK、dV，又要沿键方向累加 dQ。常见路径让一个 CTA 负责一个键块，遍历相关查询块，在本 CTA 中积累 dK、dV，却要把 dQ 的不同键块贡献合并。`flash_bwd_preprocess.py`、`flash_bwd_sm90.py`／`flash_bwd_sm100.py`、`flash_bwd_postprocess.py` 分别对应预处理、主计算和累加结果转换。

累加缓冲通常使用 FP32，然后转换到目标精度。原子加或异步块归约可以减少临时缓冲和归约步骤，但浮点加法的到达顺序可能变化。确定性模式需要固定写入顺序或采用分开的部分和与确定归约，增加同步或存储成本；具体方案随 kernel 路径而变。GQA 中多个查询头共享同一个 KV 头，dK、dV 也必须合并这些头的贡献，不能按一头一份直接覆盖。

实际训练若在长序列或稀疏路径出现梯度异常，首先应对齐缩放、mask、LSE 底数、dropout 状态和累加精度，再比较最早出现误差的张量位置。只比较最终 loss，可能掩盖错误来源。部分稀疏 MLA 路径额外保存输出舍入残差，使 D 的计算接近更高精度输出；这是用线性规模附加状态控制误差；保存整个概率矩阵是另一条路线。

