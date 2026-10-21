# Transformer 综述：来源与应用映射

`content/` 是本篇原创综述的正文源。以下资料索引用于追溯应用案例与相关技术，不直接拼入正文，也不把外部论文、产品文档或代码观察混成同一类证据。

## 原始方法证据：BERT、ViT、MAE、CLIP

[四篇研读笔记](reference/four-core-reading.md)以输入构造、可见性、预测目标与迁移协议组织证据；[实际会议版身份](reference/four-core-sources.json)记录外部路径、SHA-256、作者及实际阅读范围。BERT 使用 NAACL 2019，ViT 使用 ICLR 2021，MAE 使用 CVPR 2022，CLIP 使用 ICML 2021；不冒充此前清单上的指定预印本修订。

- **主题1**：token／图块输入、位置表征、自注意力、ViT 编码子块，MAE 的重建模块与 CLIP 双塔的职责差异。
- **主题2**：原始 ViT 的有标签预训练、BERT 的 MLM/NSP、MAE 的遮挡像素重建和 CLIP 的图文配对判别；数据、规模及不同迁移协议的边界。
- **主题3与6**：原文的任务微调、部分微调、检测／分割迁移和文本驱动零样本接口，用于辨认适配与应用输出；不将来源收录当作独立复现。

独立补充材料及全部参考文献未完成逐条核验，没有进行模型训练或实验复现。正文使用原创解释与原生 MathML，不嵌入这四篇原论文的完整译文或图表。

## SalesRLAgent 来源容器

完整旧项目保留在 `reference/sales-rl-agent/`：

- `work/content/`：九份已有译文源稿，保留原作者立场、算法、三张表及数字。
- `work/reader.json`：16 条原始参考文献与引用配置；原有“未独立核验书目准确性”的限制继续保留。
- `work/reference/`：原文提取章节、页面文本和有用参考栅格；不复制外部 PDF。
- [译文阅读页](reference/sales-rl-agent/index.html)：本地参考阅读，不是本篇原创综述。它继续使用库根共享 CSS／JS，不产生私有运行时。
- [原始 PDF 身份与路径](reference/sales-source.json)：外部 Zotero 文件已核对为 `arXiv:2503.23303v1`，6 页。

旧提取报告中的 `.local/source/.../paper.pdf` 是历史路径，不是当前输入路径，不据此重建旧目录或复制 PDF。实际外部路径单独记录，重建保留来源页不需要 PDF。

## 主题 6：行业应用——销售对话转化预测

| 既有来源位置 | 原创解释的对象 | 不能省略的边界 |
|---|---|---|
| §3，`03-data.md` | GPT-4O 合成对话、嵌入与业务特征的作用 | 合成标签、数据划分、领域与语言范围；不能把该过程写成基础 Transformer 的预训练 |
| §4，`04-architecture.md` | 状态编码、策略／价值预测和不确定性信息 | 原文动作对应概率估计；不补造 PPO 等算法名，不默认这些网络就是 Transformer 主体 |
| §5，`05-system.md` | 增量状态、缓存、外部嵌入与业务工作流 | 分清编码调用、预测器、指导生成与端到端时延 |
| §6，`06-results.md` | 作者的准确率、AUC、消融及部署评价 | 结果属于作者报告；不将移入资料当作独立验证，不混淆预测表现与因果业务收益 |
| §7，`07-discussion.md` | 多语言、多模态、因果与长期关系的边界 | 保留原作者限定，不将单一领域结论推广到所有序列任务 |

案例的中心是“基础模型表征／数据生成与专门化预测器如何组成业务系统”，而不是“如何对大语言模型做销售领域 RLHF”。3072 维嵌入也不足以单独反推 Azure 的具体基座型号和内部网络。

## 与其他主题的联系

- **主题 1，架构**：作为表征与预测器分工的应用观察，不提供注意力机制或基础 Transformer 架构改进的直接证据。
- **主题 2，预训练**：原文的合成数据用于任务模型训练，不自动等同于基础模型预训练。
- **主题 3，后训练／适配**：原文的监督初始化、RL、课程学习等属于专门化业务模型训练；是否更新表征模型必须按原文核对，不能因出现 RL 就归为 Transformer 主体后训练。
- **主题 4，推理／部署**：增量状态、嵌入缓存与 CPU 预测器可作为组成成本的案例；原文时延与其他厂商服务的时延不直接作统一排名。

