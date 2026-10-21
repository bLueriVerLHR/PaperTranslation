#### 连接生命周期与可靠传输 {#interview-network-transport}

<article class="qa-item" id="qa-handshake" data-level="basic" markdown="1">
<p class="qa-question">Q134 · 三次握手在确认什么？两次通信为什么通常不够？</p>
<div class="qa-answer" markdown="1">

三次握手交换并确认双方的初始序号，使两个方向进入可以传输的连接状态。第二条报文把服务端对客户端 SYN 的确认与自己的 SYN 合并；第三条 ACK 则把服务端尚未得到的确认送回去。它不是对双方“收发能力”的永久体检，也不是身份认证。[25]（§3.4.1、§3.5）

以没有携带应用数据的典型主动打开为例，初始序号为 x、y：

| 步骤 | 报文 | 主要状态推进 |
|---|---|---|
| 1 | 客户端 `SYN, seq=x` | 客户端进入 SYN_SENT；服务端从 LISTEN 接收打开请求 |
| 2 | 服务端 `SYN+ACK, seq=y, ack=x+1` | 服务端处于 SYN_RECEIVED，等待自己 SYN 的确认 |
| 3 | 客户端 `ACK, seq=x+1, ack=y+1` | 客户端接受有效 SYN+ACK 后进入 ESTABLISHED；服务端收到有效 ACK 后进入 ESTABLISHED |

SYN 占用一个序号位置。第一条 SYN 也可能是旧连接残留报文，被动端不能仅凭它确认对方此刻确实参与新的打开；握手通过后续确认与序号检查处理这一歧义。只保留前两条，服务端仍未收到对自身初始序号的有效确认，两端进入状态的依据就不完整。[25]

即使假设链路绝不丢包、重排或残留旧请求，删掉第三条仍不符合现有 TCP 的状态机。若另外规定送达保证和不同的建立规则，那是在设计另一种协议，不能据此说 TCP 已允许两次握手。反过来，握手完成也不保证连接以后不会失效。

三次握手不自动抵御 SYN flood：资源恰可能在等待第三条时被消耗，防护须另行讨论半连接状态、SYN cookies 和容量。重传、同时打开、扩展及携带数据等情况会改变实际包数；TCP 建立与后续 TLS 握手也承担不同职责。[25,88]

</div>
</article>

<article class="qa-item" id="qa-close-states" data-level="basic" markdown="1">
<p class="qa-question">Q135 · 四次挥手、TIME_WAIT 与 CLOSE_WAIT 分别意味着什么？</p>
<div class="qa-answer" markdown="1">

TCP 的两个发送方向可以独立结束。FIN 表示该方向没有更多字节，不要求接收方立即结束自己的发送；因此确认对方 FIN 和发送自身 FIN 往往分开，形成常说的“四次挥手”。ACK 与 FIN 也可能合并，四个独立报文不是强制包数。[25]（§3.6）

在没有同时关闭、且 ACK 与 FIN 分开发送的典型路径中：

| 阶段 | 主动关闭方 | 被动关闭方 |
|---|---|---|
| 主动方发送 FIN | 进入 FIN_WAIT_1 | 收到 FIN、回复 ACK，进入 CLOSE_WAIT |
| 主动方收到相应 ACK | 进入 FIN_WAIT_2，等待对方结束发送 | 仍可发送剩余数据，等待本地应用关闭发送方向 |
| 被动方发送 FIN | 收到 FIN、回复最后 ACK，进入 TIME_WAIT | 进入 LAST_ACK，等待自身 FIN 的确认 |
| 最后 ACK 被接收 | 保留 TIME_WAIT 状态至相应规则允许结束 | 完成关闭 |

FIN 和 SYN 一样占用一个序号位置；确认 FIN 的 ACK 必须越过该位置。半关闭允许一方向已经结束而另一方向继续传输，不等于连接上的任务和缓冲都已释放。[25]

TIME_WAIT 保留状态，使最后 ACK 丢失后仍能应答对方重传的 FIN，并降低旧连接报文与后续连接混淆的风险。协议使用 2MSL 等等待规则，不能把某个内核的实际秒数当作所有系统的固定值。先发 FIN 的端点也不在所有路径中独占 TIME_WAIT：同时关闭会产生不同状态推进。缩短等待或套用复用选项不是无条件安全的清理方法。[25]（§3.3.2、§3.6）

