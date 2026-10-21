### GDN：门控与 delta 写进同一个转移矩阵

DeltaNet 补上了写入纠错，衰减仍是外部给定的常数；Mamba2 有输入相关的衰减，写入却是纯加法。门控 delta 网络（Gated Delta Network，GDN）把两者乘进同一个转移矩阵：衰减项 αₜ 与写强度 βₜ 都由当前输入产生，delta 结构保证写入只改一个秩一项，αₜ 决定整个状态先缩多少。[42]（§3.1）

<math display="block"><msub><mi>S</mi><mi>t</mi></msub><mo>=</mo><msub><mi>S</mi><mrow><mi>t</mi><mo>−</mo><mn>1</mn></mrow></msub><mrow><mo>(</mo><msub><mi>α</mi><mi>t</mi></msub><mo stretchy="false">(</mo><mi>I</mi><mo>−</mo><msub><mi>β</mi><mi>t</mi></msub><msub><mi>k</mi><mi>t</mi></msub><msubsup><mi>k</mi><mi>t</mi><mi>T</mi></msubsup><mo stretchy="false">)</mo><mo>)</mo></mrow><mo>+</mo><msub><mi>β</mi><mi>t</mi></msub><msub><mi>v</mi><mi>t</mi></msub><msubsup><mi>k</mi><mi>t</mi><mi>T</mi></msubsup><mo>,</mo><mspace width="1em"/><msub><mi>α</mi><mi>t</mi></msub><mo>∈</mo><mo stretchy="false">(</mo><mn>0</mn><mo>,</mo><mn>1</mn><mo stretchy="false">)</mo></math>

取 αₜ=1 就退回 DeltaNet，去掉 delta 结构就退回 Mamba2 的 <math><msub><mi>S</mi><mi>t</mi></msub><mo>=</mo><msub><mi>α</mi><mi>t</mi></msub><msub><mi>S</mi><mrow><mi>t</mi><mo>−</mo><mn>1</mn></mrow></msub><mo>+</mo><msub><mi>v</mi><mi>t</mi></msub><msubsup><mi>k</mi><mi>t</mi><mi>T</mi></msubsup></math>。合并不是符号上的拼合，两项各自解决一个具体问题。

#### 用在线学习目标读出两项各自的作用

把状态更新写成“对当前键值对做一步在线学习”的闭式解，几种机制就落在同一张表里。[42]（表 1，该框架引自在线学习视角的既有工作）按这个视角，每一步要解的目标由两部分组成：把新状态拉向上一步的正则项，和用当前键值对构造的回归项。GDN 的目标写成

<math display="block"><msub><mi>ℒ</mi><mi>t</mi></msub><mo stretchy="false">(</mo><mi>S</mi><mo stretchy="false">)</mo><mo>=</mo><msubsup><mrow><mo>‖</mo><mi>S</mi><mo>−</mo><msub><mi>α</mi><mi>t</mi></msub><msub><mi>S</mi><mrow><mi>t</mi><mo>−</mo><mn>1</mn></mrow></msub><mo>‖</mo></mrow><mi>F</mi><mn>2</mn></msubsup><mo>−</mo><mn>2</mn><mo>⟨</mo><mi>S</mi><msub><mi>k</mi><mi>t</mi></msub><mo>,</mo><msub><mi>β</mi><mi>t</mi></msub><mo>(</mo><msub><mi>v</mi><mi>t</mi></msub><mo>−</mo><msub><mi>α</mi><mi>t</mi></msub><msub><mi>S</mi><mrow><mi>t</mi><mo>−</mo><mn>1</mn></mrow></msub><msub><mi>k</mi><mi>t</mi></msub><mo>)</mo><mo>⟩</mo></math>

式中的双竖线为 Frobenius 范数，尖括号为两个矩阵的内积。正则项的系数从 1 换成 αₜ，回归项里的目标值从 vₜ 换成相对上一步预测的误差。把四种机制在这两处的取值依次列出，就得到下表。

| 机制 | 更新式 |
|---|---|
| 线性注意力 | S(t) = S(t−1) + v(t)k(t)ᵀ |
| Mamba2 | S(t) = α(t)S(t−1) + v(t)k(t)ᵀ |
| DeltaNet | S(t) = S(t−1)(I − β(t)k(t)k(t)ᵀ) + β(t)v(t)k(t)ᵀ |
| GDN | S(t) = S(t−1)(α(t)(I − β(t)k(t)k(t)ᵀ)) + β(t)v(t)k(t)ᵀ |

