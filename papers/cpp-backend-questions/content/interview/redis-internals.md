#### Redis 底层编码与数据结构 {#interview-redis-internals}

<article class="qa-item" id="qa-redis-sds" data-level="principle" markdown="1">
<p class="qa-question">Q209 · SDS 为什么不直接使用以零结尾的 C 字符串？记录长度与容量有哪些收益和成本？</p>
<div class="qa-answer" markdown="1">

C 字符串用首个零字节表示结尾，求长度通常要扫描，也不能仅凭该终止规则表达含内部零的字节序列。SDS（simple dynamic string，简单动态字符串）另外保存逻辑长度和相应分配信息，因此长度查询可以读取元数据，内部零字节也能作为内容。它仍保留结尾零，方便只处理相容内容的 C 接口；含内部零时用普通 strlen，结果仍会在首个零停止。[115]

Redis 7.2.6 按范围选用不同宽度的头；最小 type 5 把长度放在 flags 位中，其他相应头有 len 和 alloc 字段。数据指针指向字节区，而不直接指向头。这里使用具体 C 编译器的 packed 等属性，不能当作 ISO C++ 字符串的通用布局。[115]

逻辑长度和容量是两件事。固定版本的扩容路径先检查剩余空间，够用就复用；不足时计算所需容量，greedy 路径额外预留，而 non-greedy 只申请相应所需量。扩容本身不增加逻辑长度，调用者仍要写入内容并更新长度。预留能减少重复分配，却增加空闲与峰值；头类型改变时还要移动原有数据，不是每次追加都恒定成本。[256]

这些函数返回可能变化的新指针，调用者必须按约定更新拥有指针，不能保留已经失效的借用地址；分配失败返回空时，也不能盲目覆盖旧指针而丢失仍需管理的缓冲。二进制安全也依赖全链路使用正确长度，不能只把数据装进 SDS 就让后续 C 字符串函数自动安全。SDS 改进的是长度表示和容量管理，并不免除错误处理、长度边界或释放责任。

</div>
</article>

<article class="qa-item" id="qa-redis-dict-rehash" data-level="principle" markdown="1">
<p class="qa-question">Q210 · dict 怎样处理冲突和渐进式 rehash？迁移时为什么查找需要维护两张表？</p>
<div class="qa-answer" markdown="1">

Redis 7.2.6 的字典用桶定位候选，以链处理落入同桶的记录；良好散列下访问通常较便宜，冲突链变长仍增加比较。扩缩容不是仅更换一个容量数字，还要按新表大小重新安排记录位置。渐进式 rehash 把迁移分散到后续操作与相应维护机会，避免一轮搬完全部数据；迁移期间旧桶数组与新桶数组同时存在。[111]

下面是 Redis 7.2.6，固定提交 `ae6a2aa95cd094b032e7a69b8b59f64dd1ed085f`，`src/dict.c` 668–688 行的原文摘录。`dictFind` 在相应情况下推进迁移，再分别检查旧表和新表；未处于迁移时，查完首表即可停止。

```c
dictEntry *dictFind(dict *d, const void *key)
{
    dictEntry *he;
    uint64_t h, idx, table;

    if (dictSize(d) == 0) return NULL; /* dict is empty */
    if (dictIsRehashing(d)) _dictRehashStep(d);
    h = dictHashKey(d, key);
    for (table = 0; table <= 1; table++) {
        idx = h & DICTHT_SIZE_MASK(d->ht_size_exp[table]);
        he = d->ht_table[table][idx];
        while(he) {
            void *he_key = dictGetKey(he);
            if (key == he_key || dictCompareKeys(d, key, he_key))
                return he;
            he = dictGetNext(he);
        }
        if (!dictIsRehashing(d)) return NULL;
    }
    return NULL;
}
```

循环先检查旧表，再检查新表，是因为某个键可能还没搬迁。新插入在迁移状态下进入新表，搬完旧桶后清空其入口并推进 rehashidx；旧表已空时才释放旧桶数组并把新表接为常规表。暂停推进并不等于可以跳过其中一张表，查找仍须遵守当前迁移状态。[111]

