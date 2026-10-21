## 术语对应表

本篇采用下列用词。英文原词与中文用语并列登记，正文按“本篇用语”一列书写；token 这类没有通行译名的词直接写英文，不再另造译名。模型名、API 和代码标识保持原样。

| 英文术语 | 本篇用语 | 说明 |
|---|---|---|
| token | token | 序列处理单位；文本中可为词、子词或其他离散单位 |
| tokenization / tokenizer | tokenization／tokenizer | 输入划分过程／相应工具；不默认以单词为边界 |
| patch | 图块（patch） | 图像的几何划分，不天然是物体或语义区域 |
| embedding | 嵌入（embedding） | 向量表示；与 token 身份或原始像素区分 |
| hidden state | 隐藏状态 | 某层的位置表示，不等于全部程序执行状态 |
| query / key / value | 查询／键／值（Q／K／V） | 注意力的匹配与汇聚分工，不指数据库字段 |
| self-attention | 自注意力 | 查询、键和值来自同一输入序列的表示 |
| cross-attention | 交叉注意力 | 查询与键／值来自不同表示集合 |
| multi-head attention (MHA) | 多头注意力（MHA） | 多组投影并行计算，之后拼接和投影；标准形式中各头有独立 K／V |
| multi-query attention (MQA) | 多查询注意力（MQA） | 多个查询头共享同一套 K／V，不是只保留一个查询头 |
| grouped-query attention (GQA) | 分组查询注意力（GQA） | 组内查询头共享 K／V；分组不指切分输入序列 |
| multi-head Latent Attention (MLA) | 多头潜在注意力（MLA） | 联合低维参数化内容 K／V，缓存潜在向量及解耦的位置键 |
| linear attention / kernelized linear attention | 线性注意力／核化线性注意力 | 把相似性写成有限维特征內积，交换求和顺序，用累计状态代替逐位置键值 |
| state | 状态 | 递推机制用矩阵或向量汇总的历史，不等同于 KV 缓存，也不保证逐位置可寻址 |
| decay | 衰减 | 旧状态按位置距离或输入系数缩小的机制；标量、通道向量与逐头取值需分别说明 |
| delta rule / write strength | delta 规则／写强度 | 用目标值减当前读值修正状态的写入规则；写强度 β 越大修正越彻底 |
| gated delta network (GDN) | 门控 delta 网络（GDN） | 在 delta 规则上乘输入相关的逐头衰减 α；不是门控注意力的别名 |
| Kimi Delta Attention (KDA) | Kimi Delta 注意力（KDA） | 把 GDN 的逐头标量门控换成逐通道对角门控；名称保留 |
| diagonal-plus-low-rank (DPLR) | 对角加低秩（DPLR） | 转移矩阵形如 D − abᵀ 的状态演化族；可分块但数值与吞吐代价各异 |
| WY representation | WY 表示 | 把一叠 Householder 乘积压成两个小矩阵的紧凑形式，使分块训练可用矩阵乘 |
| state space model (SSM) / selection | 状态空间模型（SSM）／选择性 | 连续时间系统离散化后的递推；选择性指 Δ、B、C 随输入变化 |
| RWKV | RWKV | 从线性注意力出发、衰减写成通道向量的递推结构；名称保留 |
| Native Sparse Attention (NSA) | 原生稀疏注意力（NSA） | 压缩、选择、窗口三条分支并联，在预训练阶段就打开稀疏 |
| needle-in-a-haystack (NIAH) / S-NIAH | 单针检索（S-NIAH） | 把键值对埋进长上下文并要求原样取回的合成评测；S-NIAH 指单针变体 |
| L2 normalization | L2 归一化 | 把查询与键的范数缩到单位长度的归一化，用于稳定递推类机制的训练 |
| DeepSeek Sparse Attention (DSA) | DeepSeek 稀疏注意力（DSA） | 用轻量索引器选择历史 token，主分支在入选集合上计算 |
| MiniMax Sparse Attention (MSA) | MiniMax 稀疏注意力（MSA） | 每个 GQA 组独立选历史块；与多头自注意力、多序列比对同名不同义 |
| lightning indexer / index branch | 轻量索引器／索引分支 | 为主注意力选择候选的代理，不等于主注意力权重 |
| attention mask | 注意力掩码 | 限定位置可见性；不等同输入中的 `[MASK]` token |
| causal attention | 因果注意力 | 禁止访问未来位置，不是因果推断的充分条件 |
| positional encoding / embedding | 位置编码／位置嵌入 | 一般位置表征／具体嵌入参数，按方法区分 |
| Rotary Position Embedding (RoPE) | 旋转位置嵌入（RoPE） | 依位置旋转查询／键；MLA 将位置分支与可吸收的内容分支分开 |
| residual connection | 残差连接 | 将子块输出与旁路输入相加 |
| LayerNorm | 层归一化（LayerNorm） | 名称保留；归一化位置依架构而变 |
| feed-forward network (FFN) | 前馈网络（FFN） | Transformer 中通常是逐位置子块 |
| Mixture of Experts (MoE) | 混合专家（MoE） | 本篇重点是以稀疏路由专家替换逐位置 FFN，不是多个完整模型投票 |
| routed expert / shared expert | 路由专家／共享专家 | 按输入选择的分支／每个 token 始终执行的公共分支 |
| router / gating weight | 路由器／门控权重 | 决定调用分支／控制返回输出的混合幅度，二者的分数未必相同 |
| capacity factor / token dropping | 容量因子／token 分支丢弃 | 专家槽位余量／溢出时跳过专家计算，不等于删除整个序列位置 |
| total / activated parameters | 总参数／激活参数 | 保存的全部参数／单个 token 调用的参数；两者均不能直接替代 FLOPs |
| floating-point operations (FLOPs) | 浮点运算量（FLOPs） | 与 FLOP/s 速率、访存字节和端到端时延区分 |
| encoder / decoder | 编码器／解码器 | 按职责辨认；重建解码器不一定自回归 |
| image tower / text tower | 图像编码器／文本编码器 | tower 指相对独立的编码分支，不是特殊网络层 |
| dual-encoder / two-tower architecture | 双编码器／双塔架构 | 两个分支分别编码输入，再比较投影后的表示 |
| pretraining / post-training | 预训练／后训练 | 训练安排，不是所有任务的固定生命周期 |
| fine-tuning | 微调 | 在目标任务下更新指定模型参数 |
| parameter-efficient fine-tuning (PEFT) | 参数高效微调 | 少量可训练参数不等于低部署内存 |
| low-rank adaptation (LoRA) | 低秩适配（LoRA） | 分解权重增量，基座权重本身不必低秩 |
| supervised fine-tuning (SFT) | 监督微调（SFT） | 用条件输入与目标输出训练，目标角色与损失范围需区分 |
| reinforcement learning from human feedback (RLHF) | 人类反馈强化学习（RLHF） | 用偏好等反馈建立奖励并优化策略 |
| reward model / Bradley–Terry model | 奖励模型／Bradley–Terry 模型 | 标量代理评价／由奖励差表达成对偏好的模型 |
| proximal policy optimization (PPO) / advantage | 近端策略优化（PPO）／优势 | 控制局部策略更新的算法／动作相对条件基线的收益 |
| direct preference optimization (DPO) | 直接偏好优化（DPO） | 以参考校正的策略概率比拟合偏好，无须显式奖励优化循环 |
| reference policy / behavior policy | 参考策略／行为策略 | 整体偏离基准／实际产生样本的策略，不自动是同一模型 |
| masking / reconstruction | 遮挡／重建 | 交代遮挡对象和预测目标 |
| contrastive learning | 对比学习 | 对相对匹配施加监督，不自动生成文本 |
| masked language modeling (MLM) | 掩码语言建模（MLM） | 预测选中位置的原 token，目标选择与输入替换比例不同 |
| next sentence prediction (NSP) | 下一句预测（NSP） | 原版 BERT 的片段连续性二元判别，不是下一 token 生成 |
| cross-entropy / KL divergence | 交叉熵／KL 散度 | 条件预测风险／分布差异；KL 一般不对称 |
| mean squared error (MSE) | 均方误差（MSE） | 平方误差平均，无限制预测器对应条件均值 |
| negative candidate / false negative | 负候选／假负例 | 配对索引中的竞争者／实际上仍具有目标相关关系的负候选 |
| temperature / logit scale | 温度／logit 尺度 | 正尺度与温度互为倒数时，尺度增大使 softmax 更尖锐 |
| linear probing | 线性探测 | 冻结表示模型、训练线性任务头 |
| zero-shot | 零样本 | 限定目标任务适配协议，不否认已有预训练监督 |
| autoregressive | 自回归 | 逐步以前序内容条件化预测 |
| prefill / incremental decoding | 预填充／增量解码 | 首次处理已有上下文／后续逐步生成 |
| KV cache | 键值缓存（KV cache） | 复用历史注意力状态，保留英文名称 |
| inference / serving | 推理／模型服务 | 模型计算／包含排队和调度等的服务过程 |
| FlashAttention | FlashAttention | IO 感知的注意力前向与反向实现，不是完整模型服务框架 |
| online softmax / log-sum-exp (LSE) | 在线 softmax／LSE | 分块归一化的行统计／对数指数和，前后向约定须一致 |
| HBM / shared memory / TMEM | 高带宽显存／共享内存／张量内存 | 不同存储层级；TMEM 是特定硬件的矩阵运算存储 |
| warp / CTA / tile | warp／协作线程块／计算块 | 执行协作与数据分块，不能等同于 KV 页 |
| SM100 / Ascend 950 | SM100／昇腾 950 | 两种目标硬件代号；并列出现只说明适配范围，不表示性能或能力等价 |
| host / device | 主机／设备 | CPU 一侧的内存与线程／加速器及其显存；两侧各有自己的地址空间 |
| H2D / D2H | 主机到设备／设备到主机拷贝 | 跨地址空间的搬运；同步与否由调用方式决定，异步回读往往要显式等待 |
| pinned memory | 页锁定内存（pinned） | 主机内存不被换出，可直接参与 DMA；注册与占用都有成本 |
| GIL | 全局解释器锁（GIL） | CPython 的互斥锁；C++ 扩展可在计算期间释放，使 Python 线程继续运行 |
| nanobind | nanobind | C++ 与 Python 的绑定库；文中用于把 C++ 调度器暴露为 Python 模块 |
| 3FS | 3FS | DeepSeek 的分布式文件系统；文中指承载块级 KV 的存储集群 |
| TTL | 存活期（TTL） | 缓存条目的保留时长，过期后由存储层回收；与淘汰策略不同一层 |
| Wide-EP | 宽专家并行（Wide-EP） | 用几十个 rank 承载专家并行的解码部署形态，DP 数与 EP 数相同 |
| Triton / CUTLASS / CuTe | Triton／CUTLASS／CuTe | 内核语言、模板库与布局抽象；Triton 不指同名推理服务器 |
| continuous batching / chunked prefill | 连续批处理／分块预填充 | 按步调整请求批／分多步处理长输入 |
| paged KV / block table | 分页 KV／块表 | 逻辑位置到物理状态的映射，不改变注意力公式 |
| prefix caching / RadixCache | 前缀缓存／RadixCache | 复用一致上下文的状态／基数树组织，仍受物理页约束 |
| SplitKV / cascade attention | SplitKV／级联注意力 | 沿键区间拆分并归约／组织共享前缀的读取 |
| CUDA Graph / overlap scheduling | CUDA Graph／重叠调度 | 捕获重放设备计算／错开准备、计算与输出，需保证缓冲生命周期 |
| zero-overhead (asynchronous) scheduling | 零开销调度／异步调度 | 把上一步后处理与下一步前向重叠，代价是调度在采样结果未知时完成 |
| batch-invariant inference | 批次不变推理 | 同一请求在不同批组成下得到相同结果，不等于确定性采样 |
| speculative decoding / speculative sampling | 投机解码／投机采样 | 前者统称提议—验证执行；后者包含保持目标分布的随机校正 |
| confidence-scheduled verification | 置信度调度验证 | 按逐草稿 token 的预测接受率分配本步验证预算，不是固定验证长度 |
| total variation distance (TV) | 总变差距离（TV） | 离散分布的半 L1 距离；单步投机接受率等于 1−TV |
| top-k / nucleus sampling | Top-k／nucleus 采样 | 固定候选数量／按累计概率选候选后重新归一化 |
| beam search | 束搜索（beam search） | 保留多个部分序列，有限束宽不保证全局最优 |
| round-to-nearest (RTN) / GPTQ | 最近舍入（RTN）／GPTQ | 逐元素网格选择／使用校准输入和二阶补偿的量化方法 |
| TTFT / TPOT / ITL | 首 token 时间／每输出 token 时间／token 间隔 | 定义测量边界，TTFT 不只是算子预填充耗时 |
| Tensor / Pipeline / Data / Expert Parallelism (TP / PP / DP / EP) | 张量／流水线／数据／专家并行（TP／PP／DP／EP） | 分别划分张量维度、层、数据及参数副本、专家；不同通信组须分别定义 |
| dispatch / combine / all-to-all | 分派／返回合并／全交换通信 | 专家输入送达／输出还原到来源 token／多设备按目的地交换数据，不是向所有专家广播 |
| expert-parallel load balancing (EPLB) / redundant expert | 专家并行负载均衡（EPLB）／冗余专家 | 为热点专家增加副本并重新放置以抹平 rank 间负载；增加权重副本与重排开销 |
| prefill–decode disaggregation | 预填充—解码分离（PD 分离） | 不同实例执行两段计算，需传输并确认 KV |
| sliding window attention (SWA) / bounded replay | 滑动窗口注意力（SWA）／有界重放 | 只保留或重算同定长度的末尾窗口；重放结果不覆盖未命中的历史 |
| YoCo / consumer layer | YoCo／consumer 层 | 项目术语：前 n_prefill_layer 层之外的层按 consumer 处理，其块级 KV 可由编码器末层隐状态投影 |
| W4A16 / EXL2 / GGUF | W4A16／EXL2／GGUF | 权重与激活精度约定／量化格式／模型容器，不属同一分类轴 |
| ZeRO / offload | ZeRO／卸载 | 训练状态分片／状态转移至其他设备或存储，作用对象须说明 |
| Adam / moment estimate | Adam／矩估计 | 一阶与未经中心化的二阶梯度统计，二阶原始矩不等于方差 |
| initialization bias correction | 初始化偏差修正 | 抵消矩统计零初始化的权重缺失，不是所有非平稳误差的修正 |
| learning-rate warmup / gradient clipping | 学习率预热／梯度裁剪 | 渐增早期步长／限制送入后续步骤的梯度幅度 |
| covariance / Hessian | 协方差／Hessian（海森矩阵） | 随机变化的二阶统计／目标局部曲率，作用对象不同 |
| quantization | 量化 | 低精度表示和计算，须说明对象与格式 |
| distillation | 蒸馏 | 用教师信息训练学生，不等于简单复制权重 |
| soft target / hard target | 软目标／硬目标 | 概率关系／离散标签或具体输出样本 |
| confidence calibration / temperature scaling | 置信度校准／温度缩放 | 概率与正确频率的对应／用正温度重标 logits |
| expected calibration error (ECE) | 期望校准误差（ECE） | 通常按分箱近似，结果依赖样本和分箱协议 |
| rollout / trajectory | rollout／轨迹 | 保留 rollout；指交互展开／产生的数据序列 |
| sandbox | 沙箱 | 工具执行环境，不是模型缓存 |
| checkpoint / snapshot | 检查点／快照 | 保存对象与恢复范围必须分别说明 |
| reward hacking | 奖励欺骗（reward hacking） | 通过偏离任务本意的途径取得奖励 |
| object query / bipartite matching | 对象查询／二分匹配 | 可学习预测槽位身份／目标与槽位之间的一对一分配 |
| non-maximum suppression (NMS) | 非极大值抑制（NMS） | 检测后处理去重，与匹配监督机制不同 |
| log-Mel spectrogram / WER | log-Mel 频谱／词错误率（WER） | 声学输入表示／替换、删除与插入数按参考词数归一 |
| temporal patch / channel-independence | 时间片段／通道独立 | 子序列输入单位／各通道独立前向并共享模型参数 |
| multiple sequence alignment (MSA) | 多序列比对（MSA） | 对齐相关序列的同源位置，不等于单条序列的自注意力 |
| residue contact / fold | 残基接触／折叠 | 结构预测对象／结构组织与泛化划分层级 |

文中模型报告、工程归纳与原创推导分别标明。预训练、后训练与 KV 管理并不自动成为视觉、音频及其他序列模型的共同流程。