第一项是正则：它惩罚新状态偏离上一步的程度。系数取 1 表示强约束，状态只能小步移动，历史因此被保留；系数取 αₜ<1 表示放松约束，允许状态按当前输入偏离。状态越满，继续强行保留越会让多条信息叠在一起，读取时分辨不出对应关系，放松约束正是为这种情形准备的。第二项决定写入的形状：负内积对应“只往状态里加”，平方误差对应“先读出旧值再写差值”，后者在预测错得离谱时修正量也大。

两项的作用对象不同，因而可以叠加：门控管“留多久”，delta 管“写得准不准”。消融给出了这两件事的量级差别：在 400M 参数、15B token 的同条件下，把门控 delta 规则换成朴素 delta 规则，平均困惑度从 27.35 升到 30.87，平均零样本准确率从 47.26 降到 45.12。[42]（表 S.1）

#### 三种检索任务暴露三种失效

单针检索（Single Needle-in-a-Haystack，S-NIAH）把键值对埋进上下文，正是这几项机制针对性要解决的问题。原文在 1.3B 规模上做了三组变体，结论按失效类型分开：S-NIAH-1 用重复的合成上下文，只需记住极少信息，考的是长期保持；S-NIAH-2 把针埋进真实文章，考的是在容量有限的记忆里清理无关内容；S-NIAH-3 把值换成 UUID，考复杂模式的写入。[42]（§3.2、表 2）

三组结果的走向并不一致。在第一组上，DeltaNet 到 8K 仍是 98.8，Mamba2 从 2K 的 98.8 掉到 8K 的 30.4，GDN 是 91.8：衰减过快会伤长期保持，delta 结构把损失压住了。第二组上，DeltaNet 在 8K 只剩 14.4，Mamba2 是 17.0，GDN 升到 29.6：没有输入相关的清除手段，固定容量的状态会被无关内容占满。第三组上 Mamba2 掉到 4.6，GDN 仍有 27.6，差距来自写入的方式而非衰减。三组数字合起来说明，门控与 delta 各自覆盖一类失效，任何单独一项都会在另外两组上暴露短板。

#### 分块训练要把门控乘进三角求解

门控进入分块算法后，累积转移不再是 <math><msub><mi>P</mi><mrow><mo stretchy="false">[</mo><mi>t</mi><mo stretchy="false">]</mo></mrow></msub></math> 而是 <math><msub><mi>γ</mi><mrow><mo stretchy="false">[</mo><mi>t</mi><mo stretchy="false">]</mo></mrow></msub><msub><mi>P</mi><mrow><mo stretchy="false">[</mo><mi>t</mi><mo stretchy="false">]</mo></mrow></msub></math>，块内的键内积项也要按位置对衰减加权。原文的做法是把两个位置的累积衰减之比 <math><msub><mi>Γ</mi><mrow><mi>i</mi><mi>j</mi></mrow></msub><mo>=</mo><msub><mi>γ</mi><mi>i</mi></msub><mo>/</mo><msub><mi>γ</mi><mi>j</mi></msub></math> 逐元素乘进 K Kᵀ，三角求解因此变成：[42]（§3.3、附录 A）

<math display="block"><msub><mover><mi>U</mi><mo>~</mo></mover><mrow><mo stretchy="false">[</mo><mi>t</mi><mo stretchy="false">]</mo></mrow></msub><mo>=</mo><msup><mrow><mo>[</mo><mi>I</mi><mo>+</mo><mi mathvariant="normal">strictLower</mi><mo>(</mo><mi mathvariant="normal">diag</mi><mo stretchy="false">(</mo><msub><mi>β</mi><mrow><mo stretchy="false">[</mo><mi>t</mi><mo stretchy="false">]</mo></mrow></msub><mo stretchy="false">)</mo><mo>(</mo><msub><mi>Γ</mi><mrow><mo stretchy="false">[</mo><mi>t</mi><mo stretchy="false">]</mo></mrow></msub><mo>⊙</mo><msub><mi>K</mi><mrow><mo stretchy="false">[</mo><mi>t</mi><mo stretchy="false">]</mo></mrow></msub><msubsup><mi>K</mi><mrow><mo stretchy="false">[</mo><mi>t</mi><mo stretchy="false">]</mo></mrow><mi>T</mi></msubsup><mo>)</mo><mo>)</mo><mo>]</mo></mrow><mrow><mo>−</mo><mn>1</mn></mrow></msup><mi mathvariant="normal">diag</mi><mo stretchy="false">(</mo><msub><mi>β</mi><mrow><mo stretchy="false">[</mo><mi>t</mi><mo stretchy="false">]</mo></mrow></msub><mo stretchy="false">)</mo><msub><mi>V</mi><mrow><mo stretchy="false">[</mo><mi>t</mi><mo stretchy="false">]</mo></mrow></msub></math>

