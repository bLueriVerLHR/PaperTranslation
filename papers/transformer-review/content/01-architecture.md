## 1. 基础原理与架构演进

Transformer 把序列建模拆成四件事：输入怎样表示、位置关系怎样进入计算、内容之间怎样交互、特征怎样变换，再由任务目标把这些组件组织起来。本章先说明这几步的基本计算，再看局部连接、累计状态与输入粒度怎样改变信息传播和资源需求。模型定义以原始论文为准，比较视角来自架构综述。[1–4, 6, 9, 10]

{{include:architecture/representation.md}}

{{include:architecture/attention.md}}

{{include:architecture/blocks.md}}

{{include:architecture/moe.md}}

{{include:architecture/expert-parallel.md}}

{{include:architecture/model-families.md}}

{{include:architecture/interaction-paths.md}}

{{include:architecture/mla.md}}

{{include:architecture/dsa.md}}

{{include:architecture/msa.md}}

{{include:architecture/linear-attention.md}}

{{include:architecture/complexity.md}}

{{include:architecture/survey-taxonomy.md}}
