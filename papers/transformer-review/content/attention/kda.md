### KDA：门控细化到通道，并在半精度矩阵乘里成立

GDN 的门控是每个头一个标量，衰减只能把整个状态等比缩小。Kimi Delta 注意力（Kimi Delta Attention，KDA）把它换成逐通道的对角矩阵，每个键维度各有自己的遗忘速率；同时它必须回答一个工程问题：更细的门控为什么没有把内核拖慢。[50]（§3）

#### 更新式与它对应的 DPLR 结构

KDA 的状态更新写成：

<math display="block"><msub><mi>S</mi><mi>t</mi></msub><mo>=</mo><mrow><mo>(</mo><mi>I</mi><mo>−</mo><msub><mi>β</mi><mi>t</mi></msub><msub><mi>k</mi><mi>t</mi></msub><msubsup><mi>k</mi><mi>t</mi><mi>T</mi></msubsup><mo>)</mo></mrow><mi mathvariant="normal">Diag</mi><mo>(</mo><msub><mi>α</mi><mi>t</mi></msub><mo>)</mo><msub><mi>S</mi><mrow><mi>t</mi><mo>−</mo><mn>1</mn></mrow></msub><mo>+</mo><msub><mi>β</mi><mi>t</mi></msub><msub><mi>k</mi><mi>t</mi></msub><msubsup><mi>v</mi><mi>t</mi><mi>T</mi></msubsup><mo>,</mo><mspace width="1em"/><msub><mi>α</mi><mi>t</mi></msub><mo>∈</mo><msup><mrow><mo>[</mo><mn>0</mn><mo>,</mo><mn>1</mn><mo>]</mo></mrow><msub><mi>d</mi><mi>k</mi></msub></msup></math>

与 GDN 的式子相比，α 从标量换成了对角矩阵，两个因子不再可交换，乘法位置因此有了意义。GDN 的转移矩阵是 <math><msub><mi>α</mi><mi>t</mi></msub><mrow><mo>(</mo><mi>I</mi><mo>−</mo><msub><mi>β</mi><mi>t</mi></msub><msub><mi>k</mi><mi>t</mi></msub><msubsup><mi>k</mi><mi>t</mi><mi>T</mi></msubsup><mo>)</mo></mrow></math>，先读出未衰减的旧值、再整体缩放；KDA 的转移矩阵是 <math><mrow><mo>(</mo><mi>I</mi><mo>−</mo><msub><mi>β</mi><mi>t</mi></msub><msub><mi>k</mi><mi>t</mi></msub><msubsup><mi>k</mi><mi>t</mi><mi>T</mi></msubsup><mo>)</mo></mrow><mi mathvariant="normal">Diag</mi><mo>(</mo><msub><mi>α</mi><mi>t</mi></msub><mo>)</mo></math>，先逐通道衰减、再读出旧值做修正，写入项 <math><msub><mi>β</mi><mi>t</mi></msub><msub><mi>k</mi><mi>t</mi></msub><msubsup><mi>v</mi><mi>t</mi><mi>T</mi></msubsup></math> 不被同期衰减。结构上它属于对角加低秩（Diagonal-Plus-Low-Rank，DPLR）族：令 <math><mi>D</mi><mo>=</mo><mi mathvariant="normal">Diag</mi><mo>(</mo><msub><mi>α</mi><mi>t</mi></msub><mo>)</mo></math>、<math><msub><mi>a</mi><mi>t</mi></msub><mo>=</mo><msub><mi>β</mi><mi>t</mi></msub><msub><mi>k</mi><mi>t</mi></msub></math>、<math><msub><mi>b</mi><mi>t</mi></msub><mo>=</mo><msub><mi>k</mi><mi>t</mi></msub><mo>⊙</mo><msub><mi>α</mi><mi>t</mi></msub></math>，上式就是 <math><msub><mi>S</mi><mi>t</mi></msub><mo>=</mo><mo>(</mo><mi>D</mi><mo>−</mo><msub><mi>a</mi><mi>t</mi></msub><msubsup><mi>b</mi><mi>t</mi><mi>T</mi></msubsup><mo>)</mo><msub><mi>S</mi><mrow><mi>t</mi><mo>−</mo><mn>1</mn></mrow></msub><mo>+</mo><msub><mi>k</mi><mi>t</mi></msub><msubsup><mi>v</mi><mi>t</mi><mi>T</mi></msubsup></math>，并且 a 与 b 都由同一把键派生。[50]（§6.2）

