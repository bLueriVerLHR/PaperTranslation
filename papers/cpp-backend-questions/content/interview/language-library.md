#### 标准库、泛型与容器机制 {#interview-cpp-library}

<article class="qa-item" id="qa-stl-components" data-level="basic" markdown="1">
<p class="qa-question">Q41 · STL 怎样把容器与算法解耦？迭代器类别意味着什么？</p>
<div class="qa-answer" markdown="1">

典型 STL 设计用容器保存数据，用迭代器表达访问区间，用算法操作这些区间，再通过函数对象和分配器定制行为及存储。容器适配器把底层容器包装成受限接口，例如 stack 不对外暴露任意位置遍历。标准库还包含线程、文件等模块，不能把所有标准库能力都等同于 STL。

stack 和 queue 默认以 deque 为底层，却不强制只能使用它：stack 要求相应序列容器提供 back、push_back、pop_back，vector、list、deque 都可以满足；queue 需要 front、back、push_back、pop_front，list 和 deque 可以满足，普通 vector 缺少 pop_front。[180] 算法的范围与参数也各有契约，例如 copy 除输入半开区间外还需要输出起点；容器的 erase 成员接口与通用算法不能只按名称合并。

迭代器类别约束算法能够使用的操作及其复杂度：输入／输出迭代器支持相应的单遍读写，前向迭代器增加多遍保证，双向迭代器允许反向移动，随机访问迭代器支持常数时间跳转和距离计算，C++20 的连续迭代器还描述元素地址的连续关系。通用 `sort` 要求随机访问，而不要求连续存储；因此 `deque` 可以满足这一要求，`list` 则应使用其成员 `sort`。[208, 216]

区间通常写成 `[first, last)`，`last` 不属于这个区间，但它未必不可解引用：子区间的右边界可能仍指向容器中的另一个元素。容器的尾后迭代器 `end()` 则不能解引用。满足条件的原生指针也可以作为迭代器；迭代器不是天然带边界检查的安全指针，合法操作仍受区间和失效规则约束。[208]

`list` 是双向链表，`forward_list` 提供相应的单向链表接口；`array` 的固定元素存储则不依赖动态容器分配器。它们的访问和存储契约不同，不能归结为一种统一的实现结构。[179, 209]

适配器不仅包装容器，也能改变访问和调用接口。reverse_iterator 把基迭代器前一个元素作为当前解引用目标，使算法沿反方向读取；back_insert_iterator 则把赋值转成底层容器的 push_back，其递增不会像普通输出指针那样移动到尚不存在的元素。[168] 例如下面的原创示意把一个区间反向复制到另一容器；目标初始为空仍可逐项增长，因为输出接口明确执行追加，而不是向空 vector 的 begin 写入。

```cpp
std::vector<int> source{1, 2, 3};
std::vector<int> result;
std::copy(source.rbegin(), source.rend(), std::back_inserter(result));
```

函数适配器可以保存部分参数并重组调用参数。以整数阈值 threshold 为例，`std::bind(std::greater<int>{}, std::placeholders::_1, threshold)` 把二元比较包装成一元判定：调用时传入待比较值，另一参数来自保存的阈值副本。[169] 明确需要借用时可用 reference_wrapper 协议，但必须另行保证被借用对象存活。适配改变的是接口，分配器改变的是存储协议；二者都不能替算法解除区间、比较关系或生命周期要求。

历史名称还需要与标准名称分开。libstdc++ 保留过 SGI 风格的 hash_map／hash_multimap、hash_set／hash_multiset、slist、rope 等扩展，其中旧哈希容器由 C++11 的 unordered 系列标准接口接续，slist 是单向链表，标准库已有 forward_list；旧名称不因出现在教材里就变成通用标准接口。[170] 同一实现还曾提供 bit_vector 兼容设施和额外的 bitset 方法，这些是实现扩展，不能直接推定在另一标准库中也可用。[161]

“标准但非 STL 的容器”通常来自历史教材的划分口径，不应代替具体类型的契约。标准库的 basic_string 保存可变字符序列，当前草案明确将其归为连续容器；bitset<N> 则保存固定数量的位，其非 const 下标访问返回位引用代理，不是普通元素引用。[175, 177] valarray 面向数值数组，例如两个等长数组相加按对应元素产生结果，而非把两个序列拼接起来。[176] 这些设施都属于标准库，但访问接口、元素操作和失效规则各有规定，不能从“非 STL”这个标签推导它们非标准，或把 vector 的全部保证直接移植过去。

