#### C++17／20 语言特性与编译期编程 {#interview-cpp-modern}

<article class="qa-item" id="qa-structured-binding" data-level="basic" markdown="1">
<p class="qa-question">Q63 · 结构化绑定绑定的是什么？为什么 <code>auto [a, b] = m</code> 拿不到引用？</p>
<div class="qa-answer" markdown="1">

`auto [a, b] = expr;` 会先引入一个隐藏变量 e，其类型由 `auto` 与说明符推导，绑定名是 e 的成员或元素的别名，而不是独立对象；写在 `auto` 上的 cv 与引用说明符作用于 e，不作用于单个绑定名。[309] 因此 `auto [a, b] = pair` 复制一份，元素是副本；要绑定到原对象必须写 `auto& [a, b] = pair`。

这解释了两个常见现象：遍历 `std::map` 时写 `for (auto [k, v] : m)` 会为每个元素复制键和值，改成 `auto& [k, v]` 或 `const auto& [k, v]` 才是引用；绑定名本身可读可写（当 e 可修改时），修改会作用到 e 的对应成员。

使用边界：绑定名不能再附加 `static`、`thread_local` 等存储类说明符；对聚合类型是按成员声明顺序绑定，成员顺序变化会静默改变含义，比具名访问更脆弱；只需要个别成员或需要明确类型时，直接写成员访问或 `std::get` 更清楚。结构化绑定适合拆开 pair／tuple、结构体与数组这类“整体打包、局部使用”的场景。

</div>
</article>

<article class="qa-item" id="qa-constexpr-family" data-level="basic" markdown="1">
<p class="qa-question">Q64 · constexpr、consteval 和 constinit 有什么区别？</p>
<div class="qa-answer" markdown="1">

`constexpr` 变量要求常量初始化并且可用于常量表达式，其对象隐含 const；`constexpr` 函数表示“可以在常量表达式中求值”，同时允许运行期调用。[306] 它是“可用于编译期”的一般标记。

`consteval`（C++20）声明立即函数：每次调用都必须在编译期产生常量，不能用于需要运行期求值的场合；[307] 适合必须编译期完成的检查与转换，例如把解析结果固化成类型信息，让错误发生在编译期。

`constinit`（C++20）只断言变量具有静态初始化（零初始化或常量初始化），不要求它是 const；违反时程序 ill-formed。[308] 它针对的是静态初始化顺序问题：变量在程序启动前完成初始化，其它翻译单元的动态初始化读它不会读到未初始化值。三者可以组合：`constexpr` 变量本身已满足静态初始化的要求；`consteval` 是函数的性质，不影响变量的存储与初始化。

</div>
</article>

<article class="qa-item" id="qa-if-constexpr" data-level="principle" markdown="1">
<p class="qa-question">Q65 · if constexpr 与普通 if 有什么区别？为什么它能替代一部分 SFINAE？</p>
<div class="qa-answer" markdown="1">

`if constexpr` 的条件必须是可转换到 bool 的常量表达式。条件为真的分支被保留，另一个分支成为“被丢弃语句”：它仍要通过语法与名字解析，但其中的模板实例化、常量求值等不会发生，因此可以写只在某些实参类型下合法的代码。[304]

与普通 `if` 的关键差别就在这里：普通 `if` 的两个分支都会被实例化与编译，所以“对部分类型非法”的代码无法用运行时分支藏起来。`if constexpr` 把选择移到编译期，起到过去用重载、标签分派或声明式 SFINAE 才能达到的效果，而错误信息落在真正被实例化的分支上，比替换失败的层层展开更易读。

边界也要清楚：被丢弃的分支不能包含对任何实例化都非法的非依赖代码（解析阶段就会失败）；依赖模板参数的名字要到实例化时才检查，因此写错的分支可能长期不被发现；`if constexpr` 只在函数体内做选择，不参与重载解析的候选筛选，需要按类型能力选择候选时仍然要用约束或 SFINAE。[305]

</div>
</article>

<article class="qa-item" id="qa-concepts" data-level="principle" markdown="1">
<p class="qa-question">Q66 · concepts 与 enable_if 相比改变了什么？代价是什么？</p>
<div class="qa-answer" markdown="1">

约束与概念把“模板对实参的要求”写成可检查、可命名的谓词，并参与重载解析：多个候选都可用时，约束更特化者优先，不满足约束的候选被排除；这要求约束之间存在偏序关系，而不是靠实现约定。[305]

与 `enable_if`／SFINAE 相比，变化有三点：错误信息落在调用点并指出哪个约束不满足，而不是展开成多层替换失败；约束可以命名复用，也可以写进 `requires` 子句；requires 表达式可以检查一组表达式的合法性（成员是否存在、能否调用、返回类型是否可转换），标准库的迭代器与范围概念因此可以按能力分层表达。代价是约束在编译期求值，复杂约束与大量候选会增加编译负担；requires 表达式只检查语法层面的合法性，不检查语义不变量（例如“比较必须构成严格弱序”仍靠文档与测试）；约束是接口的一部分，改动约束等于改变重载集合，可能让调用静默换到另一个候选。

</div>
</article>
