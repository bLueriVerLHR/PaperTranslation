### MLA：把 KV 缓存压进一个潜在向量

MQA 与 GQA 都在“哪些查询头共用一份键值”上取值，键值本身的宽度没有变化。多头潜在注意力（Multi-head Latent Attention，MLA）换掉的是存储对象：先把键与值压缩成一个低维潜在向量存下来，用到时再展开。[32, 33]（§2.1）同一份缓存里因此能装下更多历史位置，或者在同一段历史上少读几个字节。

#### 联合低维参数化保留头间差异

用列向量来推内容分支。输入 xₜ 为 d 维，潜在向量 cₜ 为 d𝚌 维，由一个下投影产生；第 h 头的内容键和值各自由一个上投影展开：

<math display="block"><msub><mi>c</mi><mi>t</mi></msub><mo>=</mo><msub><mi>W</mi><mi>D</mi></msub><msub><mi>x</mi><mi>t</mi></msub><mo>,</mo><mspace width="1em"/><msubsup><mi>k</mi><mrow><mi>t</mi><mo>,</mo><mi>h</mi></mrow><mi>C</mi></msubsup><mo>=</mo><msubsup><mi>U</mi><mi>K</mi><mi>h</mi></msubsup><msub><mi>c</mi><mi>t</mi></msub><mo>,</mo><mspace width="1em"/><msub><mi>v</mi><mrow><mi>t</mi><mo>,</mo><mi>h</mi></mrow></msub><mo>=</mo><msubsup><mi>U</mi><mi>V</mi><mi>h</mi></msubsup><msub><mi>c</mi><mi>t</mi></msub></math>

`W_D` 的形状是 `d_c × d`，`U_K^h` 是 `d_h × d_c`，`U_V^h` 是 `d_v × d_c`，dₕ 专指内容查询与键的维度。各头共享 c，展开出来的键与值却各不相同。与 MQA 的差别正在这里：MQA 直接共用一份投影后的键值，MLA 共用的是生成键值的那份低维状态，头与头之间的差异由各自的展开矩阵提供。代价也随之出现：所有头的键值表示都要经过同一个瓶颈，d𝚌 决定了这个瓶颈能保留多少信息。

查询同样可以压缩后再上投影。查询只服务当前这一步计算，不需要像历史状态那样长期留在显存里，所以查询压缩省的是训练激活，与缓存压缩来自不同地方。[32]（§2.1.2）

#### 矩阵吸收：历史访问留在低维空间

设第 h 头的内容查询为 qᶜₜ,ₕ。忽略位置分支，它与历史位置 s 的打分可以重新结合：

<math display="block"><msup><mrow><mo>(</mo><msubsup><mi>q</mi><mrow><mi>t</mi><mo>,</mo><mi>h</mi></mrow><mi>C</mi></msubsup><mo>)</mo></mrow><mi>T</mi></msup><msubsup><mi>U</mi><mi>K</mi><mi>h</mi></msubsup><msub><mi>c</mi><mi>s</mi></msub><mo>=</mo><msup><mrow><mo>(</mo><msup><mrow><mo>(</mo><msubsup><mi>U</mi><mi>K</mi><mi>h</mi></msubsup><mo>)</mo></mrow><mi>T</mi></msup><msubsup><mi>q</mi><mrow><mi>t</mi><mo>,</mo><mi>h</mi></mrow><mi>C</mi></msubsup><mo>)</mo></mrow><mi>T</mi></msup><msub><mi>c</mi><mi>s</mi></msub></math>

据此，先把当前查询做一次线性变换，得到 d𝚌 维的“吸收后查询”，就能直接拿它和缓存的 cₛ 打分，无需为每个历史位置重建每头的内容键。归一化得到权重 aₜₛʰ 之后，值分支靠线性性同样可以后移：

<math display="block"><msub><mi>o</mi><mrow><mi>t</mi><mo>,</mo><mi>h</mi></mrow></msub><mo>=</mo><munder><mo>∑</mo><mrow><mi>s</mi><mo>≤</mo><mi>t</mi></mrow></munder><msubsup><mi>a</mi><mrow><mi>t</mi><mi>s</mi></mrow><mi>h</mi></msubsup><msubsup><mi>U</mi><mi>V</mi><mi>h</mi></msubsup><msub><mi>c</mi><mi>s</mi></msub><mo>=</mo><msubsup><mi>U</mi><mi>V</mi><mi>h</mi></msubsup><munder><mo>∑</mo><mrow><mi>s</mi><mo>≤</mo><mi>t</mi></mrow></munder><msubsup><mi>a</mi><mrow><mi>t</mi><mi>s</mi></mrow><mi>h</mi></msubsup><msub><mi>c</mi><mi>s</mi></msub></math>

