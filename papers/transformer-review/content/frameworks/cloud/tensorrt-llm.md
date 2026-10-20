#### TensorRT-LLM：引擎构建与动态执行路线

固定版本同时保留 TRT 引擎与 `_torch/` 路线。经典路线经构建生成 engine，将部分图优化、精度和内核选择提前；PyTorch 路线在 `_torch/attention/`、`pyexecutor/`、`speculative/`、`compilation/` 组织执行与优化。两条路线把专门化放在不同阶段：预先构建能够固定一部分执行决策，动态路线则在运行组织中保留更多形状与调度处理。所需构建产物、启动路径和适配条件因此不同。

`cpp/tensorrt_llm/kernels/` 将上下文融合注意力、解码注意力、weight-only 矩阵乘、MoE、采样和通信等分开。预填充与解码的不同形状由不同内核承接，低比特格式与特定硬件原语紧密耦合。`_torch/attention/ATTENTION_DEVELOPER_GUIDE.md` 与后端接口提供了新注意力实现的接入边界。

实际场景是“模型和硬件长期固定，需要降低延迟并纳入现有 NVIDIA 部署栈”。可分别评估 engine 与 PyTorch 路线，固定模型、硬件、精度和形状范围，考察构建／预热、峰值内存、请求尾延迟以及升级重建成本。模型频繁变化或形状范围很宽时，特化收益可能被构建和维护成本抵消；不存在由厂商身份推出的性能第一。

`pyexecutor/cuda_graph_runner.py`、`breakable_cuda_graph/`、KV 管理、连接器与卡死诊断说明优化对象不止单个 kernel。多节点还要同时维护通信拓扑、专家映射和状态传输；一次局部快速矩阵乘未必改善端到端延迟。