</div>
</article>

<article class="qa-item" id="qa-sequence-containers" data-level="basic" markdown="1">
<p class="qa-question">Q42 · array、vector、deque 和 list 应怎样选择？</p>
<div class="qa-answer" markdown="1">

选择首先取决于长度、访问方式和元素地址是否需要稳定。`array` 适合固定元素数；普通 `vector<T>` 在 `T` 不是 `bool` 时提供连续存储，适合索引访问和尾部增长；`deque` 支持两端增长与随机访问，但不保证整段元素连续；`list` 支持已知位置的节点插入、删除，不提供常数时间的任意位置访问。[209]

链表在已取得位置时插入一个元素具有常数时间复杂度，寻找第 k 个节点却仍需遍历；频繁按序号定位时，这部分成本不能省略。`vector` 的中间插入和删除需要移动后继元素，但连续访问也可能改善局部性，实际优劣取决于对象大小和访问模式。`deque` 常以分块结构实现，块大小和目录组织并非标准固定值。要求连续缓冲的接口不能直接接收整段 `deque` 或 `list` 存储，而链表删除后的稳定性保证也只适用于仍存活的元素。[209, 210]

</div>
</article>

<article class="qa-item" id="qa-emplace-push" data-level="basic" markdown="1">
<p class="qa-question">Q43 · push_back 与 emplace_back 有什么区别？什么时候 emplace 反而更贵？</p>
<div class="qa-answer" markdown="1">

`push_back` 需要一个已经存在的对象，左值走拷贝、右值走移动；`emplace_back` 把参数完美转发给元素类型的构造函数，在容器存储上直接构造，省掉一次临时对象及其移动／拷贝。[293]

但对“本来就有对象”的调用，两者的代价可能相同甚至反过来：`v.push_back(std::move(x))` 是一次移动，`v.emplace_back(std::move(x))` 会调用移动构造，也是一次移动；`v.emplace_back(x)` 与 `v.push_back(x)` 都是一次拷贝。`emplace` 的优势出现在能直接给出构造参数的场合，例如 `v.emplace_back(3, "abc")` 一步构造 `std::string`，不必先造临时对象。

需要注意的边界：插入可能触发重分配并使已有元素的引用与迭代器失效，[293] 因此 `v.emplace_back(v[0])` 这类“参数引用容器自身元素”的写法会在重分配后用到失效引用，`v.push_back(v[0])` 也有同样问题，应先取副本或先 `reserve`。另外 `emplace` 允许显式构造，某些把花括号初始化列表与 `initializer_list` 构造混用的写法在 `push_back` 与 `emplace_back` 下会选择不同的重载；对关联容器还要区分 `emplace`、`insert` 与 `try_emplace` 在键已存在时的行为差异。

</div>
</article>

<article class="qa-item" id="qa-vector-capacity" data-level="basic" markdown="1">
<p class="qa-question">Q44 · vector 怎样扩容？reserve、resize、clear 和 shrink_to_fit 有何区别？</p>
<div class="qa-answer" markdown="1">

`size` 是当前元素数，`capacity` 是无需重分配即可容纳的元素数。`reserve` 请求容量，不创建新元素，也不改变 `size`；`resize` 改变元素数量，增长时初始化新增元素，缩小时销毁尾部元素；`clear` 销毁全部元素并使 `size` 归零，不是缩容请求。因此，即使已经 `reserve(100)`，空 `vector` 也不能直接访问下标 0 的元素。[18, 210]

插入后所需容量超过旧容量时，容器分配新存储并迁移元素；标准不规定统一的 1.5 倍或 2 倍增长策略。普通尾插具有摊还常数复杂度，但一次重分配仍需处理原有元素。反复在插入前请求刚够用的容量，还可能增加累计迁移工作量。[209, 210]

异常保证取决于操作和元素类型。对 `reserve` 以及满足相应类型条件的单元素尾插，失败可以保持原状态；若只能使用可能抛异常的移动构造，则不能无条件承诺这一保证。实现选择复制来维持保证，是常见的策略而非所有操作的统一算法。`shrink_to_fit` 只是非强制缩容请求；即使容器释放了旧存储，分配器保留和页面管理也使 RSS 未必立即下降。[210]

</div>
</article>

<article class="qa-item" id="qa-iterator-invalidation" data-level="basic" markdown="1">
<p class="qa-question">Q45 · 什么操作会使迭代器失效？遍历删除怎样写？</p>
<div class="qa-answer" markdown="1">

