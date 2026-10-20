#### 库接口与算法使用 {#interview-cpp-interfaces}

<article class="qa-item" id="qa-map-access" data-level="basic" markdown="1">
<p class="qa-question">Q58 · map 的 []、insert、find、at 和 try_emplace 有什么区别？</p>
<div class="qa-answer" markdown="1">

区别主要在于是否插入缺失键、是否覆盖已有值，以及未命中时如何返回。`m[key]` 在缺键时插入元素，再返回映射值的引用；已有键时，单独访问不会覆盖原值，`m[key] = value` 才进行赋值。`find` 返回迭代器，未命中返回 `end()`，不插入元素；`at` 返回映射值引用，未命中抛出 `std::out_of_range`。因此，只查询是否存在可用 `find`，要求键已存在可用 `at`。[58]

不带位置提示的单元素 `insert` 返回迭代器与插入标志，遇到等价键保留原映射。C++17 的 `try_emplace` 只在缺键时构造映射对象，`insert_or_assign` 则在缺键时插入、已有键时赋值。这里的“按需构造”不包括推迟实参求值：`try_emplace(key, build())` 在进入容器操作前仍会求值 `build()`；若直接传入映射类型的构造参数，才可能避免已有键情况下的对象构造。[183]

并发下，先 `find` 再 `insert` 是多个操作，中间可能发生结构修改。是否需要同步取决于实际访问组合，不能把两个接口合起来当成原子的“检查并插入”。[17]

</div>
</article>

<article class="qa-item" id="qa-search-bounds" data-level="basic" markdown="1">
<p class="qa-question">Q59 · find、binary_search、lower_bound 和 upper_bound 怎样区分？</p>
<div class="qa-answer" markdown="1">

通用 `find` 逐项检查相等条件，返回首个匹配迭代器，未命中返回 `end()`。`binary_search` 只返回是否存在比较器意义下的等价元素，不给出位置；`lower_bound` 和 `upper_bound` 返回边界位置。对通常的升序区间，前者指向第一个不小于目标的元素，后者指向第一个大于目标的元素。[59–61]

例如在 `[2, 5, 5, 9]` 中查找 5，`lower_bound` 指向第一个 5，`upper_bound` 指向 9，两者之间就是等价元素范围。查找 6 时，两者都指向 9：边界位置也可以表示插入位置，并不保证该处元素等于目标。返回 `end()` 时，该迭代器不能解引用。

这些二分接口要求区间满足各自相对目标的分区条件；按相应比较规则排序是常用的充分条件。比较次数和迭代器移动次数还要分开计算：二分比较是对数级，但非随机访问迭代器可能累计线性移动。对 `map`、`set`，成员 `find`、`lower_bound` 和 `upper_bound` 有对数复杂度契约，通用二分算法并不能通过普通迭代器直接利用容器内部的查找结构。[189]

</div>
</article>

<article class="qa-item" id="qa-set-multi" data-level="basic" markdown="1">
<p class="qa-question">Q60 · set、multiset、map、multimap 怎样处理键和重复项？</p>
<div class="qa-answer" markdown="1">

`set`、`multiset` 的元素本身就是键，`map`、`multimap` 的元素包含键与映射值。`set`、`map` 只保留每个等价键的一项，两个 `multi` 版本允许多项。键等价由比较器定义：`comp(a, b)` 与 `comp(b, a)` 都为假，不必与类型的 `operator==` 相同。四者都有按比较器组织的有序语义，常见实现采用平衡树，但标准不规定固定的节点布局。[178]

元素在容器内时，`set`、`multiset` 的迭代器提供只读键访问；`map`、`multimap` 可以修改映射值，不能通过迭代器修改键。这样才能维持容器的键序关系。同键组可用 `equal_range` 取得；按键 `erase` 删除所有等价键元素，按单个迭代器 `erase` 只删除指定元素。[189]

无序版本改用相等判定与哈希规则，等价键必须具有相同哈希值。若用集合去重，比较器或相等判定表达的还须是业务上的“同一项”；容器只能执行给定的等价规则，不会自动识别重复请求。

</div>
</article>

<article class="qa-item" id="qa-algorithm-categories" data-level="basic" markdown="1">
<p class="qa-question">Q61 · 常见算法除了排序还包括什么？使用时最容易漏掉哪些条件？</p>
<div class="qa-answer" markdown="1">

标准库算法还包括查询与判定，如 `find`、`count`、`all_of`；序列变换，如 `transform`、`copy`、`reverse`、`rotate`；划分、合并与排列，如 `partition`、`merge`、`next_permutation`；数值累计，如 `accumulate`、`inner_product`；以及 `make_heap`、`push_heap`、`pop_heap` 等堆操作。它们通过迭代器处理区间，各自仍有输入、输出和类型条件。

`copy` 给目标元素赋值，并不替容器建立足够多的新元素。空 `vector` 的 `begin()` 不是可自动扩容的输出位置，即使已经 `reserve` 也不等于已经有可写元素；可以先建立目标元素，或用 `back_inserter` 通过 `push_back` 逐项追加。普通 `copy` 的目标起点不能位于源区间内，重叠复制还要选择满足相应方向及范围条件的操作。[184]

`merge` 的输入须按同一比较规则有序；`push_heap` 则要求除新追加末项外的前缀已满足堆序，它只修复新项，不负责把任意区间建成堆。[38, 184] `accumulate` 的累计类型由初始值参与推导：用整数 `0` 累加浮点序列，累计结果会反复转换回整数；用 `0.0` 可采用 `double` 累计，但仍不消除浮点舍入误差。[184]

</div>
</article>

<article class="qa-item" id="qa-c-string-functions" data-level="principle" markdown="1">
<p class="qa-question">Q62 · strcpy、strcmp 和 malloc 的简化实现要维持什么不变量？为什么一些接口风险高？</p>
<div class="qa-answer" markdown="1">

`strcpy` 复制源字符串，包括终止零字符；目标至少要容纳源长度加 1，源与目标不能重叠。它不接收目标容量，因此无法替调用方确认目标是否足够，越界写入会产生未定义行为。[185] `strcmp` 按 `unsigned char` 的字节值比较，在首个差异或串尾决定次序；调用方根据返回值小于、等于或大于 0 判断关系，不依赖它恰好返回 −1 或 1。[186–187]

容量受控的教学复制接口需要同时约定源的有效范围和目标容量。可以先在源界内找到零字符，再检查长度加 1 不溢出且目标容量足够，最后复制字节与零字符。没有在源界内找到串尾、容量不足或违反指针及重叠约定时，应按接口约定报告失败，而不是把截断结果当作完整复制成功。安全性来自这些前提得到维持，不是仅把函数名换成 `strncpy`。

完整的 `malloc`／`free` 实现还需要维护对齐、可用块与回收状态，并处理并发访问、尺寸计算和系统申请等问题。glibc 可结合堆扩展、匿名映射和多个分配区管理存储；这属于具体实现，不是所有分配器的固定结构。仅调用 `sbrk(size)` 的短片段没有解释后续如何 `free`、复用存储或保护共享状态，因此只能作系统申请的教学示意，不能替代完整或跨平台的分配器。[188]

</div>
</article>
