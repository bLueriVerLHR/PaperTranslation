### 比较条件决定结论的有效范围

xCCL 综述在 SDSC Expanse 测试 NCCL、MSCCL、Gloo 和 CUDA-aware MPICH／UCX；没有将六个库全部跑成同一榜单。每节点 4×V100、NVLink 2、HDR InfiniBand、Hybrid Fat-Tree，最多四节点 16 GPU。软件是 Python 3.7、PyTorch 1.13、CUDA 11.6、NCCL 2.14.3、MSCCL 0.7.3、MPICH 4.0.2、UCX 1.13.1；论文说明重复三次并报告稳定平均，但没有据此提供所有比较的置信区间。[1]（§7.1、表 4）

NCCL Tests 对 NCCL／MSCCL，OMB 对 CUDA-aware MPI，PARAM 经 PyTorch 比较 NCCL／Gloo。前两组虽对齐消息大小和算子，仍经过不同基准路径；PARAM 更包含框架层开销。一个 API 是否原生公开某算子，又不同于测试程序能否用点对点实现它；该测试中的 AlltoAll 不应反向证明当时 NCCL 原生 API 已提供 `ncclAlltoAll`。

| 测试对象 | 原文报告的主要观察 | 可以推出什么 |
|---|---|---|
| NCCL Tests：AllReduce | NCCL 时延总体约为 MSCCL 的 1.07 倍；MPI 在该组较慢 | 定制算法可能改善此配置；不是训练固定快 7% |
| NCCL Tests／OMB：AllGather | NCCL 与 MSCCL 近似；MPI 在小于约 1.5 KB 区域可能更快，长消息变慢 | 消息区间会改变后端比较 |
| NCCL Tests／OMB：AlltoAll | NCCL 与 MSCCL 近似；正文在小于约 6 KB 处报告 MPI 较低时延 | 不能用总括的 1.5 KB 阈值替代该算子的具体描述 |
| NCCL Tests／OMB：Broadcast | MPI 在小于约 512 KB 处有优势，较大消息逆转 | 广播不能套用 AllReduce 的结论 |
| PARAM：AllReduce | Gloo 平均约为 NCCL 时延的 10–20 倍，部分小消息情况差距更大 | 这是 GPU／框架路径上的观察，不是 CPU 通信排名 |
| PARAM：AllGather | 小消息 Gloo 约为 NCCL 的 3–6 倍，长消息平均差距扩大 | 比例随消息大小变化 |
| PARAM：Broadcast | NCCL 的范围较稳定，Gloo 随消息／规模变化更明显 | 稳定性和平均值是不同维度 |

以上数字均归属 [1]（§§7.2–7.3、图 9–10）的测试，不是跨论文拼接。原文把某些差距归因于 GPU 优化、CPU 执行或网络瓶颈；这些是作者解释，基准本身没有逐项消融排除全部因素。原文某处将 Two-Step 与 AllReduce 并列，但算法章明确讨论的是 Two-Step AlltoAll，本篇不据此新增一个已核验的 Two-Step AllReduce 实现。

AllGather 与 AllReduce 的时延也不能只靠“前者没有归约”解释：若消息大小字段的口径不同，一个可能表示本 rank 发送量，另一个表示完整向量大小。只有对齐有效字节、参与者及测试路径后，减少归约计算才是可比较原因。[1]（§7；本篇的指标分析见第 17 章）
