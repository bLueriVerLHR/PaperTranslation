### MiniMax MSA：每个 GQA 组挑自己的历史块

把选择粒度放到单个 token，精度最好，代价是路由变得零散：每个查询位置一套索引，几十个主头各自读不同的位置，GPU 上的分块矩阵乘拼不起来。MiniMax 稀疏注意力（MiniMax Sparse Attention，MSA）退一步处理这件事：选择在 GQA 组的粒度上做，一个组共用一套索引，组与组之间互不相同；被选中的单位是 token 块，粒度比单个 token 粗。[35] 这样既保留了内容相关的稀疏性，又把访存整理成连续的块。这里的 MSA 指 MiniMax 的这套机制，与多头自注意力、与蛋白质主题中的多序列比对都无关。

#### 每个 GQA 组选自己的历史块

设输入 X 为 `N × d_model`，主分支有 <math><msub><mi>H</mi><mi>q</mi></msub></math> 个查询头、<math><msub><mi>H</mi><mrow><mi>k</mi><mi>v</mi></mrow></msub></math> 个 KV 头，每组包含 G=<math><msub><mi>H</mi><mi>q</mi></msub></math>/<math><msub><mi>H</mi><mrow><mi>k</mi><mi>v</mi></mrow></msub></math> 个查询头。索引分支给每个组配一个 <math><msub><mi>d</mi><mi>i</mi></msub></math> 维的查询，索引键则在全部组之间共享，只保留一个头：[35]（§3.1，Eq.5–7）

```text
Q_idx:     [N, Hkv, d_i]
K_idx:     [N, 1,   d_i]
主分支 Q:  [N, Hq,  d_h]
主分支 K、V:[N, Hkv, d_h]
```

这两条索引投影与主分支的 Q／K 各自独立，选择器因此可以做得比主分支轻得多。把历史按 B 个 token 一块切开，块 b 的位置集合记为 ℬᵦ。对位置 t、组 r，先算每个可见 token 的索引点积，再取块内最大值作为这一块的分数：

<math display="block"><msubsup><mi>s</mi><mrow><mi>t</mi><mi>s</mi></mrow><mi>r</mi></msubsup><mo>=</mo><mfrac><mrow><msup><mrow><mo stretchy="false">(</mo><msubsup><mi>q</mi><mi>t</mi><mi>r</mi></msubsup><mo stretchy="false">)</mo></mrow><mi>T</mi></msup><msub><mi>k</mi><mi>s</mi></msub></mrow><msqrt><msub><mi>d</mi><mi>i</mi></msub></msqrt></mfrac><mo>,</mo><mspace width="1em"/><msubsup><mi>m</mi><mrow><mi>t</mi><mi>b</mi></mrow><mi>r</mi></msubsup><mo>=</mo><munder><mi mathvariant="normal">max</mi><mrow><mi>s</mi><mo>∈</mo><msub><mi>ℬ</mi><mi>b</mi></msub><mo>,</mo><mi>s</mi><mo>≤</mo><mi>t</mi></mrow></munder><msubsup><mi>s</mi><mrow><mi>t</mi><mi>s</mi></mrow><mi>r</mi></msubsup></math>

式中的 q、k 是索引向量，主分支另有自己的投影。看不见任何因果位置的块记为负无穷。按 m 取最高的 k 个块，其中包含当前位置的本地块固定入选，占用 k 个名额中的一个。主分支随后读取入选块里所有可见 token，按每个主查询头自己的分数做 softmax，读取上限因此是 k·B 个位置。

最大池化带来了一个可以预期的后果：块内只要有一个位置和当前查询匹配得上，整块就可能被读进来，邻近位置会一并被读入。把 B 调大，读取更连续、矩阵乘形状更规整，选择精度同时下降；把 B 调小则反过来。这是硬件友好度与内容粒度之间的实际取舍，调参时两个方向都要看。

举个例子。设当前位于块 3，预算 k=2，本地块占掉一个名额。组 A 认为块 1 比块 2 重要，组 B 的判断相反，于是 A 读 `{1, 3}`、B 读 `{2, 3}`，两组在同一层里走了不同的检索路线；每组内部的多个查询头仍在这些块内形成各自的概率分布。MSA 给组以自由，但没有把自由下放到每个头，理由是后者的路由与访存会重新变得不规则。

#### 教师分布取组内概率平均

索引选取同样不可微，MSA 用主分支当教师。在该组入选块覆盖的 token 上，先让每个主头各自 softmax，再对组内 G 个头求概率平均得到教师 P；索引分支在同一 token 集合上归一化，两边做 KL 对齐：[35]（§3.2，Eq.9–11）