## Jev 与相关实现

[TypeSafe Jev 研究笔记](reference/jev-research.md)分别记录官方产品／技术介绍、官方概率与置信度契约，以及独立开源 JevEmbed 的可检查实现。两条应用路线都强调直接输出预测或结构化判断，而不是仅生成文本；任务、训练方式和内部模型并不相同。

Jev 对有限类型输出的约束与判断正确性、概率校准是不同问题。它适合作为应用接口和效率目标的补充资料；在内部架构与训练细节没有充分核实时，不把它当作 Transformer 结构论证的原始论文。JevEmbed 的向量打分、监督式 LoRA 和默认未校准映射也不写成官方 Jev 的 RLCD 实现。

## 设备端 LLM 来源容器

完整项目保留在 `reference/on-device-llm-survey/`，与 SalesRLAgent 各自保留原有译文身份：

- [本地译文阅读页](reference/on-device-llm-survey/index.html)：13 份章节源稿、原生 MathML、9 幅图、9 张表及其原有数字、引用和权利说明。
- `work/reference/` 与 `work/reader.json`：英文参考文献、提取文本、页面资料及既有引用映射。592 次已链接引文不是 592 篇已核实论文；未匹配与歧义记录继续保留。
- [实际原文记录](reference/on-device-source.json)：Wanyi Chen 等，*Artificial Intelligence Review* 59（2026），191，DOI `10.1007/s10462-026-11538-1`；外部 PDF 60 页。源稿章程的正文范围到第 48 页，不是完整 PDF 页数。

这是期刊正式版，不是同名近似的 Xu 预印本。CC BY-NC-ND 4.0 限制仍然保留，未确认允许发布完整改编译文；原 PDF 不移入项目。

### 主题映射

| 主题 | 既有来源位置 | 可以组织的问题与核对边界 |
|---|---|---|
| 1，架构 | §2、§3.4.4–3.4.5（`02-background.md`、`03d-low-rank.md`） | 参数共享、结构化矩阵与线性注意力的不同作用点；权重低秩、注意力近似与状态递推不是同一种机制。具体等价和复杂度回到原始方法论文核对。 |
| 2，预训练 | §3.3、§3.5.4、§3.5.6（`03c-distillation.md`、`03e-hybrid.md`） | 教师—学生目标、训练期间稀疏／低秩参数化与预训练蒸馏的线索。并非完整预训练综述，不能用后处理压缩替代数据与目标的解释。 |
| 3，后训练／适配 | §3.1–3.5，尤其 §3.4.2–3.4.3 | QAT、PTQ、校准、PEFT、训练后分解和能力恢复分别作用于哪些对象。PTQ 的“训练后”不等同偏好对齐；LoRA 训练参数少不自动意味着基座参数或部署内存更少。 |
| 4，推理／部署 | §4–5、§6 的约束与方案栈（`04-system.md`、`05-evaluation.md`、`06-playbook.md`） | 压缩与算子、编译、运行时、缓存、硬件及端云协同的联系。区分预填充与解码、容量与带宽、目标设备与代理测量。 |
| 6，下游任务 | §6，关联 §7（`06-playbook.md`、`07-challenges.md`） | 移动助手、车载交互、工业边缘、医疗与办公应用中的约束；作者建议不是安全认证、临床有效性或生产表现的独立证据。 |

该材料主要覆盖自回归语言模型与边缘部署。它可以扩充特定应用与系统主题，不能把整篇通用 Transformer 综述缩成端侧 LLM 部署手册，更不能将 KV 管理作为所有模态的共有架构要求。

### 原文报告与原创判断的分界

