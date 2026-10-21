#### 哈希、堆与概率结构 {#interview-data-hash}

<article class="qa-item" id="qa-hash-table" data-level="principle" markdown="1">
<p class="qa-question">Q230 · 哈希表的 O(1) 是怎样的保证？为什么仍要比较完整键？</p>
<div class="qa-answer" markdown="1">

哈希把键映射到位置，冲突处理允许不同键落入同一桶或同一探查区域。链式结构在相应桶中查找，开放寻址按探查规则继续寻找；哈希值相同不意味着键相同，最终相等判断仍属于查找协议。[37]

平均常数时间需要哈希分布、负载控制及具体模型等条件，单次最坏查找可能随元素数增长。扩容和重哈希本身也可能是线性工作，恶意输入或不适当哈希使理论平均值不能直接转化成服务尾时延保证。

`unordered_map` 适合不依赖键序的定位，`map` 的有序关系适合按键顺序访问和范围操作。不能把某种常见树或桶实现细节当作所有标准库的固定布局；选择还涉及内存、地址稳定性、迭代器规则与是否需要可预测的最坏界。

</div>
</article>

<article class="qa-item" id="qa-heap" data-level="principle" markdown="1">
<p class="qa-question">Q231 · 二叉堆为什么能维护优先级？建堆为什么不是必然 O(n log n)？</p>
<div class="qa-answer" markdown="1">

二叉堆用完全二叉树形状保持对数高度，用父子顺序不变量保证堆顶是极值。插入时沿祖先方向修复，删除堆顶后用末尾元素补位并向下修复，单次最坏工作量与树高同阶。它不是完整排序，同优先级的稳定顺序需要额外信息。[38]

逐个插入 n 个元素的通用上界是对数代价的累积；自底向上建堆则不同：大多数节点靠近叶子，只需很短的向下修复。把高度为 h 的节点数以 n／2 的 h 次方作宽松上界，总代价由下式控制，因级数收敛而为线性阶：

<math display="block"><mrow><mi>T</mi><mo stretchy="false">(</mo><mi>n</mi><mo stretchy="false">)</mo><mo>≤</mo><mi>C</mi><mi>n</mi><munderover><mo>∑</mo><mrow><mi>h</mi><mo>=</mo><mn>0</mn></mrow><mi>∞</mi></munderover><mfrac><mi>h</mi><msup><mn>2</mn><mi>h</mi></msup></mfrac><mo>=</mo><mn>2</mn><mi>C</mi><mi>n</mi></mrow></math>

这里 n 是元素数，C 吸收单层比较与交换的常数；整数层数及边界项不影响渐近结论。这个推导针对通常二叉堆的自底向上算法，不是所有堆结构或实现的性能保证。线程池的优先级队列也不会因为底层用堆，就自动抢占正在执行的任务。[9]

</div>
</article>

<article class="qa-item" id="qa-bloom" data-level="principle" markdown="1">
<p class="qa-question">Q232 · 布隆过滤器为什么允许误判却通常不漏判？哈希函数越多越好吗？</p>
<div class="qa-answer" markdown="1">

经典插入型布隆过滤器将每个键通过 k 个哈希位置置位；查询发现任一相应位为零，就能排除已经正确插入的键，全部为一只表示“可能存在”，因为这些位也可能由别的键共同置位。无漏判依赖过滤器正确包含待查集合、哈希规则一致、位没有被错误清除等条件。[11]

在 m 位、n 个插入元素、近似独立均匀哈希的模型中，一个位置仍为零的概率是 <math><msup><mrow><mo>(</mo><mn>1</mn><mo>−</mo><mfrac><mn>1</mn><mi>m</mi></mfrac><mo>)</mo></mrow><mrow><mi>k</mi><mi>n</mi></mrow></msup></math>，大 m 时近似为指数项。再作查询位置近似独立的假设，误判概率为：

<math display="block"><mrow><mi>p</mi><mo>≈</mo><msup><mrow><mo stretchy="false">(</mo><mn>1</mn><mo>−</mo><msup><mi>e</mi><mrow><mo>−</mo><mi>k</mi><mi>n</mi><mo>/</mo><mi>m</mi></mrow></msup><mo stretchy="false">)</mo></mrow><mi>k</mi></msup></mrow></math>

每加一个哈希减少全部查询位偶然命中的机会，却也增加位数组占用，因此 k 不是越大越好。将 k 当作连续变量优化上述近似式，得到 <math><mi>k</mi><mo>≈</mo><mfrac><mi>m</mi><mi>n</mi></mfrac><mi>ln</mi><mn>2</mn></math>，实际还需选择整数并考虑哈希成本。这是模型推导，不能用实际相关哈希或不断增长的集合无条件套用。

普通位数组不宜直接清位删除，否则可能抹掉其他键共享的位。新数据已经写入数据库而过滤器尚未同步时，系统也可能错误拒绝请求；过滤器自身的数学性质不保证跨系统更新协议没有漏判。

</div>
</article>
