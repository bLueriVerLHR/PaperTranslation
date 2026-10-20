#### 生命周期、资源所有权与智能指针 {#interview-cpp-lifetime}

<article class="qa-item" id="qa-raii" data-level="basic" markdown="1">
<p class="qa-question">Q21 · RAII 为什么能处理提前返回和异常？它能解决所有生命周期问题吗？</p>
<div class="qa-answer" markdown="1">

RAII 把资源所有权交给对象，把释放行为接到析构路径。正常离开作用域或异常导致栈展开时，已构造完成的自动对象按相应销毁规则释放资源，因此函数不必在每一个返回分支重复写释放代码。`unique_ptr` 管理独占对象，锁守卫管理解锁；同一种机制不限于内存。[15, 42]

构造资源包装器的过程若失败，尚未构造完成的对象本身不会执行析构，已完成的成员仍按规则清理，因此资源获取过程也需要异常安全。RAII 的资源清理不自动提供“失败后状态完全不变”的强异常保证；后者需要把可能失败的准备与不可失败的提交分开。释放一个句柄不等于撤销业务副作用：数据库提交、已发出的响应或另一线程的访问，均不是析构自动回滚的对象。

对于异步任务，RAII 还依赖正确的持有关系。引用捕获不延长被引用对象的生命；任务若使用连接状态，连接状态必须活到最后一次访问之后。资源自动释放与释放时机正确是两件事：析构会归还资源，但若任务仍持有借用地址，释放之后的那次访问依然无效。

</div>
</article>

<article class="qa-item" id="qa-virtual-destruction" data-level="basic" markdown="1">
<p class="qa-question">Q22 · 什么时候需要虚析构函数？“有继承就必须加 virtual”准确吗？</p>
<div class="qa-answer" markdown="1">

在通常的单对象删除路径中，如果通过基类指针删除动态类型为派生类的对象，基类析构函数需要是虚函数，否则可能产生未定义行为。它解决的是销毁时的动态分派，不是所有继承结构都自动具有的需求。[19]

如果接口明确不允许通过基类销毁，可以用受保护的非虚析构函数表达约束。值类型、不作为多态删除入口的类，也不必仅因“可能被继承”就增加虚析构。特殊删除协议有额外规则，不能拿它们推翻普通所有权接口的要求。

虚调用通常借助实现定义的对象布局与函数表，但 C++ 规定的是可观察行为，不要求所有编译器、继承结构和 ABI 都有完全相同的 vptr 数量或表布局。因此“每个对象固定多占一个指针”不是通用语言定理。

</div>
</article>

<article class="qa-item" id="qa-constructor-virtual" data-level="basic" markdown="1">
<p class="qa-question">Q23 · 构造函数中能调用虚函数吗？它会调用最终派生类的实现吗？</p>
<div class="qa-answer" markdown="1">

可以调用，但当调用针对正在构造或析构的对象时，分派按当前构造／析构阶段所属的类进行，而不是直接跳到尚未构造完成或已经销毁的更派生部分。这使基类初始化不依赖派生对象尚未建立的状态。[20]

例如 `Base` 的构造函数调用自己的虚成员，在普通有效调用情形下不会因为最终对象是 `Derived` 就自动执行 `Derived` 的覆盖函数。因此“构造中不能出现虚调用”和“虚调用总按最终对象类型执行”都不准确。

需要派生行为的启动阶段，可以在完整对象建立后显式调用；这仍要处理启动失败及是否已向其他线程发布对象。语言的阶段规则不替代服务对象的初始化协议。

</div>
</article>

<article class="qa-item" id="qa-ownership-choice" data-level="basic" markdown="1">
<p class="qa-question">Q24 · 引用、原始指针、unique_ptr 和 shared_ptr 该怎样选？</p>
<div class="qa-answer" markdown="1">

先区分拥有与借用：拥有资源的实体负责释放，借用只在使用期间有效。[288] 表达拥有用 RAII 类型（`unique_ptr`、容器、自定义 RAII 包装）；表达借用用引用（一定不为空、不转移所有权）或指针（可能为空、可重新指向），并在接口上说明借用有效期。

`unique_ptr` 是默认的拥有形式：不可复制、可移动、通常与裸指针同尺寸，删除器可定制，数组用 `unique_ptr<T[]>`；只在生命周期确实需要共享时才用 `shared_ptr`，因为它引入控制块、原子引用计数、不确定的销毁时机与更高的对象图维护成本。`weak_ptr` 表达观察关系（打破环、缓存探测），使用时必须 `lock()` 并处理已失效的情况。