- §5 的 ALEM 结果属于原作者报告。本次收纳不运行模型、不做设备测量，也不独立复现原实验。峰值 GPU 分配量与 NVML 功率积分不自动等于手机的全系统内存或能耗。
- 表 7–8 横跨不同模型及训练史，不仅改变一种压缩处理；不能由这一表格直接推出某技术导致所有精度、能效差异。数字、单位和作者解释保留，但原创综述应注明这种比较限制。
- 原文同时描述确定性解码及 `temperature=0.2`、`top_p=0.95`；采样开关、随机种子和实际运行条件须回查。表 7 的 MC-Avg 还需核对是否符合所述四项未加权平均，而非自行按叙述修正数据。
- 服务端分页、通用 GPU 与专用 NPU 的结果不能无条件迁移到资源受限设备。算子覆盖、量化格式、序列长度、批量、热状态和网络条件是必要比较条件。
- 第 3–4 节的补充参考仓库是后续查找线索；目前未宣称已核查其全部条目或完成原方法的复现。未决引文不靠猜测同姓作者解决。

## DeepSeek DSec 来源容器与交互训练

唯一来源项目位于 `reference/deepseek-dsec/`：保留原译文、13 幅裁图、原始书目、页面文本与栅格；不复制外部 PDF。来源页沿用库根运行时。固定版本为 *DeepSeek Elastic Compute (DSec): A Sandbox Infrastructure for Effective Agentic Training at Scale*，Jialiang Huang 等，arXiv:2609.22978v1。arXiv 摘要、版本页及 HTML 的 §6 已交叉核对主要生命周期和安全描述。收录不等于已核对全部书目、复现实现或获得完整译文／图像的公开许可。

- 主题 3：§6.1–6.5 支持环境构建、rollout 与训练器解耦、抢占与恢复、非幂等动作及奖励有效性讨论。
- 主题 4：§3、§5–6 支持沙箱后端、镜像层、按需读取、资源回收与模型／工具状态分工。
- DSec 是智能体训练基础设施，不是 DeepSeek-V4.1-Flash 的 KV 压缩方法论文；引用其关联型号不构成对相应架构的独立核查。
- 原创正文不复制完整译文、关键数字列表或图表。生产规模与实验结果均属作者报告，不宣称本篇已复现。

## Zotero 综述与主题综合

`reference/zotero-surveys.json` 保留筛选文献的外部路径、附件哈希、实际版本及使用范围；`reference/zotero-survey-reading.md` 将关键断言映射到 PDF 页码与规范子稿。引用 [9]–[17] 对应九篇已核对相关段落的综述；检索匹配和附件存在不等于完成全文研读。

`content/architecture/` 组织基础机制、推导与架构比较；`pretraining/survey-data.md`、`posttraining/continual-learning.md`、`inference/optimization-levels.md`、`frameworks/training/distributed-challenges.md`、`frameworks/kv-design.md` 与 `downstream/rag-design.md` 分别承载主题补充。数学推导是本篇对定义与结构的解释，不能当作来源论文已报告的性能结果。不同 PDF 版本与 Zotero 书目差异在来源记录中单独保留。

预训练八个子稿和推导前提的详细映射见 `reference/pretraining-mechanisms.md`。其中 Adam 定义另回到原始论文 [18] 的 `1412.6980v9`，核对 PDF p.2 的 Algorithm 1 与 p.3 的零初始化偏差修正，不采用其收敛或实验排名作为 Transformer 训练结论。

## 后训练的原始机制来源

`reference/posttraining-mechanisms.md` 保存 LoRA [19]、InstructGPT [20]、DPO [21]、蒸馏 [22]、校准 [23] 和 PPO [24] 的固定版本与相关原文定位。新增来源采用公开原始论文，不以摘要替代算法阅读；原文和抽取中间量仅存系统 TEMP。后训练十个子稿的矩阵、概率与局部推导，分别说明约束和定义，不把理想分布解当作有限网络的训练保证。

## 推理及跨领域应用的原始来源

