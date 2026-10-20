### 其余经典方案：交换轮次、聚合和代数约束

Bruck 的核心是重排／聚合，使一个阶段搬运多个目的地或来源的数据，再通过后续阶段转发。用于 AllGather 时，已知块集合按对数阶段扩展，能处理非二次幂规模；用于 AlltoAll 时，聚合不同目的地的小块，减少小消息的启动次数，却增加本地整理和部分数据的中继。这解释了它为何常用于短消息，而非“对数轮算法在所有消息长度都更好”。本篇沿用综述的算法分类，不将 MPI Bruck 的每项实现细节直接归给 HCCL NB。[1]（表 2）

Isend–Irecv AlltoAll 为各对端预投递非阻塞收发，再等待匹配完成。它暴露了并行机会，也暴露队列、临时资源和同端口多流竞争。Pairwise Exchange 把交换排成轮次，第 <math><mi>s</mi></math> 轮 rank <math><mi>i</mi></math> 向 <math><mrow><mo>(</mo><mi>i</mi><mo>+</mo><mi>s</mi><mo>)</mo><mo>mod</mo><mi>p</mi></mrow></math> 发送，从 <math><mrow><mo>(</mo><mi>i</mi><mo>−</mo><mi>s</mi><mo>)</mo><mo>mod</mo><mi>p</mi></mrow></math> 接收。每轮一个发送对象和一个接收对象，经过 <math><mrow><mi>p</mi><mo>−</mo><mn>1</mn></mrow></math> 轮覆盖非本地交换。该模运算教学调度本身不要求二次幂规模；综述表中个别 Pairwise 的规模条件属于其引用的具体方案。[1]（表 2）[16]（Pairwise）

Van de Geijn Broadcast 先 Scatter，再 AllGather：root 不必在树的每一层发送完整长向量，各 rank 先得到一片，再合作复制。Rabenseifner 的归约方案同样通过分片减少长向量的反复传输：AllReduce 常由 ReduceScatter 与 AllGather 组成；有根 Reduce 则把已归约片段 Gather 到 root。Vector Halving／Distance Doubling 描述的是向量范围与伙伴距离的演化方向，而非一个新算子。

ReduceScatter 的经典方案还包括递归倍增、逐对交换，以及先二项树归约再 Linear Scatterv。不同方案对非交换归约、用户自定义操作和变长块的处理不同；维护代数顺序可能比减少字节更重要。Scatterv 的 v 指发送块长度可变，不是向量化指令。[1]（表 2、§4.1）

### 分块、多通道与 All-Pairs

Gloo 的 Ring-Chunked 把缓冲区细分，传输一块时归约另一块，缩短“等待完整数据再计算”的空档。分块粒度太小会增加调度与协议开销，太大则难以重叠。NCCL 与 MSCCL 也采用分块和通道，但逻辑 ring、软件 channel、GPU 执行资源以及 NIC 物理端口不是同一个对象。多个 channel 可以提高并发，也可能争用同一出口。[1]（§§4.2.1–4.2.3）

MSCCL 的 All-Pairs 则让不同 rank 承担不同结果片：先从各贡献者收到对应片并归约，再把完成片发给所有 rank。抽象上是两个通信阶段，相比长环减少依赖深度；若各连接共享单一端口，两个阶段并不等于两次单消息成本。输入、输出、scratch 三类缓冲区承载不同生命周期，短消息优势以连接并发、临时空间及任务编排为代价。综述此段文字将一个阶段描述误称为 Ring；这里按它明确对比的 All-Pairs 两阶段机制解释，而不据此声称二者相同。[1]（§4.2.2）

### 分层家族：相同等式，不同拼接方式

MSCCL Hierarchical 使用节点内 ReduceScatter、节点间 ReduceScatter、节点间 AllGather、节点内 AllGather；中间两步合起来是代表组的 AllReduce。ACCL Hybrid 则明确用节点内 Ring、节点间 Halving-Doubling，再节点内 Ring AllGather。Gloo BCube 也先组内分片归约，再对应代表跨组归约，最后组内拼接。它们共同把大量搬移留在较快的局部网络，但不代表选择器、分组规则或执行资源相同。[1]（§§4.2.2–4.2.4）

MSCCL Two-Step AlltoAll 面对的是跨节点大量小块：先按目的节点聚合，再跨节点传输及分发。它减少消息数量，不减少必须交付的有效载荷；额外本地拷贝与整理若超过节约的启动成本，收益会消失。Gloo 的 Pairwise-Exchange 是其文中用于基准的配对交换方案，不能仅凭同名就视为 HCCL 的完整 AlltoAll 实现。具体分层与拓扑约束将在下一章展开。
