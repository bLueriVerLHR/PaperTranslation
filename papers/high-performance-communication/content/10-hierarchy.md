## 10. 跨节点、跨网络与分层通信 {#hierarchical-communication}

逻辑上相邻的两个 rank，可能由同一芯片互连、PCIe、机架交换机或跨区域链路连接。算法轮数相同，成本仍会不同，因为不同层的链路带宽、共享程度和故障域不同。xCCL 综述的拓扑讨论针对物理网络；环和树算法则是叠加在其上的逻辑调度。[1]（§3）

{{include:hierarchy/topologies.md}}

### 局部归约与跨节点分片

设有 <math><mi>h</mi></math> 台服务器，每台 <math><mi>g</mi></math> 个 rank，完整向量大小为 <math><mi>n</mi></math>。分层 AllReduce 先在每台服务器内执行 ReduceScatter，使各本地 rank 持有 <math><mfrac><mi>n</mi><mi>g</mi></mfrac></math> 的局部归约片；再让同本地编号的 rank 组成 <math><mi>g</mi></math> 个跨服务器通信组，各组完成对应片的 AllReduce；最后每台服务器内 AllGather。[1]（§§4.2.2–4.2.4）[16]（分级通信原理）

<figure>
<a href="assets/figures/23-hierarchy.svg"><img src="assets/figures/23-hierarchy.svg" alt="两台服务器各四 rank 的分层 AllReduce"></a>
<figcaption>图 23：两台服务器各四 rank 的分层 AllReduce</figcaption>
</figure>

以两个服务器、每台四卡为例，原本八个 rank 的贡献先合成两个服务器的局部结果，再按四个片段并行过网。每个跨服务器组处理四分之一向量，但四个组加起来仍覆盖整个向量。若它们共享一个 NIC，不能把总时间也直接除以四；若分别连接四个独立出口，才可能同时利用更多注入带宽。

在跨服务器阶段采用环、各代表组资源独立且大小均匀的模型中，单代表发送 <math><mrow><mn>2</mn><mfrac><mrow><mi>h</mi><mo>−</mo><mn>1</mn></mrow><mi>h</mi></mfrac><mfrac><mi>n</mi><mi>g</mi></mfrac></mrow></math> 字节。按服务器聚合是 <math><mrow><mn>2</mn><mfrac><mrow><mi>h</mi><mo>−</mo><mn>1</mn></mrow><mi>h</mi></mfrac><mi>n</mi></mrow></math>。分层的价值不是凭空消除所有跨网流量，而是先合并同机贡献，并让分片与独立链路相匹配；与此同时增加局部通信、阶段同步和拓扑映射成本。

### 输出顺序限制了分层顺序

AllReduce 的内部片段可以置换，外部只观察最终完整结果；AllGather 与 ReduceScatter 却直接暴露 rank 对应的位置。以两台服务器、每台两卡为例，rank 顺序是 0、1、2、3。若先把同本地编号的 rank 做 AllGather，会得到组内序列 `[0,2]` 和 `[1,3]`；简单拼接成 `[0,2,1,3]` 就违背了外部语义。实现需要调整布局、使用步长拷贝，或选择有利于连续块的阶段顺序。

HCCL 的 Atlas A2 单算子分级说明给出 AllGather 先 Server 内、再 Server 间；ReduceScatter 则先 Server 间、再 Server 内，以维护连续块与所有者顺序。它的 Pipeline AllGather 采用另一种跨层重叠编排，不能由这张顺序阶段表直接推断全部实现均遵循相同次序。[16]（hierarchical_comm_principle、Pipeline）

有根算子也能分层。该文档的 Broadcast 使用 Server 内 Scatter、Server 间 Broadcast、Server 内 AllGather；Reduce 使用 Server 内 ReduceScatter、Server 间 Reduce、Server 内 Gather。最后的 Gather 是内部结果汇合，不意味着 HCCL 一定公开一个 Gather API。AlltoAll(v／VC) 也可在 Server 内整理后跨 Server 交换。这些分解成立的关键是 root、块位置与 rank 映射始终一致。

### 聚合与流水不是同一项优化

Two-Step AlltoAll 将发往同一服务器的小块合并。若原来有 <math><mi>m</mi></math> 条消息、整理后为 <math><mi>k</mi></math> 条，且有效载荷不变，理想启动节约是 <math><mrow><mo stretchy="false">(</mo><mi>m</mi><mo>−</mo><mi>k</mi><mo stretchy="false">)</mo><mi>α</mi></mrow></math>；本地打包／解包与额外内存流量要另计。AlltoAllv 下，不均匀的目的负载还会使某一服务器或端口成为瓶颈。[1]（§4.2.2）

Pipeline 则让一个块跨服务器转发时，另一个已到达块在服务器内分发。若每块两层服务时间分别为 <math><mi>a</mi></math>、<math><mi>b</mi></math>，两层资源真正独立、顺序块数为 <math><mi>q</mi></math>，两级流水的教学模型是 <math><mrow><mi>a</mi><mo>+</mo><mi>b</mi><mo>+</mo><mo stretchy="false">(</mo><mi>q</mi><mo>−</mo><mn>1</mn><mo stretchy="false">)</mo><mi>max</mi><mo stretchy="false">(</mo><mi>a</mi><mo>,</mo><mi>b</mi><mo stretchy="false">)</mo></mrow></math>，而串行模型为 <math><mrow><mi>q</mi><mo stretchy="false">(</mo><mi>a</mi><mo>+</mo><mi>b</mi><mo stretchy="false">)</mo></mrow></math>。收益来自重叠，不来自把慢层带宽改快。共享 DMA／内存控制器、细粒度同步及不均匀块都会缩小收益。[16]（Pipeline）

<figure>
<a href="assets/figures/24-pipeline.svg"><img src="assets/figures/24-pipeline.svg" alt="节点间转发与节点内分发的两级流水"></a>
<figcaption>图 24：节点间转发与节点内分发的两级流水</figcaption>
</figure>

### 从多网卡到跨区域

同号卡跨节点连接、multi-rail 与超级节点为分层提供了机会，但设备编号不是物理邻近性的证明。一个 GPU 到远端 NIC 的 PCIe 路径、跨 NUMA 访问、网卡绑定和交换机上行收敛都可能改变有效带宽。对通信组重新排序，是把算法流量映射到资源；它不能创造不存在的物理链路。

跨区域／广域网还带来更高 RTT、较高误码／丢包风险及管理边界。对一个单瓶颈割，若本次执行必须跨割交付 <math><mi>V</mi></math> 字节、可用速率为 <math><mi>C</mi></math> 字节／秒，则该执行的传输时间至少为 <math><mfrac><mi>V</mi><mi>C</mi></mfrac></math>，尚未计入不可隐藏的 RTT 和依赖等待。这里的 <math><mi>V</mi></math> 必须由实际分解与数据所有权决定，不是对所有算子的统一常数。区域内先合并贡献可能减少跨域输入数，但最终消费者仍需得到必要结果。本章解释的是分层原理，不把数据中心 RoCE 的无损部署条件推广到任意 WAN。
