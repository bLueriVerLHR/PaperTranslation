## 术语对应表

本篇中文用语与英文术语如下。标准库类名与 API 保持原样，便于对应固定版本源码。

| 英文 | 本篇用语 | 范围与区别 |
|---|---|---|
| backend service | 后端服务 | 处理请求、资源与业务状态，不专指编译器后端 |
| thread pool | 线程池 | 复用工作线程执行任务 |
| task / worker | 任务／工作线程 | 任务是工作单元，worker 是执行者 |
| enqueue / dequeue | 入队／出队 | 转移排队中的任务，不表示已完成 |
| mutex / critical section | 互斥量／临界区 | 保护共享状态及不变量 |
| condition variable | 条件变量 | 配合锁与谓词等待状态变化 |
| predicate / spurious wakeup | 谓词／虚假唤醒 | 条件检查／无对应条件变化的唤醒 |
| future / promise | future／promise | 消费端结果句柄／生产端结果通道 |
| move-only | 仅可移动 | 可以转移所有权，不允许复制 |
| lifetime / ownership | 生命周期／所有权 | 对象何时有效／谁负责持有与释放 |
| RAII | RAII（资源获取即初始化） | 将资源释放接到对象销毁，仍须满足依赖顺序 |
| deadlock | 死锁 | 互相等待或等待无法取得的执行资源 |
| drain / purge | 排空／清除排队任务 | 完成已接收工作／丢弃尚未运行工作 |
| pause / cancellation | 暂停取任务／取消 | 本案例 pause 不终止正在运行的任务 |
| backpressure / admission control | 背压／准入控制 | 调节上游产生速度／限制接收工作 |
| concurrency / parallelism | 并发／并行 | 任务交错推进／同时执行 |
| throughput / tail latency | 吞吐／尾时延 | 完成速率／延迟分布高分位 |
| work stealing | 工作窃取 | 分散任务队列并转移负载；本案例不是此结构 |
| value category / forwarding reference | 值类别／转发引用 | 描述表达式行为／推导上下文中的参数绑定机制 |
| control block / weak ownership | 控制块／弱观察 | 共享所有权状态／不增加强引用计数的观察句柄 |
| happens-before / data race | 先行发生／数据竞争 | 语言层顺序关系／满足相应条件的冲突访问 |
| release / acquire / relaxed | 发布／获取／宽松内存序 | 具体同步条件与原子性范围不同 |
| coroutine frame | 协程帧 | 保留跨暂停点的状态，不等同于独立原生线程栈 |
| virtual memory / TLB | 虚拟内存／地址转换缓存 | 地址映射与权限／部分转换结果的缓存 |
| page fault / copy-on-write | 缺页异常／写时复制 | 需要内核处理的页面访问／写入时建立私有副本 |
| readiness / completion | 就绪／完成 | 当前操作可能推进／相应操作已经结束 |
| level-triggered / edge-triggered | 水平触发／边缘触发（LT／ET） | I/O 就绪事件的不同通知组织方式 |
| framing / byte stream | 分帧／字节流 | 应用消息边界协议／不保留调用边界的有序字节序列 |
| idempotency / TLS | 幂等／传输层安全 | 重复请求的预期业务效果／通道认证、机密性与完整性 |
| clustered / secondary index | 聚簇／二级索引 | InnoDB 行数据组织／关联主键定位的其他索引 |
| MVCC / read view | 多版本并发控制／读视图 | 版本选择机制／一致性读的可见性边界 |
| redo / undo / binlog | 重做日志／撤销日志／二进制日志 | 恢复修改／撤销与历史版本／服务层变更事件 |
| next-key lock / gap lock | 临键锁／间隙锁 | 索引记录加前方间隙／限制区间插入 |
| expiry / eviction | 过期／淘汰 | 有效期语义／容量压力下的候选删除 |
| cache-aside / negative cache | 旁路缓存／负缓存 | 事实来源与缓存分离的访问模式／不存在结果的暂存 |
| cache penetration / breakdown / avalanche | 缓存穿透／击穿／雪崩 | 不存在请求回源／热点失效／集中失效或整体故障 |
| fencing token / hash slot | 防护序号／哈希槽 | 受保护资源拒绝旧持有者的依据／Redis Cluster 分片单位 |
| amortized / worst-case complexity | 均摊／最坏复杂度 | 一系列操作的平均界／单次最不利情形的界 |
| Bloom filter / false positive | 布隆过滤器／误判存在 | 概率集合判定／不存在元素被判断为可能存在 |
| topological ordering / DAG | 拓扑序／有向无环图 | 满足有向依赖的排序／无有向环的图 |
| BST / black height | 二叉搜索树／黑高 | 键序不变量／路径上的黑节点计数，约定计数端点 |
| skip list / trie | 跳表／字典树 | 分层有序链接／按符号路径共享前缀 |
| stable sort / in-place | 稳定排序／原地处理 | 等价键相对顺序保持／复用元素存储，不自动排除递归栈 |
| relaxation / negative cycle | 松弛／负环 | 经候选路径改进距离／权重总和为负的环 |
| Eulerian trail / circuit | 欧拉通路／欧拉回路 | 每边恰用一次／同时闭合，不限制每顶点只访问一次 |
| dynamic programming / backtracking | 动态规划／回溯 | 重用状态结果／探索并撤销选择 |
| border / prefix function | 前后缀边界／前缀函数 | 相等的真前缀与后缀／各前缀的最长边界长度 |
| external sort / bitmap | 外部排序／位图 | 内存外有序段及归并／按值域位置表达集合 |
| shuffle / combiner | 分组传输／本地合并 | 中间记录按键路由与归并／可选的局部聚合 |
| prefix-free code / lossless | 前缀码／无损 | 没有码字是另一码字前缀／可恢复原符号序列 |
| intset / span | 整数集合／跨度 | Redis 紧凑整数数组／跳表链接跨过的节点数，均受版本约束 |
| LSM / memtable / SSTable | 日志结构合并树／内存表／有序字符串表 | 更新、刷盘和合并的结构，不混同事务日志 |
| WAL / compaction | 预写日志／合并整理 | 更新恢复依据／合并有序版本；策略与持久性配置分开 |
| read / write / space amplification | 读／写／空间放大 | 额外查询、物理写入与占用，各自对齐逻辑口径 |
| prerequisite / phony | 前置依赖／伪目标 | 构建依赖关系／操作名称，后者不是同名产物 |
| core dump / debug symbols | 内存转储／调试符号 | 部分进程现场／机器地址与源码映射，必须匹配实际构建 |
| PMU / sampling / multiplexing | 性能监控单元／采样／多路复用 | 硬件事件资源／事件样本／共享有限计数器 |
| working tree / index / commit | 工作树／暂存区／提交 | 当前文件／下次快照准备状态／已记录历史 |
| authentication / authorization | 认证／授权 | 确认身份／允许相应动作，不是同一保证 |
| small string optimization (SSO) | 小字符串优化 | 短串存在对象内部缓冲；容量与布局由实现决定，不是标准要求 |
| string view | 字符串视图 | 只保存指针与长度的非拥有视图，有效性由调用方保证 |
| one definition rule (ODR) | 单一定义规则 | 每个翻译单元至多一个定义；inline、模板等实体允许跨翻译单元重复定义但须一致 |
| name mangling / ABI | 名称修饰／应用二进制接口 | 符号名编码与布局、调用约定、异常接口；源码兼容不等于二进制兼容 |
| Pimpl / opaque handle | Pimpl／不透明句柄 | 用指向不完整类型的成员或句柄隐藏实现与头文件依赖 |
| exception safety guarantee | 异常安全保证 | 不抛／强／基本／无保证，描述失败后对象与资源的状态 |
| discarded statement | 被丢弃语句 | `if constexpr` 未选中分支：仍须解析，但不实例化 |
| immediate function | 立即函数 | `consteval` 函数，每次调用都必须在编译期求值 |
| concept / constraint | 概念／约束 | 可命名并可偏序比较的模板实参要求 |
| coroutine frame / awaiter | 协程帧／等待体 | 保存挂起状态的运行期对象／决定挂起与恢复的协议 |
| hazard pointer / RCU | 危险指针／读-复制-更新 | 读者发布引用或延长宽限期的延迟回收策略 |
| ABA problem | ABA 问题 | 值比较无法区分“一直未变”与“变回原值” |
| type erasure / monomorphization | 类型擦除／单态化 | 运行期不保留类型参数／为每个实参组合生成专门代码 |
| reference counting / tracing GC | 引用计数／追踪式回收 | 计数归零即回收但难处理环／从根遍历可达对象但回收时机不确定 |
| treeify | 树化 | Java `HashMap` 桶内链表转为红黑树形态，改善最坏查找 |
| Nagle algorithm / delayed ACK | Nagle 算法／延迟确认 | 发送方合并未确认小报文／接收方推迟确认；两者叠加会带来额外延迟 |
| path MTU discovery | 路径 MTU 发现 | 靠 ICMP 反馈探测路径最小 MTU，ICMP 被过滤时表现为大包不通 |
| request smuggling | 请求走私 | 链路两端对同一条请求的边界判断不一致，导致后续字节被重新解释 |
| cache validation / conditional request | 缓存验证／条件请求 | 用 `ETag`／`Last-Modified` 验证副本能否复用，可复用时返回 304 |
| shared / private cache | 共享缓存／私有缓存 | 可被多个用户复用的代理缓存／仅单用户可用的客户端缓存 |
| layer 4 / layer 7 load balancing | 四层／七层负载均衡 | 按连接转发／按应用协议内容路由 |
| health check / session affinity | 健康检查／会话保持 | 摘除不可用后端／把同一用户固定到同一后端 |
| backoff / jitter / retry budget | 退避／抖动／重试预算 | 失败后延迟重试／随机化避免同步／限制额外尝试的比例 |
| index condition pushdown (ICP) | 索引条件下推 | 把仅用索引列即可判断的条件下推到存储引擎，减少回表 |
| covering index | 覆盖索引 | 查询所需列都在索引中，可只读索引而不回表 |
| metadata lock (MDL) | 元数据锁 | 保护表结构一致性的锁，DDL 要等持有者释放 |
| online DDL | 在线 DDL | 尽量缩短持锁时间的结构变更方式，不等于没有影响 |
| distributed transaction / compensation | 分布式事务／补偿 | 跨库的两阶段提交，或基于补偿与幂等的最终一致方案 |
| global ID generator | 全局 ID 发号器 | 分片后统一生成唯一标识的组件 |
| vacuum / transaction ID wraparound | 清理（VACUUM）／事务标识回卷 | PostgreSQL 回收死亡版本／事务标识用尽导致拒绝写入 |
| write-ahead logging (WAL mode) | 预写日志（WAL 模式） | SQLite 把修改先写入日志文件，读者与写者不互相阻塞，但仍只有一个写者 |