<math display="block"><msubsup><mi>P</mi><mrow><mi>t</mi><mi>s</mi></mrow><mi>r</mi></msubsup><mo>=</mo><mfrac><mn>1</mn><mi>G</mi></mfrac><munder><mo>∑</mo><mrow><mi>h</mi><mo>∈</mo><msub><mi>ℋ</mi><mi>r</mi></msub></mrow></munder><msubsup><mi>a</mi><mrow><mi>t</mi><mi>s</mi></mrow><mi>h</mi></msubsup><mo>,</mo><mspace width="1em"/><msub><mi>ℒ</mi><mi mathvariant="normal">KL</mi></msub><mo>=</mo><mfrac><mn>1</mn><mrow><mi>N</mi><msub><mi>H</mi><mi mathvariant="normal">kv</mi></msub></mrow></mfrac><munder><mo>∑</mo><mrow><mi>t</mi><mo>,</mo><mi>r</mi></mrow></munder><msub><mi>D</mi><mi mathvariant="normal">KL</mi></msub><mo stretchy="false">(</mo><mi mathvariant="normal">stopgrad</mi><mo stretchy="false">(</mo><msup><mi>P</mi><mi>r</mi></msup><mo stretchy="false">)</mo><mo>‖</mo><msup><mi>P</mi><mi mathvariant="normal">idx</mi></msup><mo stretchy="false">)</mo></math>

ℋᵣ 是第 r 组的查询头集合，a 是各头在该集合上归一化后的主注意力概率，KL 两个分布省略了位置下标 t。教师端停止梯度，索引器输入 X 也停止梯度，辅助损失只更新两条索引投影：主分支继续由语言建模损失训练，索引器单独学“主分支会看哪里”。顺序上先跑一段全注意力做预热，等索引器大致对齐之后再切换到稀疏，训练时本地块始终强制保留。

到这里，MSA 与 DSA 的数字出现了一个巧合：两者都写着 2,048。DSA 是每个查询选 2,048 个 token、全部主头共用；MSA 是每个查询、每个 GQA 组各选 16 块 ×128 token，并且其中一块被本地块占住。连接图不同，底座、训练数据、头数与硬件也不同，这个数字对齐并不意味着两种方法可以互相替代或直接比高低。

#### 块稀疏没有消掉二次索引项

索引器依然要在全部因果位置上算一遍轻量分数，块最大值与 Top-k 削减的是随后主分支的读取集合。按论文的计数方式（一次乘加算 2 FLOPs，忽略投影与边界项），长序列下：

<math display="block"><msub><mi>F</mi><mi mathvariant="normal">GQA</mi></msub><mo>≈</mo><mn>2</mn><msub><mi>H</mi><mi>q</mi></msub><msub><mi>d</mi><mi>h</mi></msub><msup><mi>N</mi><mn>2</mn></msup></math>

<math display="block"><msub><mi>F</mi><mi mathvariant="normal">MSA</mi></msub><mo>≈</mo><msub><mi>H</mi><mi mathvariant="normal">kv</mi></msub><msub><mi>d</mi><mi>i</mi></msub><msup><mi>N</mi><mn>2</mn></msup><mo>+</mo><mn>4</mn><msub><mi>H</mi><mi>q</mi></msub><msub><mi>d</mi><mi>h</mi></msub><mi>N</mi><mi>k</mi><mi>B</mi></math>

第一项是索引分支，仍随 N² 增长，只是 <math><msub><mi>H</mi><mrow><mi>k</mi><mi>v</mi></mrow></msub></math>·<math><msub><mi>d</mi><mi>i</mi></msub></math> 远小于 <math><msub><mi>H</mi><mi>q</mi></msub></math>·<math><msub><mi>d</mi><mi>h</mi></msub></math>；第二项是主分支，固定 k·B 之后随 N 线性增长。序列继续加长，索引分支在总量中的占比会上升，这是这类两阶段结构的固有走向。

状态方面，MSA 仍然保留完整的、可供未来查询读取的主 K／V，另外多出一份索引键。当前少读一些块，与永久释放其余块是两回事：后面的查询完全可能选到它们。它降低的是主注意力的读取工作，与 MLA 那种直接压缩每个位置表示宽度的做法落在不同位置。短输入上，索引与选择的固定开销还可能超过省下的计算。

#### 从稀疏连接到 GPU 执行

第一步优化来自 softmax 的一个性质：它是保序的，同一行里 <math><msub><mi>s</mi><mi>i</mi></msub><mo>≤</mo><msub><mi>s</mi><mi>j</mi></msub></math> 与 <math><mi mathvariant="normal">softmax</mi><mo stretchy="false">(</mo><mi>s</mi><msub><mo stretchy="false">)</mo><mi>i</mi></msub><mo>≤</mo><mi mathvariant="normal">softmax</mi><mo stretchy="false">(</mo><mi>s</mi><msub><mo stretchy="false">)</mo><mi>j</mi></msub></math> 等价，因此选块直接用原始索引分数即可，省掉 max／exp／求和，Top-k 的结果不变。[35]（§4.1）主注意力与训练 KL 该做的归一化照做。

