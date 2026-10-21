## 7. 有根集合算子：复制、分发、汇集与归约 {#rooted-collectives}

本章用 root=0、三个 rank 描述四个基础算子。设每个小块有 b 个元素，类型和块内布局已约定。集合操作需要参与者在同一通信域上形成相匹配的调用；不同 API 对 count 的含义有所区别。NCCL 的类型与计数规则不能简单替换成 MPI 的派生类型和类型签名规则。[4][5][15]

设通信域有 p 个 rank，编号为 0 到 p−1。rank 是通信域内的逻辑身份；一个进程可以控制一个或多个设备，一个主机可以包含多个 rank。root 是某个 rank，不是自动取 GPU 的物理编号。改变 rank 与设备的映射，一方面改变 Scatter、Gather 等算子的块位置，另一方面也改变逻辑通信边在真实拓扑上的路径。[4]

本篇图示采用少量 rank 以展示语义。算子的“操作后”只表示规定的接收结果，不表示原来的输入缓冲被擦除。箭头若表示实际调度，会另外注明算法和轮次。在 Reduce 的语义图里把输入画到 root，并不能据此认定实现一定让 root 接收所有原始数据。

### 7.1 Broadcast：同一份数据的复制 {#operator-broadcast}

Broadcast 的输入是 root 上长度为 b 的向量 x，输出是每个 rank 上的同一向量。它不划分工作，不合并各 rank 的输入，也不为每个目的地生成不同数据。

<math xmlns="http://www.w3.org/1998/Math/MathML" display="block"><mrow><msub><mi>y</mi><mi>i</mi></msub><mo>=</mo><msub><mi>x</mi><mi>r</mi></msub><mo>,</mo><mspace width="1em"/><mn>0</mn><mo>≤</mo><mi>i</mi><mo>&lt;</mo><mi>p</mi></mrow></math>

<figure><a href="assets/figures/11-broadcast.svg"><img src="assets/figures/11-broadcast.svg" alt="root 0 输入 A，操作后 rank 0、1、2 的接收结果均为 A。"></a><figcaption>图 11：Broadcast。所有接收块相同；图示不限定 root 直接逐个发送还是采用树形转发。</figcaption></figure>

例如，模型初始化参数由某个 rank 生成，其他副本需要相同起点，就可以用 Broadcast 传播参数。若 root 逐个发送，会在单个出口重复注入数据；树形算法让已收到数据的 rank 继续转发，减少传播轮次。但算子本身只承诺结果相同，不承诺具体轮数或物理链路流量。NCCL 2.28.3 的 `ncclBroadcast` 中 count 是每个 rank 接收的元素数，root 的 send buffer 才是有效输入。[5]

### 7.2 Scatter：把不同块分给不同参与者 {#operator-scatter}

root 持有按 rank 顺序排列的 p 个块 `[x₀ | x₁ | … | xₚ₋₁]`，每块 b 个元素。Scatter 的输出是在 rank i 上得到 xᵢ；root 自己也得到属于它的那块。root 的总输入是 pb，而不是 b。

<figure><a href="assets/figures/12-scatter.svg"><img src="assets/figures/12-scatter.svg" alt="root 0 输入 A、B、C 三块，rank 0、1、2 的接收结果分别为 A、B、C。"></a><figcaption>图 12：Scatter。分发遵循目的 rank，和 Broadcast 的“每人一份全量副本”不同。</figcaption></figure>

若 A、B、C 是不同数据批次，Scatter 能使各 rank 只获得自己的批次。用 Broadcast 先复制全部批次再在本地挑选，也可能生成相同有效输入，但会额外占用接收容量和通信资源；这不是 Scatter 的等成本实现。另一方面，实际训练常由每个 rank 自行读取分片数据，不必真的把全部训练样本先放到 root。算子的教学用途与框架实际输入流水线应分开。

在 `ncclScatter` 中，count=b，root 至少提供 pb 个元素，非 root 的发送指针不作为输入。[5] MPI_Scatter 的发送计数也是**给每个目的地**的数量，而不是根缓冲的总元素数；不过 MPI 还允许以类型签名描述布局，这不意味着 NCCL 也有相同类型系统。[15]

### 7.3 Gather：保留各块，按 rank 汇集 {#operator-gather}

每个 rank i 输入 xᵢ，root 接收按 rank 顺序的拼接结果。它不对相同位置的数字做运算。

