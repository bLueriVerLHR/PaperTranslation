### DSA：用轻量索引器挑出要读的历史

MLA 压缩了每个历史位置的宽度，位置个数却没有减少。一个长度为 N 的序列仍有大约 N²/2 个可见位置对，主注意力要逐个打分、逐个汇聚，长上下文下这项开销重新成为主导。DeepSeek 稀疏注意力（DeepSeek Sparse Attention，DSA）在 MLA 之上加了一条轻量通道：先用低代价的索引器扫一遍历史，挑出重要的若干位置，再让主注意力只在这些位置之间做完整计算。DeepSeek-V3.2 用它把每查询的主分支读取量固定在 2,048 个 KV token。[34]（§2.1）

NSA 也做同一件事，区别在选择粒度与依据：NSA 复用压缩分支已经算出的块分数、按块选择；DSA 用一套独立的索引头逐 token 打分，并把选中的位置对应到 MLA 的公共潜在状态上，于是一套入选集合可以被全部主注意力头共用。

#### 索引分数与主注意力权重各司其职

设当前查询位置 t，可见历史位置 s≤t。索引器有 Hᴵ 个头，每头索引查询 qᴵₜ,ⱼ 为 dᴵ 维，历史位置共用一份索引键 kᴵₛ，当前输入另外给出每头一个标量权重 wᴵₜ,ⱼ。索引分数是各头点积的加权和，激活函数取 ReLU：[34]（Eq.1）

<math display="block"><msub><mi>I</mi><mrow><mi>t</mi><mi>s</mi></mrow></msub><mo>=</mo><munderover><mo>∑</mo><mrow><mi>j</mi><mo>=</mo><mn>1</mn></mrow><msup><mi>H</mi><mi>I</mi></msup></munderover><msubsup><mi>w</mi><mrow><mi>t</mi><mo>,</mo><mi>j</mi></mrow><mi>I</mi></msubsup><mi mathvariant="normal">ReLU</mi><mo>(</mo><msup><mrow><mo>(</mo><msubsup><mi>q</mi><mrow><mi>t</mi><mo>,</mo><mi>j</mi></mrow><mi>I</mi></msubsup><mo>)</mo></mrow><mi>T</mi></msup><msubsup><mi>k</mi><mi>s</mi><mi>I</mi></msubsup><mo>)</mo></math>

多个索引头先合成一个位置分数，再取 Top-k，得到的是一套共享的位置集合：

<math display="block"><msub><mi>S</mi><mi>t</mi></msub><mo>=</mo><mi mathvariant="normal">TopK</mi><mo>(</mo><mo>{</mo><msub><mi>I</mi><mrow><mi>t</mi><mi>s</mi></mrow></msub><mo>:</mo><mi>s</mi><mo>≤</mo><mi>t</mi><mo>}</mo><mo>,</mo><mi>k</mi><mo>)</mo></math>

历史不足 k 时取已有的全部合法位置。这套集合由该位置的全部主注意力头共用，因为它对齐的是 MLA 的公共潜在 KV 条目：一个被选中的历史位置贡献的是一份潜在状态，各主头各自拿它算自己的分数。索引器头数少、维度小，还可以用 FP8 实现，扫描一遍全历史的代价远低于完整主注意力。它依然要看过历史，扫描量随当前历史长度增长。

选出位置之后，主分支重新用自己的 MLA 查询、潜在状态和位置项打分，走一次 softmax 并汇聚：

<math display="block"><msub><mi>o</mi><mrow><mi>t</mi><mo>,</mo><mi>h</mi></mrow></msub><mo>=</mo><munder><mo>∑</mo><mrow><mi>s</mi><mo>∈</mo><msub><mi>S</mi><mi>t</mi></msub></mrow></munder><mfrac><mrow><mi mathvariant="normal">exp</mi><mo>(</mo><msubsup><mi>ℓ</mi><mrow><mi>t</mi><mi>s</mi></mrow><mi>h</mi></msubsup><mo>)</mo></mrow><mrow><munder><mo>∑</mo><mrow><mi>u</mi><mo>∈</mo><msub><mi>S</mi><mi>t</mi></msub></mrow></munder><mi mathvariant="normal">exp</mi><mo>(</mo><msubsup><mi>ℓ</mi><mrow><mi>t</mi><mi>u</mi></mrow><mi>h</mi></msubsup><mo>)</mo></mrow></mfrac><msubsup><mi>v</mi><mi>s</mi><mi>h</mi></msubsup></math>

分母只统计入选位置，所以入选者的权重会因为没选中的位置被剔除而重新分配。ReLU 索引分数只承当路由代理的职责，最终权重仍由 ℓ 决定。

#### 选定集合上的 softmax 是精确的

