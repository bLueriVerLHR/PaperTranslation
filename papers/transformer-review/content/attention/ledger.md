### 三条轴上的成本对照

把本章的机制放到同一组单位上，差别落在三个方向上：每个历史位置留下多少、一次解码要读多少、每 token 要做多少成对计算；状态容量对递推类机制另记一项。下表按这三个方向排列，最后一列写各自新增的成本。表中 <math><msub><mi>H</mi><mi>q</mi></msub></math> 为查询头数、<math><msub><mi>H</mi><mrow><mi>k</mi><mi>v</mi></mrow></msub></math> 为键值头数、d 为每头维度、N 为历史长度、s 为当前已缓存长度；算术一列只保留主导项，常数因子省略。

| 机制 | 每历史位置的缓存 | 单步读取量 | 每 token 成对算术 | 主要新增成本 |
|---|---|---|---|---|
| MHA | <math><msub><mi>H</mi><mi>q</mi></msub></math>(<math><msub><mi>d</mi><mi>k</mi></msub></math>+<math><msub><mi>d</mi><mi>v</mi></msub></math>) | 与 N 成正比 | ≈ <math><msub><mi>H</mi><mi>q</mi></msub></math>·d·N² | 缓存随头数与长度双双增长 |
| GQA | <math><msub><mi>H</mi><mrow><mi>k</mi><mi>v</mi></mrow></msub></math>(<math><msub><mi>d</mi><mi>k</mi></msub></math>+<math><msub><mi>d</mi><mi>v</mi></msub></math>) | 与 N 成正比，按 <math><msub><mi>H</mi><mi>q</mi></msub></math>/<math><msub><mi>H</mi><mrow><mi>k</mi><mi>v</mi></mrow></msub></math> 缩小 | ≈ <math><msub><mi>H</mi><mi>q</mi></msub></math>·d·N² | 需继续预训练恢复质量 |
| MLA | <math><msub><mi>d</mi><mi>c</mi></msub></math>+<math><msub><mi>d</mi><mi>r</mi></msub></math> | 与 N 成正比，按宽度缩小 | ≈ <math><msub><mi>H</mi><mi>q</mi></msub></math>·<math><msub><mi>d</mi><mi>c</mi></msub></math>·N² | 表示受瓶颈约束、位置分支必须解耦 |
| 核化线性注意力 | 状态 r×<math><msub><mi>d</mi><mi>v</mi></msub></math>+r | 与 N 无关 | ≈ N·d·r | 有限维特征装不下指数核 |
| RetNet | 同上，加逐头衰减 | 与 N 无关 | 同上 | 衰减形状固定 |
| DeltaNet | <math><msub><mi>d</mi><mi>v</mi></msub></math>×<math><msub><mi>d</mi><mi>k</mi></msub></math> | 与 N 无关 | 同上，另加块内三角求解 | 并行化依赖 WY 表示 |
| GDN | <math><msub><mi>d</mi><mi>v</mi></msub></math>×<math><msub><mi>d</mi><mi>k</mi></msub></math> | 与 N 无关 | 同上，三角求解带逐元素权重 | α、β 投影与短卷积 |
| KDA | <math><msub><mi>d</mi><mi>v</mi></msub></math>×<math><msub><mi>d</mi><mi>k</mi></msub></math> | 与 N 无关 | ≈ N(6d² + 3Cd + C²)，C 为块宽 | α 的逐通道低秩投影与短卷积 |
| SSM（Mamba2） | 每头 P×N | 与 N 无关 | ≈ N·d·P | 专用扫描内核 |
| SWA | <math><msub><mi>H</mi><mi>q</mi></msub></math>(<math><msub><mi>d</mi><mi>k</mi></msub></math>+<math><msub><mi>d</mi><mi>v</mi></msub></math>)，长度封顶 W | 与 W 成正比 | ≈ <math><msub><mi>H</mi><mi>q</mi></msub></math>·d·N·W | 覆盖写入，远距离只能靠层数 |
| NSA | 完整历史加压缩键值 | ≈ s/d + n·l′ + w | 索引项 ≈ <math><msub><mi>H</mi><mrow><mi>k</mi><mi>v</mi></mrow></msub></math>·<math><msub><mi>d</mi><mi>i</mi></msub></math>·N²，主分支 ≈ N·k·B | 三分支投影、选择不可微 |
| DSA | 完整潜在状态 | ≈ k（论文取 2,048） | 索引项 ≈ N²·Hᴵ·dᴵ，主分支 ≈ N·k·d | 索引扫描、选择误差 |
| MSA | 完整历史加索引键 | ≈ k·B | 索引项 ≈ <math><msub><mi>H</mi><mrow><mi>k</mi><mi>v</mi></mrow></msub></math>·<math><msub><mi>d</mi><mi>i</mi></msub></math>·N²，主分支 ≈ N·k·B | 块内冗余、二次索引项 |

