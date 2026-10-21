## 15. 从队列积累到 PFC、ECN {#congestion-foundations}

多条链路把数据汇入一条出口时，即使每个发送者都没有超过自己的端口速率，汇总到达率仍可能超过出口服务率。集合通信的同步启动、AlltoAll 的多流和 Reduce 的汇聚都可能制造这种瞬态。RDMA 减少端点开销，却也让发送端更容易高速注入。[3]（§§2–3）

### 队列是速率差的积分

令队列占用 <math><mi>q</mi></math> 为字节，到达率 <math><mi>A</mi></math> 与服务率 <math><mi>C</mi></math> 为字节／秒。在队列为正、没有丢弃的流体近似中：

<math display="block"><mrow><mfrac><mrow><mi>d</mi><mi>q</mi></mrow><mrow><mi>d</mi><mi>t</mi></mrow></mfrac><mo>=</mo><mi>A</mi><mo>−</mo><mi>C</mi></mrow></math>

队列为零且 <math><mrow><mi>A</mi><mo>&lt;</mo><mi>C</mi></mrow></math> 时，占用保持零而非变负。反馈延迟 <math><mi>τ</mi></math> 内若过载量保持为 <math><mrow><mi>A</mi><mo>−</mo><mi>C</mi></mrow></math>，就额外积累约 <math><mrow><mo stretchy="false">(</mo><mi>A</mi><mo>−</mo><mi>C</mi><mo stretchy="false">)</mo><mi>τ</mi></mrow></math> 字节。这是近似的队列平衡，不是完整交换机缓冲模型。

以教学数字说明：8 个 100 Gbit/s 发送者同时汇入 100 Gbit/s 出口，持续 10 微秒的净积累约为 875 kB（按十进制字节），未计帧开销与流量变化。该数字不是论文实验，而是说明缓冲可以在很短时间内被同步突发填满。

<figure>
<a href="assets/figures/31-congestion-signals.svg"><img src="assets/figures/31-congestion-signals.svg" alt="多发送者汇入单出口以及 ECN、PFC 两种反馈"></a>
<figcaption>图 31：多发送者汇入单出口以及 ECN、PFC 两种反馈</figcaption>
</figure>

### Incast、队头阻塞与不公平

Incast 是多个发送者汇聚到同一接收点／出口的流量模式；拥塞还可能发生在任何共享链路，不只在接收机。平均链路利用率不高，也可能因为突发和不均匀映射出现高队列。

PFC（Priority-based Flow Control）在链路上按优先级暂停上游，保护某类流量不因缓冲耗尽而丢弃。它是逐跳反压，不是对每条业务流的端到端公平分配。暂停同优先级队列时，无关流也可能被挡住；反压进一步向上游传播，会把局部热点扩大成拥塞树。循环依赖和复杂拓扑中还可能出现死锁风险。[3]（§2）

无损于是不能推出无拥塞、低延迟或公平。缓冲区保存了尚未服务的数据，排队时延仍在；某些流因为与热点共享优先级而被间接暂停，吞吐也可能不公平。集合通信等待最慢参与者，这种拖尾会放大到整个阶段。

### PFC headroom 与反应距离

发出 Pause 后，上游不会立即停止；传播、处理和已在途数据仍会到达。headroom 必须容纳这部分余量。按单入链路速率 <math><mi>L</mi></math>（字节／秒）、停止生效前延迟 <math><msub><mi>τ</mi><mtext>stop</mtext></msub></math> 的简化估计，需要至少 <math><mrow><mi>L</mi><msub><mi>τ</mi><mtext>stop</mtext></msub></mrow></math> 字节，还要加帧及硬件余量。多入口、共享缓冲及不同长度线缆会改变配置，不能仅用一个端到端 RTT 代替逐跳反应距离。[3]（§4；本篇解释量纲）

### ECN：在丢包之前给出速率信号

ECN（Explicit Congestion Notification）让拥塞节点标记支持 ECN 的包，接收端或传输协议把拥塞反馈给发送者。标记告诉发送者路径有压力，但并不自己降低注入率；必须配合端点控制算法。PFC 的对象是相邻链路／优先级，ECN 的信号能参与端到端速率控制，两者作用时间和范围不同。

DCQCN 的 RoCE 部署让 PFC 作为缓冲保护，ECN／CNP 驱动发送者长期调速。由于标记与暂停在不同缓冲／测量位置生效，两者阈值也不能简单比较成“ECN 的数字必须小于 PFC 的数字”。要对齐入口 headroom、出口排队和共享缓冲的计量口径，才能讨论何者更早触发。[3]（§§3–4）

控制器慢，队列会在反馈返回前溢出；控制器过强或恢复过快，又可能振荡或长期欠利用。下一章解释 DCQCN 如何在这些限制中压缩反馈、减速与恢复，以及原论文的证据覆盖到哪里。
