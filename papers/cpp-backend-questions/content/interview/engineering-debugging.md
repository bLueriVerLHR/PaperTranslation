#### 崩溃排查与性能分析 {#interview-engineering-debugging}

<article class="qa-item" id="qa-gdb-core-symbols" data-level="scenario" markdown="1">
<p class="qa-question">Q253 · core、可执行文件和符号怎样配合排查崩溃？看到栈顶就能确定根因吗？</p>
<div class="qa-answer" markdown="1">

Core 保存崩溃时部分进程状态，可执行文件、共享库与调试符号帮助把地址解释为函数、行和变量；需要与实际运行版本匹配，不能用重新构建的同名文件代替。GDB（GNU Debugger）的文件、符号和 core 输入也分别有职责，core 不保证包含整个地址空间。[158]

栈回溯定位当时的调用链，切换栈帧查看参数与局部状态，再结合其他线程、异常或信号及对象寿命建立因果假设。优化、损坏的栈、缺失展开信息和符号都会限制结果。崩溃发生在释放或容器操作中，可能只是较早内存破坏的暴露点，不等于该库函数就是最初错误。

系统是否生成 core 还受资源限制、转储配置、权限及空间影响；文件可能含密钥与用户数据，需要按敏感资料处理。附加调试、断点和继续执行会改变目标状态；事后 core 分析保留一份现场，却不重现导致崩溃的完整事件过程。死锁则需建立完整的等待与持有关系，core 里的线程栈只能提供其中一部分证据。[63]

</div>
</article>

<article class="qa-item" id="qa-perf-count-sample" data-level="scenario" markdown="1">
<p class="qa-question">Q254 · perf stat 与 record 分别看什么？热点百分比能直接解释请求慢吗？</p>
<div class="qa-answer" markdown="1">

`perf stat` 汇总选定事件的计数，`perf record` 保存按事件或频率采集的样本及可选调用链；总计数与样本分布不是同一种证据。[144–145] 事件含义还取决于 CPU、内核和 PMU（performance monitoring unit，性能监控单元），不能把不同机器的同名事件无条件比较。

CPU 样本多说明相应代码在观测口径中占比高，不说明每个请求都慢在此处；网络、锁和存储等待可能消耗墙钟时间却不占相同 CPU 样本。归因要对齐请求阶段、运行区间、线程及资源范围，并区分自身函数和包含子调用的成本。

计数器数量有限时，多路复用与缩放可能影响准确性；采样频率、丢样和展开方式也改变结果。省略帧指针的程序用相应 frame-pointer 模式可能得到错误调用链，DWARF 或其他方式又有支持范围与成本。[144–145] 权限和安全配置可能限制观测，关闭防护还会改变访问边界。文档示例的倍率与实际服务的采样及性能证据不同。

</div>
</article>

<article class="qa-item" id="qa-memory-debug-tools" data-level="scenario" markdown="1">
<p class="qa-question">Q255 · Memcheck、ASan、LSan 与 pmap 怎样区分？检查通过是否证明没有内存错误？</p>
<div class="qa-answer" markdown="1">

Valgrind Memcheck 动态检查执行中的部分非法访问、未初始化值使用和泄漏；ASan 通过编译插桩与运行时检测相应越界、释放后使用等错误；LSan 专门分析泄漏，可与 ASan 集成或独立使用。pmap 展示地址映射，不是同一种对象级泄漏检测器。[146–148]

这些工具主要覆盖实际执行到、被检查支持的路径。未触发分支、定制分配器、抑制规则或平台能力都影响可检测范围；没有报告不能证明任意输入或并发交错都安全。Memcheck 的泄漏分类区分找不到块与仍可达，LSan 的根与可达性也不同于“业务仍然需要”；引用保留导致的业务容量增长可能需要额外对象分析。

工具增加时间、内存或地址空间成本，并可能改变时序；官方示例开销不自动成为该服务的测量值。ASan／LSan 支持范围还依赖具体平台，不能因 Windows 上编译器支持 ASan 就推导相同集成泄漏检查一定可用。[147–148] 这类错误检查也不替代竞争检测、性能分析或生产加固；检测器运行时本身的安全约束与生产程序也不同。

</div>
</article>