失效取决于具体容器和操作。`vector` 重分配使原有元素的迭代器、指针、引用及旧 `end()` 失效；不重分配的插入仍会使插入位置及其后的访问路径失效。删除也会影响被删除位置及其后继。`list` 删除只使被删元素的迭代器和引用失效，有序关联容器的删除也有相应节点保证；哈希容器 `rehash` 则使迭代器失效，却不使保留元素的指针和引用失效。[189, 210, 211]

`deque` 需要另行判断：两端插入会使迭代器失效，但保留已有元素的引用；中部插入还会使元素引用失效。删除最后一个元素会使旧 `end()` 失效，因此即使遍历位置已更新，预先缓存的结束迭代器也可能不再有效。[210]

对于返回后继迭代器的 `erase`，遍历删除可以用 `it = c.erase(it)`，保留元素时才执行 `++it`。这样后续迭代不再使用已删除元素的旧迭代器。元素地址是否仍有效，还受生命周期约束；不使迭代器失效的操作也不因此自动获得并发访问许可。[17]

</div>
</article>

<article class="qa-item" id="qa-ordered-hash" data-level="basic" markdown="1">
<p class="qa-question">Q46 · map 与 unordered_map 的底层结构、复杂度和使用条件是什么？</p>
<div class="qa-answer" markdown="1">

`map` 按比较关系维护键次序，支持有序遍历和范围查询；按键查找、普通插入及按键删除具有对数复杂度，不能据此推断所有删除接口都相同，例如按迭代器删除的复杂度另有规定。红黑树是常见实现，但标准约束行为与复杂度，并不指定唯一的树结构。[178, 189] `unordered_map` 按哈希和键等价关系组织，查找的平均复杂度为常数，最坏可为线性。[211]

有序容器的比较器需要建立严格弱序；哈希容器则要求等价键产生相同哈希，并且已有键的哈希和等价判定在容器内保持一致。反过来，哈希值相同不意味着键等价，碰撞后仍须用等价谓词区分候选键；桶接口也不规定所有实现都采用同一种链表节点布局。桶数量、负载因子和 `rehash` 也有成本，所以平均常数时间查找不等于所有操作都更快。范围查询和有序遍历倾向于有序结构，大量等值查找可以考虑哈希结构。复杂度还须与单次比较或哈希的成本分开：字符串键的处理量可能随长度增长。[178, 211]

</div>
</article>

<article class="qa-item" id="qa-key-comparator" data-level="basic" markdown="1">
<p class="qa-question">Q47 · map 的 key 能修改吗？自定义类型和浮点数能作键吗？</p>
<div class="qa-answer" markdown="1">

`map` 的元素类型是 `pair<const Key, T>`，普通迭代器允许修改映射值，却不允许直接修改键。C++17 起可以先用 `extract` 将节点移出容器，通过非空节点句柄的 `key()` 修改键，再重新插入，并处理新键与已有键等价而未能插入的情况。自定义键类型不必继承特定基类，但比较关系须满足严格弱序，且不能随外部可变状态使已有键的次序发生变化。[178, 212]

键的唯一性取决于比较器诱导的等价关系，即两个方向的比较都为假，而不一定取决于 `operator==`。这也解释了浮点 NaN 的问题：在通常的 NaN 比较语义下，0 与 NaN、NaN 与 1 都被普通 `<` 视为等价，0 与 1 却不等价，因而破坏等价关系的传递性。允许 NaN 的键域需要明确处理 NaN 或采用满足要求的排序策略；近似相等也不能未经检验就代替这一关系。哈希键还须使等价关系与哈希值一致。[178, 211, 216]

</div>
</article>

<article class="qa-item" id="qa-vector" data-level="principle" markdown="1">
<p class="qa-question">Q48 · vector 扩容会发生什么？reserve 能保证迭代器永远有效吗？</p>
<div class="qa-answer" markdown="1">

`vector<T>`（除 `bool` 特化等特殊情况）连续存放元素。容量不足导致重分配时，需要建立新存储，将元素移动或复制到新位置，再释放旧存储，原有指针、引用和迭代器因此失效。具体采用移动还是复制，受类型能力和异常保证等条件影响。[18]

`reserve` 可以为预期增长预留容量，但它自身如果改变容量也会使已有引用失效。后续增长超出容量仍会重分配；即使不重分配，中间插入或删除也可能使插入点或删除点之后的迭代器失效，旧 `end()` 也有单独规则。它不是永久地址稳定承诺。