<math xmlns="http://www.w3.org/1998/Math/MathML" display="block"><mrow><msub><mi>y</mi><mi>r</mi></msub><mo>=</mo><mo stretchy="false">[</mo><msub><mi>x</mi><mn>0</mn></msub><mo>|</mo><msub><mi>x</mi><mn>1</mn></msub><mo>|</mo><mo>⋯</mo><mo>|</mo><msub><mi>x</mi><mrow><mi>p</mi><mo>−</mo><mn>1</mn></mrow></msub><mo stretchy="false">]</mo></mrow></math>

<figure><a href="assets/figures/13-gather.svg"><img src="assets/figures/13-gather.svg" alt="rank 0、1、2 分别输入 A、B、C，root 0 接收按 rank 拼接的 A、B、C，其他 rank 没有规定接收结果。"></a><figcaption>图 13：Gather。root 的接收容量随参与者数量增长，其他 rank 不获得汇集结果。</figcaption></figure>

例如，三个 rank 各输出两条预测，Gather 后 root 得到六条按 rank 分组的预测。若先对预测相加，就会丢掉逐样本身份，变成另一个问题。Gather 的“先后顺序”指最终布局按 rank 排列，不要求报文在网络上按这个顺序到达。接收侧可以把不同来源直接放入不同偏移位置。

Scatter 和 Gather 在**布局意义**上相反，但不互为任意程序状态的逆操作：谁拥有缓冲、是否别名、其他 rank 原有数据是否保留，都不是这个口头关系所完整描述的内容。`ncclGather` 的 count=b，root 的接收空间至少为 pb 个元素。[5]

### 7.4 Reduce：按相同位置合并 {#operator-reduce}

设每个 rank 输入长度为 b 的向量 xᵢ，归约运算为 ⊕。Reduce 把相同位置的值合并，只在 root 的接收缓冲留下长度为 b 的结果。

<math xmlns="http://www.w3.org/1998/Math/MathML" display="block"><mrow><msub><mi>y</mi><mi>r</mi></msub><mo stretchy="false">[</mo><mi>k</mi><mo stretchy="false">]</mo><mo>=</mo><munderover><mo>⨁</mo><mrow><mi>i</mi><mo>=</mo><mn>0</mn></mrow><mrow><mi>p</mi><mo>−</mo><mn>1</mn></mrow></munderover><msub><mi>x</mi><mi>i</mi></msub><mo stretchy="false">[</mo><mi>k</mi><mo stretchy="false">]</mo><mo>,</mo><mspace width="1em"/><mn>0</mn><mo>≤</mo><mi>k</mi><mo>&lt;</mo><mi>b</mi><mspace width="1em"/><mtext>（归约覆盖全部 p 个 rank）</mtext></mrow></math>

<figure><a href="assets/figures/14-reduce.svg"><img src="assets/figures/14-reduce.svg" alt="rank 0 输入一和十，rank 1 输入二和二十，rank 2 输入三和三十；求和 Reduce 后 root 得到六和六十。"></a><figcaption>图 14：求和 Reduce。三份两元素输入生成一份两元素结果，而不是六元素拼接。</figcaption></figure>

求和、最小值、最大值都是常见归约。归约可以在中间节点先合并，root 不必接收每份原始数据：这正是它和 Gather 在通信组织上的重要区别。运算允许怎样重排则受代数性质和 API 支持约束。结合律允许改变括号；交换律还允许改变参与者顺序。非交换但结合的运算不能随意套用会重排来源的算法。

浮点加法在实际舍入运算下不满足严格结合律。以足够大的正数、其相反数和一个小数为例，先抵消大数与先把小数加到大数，可能得到不同结果。因此，数学上的“等价归约”不自动意味着不同环、树或分层方案产生位级相同结果。NCCL 的预定义运算、数据类型和缩放接口也不等同于“任意用户函数都可作为归约”。[4][5]

### 7.5 四个算子的容量区别

| 算子 | 有效输入 | 规定接收结果 | 是否按元素合并 |
|---|---|---|---|
| Broadcast | root：b | 每个 rank：b，同一块 | 否 |
| Scatter | root：pb | 每个 rank：b，不同块 | 否 |
| Gather | 每个 rank：b | root：pb，按 rank 拼接 | 否 |
| Reduce | 每个 rank：b | root：b，按位置归约 | 是 |

这些数字是**有效元素容量**，不是实际显存分配量，也不是线上报文字节数。类型宽度把元素数转换成有效载荷字节；临时空间、对齐、协议头、转发和流水线缓冲，还会进一步改变存储与通信成本。