`reference/inference-applications-mechanisms.md` 对应新增引用 [25]–[30]：投机采样的 Algorithm 2 和单步分布证明，GPTQ 的逐层重建与 Cholesky 补偿，DETR 的匹配及并行对象解码，Whisper 的音频接口与任务格式，PatchTST 的片段化和通道独立，蛋白质语言模型的结构探测。使用固定 PDF 修订或期刊 JATS 正文，不以摘要代替算法核对。张量容量、连续补偿、接受率、时间片段计数与信息边界的分析各自写明前提，不将理论解释当作本机性能证据。

推理与应用均以父稿 include 组合。框架跨项目资源与生命周期分析保留固定源码入口及原有摘录，不改变上游提交或执行项目。

## 本地算子与推理框架源码

源码入口身份记录在 `reference/source-repositories.json`。工作区 `repos/` 下保留 21 个独立源码仓库（含 FlashAttention），各自提交和检出状态单独记录；`flash-attention` 的固定迁移提交为 `e9515d5dee6ade134a33d6020d38d01ef0596996`，新增的 `deepinfer` 为 `774ce244`。原 `docs/`、`notes/`、`scripts/` 与 README 已迁至本项目 `reference/framework-notes/`，源码未移动或改写。

主题 5 的组合入口为 `content/05-frameworks.md`，规范正文位于其显式嵌入的 `content/frameworks/` 子稿。具体项目修改入口见 `README.md`；固定源码摘录的行范围与符号见 `source-excerpts.json`，可用 `excerpts.py --check` 对照 Git 对象。来源按以下关系重新组织：