不要用裸指针表达所有权（`new`／`delete` 散落在业务路径上，异常分支容易漏），也不要为了“少写所有权说明”把一切都做成 `shared_ptr`，那会把生命周期变成隐式全局协议，让销毁时机与依赖关系难以推理和测试。

参数与返回的约定可以固定下来：只读用 `const T&`，需要修改用 `T&`，可能为空用 `T*`，转移所有权用按值的 `unique_ptr<T>`，共享所有权用按值的 `shared_ptr<T>`，借用连续区间用 `span` 或 `string_view`，并按各自的失效规则约束调用方（字符串相关的生命周期见 `string_view` 题）。

</div>
</article>

<article class="qa-item" id="qa-move" data-level="principle" markdown="1">
<p class="qa-question">Q25 · std::move 是否真的移动数据？对 const 对象使用它会怎样？</p>
<div class="qa-answer" markdown="1">

`std::move` 本身只是把表达式转换成允许匹配右值引用的值类别；资源是否转移，由随后选中的构造、赋值或其他函数决定。对拥有缓冲区的对象，移动操作可能转移指针和容量，而复制通常需要另外建立资源；对简单标量，这种差别可能不存在。[13]

一个具名的右值引用变量，在表达式中仍是左值。另一方面，`const T` 经 `std::move` 不会失去 const；常见移动构造要求 `T&&`，无法接收 `const T&&`，于是可能选择复制构造，或因类型不允许复制而编译失败。不能看到 `std::move` 就认定没有复制。

标准库对象被移动后通常处于有效但未指定的状态，除非类型或具体操作有更强约定。有效意味着仍能销毁、赋值，并在满足前置条件时调用接口，不意味着字符串必为空或容器仍保留原内容。

</div>
</article>

<article class="qa-item" id="qa-forward" data-level="principle" markdown="1">
<p class="qa-question">Q26 · 完美转发与无条件移动有什么区别？为什么 T&amp;&amp; 不总是右值引用参数？</p>
<div class="qa-answer" markdown="1">

当函数模板参数 `T` 正在推导且参数形式满足转发引用条件时，`T&&` 可以接收左值和右值。左值实参使 `T` 推导为引用类型，引用折叠后参数仍绑定左值；右值实参则得到相应右值引用。不是所有 `T&&` 都满足这些条件，例如非推导上下文或 `const T&&` 不能直接套用该规则。[14]

包装函数内部的具名参数是左值，直接传给下一层会丢失原来的值类别。`std::forward<T>` 利用推导的 `T` 恢复相应左值或右值行为；`std::move` 则无条件请求右值行为，可能错误地消耗调用方仍需要的对象。

下面是本篇的教学片段，不是上游摘录；它只展示转发位置，`consume` 的实际重载决定下一步行为：

```cpp
template<class T>
void relay(T&& value) {
    consume(std::forward<T>(value));
}
```

转发不会延长生命周期，也不会保证参数只被使用一次。把同一个参数转发给两个可能消耗它的操作，仍需要单独定义先后关系和剩余状态。

</div>
</article>

<article class="qa-item" id="qa-move-noexcept" data-level="principle" markdown="1">
<p class="qa-question">Q27 · 移动构造为什么要标 noexcept？标准库在什么条件下才敢用移动？</p>
<div class="qa-answer" markdown="1">

容器扩容或插入搬移元素时，会在新存储上逐个构造元素。如果移动构造可能抛出，中途失败就可能已经把部分源元素“掏空”，无法再把容器恢复到操作前的状态，强异常保证就守不住。[289] 因此标准库提供了 `std::move_if_noexcept`：只有在移动操作被声明为不抛（或类型不可复制）时才返回右值引用去触发移动，否则退回左值以走复制路径。[289,290]

