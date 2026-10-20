# C++ 后端问答：来源与维护入口

## 八股文：选题与技术依据

规范问答入口为 `content/06-interview.md`，它按部分组合 `content/interview/part-*.md`，各部分再组合本部分的主题子稿。实际组合文件及题目顺序以父稿和生成的 `manifest.json` 为准；题目使用稳定 `qa-*` ID，显示题号只是阅读顺序编号，不作为来源映射身份，也没有来源映射意义。

重排只移动题目正文并新增 `data-level` 层级属性，答案文字、引文和公式未改写。原先依赖位置措辞的三处跨题引用（堆的建堆成本、布隆过滤器边界、联合索引最左前缀）改为稳定锚点，线程池题的“前文”改为指向所引固定提交的表述。TechCPP 固定到 `c7aea7cb835bca777a2343a385a423aad3fcc973`，interview-guide 固定到 `9821f6af0cfd5948f2f116b829e62778f842c7b5`，分别提供具体题目与复习主题导航，不作为全部答案的技术保证。

重排前的 24 个子稿按主题归入七个部分，选题与技术核对关系不变。

| 部分 | 主题子稿 | 选题对应 | 主要技术核对 |
|---|---|---|---|
| 编程语言（C++） | `language-basics.md`、`language-objects.md`、`language-lifetime.md`、`language-memory.md`、`language-library.md`、`language-interfaces.md`、`language-modern.md`、`language-errors.md`、`language-compilation.md`、`language-concurrency.md`、`language-coroutines.md`、`language-cross-language.md` | TechCPP 的右值引用、智能指针及 README 的对象／容器主题；操作系统导航的同步与死锁；原 `cpp.md`、`cpp-language.md`、`cpp-object.md`、`cpp-memory.md`、`cpp-library.md`、`cpp-interfaces.md`、`concurrency.md` 的并发题；2026-10-19 补充批次的公开题目目录导航[343–344] | RAII、move/forward、共享句柄、删除与构造规则、vector、标准库接口、数据竞争与内存序；C++ 工作草案（关键字句与等待、联合体、移位、ODR、语言链接、协程、block 作用域初始化）、cppreference 页面、Core Guidelines、Itanium C++ ABI 与 libstdc++ ABI 政策；固定版本的 libstdc++ 本地缓冲[294]与 OpenJDK `HashMap` 阈值[336]；Java 侧为 JLS SE 21 与 JDK 21 API 文档；既有线程池固定源码 |
| 操作系统 | `os-basics.md`、`os-processes.md`、`os-ipc.md`、`os-deadlock.md`、`os-memory.md`、`os-io.md`、`os-service.md`、`os-diagnostics.md` | 操作系统导航；TechCPP 的 epoll；原 `operating-system.md`、`os-foundations.md`、`linux-service.md`，以及原 `cpp-interfaces.md` 的 GDB 死锁题 | Linux MM、pthreads、getrusage、mmap、epoll；教材式调度、死锁与置换模型的适用条件 |
| 网络 | `network-layers.md`、`network-transport.md`、`network-lifecycle.md`、`network-http.md`、`network-security.md`、`network-diagnostics.md` | 网络导航；TechCPP 的 TCP 字节流；原 `network.md`、`network-foundations.md`、`network-headers.md`，以及原 `engineering.md` 的网络诊断题；2026-10-19 补充批次仍在同一主题内插入状态机、Nagle、分片与 MTU、消息长度歧义、缓存、RPC、抓包、长连接、重试与负载均衡题[343–344] | RFC 9293（含 §3.7 分段）、9110、9111、9112、8446、896、1122、1191、791 的相关段落；tcp(7)、ss(8)、tcpdump(8) 与内核 ip-sysctl 文档；nginx 与 gRPC over HTTP/2 规范、厂商退避与 SRE 过载处理文档 |
| 数据库 | `database-sql.md`、`database-index.md`、`database-transactions.md`、`database-logs.md`、`database-tuning.md`、`database-others.md`、`database-cache.md`、`redis-model.md`、`redis-internals.md`、`redis-cluster.md` | MySQL 与 Redis 导航；TechCPP 的索引题与缓存一致性题；原 `database.md`、`database-foundations.md`、`cache.md`、`redis-foundations.md`、`redis-internals.md`，以及原 `engineering.md` 的 LSM 题；2026-10-19 补充批次的 ICP、主键选择、两阶段提交、死锁、读写一致性、在线 DDL、分库分表、连接池与 Redis 阻塞题 | MySQL 8.4 索引、范围优化、ICP、快照、日志、两阶段提交与崩溃恢复、锁、元数据锁、AUTO_INCREMENT 与 `max_connections`；PostgreSQL 17 的清理／回卷与隔离级别；SQLite 的 WAL 与锁状态；Redis 官方事务、过期／淘汰、持久化、锁、集群与延迟诊断；分库分表引用中间件文档 |
| 数据结构 | `structures-linear.md`、`structures-trees.md`、`structures-hash.md` | 数据结构导航；TechCPP 的布隆过滤器题；原 `data-structures.md`、`data-foundations.md` | OI Wiki 哈希／二叉堆机制；原创概率与成本推导 |
| 算法 | `algorithms-basics.md`、`algorithms-graph.md`、`algorithms-paradigms.md`、`algorithms-large-data.md`、`algorithms-membership.md` | 算法与数据结构导航；原 `algorithm-foundations.md`、`large-data.md`、`large-data-membership.md`，以及原 `data-structures.md` 的拓扑排序题 | OI Wiki 排序与图算法机制；原创复杂度、概率与容量推导 |
| 工程与工具 | `engineering-build.md`、`engineering-debugging.md`、`engineering-vcs.md`、`engineering-ops.md` | 工程、工具与设计模式补充；原 `engineering.md`，并吸收原 `os-foundations.md` 的编译链接题 | 工具官方文档与固定版本手册；未运行构建、性能或内存检查 |

文件清单、许可检查和实际研读范围在 `reference/interview-sources.json`，绝对化表述的修正在 `reference/interview-reading.md`。Redis 固定源码依据见 `reference/redis-implementation-reading.md`；数据结构、算法与海量数据依据见 `reference/algorithms-reading.md`；工程、工具与设计模式补充依据见 `reference/engineering-reading.md`。可复用文档快照的哈希及版本边界保存在 `reference/technical-docs/index.json`，不进入公共导出。

引文 [11]–[12] 为选题来源，[343]–[344] 为 2026-10-19 补充批次的题目标题目录导航；[13] 起为技术资料及相关实现定位，[282]–[372] 为两批补充的页级引用。不能把动态标准草稿当作某一正式 ISO 版本；实现细节引用限于所标注的固定版本。两选题仓库未发现明确许可证，不转载其答案全文、图表或求职话术，不复制完整仓库；补充批次只记录题目目录链接，不转载其题目或答案文字。

问答采用 `docs/questions.md` 的显式结构与可选 `data-level` 层级；默认完整展开，原有五章不变成题库。新问答没有上游执行证据，文档构建和浏览器回归不扩张上述早期 C++ 契约检查范围。

规范与手册的引用保留原始链接与版本，不依赖已移除项目的文档快照归档；线程池题的固定版本与源码位置写在答案的引文中。独立阅读页为 `cpp-backend-questions/index.html`，题目 ID 和来源核对状态沿用原记录，润色不提升覆盖状态。
