### 从模型计算到系统执行：三种不同的优化对象

Transformer 的架构规定了表示如何交互，训练与推理框架则决定这些计算怎样映射到设备、内存和请求。这里需要区分三个层次。算子层执行矩阵乘、注意力、归一化和量化；引擎层组织模型前向、状态分配、批处理与采样；服务层处理协议、连接、排队、路由和模型生命周期。FlashAttention 属于训练与推理都可使用的注意力加速技术，vLLM、SGLang 等主要组织推理执行，Ollama 则把执行引擎连接到模型分发与本地服务。它们各占一层，彼此没有替代关系。

训练要保存或重算激活、计算梯度并更新参数。推理不执行反向，却要为每条活跃序列长期维护 KV cache，直到该请求结束。由此可以分开三件事：模型能否装进显存，取决于权重与激活的峰值；能否训练，取决于激活、梯度与优化器状态是否放得下、通信是否跟得上；能否同时服务很多长请求，取决于 KV cache 的容量与调度。本节先从 FlashAttention 的前向和反向算法解释算子层，然后沿训练执行、云端调度（含为单一模型定制的生产引擎）、端侧部署、异构硬件和服务组织展开。框架的共同机制与不同设计在同一条数据流上比较，不按功能名堆成排名。算子与 DSL 编译器的内部机制（Triton、TileLang、CUTLASS／CuTe、TVM、LLVM、MLIR 等）不在本书展开，另见编译栈书稿《编译栈：前端抽象、Pass 与后端》。

##### 各层要回答的问题与失败方式

| 层 | 本节对应对象 | 该层要回答的问题 | 典型失败方式 |
|---|---|---|---|
| 算子 | FlashAttention | 同一段注意力在片上存储里怎么分块、怎么重算 | 分块后数值递推不一致，或访存成了瓶颈 |
| 训练执行 | llm.c、DeepSpeed | 参数、梯度与优化器状态如何摆放与重算 | 状态装不下，或通信取代了计算成为限制 |
| 推理引擎 | vLLM、SGLang、DeepInfer、极简实现 | 请求如何变成设备上的一批执行与状态写入 | 长请求拖慢短请求，或 KV 容量先耗尽 |
| 专用与端侧 | TensorRT-LLM、LMDeploy、llama.cpp、Ollama 等 | 在固定硬件与分发形态下怎样换编译、量化与生命周期 | 量化与内核不匹配，或加载/卸载引起抖动 |
| 异构 | ktransformers、PowerInfer、vLLM-Ascend | 容量或平台不足时把计算放到哪里 | 专家或激活跨设备搬运成为新瓶颈 |
| 服务组织 | 各家的前端与协议层 | 排队、路由、取消与多模型共存如何定义 | 路由局部性与负载均衡相互冲突 |

每一行都可以单独读懂，但真实系统会把它们叠在一起。同一个部署里，算子决定单步能跑多快，引擎决定每步做什么，服务层决定请求什么时候到这个引擎；只改其中一层时，另外两层留下的限制常常让这部分收益无法体现；本节因此按问题与作用点组织，而不按功能列表罗列。

#### 固定源码与结论范围

下表列出本节采用的本地源码版本。框架路径均以工作区根目录为基准，位于 `repos/<仓库名>/`。短提交标识用于阅读定位，完整提交记录保留在本地来源清单。文中的源码文件与符号指向这些版本，不默认适用于后续版本。

| 对象 | 固定提交 | 本节关注的执行对象 |
|---|---|---|
| [FlashAttention](https://github.com/Dao-AILab/flash-attention/tree/e9515d5dee6ade134a33d6020d38d01ef0596996) | `e9515d5` | 注意力前向、反向及 GPU 流水线 |
| [llm.c](https://github.com/karpathy/llm.c) | `f1e2ace` | 训练的前向、反向、优化器与验证 |
| [DeepSpeed](https://github.com/microsoft/DeepSpeed) | `8fb2c9a` | 训练状态管理与推理执行 |
| [vLLM](https://github.com/vllm-project/vllm) | `b0e21b3083` | 请求进度、块池与注意力后端 |
| [SGLang](https://github.com/sgl-project/sglang) | `00bcc25f6c` | 前缀树、缓存感知调度与程序接口 |
| [DeepInfer](https://github.com/deepseek-ai/DeepInfer) | `774ce244` | 单一模型的生产执行：异步调度、有界重放与变长验证 |
| [TensorRT-LLM](https://github.com/NVIDIA/TensorRT-LLM) | `4151db3c` | TRT 引擎与 PyTorch 两条执行路线 |
| [LMDeploy](https://github.com/InternLM/lmdeploy) | `110965c` | TurboMind／PyTorch 引擎与量化 |
| [TGI](https://github.com/huggingface/text-generation-inference) | `b4adbf2` | Rust 接入、批调度与执行协议 |
| [LightLLM](https://github.com/ModelTC/LightLLM) | `6c9e03b` | token 级 KV 分配与 Triton 内核 |
| [llama.cpp](https://github.com/ggml-org/llama.cpp) | `cb7934c52` | ggml 图、量化格式与序列状态 |
| [exllamav2](https://github.com/turboderp-org/exllamav2) | `7dc12af` | 低比特权重、缓存与动态生成 |
| [Ollama](https://github.com/ollama/ollama) | `42e911b` | 模型清单、下载、加载与卸载 |
| [MLC-LLM](https://github.com/mlc-ai/mlc-llm) | `b84792a` | 模型编译与跨端运行时 |
| [ktransformers](https://github.com/kvcache-ai/ktransformers) | `a5d7ad9` | CPU／GPU 专家计算放置 |
| [PowerInfer](https://github.com/SJTU-IPADS/PowerInfer) | `8bd56d6` | 激活稀疏与热／冷权重放置 |
| [vLLM-Ascend](https://github.com/vllm-project/vllm-ascend) | `4ebb309` | NPU 平台、算子与通信适配 |
| [nano-vllm](https://github.com/GeeeekExplorer/nano-vllm) | `bb823b3` | 请求、分块缓存和简化调度 |
| [mini-sglang](https://github.com/sgl-project/mini-sglang) | `9a91cfa` | 前缀树、准入、图重放与重叠执行 |

源码能说明某个状态或执行路径如何组织，不能单独证明该框架更快。以下方案分析来自机制推导与静态阅读，没有配合 GPU 测量。硬件、模型、精度、形状和并发改变时，需要重新测量；单个配置的性能不能外推成跨框架排名。

