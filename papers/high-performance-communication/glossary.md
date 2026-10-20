## 术语对应表

本篇用“集合通信”对应 collective communication；“归约”是按元素合并，不是拼接或数据压缩。同名 rank、ring、channel 在不同层次含义不同，以下约定贯穿正文。

| 英文／缩写 | 本篇用语 | 所在层次与区别 |
|---|---|---|
| collective / xCCL | 集合通信／集合通信库家族 | xCCL 不是一个统一库或线缆协议 |
| rank / root | 参与者编号／根参与者 | communicator 内的逻辑编号，不是主机号或 GPU 硬件编号 |
| communicator | 通信域 | 定义参与者及通信上下文，不是物理网络 |
| tensor / chunk / slice | 张量／分块／片段 | 算子输入、调度单位与流水单位不必同大 |
| Broadcast / Scatter | 广播／分发 | 同一块复制给全体／不同块分给不同 rank |
| Gather / AllGather | 汇集／全汇集 | 拼接仅存于 root／拼接存于每个 rank |
| Reduce / AllReduce | 归约／全归约 | 按元素合并，仅 root／全体得到结果 |
| ReduceScatter | 归约分发 | 先按元素归约，再由各 rank 持有不同结果分块 |
| AlltoAll / AlltoAllv | 全交换／变长全交换 | 每个源给每个目的不同块；v 表示可变计数 |
| Barrier | 屏障 | 参与者同步，不自动产生张量归约或数据布局变换 |
| ring / tree | 环／树 | 通信算法的逻辑图，未必是物理布线 |
| HCCL / HCOMM | 华为集合通信库／通信基础库 | 算子、选择与执行／通信域、拓扑和基础资源 |
| RHD / H-D_R | Recursive Halving-Doubling／旧配置别名 | 递归折半—倍增；非二次幂有附加工作 |
| NHR / NB | Nonuniform Hierarchical Ring／Nonuniform Bruck | 非均衡层次环／非均匀 Bruck；不是普通环或 nonblocking |
| AHC / NHR-HCF | Asymmetric Hierarchical Concatenate／NHR Highest Common Factor | 非对称层次拼接／按 Server 数最大公约数重组 |
| CP（HCCL 支持表） | 保留 CP；条目未展开全称 | Atlas A2 单算子 AlltoAllV 的算法名，不是 DCQCN 的拥塞点 |
| CCU / AIV / AICPU_TS | 集合通信单元／向量核／AICPU 与任务调度器 | HCCL 文档的不同通信执行路线，产品与资源条件不同 |
| recursive doubling / halving | 递归倍增／递归折半 | 每轮已知贡献集合扩张／负责的数据范围缩小 |
| channel / multi-rail | 通信通道／多轨网络 | 库调度通道／多条物理网络路径，不能等同 |
| latency / bandwidth / goodput | 时延／带宽／有效吞吐量 | 完成所需时间／链路能力／单位时间有效载荷 |
| bisection bandwidth | 对分带宽 | 网络被划分为两半后的跨割容量，取决于切分与拓扑 |
| data / tensor / pipeline / expert parallelism | 数据／张量／流水线／专家并行 | 划分训练样本／张量运算／层／专家，产生不同通信 |
| PCIe / NVLink / NVSwitch / xGMI | 保留原名 | 主机 I/O 互连／NVIDIA GPU 互连与交换／AMD GPU 互连 |
| NUMA / HBM | 非一致内存访问／高带宽内存 | CPU—内存局部性／常见 GPU 存储技术 |
| DMA / IOVA / IOMMU | 直接内存访问／I/O 虚拟地址／I/O 内存管理单元 | DMA 仍搬数据；设备地址不必等于 CPU 物理地址 |
| ceiling / roofline | 屋顶线／带宽上界 | 以算术强度与峰值算力、带宽定义的性能上界；本篇数值为按明确参数推导 |
| arithmetic intensity / machine balance | 算术强度／机器平衡点 | 每字节对应的浮点运算数／峰值算力与带宽之比 |
| bank / row / column | 存储体／行／列 | DRAM 内部寻址层次，与“通信域 rank”无关 |
| rank（DRAM） | 存储体排 | 同一通道上并行的一组芯片；与通信域的 rank 同名不同义，须按上下文区分 |
| row buffer | 行缓冲 | 整行被激活后暂存的感应结果，命中与否决定访问代价 |
| RAS / CAS / precharge | 行地址选通／列地址选通／预充电 | 选行、选列与关闭当前行的动作 |
| refresh | 刷新 | 电容电荷定期恢复；期间不能访问，带宽损耗随容量增长 |
| HBM / stack / TSV / interposer | 高带宽内存／堆叠／硅通孔／中介层 | 宽接口加堆叠的存储形态；带宽来自位宽与引脚速率的乘积 |
| root complex / lane / TLP | 根复合体／通道／事务层数据包 | PCIe 的拓扑节点、物理通道与事务封装单位 |
| CXL.io / CXL.cache / CXL.mem | 保留原名 | 复用 PCIe 物理层的三种协议：配置与 I/O、设备缓存一致性、主机访问设备内存 |
| host agent | 主机侧代理 | 处理 CXL.mem 并把设备内存暴露给主机的组件 |
| quantization / sparsity / low rank | 量化／稀疏／低秩 | 降低位宽、减少非零元素、用低秩分解近似矩阵；三者减少字节的方式不同 |
| error feedback | 误差反馈 | 把本次丢弃的残差留在本地累加到下一次，用于补偿压缩偏差 |
| compression ratio | 压缩比 | 原字节数与压缩后字节数之比；不能直接当作时间收益 |
| cache / buffer | 高速缓存／缓冲区 | 硬件 cache 与软件数据存储区域不可混称 |
| descriptor / doorbell | 描述符／门铃 | 工作参数／通知设备有新工作，不是有效载荷 |
| Socket / NAPI / skb | 套接字／NAPI／套接字缓冲对象 | 内核 API／事件处理机制／内核包元数据结构 |
| DPDK / EAL / PMD | 数据平面开发工具包／环境抽象层／轮询模式驱动 | 用户态包处理框架、资源初始化与设备快路径 |
| UIO / VFIO | 用户空间 I/O／VFIO | 设备访问框架；DMA 隔离能力不同 |
| XDP / eBPF / AF_XDP | 快速数据路径／扩展 BPF／AF_XDP | 接收钩子、受约束程序机制与用户态包接口 |
| UMEM / FILL ring | 用户共享包内存／补充环 | AF_XDP 数据区域／把可接收帧的所有权交给内核 |
| RDMA / RNIC / HCA | 远程直接内存访问／RDMA 网卡／主机通道适配器 | 内存访问能力、执行硬件与 InfiniBand 体系称谓 |
| InfiniBand / RoCEv2 / iWARP | 保留原名 | 三类 RDMA 协议承载，不是三种集合算子 |
| verbs / provider | 保留 verbs／设备提供层 | RDMA 操作接口／厂商实现适配层 |
| PD / MR / lkey / rkey | 保护域／注册内存区域／本地键／远程键 | 权限与映射；key 不是链路加密密钥 |
| QP / SQ / RQ | 队列对／发送工作队列／接收工作队列 | SQ 也承载 Read、Write 等请求 |
| WR / WQE / WC / CQE | 工作请求／工作队列元素／工作完成／完成队列元素 | API 表示／设备表示；完成信息不是收到业务结果 |
| CQ / RC / UC / UD | 完成队列／可靠连接／不可靠连接／不可靠数据报 | 队列与三类传输服务，不能把 RC 当成 TCP |
| GPUDirect RDMA | 保留原名 | RNIC 直接访问 GPU 内存的数据路径，不是集合算法 |
| incast / head-of-line blocking | 多对一汇聚／队头阻塞 | 突发扇入／一个拥塞流阻碍同队列其他流 |
| PFC / ECN / CNP | 优先级流控／显式拥塞通知／拥塞通知报文 | 逐跳暂停／IP 标记／接收端返回的 RoCE 通知 |
| DCQCN / CP / NP / RP | 数据中心 QCN／拥塞点／通知点／反应点 | 交换机标记、接收 RNIC 反馈、发送 RNIC 调速 |
| current rate / target rate | 当前速率／目标速率 | 实际限速值／恢复状态变量，不是保证获得的容量 |
| RED / headroom | 随机早期检测／预留缓冲余量 | 概率标记策略／PAUSE 生效前吸收在途数据的空间 |
