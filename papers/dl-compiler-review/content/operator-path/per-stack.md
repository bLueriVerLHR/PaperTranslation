## 各栈各自交出了什么 {#operator-path-per-stack}

### Triton：使用者写出整条递推 {#op-triton}

Triton 官方教程里有一份融合注意力实现（`python/tutorials/06-fused-attention.py`）。它把上一节的递推逐行写进一个循环：

```python
# 编者定位：repos/triton · ebdd5b6b4856 · python/tutorials/06-fused-attention.py:67-93
    for start_n in tl.range(lo, hi, BLOCK_N, warp_specialize=warp_specialize):
        start_n = tl.multiple_of(start_n, BLOCK_N)
        # -- compute qk ----
        k = desc_k.load([offsetk_y, 0]).T
        qk = tl.dot(q, k)
        if STAGE == 2:
            mask = offs_m[:, None] >= (start_n + offs_n[None, :])
            qk = qk * qk_scale + tl.where(mask, 0, -1.0e6)
            m_ij = tl.maximum(m_i, tl.max(qk, 1))
            qk -= m_ij[:, None]
        else:
            m_ij = tl.maximum(m_i, tl.max(qk, 1) * qk_scale)
            qk = qk * qk_scale - m_ij[:, None]
        p = tl.math.exp2(qk)
        # -- compute correction factor
        alpha = tl.math.exp2(m_i - m_ij)
        l_ij = tl.sum(p, 1)
        # -- update output accumulator --
        if not IS_HOPPER and warp_specialize and BLOCK_M == 128 and HEAD_DIM == 128:
            BM: tl.constexpr = acc.shape[0]
            BN: tl.constexpr = acc.shape[1]
            acc0, acc1 = acc.reshape([BM, 2, BN // 2]).permute(0, 2, 1).split()
            acc0 = acc0 * alpha[:, None]
            acc1 = acc1 * alpha[:, None]
            acc = tl.join(acc0, acc1).permute(0, 2, 1).reshape([BM, BN])
        else:
            acc = acc * alpha[:, None]
```

几处细节说明这里的分工。缩放系数被折进指数：代码用 `exp2` 与一个把 `log2(e)` 一并计入的 `qk_scale`，与上一节按自然指数写的递推等价，只是换了一个底数。循环头把 `warp_specialize` 作为参数传给 `tl.range`，也就是把线程分工的请求写在源码里。最值得注意的一段是重标定的分支：在非 Hopper、开启专门化且块形状恰为 128×128 的条件下，作者把 `acc` 拆成两半分别缩放再拼回（`:88-91`）。这一步是使用者在手工处理布局——直接对 `acc` 做缩放会触发一次代价不低的布局转换，拆成两半后两个半区各自映射到更好的形状上。循环末尾还有一行注释交代了语句顺序的用意：`l_i` 与 `m_i` 的更新放在循环尾部，为的是降低寄存器压力（`:102-105`）。

同一个仓库里还有一份用新方言 Gluon 写的版本（`python/examples/gluon/01-attention-forward.py`）。它把布局与流水显式写出来，说明即便在 Triton 内部，也存在一套“把后端自动做的选择交回使用者”的写法。

至于布局转换、共享内存分配与流水排布，仍由 Triton 那一章讲的那条固定管线完成。使用者交出的是循环结构与递推公式，后端交出的是这些结构如何落到硬件上。

### TileLang：递推写成图块算子，布局交给推导 {#op-tilelang}

TileLang 官方示例里的融合注意力（`examples/flash_attention/example_mha_fwd_bshd.py`）把同一条递推写成图块算子，而不是循环里的标量表达式：