这条约束决定了它的工程可行性：一般的 DPLR 允许 a、b 独立，表达能力更强，但分块计算里会出现累积衰减的倒数，数值上极易溢出或下溢。此前 GLA 一类做法在 log 域计算并在全精度下做二级分块（secondary chunking）来守住数值范围，代价是不能全程使用半精度矩阵乘。KDA 把 a、b 都绑到 k，倒数的因子就可以拆进两侧的乘法里，不再需要那些额外的全精度分块。[50]（§3.2、§6.2）

#### 分块算法：把逐元素缩放挤进矩阵乘两侧

块内累积转移与累积写入按递推展开，得到两个 Householder 乘积序列；把它们压成两个小矩阵，就是 WY 表示（这里采用 Comba 的形式，省掉一次额外的矩阵求逆）：[50]（Eq.2–3）

<math display="block"><msub><mi>P</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub><mo>=</mo><mi mathvariant="normal">Diag</mi><mo>(</mo><msubsup><mi>γ</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow><mi>r</mi></msubsup><mo>)</mo><mo>−</mo><munderover><mo>∑</mo><mrow><mi>i</mi><mo>=</mo><mn>1</mn></mrow><mi>r</mi></munderover><mi mathvariant="normal">Diag</mi><mo>(</mo><msubsup><mi>γ</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow><mrow><mi>i</mi><mo>→</mo><mi>r</mi></mrow></msubsup><mo>)</mo><msubsup><mi>k</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow><mi>i</mi></msubsup><msup><mrow><mo>(</mo><msubsup><mi>w</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow><mi>i</mi></msubsup><mo>)</mo></mrow><mi>T</mi></msup><mo>,</mo><mspace width="1em"/><msub><mi>H</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub><mo>=</mo><munderover><mo>∑</mo><mrow><mi>i</mi><mo>=</mo><mn>1</mn></mrow><mi>r</mi></munderover><mi mathvariant="normal">Diag</mi><mo>(</mo><msubsup><mi>γ</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow><mrow><mi>i</mi><mo>→</mo><mi>r</mi></mrow></msubsup><mo>)</mo><msubsup><mi>k</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow><mi>i</mi></msubsup><msup><mrow><mo>(</mo><msubsup><mi>u</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow><mi>i</mi></msubsup><mo>)</mo></mrow><mi>T</mi></msup></math>

其中 w、u 由与 DeltaNet 同形的递推给出，只是键内积多了按位置对加权的衰减。把这一叠秩一更新压成稠密矩阵，用 UT 变换一次解出：[50]（Eq.6–7）

<math display="block"><msub><mi>M</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub><mo>=</mo><msup><mrow><mo>[</mo><mi>I</mi><mo>+</mo><mi mathvariant="normal">StrictTril</mi><mrow><mo>(</mo><mi mathvariant="normal">Diag</mi><mo>(</mo><msub><mi>β</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub><mo>)</mo><mrow><mo>(</mo><msubsup><mi>Γ</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow><mrow><mn>1</mn><mo>→</mo><mi>C</mi></mrow></msubsup><mo>⊙</mo><msub><mi>K</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub><mo>)</mo></mrow><msup><mrow><mo>(</mo><mfrac><msub><mi>K</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub><msubsup><mi>Γ</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow><mrow><mn>1</mn><mo>→</mo><mi>C</mi></mrow></msubsup></mfrac><mo>)</mo></mrow><mi>T</mi></msup><mo>)</mo></mrow><mo>]</mo></mrow><mrow><mo>−</mo><mn>1</mn></mrow></msup><mi mathvariant="normal">Diag</mi><mo>(</mo><msub><mi>β</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub><mo>)</mo></math>

<math display="block"><msub><mi>W</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub><mo>=</mo><msub><mi>M</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub><mrow><mo>(</mo><msubsup><mi>Γ</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow><mrow><mn>1</mn><mo>→</mo><mi>C</mi></mrow></msubsup><mo>⊙</mo><msub><mi>K</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub><mo>)</mo></mrow><mo>,</mo><mspace width="1em"/><msub><mi>U</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub><mo>=</mo><msub><mi>M</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub><msub><mi>V</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub></math>

决定它在半精度下能不能成立的是括号里两个因子的写法：一个写成 <math><msubsup><mi>Γ</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow><mrow><mn>1</mn><mo>→</mo><mi>C</mi></mrow></msubsup><mo>⊙</mo><msub><mi>K</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub></math>，另一个写成 <math><msub><mi>K</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub><mo>/</mo><msubsup><mi>Γ</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow><mrow><mn>1</mn><mo>→</mo><mi>C</mi></mrow></msubsup></math>。两者相乘给出的正是位置对之间的衰减比 <math><msub><mi>γ</mi><mi>i</mi></msub><mo>/</mo><msub><mi>γ</mi><mi>j</mi></msub></math>，而式子本身仍是两次矩阵乘加一个 C×C 的下三角逆。倒数的数值风险被分摊到两个因子上，块内的衰减量级不再需要全精度才能算。三角逆用高斯消元的前向代入逐行求出，串行长度只有块宽 C。[50]（§3.1）