循环顺序决定访存能不能复用。按查询遍历，每个查询去收集自己选中的若干 KV 块，K／V 会被反复读取；按 KV 块遍历，先建一张反向索引，把选中该块的所有查询聚到一起，载入一份 K／V 就能服务多个查询和组内多个头。用论文给的一阶估计比较两种顺序的算术访存比（bf16，忽略次要项）：[35]（§4.2）

- 查询外层：FLOPs 为 4·<math><msub><mi>H</mi><mi>q</mi></msub></math>·N·<math><msub><mi>d</mi><mi>h</mi></msub></math>·k·B，IO 主要是 Q 与 O 的读写 4·<math><msub><mi>H</mi><mi>q</mi></msub></math>·N·<math><msub><mi>d</mi><mi>h</mi></msub></math> 加上 K／V 的读取 4·<math><msub><mi>H</mi><mrow><mi>k</mi><mi>v</mi></mrow></msub></math>·N·k·B·<math><msub><mi>d</mi><mi>h</mi></msub></math>，比值约为 G。
- KV 外层：K／V 只读一遍，Q 与局部输出缓冲按 k 倍放大，比值约为 <math><mfrac><mn>2</mn><mn>3</mn></mfrac><mi>B</mi></math>。

取论文的配置 G=16、B=128，两个比值分别是 16 与 85 左右，KV 外层高出数倍，因此实现选了后者。代回的代价也具体：热门块会被大量查询选中，一个 CTA 承担不了，需要沿查询方向切分并预先分配输出槽位；每个查询的输出被拆成 k 份，由不同 CTA 产生。

这些局部结果不能直接平均。若第 b 块的局部归一化输出为 oᵦ、其对数指数和为 Lᵦ，正确合并方式是按各自的概率质量加权：

<math display="block"><mi>L</mi><mo>=</mo><mi mathvariant="normal">log</mi><munder><mo>∑</mo><mi>b</mi></munder><mi mathvariant="normal">exp</mi><mo stretchy="false">(</mo><msub><mi>L</mi><mi>b</mi></msub><mo stretchy="false">)</mo><mo>,</mo><mspace width="1em"/><mi>o</mi><mo>=</mo><munder><mo>∑</mo><mi>b</mi></munder><mi mathvariant="normal">exp</mi><mo stretchy="false">(</mo><msub><mi>L</mi><mi>b</mi></msub><mo>−</mo><mi>L</mi><mo stretchy="false">)</mo><msub><mi>o</mi><mi>b</mi></msub></math>

实现里减去最大的 Lᵦ 以免指数溢出。这与在线 softmax 的归一化守恒是同一件事：分块计算的各部分要按自己的概率质量相加，按块数等权相加会得到另一个结果。收益是 KV 复用与更规整的矩阵乘，代价是反向索引、局部输出与 LSE 缓冲，以及一个额外的合并阶段。

论文的质量验证放在一个约 109B 总参数、每个 token 约 6B 激活参数的多模态 MoE 底座上：41 层，前 3 层稠密，其余 38 层为 MoE，64 个查询头、4 个 KV 头、头维 128、RoPE 维 64，每层 128 个路由专家加 1 个共享专家、每次选 4 个，训练 3T token；对比稠密 GQA、原生稀疏训练与从稠密检查点继续训练三条路线。[35]（§5.1–5.3）作者报告的结论支持这些设置下的可行性，换模型、换训练史仍是另一回事。本篇没有运行其内核，也没有复现这些测量。

#### 块内冗余与二次索引项都还在

MSA 的选择单位是块，块内只要有一个位置与当前查询匹配，整块就被读进来，这部分冗余随块长 B 上升；索引分支仍要在全部因果位置上算一遍轻量分数，二次项没有消失，只是系数从 <math><msub><mi>H</mi><mi>q</mi></msub></math>·<math><msub><mi>d</mi><mi>h</mi></msub></math> 换成了 <math><msub><mi>H</mi><mrow><mi>k</mi><mi>v</mi></mrow></msub></math>·<math><msub><mi>d</mi><mi>i</mi></msub></math>。它换来的是访存连续、组内共享与可提前调度的块形状，这三样决定稀疏在内核里能不能真的变成加速。

本章的机制到此分属三条改法：改单个位置的宽度（MQA、GQA、MLA）、改状态与历史长度的关系（核化线性注意力、RetNet、DeltaNet、GDN、KDA、SSM 与 RWKV）、改单次读取的集合（SWA、NSA、DSA、MSA）。三组成本要放在同一张表上，才能判断哪些数字可以直接相乘、哪些不能。
