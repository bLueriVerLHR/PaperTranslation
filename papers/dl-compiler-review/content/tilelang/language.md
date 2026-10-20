## 语言层：登记计算意图，把线程留给编译期 {#tilelang-language}

一段 TileLang 内核的骨架与 Triton 相似：`T.Kernel(...)` 给出网格与线程数，`T.alloc_shared`、`T.alloc_fragment` 写明缓冲落在哪一层存储，`T.copy` 搬运，`T.gemm` 做矩阵乘，`T.Parallel` 写逐元素计算。相似之处到此为止：这些调用在语言层并不展开成循环或指令，而是被归一化成带区域与注解的图块算子调用，真正决定“哪个线程读写哪个元素”的工作留到降低阶段。这样安排的原因很实际——线程映射与布局的选择依赖整段内核的上下文（相邻算子对同一缓冲的要求、流水把它分成几个版本），单看一行源码无法决定。

`T.copy` 的末段展示了这条分界线：

```python
# 编者定位：repos/tilelang · 876a59e6eb80 · tilelang/language/copy_op.py:107-130
    src, dst = _normalize_copy_regions(src, dst)

    # Build annotations dict before selecting the scalar fast path: a scalar
    # copy with metadata must remain a tile op so the metadata is preserved.
    ann = _normalize_annotations(annotations)

    # Individual arguments take lower precedence than annotations
    if "coalesced_width" not in ann and coalesced_width is not None:
        ann["coalesced_width"] = coalesced_width

    # Parallel loop layout hint (Fragment). Mirrors T.Parallel(loop_layout=...)
    if loop_layout is not None and "parallel_loop_layout" not in ann:
        ann["parallel_loop_layout"] = loop_layout

    if isinstance(src, tirx.BufferLoad) and isinstance(dst, tirx.BufferLoad) and not ann:
        # Scalar fast path. Mirror the dtype conversion the region path applies
        # in copy.cc; cast to the load dtype, which is what BufferStore checks
        # once index lanes are folded in.
        value = src
        if src.dtype != dst.dtype:
            value = tirx.Cast(dst.dtype, src)
        return tirx.BufferStore(dst.buffer, value, dst.indices)

    return tirx.call_intrin("handle", tirx.op.Op.get("tl.tileop.copy"), src, dst, annotations=ann)
```

`_normalize_copy_regions` 把两端统一成区域并校验形状；注解承担后端与优化提示（合并宽度、循环布局、是否允许 TMA）；只有两端都是标量且没有注解时才退化为一次直接存储。剩下的情况保持为一条 `tl.tileop.copy` 调用，留给算子实现与后续 pass 决定用哪种指令、切多宽、走不走异步。源码看起来像 NumPy，运行期并不会逐元素解释——这个落差正是语言层存在的意义。

`T.gemm` 的做法一致而更露骨：它把 A／B／C 区域、转置标记、M／N／K、warp 划分策略、是否清空累加器、可选完成屏障和 C 的起点坐标打包成位置参数，并检查 M／N／K 必须是静态值。静态尺寸的要求直接对应本书总览里的那条前提：编译期已知的尺寸越多，后端能做的静态决定越多。后端方言在此基础上追加自己的旋钮——CUDA 版多一个屏障参数，ROCm 版多 `k_pack`，Ascend 版多 `unit_flag_ctrl`——同一语义靠包装函数适配，内核代码不必分叉。

这种分工的代价出现在两处反馈上。使用者放弃了直接控制线程与指令的能力，遇到推导结果不合预期时只能在图块层加注解或下沉到线程原语；错误信息的落点也远离源码，一条布局冲突会以求解器的措辞出现，而不是指向写错的那一行。换来的是内核在不同形状、不同后端之间保持可读，且优化发生在比手写循环更结构化的一层。