该版本 dictRehash 以桶而非单键为迁移单位，并限制空桶访问预算；一个桶可能包含多条冲突记录，所以“每步只搬一个键”“每次绝对固定耗时”都不成立。额外桶数组、长链及分配仍有内存和尾时延成本，分步迁移不证明完全不影响性能。这里只读源码，未运行或测量 Redis；摘录保留原作者版权与 BSD 三条款条件，不属于本书原创段落的许可。[111]

</div>
</article>

<article class="qa-item" id="qa-redis-compact-layout" data-level="principle" markdown="1">
<p class="qa-question">Q211 · ziplist 的连锁更新是什么？listpack 和 quicklist 怎样改变存储组织？</p>
<div class="qa-answer" markdown="1">

ziplist 把多条记录放在连续内存里，每条记录还保存前驱记录的长度以便逆向定位。前驱变长后，后继的前驱长度字段可能从短表示扩为长表示；字段扩宽又使该后继总长度增加，从而触发再下一条的同类变化。这才是连锁更新，不是空间不足后把 ziplist 转换为普通链表。[112]

Redis 7.2.6 仍保留相关 ziplist 代码，`__ziplistCascadeUpdate` 的注释和控制流可以用来核对这种历史布局的问题；保留文件不代表该版本所有集合仍默认使用它。listpack 把逆向解析用的长度信息放在对应条目后面，取决于该条目自己的编码长度，不再以同一种前驱长度依赖向后传播。因此它避免的是这一类级联，而不是消除连续内存的插入、重分配和后缀移动。[112–113]

quicklist 是另一层组织：双向链式节点分别承载紧凑片段，不等于每个列表元素各有一对前后指针。片段较大时指针开销可摊薄，但局部插入和扫描可能处理更多连续数据；片段较小时又有更多节点及分配。固定 7.2.6 使用 listpack，旧版 quicklist 使用 ziplist，这两个版本不能混成一个不变布局。[116]

listpack 不是“分层的 quicklist 与压缩列表混合体”，quicklist 也不是 listpack 的改名。对象类型、片段内编码与片段间链接各解决不同问题；节约空间是有条件的取舍，阈值应结合成员大小和访问方式评估，不能仅凭紧凑二字宣称所有操作更快。

</div>
</article>

<article class="qa-item" id="qa-redis-intset-upgrade" data-level="principle" markdown="1">
<p class="qa-question">Q212 · intset 怎样查找与升级？删除大整数后会自动降级吗？</p>
<div class="qa-answer" markdown="1">

Redis 7.2.6 的 intset 把不重复整数按值排序，连续存放；同一实例统一采用 16、32 或 64 位编码，不是每个元素各自挑宽度。查找利用有序性作二分，每次比较缩小候选区间；中部插删却要移动后缀，不能把所有操作都称为常数时间。新整数超出当前宽度时，升级整个元素区后再加入它。[140]

以下是固定提交 `ae6a2aa95cd094b032e7a69b8b59f64dd1ed085f`，`src/intset.c` 166–173 行，`intsetUpgradeAndAdd` 的原文摘录。先扩大编码并调整存储，再从后往前按旧编码读、按新编码写，避免扩宽覆盖尚未转换的元素。

```c
    is->encoding = intrev32ifbe(newenc);
    is = intsetResize(is,intrev32ifbe(is->length)+1);

    /* Upgrade back-to-front so we don't overwrite values.
     * Note that the "prepend" variable is used to make sure we have an empty
     * space at either the beginning or the end of the intset. */
    while(length--)
        _intsetSet(is,length+prepend,_intsetGetEncoded(is,length,curenc));
```

新值超出旧编码范围，必在所有旧值之前或之后，prepend 给对应端点留位。先改编码字段，并不意味着可以按新宽度直接读取尚未转换的旧字节；这里显式用 curenc 读取旧表示，再按新表示写入。若从前往后扩宽写，后续旧数据可能被覆盖，反向遍历避免这一交叠问题。

