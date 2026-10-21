### MoE：把参数容量与每个 token 计算分开

稠密 Transformer 里，每个 token 都要过同一套前馈权重，参数涨多少，每个 token 的计算量就跟着涨多少。MoE 把这份权重拆成 E 个互不共享的分支（专家），再用一个学出来的路由器为每个 token 挑 k 个执行。参数容量随 E 增长，单个 token 要付的专家算术量只按 k 计。Switch Transformer 用 Top-1 路由说明这种简化仍然训得起来，DeepSeek-V2 与 V3 在此之上加入细粒度专家、共享专家和偏置式负载均衡。[31–33]

#### 路由器决定调用哪几个分支

设单个位置的输入为 <math><mi>x</mi><mo>∈</mo><msup><mi>ℝ</mi><mi>d</mi></msup></math>，E 个路由专家各自给出 d 维输出 <math><msub><mi>F</mi><mi>e</mi></msub><mo stretchy="false">(</mo><mi>x</mi><mo stretchy="false">)</mo></math>。路由矩阵 <math><msub><mi>W</mi><mi>r</mi></msub><mo>∈</mo><msup><mi>ℝ</mi><mrow><mi>E</mi><mo>×</mo><mi>d</mi></mrow></msup></math> 打出 E 个分数，softmax 归一化后取 Top-k：

<math display="block"><mi>z</mi><mo>=</mo><msub><mi>W</mi><mi>r</mi></msub><mi>x</mi><mo>,</mo><mspace width="1em"/><msub><mi>p</mi><mi>e</mi></msub><mo>=</mo><mfrac><mrow><mi mathvariant="normal">exp</mi><mo stretchy="false">(</mo><msub><mi>z</mi><mi>e</mi></msub><mo stretchy="false">)</mo></mrow><mrow><munder><mo>∑</mo><mi>j</mi></munder><mi mathvariant="normal">exp</mi><mo stretchy="false">(</mo><msub><mi>z</mi><mi>j</mi></msub><mo stretchy="false">)</mo></mrow></mfrac><mo>,</mo><mspace width="1em"/><mi>S</mi><mo stretchy="false">(</mo><mi>x</mi><mo stretchy="false">)</mo><mo>=</mo><mi mathvariant="normal">TopK</mi><mo stretchy="false">(</mo><mi>p</mi><mo>,</mo><mi>k</mi><mo stretchy="false">)</mo></math>

TopK 返回的是专家索引。把入选分支的输出按门控权重相加，就得到这一子层的专家部分：

<math display="block"><msub><mi>g</mi><mi>e</mi></msub><mo>=</mo><mfrac><msub><mi>p</mi><mi>e</mi></msub><mrow><munder><mo>∑</mo><mrow><mi>j</mi><mo>∈</mo><mi>S</mi><mo stretchy="false">(</mo><mi>x</mi><mo stretchy="false">)</mo></mrow></munder><msub><mi>p</mi><mi>j</mi></msub></mrow></mfrac><mo>,</mo><mspace width="1em"/><mi>y</mi><mo>=</mo><munder><mo>∑</mo><mrow><mi>e</mi><mo>∈</mo><mi>S</mi><mo stretchy="false">(</mo><mi>x</mi><mo stretchy="false">)</mo></mrow></munder><msub><mi>g</mi><mi>e</mi></msub><msub><mi>F</mi><mi>e</mi></msub><mo stretchy="false">(</mo><mi>x</mi><mo stretchy="false">)</mo></math>

每个位置独立路由，同一句话里的不同 token、同一 token 在不同层，都可以落到不同专家上。稀疏发生在被执行的分支集合，专家内部仍是适合矩阵乘的稠密网络；共享专家若有，其输出另行加入 y，残差连接再加上 x。

上面这套写法在入选集合内重新归一化门控，Switch 的 Top-1 并不这么做：它保留原始 softmax 门值。这样一来，唯一入选者的门值并不恒等于 1，任务损失才能通过它对输出幅度施加影响。把 Top-1 的门值强行归一化为 1，等于切断了这条路径。离散的索引本身没有梯度，但入选集合固定时，连续门值与入选专家的输出照常可微，路由器的学习信号由此产生。DeepSeek-V3 改用了 sigmoid 亲和分数，再对入选分数归一化，并且给选择过程加了偏置。[31, 33]（分别见 §2.1、§2.1.2）

#### 总参数、激活参数与 FLOPs 是三件不同的事

设每个路由专家有相同参数量 <math><msub><mi>P</mi><mi mathvariant="normal">exp</mi></msub></math>，路由器、共享专家等常开部分合计 P₀，每个 token 选 k 个专家，那么：

<math display="block"><msub><mi>P</mi><mi mathvariant="normal">total</mi></msub><mo>=</mo><msub><mi>P</mi><mn>0</mn></msub><mo>+</mo><mi>E</mi><msub><mi>P</mi><mi mathvariant="normal">exp</mi></msub><mo>,</mo><mspace width="1em"/><msub><mi>P</mi><mi mathvariant="normal">active</mi></msub><mo>≈</mo><msub><mi>P</mi><mn>0</mn></msub><mo>+</mo><mi>k</mi><msub><mi>P</mi><mi mathvariant="normal">exp</mi></msub></math>

