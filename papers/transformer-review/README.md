# Transformer 综述：源稿与构建

本项目是独立的原创学习综述，不是单篇论文的翻译或本地代码仓库分析。身份存于 `meta.json`，不使用 PDF/web 的 `paper.json`。六个主题的阅读顺序由 `meta.json` 与 `content/` 文件名共同规定；增删章节时同步更新。术语以 `glossary.md` 为唯一源稿，`reader.json` 的 `show_glossary: true` 将其直接纳入正文与目录，不另外复制对应表。

范围是通用架构与序列建模。按任务与模态区分研究设置，不将所有工作硬套入语言模型的训练与部署流程。综述正文围绕机制、推导与证据组织，不逐篇堆叠摘要。文献记录只加入核实过的身份、版本和链接；未验证的信息不伪装成研究结论。

## 本地源码入口

源码保持在工作区根的 `repos/<仓库名>/`（如 `repos/flash-attention/`、`repos/deepinfer/`），保留独立 Git 历史、许可证和原有检出状态。笔记、框架说明、原入口及维护脚本的唯一位置为 `reference/framework-notes/`，不再混放在源码容器中；FlashAttention 仓库内上游跟踪的 `AI/` 等资料仍留在原仓库，避免改变其工作树。固定提交、真实路径和注册时状态见 `reference/source-repositories.json`。

`content/05-frameworks.md` 是框架章的组合入口，仅维护章名和嵌入顺序。规范正文分布于 `content/frameworks/`；嵌入后仍是一章连续的阅读内容，不维护第二份完整稿。先讲 FlashAttention 前向／反向与 GPU 组织，再按训练、云端、端侧、异构、编译与服务目的比较框架，最后连接实际问题的方案。保留笔记是来源记录，不参与自动拼接或单独发布；原有相对源码命令属于历史写法，当前路径与核对边界见 `reference/framework-notes/LOCATION.md`。临时实验、调优、报告与缓存仍放系统 TEMP。

### 修改入口

| 内容 | 规范源稿（相对于 `content/frameworks/`） |
|---|---|
| 分层与固定版本 | `overview.md` |
| FlashAttention 算法／GPU 组织 | `flash-attention/algorithms.md`、`gpu.md` |
| llm.c／DeepSpeed | `training/llm-c.md`、`deepspeed.md` |
| vLLM／SGLang | `vllm.md`、`sglang.md` |
| 专用云端框架 | `cloud/{deepinfer,tensorrt-llm,lmdeploy,tgi,lightllm}.md` |
| llama.cpp 与 server／其他端侧框架 | `local/*.md`，每个技术对象单独一稿 |
| ktransformers／PowerInfer／Ascend | `heterogeneous/*.md` |
| 跨框架共同机制 | `cross-cutting.md` |
| nano-vllm／mini-sglang | `minimal/nano-vllm.md`、`mini-sglang.md` |
| 方案选择与验证边界 | `selection.md` |

各目录 `index.md` 只负责组内顺序。子稿标题与展开前保持一致，以保留阅读页的标题锚点。include 语法与源码解读方法见 [源码解读规范](../../../docs/source-analysis.md)。

DeepInfer 子稿按固定提交静态阅读。它的 `vendor/` 子模块（FlashMLA、DeepGEMM、DeepEP、DeepSelect）未拉取，项目也未开源 KV 缓存系统、完整的 PD 分离部署与数据并行负载均衡，因此该稿只讨论引擎内部机制与模型执行，不声称覆盖完整服务；性能数字均为官方文档报告值。内核语言与编译机制（含 TileLang）不由本书维护，它们的规范稿在编译栈书稿《编译栈：前端抽象、Pass 与后端》中；本书只在项目稿里说明谁调用了它们。

`source-excerpts.json` 指定关键代码的仓库、符号与真实行范围；`excerpts.py` 从 `reference/source-repositories.json` 的固定 Git 对象生成 `content/frameworks/excerpts/*.md`。这些是短摘录而非运行时抓取：普通重建无需源码仓库，升级摘录才需要 Git 对象。源码解释在对应项目稿中，代码定位与摘录则嵌入在论点旁；没有将全部上游文件复制进正文。

```powershell
. .\tools\dev-env.ps1
# 检查现有摘录是否与固定提交及选定行范围相同，不改文件：
& $Python dist\transformer-review\work\excerpts.py --check
# 明确改变行范围或固定版本后重新生成：
& $Python dist\transformer-review\work\excerpts.py
```

改变项目机制时优先修改对应子稿；改变代码选择时同步维护摘录范围并核对前后上下文。`manifest.json` 的 `content_dependencies` 是构建时的实际依赖清单，不手工维护生成结果。

## 基础机制与其他主题的修改入口

`content/01-architecture.md` 只组合章内子稿：`architecture/{representation,attention,blocks,moe,expert-parallel,model-families,interaction-paths,mla,dsa,msa,linear-attention,complexity,survey-taxonomy}.md`。位置与置换、注意力与梯度、残差与归一化、条件生成、稀疏传播、核化与秩约束、成本拆分分别维护，修改机制解释不必重写整章。

