## 8. 全体集合算子与语义组合 {#all-collectives}

“All”意味着输出分布涉及全体参与者，但不意味着所有人总得到相同内容。AllGather 和 AllReduce 的结果在各 rank 相同；ReduceScatter 和 AlltoAll 则让各 rank 得到不同的数据。判断算子，首先应明确数据的身份是否保留、是否归约，以及输出如何分布。[1][4]

### 8.1 AllGather：每人都得到按 rank 拼接的全部块 {#operator-allgather}

rank i 输入长度为 b 的 xᵢ，每个 rank 都接收 `[x₀ | … | xₚ₋₁]`，长度 pb。它可以在语义上理解为 Gather 后 Broadcast，但实现通常不需要一个 root 持有并转发全部数据。

<figure><a href="assets/figures/15-allgather.svg"><img src="assets/figures/15-allgather.svg" alt="三个 rank 输入 A、B、C，操作后每个 rank 接收相同的 A、B、C 拼接结果。"></a><figcaption>图 15：AllGather 保留各输入块身份，不做数值归约。</figcaption></figure>

例如，模型参数分别分片存于各 GPU，而一个计算阶段需要完整参数，就可以通过 AllGather 恢复全量视图。每个 rank 的接收容量从 b 增至 pb，通信成功并不等于显存足够；多个计算层提前汇集参数还会拉长全量参数的驻留时间。NCCL 的 `ncclAllGather` 参数名是 sendcount：传入 b 时，接收缓冲仍须容纳 pb 个元素。[5]

### 8.2 ReduceScatter：归约后，各自拥有不同结果块 {#operator-reducescatter}

每个 rank 输入一个长度 pb 的向量，分为 p 块。先对各输入相同位置归约，得到一个长度 pb 的结果 y；rank i 只接收 y 的第 i 块，长度 b。输入已经按块排列，不意味着先把原始块发给对应 rank 就结束；每个结果块都必须包含**全部 rank 的贡献**。

<figure><a href="assets/figures/16-reduce-scatter.svg"><img src="assets/figures/16-reduce-scatter.svg" alt="三个 rank 分别输入1、10、100；2、20、200；3、30、300；求和后 rank 0 得6，rank1得60，rank2得600。"></a><figcaption>图 16：ReduceScatter。不同输出块都是全体输入的归约，而不是各 rank 原输入的局部切片。</figcaption></figure>

这个三元素算例中，输入是 `(1,10,100)`、`(2,20,200)`、`(3,30,300)`，全归约结果是 `(6,60,600)`。ReduceScatter 分别把 6、60、600 留在 rank 0、1、2。它适合下游本来就按块更新状态的任务：没有必要先让每个 rank 保存全部结果，再丢弃其中大部分。

`ncclReduceScatter` 的 recvcount=b，发送缓冲要有 pb 个元素；MPI 的相关接口还区分等块与可变块计数。不能把所有库中名字相近的 ReduceScatter 都理解成相同的变长接口。[5]

### 8.3 AllReduce：每个人得到完整归约结果 {#operator-allreduce}

每个 rank 输入长度 n 的向量；所有 rank 接收长度 n 的相同归约结果。沿用上例，每人都得到 `(6,60,600)`。

<figure><a href="assets/figures/17-allreduce.svg"><img src="assets/figures/17-allreduce.svg" alt="三个 rank 的三元素向量按位置求和，操作后每人接收6、60、600。"></a><figcaption>图 17：AllReduce。结果容量不随 rank 数增长，但生成结果需要全体贡献。</figcaption></figure>

它有两种重要的语义分解：[4]

<math xmlns="http://www.w3.org/1998/Math/MathML" display="block"><mtable><mtr><mtd><mtext>AllReduce</mtext></mtd><mtd><mo>≡</mo></mtd><mtd><mtext>Reduce → Broadcast</mtext></mtd></mtr><mtr><mtd><mtext>AllReduce</mtext></mtd><mtd><mo>≡</mo></mtd><mtd><mtext>ReduceScatter → AllGather</mtext></mtd></mtr></mtable></math>