按这个定义算一个例子：保存 8 个等宽路由专家、每次调用 2 个，专家权重占用的存储是单专家的 8 倍，而每个 token 要做的专家矩阵乘只对应约 2 份。E 增加而 k 与专家宽度不变时，可选择的参数变多，路由、跨卡搬运和总权重存储一并增长。一批请求里的不同 token 会落到不同专家上，其并集完全可能覆盖全部专家，因此显存要按总参数准备。

激活参数也替换不了 FLOPs。长序列的注意力交互不体现在专家参数计数里，嵌入层的参数用法与专家层又不一样。MoE 的容量收益来自不同数据可以用到不同的参数子集，这份分工能不能形成，取决于数据、路由与优化过程，跟专家是否恰好对应“数学”“代码”这类可命名的领域没有关系。

DeepSeekMoE 把专家切得更细，并隔离出共享专家。[32]（§2.2.1）把专家宽度缩到 1/m、专家数与每次入选数同时扩大 m 倍，总专家参数和激活专家算术量大致不变，可组合的分支数却增加了。共享专家让每个 token 都走一条公共变换，路由专家于是不必各自重复承担通用成分。更细的分支也意味着更碎的工作和更大的路由扇出，组合数量的增加本身不构成质量保证。

#### 负载均衡同时影响训练与等待时间

路由集中到少数专家，冷门专家拿不到训练样本，热门专家要么溢出、要么拖住整个并行组。以 Switch 的 Top-1 为例，T 个 token 中真正送给专家 e 的比例为 fₑ，路由器对该专家的平均概率为 Pₑ，辅助项写成：[31]（§2.2）

<math display="block"><msub><mi>f</mi><mi>e</mi></msub><mo>=</mo><mfrac><mn>1</mn><mi>T</mi></mfrac><munder><mo>∑</mo><mi>t</mi></munder><mi mathvariant="normal">𝟙</mi><mo stretchy="false">[</mo><mi>S</mi><mo stretchy="false">(</mo><msub><mi>x</mi><mi>t</mi></msub><mo stretchy="false">)</mo><mo>=</mo><mo stretchy="false">{</mo><mi>e</mi><mo stretchy="false">}</mo><mo stretchy="false">]</mo><mo>,</mo><mspace width="1em"/><msub><mi>P</mi><mi>e</mi></msub><mo>=</mo><mfrac><mn>1</mn><mi>T</mi></mfrac><munder><mo>∑</mo><mi>t</mi></munder><msub><mi>p</mi><mi>e</mi></msub><mo stretchy="false">(</mo><msub><mi>x</mi><mi>t</mi></msub><mo stretchy="false">)</mo><mo>,</mo><mspace width="1em"/><msub><mi>ℒ</mi><mi mathvariant="normal">bal</mi></msub><mo>=</mo><mi>α</mi><mi>E</mi><munder><mo>∑</mo><mi>e</mi></munder><msub><mi>f</mi><mi>e</mi></msub><msub><mi>P</mi><mi>e</mi></msub></math>

Pₑ 在这里表示概率，与前文专家参数量的符号无关，两处各在自己的小节内使用。fₑ 由硬分派产生，反向时把当前 f 当作固定统计，梯度经由 Pₑ 回到路由器：负载偏高的专家受到抑制压力，偏低的获得鼓励。这是辅助损失给出的均衡压力，每一步并不严格等分，均衡本身也不证明语义分工最优。α 取大时，路由会优先照顾均衡，与“选到对当前数据有用的专家”这个目标发生竞争。

固定容量的实现按 <math><mi>C</mi><mo>=</mo><mo>⌈</mo><mi>φ</mi><mi>T</mi><mi>k</mi><mo>/</mo><mi>E</mi><mo>⌉</mo></math> 规划每个专家的槽位，φ 是容量因子，Switch 对应 k=1 的情形。φ 调大能容纳更多偏斜，代价是填充、缓冲和可能的无效计算。Switch 里溢出的 token 跳过这一专家子层，经残差继续往上走，序列位置本身并未消失。改用无丢弃的变长打包，实际负载、分组矩阵乘与尾部等待就落到实现层，失衡的成本从丢弃逻辑转移到实现。[31]（§2.2）

DeepSeek-V3 走的是另一条路线：给每个专家挂一个只参与排名的偏置 bₑ，按 <math><msub><mi>s</mi><mrow><mi>i</mi><mo>,</mo><mi>t</mi></mrow></msub><mo>+</mo><msub><mi>b</mi><mi>i</mi></msub></math> 排 Top-k，过载专家的偏置降低、空闲专家的偏置升高；输出混合权重仍由原始亲和分数算，偏置不进入前向数值。[33]（§2.1.2）这样一来，负载控制与输出幅度分开了：调偏置只改变谁被选中，不改变选中后的混合比例。所谓“辅助损失自由”针对的是主要均衡手段，报告仍保留一个系数极小的序列级辅助项，用于防止单条序列内部极端偏斜。批次级均衡、单序列偏斜和实际设备负载是三个不同的统计量，它们怎么转成通信与等待，取决于专家并行的放置方式。