稀疏注意力在给定集合上做的仍是完整 softmax，问题在于这个集合是否装住了该装的信息。做一个局部估算：固定同一组主分数和值，设稠密分布在未选位置上的概率总和为 ε<1，各值向量的范数不超过 V。稠密输出可以拆成入选部分与未选部分两个条件均值：

<math display="block"><msub><mi>o</mi><mi mathvariant="normal">dense</mi></msub><mo>=</mo><mo>(</mo><mn>1</mn><mo>−</mo><mi>ε</mi><mo>)</mo><msub><mi>o</mi><mi>S</mi></msub><mo>+</mo><mi>ε</mi><msub><mi>o</mi><mover><mi>S</mi><mo>¯</mo></mover></msub><mo>,</mo><mspace width="1em"/><mo>‖</mo><msub><mi>o</mi><mi mathvariant="normal">dense</mi></msub><mo>−</mo><msub><mi>o</mi><mi>S</mi></msub><mo>‖</mo><mo>≤</mo><mn>2</mn><mi>ε</mi><mi>V</mi></math>

`o_S` 是入选集合上重新归一化的输出，ε=0 时两个输出相同，此时未选部分的均值无需定义。这个式子说明只统计选对了多少位置并不够用：遗漏的概率质量和值的尺度都会进入误差。它只覆盖固定参数下的单个注意力层，后续层、非线性以及训练本身都在范围之外。

#### 硬 Top-k 靠辅助损失学习

Top-k 的索引选取不可微，“哪些位置值得读”这件事没法学。DeepSeek-V3.2 分两段训练：[34]（§2.1.1）稠密预热阶段冻结主模型，只练新增的索引器；主注意力各头的概率按位置求和，再沿序列做 L1 归一化，得到教师分布 pₜ，索引器用 KL 散度对齐它：

<math display="block"><msub><mi>ℒ</mi><mi>I</mi></msub><mo>=</mo><munder><mo>∑</mo><mi>t</mi></munder><msub><mi>D</mi><mi mathvariant="normal">KL</mi></msub><mo>(</mo><mi mathvariant="normal">stopgrad</mi><mo>(</mo><msub><mi>p</mi><mi>t</mi></msub><mo>)</mo><mo>‖</mo><mi mathvariant="normal">softmax</mi><mo>(</mo><msub><mi>I</mi><mrow><mi>t</mi><mo>,</mo><mo>:</mo></mrow></msub><mo>)</mo><mo>)</mo></math>

教师端取自动梯度，索引器输入也从计算图上断开，于是这项损失只更新索引器的投影，主模型由语言建模损失单独负责。稀疏阶段打开 Top-k，主模型学着适应新的连接模式，索引器转为在入选集合上对齐归一化后的主注意力分布。两段的规模在报告中写得很清楚：预热 1,000 步，每步 16 条 128K 序列，合计 2.1B token；稀疏训练 15,000 步，每步 480 条 128K 序列，合计 943.7B token。

2,048 这个数字值得单独说明：它是主分支每个查询的读取预算。把它当成上下文长度上限或者缓存容量都会算错：索引键与可供未来查询选择的潜在状态仍全部留在显存里，不同的查询会从不同的位置拼出自己的集合。DSA 因此与滑动窗口、与按重要性永久驱逐 KV 的做法都不同。

#### 索引项的二次规模留在那里

设序列长度为 N，主分支每查询的读取预算为 k，每条主连接的有效工作量记作 D。忽略投影、选择、逐元素运算与常数因子，预填充阶段的主要结构是：

<math display="block"><msub><mi>C</mi><mi mathvariant="normal">DSA</mi></msub><mo>=</mo><mi>O</mi><mo>(</mo><msup><mi>N</mi><mn>2</mn></msup><msup><mi>H</mi><mi>I</mi></msup><msup><mi>d</mi><mi>I</mi></msup><mo>)</mo><mo>+</mo><mi>O</mi><mo>(</mo><mi>N</mi><mi>k</mi><mi>D</mi><mo>)</mo></math>

第一项留在原处，只是系数小；被降下来的是第二项。对一个新查询，索引扫描的长度随当前历史增长，主分支的访问量由 k 封顶。排序、非连续 gather、索引缓存与内核启动都是新增开销，短上下文下这笔开销可能超过省下的主计算，报告因此对短序列预填充专门实现了带掩码的 MHA 视图。[34]（§2.3）

这些结论带着具体的训练条件：DSA 是在 DeepSeek-V3.1-Terminus 检查点上继续训练得到的，评测也落在相应设置内，把它当作任意 MLA 模型套用 Top-k 即可无损的依据并不成立。报告里的 H800 服务成本换算自真实部署，与另一篇论文的单内核时间不能拼成一栏排名。MSA 用了另一套共享边界：选择在 GQA 组内共享，组与组之间可以不同。