把逐位置的 γᵢγⱼ 直接相乘会放大数值误差：块长 64 时累积衰减可以小到 10⁻⁶ 量级，相乘后再求逆会把误差一起放大。取相邻位置的比值能把量级归一到 1 附近，原因在这一步。块间传递与块内输出沿用 DeltaNet 的形状，只需把查询、键与状态按各自方向加权：<math><msub><mover><mi>S</mi><mo>→</mo></mover><mrow><mo stretchy="false">[</mo><mi>t</mi><mo stretchy="false">]</mo></mrow></msub><mo>=</mo><msub><mi>γ</mi><mrow><mo stretchy="false">[</mo><mi>t</mi><mo stretchy="false">]</mo></mrow></msub><msub><mi>S</mi><mrow><mo stretchy="false">[</mo><mi>t</mi><mo stretchy="false">]</mo></mrow></msub></math>、<math><msub><mover><mi>q</mi><mo>←</mo></mover><mrow><mo stretchy="false">[</mo><mi>t</mi><mo stretchy="false">]</mo></mrow></msub><mo>=</mo><msub><mi>γ</mi><mrow><mo stretchy="false">[</mo><mi>t</mi><mo stretchy="false">]</mo></mrow></msub><msub><mi>q</mi><mrow><mo stretchy="false">[</mo><mi>t</mi><mo stretchy="false">]</mo></mrow></msub></math>、<math><msub><mover><mi>k</mi><mo>→</mo></mover><mrow><mo stretchy="false">[</mo><mi>t</mi><mo stretchy="false">]</mo></mrow></msub><mo>=</mo><mo stretchy="false">(</mo><msub><mi>γ</mi><mrow><mo stretchy="false">[</mo><mi>t</mi><mo stretchy="false">]</mo></mrow></msub><mo>/</mo><msub><mi>γ</mi><mi>i</mi></msub><mo stretchy="false">)</mo><msub><mi>k</mi><mi>i</mi></msub></math>。多出来的计算是 α、β 两条投影与一次逐元素缩放，块内仍只有一次三角逆与几次矩阵乘。

参数侧与 DeltaNet 的差别不大：查询、键、值各走一条线性投影加短卷积，查询与键再做 L2 归一化，α、β 只用线性投影。[42]（§3.4）这些细节决定训练稳定性，不改变上面的状态口径。

#### 单层递推在检索上的短板要靠混合补

纯递推模型在真实检索任务上仍落后同样规模的注意力模型，原文把原因分为两类：固定状态容量装不下精确的键值检索，线性结构本身也不擅长局部比较与位置平移。[42]（§3.4、§4）它的应对是把 GDN 层与滑动窗口注意力交替堆叠，形成混合模型：H1 是 GDN 与 SWA 交替，H2 再加入 Mamba2 层。在 1.3B 参数、100B token、窗口 2K 的同条件下，纯 GDN 在常识推理平均分上是 55.32，H1 是 56.40；在 LongBench 的 14 项平均上分别是 16.6 与 17.8，而对照的 Transformer++ 是 11.0。[42]（表 3、表 5）原文同时指出，混合模型的检索提升主要来自那些注意力层，递推层提供的仍是线性成本的长程压缩。

这个取舍在开源权重里可以看到具体配置。Qwen3-Next-80B-A3B 的模型卡写明用门控 delta 网络与门控注意力组合替换标准注意力，[49] 配置里 48 层按每 4 层一个全注意力层排列，其余为线性层；线性层的键头 16 个、值头 32 个、头维 128、短卷积核宽 4，全注意力层是 16 个查询头配 2 个键值头、头维 256、只对四分之一的维度施加旋转位置嵌入。厂商报告给出的对照是：相对 Qwen3-32B，训练成本约为十分之一，32K 以上上下文的推理吞吐约十倍。[49] 这些数字属于厂商自述，没有独立复现，只说明这套组合在实际模型规模上被采用过。