```python
# 编者定位：repos/tilelang · 876a59e6eb80 · examples/flash_attention/example_mha_fwd_bshd.py:59-87
            for k in T.Pipelined(loop_range, num_stages=num_stages):
                T.copy(K[bz, k * block_N : (k + 1) * block_N, by, :], K_shared)
                if is_causal:
                    for i, j in T.Parallel(block_M, block_N):
                        acc_s[i, j] = T.if_then_else(bx * block_M + i >= k * block_N + j, 0, -T.infinity(acc_s.dtype))
                else:
                    for i, j in T.Parallel(block_M, block_N):
                        acc_s[i, j] = T.if_then_else(k * block_N + j >= seq_len, -T.infinity(acc_s.dtype), 0)
                T.gemm(Q_shared, K_shared, acc_s, transpose_B=True, policy=T.GemmWarpPolicy.FullRow)

                T.copy(scores_max, scores_max_prev)
                T.fill(scores_max, -T.infinity(accum_dtype))
                T.reduce_max(acc_s, scores_max, dim=1, clear=False)
                for i in T.Parallel(block_M):
                    scores_max[i] = T.max(scores_max[i], scores_max_prev[i])
                for i in T.Parallel(block_M):
                    scores_scale[i] = T.exp2(scores_max_prev[i] * scale - scores_max[i] * scale)
                for i, j in T.Parallel(block_M, block_N):
                    acc_s[i, j] = T.exp2(acc_s[i, j] * scale - scores_max[i] * scale)
                T.reduce_sum(acc_s, scores_sum, dim=1)
                for i in T.Parallel(block_M):
                    logsum[i] = logsum[i] * scores_scale[i] + scores_sum[i]
                T.copy(acc_s, acc_s_cast)

                for i, j in T.Parallel(block_M, dim):
                    acc_o[i, j] *= scores_scale[i]

                T.copy(V[bz, k * block_N : (k + 1) * block_N, by, :], V_shared)
                T.gemm(acc_s_cast, V_shared, acc_o, policy=T.GemmWarpPolicy.FullRow)
```

分工在三个地方与 Triton 不同。第一，`T.alloc_fragment` 只声明寄存器块的逻辑形状（`:41-48`），没有线程维；每个元素归哪个线程由布局推导决定，而 Triton 的块级程序同样不写线程，但布局变换与转换代价要到 TTGIR 才看得见。第二，流水的深浅是一个参数（`T.Pipelined(..., num_stages=...)`），它先于布局推导改写缓冲版本（见 TileLang 章的 Pass 顺序一节），而 Triton 把流水写在后端固定的 pass 里。第三，重标定这一步在这里是一条普通的 `T.Parallel` 循环（`:83-84`）：Triton 教程为了避开一次布局转换，把 `acc` 拆成两半分别缩放再拼回；TileLang 版本不做这个手工拆分，代价与收益就转移到推导与寄存器压力上——如果推导选出的片布局导致溢出，症状会以溢出重置与占用率下降的形式出现在后端，而不是在源码里。

合法性检查也换了位置。Triton 靠后端 pass 的前置条件，失败时仍生成代码只是慢；TileLang 在推导阶段对布局冲突直接报错（`LayoutConflictException`），并把两侧布局打印出来；目标绑定也在编译期完成，方言专属的参数（例如 CUDA 的屏障、ROCm 的 `k_pack`）写错位置会在构造调用时失败。对使用者的含义是：一条错误的声明不会静默变慢，而会在编译期或以断言失败的形式出现，前提是你能读懂它的报错。

这些例子都是官方仓库中的演示内核，不是生产实现；本书不运行它们，也不给出任何跨栈的性能比较。

### CuTe：从示例里选一套模板 {#op-cute}

CuTe 一侧没有“注意力编译器”，有的是按架构给出的实现。仓库里可以直接找到三份：`examples/41_fused_multi_head_attention`、`examples/88_hopper_fmha`（单文件 `88_hopper_fmha.cu` 加一份 `README.md`）、`examples/77_blackwell_fmha`。它们的写法与前几章的 CuTe 用法一致：选定集体层（collective）与指令原子，给出分块形状与线程划分，合法性由 CuTe 那一章那套编译期条件约束。

