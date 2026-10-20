### 从文档中的执行链理解实现边界

归档架构把 HCCL 算子层与 HCOMM 分开：算子入口接收语义参数，算法选择器结合拓扑与代价选取执行方案，executor／template／topo_match 将方案分解到具体层级；HCOMM 管理通信域、拓扑和资源，并提供搬移与同步原语。[16]（architecture-brief、README）

拓扑描述与资源实例也不同。该文档的 Edge 描述节点连接，Link 表示可建链信息，Channel 则是可执行数据通道；这些名称与 NCCL 的 Link／Path 不完全对应。CommMem 给出可被设备访问的通信内存，CommEngine 驱动任务。控制面创建或查询资源，数据面执行 Read／Write／Reduce／Notify。一个算法名只有在连接、内存权限和同步依赖都落地后，才形成可执行通信。

HCCL 并不总由同一种核执行通信。文档中的 AICPU_TS 由 AICPU 组织任务、TS 调度搬移；AIV 直接使用 Vector Core，低延迟路线同时占用计算资源；CCU 用专用集合通信单元和预置指令流，减少部分通用执行开销，也受片上资源与支持产品限制。ThreadNotify 管理本实体不同执行上下文的顺序，ChannelNotify 协调远端通信。它们负责数据就绪，不应被简化成与所有设备都一样的 CPU 线程模型。[16]（architecture-brief §§2–3）

以下是原创的算法实施不变量，不是 HCCL 源码摘录：

```text
按拓扑分组并确定每个结果区间的所有者
取得对应Channel与已注册通信内存
每个归约阶段：
    等待输入区间就绪
    发送对端所需区间，接收本地所有区间
    对不重叠的贡献集合执行归约
    标记本阶段结果可供下一阶段读取
结果阶段：按外部算子要求恢复位置并通知消费者
在未完成操作不再引用资源后才允许复用或释放
```

该执行链来自官方架构／算法说明，而非对全部 C++ 模板的逐函数源码审计。提供包中的源码及 HCOMM 依赖具有不同目录与演进边界；本篇不因文件名包含 NHR 就声称 NB、AHC 的每项调度均已对照源码。HCCL 文档与源码的许可不是 MIT，公开阅读页不附带它们的原图或代码，仅保留原创解释及定位。[16]

### 配置语法与产品形态不能混用

Atlas A2／A3 等旧产品说明采用 `level0:NA;level1:...;level2:...` 风格，level0 的内部算法不由该项手工指定，RHD 的配置值写作 `H-D_R`。950PR／950DT 的说明改为 executor 与层级算法组合，包括 Sole、Sequence、Parallel、Pipeline、Concur、StrictOrdered 等执行器概念。这里的 Sequence 指阶段顺序，Parallel 指不同维度并行，Concur 指同层算法并发；它们不等于额外公开算子。[16]（HCCL_ALGO）

950 分支的配置表示优先级与排除条件，仍受拓扑、类型和已注册算法约束；未匹配或全部排除可能警告并回退自适应选择。旧产品的一般说明则强调指定算法替代自适应，某些小数据／特定处理器场景另有例外。因此，一条 `HCCL_ALGO` 字符串不是跨代可复制的性能保证，也不能仅凭设置成功就证明所指定算法实际执行。

Server 间、超节点间的支持度还与产品、算子、数据类型、运行／展开模式相关。AHC 在旧产品配置中可同时影响 level1 和 level2；Pairwise 仅用于 AlltoAll 系列；NHR-HCF 和分组 Full Mesh 有特殊自动选择条件。例如，Atlas A2 的 Server 间 Pipeline 不支持开启确定性计算；Atlas A3 的超节点间 Pipeline 表中，AllGather／ReduceScatter 则要求单算子零拷贝场景，并标为支持确定性计算。两个层级的限制不能合并成“Pipeline 总不支持确定性”。[16]（inter_server_algo_support、inter_superpod_algo_support）

Server 间支持表还列出 Atlas A2 的 CP：用于单算子 AlltoAllV，不支持时回退 Pairwise。该条目没有给出英文全称或独立算法过程，因此不能据两个字母反推机制，也不能把它解释成第 16 章的 Congestion Point。归档文档足以解释已列出的支持边界，但当前设备是否命中某个实现，仍需配套版本与运行记录；这里没有这样的本机实验声明。
