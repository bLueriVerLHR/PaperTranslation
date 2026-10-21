## 1. 为什么瓶颈在移动 {#why-movement}

把一份模型放到加速器上，算力通常不是最先耗尽的资源。实测数据给出同一台机器上三个相差三个数量级的速率：Grace Hopper 平台上，GPU 的 HBM3 实测 3.4 TB/s（同文给出的理论值 4 TB/s），CPU 侧的 LPDDR5X 实测 486 GB/s（理论 500 GB/s）[23]；同一代节点的 PCIe 5.0，每条 lane 32 GT/s，16 条 lane 约 64 GB/s [20]；一个 400 Gb/s 的网口折算约 50 GB/s。计算单元每秒能做的浮点运算以 10<sup>14</sup>～10<sup>15</sup> 计，而这些路径每秒只能送进 10<sup>10</sup>～10<sup>12</sup> 字节。两者放在一起，问题就从“算得快不快”变成“数据能不能及时送到”。

本章先把这些数字算清楚：一个计算任务需要搬多少字节、它相对于算力的密度是多少、什么时候会跨过带宽限制的边界。得出边界之后，后面各章讨论的都是同一个问题的不同层面——怎样少搬、怎样搬得更有效。

### 1.1 算术强度与机器平衡

屋顶线模型（roofline）用两个量刻画一个计算任务：峰值算力 <math><mi>P</mi></math>（每秒浮点运算次数）与内存带宽 <math><mi>B</mi></math>（每秒字节数），以及该任务的算术强度 <math><mi>I</mi></math>（每搬入一个字节所完成的浮点运算次数）[17]。任务可达到的性能上界是：

<math display="block"><mrow><mi>F</mi><mo>≤</mo><mi>min</mi><mo stretchy="false">(</mo><mi>P</mi><mo>,</mo><mspace width="0.3em"/><mi>I</mi><msup><mo>·</mo><mrow><mspace width="0.2em"/></mrow></msup><mi>B</mi><mo stretchy="false">)</mo></mrow></math>

式中的 <math><mi>min</mi></math> 是两条上界取小：真正决定结果的是算力上限 <math><mi>P</mi></math> 还是带宽上限 <math><mrow><mi>I</mi><mi>B</mi></mrow></math>。两者相等处的强度

<math display="block"><mrow><msub><mi>I</mi><mo>*</mo></msub><mo>=</mo><mfrac><mi>P</mi><mi>B</mi></mfrac></mrow></math>

称为该机器的平衡点。任务的算术强度低于 <math><msub><mi>I</mi><mo>*</mo></msub></math> 时，提升算力不会提升性能：多出来的算力在等数据。

用文献报告的数据代入一个具体机器。Hopper 代 H800 的 FP16 峰值吞吐为 756.5 TFLOPS [21]，同文测得的全局内存吞吐约 2.0 TB/s（2039 GB/s）[21]，于是

<math display="block"><mrow><msub><mi>I</mi><mo>*</mo></msub><mo>≈</mo><mfrac><mrow><mn>756.5</mn><mo>×</mo><msup><mn>10</mn><mn>12</mn></msup></mrow><mrow><mn>2039</mn><mo>×</mo><msup><mn>10</mn><mn>9</mn></msup></mrow></mfrac><mo>≈</mo><mn>371</mn><mspace width="0.3em"/><mtext>FLOP/byte</mtext></mrow></math>

这个数是按该文报告的峰值与实测带宽算出的比值，条件属于其测试平台；换成 HBM3 的 Hopper 系统（实测 3.4 TB/s [23]），同样的峰值吞吐下平衡点降到约 222 FLOP/byte。

### 1.2 两类计算的差距有多大

矩阵乘法的算术强度随规模增长。一个 <math><mrow><mi>n</mi><mo>×</mo><mi>n</mi><mo>×</mo><mi>n</mi></mrow></math> 的乘加，浮点运算量是 <math><mrow><mn>2</mn><msup><mi>n</mi><mn>3</mn></msup></mrow></math>；按“每个操作数各从内存读一次、结果写一次”的口径，FP16 下搬运字节数是 <math><mrow><mn>2</mn><msup><mi>n</mi><mn>2</mn></msup><mo>×</mo><mn>2</mn><mo>=</mo><mn>4</mn><msup><mi>n</mi><mn>2</mn></msup></mrow></math>（把结果写回也计入时系数更大），于是

<math display="block"><mrow><mi>I</mi><mo>=</mo><mfrac><mrow><mn>2</mn><msup><mi>n</mi><mn>3</mn></msup></mrow><mrow><mn>4</mn><msup><mi>n</mi><mn>2</mn></msup></mrow></mfrac><mo>=</mo><mfrac><mi>n</mi><mn>2</mn></mfrac><mspace width="0.3em"/><mtext>FLOP/byte</mtext></mrow></math>