#### 一个统一配置下的量级

把三种改法放到同一个算例里：单层、批量 1、上下文 128K，缓存按 2 字节计。MHA 在每个 token 上留 64 KiB，一次解码要读 <math><mn>65536</mn><mo>×</mo><mn>131072</mn><mo>≈</mo><mn>8</mn></math> GiB；MLA 每 token 留 576 个元素、1,152 字节，读同一段历史约 141 MiB；DSA 只读 2,048 个潜在状态，约 2.3 MB；NSA 在 4 组 GQA、每 token 512 字节的配置下读约 5,632 个位置，约 2.8 MB。这几组数字横跨三个数量级，来源是三项互相独立的改动：压缩每个位置的宽度、把历史换成递推状态、限制单次读取的集合。它们是教学算例，没有计入分页、对齐、索引键与工作区，也不代表端到端时延。

#### 收益为什么不能直接相乘

宽度压缩与读取集合截断作用在同一个字节流上：先按 MLA 把每个位置压到 1,152 字节，再按 DSA 只读其中 2,048 个，两步的乘积才是读取量。换成 GDN 这类递推机制就不同了：它根本不读历史位置，缓存侧没有可再压缩的字节，与稀疏读取组合时省下的是同一份访存，不能按两个倍数叠乘。同理，SWA 把可读位置换成固定窗口之后，再对窗口内做 token 选择，收益也远小于两者各自的比例。

质量一侧的代价同样不能互抵。MQA 与 GQA 用共享换取带宽，代价是表示受限；MLA 用低秩瓶颈换取宽度，代价是表示被压进 <math><msub><mi>d</mi><mi>c</mi></msub></math> 维；递推机制用固定状态换取线性成本，代价是精确检索；稀疏机制用访问预算换取算力，代价是可能漏掉该读的位置。每一项都要在训练里验证，任何一项的收益都不自动抵消另一项的质量损失。

#### 按最先到上限的那一项选

选择机制时先确定当前部署先撞上哪一项约束，再沿对应轴找解：

- 容量先满、而上下文仍需延长：先看每个位置的宽度（GQA、MLA），再看是否必须保留逐位置可寻址能力。若检索精度要求高，MLA 是能保住全历史的方案；若可以接受状态压缩，递推类机制的容量与长度无关。
- 解码带宽先满、批量很小：头共享与潜在压缩的直接收益最明显，因为它们的收益直接作用在每步搬运的字节上；稀疏读取在批量小、上下文长时优势更大。
- 训练算力先满、序列很长：成对项是主项，线性注意力与稀疏读取都能把这一项降下来，但要接受额外的内核复杂度与训练不稳定风险。
- 需要精确长程检索：保留全历史的结构（MLA、稀疏读取）比固定状态更稳，混合结构把少量全注意力层留给检索，其余层换成递推，是当前开源权重里常见的折中。

模型往往会同时采用几种机制，例如潜在压缩加稀疏读取、递推层加窗口层。判断这类组合的效果，要按上面三条轴分别算它改的是哪一项，再看两项是否落在同一条字节流上；同一份访存被两次压缩只算一次收益，不同资源上的节省才谈得上叠加。
