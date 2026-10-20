## 分阶段的编译与后端固定的顺序 {#triton-pipeline}

Triton 的编译按表示分阶段推进，每个阶段对应后端里的一个函数。以 NVIDIA 后端为例，`third_party/nvidia/backend/compiler.py` 依次定义 `make_ttir`（`:286`）、`make_ttgir`（`:302`）、`make_llir`（`:417`）、`make_ptx`（`:541`）与 `make_cubin`（`:575`）。前端先把 Python 源码翻成 TTIR，后端再把 TTIR 变成 TritonGPU 方言、降低到 LLVM、生成 PTX，最后交给 ptxas 得到 cubin。每两个阶段之间是完整的中间表示，可以打印、可以 dump：`make_ttgir` 开头就打开调试输出（`pm.enable_debug()`）。

TTIR 阶段的变换保持保守，`make_ttir` 里只有内联、规范化、算子合并、广播重排、公共子表达式消除、符号死代码消除与循环展开（`:289-297`）。真正决定性能的决策全部发生在 TTGIR 阶段，因为它一开始就把具体的执行配置写进程序：

```python
# 编者定位：repos/triton · ebdd5b6b4856 · third_party/nvidia/backend/compiler.py:310-323
passes.ttir.add_convert_to_ttgpuir(pm, f"cuda:{capability}", opt.num_warps, 32, opt.num_ctas)
if opt.clc:
    nvidia.passes.ttnvgpuir.add_to_clc(pm)
# optimize TTGIR
passes.ttgpuir.add_coalesce(pm)
passes.ttgpuir.add_f32_dot_tc(pm, emuTF32)
nvidia.passes.ttnvgpuir.add_assign_cga_layouts(pm)
passes.ttgpuir.add_remove_layout_conversions(pm)
nvidia.passes.ttnvgpuir.add_optimize_cta_locality(pm)
passes.ttgpuir.add_remove_layout_conversions(pm)
passes.ttgpuir.add_optimize_thread_locality(pm)
passes.ttgpuir.add_accelerate_matmul(pm)
nvidia.passes.ttnvgpuir.add_check_matmul_two_cta(pm)
passes.ttgpuir.add_remove_layout_conversions(pm)
```

`add_convert_to_ttgpuir` 把线程数、每 warp 的线程数与 CTA 数固定下来，从此张量带有布局。接下来这一小段里，`add_remove_layout_conversions` 出现了三次，中间夹着合并访问、CTA 内局部性、线程局部性与矩阵乘加速。清理动作被反复执行，原因在后面的布局一节：`accelerate_matmul` 一类 pass 会把张量改成矩阵指令要求的布局，从而制造出新的转换需求。

管线不是一条直线，它按目标算力分支。同一文件里，算力 8.x 与 9.x 会走 `add_hopper_warpspec`，10.x 走另一组 pass——`add_optimize_accumulator_init`、`add_hoist_tmem_alloc`、`add_promote_lhs_to_tmem`、`add_warp_specialize`、`add_optimize_partition_warps`，末尾还有一次允许移出条件分支的 `add_hoist_tmem_alloc` 与 `add_remove_tmem_tokens`（`:337-352`）。同一份 Triton 源码在两代硬件上由不同的 pass 序列处理，这正是布局编译器把自己绑到目标上的一种表现：管线本身携带着目标知识。

这套结构的代价是可见性。使用者在源码里看不到 loop 流水与线程分工，能调整的只有少量旋钮，出问题时也只能从 TTGIR 起读；反过来说，正因为后端掌握了完整顺序，它才能在中间插入针对矩阵指令与新一代存储层次的改写。
