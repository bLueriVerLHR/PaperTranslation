# Transformer 综述：起始论文与本地原文路径

这是本项目独立的文献获取清单，不是正文，也不是逐篇摘要目录。具体论证与证据位置分别见正文和研读笔记。

本清单保留原文献分类的五主题编号：条目中的主题 5 指下游任务，对应当前正文第 6 节。新增正文第 5 节“训练／推理框架”的固定源码与笔记映射见 `source-map.md` 及 `reference/framework-notes/LOCATION.md`；本清单原第 4 类的 FlashAttention、PagedAttention、FlashAttention-2 与设备端综述同时与新框架节相关，不因章节插入改变其书目身份和版本。

- **P1：先提供**，用于搭建基础解释和主要领域的阅读起点。
- **P2：随后补充**，不必一次找齐。优先级表示阅读顺序，不表示论文质量排名。
- 范围是通用架构与序列建模；语言模型专属的后训练、缓存与服务论文已单独标注。
- 已核对的附件填写在“本地文件路径”中；尚未找到的继续留空，可填写外部原文件的绝对路径。不要把 PDF 复制进项目。
- 优先找列出的固定 arXiv 版本。正式会议/期刊版也可提供；若版本不同，请注明，使用前再核对标题、作者与内容，不只依赖文件名。
- 两份清单若有同一论文，可填写同一外部文件路径，不必下载两份；两个综述仍独立维护。
- 原文供研读与准确引用；提供文件不等于许可翻译、复刻图表或公开分发。
- 检索参考版本与本地实际版本分开记录。已找到的正式版不冒充 arXiv 版本；作者与附件信息存于 `reference/local-sources.json`，不根据投稿人信息推断作者。

以下保留 23 篇起始条目的编号和候选附件记录，其中 P1 为 8 篇。空白路径与 `download-needed.md` 是初始获取清单，不再作为当前附件缺失结论；后续 Zotero 只读核对结果见 `reference/zotero-surveys.json`。实际用于正文的公开原始来源 [18]–[30] 及固定修订另见 `reader.json`、`reference/pretraining-mechanisms.md`、`reference/posttraining-mechanisms.md` 与 `reference/inference-applications-mechanisms.md`。MoE、EP、MLA、DSA、MiniMax MSA 和 GQA 的原始来源 [31]–[36] 及固定修订另见 `reference/moe-attention-mechanisms.md`，不依赖本表另行登记 PDF 附件。T14、T15、T18、T19 已通过公开固定版本核对相关机制，不依赖本表是否登记 Zotero 路径。T02、T08、T09、T10 的实际会议版身份与研读范围见 `reference/four-core-sources.json` 和 `reference/four-core-reading.md`，不将正式版冒充指定 arXiv 修订版。

## 1. 基础原理与架构演进

### T01 · P1 · Attention Is All You Need