## 缩写与符号

正文使用的缩写、符号与短写形式如下。每个缩写给出英文全称；产品名、命令名、协议字段名和标准库类名保持原样，便于检索与对照。

### 网络与协议

| 缩写 | 英文全称 | 中文与用法 |
|---|---|---|
| OSI | Open Systems Interconnection | 开放系统互联参考模型 |
| MAC | Media Access Control | 介质访问控制地址，用于当前链路的帧交付 |
| ARP | Address Resolution Protocol | 直接相连 IPv4 网络的地址解析协议 |
| DHCP | Dynamic Host Configuration Protocol | 动态主机配置协议，交付地址与配置 |
| DNS | Domain Name System | 域名系统 |
| CNAME | canonical name | DNS 中表示别名的记录 |
| EDNS | Extension Mechanisms for DNS | DNS 扩展机制，选项由 OPT 伪记录承载 |
| OPT | option | EDNS(0) 使用的伪资源记录类型；也指 TCP 选项字段 |
| NAT | Network Address Translation | 网络地址转换 |
| NAPT | Network Address Port Translation | 网络地址端口转换 |
| ICMP | Internet Control Message Protocol | 网际控制报文协议，用于差错报告与诊断 |
| FTP | File Transfer Protocol | 文件传输协议 |
| SMTP | Simple Mail Transfer Protocol | 简单邮件传输协议 |
| P2P | peer-to-peer | 对等网络，参与者同时提供与获取资源 |
| URL | Uniform Resource Locator | 统一资源定位符 |
| HTTP | HyperText Transfer Protocol | 超文本传输协议 |
| HTTPS | HTTP over TLS（也写作 HTTP Secure） | 在 TLS 通道内传输 HTTP |
| TLS | Transport Layer Security | 传输层安全协议 |
| QUIC | 协议名称，现不再作为首字母缩略语展开 | 基于 UDP 的传输协议，HTTP/3 的传输基础 |
| ACK | acknowledgement | 确认标志或确认号 |
| SYN | synchronize | 同步序号、请求建立的标志 |
| FIN | finish | 表示该方向没有更多字节的标志 |
| RST | reset | 复位连接 |
| PSH | push | 提示推交数据的标志，不是消息边界 |
| URG | urgent | 使紧急指针有效的标志 |
| MSS | maximum segment size | 最大段长度 |
| PMTUD | Path MTU Discovery | 路径 MTU 发现，靠 ICMP 差错报文逐步探测 |
| SMSS | sender maximum segment size | 发送方最大段长度 |
| MTU | maximum transmission unit | 最大传输单元 |
| RTT | round-trip time | 往返时间 |
| RTO | retransmission timeout | 重传超时 |
| SRTT | smoothed round-trip time | 平滑往返时间 |
| RTTVAR | round-trip time variation | 往返时间波动估计 |
| `rwnd` | receive window | 接收窗口，保护接收缓冲 |
| `cwnd` | congestion window | 拥塞窗口，限制网络在途负荷 |
| `ssthresh` | slow start threshold | 慢启动阈值 |
| FlightSize | 不是缩写，指已发送但尚未确认的数据量 | 在途未确认量，与 `cwnd` 不是同一个量 |
| SACK | selective acknowledgement | 选择性确认 |
| ARQ | Automatic Repeat reQuest | 自动重传请求，确认与重传相结合的恢复思路 |
| TTL | time to live | 生存时间；在 DNS 中还表示记录的缓存时长 |
| EOF | end of file | 流上没有更多字节 |
| EAGAIN | try again（errno 名称） | “当前不能完成、应当重试”的返回 |

