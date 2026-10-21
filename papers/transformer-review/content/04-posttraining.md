## 4. 后训练阶段

后训练把预训练得到的能力接到具体任务、领域与行为要求上。任务微调改变模型承担的输出职责，参数高效方法限制可更新的范围，持续学习处理新旧目标之间的干扰；示范与偏好提供不同类型的监督；蒸馏与校准分别改变承载知识的模型和概率的解释。本章按这些机制依次讨论。[1–3, 15, 19–23]

{{include:posttraining/task-adaptation.md}}

{{include:posttraining/peft.md}}

{{include:posttraining/continual-learning.md}}

{{include:posttraining/instruction-sft.md}}

{{include:posttraining/reward-policy.md}}

{{include:posttraining/direct-preference.md}}

{{include:posttraining/agent-environment.md}}

### 蒸馏、校准与适配效果评估

{{include:posttraining/distillation.md}}

{{include:posttraining/calibration.md}}

{{include:posttraining/assessment.md}}