CLOSE_WAIT 则表示已经收到对端 FIN，本地发送方向尚未完成关闭。持续大量积累时，应检查处理 EOF 的路径、描述符所有权、仍持有连接的任务和输出队列；它不是靠缩短 TIME_WAIT 就能修复的问题。连接状态只说明传输协议进展，不说明业务请求成功，也不自动取消应用定时器或依赖任务。

</div>
</article>

<article class="qa-item" id="qa-tcp-state-machine" data-level="principle" markdown="1">
<p class="qa-question">Q136 · TCP 状态机里那么多状态各代表什么？半关闭和同时关闭为什么需要额外状态？</p>
<div class="qa-answer" markdown="1">

RFC 9293 给出的连接状态包括 CLOSED、LISTEN、SYN-SENT、SYN-RECEIVED、ESTABLISHED、FIN-WAIT-1、FIN-WAIT-2、CLOSE-WAIT、CLOSING、LAST-ACK 和 TIME-WAIT。[25,372] 它们不是实现细节，而是把“本端是否已发送 FIN”“是否已收到对方的 FIN”“是否已确认”三件事组合起来的结果：FIN-WAIT-1 表示本端已发 FIN 等确认，FIN-WAIT-2 表示确认已收到、只等对方的 FIN，CLOSE-WAIT 表示收到对方 FIN 而本端还没关闭，LAST-ACK 表示被动方也发了 FIN 只等确认。

半关闭是这些状态存在的原因之一：TCP 的两个方向独立关闭，一端可以发完数据发 FIN 而继续接收对方数据，这也让“对方已关闭”和“连接不可用”需要分别判断。[25] 同时关闭时双方都处于 FIN-WAIT-1 并各收到对方的 FIN，此时进入 CLOSING 而不是直接进入 TIME-WAIT，直到双方的 FIN 都被确认。

TIME-WAIT 的作用是限制连接复用：旧连接残留在网络中的报文可能与新连接的重叠，等待两倍报文最大生存时间让旧报文消散，同时保证最后的 ACK 丢失时还能重传。[25] 因此 CLOSE-WAIT 堆积通常是应用没有关闭连接（代码或框架问题），TIME-WAIT 堆积则是主动关闭方正常回收的代价，两者的处理方向相反。

</div>
</article>

<article class="qa-item" id="qa-tcp-reliability" data-level="principle" markdown="1">
<p class="qa-question">Q137 · TCP 怎样保证可靠传输？ARQ、序号、确认、重传计时器及 MSS 分别起什么作用？</p>
<div class="qa-answer" markdown="1">

TCP 以字节序号识别位置，以确认报告进展，保留未确认数据并在需要时重传；接收端利用序号处理重复与乱序，交给应用的仍是有序字节流。校验和帮助检测传输差错，但不提供恶意篡改防护。可靠意味着协议尝试恢复缺失并保持交付语义，不意味着所有连接最终必定成功。[25]

ARQ 是确认与重传相结合的恢复思路。停等只让一份数据等待确认，滑动窗口允许多份数据在途，从而利用等待期间的链路能力；Go-Back-N 和选择重传分别代表从缺口重传后续数据、或选择缺失部分等教学组织。TCP 使用字节流与累积确认，并可借助 SACK 报告非连续接收区间，不能完全等同于某个固定分组的教学模型。[25,79]

例如当前下一期待字节是 1000，接收端随后连续收到序号 1000–1499 的字节，就可以把累积确认推进到 `ACK=1500`。若 1500–1999 缺失而 2000–2499 已到达，累积确认仍停在 1500；额外接收信息可以帮助发送方识别缺口。重复 ACK 可能提示缺失，也可能来自重排；恢复算法必须结合状态，而不是见一个重复确认就立即断言丢包。[25,79]

RTO 不是固定 RTT。RFC 6298 根据有效 RTT 样本维护平滑值 SRTT 和波动估计 RTTVAR，G 表示计时粒度，基本计算是：

