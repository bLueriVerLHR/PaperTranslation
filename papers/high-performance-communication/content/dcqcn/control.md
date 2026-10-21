### CP、NP、RP 的反馈链

CP（Congestion Point）是交换机拥塞点，按出口队列占用标记数据包；NP（Notification Point）是接收端 NIC，把标记转成 CNP；RP（Reaction Point）是发送端 NIC，用 CNP 更新流的控制状态和发送速率。CNP 不是普通数据的逐包 ACK，也不是相邻交换机的 PFC Pause。

<figure>
<a href="assets/figures/32-dcqcn-loop.svg"><img src="assets/figures/32-dcqcn-loop.svg" alt="DCQCN 数据方向、ECN 标记与 CNP 返回"></a>
<figcaption>图 32：DCQCN 数据方向、ECN 标记与 CNP 返回</figcaption>
</figure>

论文采用 RED 式概率标记。在 <math><mrow><msub><mi>K</mi><mtext>min</mtext></msub><mo>&lt;</mo><msub><mi>K</mi><mtext>max</mtext></msub></mrow></math> 时，队列大小 <math><mi>q</mi></math> 对应的标记概率为：

<math display="block"><mrow><mi>P</mi><mo stretchy="false">(</mo><mi>q</mi><mo stretchy="false">)</mo><mo>=</mo><mo>{</mo><mtable columnalign="left left"><mtr><mtd><mn>0</mn></mtd><mtd><mi>q</mi><mo>≤</mo><msub><mi>K</mi><mtext>min</mtext></msub></mtd></mtr><mtr><mtd><msub><mi>P</mi><mtext>max</mtext></msub><mfrac><mrow><mi>q</mi><mo>−</mo><msub><mi>K</mi><mtext>min</mtext></msub></mrow><mrow><msub><mi>K</mi><mtext>max</mtext></msub><mo>−</mo><msub><mi>K</mi><mtext>min</mtext></msub></mrow></mfrac></mtd><mtd><msub><mi>K</mi><mtext>min</mtext></msub><mo>&lt;</mo><mi>q</mi><mo>≤</mo><msub><mi>K</mi><mtext>max</mtext></msub></mtd></mtr><mtr><mtd><mn>1</mn></mtd><mtd><mi>q</mi><mo>&gt;</mo><msub><mi>K</mi><mtext>max</mtext></msub></mtd></mtr></mtable></mrow></math>

当 <math><msub><mi>P</mi><mtext>max</mtext></msub></math> 小于 1 时，上越 <math><msub><mi>K</mi><mtext>max</mtext></msub></math> 后概率会跳到 1；它不是一直延伸的小斜率直线。令两阈值相同则成为阈值式 cut-off，不能在上面的分母为零时直接代入计算。[3]（图 5、式 5）

NP 首次收到需要反馈的标记时可立即发 CNP，随后按每流窗口限制生成频率：论文部署每 50 微秒最多一个，有标记才反馈。这样降低 NIC 处理开销，但把窗口中一个标记和很多标记压成同一种“有拥塞”信号。[3]（§3.1、图 6）反向 CNP 采用高优先级以减少反馈延误；不需要精确 RTT 测量不代表反馈延迟无影响。

### 减速状态：目标速率不是立即发送速率

RP 保存当前速率 <math><msub><mi>R</mi><mi>C</mi></msub></math>、目标速率 <math><msub><mi>R</mi><mi>T</mi></msub></math> 与拥塞系数 <math><mi>α</mi></math>。本章的 <math><mi>α</mi></math> 无量纲，取值在 0 到 1；它与第 9 章单位为秒的消息启动 <math><mi>α</mi></math> 不同。<math><mi>g</mi></math> 是无量纲平滑权重。

收到 CNP 时，按论文式 1 的顺序保存减速前的目标、降低当前速率，再加强拥塞记忆：

<math display="block"><mtable columnalign="right left"><mtr><mtd><msub><mi>R</mi><mi>T</mi></msub></mtd><mtd><mo>←</mo><msub><mi>R</mi><mi>C</mi></msub></mtd></mtr><mtr><mtd><msub><mi>R</mi><mi>C</mi></msub></mtd><mtd><mo>←</mo><msub><mi>R</mi><mi>C</mi></msub><mo>(</mo><mn>1</mn><mo>−</mo><mfrac><mi>α</mi><mn>2</mn></mfrac><mo>)</mo></mtd></mtr><mtr><mtd><mi>α</mi></mtd><mtd><mo>←</mo><mo stretchy="false">(</mo><mn>1</mn><mo>−</mo><mi>g</mi><mo stretchy="false">)</mo><mi>α</mi><mo>+</mo><mi>g</mi></mtd></mtr></mtable></math>

这里减速使用更新前的 <math><mi>α</mi></math>。初值为 1，所以第一次反馈可把当前速率减半；若初始 40 Gbit/s，就是 20 Gbit/s，而目标仍记为 40 Gbit/s。其他主机流和本地 QoS 可以限制实际起始速率，不能普遍假定所有新流都获得整个端口。

未收到反馈的更新间隔中，<math><mrow><mi>α</mi><mo>←</mo><mo stretchy="false">(</mo><mn>1</mn><mo>−</mo><mi>g</mi><mo stretchy="false">)</mo><mi>α</mi></mrow></math>，拥塞记忆逐渐衰减。连续 <math><mi>m</mi></math> 个这样的更新后，<math><mrow><msub><mi>α</mi><mi>m</mi></msub><mo>=</mo><msup><mrow><mo stretchy="false">(</mo><mn>1</mn><mo>−</mo><mi>g</mi><mo stretchy="false">)</mo></mrow><mi>m</mi></msup><msub><mi>α</mi><mn>0</mn></msub></mrow></math>。较小 <math><mi>g</mi></math> 保留更长记忆，能减少激进变化，也可能放慢适应；它不是“越小越正确”。论文 α 更新间隔为 55 微秒，略大于 NP 的 50 微秒窗口，以避免尚等下一次 CNP 时过早判断无拥塞。[3]（§§3.1、5.2）

### 恢复：两种触发源与三种阶段

速率增加既由时间触发，也由已发送字节触发。字节计数器每累计 <math><mi>B</mi></math> 字节产生事件，timer 每 <math><mi>T</mi></math> 时间产生事件。只用字节触发会让高速流更快积累恢复次数，低速流恢复缓慢；timer 为低速流提供独立于吞吐的恢复机会。[3]（§3.1）

快速恢复固定目标，让当前速率向它靠近：

<math display="block"><mrow><msub><mi>R</mi><mi>C</mi></msub><mo>←</mo><mfrac><mrow><msub><mi>R</mi><mi>T</mi></msub><mo>+</mo><msub><mi>R</mi><mi>C</mi></msub></mrow><mn>2</mn></mfrac></mrow></math>

若目标不变且期间没有新 CNP，每次目标差值减半。前例从 20 向 40 Gbit/s 恢复，依次为 30、35、37.5 等；五次后为 39.375。这是对更新式的算例，不是 NIC 吞吐曲线。快速恢复并不立即探测高于旧目标的额外带宽。

加性增加阶段先更新 <math><mrow><msub><mi>R</mi><mi>T</mi></msub><mo>←</mo><msub><mi>R</mi><mi>T</mi></msub><mo>+</mo><msub><mi>R</mi><mtext>AI</mtext></msub></mrow></math>，再执行上述平均。目标因而逐步探索新容量，当前速率平滑跟随。论文还有 hyper increase 加速探测阶段，其具体斜率交由 QCN 规范／实现说明，而非论文式 1–4 完整定义。[3]（§3.1）

<figure>
<a href="assets/figures/33-dcqcn-recovery.svg"><img src="assets/figures/33-dcqcn-recovery.svg" alt="减速和三类恢复阶段的状态关系"></a>
<figcaption>图 33：减速和三类恢复阶段的状态关系</figcaption>
</figure>

图按论文图 7 的门限关系整理：用 <math><mi>u</mi></math> 表示自最近减速以来的 timer 事件次数，<math><mi>v</mi></math> 表示 byte 事件次数，阈值为 <math><mi>F</mi></math>。若 <math><mrow><mi>max</mi><mo stretchy="false">(</mo><mi>u</mi><mo>,</mo><mi>v</mi><mo stretchy="false">)</mo><mo>&lt;</mo><mi>F</mi></mrow></math> 则快速恢复；若 <math><mrow><mi>min</mi><mo stretchy="false">(</mo><mi>u</mi><mo>,</mo><mi>v</mi><mo stretchy="false">)</mo><mo>&gt;</mo><mi>F</mi></mrow></math> 则 hyper increase；中间区域是加性增加。新 CNP 导致减速并重置相关计时／计数。论文正文用 <math><mrow><mi>F</mi><mo>=</mo><mn>5</mn></mrow></math> 概括快速恢复长度，但图中是两计数器判定，不等于简单“每收到五个包换阶段”。

### 不采用慢启动的收益与风险

无其他本地流时，论文让新流以线速启动，减少空网络中小传输的爬升时间。同步 incast 下，同一决定也会制造大突发：ECN 的端到端反馈尚未回来，发送者仍高速注入。因此其部署保留 PFC 保护在途数据，并用 DCQCN 避免长期反压。关闭 PFC 是否仍可行，要取决于其他丢包处理和控制设计；不能由 DCQCN 的名字自动保证。[3]（§§3.3、6.2）
