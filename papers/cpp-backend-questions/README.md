# C++ 后端问答维护说明

本书独立维护这套问答；此前与它并列的后端主书已移除，书中不再指向该页面，需要的结论都在本文内写全。规范入口保留 `content/06-interview.md` 文件名，它按七个部分组合 `content/interview/part-*.md`，每个部分再用 `{{include:...}}` 组合本部分的主题子稿；单一题库 ID 为 `cpp-backend-questions`。

- 七个部分固定为编程语言（C++）、操作系统、网络、数据库、数据结构、算法和工程与工具。前六个是基本构成，工程与工具承载构建、调试、版本控制与运维题。当前 48 个主题、260 道题。
- 部分标题为 `h3`、主题标题为 `h4`；随机抽题按这一层级推导主题范围，因此主题划分属于规范稿结构，不在共享脚本里写死。
- 260 道题沿用稳定 `qa-*` ID、答案正文、引文与 MathML；结构变动只改变阅读顺序、显示题号与 `data-level` 层级属性。显示题号按阅读顺序连续重编，实际清单以重建的 `manifest.json` 为准。
- 2026-10-19 两批补充共 55 道。第一批 33 道以 C++ 为主：语言部分在既有主题内插入 16 道，并新增 C++17／20 语言特性与编译期编程、错误处理与异常安全、编译模型／ODR 与 ABI、协程与异步执行、跨语言对比五个主题。第二批 22 道聚焦网络与数据库：网络在既有主题内插入 10 道（状态机、Nagle 与延迟确认、分片与 MTU、消息长度歧义、HTTP 缓存、RPC、抓包、长连接与 TIME_WAIT、重试退避、负载均衡），数据库插入 9 道 MySQL／Redis 题并新增 PostgreSQL 与 SQLite 机制对比主题。选题以公开题目目录导航，技术依据为各答案引用的标准、手册与产品文档；核对方式与局限记在 `reference/interview-reading.md`，页级引用为 `reader.json` 的 [282]–[372]。
- `data-level` 取 `basic`、`principle`、`scenario`（基础、原理、场景），同一主题内按此递增排列；层级角标由共享样式按属性生成，不写入问题文字。
- 阅读页为 `dist/cpp-backend-questions/index.html`；本书独立维护，不依赖其他项目的阅读页。
- 题目与答案只在本书保留一份规范正文；显示 Q 编号不作为来源身份。
- 原 `6.x` 主题前缀取消，主题 ID 不变，旧 `interview-*` 锚点映射到含义最接近的新部分或新主题。3 处线程池正文原先指向已移除的阅读页，现已改为句内表述；内部 `qa-*` 链接保持不变；跨题的位置式引用改为稳定锚点。
- `reference/interview-coverage.json`、`interview-guide-topics.json`、`interview-roadmap-topics.json` 保留原核对状态；候选对应、归档与完整核验仍分开。
- 选题及权利身份在 `reference/interview-sources.json`；相关阅读记录仍在 `reference/`。规范与手册引用保留原始链接与版本，不复制原文快照。
- 来源映射在 `source-map.md`；引文为 `reader.json`；唯一词表是 `glossary.md`；完整来源、许可和限制放 `reader-meta.md`。
- 依照根 `docs/questions.md` 维护显式问答配对与可选层级。默认完整阅读，自测、仅问题搜索和按主题随机抽题由共享运行时增强，无脚本与打印包含完整答案；不创建项目私有 CSS/JS。

从库根重建：

```powershell
python tools/dev.py run -- dist/cpp-backend-questions/work/rebuild.py
```

重建不需要原始仓库或网络快照。研究资料保留用于之后的证据维护，不把生成成功、题目数量相同或来源记录存在当成全部答案正确的证明。本次重排没有执行 C++ 示例、Redis、数据库或上游测试。

`meta.json` 与 `reader.json` 的 `public_export` 布尔标志必须一致；导出资格不代替具体快照的发布授权。公开可访问的选题仓库不自动授予再分发权，原代码摘录许可完整保留。提交、推送和发布需另行授权，一次性检查报告与截图置于系统 TEMP。