- 首次预印本年份：2017（不是会议／期刊发表年份）。
- 原文与固定版本：[1706.03762v7](https://arxiv.org/abs/1706.03762v7)。
- 研究对象：机器翻译；架构基础。
- 阅读用途：建立注意力、编码器—解码器与基本 Transformer 的原始定义。
- 主主题：1；关联主题：2、4、5。
- 本地文件路径：`C:\Users\Lozz\Zotero\storage\7LH4JDVB\Vaswani et al. - 2017 - Attention is all you need.pdf`
- 本地版：NIPS 2017 会议版，11 页；PDF 无 arXiv 版本标记，不视为已确认的 v7。

### T02 · P1 · An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale

- 首次预印本年份：2020（不是会议／期刊发表年份）。
- 原文与固定版本：[2010.11929v2](https://arxiv.org/abs/2010.11929v2)。
- 研究对象：视觉。
- 阅读用途：连接输入序列化、视觉表征与 Transformer 架构适配。
- 主主题：1；关联主题：2、5。
- 本地文件路径：`C:\Users\Lozz\Zotero\storage\JM3GS25Q\Dosovitskiy et al. - 2020 - An Image is Worth 16x16 Words Transformers for Image Recognition at Scale.pdf`
- 本地版：ICLR 2021 正式版，21 页；实际首页题名与署名核对，无自有 arXiv 版本章，不认定为 v2，文件名年份不取代会议年份。

### T03 · P1 · Transformers are RNNs: Fast Autoregressive Transformers with Linear Attention

- 首次预印本年份：2020（不是会议／期刊发表年份）。
- 原文与固定版本：[2006.16236v3](https://arxiv.org/abs/2006.16236v3)。
- 研究对象：注意力与自回归序列建模。
- 阅读用途：作为线性注意力与递推形式的基础阅读；不与标准注意力混为同一种计算。
- 主主题：1；关联主题：4。
- 本地文件路径：`C:\Users\Lozz\Zotero\storage\WYWADMQW\Katharopoulos et al. - 2020 - Transformers are RNNs Fast Autoregressive Transformers with Linear Attention.pdf`；`C:\Users\Lozz\Zotero\storage\WGB9ZTM6\Katharopoulos et al. - 2020 - Transformers are RNNs Fast Autoregressive Transformers with Linear Attention.pdf`
- 本地版：两附件题名均匹配，文件字节不同；保留候选，不任意认定两者都是 arXiv v3，具体差异留待逐页比对。

### T04 · P2 · Rethinking Attention with Performers

- 首次预印本年份：2020（不是会议／期刊发表年份）。
- 原文与固定版本：[2009.14794v4](https://arxiv.org/abs/2009.14794v4)。
- 研究对象：注意力机制。
- 阅读用途：讨论随机特征与注意力近似的技术路线及适用条件。
- 主主题：1；关联主题：4。
- 本地文件路径：

### T05 · P2 · Swin Transformer: Hierarchical Vision Transformer using Shifted Windows

- 首次预印本年份：2021（不是会议／期刊发表年份）。
- 原文与固定版本：[2103.14030v2](https://arxiv.org/abs/2103.14030v2)。
- 研究对象：视觉。
- 阅读用途：覆盖窗口注意力与层级视觉结构。
- 主主题：1；关联主题：4、5。
- 本地文件路径：

### T06 · P2 · RoFormer: Enhanced Transformer with Rotary Position Embedding

- 首次预印本年份：2021（不是会议／期刊发表年份）。
- 原文与固定版本：[2104.09864v5](https://arxiv.org/abs/2104.09864v5)。
- 研究对象：位置表征。
- 阅读用途：补充旋转位置编码及其与注意力的关系。
- 主主题：1；关联主题：2、4。
- 本地文件路径：`C:\Users\Lozz\Zotero\storage\VKTTS7GI\Su et al. - 2024 - RoFormer Enhanced transformer with Rotary Position Embedding.pdf`
- 本地版：期刊版，DOI `10.1016/j.neucom.2023.127063`；不将文件名的 2024 年当成预印本首发年份。

### T07 · P2 · Jamba: A Hybrid Transformer-Mamba Language Model

- 首次预印本年份：2024（不是会议／期刊发表年份）。
- 原文与固定版本：[2403.19887v2](https://arxiv.org/abs/2403.19887v2)。
- 研究对象：语言；混合架构。
- 阅读用途：连接 Transformer 与 Mamba 的混合设计；另一个项目也需要此文。
- 主主题：1；关联主题：2、4。
- 本地文件路径：

### T20 · P2 · A Review of Sparse Expert Models in Deep Learning

- 作者：William Fedus、Jeff Dean、Barret Zoph（原文署名）。
- 来源类型：综述；2022 年，PDF 标明 `arXiv:2209.01667v1`。
- 原文：[2209.01667v1](https://arxiv.org/abs/2209.01667v1)。
- 主主题：1；关联主题：2、4、5。
- 阅读用途：梳理稀疏专家、路由与计算分配，作为寻找原始研究的线索；具体方法与实验仍回到被引原论文核对。
- 本地文件路径：`C:\Users\Lozz\Zotero\storage\NFFPIT7C\Fedus 等 - 2022 - A Review of Sparse Expert Models in Deep Learning.pdf`

## 2. 预训练阶段

### T08 · P1 · BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding

- 首次预印本年份：2018（不是会议／期刊发表年份）。
- 原文与固定版本：[1810.04805v2](https://arxiv.org/abs/1810.04805v2)。
- 研究对象：语言。
- 阅读用途：覆盖编码器式预训练与下游适配，与生成式训练区分。
- 主主题：2；关联主题：3、5。
- 本地文件路径：`C:\Users\Lozz\Zotero\storage\69PAINK6\Devlin et al. - 2019 - BERT Pre-training of Deep Bidirectional Transformers for Language Understanding.pdf`
- 本地版：NAACL-HLT 2019 正式版，16 页，pp.4171–4186，DOI `10.18653/v1/N19-1423`；无自有 arXiv 版本章，不认定为 v2。

### T09 · P1 · Masked Autoencoders Are Scalable Vision Learners

- 首次预印本年份：2021（不是会议／期刊发表年份）。
- 原文与固定版本：[2111.06377v3](https://arxiv.org/abs/2111.06377v3)。
- 研究对象：视觉。
- 阅读用途：覆盖视觉中的掩码自监督学习，不将预训练等同于语言建模。
- 主主题：2；关联主题：5。
- 本地文件路径：`C:\Users\Lozz\Zotero\storage\6N3T2LYK\He et al. - 2022 - Masked Autoencoders Are Scalable Vision Learners.pdf`
- 本地版：CVPR 2022 正式版，10 页，pp.16000–16009；无自有 arXiv 版本章，不认定为 v3。

### T10 · P1 · Learning Transferable Visual Models From Natural Language Supervision

- 首次预印本年份：2021（不是会议／期刊发表年份）。
- 原文与固定版本：[2103.00020v1](https://arxiv.org/abs/2103.00020v1)。
- 研究对象：视觉—语言。
- 阅读用途：覆盖跨模态对比学习与迁移。
- 主主题：2；关联主题：5。
- 本地文件路径：`C:\Users\Lozz\Zotero\storage\ZXF2V69F\Radford et al. - 2021 - Learning Transferable Visual Models From Natural Language Supervision.pdf`
- 本地版：ICML 2021，PMLR 139:8748–8763，16 页；无自有 arXiv 版本章，不认定为 v1。

### T11 · P2 · wav2vec 2.0: A Framework for Self-Supervised Learning of Speech Representations

- 首次预印本年份：2020（不是会议／期刊发表年份）。
- 原文与固定版本：[2006.11477v3](https://arxiv.org/abs/2006.11477v3)。
- 研究对象：语音。
- 阅读用途：补充语音表征的自监督预训练实例。
- 主主题：2；关联主题：5。
- 本地文件路径：

### T12 · P2 · Language Models are Few-Shot Learners

- 首次预印本年份：2020（不是会议／期刊发表年份）。
- 原文与固定版本：[2005.14165v4](https://arxiv.org/abs/2005.14165v4)。
- 研究对象：语言。
- 阅读用途：补充大规模自回归语言预训练与少样本评估。
- 主主题：2；关联主题：5。
- 本地文件路径：

## 3. 后训练阶段

### T13 · P1 · LoRA: Low-Rank Adaptation of Large Language Models

- 首次预印本年份：2021（不是会议／期刊发表年份）。
- 原文与固定版本：[2106.09685v2](https://arxiv.org/abs/2106.09685v2)。
- 研究对象：语言；参数高效适配。
- 阅读用途：建立低秩适配的原始方法与实验范围，不预设其跨领域结论。
- 主主题：3；关联主题：5。
- 本地文件路径：`C:\Users\Lozz\Zotero\storage\3TWFZESF\Hu et al. - 2021 - LoRA Low-Rank Adaptation of Large Language Models.pdf`
- 本地版：PDF 标明 `arXiv:2106.09685v2`，与检索参考版本一致。

### T14 · P2 · Training language models to follow instructions with human feedback

- 首次预印本年份：2022（不是会议／期刊发表年份）。
- 原文与固定版本：[2203.02155v1](https://arxiv.org/abs/2203.02155v1)。
- 研究对象：语言；指令与偏好。
- 阅读用途：作为语言模型后训练案例，不当作所有 Transformer 任务的必经过程。
- 主主题：3；关联主题：5。
- 本地文件路径：

### T15 · P2 · Direct Preference Optimization: Your Language Model is Secretly a Reward Model

- 首次预印本年份：2023（不是会议／期刊发表年份）。
- 原文与固定版本：[2305.18290v3](https://arxiv.org/abs/2305.18290v3)。
- 研究对象：语言；偏好优化。
- 阅读用途：补充偏好优化的目标与方法，与一般任务微调区分。
- 主主题：3；关联主题：5。
- 本地文件路径：

## 4. 推理阶段

### T16 · P1 · FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness

- 首次预印本年份：2022（不是会议／期刊发表年份）。
- 原文与固定版本：[2205.14135v2](https://arxiv.org/abs/2205.14135v2)。
- 研究对象：精确注意力实现。
- 阅读用途：讨论 IO 感知的注意力实现；它不是替换注意力数学定义的新架构。
- 主主题：4；关联主题：1。
- 本地文件路径：`C:\Users\Lozz\Zotero\storage\9D4UDLWS\Dao et al. - 2022 - FlashAttention Fast and Memory-Efficient Exact Attention with IO-Awareness.pdf`
- 本地版：PDF 标明 `arXiv:2205.14135v2`。另有会议版附件 `EA6RYPCP`，未将两个版本混作同一份文件。

### T17 · P2 · Efficient Memory Management for Large Language Model Serving with PagedAttention

- 首次预印本年份：2023（不是会议／期刊发表年份）。
- 原文与固定版本：[2309.06180v1](https://arxiv.org/abs/2309.06180v1)。
- 研究对象：自回归语言模型服务。
- 阅读用途：补充 KV cache 与服务端内存管理；不将其要求套到所有推理任务。
- 主主题：4；关联主题：无额外指定。
- 本地文件路径：`C:\Users\Lozz\Zotero\storage\TRY2BDBF\Kwon et al. - 2023 - Efficient Memory Management for Large Language Model Serving with PagedAttention.pdf`
- 本地版：SOSP 2023 会议版，DOI `10.1145/3600006.3613165`；不视为已确认的 arXiv v1。

### T21 · P2 · FlashAttention-2: Faster Attention with Better Parallelism and Work Partitioning

- 作者：Tri Dao（原文署名）。
- 来源类型：原始算法与实现研究，2023 年。
- 检索原文：[2307.08691](https://arxiv.org/abs/2307.08691)。
- 主主题：4；关联主题：1、2。
- 阅读用途：讨论注意力的并行组织与工作划分，区别算法实现与注意力数学定义；速度结果保留其硬件、输入和基线条件。
- 本地版：14 页，题名与作者已从 PDF 核对；首页未带 arXiv 版本标记，暂不指定 v1/v2/v3。
- 本地文件路径：`C:\Users\Lozz\Zotero\storage\T56R4FPP\Dao - 2023 - FlashAttention-2 Faster Attention with Better Parallelism and Work Partitioning.pdf`

### T23 · P2 · On-device large language models: a survey of model compression and system optimization

- 作者：Wanyi Chen 等（实际 PDF 署名）。
- 来源类型：正式期刊综述，*Artificial Intelligence Review* 59（2026），191，2026-05-22 在线发表。
- 原文：[DOI 10.1007/s10462-026-11538-1](https://doi.org/10.1007/s10462-026-11538-1)。不是 Xu 的近似题名预印本，不以其他工作替代。
- 主主题：4；关联主题：1、2、3、5，范围主要是自回归语言模型与边缘部署。
- 阅读用途：连接模型压缩、适配与系统协同；以 ALEM 区分精度、时延、能耗和内存，回查原方法及测量条件，不将作者报告当作本项目复现或跨模型因果比较。
- 保留的来源：[本地译文阅读页](reference/on-device-llm-survey/index.html)；完整原稿、图表、引用与提取资料位于同名容器。五主题定位见 [source-map.md](source-map.md)。
- 本地版：实际 PDF 60 页，题名、作者署名与 DOI 已核对；源稿正文范围到 48 页不是整份 PDF 页数。
- 权利：CC BY-NC-ND 4.0；完整译文保持本地，不因收纳而获改编发布许可。
- 本地文件路径：`C:\Users\Lozz\Zotero\storage\CZL8PCH3\Chen 等 - 2026 - On-device large language models a survey of model compression and system optimization.pdf`
- 实际来源及哈希：[on-device-source.json](reference/on-device-source.json)。已有原文，不新增待下载请求。

## 5. 下游任务

### T18 · P2 · End-to-End Object Detection with Transformers

- 首次预印本年份：2020（不是会议／期刊发表年份）。
- 原文与固定版本：[2005.12872v3](https://arxiv.org/abs/2005.12872v3)。
- 研究对象：目标检测。
- 阅读用途：补充分类之外的视觉任务与编码器—解码器应用。
- 主主题：5；关联主题：1、3。
- 本地文件路径：

### T19 · P2 · A Time Series is Worth 64 Words: Long-term Forecasting with Transformers

- 首次预印本年份：2022（不是会议／期刊发表年份）。
- 原文与固定版本：[2211.14730v2](https://arxiv.org/abs/2211.14730v2)。
- 研究对象：时间序列预测。
- 阅读用途：补充通用序列建模中的非语言任务。
- 主主题：5；关联主题：1、2。
- 本地文件路径：

### T22 · P2 · SalesRLAgent: A Reinforcement Learning Approach for Real-Time Sales Conversion Prediction and Optimization

- 作者：Nandakishor M（Deepmost Innovations，原文署名）。
- 来源类型：应用研究预印本，2025-03-30，`arXiv:2503.23303v1`。
- 原文与固定版本：[2503.23303v1](https://arxiv.org/abs/2503.23303v1)。
- 研究对象：销售对话与转化预测。
- 主主题：5；关联主题：4；主题 3 仅作任务预测器训练的对照，不当作 Transformer 主体后训练证据。
- 阅读用途：结合 GPT-4O 合成数据、Azure OpenAI 嵌入与 RL 预测器的行业案例；区分表征模型、业务状态、最终预测器与编排。数字只作为作者报告，不当作本项目复现或跨系统排名。
- 保留的来源：[译文阅读页](reference/sales-rl-agent/index.html)，原稿与提取资料位于 `reference/sales-rl-agent/`；对应 [source-map.md](source-map.md)。
- 相近研究线索：[TypeSafe Jev 比较笔记](reference/jev-research.md)。Jev 是产品／技术资料，不冒充同行评议论文或本案例的同一实现。
- 本地版：6 页，题名、原文署名与 `arXiv:2503.23303v1` 已核对。
- 本地文件路径：`C:\Users\Lozz\Zotero\storage\B3WY3NMX\M - 2025 - SalesRLAgent A Reinforcement Learning Approach for Real-Time Sales Conversion Prediction and Optimi.pdf`
