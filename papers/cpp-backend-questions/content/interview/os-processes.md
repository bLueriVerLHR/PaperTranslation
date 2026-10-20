#### 进程、线程与调度 {#interview-os-process}

<article class="qa-item" id="qa-process-thread-coroutine" data-level="basic" markdown="1">
<p class="qa-question">Q93 · 进程、线程、协程的隔离、调度和内存边界有什么区别？</p>
<div class="qa-answer" markdown="1">

进程通常提供独立地址空间及一组资源边界；同一进程中的线程共享地址空间与许多进程资源，各有执行上下文、栈和线程局部状态。POSIX 线程还共享打开的文件描述符等属性，不是每个线程都有一份完全独立的堆。[23]

协程是可暂停、恢复的执行结构，通常由程序或运行时安排在哪条线程执行。C++20 协程机制本身不提供通用调度器，也不承诺每个协程都有独立原生栈；状态可以保存在协程帧中。单线程交错推进多个协程是并发，不是同时使用多个核心。

协程能够隐藏等待期间的执行资源占用，但如果在承载线程上调用阻塞接口，其他依赖该线程推进的协程仍会停顿。协程也不会自动隔离共享对象；一旦跨线程恢复或共享可变状态，仍需相应同步协议。

</div>
</article>

<article class="qa-item" id="qa-fork-exec-zombie" data-level="basic" markdown="1">
<p class="qa-question">Q94 · fork 与 exec 有何区别？僵尸、孤儿及父进程退出怎样处理？</p>
<div class="qa-answer" markdown="1">

fork 创建子进程，父返回子 PID、子返回 0，失败返回−1；exec 成功时替换当前进程的程序映像，而不是自动再创建一个进程。Linux fork 常借助写时复制，但仍有页表与任务管理成本；父子描述符还可能引用同一打开文件描述，共享偏移等状态。[66–67]

子进程已终止但退出信息未被回收时是僵尸，父进程用 wait 等接口取得状态；孤儿是失去原父进程的仍存在子进程，可被 init 或 subreaper 重新托管，两者不能互换。[65] 父退出不一般性地杀掉所有子进程，具体信号、终端和监督协议另有规则。多线程进程 fork 后子进程只保留调用线程，却复制了其他线程可能持有的锁状态，因此 exec 前安全操作有严格限制，不能继续任意调用带内部锁的库函数。[66]

</div>
</article>

<article class="qa-item" id="qa-scheduling-policies" data-level="principle" markdown="1">
<p class="qa-question">Q95 · FCFS、SJF、RR、优先级和反馈队列有什么取舍？Linux 一直用 CFS 吗？</p>
<div class="qa-answer" markdown="1">

FCFS 简单但长作业可能阻塞短作业；SJF 在给定到达与运行时间等模型中改善平均等待，却依赖可知或可估计的作业长度；RR 用时间片改善轮转响应，片太短增加切换，太长接近先来先服务。优先级调度可能使低优先级任务饥饿，多级反馈队列根据行为调整等级，常配合老化等机制平衡响应与公平。

这些是不同目标下的策略，不是 Linux 所有任务共用的一条规则。Linux 有普通、实时和 deadline 等调度类别；普通公平调度从 CFS 演进，内核文档说明 6.6 开始向 EEVDF 转变，不能把旧版“按最小虚拟运行时间选任务”的描述固定到所有现代版本。EEVDF 在合格任务中考虑虚拟截止时间，虚拟时间不是业务请求真正的完成期限；实时策略也不能绕过过载和错误优先级设计。[68]

</div>
</article>

<article class="qa-item" id="qa-signal-exit" data-level="principle" markdown="1">
<p class="qa-question">Q96 · 信号怎样送达？SIGTERM、SIGKILL、SIGCHLD 与正常退出有何不同？</p>
<div class="qa-answer" markdown="1">

信号生成后可能先处于待决状态，屏蔽会推迟相应送达，不是立即执行默认动作。处理方式有默认、忽略或处理函数；处置通常是进程级属性，屏蔽字是线程级属性，进程定向与线程定向信号的目标选择不同。Linux 在适当的内核返回用户态路径上安排处理函数，处理函数本身在用户态执行。[64]

SIGTERM 可用于约定的正常收尾，SIGKILL 和 SIGSTOP 不能捕获、忽略或屏蔽；SIGCHLD 表达子状态变化，普通信号可能合并，处理程序不能据次数机械回收同样次数的子进程。正常 return、exit、_exit、异常崩溃和强制终止的清理行为不同，不能假设每条终止路径都会展开 C++ 自动对象析构。异步信号处理函数可安全调用的操作受限制，通常把完整业务收尾移到正常执行流，而不是在处理函数中随意加锁、分配或写复杂日志。[64–65]

</div>
</article>
