## 适配层：注册、算子生成与回退清单 {#ascend-torch-npu}

PyTorch 为第三方设备预留了一个分派键，适配层的第一件事就是给它一个名字：

```python
# 编者定位：repos/torch-npu · f38351b66d9edcb32ac71b372d68d18baa797106 · torch_npu/_init/registry/backend.py:47
torch.utils.rename_privateuse1_backend("npu")
```

调用之后，`PrivateUse1` 这个键对外显示为 `npu`，张量的设备字符串、模块上的设备迁移方法等一批通用机制随之可用。这一步说明了适配层的定位：它不替换 PyTorch 的分发结构，而是在预留位置注册一个新设备，让框架原有的机制继续工作。

算子侧的接口不是手写的。`torchnpugen/` 里有一套生成器：`gen_backend_stubs.py` 生成后端存根，`gen_npu_c_shim.py` 生成 C 接口胶水层，`codegen_ops_info.py` 处理算子信息，另有针对自动微分与函数化的生成器。这与 PyTorch 自己从算子清单生成注册代码是同一套做法——算子的签名与分派是数据，胶水代码是产物。

覆盖不全的算子走另一条路。`torchnpugen/aoti/fallback_ops.py` 是一份显式清单，条目形如：

```python
# 编者定位：repos/torch-npu · f38351b66d9edcb32ac71b372d68d18baa797106 · torchnpugen/aoti/fallback_ops.py:13-23（节选）
    "aten.__and__": {},
    "aten.__and__.bool": {},
    "aten.__and__.int": {},
    "aten.__iand__": {},
    "aten.__iand__.Scalar": {},
    "aten.__iand__.Tensor": {},
    "aten.__ilshift__": {},
    "aten.__ilshift__.Scalar": {},
    "aten.__ilshift__.Tensor": {},
    "aten.__ior__.Scalar": {},
    "aten.__irshift__.Scalar": {},
```

条目用点号名字标识重载，例如 `aten.__lshift__.Scalar` 与 `aten.__lshift__.Tensor` 是两条不同的记录。把回退写成清单而不是异常处理，意味着“哪些算子能落在昇腾上”在构建期就是确定的，运行期不必靠失败重试来发现。清单之外，运行期还有内核可用性检查（`torch_npu/npu/_kernel_check.py`）。

## 编译路径：既有编译链接到新设备 {#ascend-compile}

`torch_npu/_inductor/` 是把 Inductor 接到昇腾上的扩展包，里面的文件与前章 Inductor 的组成一一对应：`lowering.py` 与 `lowering_common.py` 提供该设备的 lowering，`ir.py`、`graph.py`、`codecache.py`、`choices.py`、`decomposition.py`、`export.py`、`autotune_process.py`、`cpp_builder.py` 分别对应 IR、图处理、代码缓存、选择、分解、导出、调优与构建。这种对应关系本身就是证据：PyTorch 的编译链没有被替换，昇腾补的是后端需要的实现与选择。

补齐过程会遇到覆盖不足，于是这里也有一份回退清单：`torch_npu/_inductor/lowering_fallback_list.py` 从 `torch._inductor` 导入相关模块，并列出应走回退路径的高阶算子一类对象（文件开头可见 `while_loop`、`invoke_quant`、`associative_scan`、`with_effects` 等导入，以及一份列名清单）。两级清单合起来界定了这条路的适用范围：图里的算子要么被 lower 成设备代码，要么落到回退实现上。

到这一步，源码能提供的证据就到头了。设备代码最终由昇腾的算子编译器生成，其缓存与模式由环境变量控制，仓库里只有对应文档——`docs/` 下的 `ACL_OP_COMPILER_CACHE_DIR.md`、`ACL_OP_COMPILER_CACHE_MODE.md` 说明存在算子编译缓存与缓存模式两项控制。本章不推测这些开关背后的实现。

## 图模式与惰性融合 {#ascend-graph}

第二类机制是执行层的图化。`torch_npu/npu/graphs.py:590` 定义了 `NPUGraph`，对应图捕获与回放；`torch_npu/npu/_graph_tree.py` 里的 `NPUGraphNode`（`:740`）与 `NPUGraphTreeManager`（`:1897`）与前一章的 CUDA 图树在命名上对应，处理的是同一类问题——复用内存池时中间结果的存活期冲突。控制流在图捕获中的处理另有专门模块（`torch_npu/npu/_npugraph_conditional_nodes.py:12` 的 `NPUGraphCaptureControlFlowOpDispatchMode`，名字表明它是一个捕获期的分派模式）。

惰性融合这条路把“何时成图”暴露成了一个全局状态，其约束写在模块文档字符串里：

```text
编者定位：repos/torch-npu · f38351b66d9edcb32ac71b372d68d18baa797106 · torch_npu/npu/lazy_fusion.py:14-22（摘录）

    Requires ``TORCH_NPU_LAZY_FUSION`` to be enabled before importing
    torch_npu. This gate cannot override the environment master switch.
    The setting persists until changed; unlike a context manager, this
    function does not automatically restore the previous state.

    A state change flushes the pending graph without waiting for device
    execution to finish. Call at region boundaries, without concurrent
    graph producers. Context managers restore their entry state on exit,
    including when this setter is called inside the context.
```

四点约束都在这里：开关必须在导入之前由环境变量打开，代码里的门无法覆盖它；状态设置持续生效，不随上下文退出而恢复；改变状态会冲刷待处理的图，且不等待设备执行完成；因此调用点应落在区域边界，并避开并发的图生产者。这类约束在 CUDA 侧的同类机制里不常出现在使用者的视野中，而在适配层里必须显式写出，因为成图时机影响了正确性而不只是性能。

同步语义同样如此。`docs/` 下成组出现的行为说明——`ACL_DEVICE_SYNC_TIMEOUT.md`、`synchronization_timeout.md`、`ASCEND_LAUNCH_BLOCKING.md`、`HCCL_DESYNC_DEBUG.md`——对应超时、阻塞式启动与通信失步三件事。设备语义映射到另一套运行时之后，这些差异需要单独交代，文档的存在本身就是这种映射复杂度的证据。

这一节的证据边界很清楚：能读到的是接口、清单与开关，读不到的是图编译器与算子编译器的内部实现。下一节转向昇腾另一条开源路径——MindSpore，它把图编译的一部分放进了开源仓库。
