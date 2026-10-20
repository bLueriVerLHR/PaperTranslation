#### 协程与异步执行 {#interview-cpp-coroutines}

<article class="qa-item" id="qa-coroutine-frame" data-level="principle" markdown="1">
<p class="qa-question">Q83 · C++20 协程的状态保存在哪里？谁负责销毁？</p>
<div class="qa-answer" markdown="1">

协程函数会被编译器改写成状态机，运行期对象是协程帧（协程状态）：它保存形参与局部变量、当前挂起点、promise 对象以及恢复所需的信息。帧的分配与释放由编译器生成的代码通过分配函数完成，[322] 可以定制 promise 的 `operator new`／`operator delete`，在条件允许时实现也可以省略分配或使用调用方提供的存储。[320]

协程的生存期不随函数返回结束，控制权交给句柄：`resume()` 从最近挂起点继续执行，`destroy()` 释放帧并析构 promise；如果没有人在完成或取消时销毁句柄，帧不会被回收，这就是协程最常见的泄漏形式。[320]

因此异步接口必须明确所有权：谁持有句柄、完成与取消时由谁销毁、异常如何转交（`unhandled_exception`）、`final_suspend` 采用哪种策略（返回始终挂起可以让调用方决定销毁时机，很多库这样设计）。帧是普通对象（除非定制分配），挂起不占用线程栈也不代表有线程在等它；由于恢复可能发生在另一个线程上，协程内部状态仍受并发规则约束。

</div>
</article>

<article class="qa-item" id="qa-coroutine-awaitable" data-level="principle" markdown="1">
<p class="qa-question">Q84 · awaitable 协议怎样决定挂起与恢复？</p>
<div class="qa-answer" markdown="1">

`co_await e` 的处理顺序是：先取得 awaiter（`e.operator co_await()`、`operator co_await(e)` 或 e 自身），再调用 `await_ready()`；返回 true 表示结果可立即取得、不挂起，这是可选的短路优化。[321,323]

需要挂起时调用 `await_suspend(handle)` 决定控制转移：返回 void 表示挂起并把控制交回调用者或恢复者；返回 bool 表示是否真的挂起（false 则立即继续）；返回另一个协程句柄表示把控制直接转交给那个协程，让恢复链不增长调用栈。恢复后调用 `await_resume()` 取得表达式结果，或抛出在等待期间保存的异常。[321,323]

由此产生几条工程约束：`await_suspend` 可以把句柄交给线程池或事件循环，之后 `resume()` 在哪个线程发生由调度器决定，因此跨线程恢复后共享状态仍需同步；若 `await_suspend` 声明不抛却抛出，会直接终止程序（见 [noexcept 与终止](#qa-noexcept-terminate)）；awaitable 协议本身不提供取消、超时与优先级，这些要由 promise、句柄管理或上层调度器实现。

</div>
</article>

<article class="qa-item" id="qa-coroutine-service" data-level="scenario" markdown="1">
<p class="qa-question">Q85 · 协程、回调与线程池在服务端各解决什么问题？</p>
<div class="qa-answer" markdown="1">

线程池解决“执行资源如何复用”的问题：它限制并行度、复用线程，但在阻塞式调用下每个等待都会占用一个线程，因此线程数随并发等待数增长；连接状态要么与线程绑定，要么显式沿调用链传递。

回调把“完成之后的继续动作”写成函数：不需要为等待占用线程，却把控制反转给了调用方——状态必须手工保存在对象里，错误与取消要层层转发，调用栈在异步边界处断裂，可读性与调试难度随之上升。

协程提供挂起／恢复的语法与状态保存：局部变量留在帧里，因此可以用接近同步代码的写法表达异步流程，而执行资源由调度器决定（一个连接一个协程时，挂起不占线程）。[320,323] 代价是帧的分配与生命周期管理（见 [协程帧的所有权](#qa-coroutine-frame)）、跨线程恢复带来的并发问题、调试器对挂起协程栈的支持有限，以及取消与超时需要额外协议。

选择依据是任务形态：计算密集用线程池；等待型任务的并发数量远超核数时，线程模型成本高，应考虑异步；大量并发等待加顺序业务逻辑适合协程；一次性完成通知与对接既有 C 回调接口时回调最直接。三者可以组合——协程挂起后由线程池恢复是常见做法——但组合时要明确句柄所有权与线程亲和性。

</div>
</article>
