### DeltaNet：把加法写入换成误差修正

衰减只管缩小旧内容，不管写进去的内容对不对。核化线性注意力的状态是若干个外积之和，同一把键被写入多次时，新值只是叠加上去，读出来的是所有历史值的混合。DeltaNet 换掉的是写入规则：写入前先读出当前键对应的旧值，只把“目标值与旧值之差”写进去。[39][41]（§2.2）

#### 一次写入只改一个秩一项

设第 t 步的键为 kₜ、值为 vₜ、写入强度为 <math><msub><mi>β</mi><mi>t</mi></msub><mo>∈</mo><mo>(</mo><mn>0</mn><mo>,</mo><mn>1</mn><mo>)</mo></math>。状态的更新写成两步：先读出旧值，再按差值写入：

<math display="block"><msub><mi>S</mi><mi>t</mi></msub><mo>=</mo><msub><mi>S</mi><mrow><mi>t</mi><mo>−</mo><mn>1</mn></mrow></msub><mo>−</mo><msub><mi>β</mi><mi>t</mi></msub><mo>(</mo><msub><mi>S</mi><mrow><mi>t</mi><mo>−</mo><mn>1</mn></mrow></msub><msub><mi>k</mi><mi>t</mi></msub><mo>−</mo><msub><mi>v</mi><mi>t</mi></msub><mo>)</mo><msubsup><mi>k</mi><mi>t</mi><mi>T</mi></msubsup><mo>=</mo><msub><mi>S</mi><mrow><mi>t</mi><mo>−</mo><mn>1</mn></mrow></msub><mrow><mo>(</mo><mi>I</mi><mo>−</mo><msub><mi>β</mi><mi>t</mi></msub><msub><mi>k</mi><mi>t</mi></msub><msubsup><mi>k</mi><mi>t</mi><mi>T</mi></msubsup><mo>)</mo></mrow><mo>+</mo><msub><mi>β</mi><mi>t</mi></msub><msub><mi>v</mi><mi>t</mi></msub><msubsup><mi>k</mi><mi>t</mi><mi>T</mi></msubsup></math>

右端的转移矩阵 <math><mrow><mo>(</mo><mi>I</mi><mo>−</mo><msub><mi>β</mi><mi>t</mi></msub><msub><mi>k</mi><mi>t</mi></msub><msubsup><mi>k</mi><mi>t</mi><mi>T</mi></msubsup><mo>)</mo></mrow></math> 是单位矩阵减去一个秩一项，属于广义 Householder 变换；βₜ=1 时旧值被完全替换，βₜ=0 时状态不动。把每次写入看成 kₜ 方向上的插值更直观：新值是 <math><msub><mi>β</mi><mi>t</mi></msub><msub><mi>v</mi><mi>t</mi></msub><mo>+</mo><mo>(</mo><mn>1</mn><mo>−</mo><msub><mi>β</mi><mi>t</mi></msub><mo>)</mo><msub><mi>S</mi><mrow><mi>t</mi><mo>−</mo><mn>1</mn></mrow></msub><msub><mi>k</mi><mi>t</mi></msub></math>，写入就是把旧值换成这个插值。输出仍由 <math><msub><mi>o</mi><mi>t</mi></msub><mo>=</mo><msub><mi>S</mi><mi>t</mi></msub><msub><mi>q</mi><mi>t</mi></msub></math> 给出。

这条规则有明确的优化解释。把状态看作一个把键映射到值的在线回归模型，第 t 步的损失取平方误差，一次梯度下降步长取 βₜ：

<math display="block"><msub><mi>ℒ</mi><mi>t</mi></msub><mo>(</mo><mi>S</mi><mo>)</mo><mo>=</mo><mfrac><mn>1</mn><mn>2</mn></mfrac><mo>‖</mo><mi>S</mi><msub><mi>k</mi><mi>t</mi></msub><mo>−</mo><msub><mi>v</mi><mi>t</mi></msub><msup><mo>‖</mo><mn>2</mn></msup><mo>,</mo><mspace width="1em"/><msub><mi>S</mi><mi>t</mi></msub><mo>=</mo><msub><mi>S</mi><mrow><mi>t</mi><mo>−</mo><mn>1</mn></mrow></msub><mo>−</mo><msub><mi>β</mi><mi>t</mi></msub><mi>∇</mi><msub><mi>ℒ</mi><mi>t</mi></msub><mo>(</mo><msub><mi>S</mi><mrow><mi>t</mi><mo>−</mo><mn>1</mn></mrow></msub><mo>)</mo></math>

展开梯度就回到上面的更新式。对照之下，核化线性注意力相当于优化负内积损失 <math><mo>−</mo><mo>⟨</mo><mi>S</mi><msub><mi>k</mi><mi>t</mi></msub><mo>,</mo><msub><mi>v</mi><mi>t</mi></msub><mo>⟩</mo></math>，它的梯度与预测误差无关：即使当前读出已经错得很远，写入量也不变。平方误差的梯度随误差增长，因此 DeltaNet 在预测错误时修正得更狠，这是它在关联召回任务上强于朴素线性注意力的机制来源。[41]（§2.2）

#### 状态容量可以算出来

把状态写成 <math><msub><mi>S</mi><mi>t</mi></msub><mo>=</mo><munder><mo>∑</mo><mrow><mi>i</mi><mo>≤</mo><mi>t</mi></mrow></munder><msub><mi>u</mi><mi>i</mi></msub><msubsup><mi>k</mi><mi>i</mi><mi>T</mi></msubsup></math> 的形式，代入上面的更新式并按归纳法展开，得到伪值的递推：

