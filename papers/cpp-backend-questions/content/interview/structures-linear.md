#### 复杂度与线性结构 {#interview-data-foundations}

<article class="qa-item" id="qa-complexity-model" data-level="basic" markdown="1">
<p class="qa-question">Q222 · 最坏、期望和均摊复杂度分别说明什么？空间换时间一定更快吗？</p>
<div class="qa-answer" markdown="1">

最坏界约束给定规模中最不利的输入，期望界依赖输入或算法随机性的概率模型，均摊界约束一系列操作的总成本；三者不能互换。复杂度还需要明确规模与基本操作，例如长字符串的一次比较不一定是常数成本。[118]

动态数组按固定倍率扩容时，少数追加需要搬迁大量元素，但此前扩容的搬迁量形成几何级数，因此连续追加的总搬迁量是线性阶，追加可有均摊常数界。它没有承诺每次追加的最坏耗时为常数，也没有假设输入随机。[18] 随机跳表的对数期望界则来自随机层高，属于另一类保证。[123]

缓存、索引和预计算用存储换取少做重复工作，却也增加构建、失效处理、同步和数据移动。工作集超过缓存容量时，新增结构反而可能扩大访问成本。渐近阶忽略常数和机器层次，不能单凭较低阶数断言某个服务的端到端时间更短。

</div>
</article>

<article class="qa-item" id="qa-array-list-cost" data-level="basic" markdown="1">
<p class="qa-question">Q223 · 数组和链表怎样选择？链表插入、删除为什么不总是常数时间？</p>
<div class="qa-answer" markdown="1">

数组用连续存储支持按下标定位，链表通过链接表达顺序，节点不要求物理连续。链表常数时间的局部修改以已取得所需节点和链接为前提；先按值或位置寻找目标仍可能遍历整表。分配、释放和元素析构也不是“改几根指针”的同义词。

动态数组中部插入通常移动后缀，扩容还可能迁移全部元素；连续表示有利于顺序扫描，但相应迭代器和地址可能失效。[18] 单链表删除通常需要前驱；双链表用额外链接使已定位节点更易摘除。链表省去后缀搬迁，却支付节点链接、分配元数据和指针追踪成本。

读多、密集扫描和下标访问倾向于数组；经常在已持有位置进行局部拼接时，链表才可能有价值。两种容器的收益都依赖元素大小、修改位置和所有权协议，不能按“插入多就用链表”概括所有工作负载。

</div>
</article>

<article class="qa-item" id="qa-linked-list-transform" data-level="basic" markdown="1">
<p class="qa-question">Q224 · 单链表怎样反转、找倒数第 k 个节点和合并？边界在哪里？</p>
<div class="qa-answer" markdown="1">

反转保存下一节点后改写链接；倒数第 k 个节点用两个指针保持 k 步间距；合并两个有序链表反复连接较小头节点。它们依赖有限、无环且访问期间不被并发修改的输入，不能只给循环而省略这些前提。

下面是原创 C++ 教学示例，不是上游摘录，也没有作为本机实测结果。节点及其 `next` 可写，调用者负责排他访问与节点寿命；算法不分配、不释放节点。

```cpp
struct ListNode {
    int value;
    ListNode* next;
};

ListNode* reverse_list(ListNode* head) {
    ListNode* reversed = nullptr;
    while (head != nullptr) {
        ListNode* remaining = head->next;
        head->next = reversed;
        reversed = head;
        head = remaining;
    }
    return reversed;
}
```

每轮已处理前缀变成反向链，未处理后缀仍由 `remaining` 保存；空表返回空指针。它访问每个节点一次，时间为 <math><mi>O</mi><mo stretchy="false">(</mo><mi>n</mi><mo stretchy="false">)</mo></math>，额外指针空间为常数。

倒数定位约定 k 从 1 开始，快指针先走 k 步；不足 k 个节点或 k 为零属于无有效结果，之后两指针同步前进直到快指针为空。合并还要求两输入各自有序且不共享节点，否则原地重连可能生成环；相等时先选第一条链可保持约定的稳定顺序。复制值与转移节点是不同的所有权方案。

</div>
</article>

<article class="qa-item" id="qa-stack-queue-ring" data-level="basic" markdown="1">
<p class="qa-question">Q225 · 栈、队列和优先队列有何区别？循环队列怎样区分满与空？</p>
<div class="qa-answer" markdown="1">

栈按当前元素的后进先出顺序访问，普通队列按入队顺序先进先出，优先队列按比较关系选择元素；优先队列不是 FIFO 的另一种实现。[119–120] 栈可在动态数组尾部追加和移除，队列可用首尾链接或环形数组，具体成本随底层表示变化。

环形数组的首尾下标相同可能表示空，也可能表示绕行一圈后的满。保存元素数、另设满标志或预留一个槽位都能消除歧义，但容量定义不同。下面的原创 C++17 教学示例用计数保留全部槽位；满时拒绝追加、空时返回无值，只用于单线程说明，不是无锁队列或实测实现。

```cpp
#include <cstddef>
#include <optional>
#include <stdexcept>
#include <vector>

class IntRing {
    std::vector<int> slots;
    std::size_t head = 0, tail = 0, count = 0;
public:
    explicit IntRing(std::size_t capacity) : slots(capacity) {
        if (capacity == 0) throw std::invalid_argument("zero capacity");
    }
    bool push(int value) {
        if (count == slots.size()) return false;
        slots[tail] = value;
        tail = (tail + 1) % slots.size();
        ++count;
        return true;
    }
    std::optional<int> pop() {
        if (count == 0) return std::nullopt;
        int value = slots[head];
        head = (head + 1) % slots.size();
        --count;
        return value;
    }
};
```

两个栈也能模拟队列：元素先进输入栈，输出栈为空时再一次性倒入，之后从输出栈弹出。每个元素只转移一次，因而操作有均摊常数界，某一次倒栈仍可能是线性工作。[120] 并发版本另外需要同步、发布顺序及对象寿命协议。

</div>
</article>
