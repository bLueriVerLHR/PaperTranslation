## 14. RDMA：资源、驱动与完成语义 {#rdma-mechanisms}

RDMA 将数据搬移描述为设备可执行的网络／内存操作，降低逐消息 CPU 协议处理和中间复制。Remote Direct Memory Access 并不意味着任意进程能直接访问任意地址：保护域、注册内存、队列、权限和连接状态共同限定访问。[2]（第 13–17 章）[13–14]

### 三种网络承载，不同可靠性基础

InfiniBand 自身具有专门的链路、交换与传输体系；RoCE v1 使用以太网二层承载，RoCE v2 封装到 UDP/IP，可在 IP 网络中路由；iWARP 基于 TCP 等协议形成 RDMA 能力。RoCE v2 的 UDP 封装不意味着上层 RC 操作没有可靠性，可靠性由 RDMA 传输机制而非普通 UDP socket 提供。反过来，使用 TCP 的 iWARP 也不是所有 RoCE 网络配置的替代名称。[2]（第 13 章）[3]（§2）

协议名称、QP 类型与业务保证不同。RC（Reliable Connected）、UC、UD 等服务提供的操作和可靠性并不相同；本章队列生命周期主要以常见 RC verbs 路径解释，不将其保证推广到所有 QP。

### 控制面建立权限与地址关系

用户态 verbs 库和 provider 对接内核 RDMA 子系统与设备驱动。内核执行资源创建、保护、映射等控制操作；建立资源后，典型快速路径通过映射的队列／doorbell 与 NIC 交互，减少每条消息进入普通内核网络栈的需要。用户态快速路径不是无驱动路径。[2]（第 14–15 章）

常见对象的关系如下：PD（Protection Domain）划分资源保护域；MR（Memory Region）登记一段可访问内存及权限；QP（Queue Pair）包含发送和接收工作队列；CQ（Completion Queue）保存完成记录。多个 QP 可以关联一个 CQ，但队列容量、轮询及错误处理责任必须明确。

<figure>
<a href="assets/figures/30-rdma-resources.svg"><img src="assets/figures/30-rdma-resources.svg" alt="PD、MR、QP、CQ 与远端缓冲区"></a>
<figcaption>图 30：PD、MR、QP、CQ 与远端缓冲区</figcaption>
</figure>

传统内存注册固定相应页并建立设备映射，保持 DMA 地址在操作期间有效；On-Demand Paging 等机制可以改变页驻留和缺页处理方式，不能一概说所有注册都永久固定全部页。[14] MR 的 lkey 支持本地访问检查，rkey 配合远端地址授权特定远端操作。键值和权限不是加密，也不是任意网络参与者的身份认证替代品；撤销／更新资源后，旧地址与键不能继续使用。

### 工作请求如何变成设备动作

应用准备 WR（Work Request），其中含操作类型和 SGE（Scatter/Gather Entry）列表。SGE 指本地地址、长度与 lkey；RDMA Read／Write 另需远端地址与 rkey。这里的 Scatter/Gather 是本地分散缓冲区描述，不是第 2 章的跨 rank Scatter／Gather 算子。[13]

`ibv_post_send` 将工作请求提交到发送队列。成功返回主要说明投递被接受，不是搬移已完成；NIC 稍后执行，并按 signaling 条件生成 CQE。调用失败可通过 `bad_wr` 定位首个未成功投递请求，不能把请求链的部分成功当作全部失败再盲目重投。发送缓冲区要保持到相应工作完成，inline 特例及 unsignaled 管理各有条件。[13]（DESCRIPTION、NOTES）

下例是原创生命周期伪代码，不是可编译的 verbs 程序或上游摘录：

```text
创建PD、CQ、QP，交换连接参数与远端授权信息
注册本地缓冲区，取得lkey；必要时交换远端地址与rkey
填充数据 → 构造SGE与WR → post_send
while 尚未确认所需完成:
    poll_cq
    匹配wr_id并检查status
完成且消费者依赖满足后：复用缓冲区
所有相关操作结束后：撤销MR并释放资源
```

### 双边消息与单边内存操作

Send／Receive 要求远端预投递接收缓冲区，接收方通过 CQE 获知消息；RC 下接收资源不足可能触发 RNR 与重试限制。RDMA Write 把本地数据写入已经授权的远端 MR，一般 Write 本身不要求一个普通 Receive WR，也不自动让远端应用得到同样的接收 CQE；Write with Immediate 有额外通知及接收资源语义。RDMA Read 则由发起者拉取远端授权区的数据。原子操作提供受支持范围内的远端 read-modify-write，不等于任意复杂归约函数。[13]

“单边”说的是操作发起时不需要远端应用逐次执行对称收发，不是没有远端 NIC、驱动、注册或先前协议协商。应用仍要知道何时数据完整、哪个消费者可以读取，以及何时释放远端内存。

### 三个不同的完成时刻

投递完成、传输工作完成、远端业务处理完成不能互换。本地 CQE 按操作类型和传输语义表示该 WR 的完成，使相应资源可按规范复用；它不证明远端程序已解析、归约或持久化数据。远端消费还需要相应通知、顺序和内存可见性协议。GPU 消费者另需符合设备同步规则。[13][8]（§3.7）

如果应用要求“远端归约已经完成”，应有完成通知或返回消息确认该语义，而非只观察本地 Write CQE。持久化存储还要处理缓存刷写及故障域，普通 RDMA 写完成不是持久事务提交。RDMA 所减少的 CPU 工作很真实，却不会替应用定义这些更高层语义。

### RDMA 与集合库的职责分界

RC QP 对应一条已连接的传输关系；集合算法负责多个关系之间的贡献合并、块所有权与依赖。NIC 完成搬移，归约通常还由 GPU／NPU／CPU 或专用通信硬件执行。硬件 offload 可能承担更多工作，但不能默认任意 RDMA NIC 自动执行 AllReduce。很多 QP 并发还会争用上下文缓存、PCIe 和网络路径。于是 RDMA 降低单次搬移成本后，算法和网络拥塞仍可能成为主导因素。
