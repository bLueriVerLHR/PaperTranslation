## MindSpore：图编译的开源部分 {#ascend-mindspore}

与适配层相比，MindSpore 把图编译的更多部分放在仓库里，结构可以分成三块。前端编译在 `mindspore/ccsrc/frontend/jit/ps/`：`action.cc`、`pass.cc`、`pipeline.cc` 分别对应动作、变换与管线三层，同一目录下还有 `compile_cache_manager.cc`（编译缓存）、`fallback.cc`（回退）、`load_mindir.cc`、`validator.cc` 与 `pipeline_split.cc`。后端在 `mindspore/ccsrc/backend/` 分为并列的两条：`ms_backend` 含 `graph_fusion` 与 `runtime`，`ge_backend` 含 `graph_ir`、`pass`、`executor` 与 `runtime`。设备相关部分在 `mindspore/ccsrc/plugin/{ascend, cpu, gpu}`，昇腾侧有 `graph_optimizer/ascend_graph_optimization.cc` 与 `kernel_executor/{ascend_kernel_executor.cc, kernel_select_ascend.cc}`。

变换通过注册表按名字登记，宏把函数名本身当作注册键：

```cpp
// 编者定位：repos/mindspore · c91ca93fd5b37e4f61b0db00994573da86127c5e · mindspore/ccsrc/frontend/jit/ps/pass.cc:134
static auto helper_pass_func_##name = opt::RegisterPassFunc(#name, opt::OptPassConfigLib::PassFunc(name)); \
```

登记之后按具名分组组织进管线，`pass.cc:238` 起的函数构造第一组 pass 表，`:253` 处开始逐项加入。这种“按名注册 + 具名分组”的写法与前一章那个把 pass 顺序硬写在单个后端函数里的做法形成对照：这里的顺序可以由名字与配置组合出来，代价是注册表本身成为一处需要维护的全局状态。

算子选择发生在设备侧。`kernel_select_ascend.cc` 决定一个结点最终用哪个内核，结果记录成 `kernel::KernelBuildInfo`（`SetMatchKernelInfo`，`:339`）。选择过程受开关影响：文件里有读环境变量的入口（`ReadAclnnEnableEnv`，`:400`），也有判断是否启用 aclnn 的函数（`IsEnableAclnn`，`:837`）。同一个算子在昇腾上因此可能落到不同实现上，依据包含构建期与运行期的开关，而不是只看算子名。选定之后的执行准备由 `AscendKernelExecutor` 承担，它的方法序列说明了职责边界：`Initialize`（`:1003`）、`AddMindIRPass`（`:1022`）、`OptimizeGraph`（`:1026`）、`CreateKernel`（`:1057`）、`DoStreamAssign`（`:1098`）。

第三类机制是回退。有些构造无法编译成图，框架为此准备了专门的结点：

```cpp
// 编者定位：repos/mindspore · c91ca93fd5b37e4f61b0db00994573da86127c5e · mindspore/ccsrc/frontend/jit/ps/fallback.h:40-44
// Create a PyExecute CNode by old node or debug_info.
CNodePtr CreatePyExecuteCNode(const FuncGraphPtr &fg, const AnfNodePtr &script, const AnfNodePtr &keys,
                              const AnfNodePtr &values, const NodeDebugInfoPtr &debug_info);
CNodePtr CreatePyExecuteCNode(const AnfNodePtr &orig_node, const AnfNodePtr &script, const AnfNodePtr &keys,
                              const AnfNodePtr &values);
```

这个结点的语义是在图内执行一段 Python，配套的常量给出脚本与键值的命名约定（同文件 `:32-38`）。回退在这里不表现为编译失败，而表现为图里多出一个负责运行 Python 的结点，编译的覆盖范围由它标出。三个栈对同一件事给了三种答案：PyTorch 的捕获层在无法记录时切断图并继续执行，适配层把可回退的算子写成清单，MindSpore 把回退留在图内。

边界在昇腾侧同样清楚：真正生成算子代码的组件不在这个仓库里。仓库能证明的是分流点（`backend/` 下的两条路）、选择机制（`kernel_select_ascend.cc`）与执行准备（`AscendKernelExecutor`），至于内核由谁生成、如何缓存与版本化，只能从外部文档得知。三块拼在一起，昇腾这一侧的可检查范围就划定了：编译的前端与选择在开源仓里，运行期的算子编译器在仓库之外。