<math display="block"><msub><mi>u</mi><mi>t</mi></msub><mo>=</mo><msub><mi>β</mi><mi>t</mi></msub><mrow><mo>(</mo><msub><mi>v</mi><mi>t</mi></msub><mo>−</mo><munder><mo>∑</mo><mrow><mi>i</mi><mo>&lt;</mo><mi>t</mi></mrow></munder><msub><mi>u</mi><mi>i</mi></msub><mo>(</mo><msubsup><mi>k</mi><mi>i</mi><mi>T</mi></msubsup><msub><mi>k</mi><mi>t</mi></msub><mo>)</mo><mo>)</mo></mrow></math>

这一步说明三件事。其一，DeltaNet 并没有保存历史键值，它保存的是被改写过的伪值 uᵢ，读取时与线性注意力完全同形。其二，计算 uₜ 不需要把 S 显式算出来，只要知道已经写过的 uᵢ 与键的内积：计算 uₜ 只需 <math><mi>O</mi><mo>(</mo><mi>d</mi><mo>)</mo></math> 空间，显式维护一个 d×d 的状态才需要 <math><mi>O</mi><mo>(</mo><msup><mi>d</mi><mn>2</mn></msup><mo>)</mo></math>。其三，容量是算得出来的：若各 kᵢ 两两正交，交叉项 <math><msubsup><mi>k</mi><mi>i</mi><mi>T</mi></msubsup><msub><mi>k</mi><mi>t</mi></msub></math> 全为零，uᵢ=βᵢvᵢ，状态精确存下 dₖ 条关联；取 dₖ=128 就是 128 条。同一个模型换 MHA 显式缓存，32K 上下文能精确保留 32,768 个位置的键值。两者的检索精度差距主要来自这个容量上限，训练更充分难以弥平。

#### 并行化靠 WY 表示

伪值递推本身沿序列串行，直接算的总时间是 <math><mi>O</mi><mo>(</mo><msup><mi>L</mi><mn>2</mn></msup><mi>d</mi><mo>)</mo></math>。并行化利用的是 WY 表示（compact WY representation）把一叠 Householder 乘积压成两个小矩阵。在长度 C 的块内，累积转移矩阵与累积写入分别写成：

<math display="block"><msub><mi>P</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub><mo>=</mo><mi>I</mi><mo>−</mo><msubsup><mi>W</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow><mi>T</mi></msubsup><msub><mi>K</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub><mo>,</mo><mspace width="1em"/><msub><mi>H</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub><mo>=</mo><msubsup><mi>U</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow><mi>T</mi></msubsup><msub><mi>K</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub></math>

其中 W 与 U 由一个 C×C 的下三角逆一次性解出：

<math display="block"><msub><mi>T</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub><mo>=</mo><msup><mrow><mo>[</mo><mi>I</mi><mo>+</mo><mi mathvariant="normal">strictLower</mi><mo>(</mo><mi mathvariant="normal">diag</mi><mo>(</mo><msub><mi>β</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub><mo>)</mo><msub><mi>K</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub><msubsup><mi>K</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow><mi>T</mi></msubsup><mo>)</mo><mo>]</mo></mrow><mrow><mo>−</mo><mn>1</mn></mrow></msup><mi mathvariant="normal">diag</mi><mo>(</mo><msub><mi>β</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub><mo>)</mo></math>

<math display="block"><msub><mi>W</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub><mo>=</mo><msub><mi>T</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub><msub><mi>K</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub><mo>,</mo><mspace width="1em"/><msub><mi>U</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub><mo>=</mo><msub><mi>T</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub><msub><mi>V</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub></math>

块间状态与块内输出因此都只需要矩阵乘与一次三角求解：

<math display="block"><msub><mi>S</mi><mrow><mo>[</mo><mi>t</mi><mo>+</mo><mn>1</mn><mo>]</mo></mrow></msub><mo>=</mo><msub><mi>S</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub><mo>+</mo><msup><mrow><mo>(</mo><msub><mi>U</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub><mo>−</mo><msub><mi>W</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub><msubsup><mi>S</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow><mi>T</mi></msubsup><mo>)</mo></mrow><mi>T</mi></msup><msub><mi>K</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub></math>

<math display="block"><msub><mi>O</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub><mo>=</mo><msub><mi>Q</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub><msubsup><mi>S</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow><mi>T</mi></msubsup><mo>+</mo><mo>(</mo><msub><mi>Q</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub><msubsup><mi>K</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow><mi>T</mi></msubsup><mo>⊙</mo><mi>M</mi><mo>)</mo><mo>(</mo><msub><mi>U</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub><mo>−</mo><msub><mi>W</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow></msub><msubsup><mi>S</mi><mrow><mo>[</mo><mi>t</mi><mo>]</mo></mrow><mi>T</mi></msubsup><mo>)</mo></math>

这套形式让 DeltaNet 从只能在小任务上跑到 1.3B 参数、100B token 的规模。原文在相同条件下与 Mamba、GLA 等线性时间基线比较，报告的困惑度与零样本下游指标更好；把 DeltaNet 层与每两层插一个滑动窗口注意力、或与两个全局注意力层混合，得到的模型又能超过强 Transformer 基线。[41]（摘要、§1）这些是原文在其设置下的报告，换底座与数据仍要重测。

#### 剩下的两处

伪值递推里的 βₜ 是一个标量写强度，它决定这次修正多大，但不决定历史衰减多快；衰减仍由外部给定，与内容无关。把“忘多快”也做成输入相关的量，并把两者乘进同一个转移矩阵，就是 GDN 的改动。[42]（§3.1）