块间传递与块内输出沿用同一套因子拆分：[50]（Eq.8–9）

<math display="block"><msub><mi>S</mi><mrow><mo>[</mo><mi>t</mi><mo>+</mo><mn>1</mn><mo>]</mo></mrow></msub><mo>=</mo><mi mathvariant="normal">Diag</mi><mo>(</mo><msubsup><mi>γ</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow><mi>C</mi></msubsup><mo>)</mo><msub><mi>S</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub><mo>+</mo><msup><mrow><mo>(</mo><msubsup><mi>Γ</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow><mrow><mi>i</mi><mo>→</mo><mi>C</mi></mrow></msubsup><mo>⊙</mo><msub><mi>K</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub><mo>)</mo></mrow><mi>T</mi></msup><mrow><mo>(</mo><msub><mi>U</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub><mo>−</mo><msub><mi>W</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub><msub><mi>S</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub><mo>)</mo></mrow></math>

<math display="block"><msub><mi>O</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub><mo>=</mo><mrow><mo>(</mo><msubsup><mi>Γ</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow><mrow><mn>1</mn><mo>→</mo><mi>C</mi></mrow></msubsup><mo>⊙</mo><msub><mi>Q</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub><mo>)</mo></mrow><msub><mi>S</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub><mo>+</mo><mi mathvariant="normal">Tril</mi><mrow><mo>(</mo><mrow><mo>(</mo><msubsup><mi>Γ</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow><mrow><mn>1</mn><mo>→</mo><mi>C</mi></mrow></msubsup><mo>⊙</mo><msub><mi>Q</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub><mo>)</mo></mrow><msup><mrow><mo>(</mo><mfrac><msub><mi>K</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub><msubsup><mi>Γ</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow><mrow><mn>1</mn><mo>→</mo><mi>C</mi></mrow></msubsup></mfrac><mo>)</mo></mrow><mi>T</mi></msup><mo>)</mo></mrow><mrow><mo>(</mo><msub><mi>U</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub><mo>−</mo><msub><mi>W</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub><msub><mi>S</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub><mo>)</mo></mrow></math>

输出分两部分：跨块项用衰减加权后的查询直接读状态，块内项按 DeltaNet 的形状算。整段的非矩阵乘运算被压到逐元素缩放与一次前向代入，这是它能把主要算术交给张量核心的前提。[50]（§3.1）

#### 三个可核对的量

第一项是矩阵乘次数。相对一般 DPLR，KDA 把二级分块的矩阵运算从四次减到两次，又在块间与输出阶段省掉约三次矩阵乘，同长度下内核速度约为 DPLR 的两倍（测试到 64K）。[50]（§6.2、图 2）

第二项是算术量。按分块内核的实现口径，单头、块宽 C、序列长度 T 的训练浮点运算量为：[50]（Eq.13）

<math display="block"><msub><mi>FLOPs</mi><mi>KDA</mi></msub><mo>=</mo><mn>6</mn><mi>T</mi><msubsup><mi>d</mi><mi>h</mi><mn>2</mn></msubsup><mo>+</mo><mn>3</mn><mi>T</mi><mi>C</mi><msub><mi>d</mi><mi>h</mi></msub><mo>+</mo><mi>T</mi><msup><mi>C</mi><mn>2</mn></msup></math>

三项都对 T 线性，C² 是常数。取 d_h=128、C=64 得每个 token 约 126,976 次浮点运算；全注意力的主项是 <math><mn>2</mn><msup><mi>T</mi><mn>2</mn></msup><msub><mi>d</mi><mi>h</mi></msub></math>，同样配置下每 token 是 256T。两者相等的交叉点在 T≈496：短于它时全注意力的算术量更小，长于它时递推的线性优势逐段拉开。这条式子解释了为什么论文的比较从 4K 起步，也解释了为什么短上下文上混合模型与纯注意力打平。

第三项是状态容量。KDA 的状态是 dᵥ×dₖ 的矩阵，与上下文长度无关；混合模型中每四层才有一层保存 KV，长序列生成时这部分占用最多下降 75%。[50]（摘要、§4）

#### 把位置信息交给 KDA