尾部追加的均摊常数复杂度不等于每次追加都是常数时间。对按几何比例增长的教学模型，历次迁移量构成几何级数，总量与最终元素数同阶；实际增长系数由实现决定。连续布局改善局部性，但大规模重分配的单次时延仍可能影响服务尾时延。

</div>
</article>

<article class="qa-item" id="qa-unordered-rehash" data-level="principle" markdown="1">
<p class="qa-question">Q49 · unordered_map 的负载因子与 rehash 什么时候发生？哪些引用会失效？</p>
<div class="qa-answer" markdown="1">

负载因子是元素数与桶数之比，实现按最大负载因子决定何时扩容；`rehash` 与 `reserve` 可以显式调整桶数，[341] 标准对无序容器的要求是平均常数时间，最坏情况取决于实现与哈希质量。[297]

标准明确规定了 rehash 的失效范围：重新散列使迭代器失效、改变元素顺序、改变元素所在的桶，但不会使指向元素的指针与引用失效。[297] 因此可以把 `&it->second` 这类元素地址保存下来跨 rehash 使用，但不能保存迭代器，也不能在遍历过程中插入而不重新获取迭代器。

代价与选择也随之明确：不预留时，插入会周期性触发重新分配桶数组并重挂节点，单次操作的最坏代价与元素数同阶，均摊到插入是常数；上界可估时用 `reserve` 可以避免中途 rehash。把最大负载因子设得过高会增加冲突与查找长度，设得过低会浪费内存。哈希函数质量差或键有规律会让冲突集中，退化到接近线性；服务端若允许外部输入构造键，还要考虑碰撞攻击，这属于哈希函数与准入策略的决策，不是容器能自动处理的。