把输出投影按头拆成 Oₕ，最终贡献就是 <math><munder><mo>∑</mo><mi>h</mi></munder><mo>(</mo><msub><mi>O</mi><mi>h</mi></msub><msubsup><mi>U</mi><mi>V</mi><mi>h</mi></msubsup><mo>)</mo><mo>(</mo><munder><mo>∑</mo><mi>s</mi></munder><msubsup><mi>a</mi><mrow><mi>t</mi><mi>s</mi></mrow><mi>h</mi></msubsup><msub><mi>c</mi><mi>s</mi></msub><mo>)</mo></math>，值上投影与输出投影可以合成一个矩阵，挪到汇聚之后。注意 softmax 的非线性原封不动：各头的 a 互不相同，先把各头平均再共用一次汇聚会得到另一个函数。[32]（§2.1.2）

这一串变换是运算顺序的重排，实现里并不需要真的把融合后的大矩阵显式存下来。吸收之后的点积与汇聚沿 d𝚌 维进行，代回 DeepSeek-V2 的取值 d𝚌=512 与单头 128 维，每个头的点积长度从 128 变成一个更大的量，每头算术量因此上升约四倍。于是取舍出现了：省下的是缓存读取，代价在别处。训练与预填充阶段查询多，展开成多头计算更顺手；小批解码从潜在缓存里读更划算。DeepSeek-V3.2 附录 A 把这两种执行视图称作 MLA 的 MHA mode 与 MQA mode，指的是同一个已训练模型的两条计算路径，不是两套模型。[34]（附录 A）

#### RoPE 为什么必须解耦

旋转位置嵌入（Rotary Position Embedding，RoPE）给查询和键施加随位置变化的旋转 Rₜ、Rₛ。若直接旋转展开后的内容键，打分里会出现：

<math display="block"><msup><mi>q</mi><mi>T</mi></msup><msubsup><mi>R</mi><mi>t</mi><mi>T</mi></msubsup><msub><mi>R</mi><mi>s</mi></msub><msubsup><mi>U</mi><mi>K</mi><mi>h</mi></msubsup><msub><mi>c</mi><mi>s</mi></msub></math>

Rₛ 夹在中间且随 s 变化。矩阵乘法不满足交换律，把上投影吸收到查询这一侧的前提就断了：每个历史位置都得重新算一遍键，缓存的收益随之消失。这是 MLA 与 RoPE 冲突的具体位置，与“低维向量装不下位置信息”无关。[32]（§2.1.3）

MLA 的处理是把内容与位置分开：每头的内容查询与位置查询各走一条路，每个历史位置另存一个跨头共享、已经旋转过的位置键 kʳ，维度 dᵣ。主分数由两项相加构成：

<math display="block"><msubsup><mi>ℓ</mi><mrow><mi>t</mi><mi>s</mi></mrow><mi>h</mi></msubsup><mo>=</mo><mfrac><mrow><msup><mrow><mo>(</mo><msubsup><mi>q</mi><mrow><mi>t</mi><mo>,</mo><mi>h</mi></mrow><mi>C</mi></msubsup><mo>)</mo></mrow><mi>T</mi></msup><msubsup><mi>U</mi><mi>K</mi><mi>h</mi></msubsup><msub><mi>c</mi><mi>s</mi></msub><mo>+</mo><msup><mrow><mo>(</mo><msubsup><mi>q</mi><mrow><mi>t</mi><mo>,</mo><mi>h</mi></mrow><mi>R</mi></msubsup><mo>)</mo></mrow><mi>T</mi></msup><msubsup><mi>k</mi><mi>s</mi><mi>R</mi></msubsup></mrow><msqrt><mrow><msub><mi>d</mi><mi>h</mi></msub><mo>+</mo><msub><mi>d</mi><mi>r</mi></msub></mrow></msqrt></mfrac></math>

内容项照旧可以吸收，位置项单独算，两项相加后走同一次 softmax。缓存因此需要放下 cₛ 与 kʳₛ 两份数据。DeepSeek-V2 的取值是 d𝚌=512、dᵣ=64，每层每个 token 缓存 576 个元素；按 2 字节算合 1,152 字节。同一层的 MHA 对照值是 32,768 个元素、64 KiB，两者相差约 57 倍。[32]（§2.1.3、§3.1.2）这只是有效张量容量，分页、尺度、对齐与工作区另算，也不能据此推出端到端有同倍加速。

#### 宽度压缩了，位置个数还在

MLA 压缩的是每个历史位置的表示宽度，历史位置的总数没有减少：新查询仍要访问全部可见的潜在状态，预填充阶段的成对计算照旧是二次规模，缓存也照旧随上下文线性增长，只是每个格子的字节数变小。要让主注意力少读一些位置，需要一层额外的选择机制，这既是稀疏注意力那条线的起点，也是 DSA 直接接在 MLA 之上的原因。