令 <math><mrow><mi>n</mi><mo>/</mo><mn>2</mn><mo>=</mo><msub><mi>I</mi><mo>*</mo></msub><mo>=</mo><mn>371</mn></mrow></math> 得到 <math><mrow><msup><mi>n</mi><mo>*</mo></msup><mo>≈</mo><mn>742</mn></mrow></math>：方阵维度要到七百多，这份 FP16 矩阵乘才进入算力受限区。规模更小、或分块后每次只有小块的中间结果复用时，它仍在带宽侧。

逐元素算子离得更远。读两个 FP16 张量、写一个结果，每个元素搬 6 字节，做一次加法：

<math display="block"><mrow><mi>I</mi><mo>=</mo><mfrac><mn>1</mn><mn>6</mn></mfrac><mo>≈</mo><mn>0.17</mn><mspace width="0.3em"/><mtext>FLOP/byte</mtext></mrow></math>

与 371 相差约两千倍。这类算子在任何现代加速器上都被带宽锁住，算力翻倍对它们没有意义；归一化、激活、掩码、逐元素缩放都属于这一类。深度学习模型里这层算子的数量与矩阵乘相当，甚至更多。

<figure>
<a href="assets/figures/01-arithmetic-intensity.svg"><img src="assets/figures/01-arithmetic-intensity.svg" alt="横轴为算术强度（对数），纵轴为每秒浮点运算；斜线为带宽上界，水平线为峰值算力，拐点标注 371 FLOP/byte；矩阵乘与逐元素算子分别标在斜线两侧。"></a>
<figcaption>图 1：算术强度与带宽上界。斜线为带宽上界 I·B，水平线为峰值算力 P，拐点为第 1.1 节算出的 I*≈371 FLOP/byte（H800 的 FP16 峰值与实测带宽口径）。逐元素算子位于斜线左端，规模有限的矩阵乘同样如此。图中坐标为示意，不代表任何一次实测。</figcaption>
</figure>

### 1.3 移动的代价由三件事放大

同一份数据从产生到被用上，字节数往往不止一遍。放大来自三个方面，后面的章节分别处理：

**重复访问。** 数据被多次读取，即使每次只读一部分。分块能否把复用量留在片上决定了有效强度：这与第三章的内存层次和第四章的节点内互连直接相关。

**格式与精度转换。** 同一批数值在 FP32、FP16、FP8、以及量化后的整数之间来回转换，每次转换都伴随读写。降低精度的收益正是减少字节（第五章第二节讨论其边界），而转换本身的搬移也要计入。

**协议与同步开销。** 数据被封装成包、写进队列、等待完成、被重新解包。带宽标称值描述的是链路能力，实际有效载荷还要扣掉头部、重传、暂停与等待。这部分开销在第八章之后逐层展开。

### 1.4 本书的路线

据此，本书把“数据移动”当作第一性问题：先给出各层的代价地图（第 2 章），再进入节点内（第 3～6 章），然后沿此前已有的集合通信与网络材料展开节点间部分（第 7～15 章），最后回到归因方法（第 16 章）。

| 篇 | 章节 | 贯穿的问题 |
|---|---|---|
| 数据移动的基础 | [第 1 章](#why-movement)、[第 2 章](#movement-layers) | 一次搬移的字节数、速率与延迟各是多少？ |
| 节点内移动 | [第 3 章](#dram-hbm)、[第 4 章](#pcie-cxl)、[第 5 章](#communication-hardware)、[第 6 章](#reduce-movement) | 数据离开计算单元后先经过哪些瓶颈？怎样少搬？ |
| 节点间移动 | [第 7 章](#rooted-collectives)、[第 8 章](#all-collectives)、[第 9 章](#collective-algorithms)、[第 10 章](#hierarchical-communication)、[第 11 章](#training-dependencies)、[第 12 章](#xccl-libraries)、[第 13 章](#linux-network-paths)、[第 14 章](#rdma-mechanisms)、[第 15 章](#congestion-foundations)、[第 16 章](#dcqcn-mechanism) | 跨设备与跨节点的数据怎样被组织和调度？ |
| 归因 | [第 16 章](#performance-reasoning) | 一个快的微基准为什么不保证训练快？ |

到第 16 章为止，全部讨论都落在同一条链上：物理拓扑约束算法，算法由库映射到设备，设备与主机的数据路径决定有效载荷，网络反馈决定共享资源不足时的发送行为。区别只在于本书把起点定在“字节从哪里来、经过哪一层、付什么代价”。

<figure>
<a href="assets/figures/02-term-map.svg"><img src="assets/figures/02-term-map.svg" alt="应用依赖向下连接集合语义、通信算法、库调度、传输与驱动、硬件网络；拥塞控制从交换机反馈到发送网卡。"></a>
<figcaption>图 2：职责分层与术语关系。箭头表示职责依赖，不是包头封装顺序；集合语义、算法、库调度、传输驱动与硬件网络之间是层层兑现的关系，拥塞控制则从网络反馈回到发送侧。</figcaption>
</figure>