这里的等价要求归约操作、参与者和分块顺序一致；浮点数仍存在上一章讨论的重排差异。第二种分解把结果所有权分散到各 rank，让不同 rank 同时完成不同结果块，因此特别适合环形和分层算法。语义分解不要求 API 真调用两次，也不保证分开的两次调用与融合实现有相同启动成本。

求和 AllReduce 本身不一定等于训练所需的平均梯度。若各 rank 批量相等并计算局部平均梯度，结果再除以 p 才得到全局平均；若批量不同，必须按样本数加权。某些接口支持平均或预缩放语义，但缩放应以实际使用的 API 为准，而不是由 AllReduce 这个名字推断。[5]

### 8.4 AlltoAll：把按目的排列的数据转成按来源排列 {#operator-alltoall}

设 rank i 有 p 块，块 xᵢⱼ 要送给 rank j。操作后 rank j 接收 `[x₀ⱼ | x₁ⱼ | … | xₚ₋₁,ⱼ]`。如果把每个 rank 的发送块画成矩阵一行，通信后的布局就是把“源—目的”矩阵按列交给各目的 rank。它是分布式数据重排，不是对矩阵数值执行线性代数转置内核。[4]

<figure><a href="assets/figures/18-alltoall.svg"><img src="assets/figures/18-alltoall.svg" alt="发送矩阵三行分别为00、01、02；10、11、12；20、21、22；接收端rank0得00、10、20，rank1得01、11、21，rank2得02、12、22。"></a><figcaption>图 18：AlltoAll。块标签的第一位是源 rank，第二位是目的 rank；各 rank 的对角块是本地份额。</figcaption></figure>

每个 rank 的总输入和输出都为 pb，但线上实际远程发送只有其中的 `(p−1)b` 个元素，本地块无需穿越网卡。与 AllGather 相比，它并不让每个目的地持有同一套块；与 ReduceScatter 相比，它不把来自多个源的数值合并。专家并行中的 token 路由和某些张量布局转换正需要这种保留身份的重排。

AlltoAllv 允许源 i 发给目的 j 的块有不同长度 cᵢⱼ。接收端必须知道对应来源的计数与偏移，并与发送端达成一致。长度交换、打包、位移计算和输出重建都可能产生额外成本。若某个目的地收到的总字节数特别大，平均计数就掩盖了真正的尾部瓶颈。NCCL 2.28.3 文档中的 `ncclAlltoAll` 是等长 count 接口，不因名字带有 All 就自动提供 AlltoAllv。[5]

### 8.5 屏障与点对点的区别

Barrier 只建立参与者同步条件，不生成新的张量结果。集体算子完成也不应被当作任意其他 stream 或 CPU 任务的全局屏障：数据依赖还取决于执行上下文。Send／Receive 则针对指定对端搬运数据，可以组成 Scatter 或全交换的调度，但还要处理匹配、顺序、并发和错误。算子表达的是整体规则，点对点表达的是构造这条规则的局部动作。

Scan 是前缀归约：rank i 只得到从 rank 0 到 i 的贡献合并，因此各 rank 结果一般不同；它既不是全体相同结果的 AllReduce，也不是把完整结果等分的 ReduceScatter。xCCL 综述在支持表中列出 Scan，但未展开算法，也没有由此证明所列库均支持它。[1]（表 1）

| 算子 | 每 rank 输入 | 每 rank 规定输出 | 数值合并 | 最终各 rank 相同？ |
|---|---|---|---|---|
| AllGather | b | pb | 否 | 是 |
| ReduceScatter | pb | b | 是 | 否，结果分块不同 |
| AllReduce | n | n | 是 | 是 |
| AlltoAll | pb | pb | 否 | 通常不同 |

这里把 n 与 b 分开，是为了避免常见的成本混淆：AllReduce 的 n 是每个 rank 的完整向量长度，AllGather 的 b 是每个 rank 的独立输入块长度。两者不能仅凭“相同 count 数字”就判断通信量相同。
