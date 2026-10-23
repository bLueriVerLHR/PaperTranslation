# 来源索引（章节 → 仓库与路径）

维护用索引：正文论点用到的主要源码位置。行号只对 `meta.json` 中记录的固定提交成立；检索时从工作区根 `repos/<仓库>/` 继续定位。这里不重复正文论证，只标出改动时应核对的位置。

| 章节 | 仓库 | 主要位置 |
|---|---|---|
| 01 分层与研究对象 | 多仓 | 对照维度的定义；`content/01-overview.md` 单文件，无子稿 |
| 07 TVM 表示层 | tvm | `docs/arch/index.rst`（两类函数）、`include/tvm/tirx/stmt.h`（`RegionStmt`）、`src/{s_tir,tirx}` 目录划分 |
| 07 TVM 调度 | tvm | `src/s_tir/schedule/primitive/`（原语清单）、`compute_at.cc` 与 `compute_inline.cc` 的 `ScheduleError` |
| 07 TVM 自动调优 | tvm | `python/tvm/s_tir/meta_schedule/tune.py`、`src/s_tir/meta_schedule/{space_generator,search_strategy,task_scheduler}/` |
| 07 TVM 降低 | tvm | `src/tirx/transform/lower_tirx.cc`、`src/tirx/transform/tile_primitive_dispatch.cc`、`src/target/codegen.cc`、`docs/arch/codegen.rst` |
| 02 Triton 管线 | triton | `third_party/nvidia/backend/compiler.py`（`make_ttir`/`make_ttgir`/`make_llir`/`make_ptx`/`make_cubin`） |
| 02 Triton 布局 | triton | `lib/Analysis/Allocation.cpp`（`cvtNeedsSharedMemory`）、`lib/Conversion/TritonGPUToLLVM/ConvertLayoutOpToLLVM.cpp`、`lib/Analysis/AxisInfo.cpp` |
| 02 Triton 流水 | triton | `lib/Dialect/TritonGPU/Transforms/Pipeliner/`、`.../WarpSpecialization/` |
| 02 Triton 调优 | triton | `python/triton/runtime/autotuner.py` |
| 03 TileLang 语言层 | tilelang | `tilelang/language/copy_op.py`（`copy`）、`gemm_op.py`（`_gemm_impl` 与方言包装）、`src/op/operator.h` |
| 03 TileLang 布局推导 | tilelang | `src/transform/layout_inference/layout_inference.cc`（`BufferUseDefCollector::Run`）、`layout_cost_model.h`（默认与 `io-aware` 模型）、`src/op/operator.h`（`InferLevel`） |
| 03 TileLang Pass 与后端 | tilelang | `tilelang/cuda/pipeline.py`（`CUDAPassPipelineBodyPrologue`）、`tilelang/backend/module.py`（`register_backend`）、`tilelang/cuda/backend.py` |
| 03 TileLang 算子落点 | tilelang | `examples/flash_attention/example_mha_fwd_bshd.py`、`examples/deepseek_mla/`、`tilelang/cuda/language/gemm_op.py` |
| 03 TileLang 多后端边界 | deepinfer | `deepinfer/model_executor/layers/tilelang_ops/{cuda,asc}/schedule_mtp_varlen.py`、`tilelang_ops/ops.py`（仅作使用方证据，见 `tilelang/backends.md`） |
| 11 CuTe 布局代数 | cutlass | `python/pycute/layout.py`、`include/cute/layout.hpp` |
| 11 CuTe 指令与静态检查 | cutlass | `include/cute/atom/{copy_atom.hpp,mma_atom.hpp,mma_traits_sm*.hpp,copy_traits_sm*.hpp}`、`include/cute/int_tuple.hpp`、`include/cute/config.hpp` |
| 11 CuTe DSL | cutlass | `python/CuTeDSL/cutlass/base_dsl/compiler.py`、`examples/python/CuTeDSL/` |
| 04 PyTorch 分发 | pytorch | `aten/src/ATen/core/dispatch/Dispatcher.h`、`c10/core/DispatchKey.h`、`aten/src/ATen/native/native_functions.yaml` |
| 04 PyTorch 捕获 | pytorch | `torch/_dynamo/{convert_frame.py,symbolic_convert.py,output_graph.py,guards.py,config.py}` |
| 04 PyTorch 反向 | pytorch | `torch/_functorch/{aot_autograd.py,partitioners.py}` |
| 04 PyTorch 生成 | pytorch | `torch/_inductor/{compile_fx.py,graph.py,scheduler.py,codegen/}` |
| 04 PyTorch 缓存 | pytorch | `torch/_inductor/codecache.py`、`torch/fx/experimental/symbolic_shapes.py`、`torch/_inductor/cudagraph_trees.py` |
| 12 昇腾适配层 | torch-npu | `torch_npu/_init/registry/backend.py`、`torchnpugen/`、`torch_npu/_inductor/`、`torch_npu/npu/{graphs.py,lazy_fusion.py,_graph_tree.py}` |
| 12 昇腾图编译 | mindspore | `mindspore/ccsrc/frontend/jit/ps/{pass.cc,pipeline.cc,fallback.cc,compile_cache_manager.cc}`、`mindspore/ccsrc/backend/{ms_backend,ge_backend}`、`mindspore/ccsrc/plugin/ascend/` |
| 06 中间表示 | 多仓 | triton `lib/Dialect/`、`cmake/llvm-info.json`；cutlass `python/CuTeDSL/cutlass/base_dsl/compiler.py`；tvm `include/tvm/ir/instrument.h`、`src/sym/presburger_set.{h,cc}`、`python/tvm/relax/frontend/`；mindspore `core/ir/{anf.cc,func_graph.cc}`、`core/{load_mindir,proto}/`、`ccsrc/include/runtime/hardware_abstract/kernel_base/graph_fusion/graph_kernel_flags.h`；pytorch `torch/_inductor/ir.py`、`torch/_inductor/codegen/{cutedsl,pallas.py,flydsl}/` |
| 05 计算图技术 | 多仓 | pytorch `torch/_inductor/fx_passes/`、`torch/export/`；tvm `src/relax/transform/`；mindspore `ccsrc/backend/common/pass/{ir_fusion,ir_fission}/`、`ccsrc/backend/ms_backend/graph_fusion/` |
| 05 CUDA 执行图 | pytorch | `aten/src/ATen/cuda/CUDAGraph.{h,cpp,cu}`、`c10/cuda/test/impl/CUDATest.cpp`、`torch/_inductor/cudagraph_trees.py`（`apply_checkpoint_execution_state_in_allocator`）、`torch/_higher_order_ops/cudagraph_conditional_nodes.py`、`docs/source/user_guide/torch_compiler/torch.compiler_cudagraph_trees.md`；运行时接口语义引 NVIDIA CUDA Programming Guide v13.4.2 §4.2（滚动页面，2026-10-23 核对），与 PyTorch 图树策略分开 |
| 13 贯穿对照 | 多仓 | triton `python/tutorials/06-fused-attention.py`；cutlass `examples/{41_fused_multi_head_attention,88_hopper_fmha,77_blackwell_fmha}`；pytorch `torch/_inductor/fx_passes/fuse_attention.py` 与 `torch/_inductor/kernel/flex/templates/`；tvm `python/tvm/contrib/cutlass/attention_operation.py`、`src/runtime/extra/contrib/cudnn_frontend/attention.cc`；mindspore `mindspore/ccsrc/backend/common/pass/ir_fusion/flash_attention_fusion.cc` |
| 14 代价与退化 | 多仓 | 汇总前几章位置：`tune.py`、`autotuner.py`、`codecache.py`、`int_tuple.hpp`、`guards.py`、`fallback_ops.py`、`lazy_fusion.py`、`src/transform/layout_inference/` |
| 08 LLVM 流程与 SSA | llvm-project | `llvm/lib/Passes/PassBuilderPipelines.cpp`、`llvm/lib/Transforms/Utils/{PromoteMemoryToRegister,LCSSA,LoopSimplify}.cpp`、`llvm/lib/Transforms/InstCombine/InstructionCombining.cpp`、`llvm/lib/Transforms/Scalar/{SROA,SCCP}.cpp` |
| 09 LLVM 循环与并行 | llvm-project | `llvm/lib/Transforms/Vectorize/{LoopVectorize,LoopVectorizationLegality,SLPVectorizer,VPlan}.cpp`、`llvm/lib/Transforms/Scalar/{LoopInterchange,LoopUnrollPass,LICM,SimpleLoopUnswitch,LoopFlatten}.cpp`、`llvm/lib/Transforms/IPO/OpenMPOpt.cpp`、`llvm/lib/Analysis/{LoopAccessAnalysis,ScalarEvolution,DependenceAnalysis}.cpp` |
| 10 LLVM 后端 | llvm-project | `llvm/lib/CodeGen/{RegAllocGreedy,RegAllocFast,RegAllocPBQP,LiveIntervals,CalcSpillWeights,InlineSpiller,SplitKit,SpillPlacement,TargetPassConfig}.cpp`、`llvm/include/llvm/CodeGen/LiveInterval.h` |

## 更新版本时的核对顺序

1. 改 `meta.json` 的 `source.repositories` 提交与 `reader-meta.md` 的版本说明；两者必须一致。
2. 按上表逐处复核行号与符号；路径改名（例如 TVM 的 `src/tir` → `src/s_tir`）需要在正文里一并更新。TileLang 的布局推导与 Pass 顺序是易变区，升级版本时优先复核 `src/transform/layout_inference/` 与 `tilelang/cuda/pipeline.py`。
3. 重新运行 `work/rebuild.py` 与结构检查，确认锚点、引用与 MathML 仍然通过。
4. 昇腾侧的结论只覆盖开源部分；版本变化若涉及 CANN 接口，需要在正文明确新的边界。LLVM 部分另一份固定提交在独立教程项目时已核对，并入后未改动正文与行号；若单独升级 `llvm-project`，需回到 `llvm/` 各子稿逐处复核。
