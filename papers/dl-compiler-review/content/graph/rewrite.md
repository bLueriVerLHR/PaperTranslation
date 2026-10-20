## 改写的两个方向与两种尺度 {#graph-rewrite}

**模式替换**是图级改写里最常见的一种，写法是把“什么样的子图”与“换成什么”成对写出。Inductor 的注意力融合就是这个形态：`torch/_inductor/fx_passes/fuse_attention.py` 里 `_sfdp_pattern_1`（`:54`）对 `_sfdp_replacement_1`（`:63`），`_sfdp_pattern_2`（`:76`）对 `_sfdp_replacement_2`（`:85`），依此类推覆盖带掩码与 dropout 的变体。同类 pass 在同一目录里成组出现：`group_batch_fusion.py`、`mkldnn_fusion.py`、`pad_mm.py`、`decompose_mem_bound_mm.py`、`freezing_patterns.py`、`misc_patterns.py`。

改写不只朝“合并”方向走。MindSpore 在 `mindspore/ccsrc/backend/common/pass/` 下把 `ir_fusion` 与 `ir_fission` 并列——**分裂**与融合同样是一等改写。分裂的用处在于把一个大算子拆成若干个彼此独立、可分别调度或可并行的小算子。判断该往哪个方向走，取决于后端的执行单元粒度：能把更多工作塞进一个内核时融合有利，寄存器或共享内存吃紧时分裂有利。

**整体变换**是另一种尺度，它依赖图的全局性质（数据流形态、缓冲生命周期、依赖关系），不是局部能判定的。TVM 的 relax 层有整套这类 pass：`fuse_ops.cc` 与 `fuse_tir.cc`（算子融合）、`merge_composite_functions.cc`（把标记过的子图合并成外部调用）、`annotate_tir_op_pattern.cc`（打标记，供上一条使用）、`convert_dataflow.cc`（把图转成数据流形式）、`lambda_lift.cc`（把嵌套函数提到顶层）、`normalize.cc`、`fold_constant.cc` 与 `eliminate_common_subexpr.cc`（常量折叠与公共子表达式消除）、`convert_layout.cc` 与 `static_plan_block_memory.cc`（布局转换与静态内存规划）。

尺度不同，失败方式也不同：模式替换匹配不上就退回原图，而整体变换一旦破坏了某个前提，问题会推迟到生成代码时才暴露。这解释了为什么这类 pass 往往附带强烈的静态检查——TVM 的调度原语如此（TVM 那一章），`tirx` 的降低管线也如此。

还有一处变化值得单独指出：**图级决策开始需要代价模型**。Inductor 的 `fx_passes/` 目录里直接放着 `memory_estimator.py` 与 `node_runtime_estimation.py`，另有 `bucketing.py` 与 `overlap_scheduling.py` 一类的排布 pass；MindSpore 的图融合带一个 `parallel_cost_model.cc`（`mindspore/ccsrc/backend/ms_backend/graph_fusion/`）。改写从“等价的代数化简”变成了“在若干合法方案里挑一个”，判断依据是估计出来的内存与时间，而不是语法结构。
