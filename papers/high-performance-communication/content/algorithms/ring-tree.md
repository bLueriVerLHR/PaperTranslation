### 环：把完整向量变成持续流动的分块

Ring AllGather 将 rank 排成逻辑环，每个 rank 首先发送自己的块，随后转发上一轮收到的块。经过 <math><mrow><mi>p</mi><mo>−</mo><mn>1</mn></mrow></math> 轮，所有 rank 都拥有全部块。每轮传输 <math><mfrac><mi>n</mi><mi>p</mi></mfrac></math> 字节，因此单 rank 的发送总量为完整结果的 <math><mfrac><mrow><mi>p</mi><mo>−</mo><mn>1</mn></mrow><mi>p</mi></mfrac></math>，而不是每轮都发送一个完整向量。

<math display="block"><mrow><msub><mi>T</mi><mtext>Ring-AG</mtext></msub><mo>=</mo><mo stretchy="false">(</mo><mi>p</mi><mo>−</mo><mn>1</mn><mo stretchy="false">)</mo><mi>α</mi><mo>+</mo><mfrac><mrow><mi>p</mi><mo>−</mo><mn>1</mn></mrow><mi>p</mi></mfrac><mi>n</mi><mi>β</mi></mrow></math>

Ring AllReduce 再加一个 ReduceScatter 阶段。每个块沿环传播时，收到该块的 rank 把本地同位置输入归约进去；第一阶段结束后，每块都纳入全部 rank 的贡献，但分别归属于不同 rank。第二阶段只复制这些已完成的块，不能再次归约，否则会重复计入贡献。两阶段各需 <math><mrow><mi>p</mi><mo>−</mo><mn>1</mn></mrow></math> 轮。[1]（§4.1.1）

<figure>
<a href="assets/figures/19-ring-stages.svg"><img src="assets/figures/19-ring-stages.svg" alt="四 rank 环的两个阶段及每轮分块"></a>
<figcaption>图 19：四 rank 环的两个阶段及每轮分块</figcaption>
</figure>

图中的块标签表示数据归属，不指定某个库的精确块编号。内部 ReduceScatter 的归属可以置换；只要随后 AllGather 恢复完整向量及正确位置，AllReduce 的外部语义仍成立。独立调用 ReduceScatter 时则必须遵守 rank 到输出块的映射。

<math display="block"><mrow><msub><mi>T</mi><mtext>Ring-AR</mtext></msub><mo>=</mo><mn>2</mn><mo stretchy="false">(</mo><mi>p</mi><mo>−</mo><mn>1</mn><mo stretchy="false">)</mo><mi>α</mi><mo>+</mo><mn>2</mn><mfrac><mrow><mi>p</mi><mo>−</mo><mn>1</mn></mrow><mi>p</mi></mfrac><mi>n</mi><mi>β</mi><mo>+</mo><mfrac><mrow><mi>p</mi><mo>−</mo><mn>1</mn></mrow><mi>p</mi></mfrac><mi>n</mi><mi>γ</mi></mrow></math>

发送量渐近接近每 rank 两个完整向量，启动项却随规模线性增长。因此“带宽效率好”与“规模大时延迟低”是不同评价。环的单邻居通信也不保证物理网络无拥塞：多条逻辑环可能共享同一条上行链路。

### 二项树：用更多传播者减少轮数

Broadcast 的直接根发送把全部出口工作集中在 root；二项树让收到数据的 rank 成为新的传播者。以 8 个 rank、root 0 为例，一种等价调度先执行 0→4，再执行 0→2、4→6，最后执行 0→1、2→3、4→5、6→7。轮末持有完整消息的 rank 数依次为 2、4、8。逻辑边表示传输任务，不意味着机器必须按树形布线。

<figure>
<a href="assets/figures/20-binomial.svg"><img src="assets/figures/20-binomial.svg" alt="八 rank 二项树广播及反向归约"></a>
<figcaption>图 20：八 rank 二项树广播及反向归约</figcaption>
</figure>

在 <math><mrow><mi>p</mi><mo>=</mo><msup><mn>2</mn><mi>k</mi></msup></mrow></math>、每轮发送完整 <math><mi>n</mi></math> 字节的简化模型中，关键路径经过 <math><mi>k</mi></math> 轮，所以广播成本为 <math><mrow><mi>k</mi><mo stretchy="false">(</mo><mi>α</mi><mo>+</mo><mi>n</mi><mi>β</mi><mo stretchy="false">)</mo></mrow></math>。Reduce 沿反向边汇合，每轮增加相应归约成本，得到 <math><mrow><mi>k</mi><mo stretchy="false">(</mo><mi>α</mi><mo>+</mo><mi>n</mi><mi>β</mi><mo>+</mo><mi>n</mi><mi>γ</mi><mo stretchy="false">)</mo></mrow></math>。[1]（§4.1.2）

短消息受启动项支配，减少轮数很有吸引力；长向量却会在关键路径上反复传输完整消息。分段流水可以改善带宽利用，但引入段启动、管线填充与排空，不再等于上述未分段成本式。非交换归约还要维护操作数顺序，不能任意反转或重排树边。

### 双二叉树：分担转发负荷

NCCL 2.4 的双树设计把数据分成两部分，在两棵尽量互补的二叉树上执行归约与分发。某 rank 在一棵树中承担内部转发，在另一棵树中尽量作为叶子，从而分散单树内部节点的额外发送负荷，同时保留对数级树深。[7]（Double binary trees）

互补关系并不是“每个 rank 永远恰有两个父节点和两个子节点”。根、叶以及奇数规模构造都有例外。它也不是物理网络增加一倍：两棵逻辑树仍受同一设备端口、路径与内存带宽约束。厂商报告的规模化收益说明该设计在其测试条件下改善了延迟，不能外推到任意拓扑或把 NCCL 2.4 的介绍当成所有后来版本的算法清单。
