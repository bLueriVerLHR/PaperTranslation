## 2. 预训练阶段

预训练用数据中可以自行构造的预测关系学习表示。输入中哪些位置可见、预测什么、用什么误差度量，共同决定学习信号；数据分布决定这些信号出现的频率；优化与迁移协议决定有限预算内能形成什么表示、能否用到下游。本章按自回归语言建模、BERT、ViT、MAE 与 CLIP 的顺序讨论这些环节，并把目标的数学性质与具体模型的实验结果分开。[1–4, 17]

{{include:pretraining/objectives.md}}

{{include:pretraining/masked-language.md}}

{{include:pretraining/reconstruction.md}}

{{include:pretraining/contrastive.md}}

{{include:pretraining/data-organization.md}}

{{include:pretraining/survey-data.md}}

{{include:pretraining/optimization.md}}

{{include:pretraining/evaluation.md}}