### 操作系统、内存与工具

| 缩写 | 英文全称 | 中文与用法 |
|---|---|---|
| ABI | application binary interface | 应用二进制接口，参数与寄存器的实现约定 |
| TLB | translation lookaside buffer | 地址转换缓存 |
| PSS | proportional set size | 按共享关系分摊后的驻留内存 |
| RSS | resident set size | 驻留物理页统计 |
| VIRT | virtual | top 等工具中的虚拟地址范围列，不是实际占用 |
| DMA | direct memory access | 直接内存访问 |
| PID | process identifier | 进程标识符 |
| PCB | process control block | 进程控制块，教科书对进程管理状态的统称 |
| FIFO | first in, first out | 先进先出 |
| FCFS | first come, first served | 先来先服务 |
| SJF | shortest job first | 短作业优先 |
| RR | round robin（调度） | 时间片轮转；在数据库章节中 RR 指 repeatable read |
| CFS | Completely Fair Scheduler | 完全公平调度器 |
| EEVDF | Earliest Eligible Virtual Deadline First | 合格任务中优先考虑虚拟截止时间的调度算法 |
| NUMA | non-uniform memory access | 非统一内存访问 |
| ELF | Executable and Linkable Format | 可执行与可链接格式 |
| BSS | Block Started by Symbol | ELF 中存放零初始化静态数据的段 |
| POSIX | Portable Operating System Interface | 可移植操作系统接口标准族 |
| BSD | Berkeley Software Distribution | 伯克利软件发行版；BSD 三条款是其许可证 |
| GNU | GNU's Not Unix | 递归缩写的自由软件项目名 |
| GCC | GNU Compiler Collection | GNU 编译器集合 |
| GDB | GNU Debugger | GNU 调试器 |
| SGI | Silicon Graphics, Inc. | 公司名；正文指其历史 STL 扩展 |
| IEEE | Institute of Electrical and Electronics Engineers | 电气电子工程师学会 |
| IEC | International Electrotechnical Commission | 国际电工委员会 |
| ASCII | American Code for Information Interchange | 美国信息交换标准代码 |
| UTF | Unicode Transformation Format | Unicode 转换格式，如 UTF-8 |
| SSD | solid-state drive | 固态硬盘 |