Kimi Linear 的混合方式是每三层 KDA 接一层全注意力（MLA）。混合以整层为单位，不在层内按头分派，理由是基础设施简单、训练稳定。[50]（§4）另一项工程决定是位置编码：所有 MLA 层改用无位置编码（NoPE），位置与近因偏置完全由 KDA 承担。

这样做的依据可以写成一个与 RoPE 同形的式子。把带门控的 delta 规则展开成对历史的加权求和，第 t 个查询对第 i 个键的权重里含一段累积转移乘积：[50]（Eq.12）

<math display="block"><msub><mi>o</mi><mi>t</mi></msub><mo>=</mo><munderover><mo>∑</mo><mrow><mi>i</mi><mo>=</mo><mn>1</mn></mrow><mi>t</mi></munderover><mrow><mo>(</mo><msubsup><mi>q</mi><mi>t</mi><mi>T</mi></msubsup><mrow><mo>(</mo><munderover><mo>∏</mo><mrow><mi>j</mi><mo>=</mo><mi>i</mi><mo>+</mo><mn>1</mn></mrow><mi>t</mi></munderover><mi mathvariant="normal">Diag</mi><mo>(</mo><msub><mi>α</mi><mi>j</mi></msub><mo>)</mo><mrow><mo>(</mo><mi>I</mi><mo>−</mo><msub><mi>β</mi><mi>j</mi></msub><msub><mi>k</mi><mi>j</mi></msub><msubsup><mi>k</mi><mi>j</mi><mi>T</mi></msubsup><mo>)</mo></mrow><mo>)</mo></mrow><msub><mi>k</mi><mi>i</mi></msub><mo>)</mo></mrow><msub><mi>v</mi><mi>i</mi></msub></math>

RoPE 在同一位置放的是旋转矩阵的乘积，那组矩阵正交，因此可以拆到查询与键两端分别施加，得到只依赖相对距离的相位。KDA 的乘积是数据相关且非正交的，同样位置出现的是“衰减多少、修正多少”，因此相对位置信息由内容自己给出，不再需要固定的频率表。逐通道门控在这里承担了 RoPE 逐维频率的角色，这也是 KDA 必须把门控细到通道、而不能停在每头标量的原因。[50]（§6.1）

NoPE 还带来两项工程收益：MLA 在推理时可以退化成纯多查询注意力，只需缓存潜在状态；长上下文训练不再需要调频率底数或引入 YaRN 一类外推方法。[50]（§4）

#### 参数化与开源权重

q、k 走线性投影、短卷积、Swish 激活与 L2 归一化，v 走投影、短卷积与 Swish；β 由 sigmoid 给出标量，α 由一组秩等于头维的低秩投影加衰减函数生成，逐通道取值；输出前有逐头 RMSNorm 与低秩门控。键与值的头维都取 128。[50]（Eq.10）

开源权重 Kimi-Linear-48B-A3B 的配置给出了更硬的落地形态：27 层中 20 层是 KDA、7 层是全注意力（第 4、8、12、16、20、24、27 层），KDA 32 个头、头维 128、短卷积核宽 4；全注意力层是 MLA，潜在秩 512，键维与值维各 128。总参数 48B、激活 3B，前馈为 256 个路由专家、每 token 选 8 个加 1 个共享专家。

论文报告的结果带着 1.4T token 同配方训练的条件：MMLU-Pro 上 51.0，对照 GDN 混合 47.9、纯 MLA 47.2；128K 的 RULER 上 84.3，对照 80.5 与 81.3；1M 上下文解码每输出 token 1.84 ms，对照 MLA 的 11.48 ms，约 6.3 倍；预填充在 512K 与 1M 上分别是 2.3 倍与 2.9 倍。这些数字属于论文在其配置下的报告，底座、数据与内核版本不同，不能直接搬到其他模型上。

#### 细门控的代价落在哪

逐通道门控把 α 从一个标量变成 dₖ 维向量，每个头都要多做一组低秩投影与一次逐元素缩放；分块内仍有一次 C×C 的三角逆要做前向代入，块宽越大，这段串行计算越长，这也是块宽通常停在 64 的原因。混合结构里那 1/4 的全注意力层仍然要付完整的 KV 缓存与二次计算，精确检索能力主要靠它们兜底；纯 KDA 在长上下文检索上仍弱于同规模全注意力，论文的消融也显示 3:1 是质量与吞吐的折中，而非普适比例。

至于“更细的门控能否直接换成更强的表达力”，答案取决于转移矩阵是否仍落在可分块的族里。KDA 之所以能在半精度矩阵乘上成立，靠的正是把 a、b 绑到同一把键这一条约束；一旦放开这条约束回到一般 DPLR，内核就要重新面对全精度二级分块的开销。