这条路把选择权放在使用者手里：块形状、共享内存布局、流水级数由作者写定，库负责证明这套划分能落到目标指令上，并在不能时拒绝实例化。代价也在同一处——换一代硬件往往意味着重选一套示例参数，而收益是编译期就能确定代码形态。

### PyTorch：先在图上认出模式，再选择模板 {#op-pytorch}

Inductor 对注意力的处理分两级。第一级是图上的模式改写，`torch/_inductor/fx_passes/fuse_attention.py` 里成对出现的函数说明了做法：`_sfdp_pattern_1`（`:54`）与 `_sfdp_replacement_1`（`:63`），`_sfdp_pattern_2`（`:76`）与 `_sfdp_replacement_2`（`:85`），依此类推到带掩码与 dropout 的变体。每一对描述“什么样的子图可以被替换成融合后的缩放点积注意力”。这类改写不涉及指令选择，只在图上确认结构并换掉算子。

第二级是代码生成。融合后的算子经由 flex attention 的模板转成内核源码，模板文件在 `torch/_inductor/kernel/flex/templates/`（`flash_attention.py.jinja`、`flash_attention_backward.py.jinja`、`flex_attention.py.jinja`），生成的结果仍是 Triton 源码，再交给 Triton 那一章那条管线编译。于是同一次计算在 PyTorch 里经过两级改写：图上的模式替换，以及模板层的内核生成。

模式匹配带来的边界很具体：写法稍有不同就可能不被认出来，此时图照旧执行，只是少了融合收益，程序仍然正确。这类“匹配失败即退化”的设计在 PyTorch 那一章已经出现过一次。

### TVM：图上的算子加两条外部出路 {#op-tvm}

TVM 图里有注意力的算子定义（`src/relax/op/nn/attention.cc`），但它对同一个算子的处理并不唯一。仓库里同时能看到两条外部出路：一条经由 BYOC 调用 CUTLASS，`python/tvm/contrib/cutlass/attention_operation.py` 提供 `instantiate_attention_template`（`:24`）、`instantiate_flash_attention_template`（`:173`）与 `instantiate_flash_attention_var_len_template`（`:278`），也就是为注意力生成 CUTLASS 代码；另一条是运行时侧的 cuDNN 前端集成（`src/runtime/extra/contrib/cudnn_frontend/attention.cc`），把算子交给厂商库。

三条路对应三种不同的成本。走自己的调度意味着要写出一份在目标上足够好的调度；走 BYOC 意味着一部分控制权交给外部模板，换来成熟的实现；走厂商库意味着支持的形状与数据类型由库决定。TVM 那一章讲的分层在这一个算子上表现得最清楚：图上的算子保持稳定，落到哪里由后端配置与分派决定。

### 昇腾：把模式融合成一个算子，再交给设备侧 {#op-ascend}

MindSpore 的做法与 Inductor 的第一级相似，也在图上做模式改写，但产出不同。`mindspore/ccsrc/backend/common/pass/ir_fusion/flash_attention_fusion.cc` 里，`FlashAttentionFusionBase::DefinePattern`（`:109`）定义要匹配的结构，匹配成功后由 `CreateFlashAttentionNode` 造出融合结点——第一版在 `:218`，第二版在 `:336`；针对 BNSD 布局另有一条创建路径 `CreatePromptFlashAttentionCnodeForBNSD`（`:114`）。

与 PyTorch 的差别在产出物的性质。这里造出的结点对应设备侧已实现的一个融合算子，具体落到哪个内核由设备插件决定（昇腾那一章看到的 `kernel_select_ascend.cc` 与 `KernelBuildInfo`）。开源部分负责识别模式与造结点，算子的实现与编译在仓库之外。因此这一条路上，模式匹配的条件同时约束着正确性与可用性：条件比设备的实现宽，结点就选不到内核；比实现窄，就白白失去融合机会。

两版 `CreateFlashAttentionNode` 并存也说明这条路的演进方式：新模式与旧模式各自保留，由匹配条件区分，而不是在同一处分支里兼容多种结构。