与有序容器相比：`map` 的插入与删除不使其它元素的迭代器失效，并提供有序遍历；`unordered_map` 只承诺平均常数查找，不承诺任何迭代顺序（结构差异见 [map 与 unordered_map 对比](#qa-ordered-hash)）。

</div>
</article>

<article class="qa-item" id="qa-template-inheritance" data-level="principle" markdown="1">
<p class="qa-question">Q50 · 模板、泛型与继承怎样取舍？为什么模板定义常在头文件？</p>
<div class="qa-answer" markdown="1">

模板按类型或值参数产生可实例化的定义，适合把同一算法用于不同类型，通常保留编译期优化空间；虚接口适合在运行时替换实现，或让调用方不依赖具体实现类。二者可以组合，并非“模板一定快、继承一定慢”。模板增加实例化和诊断负担，也可能增加生成代码；虚接口则有对象及调用边界成本。

隐式实例化需要相关定义满足可达性要求，因此模板实现通常放在头文件或其他可见的定义单元中。若实际使用的特化集合已知，也可在实现文件中给出定义并显式实例化相应特化，而不是要求每个调用单元重复持有实现。模板并非永远不能放在 `.cpp` 中，关键是所用特化的实例化安排。[213]

C++20 concepts 可以表达接口约束，但编译器接受一次调用不等于比较关系、生命周期和异常保证都已得到证明。例如 `sort` 要求随机访问迭代器和合适的元素操作；连续存储不是其必要条件，也不能仅凭容器能提供 `begin/end` 就认定它适用。[208, 216]

</div>
</article>

<article class="qa-item" id="qa-functor-lambda" data-level="principle" markdown="1">
<p class="qa-question">Q51 · 函数指针、仿函数、lambda 和 std::function 有什么区别？</p>
<div class="qa-answer" markdown="1">

函数指针指向相应函数，不直接携带任意捕获状态；仿函数是定义调用运算符的对象，可以把状态与调用行为放在一起；lambda 产生闭包对象，捕获决定其保存或借用哪些环境；std::function 用类型擦除统一保存符合条件的可调用目标。它们都能表达回调，但拥有关系和调用成本不同。

`std::function` 保存闭包并不意味着它拥有闭包借用的对象。按引用捕获的有效性取决于被引用对象的生命周期，捕获 `this` 也不自动延长所属对象的生命周期；异步执行期间，需要独立的拥有或退出协议保证这些对象仍有效。[218]

`std::function` 要求存储的目标满足可复制等条件，因此不能直接接收只有移动构造的闭包。复制包装器会复制其目标，但目标若保存引用或指针，仍可能继续观察同一外部对象。小对象优化的存储容量不是统一标准常量，部分目标构造也可能分配内存。[214] 具体类型的模板回调保留更多静态类型信息，类型擦除则统一接口；两者的取舍还包括编译依赖、状态复制和分配成本，不能仅凭调用形式判断服务的整体性能。

</div>
</article>

<article class="qa-item" id="qa-allocator-pmr" data-level="principle" markdown="1">
<p class="qa-question">Q52 · 分配器负责什么？STL 一定用小块自由链表吗？</p>
<div class="qa-answer" markdown="1">

不一定。分配器给容器提供取得、释放存储等协议，元素的生命周期再由容器通过相应机制管理；标准的分配器要求并不强制小块自由链表结构。[179] 这种池化设计通常按尺寸等级缓存已回收块，后续同类请求可以复用它们，代价是保留内存和维护空闲状态。具体实现也可以直接依赖底层分配器，或由自定义资源改变策略，不能把一个池的设计当成所有标准库的统一结构。

C++17 的 `polymorphic_allocator` 使用 `memory_resource` 选择具体存储资源，同一个静态分配器类型的不同实例可以在运行时采取不同策略。单调资源适合逐步建立对象、阶段结束后整体回收存储的场景：单次 `deallocate` 不回收相应块，`release` 才统一释放向上游取得的存储。这减少了逐块回收管理，却也使早已不再使用的容量可能保留到阶段结束。[215]

资源回收不代替元素析构，容器所保存的资源指针也不拥有该资源。所依赖的资源及初始缓冲必须在使用期间有效，必要的对象销毁应先于存储整体回收。容器交换和赋值还受到分配器传播、相等性要求约束；例如不传播分配器的容器交换，若两分配器不相等，就不能当作普通的无条件操作。类型对齐、失败、并发和跨资源释放同样属于接口约定，而不是实现小块链表后就自然满足。[57, 215]

</div>
</article>

<article class="qa-item" id="qa-algorithm-erase-sort" data-level="principle" markdown="1">
<p class="qa-question">Q53 · remove 会真正删除元素吗？sort 与 stable_sort 怎样选择？</p>
<div class="qa-answer" markdown="1">

通用 `std::remove/remove_if` 搬移保留元素并返回新的逻辑结尾，不改变容器的 `size`，也没有把尾部对象逐个销毁。新结尾之后的对象处于有效但未指定的状态，不能视为按原值保留的被删除元素集合。随后对容器执行相应 `erase`，才真正销毁并减少这些元素。`list` 的成员 `remove/remove_if` 则会直接擦除节点，与通用算法不同；C++20 的相应 `erase/erase_if` 重载也须按具体容器判断。[210, 216]

`sort` 不保证等价元素的原相对次序，`stable_sort` 保证稳定性。对于这里讨论的普通重载，以 N 表示元素数，`sort` 的比较次数为 <math xmlns="http://www.w3.org/1998/Math/MathML"><mi>O</mi><mo>(</mo><mi>N</mi><mi>log</mi><mi>N</mi><mo>)</mo></math>；`stable_sort` 在有足够额外存储时具有同阶比较量，否则比较次数上界可到 <math xmlns="http://www.w3.org/1998/Math/MathML"><mi>O</mi><mo>(</mo><mi>N</mi><msup><mi>log</mi><mn>2</mn></msup><mi>N</mi><mo>)</mo></math>。这些是比较次数的界，不是相同数量的运行时间单位。[216]

比较器须满足严格弱序，包括 `comp(x, x)` 为假以及比较和所诱导等价关系的传递性。`a <= b` 不满足前一条件，排序期间改变外部比较依据也可能破坏关系的一致性。通用排序要求随机访问迭代器，`list` 有自己的成员排序；选择应结合稳定性、元素操作和内存预算，而不是只比较算法名称。[216]

</div>
</article>

<article class="qa-item" id="qa-priority-queue" data-level="principle" markdown="1">
<p class="qa-question">Q54 · priority_queue 是什么结构？小根堆怎样配比较器？</p>
<div class="qa-answer" markdown="1">

`priority_queue` 是堆式优先访问的容器适配器，模板默认底层容器为 `vector`，也可使用满足随机访问及 `front/push_back/pop_back` 要求的其他序列容器。默认 `less` 比较使最大元素位于 `top`；对于相应数值类型，改用 `greater` 可以让最小元素优先。比较器定义的是相对次序，而不是一个绝对的优先级数值。[217]

插入先追加元素，再通过 `push_heap` 恢复堆；删除顶端先执行 `pop_heap`，再删除底层末尾元素。堆修复的比较次数具有对数界，但不能把这个界当成包含 `vector` 重分配在内的单次总成本。读取 `top` 不弹出元素，也要求队列非空。[217]

它不提供按任意位置修改元素并自动修复堆的接口；若任务优先级会变化，可用带版本的惰性记录、支持句柄的堆或另建索引，每种都有清理和一致性成本。top-K 中保存 K 个最大值时，用小根堆暴露当前最小入选值，对新值做比较后再替换；不能因为目标是“最大 K 个”就机械使用大根堆。比较关系与重复项、稳定排序需求仍需明确。

</div>
</article>

<article class="qa-item" id="qa-string-sso" data-level="principle" markdown="1">
<p class="qa-question">Q55 · std::string 的小字符串优化是什么？它对移动和指针稳定性有什么影响？</p>
<div class="qa-answer" markdown="1">

标准只规定 `basic_string` 的接口、连续存储要求与失效规则，不规定缓冲策略。[295] 常见实现把小字符串直接放在对象内部：libstdc++ 14.2.0 的 `basic_string.h` 第 207 行定义 `_S_local_capacity = 15 / sizeof(_CharT)`，在 64 位 `char` 版本上即 15 个字符加一个终止符；[294] 其它实现的容量与布局不同，因此本地容量阈值与 `sizeof(std::string)` 都不是可移植常量。

影响之一是移动的成本：短串没有可转移的堆指针，移动往往退化为复制本地缓冲中的字符，长串移动才是转移指针；标准对移动后状态只要求有效但未指定，因此“移动一定常数时间”对 `std::string` 不成立。

影响之二是地址稳定性：本地缓冲位于对象内部，`c_str()`／`data()` 在这种情况下指向对象自身；越过本地容量、或任何引起重新分配的操作都会改变地址并使引用、指针与迭代器失效。[295] 所以不要把 `const char*` 长期保存在 `std::string` 之外，接口约定应按“调用期间有效”表述，这一点与 `string_view` 的生命周期问题同源。

影响之三是对象开销：本地缓冲换来的是常见短串不分配，代价是对象更大、不是平凡可移动类型，构造时要初始化该缓冲。

</div>
</article>

<article class="qa-item" id="qa-string-view" data-level="principle" markdown="1">
<p class="qa-question">Q56 · std::string_view 为什么既便宜又容易悬垂？</p>
<div class="qa-answer" markdown="1">

`std::string_view` 只保存指针与长度，不拥有字符、不保证以 `'\0'` 结尾，拷贝视图不复制字符，因此参数用它可以同时接受 `std::string`、字符串字面量与子串而不产生分配。[296]

它的悬垂来源也正是“不拥有”。从临时字符串构造视图后返回或保存、把视图存进容器而源串随即被修改或重新分配、以及把某个局部字符串的 `substr` 视图传出作用域，都会让视图指向已失效存储；标准把生命周期责任交给使用者，编译器一般无法检查。

因此接口约定要写清楚：参数用 `string_view` 时说明“调用期间有效”，返回值不要返回指向临时对象或自身参数的视图，除非明确由调用方保证源存活；需要长期保存就复制成 `std::string`。空视图的 `data()` 可以是空指针，视图也不等于 C 字符串，传给依赖终止符的接口要显式转换。视图上的查找返回索引而不是迭代器，用时要与源串的生命周期一起考虑。

</div>
</article>

<article class="qa-item" id="qa-container-synchronization" data-level="principle" markdown="1">
<p class="qa-question">Q57 · 容器、迭代器和 shared_ptr 同时使用时，哪些线程安全保证可以叠加？</p>
<div class="qa-answer" markdown="1">

容器结构、元素对象、访问路径和拥有关系是四个不同层次。没有并发结构修改时，规定的只读或按只读处理的成员访问可以并发进行；标准还要求避免不同元素内容修改间的数据竞争，但明确排除 `vector<bool>`。这些保证不包括一边插入或重分配、一边继续使用旧迭代器，也不保护不同元素指向的同一外部可变对象。[17, 210]

不同 `shared_ptr` 句柄共享控制块时，其拥有状态的管理可以并发进行，却不自动保护指向对象或保存句柄的 `vector`。同一个普通 `shared_ptr` 变量的并发修改还需要独立同步。典型协议是在锁内查找并复制一份拥有句柄，使查找不与结构修改竞争；解锁后，局部句柄保持目标生命周期，目标字段则由另一同步协议保护。取得拥有权不是取得对象数据的独占访问权。[15–17]

</div>
</article>
