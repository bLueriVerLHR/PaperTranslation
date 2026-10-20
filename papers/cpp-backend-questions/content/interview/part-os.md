### 第二部分 操作系统 {#interview-os}

操作系统部分按教材常见顺序展开：先确定操作系统的职责与运行机制，再依次讨论进程与调度、进程间通信、死锁、内存管理、文件系统与 I/O，最后落到服务运行和系统观测。术语沿用国内教材的常见译名，例如就绪、运行、阻塞、快表、缺页异常和银行家算法，并说明它们与 Linux 具体接口、系统调用之间的对应关系。

{{include:os-basics.md}}

{{include:os-processes.md}}

{{include:os-ipc.md}}

{{include:os-deadlock.md}}

{{include:os-memory.md}}

{{include:os-io.md}}

{{include:os-service.md}}

{{include:os-diagnostics.md}}