<math xmlns="http://www.w3.org/1998/Math/MathML" display="block"><mrow><mi mathvariant="normal">RTO</mi><mo>=</mo><mi mathvariant="normal">SRTT</mi><mo>+</mo><mi mathvariant="normal">max</mi><mo stretchy="false">(</mo><mi>G</mi><mo>,</mo><mn>4</mn><mo>·</mo><mi mathvariant="normal">RTTVAR</mi><mo stretchy="false">)</mo></mrow></math>

标准还规定初始化、更新和相应下限等规则，因此这个表达式不是某个内核的完整计时配置。Karn 取样原则避免把重传后无法判断归属的 ACK 用作普通 RTT 样本，时间戳能在相应条件下消除歧义。定时器不是为每个字节各开一个：尚有未确认数据时维护重传计时，推进确认后按规则重启；到期重传最早未确认段并增大 RTO。快速重传等恢复则可能先于超时发生。[80]

MSS 限制相应 TCP 数据部分，MTU 约束链路或路径上的 IP 分组大小。TCP 选项、IP 头和路径变化都会占用空间，不能直接令 MSS 等于 MTU，也不能据 MSS 断言所有段大小相同。[25] 写调用成功、TCP ACK、应用读取和业务提交仍是不同事件；连接失败后重试业务，可靠字节流本身不能防止重复执行。

</div>
</article>

<article class="qa-item" id="qa-tcp-flow-control" data-level="principle" markdown="1">
<p class="qa-question">Q138 · 滑动窗口、接收窗口和拥塞窗口有什么区别？零窗口时为什么还需要探测？</p>
<div class="qa-answer" markdown="1">

滑动窗口是按序号描述可发送／可接收范围，并随确认推进边界的机制；`rwnd` 是接收端通告的窗口，保护接收缓冲；`cwnd` 是发送端拥塞控制维护的约束，限制网络在途负荷。流量控制和拥塞控制的反馈对象不同，不能把两个窗口相加，也不能把拥塞窗口当作接收端写进 TCP 头的字段。[25,79]

在窗口以字节计、以同一确认边界为基准的简化发送模型中，FlightSize 表示已发送但尚未确认的数据量，新发送额度近似为：

<math xmlns="http://www.w3.org/1998/Math/MathML" display="block"><mrow><mi mathvariant="normal">额度</mi><mo>=</mo><mi mathvariant="normal">max</mi><mo stretchy="false">(</mo><mn>0</mn><mo>,</mo><mi mathvariant="normal">min</mi><mo stretchy="false">(</mo><mi mathvariant="normal">rwnd</mi><mo>,</mo><mi mathvariant="normal">cwnd</mi><mo stretchy="false">)</mo><mo>−</mo><mi mathvariant="normal">FlightSize</mi><mo stretchy="false">)</mo></mrow></math>

这个表达式说明共同约束和已用额度，不代替重传恢复、SACK 记账或 pacing 的完整规则。即使窗口允许，应用没有数据或其他发送条件未满足时，也不会自动发满。例如 `rwnd=20 KiB`、`cwnd=12 KiB`、在途 8 KiB 时，简化额度为 4 KiB，而不是 32 KiB。

接收应用读取慢，缓冲余量减少，窗口可能缩为零。零窗口不表示连接已死亡；应用后来读走数据并通告新窗口时，更新报文也可能丢失，双方若一直等待便无法推进。零窗口探测让发送方重新获得窗口信息，不是绕过接收能力的大量发送许可，也不等于对业务服务的健康检查。[25]

窗口缩放扩大窗口字段能表达的范围，不凭空增加缓冲或处理速度。对于没有其他瓶颈、窗口持续受限的理想稳态，窗口量与 RTT 可以帮助解释吞吐约束；实际丢包、拥塞算法、应用供数、排队和背压都会改变结果。“窗口越大越快”不是无条件规律。

</div>
</article>

<article class="qa-item" id="qa-tcp-congestion" data-level="principle" markdown="1">
<p class="qa-question">Q139 · 慢启动、拥塞避免、快速重传与快速恢复怎样工作？所有 TCP 都遵循同一增长曲线吗？</p>
<div class="qa-answer" markdown="1">