MoE 路由／均衡在 `architecture/moe.md`，EP 的分派、返回合并和通信口径在 `expert-parallel.md`；`mla.md` 解释 MHA／MQA／GQA、潜在缓存与吸收，`dsa.md` 和 `msa.md` 分别维护 DeepSeek token 选择与 MiniMax 分组块选择。固定来源 [31]–[36]、数学前提和核对边界见 `reference/moe-attention-mechanisms.md`；注意力预算与服务状态容量的衔接在 `inference/execution-cache.md`。这些稿件不依赖运行上游模型或内核。

`content/02-pretraining.md` 组合 `pretraining/{objectives,masked-language,reconstruction,contrastive,data-organization,survey-data,optimization,evaluation}.md`；原始定义与原创推导的范围见 `reference/pretraining-mechanisms.md`。

`content/03-posttraining.md` 组合 `posttraining/{task-adaptation,peft,continual-learning,instruction-sft,reward-policy,direct-preference,agent-environment,distillation,calibration,assessment}.md`；机制、原始论文版本与推导条件见 `reference/posttraining-mechanisms.md`。

`content/04-inference.md` 组合 `inference/{execution-cache,optimization-levels,quantization,sampling,service-environment}.md`，分别维护执行／缓存、优化分层、量化误差补偿、采样校正与端到端资源路径。

`content/06-downstream.md` 组合 `downstream/{language,rag-design,vision,multimodal-audio,time-series,protein-assessment}.md`，分别维护语言与业务预测、RAG、检测、多模态与语音、时间预测以及蛋白质探测。新增原始来源 [25]–[30] 与推导条件见 `reference/inference-applications-mechanisms.md`；不复制完整论文或原图。Zotero 筛选身份和专题证据分别保留在 `reference/zotero-surveys.json` 与 `reference/zotero-survey-reading.md`；原 PDF 继续留在外部 Zotero 存储中，不复制入 `work/`。

## 文献与保留的来源资料

`reading-list.md` 维护文献与外部原文路径，`download-needed.md` 列出尚需提供的原文。`source-map.md` 维护主题映射，不直接进入正文；`reference/jev-research.md` 区分 TypeSafe Jev 的产品资料、相关开源实现与学术研究证据。研读与审校参照 [原创综述方法](../../../docs/review-method.md)，本地方法来源与核对边界见 [review-guidance.md](reference/review-guidance.md)。

四篇核心原文 BERT、ViT、MAE、CLIP 的实际会议版身份和哈希存于 `reference/four-core-sources.json`，主文及选定附录的研读证据存于 `reference/four-core-reading.md`。原文仍位于用户 Zotero 文件夹；`reference/local-sources.json` 保留原有只读查询结果，同时记录用户提供附件的当前可用状态。阅读页的英文引用记录存于 `reader.json`。原始方法的报告结果与本篇分析分别归属，不把来源收录当作实验复现。

完整 SalesRLAgent 来源项目位于 `reference/sales-rl-agent/`，保留原译文、算法、表格、原始引用与提取资料。`reference/sales-source.json` 记录实际外部 PDF。只有一份 canonical 源稿，不将完整译文复制进原创正文，也不因此获得公开许可。

设备端 LLM 综述的完整来源项目位于 `reference/on-device-llm-survey/`，保留 13 份章节源稿、数学、9 幅图、9 张表、原始引用及提取资料。`reference/on-device-source.json` 记录 Chen 等人的外部正式版 PDF，完整 60 页，DOI `10.1007/s10462-026-11538-1`；CC BY-NC-ND 限制和未决引用继续保留，不作为原创正文或公开内容。

DSec 的完整来源项目位于 `reference/deepseek-dsec/`，固定版本为 arXiv:2609.22978v1。它用于交互训练基础设施与推理系统状态管理的机制分析，不是新的注意力架构；原译文和裁图保持本地。

保留来源使用同一重建入口：

```powershell
. .\tools\dev-env.ps1
& $Python dist\transformer-review\work\rebuild-reference.py --source sales-rl-agent
& $Python dist\transformer-review\work\rebuild-reference.py --source on-device-llm-survey
& $Python dist\transformer-review\work\rebuild-reference.py --source deepseek-dsec
```

可用 `--dist` 和 `--library-root` 指向系统 TEMP 中的试验库。来源页沿用库根共享运行时，不需要原始 PDF，也不执行发布。

## 重建

在仓库根目录的 PowerShell 中：

```powershell
. .\tools\dev-env.ps1
& $Python dist\transformer-review\work\rebuild.py
```

`--dist` 可指定系统 TEMP 中的试验输出目录。重建保留 `work/`，只生成本项目阅读页与清单，并引用库根的 `dist/assets/`，不创建私有 CSS/JS 副本。更改共享阅读器不需要修改本项目源稿。

`meta.json` 与 `reader.json` 的公开标记必须一致，生成清单沿用该标记；重建不执行发布。公开快照仅包含批准的原创阅读页，不能包含 `work/`、来源译文或裁图。审批记录保留在任务状态，不写入正文。
