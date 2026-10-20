## 分区：把图切成可独立处理的部分 {#graph-partition}

分区决定“哪里是边界”。边界一旦定下，两侧就可以各自独立优化：一侧交给别的编译器、别的硬件，或者干脆不编译。

**交给外部实现。** TVM 的做法是先标记再合并：`annotate_tir_op_pattern.cc` 给符合某个模式的子图打上标记，`merge_composite_functions.cc` 把打了标记的子图合成一次外部调用（这两个文件都在 `src/relax/transform/`，TVM 那一章讲到的 BYOC 由此落地）。昇腾侧的选择过程在这里同样是一次分区：`kernel_select_ascend.cc` 决定每个结点落到哪个内核（昇腾那一章），同一个图因此可以被切成若干由不同实现承接的片段。

**训练图的前后向分区。** AOTAutograd 把前向与反向放在一张联合图上切开，切法决定了哪些中间值需要保留、哪些由反向重算。这一步写在 `torch/_functorch/partitioners.py:4178` 的 `min_cut_rematerialization_partition`，文档字符串说明它是“让反向重算前向”，并把它称作内存带宽与计算量之间的权衡（同文件 `:4186-4193`）。分区结果直接决定峰值显存。

**失效时的分区。** Dynamo 遇到无法记录的语义会结束当前图并继续执行，MindSpore 把无法编译的构造换成执行 Python 的结点（`fallback.h:40-44`）。两者在语义上都是分区：把图切开，其中一段不走编译。这类分区与优化无关，只为了让程序继续正确运行，因此它在源码里留下的痕迹是守卫与回退结点，而不是调度决策。

**并行与通信的分区。** 图里的依赖关系是这类优化的前提。MindSpore 在 `mindspore/ccsrc/frontend/parallel/` 下处理并行策略与切分，注意力一类算子还有专门的策略信息（`ops_info/flash_attention_score_info.cc` 一带）；PyTorch 在 `torch/_inductor/fx_passes/` 下有 `ddp_fusion.py`、`bucketing.py`、`overlap_scheduling.py`、`overlap_preserving_bucketer.py`，把通信与计算按依赖关系编排重叠。这些 pass 都需要完整的图才能做：谁依赖谁、哪些通信可以互相等待拖动，都不是局部信息。

四类分区共享一条代价：**跨边界的中间值必须具体化**。落到边界之外的张量要在全局内存里真的存在，边界之内的可以只活在片上存储里。这条代价在贯穿对照那一章那个例子上最清楚——把整个注意力放进一个内核，边界外只有输入与输出；一旦把某一步切出去，那一步的输入输出都要在全局内存里往返一次。分区的收益与代价因此是同一件事的两面：边界让两侧可以独立优化，也让跨越边界的每一份数据都要付一次搬运。
