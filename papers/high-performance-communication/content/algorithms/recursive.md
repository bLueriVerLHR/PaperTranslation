### 递归倍增：每轮扩大已知集合

在 <math><mrow><mi>p</mi><mo>=</mo><msup><mn>2</mn><mi>k</mi></msup></mrow></math> 的 AllGather 中，rank 可按二进制位选择伙伴：第 <math><mi>j</mi></math> 轮与编号异或 <math><msup><mn>2</mn><mi>j</mi></msup></math> 的 rank 交换。第一轮双方各有一个块，交换后各有两个；下一轮交换两个块，得到四个。各轮已知集合互不重叠，最终覆盖全通信域。

<math display="block"><mrow><munderover><mo>∑</mo><mrow><mi>j</mi><mo>=</mo><mn>0</mn></mrow><mrow><mi>k</mi><mo>−</mo><mn>1</mn></mrow></munderover><msup><mn>2</mn><mi>j</mi></msup><mfrac><mi>n</mi><mi>p</mi></mfrac><mo>=</mo><mfrac><mi>n</mi><mi>p</mi></mfrac><mo stretchy="false">(</mo><msup><mn>2</mn><mi>k</mi></msup><mo>−</mo><mn>1</mn><mo stretchy="false">)</mo><mo>=</mo><mfrac><mrow><mi>p</mi><mo>−</mo><mn>1</mn></mrow><mi>p</mi></mfrac><mi>n</mi></mrow></math>

这给出 <math><mrow><msub><mi>T</mi><mtext>RD-AG</mtext></msub><mo>=</mo><mi>k</mi><mi>α</mi><mo>+</mo><mfrac><mrow><mi>p</mi><mo>−</mo><mn>1</mn></mrow><mi>p</mi></mfrac><mi>n</mi><mi>β</mi></mrow></math>。它与环的发送总量相同，轮数更少，但每轮伙伴发生变化，后期消息更大。[1]（§4.1.3）

AllReduce 的“完整向量递归倍增”是另一种负载：每轮交换完整向量，并把两个互不重叠 rank 集合的归约结果合并。交换大小不随轮次增长，始终是 <math><mi>n</mi></math>；已归约的贡献集合增长。因此成本是 <math><mrow><mi>k</mi><mo stretchy="false">(</mo><mi>α</mi><mo>+</mo><mi>n</mi><mi>β</mi><mo>+</mo><mi>n</mi><mi>γ</mi><mo stretchy="false">)</mo></mrow></math>，不能套用 AllGather 的几何和。短消息可能受益于少轮数，长向量则支付更多重复传输。

### 递归折半：只保留最终归自己的一半

ReduceScatter 反向收缩数据责任范围。初始每个 rank 都有完整输入；第一轮按最终所有者分成左右半区，与另一半 rank 集合中的伙伴交换：把不归本子组的半向量发送出去，把收到的本半区与本地半区归约。下一轮在各自子组中再次折半。贡献集合逐轮扩大，仍需保留的数据范围逐轮缩小。

<figure>
<a href="assets/figures/21-halving-doubling.svg"><img src="assets/figures/21-halving-doubling.svg" alt="四 rank 递归折半和反向倍增"></a>
<figcaption>图 21：四 rank 递归折半和反向倍增</figcaption>
</figure>

对于 4 rank，可先配对 0↔2、1↔3，保留各自半区，再配对 0↔1、2↔3，保留各自四分之一区。每轮交换量为 <math><mrow><mi>n</mi><mo>/</mo><mn>2</mn><mo>，</mo><mi>n</mi><mo>/</mo><mn>4</mn><mo>，</mo><mo>…</mo><mo>，</mo><mi>n</mi><mo>/</mo><mi>p</mi></mrow></math>，其和也是 <math><mrow><mo stretchy="false">(</mo><mi>p</mi><mo>−</mo><mn>1</mn><mo stretchy="false">)</mo><mi>n</mi><mo>/</mo><mi>p</mi></mrow></math>。反向执行 AllGather，每轮拼回一个更大的区间，就得到折半—倍增 AllReduce：

<math display="block"><mrow><msub><mi>T</mi><mtext>HD-AR</mtext></msub><mo>=</mo><mn>2</mn><mi>k</mi><mi>α</mi><mo>+</mo><mn>2</mn><mfrac><mrow><mi>p</mi><mo>−</mo><mn>1</mn></mrow><mi>p</mi></mfrac><mi>n</mi><mi>β</mi><mo>+</mo><mfrac><mrow><mi>p</mi><mo>−</mo><mn>1</mn></mrow><mi>p</mi></mfrac><mi>n</mi><mi>γ</mi></mrow></math>

上述伙伴顺序保留输出块的 rank 顺序；另一些实现使用“向量折半、距离倍增”，减少某层网络的流量，却产生中间块置换。内部 AllReduce 可容许置换，公开 ReduceScatter 则要还原正确所有者。交换型归约容许更灵活的贡献重排；非交换型归约需要额外的顺序约束。[1]（§§4.1.3–4.1.4）[16]（RHD）

### 非二次幂：折叠不是免费操作

若 <math><mi>p</mi></math> 不是二次幂，直接异或可能产生域外编号。令 <math><mrow><mi>q</mi><mo>=</mo><msup><mn>2</mn><mrow><mo>⌊</mo><msub><mi>log</mi><mn>2</mn></msub><mi>p</mi><mo>⌋</mo></mrow></msup></mrow></math>。一种 AllReduce 调度先让 <math><mrow><mi>p</mi><mo>−</mo><mi>q</mi></mrow></math> 对 rank 合并输入，保留 <math><mi>q</mi></math> 个活动代表；代表完成二次幂算法后，再把结果还给暂时不活跃的伙伴。5 rank 就可以先把 rank 1 的输入并入 rank 0，四个代表完成归约，再由 0 把结果传给 1。[16]（RHD）

这增加完整向量的预归约和结果回传，还改变逻辑编号映射。因此 5 个参与者不能直接把四 rank 式中的 <math><mi>k</mi></math> 换成向上取整就算完。Binary Blocks 则把规模分成若干二次幂块，在块内及块间组织合并；它处理的是不规则规模，不是不同数据类型。[1]（表 2）本篇不把这类方案的不同具体块间调度压成一个通用成本式。