升级仍需转换所有旧元素，是线性工作。例如原元素均为 16 位而新值要求 32 位，旧元素的有效载荷从每个 2 字节变成 4 字节；这只说明该元素区的增量，头部、新元素和分配器开销另计，不能把整个 Redis 键内存直接说成精确翻倍。

同一文件 248–251 行，`intsetRemove` 的删除路径如下。它移动后缀、按当前编码缩减元素数量和存储，未改编码字段；因此这个版本的删除不会自动退回更窄宽度。

```c
        if (pos < (len-1)) intsetMoveTail(is,pos+1,pos);
        is = intsetResize(is,len-1);
        is->length = intrev32ifbe(len-1);
    }
```

删除大值后，这条路径缩短数组而不改编码。剩余值若都能用较窄宽度表示，另行扫描检查并转换在数学上可以正确；不应把“实现没有降级”解释成“任何降级必然丢精度”。避免反复转换也是可以分析的成本取舍，但不是这里注释已经给出的历史设计动机。

intset 内部升级与整个 Redis Set 改用其他编码是两件事，后者还取决于成员形式、数量和版本配置；不能把删除一项当成自动退回所有更紧凑编码的承诺。摘录保留 Pieter Noordhuis 与 Salvatore Sanfilippo 的 BSD 三条款权利，未执行上游。[105,140]

</div>
</article>

<article class="qa-item" id="qa-redis-zset-dual-index" data-level="principle" markdown="1">
<p class="qa-question">Q213 · Redis 的 ZSet 为什么组合字典与跳表？重复分数、排名和范围怎样处理？</p>
<div class="qa-answer" markdown="1">

ZSet 同时需要按成员查分数，以及按分数／成员次序定位范围和名次。Redis 7.2.6 的相应跳表编码为此维护字典和跳表两个视图：字典按成员散列定位，跳表维护有序路径。散列分布与负载合适时，字典通常平均检查较少候选，但冲突及成员字节比较仍有成本，不保证任意输入都恒定时间。只用字典不能直接提供这种排序遍历，只用跳表按成员查找而没有分数等定位信息，又不能利用同样的字典访问路径。[141]

成员唯一而分数可重复。同一个成员改分数是维护原有成员的状态，不是允许它同时占两个成员位置；调用层负责检查和更新两套视图，zslInsert 注释明确要求调用者保证元素尚不存在，不能把任何跳表插入本身说成自动实施 ZSet 唯一约束。小对象还可能用 listpack，所以双索引不是所有 ZSet 的不变布局。[105,141]

以下是固定提交 `ae6a2aa95cd094b032e7a69b8b59f64dd1ed085f`，`src/t_zset.c` 145–152 行，`zslInsert` 原文摘录。沿层前进时先比较分数，同分再比较成员；span 累加跨过的节点数，供后续更新跨度。

```c
        while (x->level[i].forward &&
                (x->level[i].forward->score < score ||
                    (x->level[i].forward->score == score &&
                    sdscmp(x->level[i].forward->ele,ele) < 0)))
        {
            rank[i] += x->level[i].span;
            x = x->level[i].forward;
        }
```

这里先比较分数，同分再用成员字节次序区分，不是同分随机排列。高层链接跨过一段节点，span 记录该跨度；求秩时可累计跨过的数量，而不必总从底层逐项数起，底层后向链接则支持逆向遍历。随机层高让高层更稀疏，但范围返回仍必须访问相应结果，输出很多成员不会凭索引变成恒定成本。[141]

插删不仅改一条链接，还要协调跨度、前后链接和成员字典。字典与节点共享成员 SDS 时也不是两个独立拥有者，删除次序和释放责任必须对应，否则可能留下悬空引用或重复释放。双索引用额外空间和维护换取两类访问路径，不推出“跳表在所有场景必胜红黑树”，也不补造未经记录的历史动机或性能结论。[141]

</div>
</article>
