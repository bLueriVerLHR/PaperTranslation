### 简称、全称与改变的对象

| 简称／名称 | 归档文档给出的全称 | 核心变化 |
|---|---|---|
| RHD；旧配置值 H-D_R | Recursive Halving-Doubling | 折半归约、倍增拼接；非二次幂预合并／恢复 |
| NHR | Nonuniform Hierarchical Ring | 用非均衡生成树与切片重排形成对数阶段调度 |
| NB | Nonuniform Bruck | 用二次幂步长和非均匀块数适配任意规模 |
| AHC | Asymmetric Hierarchical Concatenate | 按物理层分组，再按数据边界拼接非对称代表 |
| NHR-HCF | NHR Highest Common Factor | 以 Server 数最大公约数重新组成逻辑拓扑 |
| NHR_V1 | 文档仅标识历史 NHR 版本 | 平方根级步数，不能套用新版 NHR 对数式 |
| Ring／Double-Ring | 环／双环 | 单邻居流动；双环组织多方向／多链路通信 |
| Mesh／Star | 全连接／星型 | 多对端直接并行；根节点集中发送或接收 |
| Pairwise／Pipeline | 逐对交换／流水 | 控制每轮并发对象；重叠不同层通信 |

表中的英文对应来自 [16]（algo_intro、HCCL_ALGO）；没有为 NHR_V1 另造一个缩写展开。后几项不是新增集合算子，而是既有算子的调度方式。

### RHD：二次幂核心与非二次幂附加工作

