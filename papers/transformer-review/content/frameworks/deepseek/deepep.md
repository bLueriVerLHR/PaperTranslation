### DeepEP：专家并行的 dispatch 与 combine

专家并行把 token 送到专家所在的设备，再把结果送回来。第 1 章算过这笔通信的量级：跨设备分支数决定消息量，门值与返回映射必须一起送达。DeepEP 是这个动作的库实现，也是这组仓库里变化最大的一块。[53]

#### V2.5 把缓冲区拆成四种

同一套生命周期被拆成并列的几个缓冲区，各自负责一种流量：

| 缓冲区 | 承担流量 | 状态 |
|---|---|---|
| `EPBuffer` | 专家的 dispatch／combine，含 FP8 分派 | 主路径 |
| `EngramBuffer` | 远端内存访问式的存储，跨 GPU 或 CPU | 实验 |
| `PPBuffer` | 流水线并行的收发 | 实验 |
| `BucketBuffer` | 集合通信式的 all-gather／reduce-scatter／all-reduce | 实验 |

拆分之后，`BufferAllocator` 在构造缓冲区之前先规划对称内存的分配，[53]（`deep_ep/buffers/allocator.py`）对称布局决定了 RDMA 能不能直接读写对端，也就决定了通信 kernel 的写法。`EPBuffer` 的公开接口保留了 dispatch、combine 与冗余专家相关的方法：

```text
# 文件：DeepEP/deep_ep/buffers/ep.py（固定提交 f6aa38fe）
# 562、770、846、854、886 行（方法定义）
def dispatch(...)
def combine(...)
def lb_get_theoretical_num_sms(self) -> int
def lb_prefetch_weights(...)
def lb_reduce_grads(...)
```

`lb_` 前缀的几个方法是给冗余专家用的：先在专家计算前通过 NVLink 预取权重与量化缩放，反向时把副本的 FP32 梯度累加回原专家。仓库注明这套原语服务于外部工作（MoonEP、UltraEP）探索的专家复制方案，也就是说库提供机制，放置策略留给上层；放置算法本身在 EPLB 仓库，两处的衔接见同章“负载均衡”一节。

#### 两处容易被旧资料误导的地方

第一处是后端。V1 的低延迟模式建立在 NVSHMEM 上，很多二手介绍仍按这个写；V2.5 的说明里写明 NVSHMEM 已不是依赖，设备侧通信改用 NCCL 的 Gin 接口，并复用已有的 NCCL 通信域。[53] 换后端的好处是少一个独立依赖，代价是要求 NCCL 2.32.3 以上，且部分实验特性需要带特定选项的 NCCL 构建。

第二处是 SM 占用。仓库明确写着 dispatch 与 combine 需要占用 GPU 的 SM，零 SM 的 RDMA 专家并行不被支持。这与 2025 年低延迟模式宣传里“通信不占计算资源”的说法不一致，原因是新版把更多工作交给了设备侧发起，需要常驻 warp 来推进。引脚规划也从自动调参改成按解析式给出 SM 与 QP 数，避免在不同机器上重复搜索。

#### 与相邻部件的关系

DeepEP 只负责把 token 与权重送到位，决定送哪些 token 的是路由器，决定何时重叠的是训练或推理引擎。DeepGEMM 的融合 MoE 把一部分通信叠进矩阵乘，两者在缓冲区布局与完成信号上耦合。判断一套部署的通信开销，仍要回到第 1 章那三个量：跨设备分支数、每个分支的字节数、以及同步等待占掉的时间。