### 语言、数据与中间件

| 缩写 | 英文全称 | 中文与用法 |
|---|---|---|
| STL | Standard Template Library | 标准模板库 |
| RAII | Resource Acquisition Is Initialization | 资源获取即初始化 |
| RTTI | run-time type information | 运行时类型信息 |
| CAS | compare and swap | 比较并交换的原子操作 |
| PMU | performance monitoring unit | 性能监控单元 |
| C99 | ISO/IEC 9899:1999 | C 语言标准的年号简称 |
| N4861 | C++20 相关工作草案的文档编号 | 不是标准正式版本号 |
| API | application programming interface | 应用编程接口 |
| JSON | JavaScript Object Notation | 一种文本数据交换格式 |
| DOM | Document Object Model | 文档对象模型 |
| JWT | JSON Web Token | 一种表达声明的令牌格式，不自动加密 |
| ACID | atomicity, consistency, isolation, durability | 事务的原子性、一致性、隔离性与持久性 |
| MVCC | multiversion concurrency control | 多版本并发控制 |
| RC | read committed | 读已提交隔离级别 |
| RR | repeatable read | 可重复读隔离级别；在调度章节中 RR 指时间片轮转 |
| RU | read uncommitted | 读未提交隔离级别 |
| DDL | data definition language | 数据定义语言 |
| DML | data manipulation language | 数据操纵语言 |
| GTID | global transaction identifier | 全局事务标识 |
| ICP | index condition pushdown | 索引条件下推 |
| MDL | metadata lock | 元数据锁，保护表结构一致性 |
| XA | X/Open XA | 分布式事务的两阶段提交接口规范 |
| TCC | Try-Confirm-Cancel | 柔性事务的一种补偿协议：预留、确认、取消 |
| UUID | universally unique identifier | 通用唯一标识符 |
| GIN | generalized inverted index | PostgreSQL 的倒排索引框架 |
| GiST | generalized search tree | PostgreSQL 的通用搜索树框架 |
| AOF | append only file | Redis 的追加写持久化 |
| RDB | Redis database | Redis 的状态快照文件 |
| SDS | simple dynamic string | Redis 的简单动态字符串 |
| LRU | least recently used | 最近最少使用 |
| LFU | least frequently used | 最不经常使用 |
| LRM | least recently modified | Redis 8.6 起的淘汰策略，只按写操作更新时间 |
| PEL | pending entries list | Stream 消费者组的待确认条目列表 |
| PSYNC | partial resynchronization | 部分重同步协商 |
| SDOWN | subjectively down | 单个 Sentinel 的主观下线判断 |
| ODOWN | objectively down | 汇集足够故障意见后的客观下线状态 |
| LSM | Log-Structured Merge | 日志结构合并树 |
| WAL | write-ahead log | 预写日志 |
| KMP | Knuth–Morris–Pratt | 字符串匹配算法及其作者缩写 |
| SSO | small string optimization | 小字符串优化，容量与布局由实现决定 |
| ODR | one definition rule | 单一定义规则 |
| CRTP | curiously recurring template pattern | 派生类把自身类型作为模板实参传给基类的静态分派惯用法 |
| RCU | read-copy update | 读侧无锁、写者等待宽限期后回收的同步机制 |
| AVL | Adelson-Velsky and Landis | 以两位作者命名的平衡二叉搜索树 |
| BFS | breadth-first search | 广度优先搜索 |
| DFS | depth-first search | 深度优先搜索 |
| LSD | least significant digit | 基数排序中从最低位开始的顺序 |
| NIL | 不是缩写，指空叶哨兵 | 红黑树等结构中代表空叶的哨兵节点 |