RHD 对应[第 9 章](#collective-algorithms)的折半—倍增家族，主要解决长环的线性启动成本。等长、二次幂规模下，ReduceScatter／AllGather 的几何级数交换量与环相同，轮数改为对数。5 rank 示例先把一个伙伴的贡献并入代表，再在四个代表上运行两阶段，最后回传完整结果。[16]（RHD）

先合并与最后恢复是额外传输，并非免费把五个编号改成四个。对于独立 ReduceScatter／AllGather，暂时合并的 rank 还意味着非均匀片段与所有者映射；AllReduce 内部可以放宽中间片段顺序，最终仍需恢复完整向量。归档中的不同 Vector／Distance 方向因此对应不同布局约束，不能只记住“RHD 等于 log 步”。

### NHR：并不是普通环缩短几条边

NHR 文档面对两个问题：长环的轮数随 rank 增长，以及 RHD 在非二次幂时的额外合并／恢复。它按每片结果的传播需求构造生成树，多个树共同组织通信；切片编号经过重排，使同一次发送尽可能聚合地址连续的块。文档还描述小消息时减少生成树数量，以减少包数与并发任务。[16]（NHR）

“非均衡”不是允许少算某些 rank 的贡献，而是适配不能平均二分的规模。ReduceScatter 让贡献逐层汇合，AllGather 反向展开结果。大流量尽量集中在物理邻近位置，是利用层级差异的策略；如果逻辑邻近实际仍共用慢端口，就不能仅凭名称推断避免冲突。文档给出的最优理论性能属于其模型，不是对任意拓扑与其他作业并发的全局最优证明。

归档文档用 <math><mrow><mo>⌈</mo><msub><mi>log</mi><mn>2</mn></msub><mi>p</mi><mo>⌉</mo></mrow></math> 表示阶段数，并给出与环同阶的有效交换量。这描述调度的抽象性质；非二次幂的每轮离散块、连续化开销与最慢路径仍需具体实现决定。本篇没有把这些成本合并成未经验证的精确墙钟时间。

### NB：二次幂步长与不均匀块数

NB 的名字明确是 Nonuniform Bruck，不是“Nonblocking”，也不是 NCCL 的协议。其 ReduceScatter 文档规定第 <math><mi>k</mi></math> 阶段向步长 <math><msup><mn>2</mn><mi>k</mi></msup></math> 的目的 rank 发送若干切片，步数为向上取整的二进制对数。每步发送份数为：

<math display="block"><mrow><msub><mi>c</mi><mi>k</mi></msub><mo>=</mo><mo>⌊</mo><mfrac><mrow><mi>p</mi><mo>−</mo><mn>1</mn><mo>+</mo><msup><mn>2</mn><mi>k</mi></msup></mrow><msup><mn>2</mn><mrow><mi>k</mi><mo>+</mo><mn>1</mn></mrow></msup></mfrac><mo>⌋</mo><mo>，</mo><mn>0</mn><mo>≤</mo><mi>k</mi><mo>&lt;</mo><mo>⌈</mo><msub><mi>log</mi><mn>2</mn></msub><mi>p</mi><mo>⌉</mo></mrow></math>

以 5 rank、每份 <math><mfrac><mi>n</mi><mn>5</mn></mfrac></math> 字节为例，步长为 1、2、4，份数是 2、1、1，总计 4 份；因此单 rank 的发送量为 <math><mrow><mn>4</mn><mi>n</mi><mo>/</mo><mn>5</mn></mrow></math>。它不是 RHD 的“先退出一个 rank 再回来”，而是改变各轮的块集合。AllGather 的伙伴距离和块增长方向相反，非二次幂尾部按剩余块数处理。[16]（NB）

<figure>
<a href="assets/figures/27-nb-rounds.svg"><img src="assets/figures/27-nb-rounds.svg" alt="五 rank NB 的步长、份数与量纲"></a>
<figcaption>图 27：五 rank NB 的步长、份数与量纲</figcaption>
</figure>

图给出文档明确的步长和发送份数，不声称展示了完整上游缓冲区排列。要实现完整调度，还必须确定每片所含贡献集合、发送顺序、接收位置以及轮间依赖。只写 `(rank + 2^k) mod p` 无法保证没有重复归约或遗漏贡献。与普通 Bruck 比较时，能对应的是聚合与对数阶段思想，而不是直接照搬某个 MPI AlltoAll 内存布局。

### Mesh、Star 与 Pairwise：并发资源的不同预算

Full Mesh 可以让不同对端通过多路独立 HCCS 链路同时交付分片。文档把它标为常数通信步数，是在足够链路／同步资源下的轮数描述；每 rank 仍要接收来自其他 rank 的有效数据，连接资源随规模增长。若全连接仅是共享一个 NIC 上的逻辑连接，传输成本就不能按每条连接独享峰值带宽计算。[16]（Mesh）

Star 围绕 root 直接辐射：Broadcast 是 root 向外复制，Reduce／Gather 是向 root 汇合。归档 Star 页面有把 Broadcast 写成 root 收集的文字，本篇依据算子语义区分方向，不把该文字当作另一个广播定义。单轮 root 的吞吐以总出口／入口为限制，不能因为每个非根只传一份，就省掉 root 的聚合工作。[16]（Star）

Pairwise 将 AlltoAll(v／VC) 的多对多流量排成轮次。等长块时每轮负载一致；变长块时，第 <math><mi>s</mi></math> 轮的服务时间由该轮最重发送及接收路径决定。在相同单端口模型下，可写成启动项 <math><mrow><mo>(</mo><mi>p</mi><mo>−</mo><mn>1</mn><mo>)</mo><mi>α</mi></mrow></math> 加各轮最大块传输项，而不是总字节平均除以 rank 数。它降低同一端口并发目的数，代价是轮数和暂存需求；网中其他流量仍可拥塞。[16]（Pairwise、HCCL_ALGO）

Pipeline 则是[第 10 章](#hierarchical-communication)的跨层重叠：已收到的块本地分发时，继续跨 Server 转发下一块。它不是把各层串行执行，也不是单独改变算子输出。分组 Full Mesh 在 Atlas A3 的 AlltoAll 系列中控制超节点内外不同并发度；它与一般 Mesh 算法、可手工选择的环境变量选项仍需区分。[16]（algo_intro）