慢启动、拥塞避免、快速重传和快速恢复是经典 TCP 拥塞处理的相关机制，不是“发送方太快就直接减半”的一个动作。以 RFC 5681 的 Reno 式规则为例，`cwnd` 控制发送方在途负荷，`ssthresh` 区分慢启动和拥塞避免，SMSS 表示发送方最大段的数据大小。[79]

| 阶段／事件 | 经典处理 | 解释与条件 |
|---|---|---|
| 慢启动 | 对确认新数据的 ACK 增加 `cwnd`，每次增量不超过一个 SMSS | 在持续供数、确认节奏合适时，每 RTT 可近似倍增；不是每个 ACK 都把整个窗口翻倍 |
| 拥塞避免 | 一个 RTT 内的增量不超过一个 SMSS，按确认逐步累计 | 近似线性增长来自每段 ACK 的小增量，不保证每条连接实际呈同一曲线 |
| 达到三次重复 ACK 等快速重传条件 | 重传推断缺失的段，进入相应快速恢复 | 还须符合重复 ACK 定义及算法状态，不能把任意三个报文当作触发依据 |
| 重传计时器到期 | 更保守地收缩窗口，并让 RTO 退避 | 超时和快速恢复不是同一条窗口恢复路径 |

在第三次重复 ACK 触发的恢复，或某段首次由重传定时器重传的路径中，阈值依据实际未确认量 FlightSize，而不是盲目使用 `cwnd`；RFC 5681 要求新的 `ssthresh` 不高于 `max(FlightSize/2, 2·SMSS)`，其中有限发送额外发出的数据还有排除规则。快速恢复可以暂以 `ssthresh+3·SMSS` 表达重复 ACK 所提示的网络进展，后续确认再推进恢复并收缩到阈值。超时路径把 `cwnd` 降到不超过一个满尺寸段，再从较低窗口启动；同一段已经被定时器重传后再次超时，则保持 `ssthresh`，不能每次重新套用减半公式。[79]

因此“丢包时窗口总是减半、然后继续线性增加”会遗漏超时、重复重传和恢复状态；重复 ACK 也可能来自重排而不是真实丢失。慢启动的“慢”是相对于一开始就注入大量数据，并不是说它比拥塞避免增长更慢。延迟 ACK、应用供数不足和具体字节计数都会改变按 RTT 绘出的增长。[79–80]

这些规则有明确算法范围。现代控制器的信号、增长函数和恢复配合并不都等同于 Reno；仅看到 TCP 协议名称，不能推出当前算法、起始窗口或吞吐。窗口演变是协议分析，不是对某条链路的性能测量。

</div>
</article>

<article class="qa-item" id="qa-nagle-delayed-ack" data-level="principle" markdown="1">
<p class="qa-question">Q140 · Nagle 算法与延迟确认为什么会互相拖慢？什么时候该关掉它？</p>
<div class="qa-answer" markdown="1">

Nagle 算法限制未被确认的小报文数量：当连接上还有未确认数据时，发送方把小数据积攒起来，凑到足够大或等到收到确认再发，目的是避免大量微小报文放大网络与处理开销。[359,372] 延迟确认是接收方的优化：不要求对每个数据段立即回 ACK，可以等待一小段时间，把确认与反向数据捎带出去。[360]

两者相遇会形成互相等待：发送方在等 ACK 才发下一段小数据，接收方在等更多数据或超时才发 ACK，于是小报文被推迟一个延迟确认周期；逐次写小包的请求—响应式服务（例如带小请求的 RPC 或交互协议）就可能出现几十毫秒级的附加延迟。它不是协议错误，而是两个独立优化叠加的结果。[359,360]

处理方式要看场景：需要低延迟的小报文交互，可以关闭 Nagle（Linux 用 `TCP_NODELAY` 设置 `IPPROTO_TCP` 选项），或由应用自己缓冲、合并写入；批量传输或把多个小消息合成一个报文时保留 Nagle 反而有益。[361] 注意 `TCP_NODELAY` 与其它选项的组合行为以及在非 Linux 平台的可移植性，都不能假设备一致；也不要把它当作解决“为什么一次 send 对应很多小包”的通用答案，先看应用层是否逐条写入。

</div>
</article>
