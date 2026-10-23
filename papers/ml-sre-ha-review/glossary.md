# 术语对应表

本文以“机制名 + 工程动作”两套词表述，避免同一对象换称呼。英文缩写首次出现时给出全称；同一缩写在分布式共识与容器编排中含义不同，按下表区分。

| 英文／缩写 | 本文用语 | 层次与区别 |
|---|---|---|
| SRE（Site Reliability Engineering） | 站点可靠性工程 | 用软件工程手段管理服务风险的职能与方法集，不是“运维”的同义词 |
| SLI（Service Level Indicator） | 服务等级指标 | 被量化的观测对象，如请求成功率、时延分位数、作业有效算力占比 |
| SLO（Service Level Objective） | 服务等级目标 | 施加在 SLI 上的目标值或区间，本文写作 `SLI ≤ 目标` 或区间形式 |
| SLA（Service Level Agreement） | 服务等级协议 | 带违约后果的对外承诺；SLO 是其内部依据，不等同 |
| error budget | 错误预算 | 1 − SLO 在一个窗口内允许消耗的不可用额度，本文按“预算比例”和“预算时长”两种口径分别说明 |
| burn rate | 预算消耗速率 | 实际错误率与预算错误率之比；消耗速率 1 表示窗口内恰好用尽预算 |
| nines | 可用性“个 9” | 99.9% 为 3 个 9，每加一个 9 表示不可用比例降低一个数量级 |
| MTBF（mean time between failures）／MTTR（mean time to repair） | 平均故障间隔／平均修复时间 | 前者决定需要多少冗余，后者决定切换与重建的时间预算 |
| toil | 重复性人工劳动 | 可被自动化、随规模线性增长、不产生持久价值的工作 |
| on-call | 值班 | 承担分页响应责任的轮值安排，本文按“分页是否可行动”讨论其设计 |
| postmortem | 复盘报告 | 对事件影响、缓解动作、成因与后续动作的书面记录，本文按无指责原则使用 |
| canary | 灰度发布 | 先对一小部分流量或作业启用新版本，观察其 SLI 后再放量 |
| container | 容器 | 依赖命名空间与 cgroups 获得受限视图的进程，与宿主机共享内核 |
| image | 镜像 | 只读的应用运行环境打包产物，构建完成后不可变 |
| namespace（Linux） | 命名空间 | 内核的资源视图隔离机制；容器编排里的 namespace 是 API 作用域，两者不同 |
| cgroup | 控制组 | 内核的资源计量与限制机制，v1 按子系统分挂载点，v2 统一层级 |
| OCI／CRI | 开放容器标准／容器运行时接口 | OCI 定义镜像与运行时规范，CRI 定义 kubelet 与运行时的调用接口 |
| runc／containerd | 低层运行时／高层运行时 | runc 负责创建受限进程，containerd 负责镜像、生命周期与 CRI 服务 |
| Pod | Pod | 共享网络、IPC、UTS 命名空间的一组容器，是调度与资源声明的基本单位 |
| request／limit | 申请量／上限 | request 参与调度与 QoS 判定，limit 写入 cgroup 上限 |
| QoS class | 服务质量等级 | Guaranteed、Burstable、BestEffort 三档，决定节点压力下的驱逐顺序 |
| eviction | 驱逐 | kubelet 在节点资源不足时按优先级终止 Pod 的动作，分软驱逐与硬驱逐 |
| Scheduler Framework | 调度框架 | kube-scheduler 暴露的插件扩展点，本文只讨论 Filter 与 Score 两段 |
| gang scheduling | 成组调度 | 一组 Pod 同时满足资源才一起启动，避免部分启动造成的互相等待 |
| device plugin | 设备插件 | 通过 gRPC 向 kubelet 上报与分配异构设备的机制，只提供计数语义 |
| MPS／MIG | 多进程服务／多实例 GPU | 前者在空间上共享 SM，后者把 GPU 切分为独立实例；两者的隔离强度不同 |
| CRAQ | 分摊查询的链式复制 | 写全链路、读任意副本的一致性协议，本文按 3FS 的实现描述其版本语义 |
| chain／chain table | 复制链／链表 | 副本序列与链的集合；链表版本号在成员变化时递增 |
| quorum | 多数派 | 超过半数的集合；共识的提交与选举都以多数派为判据 |
| term | 任期 | Raft 的单调递增编号，用于区分不同轮次的领导权 |
| commit | 提交 | 日志条目被多数派确认后可安全应用到状态机 |
| failover | 故障切换 | 把服务角色从失效节点转移出去的过程，需要防止旧主继续写入 |
| fencing | 隔离旧主 | 通过租约、代际号或存储侧拒绝写入，使被替换的节点无法继续生效 |
| checkpoint | 检查点 | 训练状态的持久化快照；本文按“写出体积／写带宽／回退损失”三项记账 |
| goodput | 有效算力产出 | 扣除故障、回退与等待后的训练推进量，区别于标称算力 |
| TTFT／TBT | 首 token 时延／token 间隔 | 生成式推理的两个时延 SLI，分别约束预填充与解码阶段 |
| P/D 分离 | 预填充与解码分离 | 把两阶段放到不同实例池，各自按不同目标调优 |
| KVCache | 键值缓存 | 解码阶段复用的中间结果；其容量与命中率决定可服务的上下文规模 |
| RDMA | 远程直接内存访问 | 绕过对端 CPU 的内存访问机制；本文只讨论其超时与故障语义 |
| PFC／ECN | 优先级流控／显式拥塞通知 | 无损网络的两类反馈手段，前者按优先级暂停链路，后者标记拥塞 |
| CPI（cycles per instruction） | 每指令周期数 | 干扰的代理指标，数值越高表示同样的工作量花掉更多周期 |
| QPS（queries per second） | 每秒请求数 | 到达率的口径，不等于可服务容量 |
| P99 | 99 分位 | 分位数口径，不能跨实例相加或取平均 |
| FUSE（Filesystem in Userspace） | 用户态文件系统 | 通过内核模块把 I/O 转到用户态进程，代价是内存拷贝与并发扩展性受限 |
| MTBI（mean time between interruptions） | 平均中断间隔 | 来源可能按 GPU 小时归一化；仅在累计暴露量口径、强度随卡数线性缩放时，可除以作业卡数估算墙钟间隔 |
| scale-up domain | 扩展域 | 通过 NVLink 紧耦合的 GPU 组；NVL72 指 72 卡一个域，取代 H100 世代的 8 卡域 |
| PAFT（parallelism-aware fault tolerance） | 并行感知容错 | 隔离故障副本，其余副本重复该步后继续；故障副本在备用资源上重启并重新同步 |
| SDC（silent data corruption） | 静默数据损坏 | 硬件算错且不留痕迹，应用消费错误结果；与可观测的故障相对 |
| Fleetscanner／Ripple／Hardware Sentinel | 三种静默损坏检测机制 | 定向微基准／与负载共置的短测试／内核态异常分析，差别在覆盖周期与侵入性 |
| DSF（disaggregated scheduled fabric）／NSF（non-scheduled fabric） | 分离式调度网络／非调度网络 | 前者在网内进行子包多路径与重排，后者依赖端点重排与交换机负载均衡；不能据此推出总体故障率 |
| BAG（back-end aggregation） | 后端汇聚网 | 连接楼内 fabric 的多层 hub-and-spoke 网络，报告的链路跨度从 2 km 到 100 km 以上 |
| AALC（air-assisted liquid cooling）／FLC（facility liquid cooling） | 风助液冷／设施液冷 | 前者用于自由空气建筑与快速部署结构，后者用于 AI 优化建筑；两者都是闭式直触液冷 |
| BESS（battery energy storage system）／BBU（battery backup unit）／CBU（capacitor backup unit） | 电池储能／机架电池／电容托盘 | 不同层级的功率缓冲；引用报告未给出统一响应时间与容量 |
| spare ratio | 备用率 | 备用量相对活跃量或装备总量的比例；两种分母不同，必须明确标注 |
