## 分主题问答 {#backend-interview}

对象所有权、线程调度、网络字节流和数据库提交分别回答不同层次的问题。一个请求可以在网络层已接收、在线程池中仍排队、在数据库中已经提交，而客户端尚未收到结果。把这些状态分开，才能解释超时、重试、并发访问和资源回收。

全书分为编程语言、操作系统、网络、数据库、数据结构、算法和工程工具七个部分，共 47 个主题。每个部分先给出基础概念，再解释机制与边界条件，最后落到选型、排障和业务场景；主题内部保持同样的递进顺序，基础题在前，原理题居中，场景题在后。题目按主题重新编号，稳定的题目 ID 与答案的技术断言不随重排和补充改变。

选题参考公开的后端与 C++ 面试主题整理：TechCPP 与 interview-guide 的固定版本提供具体题目与复习导航，[11–12] 后续补充以公开题目目录确认主题范围。[343–344] 这些资料只用于确定问题范围，答案的技术依据是各自引用的标准、手册与产品文档。

这里的问答把语言性质、操作系统接口与数据库语义分开处理，不把它们混为同一种“线程安全”。

<div class="qa-bank" id="cpp-backend-questions" markdown="1">

{{include:interview/part-language.md}}

{{include:interview/part-os.md}}

{{include:interview/part-network.md}}

{{include:interview/part-database.md}}

{{include:interview/part-structures.md}}

{{include:interview/part-algorithms.md}}

{{include:interview/part-engineering.md}}

</div>
