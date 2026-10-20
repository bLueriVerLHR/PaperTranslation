# 正文主题对应

此表对应已形成的主题论述和证据位置，不将题名匹配、文件存在或工程检查当作研究验证。具体断言边界见 `source-map.md`；表中“综述”均为 S1，不表示其所引全部论文另行全文核验。

第 1～6 章（数据移动的账本与节点内移动）的依据来自 S5 一组的官方文档与测量类论文，见 `source-map.md` 的“数据移动与节点内互连”；本表的 xCCL 与 HCCL 两节从第 7 章起的集合通信部分开始。

## xCCL 全部正文

| 原文范围 | 主题／子对象 | 本篇位置与处理 |
|---|---|---|
| §1 | DL扩展、GPU／RDMA、MPI到xCCL、三个研究问题 | 第7、11、12、17章；保留历史关系与比较范围 |
| §2.1–2.7 | Broadcast、AllGather、Scatter、AlltoAll(v)、Reduce、AllReduce、ReduceScatter | 第7–8章逐项语义、容量、例子；SVG11–18 |
| 表1 | Gather、Barrier、Scan及按库／加速器支持差异 | 第7–8、12章；历史表与NCCL2.28.3 API分开，不复制过时全表 |
| §3.1 | 完整／非完整Hypercube | hierarchy/topologies.md；二进制规模、度、容错限制 |
| §3.2 | Ring物理拓扑及利弊 | 同上；纠正碰撞类描述的通用化 |
| §3.3 | Torus、Folded Torus | 同上；回绕、维度、端口与跳数 |
| §3.4 | Fat-Tree | 同上；汇聚容量、Clos多路径和收敛比 |
| §3.5 | Dragonfly、Dragonfly+ | 同上；组内／全局链路和流量分布；SVG22 |
| §4.1.1 | Ring AllGather／AllReduce、αβγ | algorithms/ring-tree.md；几何量与两阶段成本；SVG19 |
| §4.1.2 | Binomial Tree Broadcast／Reduce | 同上；全量路径、短消息、代数顺序；SVG20 |
| §4.1.3 | Recursive-Doubling AG／AR／RS | algorithms/recursive.md、variants.md；区别全量与扩张块，RS变体按综述分类保留 |
| §4.1.4 | Recursive-Halving RS | algorithms/recursive.md；p=2^k、所有者与贡献不变量；SVG21 |
| 表2其余classic | Bruck、Isend–Irecv、Pairwise、Van de Geijn、Rabenseifner、Vector／Distance、Binary Blocks、Linear Scatterv | algorithms/variants.md及recursive.md；机制与约束，不复制阈值为普遍调参表 |
| §4.2.1 | NCCL Ring、Double Binary Trees | ring-tree.md；结合固定厂商设计说明，根／叶例外 |
| §4.2.2 | MSCCL Ring、多channel、All-Pairs、Hierarchical、Two-Step | variants.md、第10章；input／output／scratch、跨节点聚合、流量与启动区分 |
| §4.2.3 | Gloo Ring、Ring-Chunked、HD、Pairwise、BCube | variants.md、libraries/architectures.md；配对名字不自动等同 |
| §4.2.4 | ACCL Hybrid | variants.md、第10章；机内Ring＋机间HD＋机内Ring |
| §5引言 | 分布式训练动机与应用结果 | 第11章；典型状态布局为本篇扩展，不虚构原文章节 |
| §5.1 | Meta RMC／Neo、4D、kernel fusion、ZionEX、ResNet50 | 第11章工业案例，区分模型布局与硬件整合 |
| §5.2 | Google DistBelief、TensorFlow、MPI、gRPC、Fast Socket | 第11章；不添加原文未讨论的TPU案例 |
| §5.3 | Uber Michelangelo／DSW／Horovod、NCCL替换及多后端 | 第11章；原文结果保留条件，不造parameter-server对照 |
| §5.4 | Amazon MiCS、分层AG、两跳梯度、异构网络 | 第11章及第10章通用分层；2.98x不归于单算子 |
| §6.1.1–6.1.6 | NCCL架构、API、框架、comm／stream／topology／protocol、训练与应用 | libraries/architectures.md；LL128不误写通用128B原子、2.28.3核对API |
| §6.2.1–6.2.3 | oneCCL后端、host／device comm、stream／event、算子、PyTorch／Horovod | 同上；历史异构支持不当成全部设备通用域 |
| §6.3.1 | ACCL multi-rail、probe模型、hybrid、AIACC与专有 | 同上及第10章；不把AIACC系统结果当单库结果 |
| §6.4.1–6.4.2 | RCCL HIP路径、互连、stream、框架、NPKit | 同上；迁移概念不承诺任意混合设备执行 |
| §6.5.1–6.5.2 | Gloo transport、rendezvous／MPI、本地buffer与跨机三阶段 | 同上；KV store不是有效载荷中转，P2P表口径差异保留 |
| §6.6.1–6.6.4 | GC3／SCCL／TACCL、chunk DAG／instruction DAG／IR、DSL/runtime/compiler、优化、应用 | 同上；SVG26、生成／调度成本及报告结果边界 |
| 表3 | 加速器、P2P、许可、定位 | 第12章架构与设备授权节；各表与正文不一致项不强行合并 |
| §7.1 | Expanse、V100／HDR／NVLink、全部软件版本、三种基准、重复口径 | libraries/comparison.md；不是六库统一实验 |
| §7.2 | Tests／OMB的AR、AG、A2A、BC | 同上；分别报告区间、1.07x、调用路径与原文Two-Step命名问题 |
| §7.3 | PARAM NCCL／Gloo的AR、AG、BC | 同上；三算子与CPU／GPU路径局限 |
| §8 | MPI吸引力、性能／Blink／合成、共同／差异、网络瓶颈／协同 | 第12章讨论及第17章；归属历史判断 |
| §9 | MPI调优、分布式训练、框架／协议、能量／内存／运行时间 | 第12章四条互补轴；不自动核验其参考文献 |
| §10 | 拓扑→算法→工业库→评测→MPI关系 | 第12章综合；“最成熟”限制在原文时期 |

