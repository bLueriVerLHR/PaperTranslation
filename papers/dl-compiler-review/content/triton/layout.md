## 布局：编译器替使用者做出的那个关键决定 {#triton-layout}

块级编程模型把张量当作整体来写：`tl.load` 一个块，逐元素算，`tl.store` 回去。数据在物理上落在哪个线程的哪个寄存器、在共享内存里按什么顺序摆放，源码里没有对应写法。这些决定由布局承担，它是一张从逻辑坐标到物理位置的映射，决定了访问是否连续、矩阵指令能否直接用寄存器里的值。

布局在 TTIR 转 TTGIR 时被分配下去（`lib/Conversion/TritonToTritonGPU/`），此后每次改变布局都会在程序里留下一个转换操作。转换的代价并不相同。有些转换能在 warp 内部的寄存器之间经由 shuffle 完成，另一些必须绕经共享内存。判断这件事的谓词直接写在分配分析里：

```cpp
// 编者定位：repos/triton · ebdd5b6b4856 · lib/Analysis/Allocation.cpp:124-132
  if (auto cvtLayout = dyn_cast<gpu::ConvertLayoutOp>(op)) {
    auto srcTy = cvtLayout.getSrc().getType();
    auto dstTy = cvtLayout.getType();
    if (!cvtNeedsSharedMemory(cvtLayout))
      return 0;
    // The generic pass uses swizzling
    auto elems = getNumScratchElemsSwizzledCvt(srcTy, dstTy);
    return elems * getBitwidth(srcTy) / 8;
  }
```

`cvtNeedsSharedMemory` 为假的转换不申请暂存空间，为真则按 swizzle 后的元素数算出所需字节数。这段代码同时说明了两件事：转换的代价在编译期就能估出来，而且是按共享内存用量计的——共享内存正是决定占用率与并行度的资源。

既然转换有代价，管线就要减少它们的数量，于是有了反复出现的 `add_remove_layout_conversions`（`third_party/nvidia/backend/compiler.py:317`、`:319`、`:323`、`:375`）。清理之所以要做多轮，是因为后续 pass 会提出新的布局要求：`accelerate_matmul` 把点积换成矩阵指令，而矩阵指令对操作数的布局有固定要求，于是新转换被引入，需要再清一次。整套 TTGIR 阶段因此呈现出“优化—引入转换—消除转换”的交替形态，而不是一次成型的顺序。

还有一类分析专门服务于访存效率。合并访问（coalescing）判断相邻线程是否访问相邻地址，其依据是对张量各维取值规律的推导，实现在 `lib/Analysis/AxisInfo.cpp`，由 `add_coalesce` 施加到布局选择上。这条推理链决定了为读写的张量挑选哪种布局：让一个 warp 的一次访存覆盖尽可能多的连续元素。

概括这一层的分工：使用者给出块形状与计算，编译器选择布局，并把布局不一致的成本落在共享内存流量与占用率上。源码层面的可读性由块级语义保证，性能的可解释性则要求读者进到 TTGIR 里看布局从哪来到哪去。
