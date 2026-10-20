### NCCL：通信域、stream 与设备执行

NCCL 通信域确定参与 rank 及其 CUDA 设备，初始化阶段交换身份并建立资源；算子调用指定缓冲区、类型、计数、归约操作和 stream。库根据拓扑与调用条件选择算法，把传输及归约任务排入设备执行上下文。节点内可利用 PCIe／NVLink 等路径，跨节点可使用网络后端和 GPUDirect RDMA；后者仍以平台与驱动支持为前提。[1]（§6.1）[8]

论文列出的 `ncclCommInitRank`、`ncclCommInitRankConfig` 与 `ncclCommInitAll` 为不同初始化场景提供入口；建立通信域后才执行算子。TensorFlow、PyTorch、Caffe、CNTK、MXNet 与 Horovod 等在论文时期通过各自适配层使用 NCCL，这说明生态整合，而不是所有框架今天仍具有相同默认后端。[1]（§§6.1.2–6.1.3）

stream 是顺序约束，不是额外网络端口。同 stream 上的生产计算先于通信，通信后面的消费者才可依赖其结果；跨 stream 需要事件等显式依赖。在一般异步调用中，CPU 返回表明任务已排入 stream，而非 GPU 结果可随意读取。非阻塞通信域、分组操作还有各自进度要求，不能只用“返回即完成”判断。[6]

下例是原创教学伪代码，不是上游源码，也不是可直接运行的完整训练程序。它只展示数据生命周期：

```text
comm = 建立通信域(所有参与rank及设备)
在stream_C计算本地梯度
record(event_ready, stream_C)
wait(stream_N, event_ready)
在stream_N排入AllReduce(本地梯度 → 全局梯度)
record(event_done, stream_N)
wait(stream_C, event_done)
在stream_C读取归约结果并更新参数
```

LL、LL128、Simple 是 NCCL 的协议／同步粒度路线，不是 AllReduce 算法名。低延迟方案用较细粒度的就绪标记与数据组织降低等待，代价可能是有效载荷比例及带宽效率；较大消息更能摊薄 Simple 路线的开销。综述把 LL128 简写成“128 bytes atomic store”，这里不将整块 128 字节说成设备保证的一次通用原子存储；真正原子性与可见性要依赖实现和硬件语义。[1]（§6.1.4）

论文 2023 年支持表中 NCCL 不直接提供 Gather、Scatter、AlltoAll，训练示例用 Send／Recv 组合 Scatter。固定的 NCCL 2.28.3 API 已列出 `ncclGather`、`ncclScatter`、`ncclAlltoAll`，因此历史示例不能冒充当前缺失功能。[5] Barrier、Scan、任意变长或 MPI 派生类型也不能因为 API 风格相近而自动推定支持。接口名称、算法调度与设备可用性是三次不同核对。

### oneCCL：通过后端与执行上下文适配异构设备

综述中的 oneCCL 面向 oneAPI 生态，将 Intel MPI／libfabric 等底层通信与 Level Zero 等设备能力结合。通信域区分 host 与 device 参与者，stream 传递执行上下文，event 表示异步操作状态；优先级字段提供调度提示。它把可移植的传输接口与设备专用执行结合起来，代价是后端、设备和事件语义需要一致配套。[1]（§§6.2.1–6.2.2）

论文列出的算子包括 AllGather(v)、AllReduce、AlltoAll(v)、Barrier、Broadcast、Reduce、ReduceScatter。PyTorch bindings 与 Horovod 集成让框架可选择该后端；框架支持不意味着所有设备具有相同快路径。本篇介绍的是该调查时期的能力，不依据品牌名假定所有 FPGA、CPU 和 GPU 都能共享任意通信域。[1]（§6.2.3）

### ACCL：对异构互连作混合调度

Alibaba ACCL 面向多 fabric、multi-rail 以及节点内外带宽差异。文中以物理网络探测模型帮助选择 hybrid 算法：快局部网络上分片归约，慢跨节点网络上代表交换，再局部拼接。[1]（§6.3）一个统一 ring 可能把快路径变成等待慢路径的串行链，分层因此改变关键路径。

其收益以拓扑建模准确、流量分配合理和额外阶段成本可摊薄为前提。论文时期 ACCL／AIACC 是专有体系；本篇没有据名称推断公开源码，也不把论文中 AIACC 的系统比较直接归因于 ACCL 单库。这里的 ACCL 明确指 Alibaba Collective Communication Library，而非其他同缩写的项目。

### RCCL：API 相似不代表平台成本相同

RCCL 是 ROCm 的集合通信路线，与 NCCL 接口和环／树设计具有历史联系。综述用 CUDA 经 HIPify 转换为 HIP 的路径解释可移植性，提到 PCIe／xGMI、verbs 和 TCP/IP，以及 HIP stream 和 NPKit 跟踪。[1]（§6.4）

源码转换减少接口迁移工作，不消除设备原子操作、互连、调度器和内存一致性的差异。论文中的编译器和框架版本属于历史描述，不能据此声称当前 RCCL 可在任意 NVIDIA／AMD 混合域运行。MPI 可以承担多进程启动或通信协调，也不能简单等同于所有 RCCL 数据都经 MPI 搬运。

### Gloo：建立连接与执行集合通信分开

Gloo 的 CPU 通信与 GPU 支持覆盖范围不同。rendezvous 通过共享键值存储交换对端地址和端口，或使用 MPI 进行协调；完成建链后，大块数据由所选 transport 传输，键值存储并不是每块数据必经的中转服务器。[1]（§6.5）

当一个进程拥有多个缓冲区，其文中 AllReduce 分三步：本地合并缓冲区、跨进程集合、再把结果传播回本地各缓冲区。中间可用 Ring、Ring-Chunked、Halving-Doubling、BCube；这与单个 GPU 直接加入通信域的布局不同。CPU-oriented 设计在 CPU 训练和协调中有用途，不能从 GPU 测试较慢就推断它在所有场景都多余。论文表 3 的 P2P 标记与 §6.5 对 CPU 点对点的描述口径不同，不能当作今天的统一否定。[1]

### MSCCL：从块依赖图到可执行调度

MSCCL 将通信算法的表达与运行分开。GC3 提供块导向 DSL 和编译器；SCCL、TACCL 从拓扑及约束／communication sketch 合成调度。块程序说明某块从何处来到何处去，经 tracing 形成 chunk DAG；lowering 展开为指令 DAG，再将指令安排到 channel、thread block 及同步结构，生成运行时执行的中间表示。[1]（§6.6）

<figure>
<a href="assets/figures/26-library-flow.svg"><img src="assets/figures/26-library-flow.svg" alt="块依赖、指令展开与运行资源的分层"></a>
<figcaption>图 26：块依赖、指令展开与运行资源的分层</figcaption>
</figure>

两种 DAG 不能合并成一个概念：前者表示数据依赖，后者还要表达传输、归约与同步指令。调度 directives 可以拆小传输以增加并行，或合并连续块减少启动；同一对 GPU 的多个 channel 也提供不同安排。改善某一依赖图会增加算法生成、拓扑适配和维护成本；机器配置变化后，已有调度不一定仍最优。

综述报告了 8×A100 语言模型推理及 256×A100 MoE 训练中的不同加速区间，且随 batch／模型结构变化。[1]（§6.6.4）这些是所引系统的应用结果，不是本篇复现，也不是对任意 MSCCL kernel 的统一保证。NCCL-compatible API 有利于框架替换后端，但运行时兼容、算法覆盖与硬件版本仍需分别满足。