## HCCL 补充（并入第 12 章）

| 保留文档 | 本篇处理 |
|---|---|
| README、version.cmake、LICENSE | 第12章 HCCL 节与元数据：归档身份、9.2.0组件与配套界限、CANN许可 |
| algo_intro、Ring、Mesh、Star | hccl/algorithms.md；轮数与资源不同，Star方向按算子定义 |
| RHD | 同上及recursive.md；2^k与5rank折叠／恢复 |
| NHR、NB | hccl/algorithms.md；生成树／连续化与步长／份数，不臆造完整源码调度 |
| AHC | hccl/asymmetric.md；2+3组、12片、四个区间的原创推导；SVG28 |
| Pairwise、Pipeline | 第10、12章；变长每轮瓶颈与跨层重叠 |
| hierarchical_comm_principle | 第10章；AG／RS输出顺序、AR内部自由度、有根分解 |
| HCCL_ALGO、server／superpod支持列表 | hccl/execution.md；旧产品与950分开，配置优先级／回退和约束不泛化；区分A2 Server与A3超节点Pipeline确定性条件；CP仅说明条目已支持的用途，未展开全称与机制 |
| NHR_V1、NHR-HCF、分组Full Mesh | 第12章；历史与特殊自动选择条件，不猜缩写 |
| architecture-brief | hccl/execution.md；HCCL／HCOMM、拓扑／资源、AICPU_TS／AIV／CCU、Notify |

HCCL 全部 C++ 模板、未提供的 HCOMM 实现以及实际设备算法命中，不在这次已核验范围；阅读页相应采用文档机制解释而非源码执行或性能验证声明。