| 原来源 | 正文主题 | 证据范围 |
|---|---|---|
| `notes/01–09`、`docs/flash-attention.md` | GPU 存储、在线 softmax 前向、LSE 重算反向、FA2／3／CuTeDSL 与 SplitKV | 数学推导与固定实现组织；不沿用旧笔记错误的 GEMM 数或梯度恒等式解释 |
| `notes/04`、`10–13`、上游 `AI/` | 指令角色、资源预算、流水契约、问题诊断与术语 | 编译敏感性只产生待验证假说；调试案例不是新故障的默认根因 |
| `docs/llm.c.md`、`deepspeed-fastgen.md` | 训练步、分类器融合、状态分片作用点与推理 SplitFuse | 训练与推理区别；不声称完成全面 ZeRO 源码研读或 GPU 复现 |
| `vllm.md`、`sglang.md` | 进度调度、分页、前缀树、缓存保护、HiCache、程序接口 | 直接抽查 schedule、match_prefix；树复用仍受页约束，vLLM 也有引用保护 |
| TensorRT-LLM、LMDeploy、TGI、LightLLM 文档 | 双后端、量化格式、跨语言服务与 token 级分配 | 不拼性能排名；LightLLM 保留不完整 Windows 检出限制 |
| llama.cpp、exllamav2、Ollama、MLC-LLM 文档 | 图内存、序列状态、低比特、分发生命周期与跨端编译 | exllamav2 不无条件纳入 EXL3；MLC 的 TVM 子模块未完整检出 |
| ktransformers、PowerInfer、vLLM-Ascend 文档 | 专家／激活稀疏、异构放置与 NPU 移植 | 结构条件和静态范围，不虚构部署百分比或效果 |
| nano-vllm、mini-sglang 文档 | 精简状态机、准入保护、图与在途元数据 | 直接核对 nano 的图捕获和 prefill 完成迁移；mini 加锁会改变可驱逐预算 |
| [DeepInfer](https://github.com/deepseek-ai/DeepInfer) `774ce244`、官方部署问答 | 异步调度的滞后元数据修正、SWA 有界重放、变长验证、EPLB 与 DP 步型投票 | 只读引擎与模型侧源码；`vendor/` 子模块未拉取，KV 系统、PD 部署与负载均衡未开源，性能数字不当作本机复现 |
| `docs/interview-bank.md` 与各文档问答 | 缓存身份、调度公平、质量／性能测量等工程问题 | 保留原稿为来源，正文将机制融入主题，不生成题库或面试路线 |

原始笔记完整保留，但不参与自动正文拼接或单独发布；原有 LaTeX、历史路径、功能比较和面试表述不因迁移而获认可。路径对应与局部核对见 `reference/framework-notes/LOCATION.md`。源码和来源笔记各自保持唯一位置，不复制代码树到 `work/`；源码许可证仍归上游。实验、扫描、报告与缓存放系统 TEMP。

## 注意力机制章与新增来源

`reference/moe-attention-mechanisms.md` 保存 [31]–[36] 的固定修订、相关章节／公式与原创推导前提。Switch 提供路由门值、容量与专家并行基础；DeepSeek-V2 提供细粒度／共享专家及 MLA，DeepSeek-V3 提供 sigmoid、选择偏置和节点内外通信的论文定义；DeepSeek-V3.2 提供 DSA 及 MLA 两种执行视图；MiniMax 原始论文提供 MSA 的分组块选择、双分支训练、二次索引项与 LSE 合并；GQA 原文提供 KV 共享及继续预训练的边界。

规范稿位于 `content/attention/`，由 `content/02-attention.md` 按继承关系组合：`overview`（三条轴与谱系表）、`head-sharing`（MHA→MQA→GQA）、`mla`、`linear-attention`（核化线性注意力）、`retention`（RetNet）、`delta-rule`（DeltaNet）、`gdn`、`ssm-rwkv`（Mamba／Mamba2／RWKV 对照）、`sliding-window`（SWA）、`nsa`、`dsa`、`msa`、`ledger`（三条轴上的账目）。`reference/attention-mechanisms.md` 保存 [37]–[49] 的固定修订、章节定位与实际阅读范围，并单独列出哪些说法是原文报告、哪些是本篇推导；本篇未采集被引数，也不按引用量排序。MoE 与 EP 的规范稿仍为 `architecture/{moe,expert-parallel}.md`。`inference/execution-cache.md` 区分显式 KV、MLA 潜在容量和稀疏访问预算。通信字节、容量算例和单层稀疏输出界为原创解释，不是设备实测或全网络质量证明；论文执行设计不冒充固定源码审计。MSA 在此指 MiniMax Sparse Attention，不更改蛋白质主题中的 multiple sequence alignment。

## DeepSeek 自研栈

`content/frameworks/deepseek/` 由 `frameworks/deepseek/index.md` 组合四个技术对象：FlashMLA、DeepGEMM、DeepEP，以及 3FS 与 smallpond 一组存储与数据。六个仓库按固定提交写入 `source-repositories.json`，实际阅读范围、断言与来源的对应、以及“仓库报告值 vs 本机测量”的分界在 `reference/deepseek-stack.md`。[51]–[55] 为对应引用，DeepInfer 仍由 `frameworks/cloud/deepinfer.md` 维护，不重复。

本节只做静态阅读：未构建、未安装、未运行上游代码，也未跑 benchmark；所有吞吐与时延均为仓库自述，并随文保留 GPU 型号与集群规模。模型权重仓库与 Ascend 分叉只提及存在，未检出、未阅读。

## 原始 Transformer 与术语／推理推导

*Attention Is All You Need* 固定为 arXiv:1706.03762v7，作者与英文题名见 `reader.json`。HTML 的 §3–4 支持自注意力／交叉注意力、因果目标错位、归一化顺序、前馈网络及局部连接路径的讨论。局部注意力在原文中是待探索方向，不写成该文已完成的效率评测。

`glossary.md` 是公开术语对应表的唯一源稿。KV 容量与假设 192 MiB 例子按张量元素数计算，不是原论文或设备端综述的实测结果；不将该式用于任意压缩或共享状态架构。量级公式也不代替设备时延。

## 研读方法

[本项目的综述研读方法](../../../docs/review-method.md)借鉴 Feynman 的问题驱动研读、证据对照、断言核查与分层审校。资料位置和核对范围另见 [方法与来源笔记](reference/review-guidance.md)；这些记录不拼入原创正文，也不要求安装外部工具或启动代理。

## 权利与证据

完整译文及其原始资料仍只保存在本地；移入原创综述项目不改变外部材料的权利，也不构成发布许可。原创正文可以在核对来源后解释问题、机制与限制，但不直接复刻完整译文。产品宣传、原论文报告、代码静态观察与独立验证分别标明。
