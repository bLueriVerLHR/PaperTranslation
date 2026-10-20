## 13. Linux 网络数据路径 {#linux-network-paths}

Socket、DPDK、XDP 与 RDMA 并非同一条路径的四档速度开关。它们改变包处理位置、内存所有权和可提供的协议服务。网络书的 Linux／DPDK／XDP 讨论提供了这些层次的背景；这里对 NAPI、驱动模式与 AF_XDP 细节分别固定到 Linux 6.12 和 DPDK 24.11 系列文档。[2]（第 4–5、7–9、23 章）[9–12]

### Socket 与 NAPI：从每包中断到预算化轮询

典型接收路径中，NIC 将包 DMA 到接收缓冲区，通知驱动；驱动调度 NAPI poll，以 budget 批量清理接收队列，将需要上层处理的包构造成相应网络对象，进入协议栈和 socket 队列。应用随后通过系统调用读取数据。系统调用、对象管理、协议状态、唤醒和可能的复制分别产生开销，不能全称为“上下文切换”。

NAPI 让中断承担通知、poll 承担批量处理，避免高包率下每包中断都打断 CPU。预算耗尽时继续调度；完成时按驱动与 NAPI 协议重新允许通知。并非所有 poll 都在 `ksoftirqd` 进程中：软中断可能在其他上下文执行，Linux 还支持 threaded NAPI 与 busy polling 等模式。[11]（Overview、Datapath API、Threaded NAPI）

<figure>
<a href="assets/figures/29-linux-paths.svg"><img src="assets/figures/29-linux-paths.svg" alt="Socket、DPDK、XDP 与 AF_XDP 的分叉数据路径"></a>
<figcaption>图 29：Socket、DPDK、XDP 与 AF_XDP 的分叉数据路径</figcaption>
</figure>

### DPDK PMD：将快速包路径交给应用

Poll Mode Driver 从用户态轮询设备队列，以 burst 批量收发，应用通常自己决定包解析、转发和协议逻辑。hugepage、NUMA 本地内存、mbuf pool 与队列所有权帮助减少页表／分配和跨核竞争；单核独占或明确同步某个 RX／TX queue 有利于避免争用。[9]（Poll Mode Driver、Logical Cores、Packet Buffers）

PMD 避开普通内核网络栈的数据路径，不等于计算机从此不需要内核驱动。设备发现、权限、内存映射及 IOMMU 等控制仍由系统提供。书中的 UIO 示例属于一种驱动绑定方式；现代文档也讨论 VFIO，而某些设备使用 bifurcated driver，由内核与用户态协同，未必把整个设备解绑给 `vfio-pci`。[10]（Linux Drivers）

持续轮询用 CPU 时间换取低通知延迟，空闲时也可能消耗核与能量。应用接管更多协议、内存管理和运维责任；“DPDK 更快”只在相应包率、批量、协议及资源预算下有意义，不能据此将任何 Socket 业务直接改写成裸包发送。RDMA verbs 同样是设备队列接口，却具有不同的内存操作与可靠传输语义，不是 DPDK 的别名。

### XDP：在较早位置决定包的去向

原生 XDP 在驱动接收的早期执行 eBPF 程序，在创建完整上层包对象前作出 PASS、DROP、TX、REDIRECT 等决策。PASS 可以继续进入普通网络栈；DROP 让无效或不需要的包尽早结束处理。generic XDP 的位置和成本不同，硬件 offload 又受设备能力限制。[2]（第 23 章）[12]

XDP 仍是 Linux 管理的路径，强调可验证的程序与受控接口。“尽早处理”节约了后续不必要工作，但程序复杂度、映射访问和 redirect 也有成本；它并不为任意应用提供完整可靠连接或远端内存读写。

### AF_XDP：四个环承载缓冲区所有权

AF_XDP 用 UMEM 存放用户提供的帧区域，socket 的 RX／TX 环传递帧描述符；FILL 环向内核供给可接收帧，COMPLETION 环归还完成发送的帧。接收路径从 FILL 取帧，收到包后放到 RX；应用处理后再把可复用帧交回 FILL。发送路径由应用投递 TX，完成后经 COMPLETION 回收。[12]（UMEM、Rings）

这些环管理的是地址／所有权，不是把同一块内存同时随意交给双方写。重复提交、过早复用或没有补充 FILL 都会破坏进度；共享 UMEM 时还要维护正确的 socket／queue 映射和同步。用户态避开部分上层处理，不意味着生命周期可以省略。

copy mode 把收到的数据复制到 UMEM；zero-copy mode 要求驱动与设备支持直接 DMA 到相应帧。`XDP_COPY`／`XDP_ZEROCOPY` 请求及实际能力需要匹配，不能看到 AF_XDP API 就断言必为零复制。[12]（Configuration Flags）

### 所谓零复制的四种不同边界

零复制可能指应用到内核不再复制、NIC 到用户帧直接 DMA、NIC 到 GPU 不经 host staging，或集合 kernel 融合传输与归约。它们省掉的是不同搬移，仍可能存在网络分包、临时区、格式转换和本地归约读取。更准确的性能解释要列出被删掉的那一次复制、原来的字节量及剩余瓶颈，而不是把一个标签当作整条路径免费。
