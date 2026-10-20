# PyTorch：从字节码捕获到算子生成 {#pytorch}

PyTorch 的编译能力长在一个已经跑起来的框架上。算子调用先经过一层分发，张量带着设备与状态信息；编译要在这套分发之上把执行过程记录下来，再交给下游生成设备代码。这条路决定了它的难点不在代码生成，而在三件事：记录得是否完整、假设是否仍然成立、不成立时怎么退回。这套捕获加生成的结构对应 `torch.compile` 中的 TorchDynamo 与 TorchInductor（Ansel et al. 2024）。本章按分发、捕获、反向、生成、缓存五步走。

{{include:pytorch/dispatch.md}}

{{include:pytorch/capture.md}}

{{include:pytorch/aotautograd.md}}

{{include:pytorch/inductor.md}}

{{include:pytorch/cache.md}}
