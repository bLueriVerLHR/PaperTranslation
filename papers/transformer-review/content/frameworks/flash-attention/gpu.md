### 从算法到 GPU：FlashAttention 的硬件组织

#### GPU 的并行与存储层级

CUDA 中线程以 warp 执行，CTA 是协作线程块；CTA 共享片上共享内存，寄存器通常由线程持有，HBM 则承载权重和大张量。更大的 tile 能增加数据复用，却同时增加共享内存、寄存器和累加器占用。超过资源预算可能导致 spill、减少驻留 CTA，甚至无法启动。occupancy 存在最优点：少量 CTA 若能充分使用张量核，也可能比高 occupancy 的低效内核更快。

PTX 是虚拟指令层，SASS 是目标架构上的实际机器指令。源码中的一次矩阵乘会展开为多条指令，异步操作又可能跨越局部代码边界。因此，计算完成、数据可读与缓冲区可覆盖是不同事件；同步建立的是这些事件间的依赖。删去等待可能缩短指令路径，也可能让后续运算读取未完成的数据，性能与正确性的联系由依赖关系决定。

#### FA2：查询块并行与 warp 内分工

[FlashAttention-2](https://arxiv.org/abs/2307.08691)从非矩阵乘成本、序列方向并行度及 warp 分工改进执行组织。它改的是执行组织，涉及的不止一条 GPU 指令。沿查询块扩大网格能改善小 batch、少头时的并行度；将不同查询行分给不同 warp，可以减少同一输出的跨 warp 合并。

在 `csrc/flash_attn/src/kernel_traits.h`、`flash_fwd_kernel.h` 和 `softmax.h` 中，tile 大小、线程数、共享内存布局及矩阵乘原语一起决定执行路径。Ampere 路线用 `cp.async` 把全局数据异步搬入共享内存，`ldmatrix` 按矩阵乘需要的布局读取数据，`mma.sync` 执行 warp 级矩阵乘。搬运 K／V 与计算可部分重叠，但拷贝完成只说明数据已经到达，其他线程能否安全使用还要看协作同步，CTA 内的同步仍须满足。

矩阵乘累加器的布局决定 softmax 行内归约该由哪些 lane 参与。某些 `m16n8k16` 布局下，同一行的片段分在四个 lane，局部归约后用 shuffle 合并；能否使用 `Allreduce<4>` 取决于具体布局。P 转成较低精度后若能直接作为下一次 PV 的寄存器操作数，可以省掉共享内存往返，否则需要重排或共享内存中转。

头维度增大时，同一查询 tile 的输出累加器和相关操作数需要更多空间。如果寄存器占用限制驻留 CTA，或者中间值溢出到本地内存，扩大 tile 带来的复用就可能被并行度下降和额外访存抵消。缩小 tile 或重叠深度可以减少同时存活的状态，却又降低复用或延迟隐藏能力。`kSmemKVSize` 中的两份空间对应 K 与 V；流水级数则描述这些缓冲怎样按时间复用，是另一项资源因素。反向还包含梯度累加状态，其容量约束与前向不同。

#### FA3：Hopper 的 TMA、WGMMA 与生产者／消费者

[FlashAttention-3](https://arxiv.org/abs/2407.08608)利用 Hopper 的异步搬运与矩阵乘，把加载与计算交给不同 warp group。TMA 通过张量描述符处理 tile 搬运、布局和边界；WGMMA 由 warp group 协作发起异步矩阵乘。关键文件是 `hopper/mainloop_fwd_sm90_tma_gmma_ws.hpp`、`flash_fwd_kernel_sm90.h`，以及 CuTeDSL 对应的 `flash_attn/cute/flash_fwd_sm90.py`。

生产者等待某个环形缓冲 stage 空闲，再发起搬运；消费者等待该 stage 的事务完成，发起矩阵乘，并在不再读取后释放。屏障不仅记录到达次数，还要与预期传输字节数、stage 编号和 phase 对齐。多级缓冲隐藏了 HBM 延迟，却增加了共享内存占用；生产者的低寄存器需求可以让出配额给计算角色，但仍受 CTA／SM 的总资源限制。

WGMMA 的异步性允许在一个操作未结束时做独立的 softmax、输出重缩放或发起下一操作。`wait_group` 等待的是已提交组的完成程度，与单份数据是否就绪无关。使用其结果或覆盖其源操作数之前，必须确认相应组已完成。ping-pong 调度让不同 warp group 错开矩阵乘与标量运算，减少张量核等待 softmax 的空档；其收益依形状和流水线而变。

这类流水线针对的是矩阵乘与非矩阵乘阶段的速度失衡：张量核完成一次乘法后，仍可能等待概率归一化或下一块数据。角色分工与异步重叠使这些独立工作同时推进，但消费者数量增加也会分摊 CTA 的寄存器预算，并增加同步成本。FP8 降低操作数位宽，同时引入缩放、排布和误差控制，整体吞吐取决于完整流水线。FA2 可以在兼容旧指令的后续架构运行；FA3 的变化在于主动采用 Hopper 的专属执行能力。

#### FA4／CuTeDSL：Blackwell 的 TMEM 与更细角色分工

固定源码中 `flash_attn/cute/` 包含 CuTeDSL 路线及多个架构实现，不宜把整个目录都等同于一种 Blackwell kernel。`flash_fwd_sm100.py`、`flash_bwd_sm100.py` 承担 SM100 路线，SM90、SM120 另有实现。Python 在这里描述待编译的设备程序，逐元素计算发生在编译后的设备程序里。

Blackwell 的 `tcgen05.mma` 将累加结果放到张量内存（TMEM），减少长期累加器对通用寄存器的挤压。加载、矩阵乘、softmax、输出校正、写回和 tile 调度可由不同 warp 角色负责。S 完成后 softmax 角色从 TMEM 读取、计算 P，再交回矩阵乘角色执行 PV；输出校正角色同时保证旧的输出累加器已按新基准缩放。一个阶段的“完成”因此不只表示数据已经加载。

`pipeline_s_p_o` 表达的正是这个握手：S 就绪；P 写好且 O 校正完成；随后才能执行 PV。S 与低精度 P 的空间复用依赖位宽和生命周期，必须先读完 S 再覆盖。更多并行角色可以重叠 softmax 与矩阵乘，也增加 TMEM 读写、屏障与布局转换。对短输入，这些成本可能压过收益。

2CTA 路线让 cluster 中两个 CTA 协作完成更大的 tile，但 tile 坐标、远端共享内存、参与者数量和事务字节数必须在 cluster 范围一致。`tile_scheduler.py` 还包含 Cluster Launch Control（CLC）相关调度，通过领取工作改善不均匀 tile 的负载。CLC 解决的是工作分派，不改变在线 softmax 的数学。只有 leader 领取 cluster 工作，再把一致的坐标交给协作者，才能避免两侧处理不同 tile。

SM100、SM103、SM120 对应不同后端能力组合，架构名称不能替代具体接口约定。`interface.py` 以形状检查、启发式分派和编译键连接调用与 kernel；归约读、SplitKV、确定性反向和专用头维度的可用性随具体分支变化。这个分派层使硬件差异显式进入计算路径，不同设备因此可以走不同实现。

#### SplitKV：解码时用键方向补足并行度

单个 token 解码的查询方向很短，网格可能没有足够 CTA。SplitKV 将键区间分给多个 CTA，各自计算局部输出和局部 LSE，然后合并。若局部输出 Oₐ 已归一化，最终输出必须按各分片的概率质量加权，不能直接平均：

<math display="block"><mi>z</mi><mo>=</mo><mi mathvariant="normal">max</mi><msub><mi mathvariant="normal">LSE</mi><mi>a</mi></msub><mo>,</mo><mspace width="1em"/><msub><mi>w</mi><mi>a</mi></msub><mo>=</mo><msup><mi>e</mi><mrow><msub><mi mathvariant="normal">LSE</mi><mi>a</mi></msub><mo>−</mo><mi>z</mi></mrow></msup><mo>,</mo><mspace width="1em"/><mi>O</mi><mo>=</mo><mfrac><mrow><munder><mo>∑</mo><mi>a</mi></munder><msub><mi>w</mi><mi>a</mi></msub><msub><mi>O</mi><mi>a</mi></msub></mrow><mrow><munder><mo>∑</mo><mi>a</mi></munder><msub><mi>w</mi><mi>a</mi></msub></mrow></mfrac></math>

`flash_fwd_combine.py` 负责这种部分结果合并。分片越多，独立工作越多，却需要额外部分和、写回与合并 kernel；短 KV 时可能更慢。空分片必须由各角色一致处理，否则某个消费者会等待根本不会产生的数据。确定性反向与 SplitKV 前向的归约组织也不能混为一谈。

#### 数值、寻址与异步状态的不同失效路径

错误可以发生在数学定义、输入寻址或执行时序三个层次。因果边界或头映射错误改变参加计算的元素；归一化与缩放错误改变概率及梯度；缓冲提前复用则让公式正确的程序读取错误代次的数据。这些失效路径需要不同解释，单一的“精度问题”不能概括它们。

| 失效层次 | 相关状态 | 机制关系 |
|---|---|---|
| 输入与寻址 | 掩码、长度、头映射、块表 | 决定每个查询实际读到哪些键和值 |
| 数值与反向 | LSE、D、缩放、累加顺序 | 决定概率重构、梯度尺度与舍入 |
| 搬运与同步 | 事务字节、参与者、完成事件 | 决定消费者何时可以读取新数据 |
| 缓冲复用 | stage、phase、释放事件 | 区分同一地址的不同使用代次 |
| 资源与性能 | 寄存器、共享内存、驻留、spill | 决定复用收益是否被容量与访存抵消 |

以使用两相位屏障、含 S 个 stage 的抽象环形流水线为例，第 t 次工作的缓冲编号与代次可写为：

<math display="block"><mi>s</mi><mo stretchy="false">(</mo><mi>t</mi><mo stretchy="false">)</mo><mo>=</mo><mi>t</mi><mo>mod</mo><mi>S</mi><mo>,</mo><mspace width="1em"/><mi>φ</mi><mo stretchy="false">(</mo><mi>t</mi><mo stretchy="false">)</mo><mo>=</mo><mo>(</mo><msub><mi>φ</mi><mn>0</mn></msub><mo>+</mo><mo>⌊</mo><mfrac><mi>t</mi><mi>S</mi></mfrac><mo>⌋</mo><mo>)</mo><mo>mod</mo><mn>2</mn></math>

缓冲编号在一次完整轮转后重复，相位则翻转。只保存编号无法区分旧数据完成事件与新一轮使用；生产者和消费者对相位的解释不同，就可能出现提前读取或永久等待。这个状态关系说明了为什么容量正确、事务字节正确仍不足以保证异步执行正确。

仓库的 `AI/DEBUG_METHODOLOGY.md`、`DEBUG_2CTA.md` 和 `RACECHECK_TMA_HAZARD.md` 提供了时序变化和同步诊断的具体案例。插入输出语句既改变执行时机，也可能改变编译产物，错误随之消失无法单独区分竞争、布局和工具链因素；racecheck 的报告同样需要结合目标指令的同步语义解释。案例的价值在于展示失效条件与证据之间的关系；把一种历史故障推广成所有异常的原因会误判。

