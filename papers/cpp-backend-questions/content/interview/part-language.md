### 第一部分 编程语言（C++） {#interview-cpp}

语言部分从类型和值类别开始，再看类与对象如何组织状态，然后进入资源所有权、内存布局与标准库选型，随后是 C++17／20 的编译期能力、异常安全与错误处理、编译模型与 ABI，最后处理并发、协程与跨语言对比。C++ 的问题很少停留在单条语法上：一次 `vector` 重分配会同时牵动对象构造、迭代器有效性和服务尾时延，所以同一主题内先分清概念，再解释机制，最后落到选型和排障。

{{include:language-basics.md}}

{{include:language-objects.md}}

{{include:language-lifetime.md}}

{{include:language-memory.md}}

{{include:language-library.md}}

{{include:language-interfaces.md}}

{{include:language-modern.md}}

{{include:language-errors.md}}

{{include:language-compilation.md}}

{{include:language-concurrency.md}}

{{include:language-coroutines.md}}

{{include:language-cross-language.md}}