所以可移动类型的移动构造、移动赋值与 `swap` 通常标 `noexcept`。`noexcept` 是对编译器和标准库的承诺而不是性能提示：承诺失效会直接调用 `std::terminate`（见 [noexcept 与终止](#qa-noexcept-terminate)）。[311] 它同时影响重载解析、`noexcept` 运算符与容器搬运选择，因此给已有类型补标会改变行为，而不只是“加上一个优化说明”。

还有几个容易忽略的边界：搬运是否真的用移动还取决于类型是否可复制、分配器是否传播等条件；短字符串等实现细节会让移动实际复制字符（见 [`std::string` 的 SSO](#qa-string-sso)）；对可能失败的操作（例如带分配的自定义容器）不要为了贴 `noexcept` 而隐瞒失败路径，宁可让接口暴露失败并保持异常安全等级。

</div>
</article>

<article class="qa-item" id="qa-smart-pointer" data-level="principle" markdown="1">
<p class="qa-question">Q28 · unique_ptr、shared_ptr 和 weak_ptr 的所有权分别是什么？</p>
<div class="qa-answer" markdown="1">

`unique_ptr` 表示独占所有权，不可复制但可转移；独占所有权并不禁止存在不拥有资源的原始观察指针。`shared_ptr` 的多个句柄共享同一所有权组，最后一个强所有者释放时销毁受管对象。`weak_ptr` 是标准库的弱观察句柄，不增加强引用计数，通过 `lock()` 尝试取得临时强所有权。[15, 171]

若 A 和 B 互相持有对方的 `shared_ptr`，外部句柄销毁后强引用可能仍不归零。将不承担所有权的反向关系改为 `weak_ptr` 可以打断这种环，但选择哪条边是弱边，取决于对象模型，不能随意把所有成员都改成弱引用。

另一个风险是用同一原始指针分别构造两个独立 `shared_ptr`：两个控制块都会认为自己负责销毁资源，可能重复释放。共享所有权应从已有句柄复制或使用明确的共享构造关系，而不是仅让存储的地址相同。

</div>
</article>

<article class="qa-item" id="qa-shared-safety" data-level="principle" markdown="1">
<p class="qa-question">Q29 · shared_ptr 的引用计数安全，是否意味着对象和同一个句柄都能无锁修改？</p>
<div class="qa-answer" markdown="1">

必须分开三个对象：不同句柄所共享的控制块、某一个 `shared_ptr` 句柄自身、以及它指向的业务对象。不同线程可以操作各自的共享句柄，即使它们属于同一所有权组；但同一个句柄被并发读取和修改，需要同步或相应原子接口。被指向对象的字段仍遵循自身的数据竞争规则。[15–16]

例如两个线程各持有一个 `shared_ptr<Session>`，都执行 `session->count++`，引用计数机制不会保护 `count`。C++20 的 `atomic<shared_ptr<T>>` 可以用于句柄的原子发布与替换，也不会把 `T` 的全部操作变成原子操作。

`use_count()==1` 也不是建立互斥协议的办法：计数是一项观察，不能独自证明其他线程的访问已经结束或未来不会产生所有权。生命周期保证与并发访问保证必须分别设计。

</div>
</article>

<article class="qa-item" id="qa-intrusive-ownership" data-level="principle" markdown="1">
<p class="qa-question">Q30 · 侵入式与非侵入式引用计数有何区别？make_shared 一定更合适吗？</p>
<div class="qa-answer" markdown="1">

区别在于受管类型是否参与引用计数协议。侵入式方案由对象或关联接口维护计数；`shared_ptr` 使用所有权控制信息，不要求业务类型提供计数成员。所有权组与句柄保存的指针还不是同一概念：别名构造可以共享对象的所有权，却通过句柄观察其子对象。[15]

Boost 1.89.0 的 `intrusive_ptr` 通过未限定名的自由函数 `intrusive_ptr_add_ref(T*)` 和 `intrusive_ptr_release(T*)` 增减引用，通常由参数相关查找找到受管类型所在命名空间的钩子，不要求类具有同名成员函数。默认从非空裸指针构造句柄、复制非空句柄时增加引用；移动转移已有句柄，不另增引用。非空句柄析构时调用释放钩子，何时销毁对象由该协议负责。[160]

`add_ref=false` 表示接管一份已有引用，不是关闭析构时的释放。若调用方没有这份引用，析构仍执行释放就会破坏计数关系。计数协议即使支持并发，也只解决相应的所有权问题，不自动保护对象字段；互相持有的强引用还可能使计数始终无法归零。[15–16, 160]

`make_shared` 常把对象与控制信息合并分配，可以减少分配次数。但强引用归零后，对象已经销毁；若仍有 `weak_ptr`，合并存储可能继续保留到弱观察者结束，不能据此继续访问已销毁的对象。大型对象、需要指定删除器的对象和外部资源要结合释放协议选择，省一次分配并不意味着总是更合适。[15]

</div>
</article>
