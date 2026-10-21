### FlashMLA：把 MLA 的潜在状态写进逐模型内核

多头潜在注意力在推理时把每个历史位置压成「潜在向量 + 解耦位置键」，主注意力读的是这段潜在状态，键值不再逐头展开（第 2 章）。通用注意力内核按逐头 K／V 的布局组织访存与矩阵乘，遇到这种结构要先展开；FlashMLA 的做法是把展开省掉，直接按潜在状态的形状写解码与预填充内核。[51]

#### 一个仓库里放了哪几类内核

| 类别 | 作用 | 栈上的位置 |
|---|---|---|
| 稀疏解码／预填充 | DSA 的主分支只读选中的 token 集合 | CUDA C++，按头数与 KV 格式实例化 |
| 稠密预填充与反向 | 训练侧与全注意力路径 | 复用 CUTLASS 的 FMHA 模板（SM100） |
| 融合小算子 | 把 Q-归一化、Q-旋转、注意力、输出端反向旋转与转 FP8 合成一个 kernel | CUDA C++ 主体，测试与部分实现依赖 TileLang |
| 昇腾内核 | 同一套稀疏注意力在 Ascend 950 上的实现 | `.asc` 实例化文件加 C++ 头 |

融合内核要解决的是访存：这些小算子各自读写一遍张量，合并之后中间量留在片上。仓库报告该 kernel 在 B200 上预填充达 1460 TFLOPS、解码 950 TFLOPS，代价是必须提前置换 Q 与输出投影的权重布局。[51]

#### 架构绑定写进了构建脚本

`setup.py` 的目标架构是架构专属的 `sm_100a` 与 `sm_103a`，理由写在注释里：kernel 用到带缩放的 `cvt` 指令，架构家族级的 `sm_100f` 不够；`sm_103a` 还对 `exp` 有更好的代码生成。

```text
# 文件：FlashMLA/setup.py（固定提交 0f11e178）
# 26-35 行
# `-gencode` targets. We use the architecture-specific ones (sm_100a / sm_103a) instead of the
# family-specific one (sm_100f) because the kernels use `cvt` with `.scaled::n2::ue8m0`, and
# sm_103a additionally enables better code generation for `exp`.
CUDA_ARCHS = ["sm_100a", "sm_103a"]

# Build against PyTorch's stable C++ ABI.
STABLE_ABI_FLAGS = [
    "-DTORCH_TARGET_VERSION=0x020a000000000000",  # PyTorch >= 2.10
]
CUDA_STABLE_ABI_FLAGS = [*STABLE_ABI_FLAGS, "-DUSE_CUDA"]
```

两件事由此确定。其一，同一份源码只为新架构生成机器码，Hopper 用户必须切回旧提交；原因是让指令选择与缩放格式对齐硬件。其二，构建针对 PyTorch 的稳定 ABI，不绑某个具体次版本，装出来的扩展不会因为 PyTorch 升级而重编。头数也按需实例化：融合内核只对 64 与 128 两个查询头数展开模板。

#### 稀疏内核与 KV 量化互相牵制

DSA 的索引器选出的是一批 token 位置，主分支要从潜在状态里把这些位置取出来。位置集合不连续，访存因此不规整；把 KV 压到 FP8 或 FP4 之后，每个位置还要带缩放因子，取数变成「按索引取块 + 反量化」。这两件事叠在一起，决定了内核必须按索引预取、按块对齐，而不能沿用连续窗口的流水线。仓库在 2026-09-30 的版本里改掉了 KV 格式，说明这套布局仍在随模型演化，旧缓存在新内核下不可读。

这些数字都属于维护者报告，条件是各自的 GPU 与 CUDA 版本（B200 配 CUDA 13.3、Ascend 950 为 95% 峰值）。本节没有编译或运行该库，也没有核对报告值；能确认的是构建目标、内核分类与接口形状。