## 教材术语与正文用语

国内操作系统与网络教材的常见说法与本篇用语的对应如下。两种写法指同一对象时给出对照，含义或边界不同时写明区别，便于按教材背诵时回到本篇的解释。

| 教材常见说法 | 本篇用语 | 关系与区别 |
|---|---|---|
| 缺页中断 | 缺页异常（page fault） | 同一次访存引发的内核处理；来源是当前指令而不是外部设备中断 |
| 快表 | 地址转换缓存（TLB） | 缓存部分页表项，容量远小于内存中的页表 |
| 逻辑地址 | 虚拟地址 | 进程看到的地址空间；页号与页内偏移划分后交地址转换 |
| 用户态／核心态 | 用户态／内核态 | 同一条特权边界的两种常见译名 |
| 中断／异常／陷入 | 中断／异常／系统调用 | 区分异步事件、当前指令引发的内部异常与主动请求内核服务的路径 |
| 就绪态／运行态／阻塞态 | 就绪／运行／阻塞 | 教材状态机用语；Linux 用可运行集合与等待队列实现同一区分 |
| 时间片轮转 | 时间片轮转（RR） | 调度算法名；数据库章节的 RR 指可重复读，两处缩写不同义 |
| 原语 | 原语（primitive） | 不可被中断拆分的基本操作；系统调用不等于原语 |
| 管程 | 管程（monitor） | 封装共享状态与条件等待的同步结构；C++ 用互斥量加条件变量组合 |
| 死锁的四个必要条件 | 死锁的四项必要条件 | 互斥使用、持有并等待、不可剥夺、循环等待 |
| 银行家算法 | 银行家算法 | 需最大需求已知的安全状态检查模型，不是通用线上死锁检测器 |
| 请求分页 | 按需分页 | 访问到未驻留页面时才装入 |
| 抖动 | 抖动（thrashing） | 置换频繁、有效访存率下降，与工作集大小相关 |
| 工作集 | 工作集（working set） | 进程在一段时间内活跃访问的页集合 |
| 文件控制块（FCB） | 文件元数据／inode | 教材把目录项与元数据合称 FCB；Linux 把元数据放在 inode，目录项只保存名字到编号的映射 |
| 静态链接／动态链接、重定位 | 静态链接／动态链接、重定位 | 装入时或运行时解析符号并修正地址 |
| 报文段／用户数据报 | TCP 报文段／UDP 数据报 | 传输层协议数据单元的名称不同，头部字段也不同 |
| 套接字 | socket | 由地址、端口与协议等确定的通信端点抽象 |
| 端口复用／分用 | 复用／分用 | 多个应用共用传输层／把到达数据交给正确的应用 |
