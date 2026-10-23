## 执行侧的图：CUDA Graph 的捕获、实例化与回放 {#graph-cuda-graph}

编译器计算图表示算子、循环及其数据依赖，优化可以改变计算的组织方式。CUDA 图则表示内核启动、内存操作等运行时工作及其依赖，用 `cudaGraph_t` 描述、用 `cudaGraphExec_t` 执行。它既可由流捕获得到，也可显式构造；运行时利用完整工作流提前准备，降低重复提交成本（CUDA Programming Guide §4.2）。

图级中间表示（intermediate representation，IR）与执行图的分工在于可见语义：编译器可以分析和融合算子，CUDA 图按已经指定的操作与依赖执行。重复回放通常复用拓扑和参数，但 CUDA 还提供受限的参数更新、条件结点与设备端发射。PyTorch 图树采用的固定地址与按路径重录策略，需要与这些运行时接口能力分开讨论。

### 一次启动的成本落在哪里 {#graph-cuda-launch-cost}

把内核放进流不是零成本操作。驱动要为每个内核做一串准备，参数检查、地址解析、命令写入与提交是其中常见的几项；这部分开销按内核计费，内核执行时间越短，它在端到端时间里的比重越大。CUDA 官方的说法是，图将相当一部分逐内核准备工作提前完成，之后可以用很低的开销重复发射（CUDA Programming Guide §4.2）。

设一步推理有 <math><mi>K</mi></math> 次内核启动，每次的 CPU 侧提交成本为 <math><mi>c</mi></math>。逐次提交成本约为 <math><mi>K</mi><mi>c</mi></math>；图回放的 CPU 成本另记为 <math><msub><mi>c</mi><mi>g</mi></msub></math>，不假定它等于单内核启动成本。捕获、实例化等一次性准备成本合记为 <math><msub><mi>C</mi><mtext>setup</mtext></msub></math>，按 <math><mi>R</mi></math> 次回放摊销，得到主机提交成本模型：

<math display="block"><mrow><msub><mi>T</mi><mtext>CPU</mtext></msub><mo>≈</mo><mi>K</mi><mi>c</mi><mspace width="1em"/><mo>→</mo><mspace width="1em"/><msup><msub><mi>T</mi><mtext>CPU</mtext></msub><mo>′</mo></msup><mo>≈</mo><msub><mi>c</mi><mi>g</mi></msub><mo>+</mo><mfrac><msub><mi>C</mi><mtext>setup</mtext></msub><mi>R</mi></mfrac></mrow></math>

以下为教学算例：取 <math><mi>K</mi><mo>=</mo><mn>300</mn></math>、<math><mi>c</mi><mo>=</mo><mn>3</mn></math> µs，主机提交成本约为 0.9 ms。若 GPU 工作本身耗时 3 ms，0.9 ms 相当于该执行时长的 30%；只有再假定两者完全不重叠，端到端时间才是 3.9 ms，提交占比约 23%。GPU 工作为 30 ms 时，同样的非重叠模型中占比约为 2.9%。这些参数不是测量值，也未给出图回放成本，不能据此确定实际加速比。

端到端收益取决于省下的提交是否位于关键路径上。GPU 经常等待主机提交时，降低提交成本可能减少空隙；主机已经提前提交足够工作时，省下的 CPU 时间未必缩短作业。图还可能使运行时获得整体调度优化机会，因此上述模型只核算主机提交一项，不是 CUDA 图全部收益的严格上界。

<figure>
<a href="assets/figures/01-launch-lifecycle.svg"><img src="assets/figures/01-launch-lifecycle.svg" alt="逐次提交的 CPU 成本约为 K 乘 c；图执行的一次性准备按 R 次摊销，每次另付图回放成本 c_g。地址和其他参数可在接口限制内更新，拓扑不兼容时需要重新实例化；PyTorch 图树另采用按形状和路径重录的策略。"></a>
<figcaption>图 1：主机提交成本的示意模型。一次性准备按回放次数摊销；CPU 成本下降不直接等于端到端时间下降。</figcaption>
</figure>

### 结点与依赖：一张只决定“什么时候开始”的图 {#graph-cuda-structure}

结点类型由运行时定义：内核、CPU 函数调用、内存拷贝、memset、事件记录与等待、外部信号量、空结点、条件结点、内存结点，以及把整张图当作结点插入的子图（CUDA Programming Guide §4.2.1.1）。边是依赖。一个结点在它的依赖全部完成后随时可以被调度，具体什么时候执行由 CUDA 决定（同节）。

流在回放里只承担排序。同一份可执行图不能与自身并发，一次发射排在前一次之后；流只负责这次发射与流上其它异步工作的先后，既不约束图内部的并行，也不决定结点在哪个执行单元上跑（CUDA Programming Guide §4.2.7）。所以回放的效果是把一张排好的依赖图交给运行时，由它按依赖展开并行，并非把整张图当成一次更大的内核启动。

内核结点提供入口、参数及依赖，并不自动暴露可供算子融合的高层语义。编译器通常在生成内核前完成融合，再选择哪些工作组成执行图；运行时仍可依赖整张图优化提交和调度，显式构图也可以修改图描述。CUDA 12.3 起边可以携带数据，把“等到什么程度开始”与“阻塞到哪一部分”分开表达，目前唯一的非默认用途是 programmatic dependent launch（§4.2.1.2）；这属于发射时序的细化，与前面几节讨论的依赖改写不是同一件事。

### 捕获：把流上的工作记下来 {#graph-cuda-capture}

图的来源之一是捕获。`cudaStreamBeginCapture` 把一条流置入捕获模式，此后投放到该流上的工作不进入执行队列，而是追加到一张正在构建的图；`cudaStreamEndCapture` 结束捕获并返回这张图（CUDA Programming Guide §4.2.2.1.2）。捕获可以在任何流上做，唯独不能是 legacy（NULL）流，`cudaStreamPerThread` 可以（同节）。

捕获对宿主代码的约束比“别写同步”更细。跨流依赖只能通过捕获期的事件表达，并且必须在开始捕获的那条流上结束捕获，其它流先要汇回起源流，否则整个捕获失败；被捕获的流以及涵盖它的更宽句柄都不能同步或查询，因为这些工作从未被安排执行；当一条依赖会把捕获内容与非捕获内容连起来时，运行时倾向于报错而不是忽略这条依赖，只有进出捕获模式的瞬间例外；一旦发生非法操作，捕获图失效，相关流与事件在结束捕获前一律报错（同节）。

PyTorch 的封装把这些规则落成了前置检查。`capture_begin` 要求当前流不是默认流（`aten/src/ATen/cuda/CUDAGraph.cpp:165-168`），并且先建立内存池路由再开始捕获（`:236-253`）。这个顺序有原因，注释给出的解释是若反过来，autograd 线程的 `free()` 会在捕获已开始的状态下发出非法的 `cudaEventRecord`（`:236-238`）。捕获结束时还要数一遍结点，结点数为零会告警，因为它通常意味着流或设备选错了（`:320-323`）。

捕获期间不执行 GPU 代码，只把操作记进图；仓库文档把这条性质写明为“stream capture does not execute GPU code”（`torch/_higher_order_ops/cudagraph_conditional_nodes.py:47-51`）。两个后果都与框架的取舍有关：捕获可以记录 GPU 操作而不消费这些操作的新结果，但仍需满足参数、地址与库调用的有效性要求。若宿主后续计算必须等待捕获中 GPU 操作的结果，就无法按普通捕获方式继续；这与显式构图支持 CPU 函数结点并不矛盾。

### 实例化与回放 {#graph-cuda-instantiate}

`cudaGraph_t` 只是描述，要发射先实例化成 `cudaGraphExec_t`（`cudaGraphInstantiate`），再 `cudaGraphLaunch` 到某条流上。实例化验证图并准备可执行资源，重复回放用于摊销这些成本。它并不保证所有准备都在此完成：例如带内存结点的图可能在上传或首次发射时建立物理映射（CUDA Programming Guide §4.2.5.4.1）。

PyTorch 的实例化带两个标志，`cudaGraphInstantiateFlagAutoFreeOnLaunch` 与 `cudaGraphInstantiateFlagUseNodePriority`（`CUDAGraph.cpp:368-370`）。前者有具体理由：典型用法里有些张量（图的输入输出）在两次回放之间不释放，若分配器后端是 `cudaMallocAsync`，图的内部记账要求带这个标志来实例化（`:356-362`）。

回放可以换流（`:407`），换流有代价。图内存的物理映射按“能否并发”决定是否复用，把原本同流串行的图改到另一条流上发射，运行时可能要为它重新映射（§4.2.5.4）。

已经实例化的图能被更新，但更新遵守拓扑与次序：`cudaGraphExecUpdate` 要求更新图与原图的拓扑相同、依赖在 API 调用中出现的次序相同、汇点结点的次序一致（CUDA Programming Guide §4.2.3.1）；只想改少量参数时用逐结点接口（§4.2.3.2）；限制列在 §4.2.3.4：内核函数所属上下文不能变；拷贝与置值更新限于受支持的一维操作，分配上下文与设备等条件须保持；拷贝不能任意改变内存类型或传输种类；条件结点自身的部分参数不能改变，但条件体内结点仍按各自规则更新。内存结点另有限制，不能用一张当前已实例化为其他可执行图的描述图进行相应更新。因而地址、标量和部分启动参数可更新，拓扑不兼容则需重新实例化，不能把“形状变化”一概等同于 CUDA 禁止更新。

本节核对的 PyTorch ATen 图封装与 Inductor 图树路径未使用 `cudaGraphExecUpdate`。图树文档采用按不同形状、输入地址和执行路径录制或复用图的策略；外部输入也可能先复制到固定缓冲区，而非每个地址变化都重录（`torch.compiler_cudagraph_trees.md`，Limitations 与 Dynamic Shapes）。这将部分动态性转换为录制次数、输入复制和图缓存占用。

### 地址与活跃性：池、检查点与图树 {#graph-cuda-memory}

对没有更新参数的 PyTorch 回放，结点继续使用录制时的设备地址；新数据需要放到相应地址，或由框架复制到静态输入缓冲区。图树文档将这种回放约定描述为“同样的内核、同样的参数与依赖、同样的内存地址”，并补充地址里的值可以变（`docs/source/user_guide/torch_compiler/torch.compiler_cudagraph_trees.md:11-15`）。地址固定以后，内存复用要重新回答一次前面章节提出的问题：某个中间值从产生到使用之间，能不能一直占住同一块位置。

CUDA 图内存结点与框架私有池是两个不同层次的分配机制；框架还需要决定多张图是否共享池。

一种是交给图自己管。捕获 `cudaMallocAsync` 与 `cudaFreeAsync` 会生成内存结点，图拥有这些分配，生存期按 GPU 序确定，地址在整个图生命期内不变，即使驱动换了背后的物理页；同一张图内生存期不重叠的分配可以复用同一块物理内存（CUDA Programming Guide §4.2.5.1）。带 `AutoFreeOnLaunch` 实例化的图可以带着未释放的分配再次发射，发射时自动插入异步释放（§4.2.5.2.4）；池里的物理内存不随图销毁立即还给系统，要显式调用 `cudaDeviceGraphMemTrim`（§4.2.5.5）。

一种是把框架自己的分配器接到私有池上，PyTorch 的原生缓存分配器采用这条路径。捕获开始前 `beginAllocateToPool` 把这次捕获期间的所有分配路由到私有池（`CUDAGraph.cpp:239-243`），录制与预热期间由 `_use_cuda_memory_pool_manager` 打开同一个池（`torch/_inductor/cudagraph_trees.py:716-741`）。若后端为 `cudaMallocAsync` 且传入的是用户创建的池句柄，封装会忽略该句柄并告警，由 CUDA 默认异步池管理捕获分配（`CUDAGraph.cpp:216-225`）。

若前向与反向分别使用私有池，两个池无法充分复用空间，可能增加峰值占用（`torch.compiler_cudagraph_trees.md:33`）。

共享池省内存，但它把顺序写成了前提。

源码摘录：共享池的顺序约束。仓库 `pytorch/pytorch`，提交 `92f43bbed42c61d2553a49cbd85bc8b5078b1cf0`，`aten/src/ATen/cuda/CUDAGraph.h:163-175`，符号 `CUDAGraph::mempool_id_`。[固定版本](https://github.com/pytorch/pytorch/blob/92f43bbed42c61d2553a49cbd85bc8b5078b1cf0/aten/src/ATen/cuda/CUDAGraph.h#L163-L175)。

```cpp
  // uuid used to request a particular private mempool from CUDACachingAllocator.
  // By default, this will be set to {id_, 0}.
  //
  // If capture_begin is called with "pool=other_graph.pool()", this graph's mempool_id_
  // will be set to the other graph's mempool_id_, and therefore share a mempool with the
  // other graph.
  //
  // If capture_begin is called with "pool=handle" where "handle" came from graph_pool_handle(),
  // it will share a mempool with any other captures that used "pool=handle".
  //
  // Sharing a mempool across graphs saves memory, and it's safe if you
  // know you'll replay those graphs in the same order you captured them.
  MempoolId_t mempool_id_;
```

末尾两句注释是这一节的难点所在：共享的安全前提是回放顺序与录制顺序一致。框架想在同一条线程上反复走不同分支，就必须自己维持这个不变量，或者在确有把握时放弃共享。

麻烦出在记账上。回放只发射内核，分配器的 CPU 侧记账不再更新，于是它不知道用户程序里哪块内存还活着（`torch.compiler_cudagraph_trees.md:23`）。要在这张图之后再录一张新图，就得先把记账恢复到“这张图刚跑完”的样子。

源码文档摘录：从回放切换到录制。仓库 `pytorch/pytorch`，提交 `92f43bbed42c61d2553a49cbd85bc8b5078b1cf0`，`torch/_inductor/cudagraph_trees.py:30-34`，模块文档字符串。[固定版本](https://github.com/pytorch/pytorch/blob/92f43bbed42c61d2553a49cbd85bc8b5078b1cf0/torch/_inductor/cudagraph_trees.py#L30-L34)。

```text
The ability to switch from replay to record is fairly nontrivial: remember that
when you replay a CUDA graph, you only replay CUDA operations; no CPU side state
is updated.  In particular, the CPU-side book-keeping for the allocator is not
reconstructed.  However, to record a new child CUDA graph, we must restore this
book-keeping.  This is what checkpoint pool state is used for.
```

对应实现是两处调用：录制完成时 `_cuda_getCheckpointState` 存下池状态（`cudagraph_trees.py:1689-1691`），需要在这条路径之后继续录制时，`apply_checkpoint_execution_state_in_allocator` 用 `_cuda_setCheckpointPoolState` 把状态写回分配器（`:3416-3450`）。写回之后，池里剩下的块重新对得上“哪些还活着”，录制新图时的分配才不会压掉仍被引用的中间值。

有了检查点，一段代码可以按走过的路径分裂成多份录制。`1 → 2 → 4` 与 `1 → 3 → 4` 各要一份，因为结点 4 的输入地址在两份录制里不同（`torch.compiler_cudagraph_trees.md:63-78`）。这类录制按父子路径组成图树。输入地址、形状与存活条件不匹配时可能增加录制，不能把源程序路径数直接当成图份数的精确公式。

从机制上看，这一步把“活跃性决定内存复用”从编译器搬到了运行时。编译器在静态分析里推不出的活跃性，这里用录制那一刻的实际存活代替，用一份录制把那个瞬间的布局固定下来。这是对代码结构作出的解释，不是仓库文档的表述。

<figure>
<a href="assets/figures/02-pool-liveness.svg"><img src="assets/figures/02-pool-liveness.svg" alt="三个状态并排：录制 G1 时分配器记账与图内存池一致，结束时存下检查点；回放 G1 只发射内核，池里的中间值仍活着而记账停在录制时刻；恢复检查点后再录 G2，记账回到 G1 结束的状态。下方是由此形成的图树：1 到 2 到 4 与 1 到 3 到 4 各需一份录制。"></a>
<figcaption>图 2：回放与记账的错位。回放不更新分配器记账，因此要在同一池上继续录制，先得把记账恢复到上一张图结束的时刻。</figcaption>
</figure>

### 控制流：条件结点与固定地址的冲突 {#graph-cuda-conditional}

控制流在图里由条件结点承担。条件值放在 `cudaGraphConditionalHandle` 中，由 `cudaGraphConditionalHandleCreate` 创建，一个 handle 只能绑到一个条件结点，且不能销毁；创建时给 `cudaGraphCondAssignDefault`，每次图执行开始会把条件值初始化成默认值，不给则每次执行开始时值未定义（CUDA Programming Guide §4.2.4.1）。结点分 IF、WHILE、SWITCH 三类，条件体是子图，子图另有要求：所有结点在同一设备上，只允许内核、空结点、拷贝、memset、子图与条件结点，不能用动态并行与设备端发射（§4.2.4.2）。

PyTorch 的实现在 CUDA 12.4 起可用（`CUDAGraph.h:126-130`）。它在当前捕获流上取捕获信息，创建 handle，用一个单线程内核执行 `cudaGraphSetConditional` 写入条件值（`aten/src/ATen/cuda/CUDAGraph.cu:9-23`），再用 `cudaGraphAddNode` 加入条件结点、把当前流的依赖改指向它，最后在一条新建的非阻塞子流上以 `cudaStreamBeginCaptureToGraph` 把条件体记进子图（`CUDAGraph.cpp:596-672`）。这条路径在设备上更新与判定条件，避免每次分支判断都往返宿主；宿主仍负责构图、实例化与发射。

固定地址这条限制在这里反过来决定了控制流的写法。CUDA 12.8 之前没有 if-else 条件结点，PyTorch 用两个 IF 结点代替，第二个的条件取反，并把 else 分支的输出拷进 if 分支的输出：

源码摘录：将两个分支的输出合并到固定地址。仓库 `pytorch/pytorch`，提交 `92f43bbed42c61d2553a49cbd85bc8b5078b1cf0`，`torch/_higher_order_ops/cudagraph_conditional_nodes.py:157-177`，符号 `if_else_node`。[固定版本](https://github.com/pytorch/pytorch/blob/92f43bbed42c61d2553a49cbd85bc8b5078b1cf0/torch/_higher_order_ops/cudagraph_conditional_nodes.py#L157-L177)。

```python
    # if-else is not supported until CUDA 12.8. Therefore, we use two
    # if conditions, where one evaluates !pred
    outs = []

    for lazy_pred, fn in [
        (lambda: pred, true_fn),
        (lambda: torch.logical_not(pred), false_fn),
    ]:
        with _if_body(lazy_pred()):
            outs.append(fn(*operands))

            # The output of the else branch gets copied into the
            # output of the if branch. This is done because the rest
            # of the cudagraph after the conditional node has fixed
            # inputs, so we need to merge the two outputs into a
            # single output.
            if len(outs) == 2:
                for if_out, else_out in zip(
                    pytree.tree_iter(outs[0]), pytree.tree_iter(outs[1])
                ):
                    if_out.copy_(else_out)
```

注释给了理由：条件结点之后的结点输入已经固定，两个分支必须合流到同一块地址（`cudagraph_conditional_nodes.py:168-172`）。WHILE 同理，循环携带的张量在条件体输出后若地址不同，就得 `copy_` 回原地址（`:227-229`）。这个封装通过复制统一分支输出地址，可能增加数据移动；它是该固定提交的合流实现，不能概括为所有 CUDA 条件图都必须复制两个分支的结果。

捕获不执行 GPU 代码这条性质还有一个用法。数据相关的控制流不一定会走到每个子图，没走到的分支里的算子没被预热，于是 PyTorch 用一次最终被丢弃的宽松捕获遍历两个分支的宿主调用，理由写在文档字符串里：捕获不执行 GPU 代码，分支是纯 FX 图、没有 CPU 侧效果（`cudagraph_conditional_nodes.py:42-51`）。

设备端发射是同一类能力的极限形式。用 `cudaGraphInstantiateFlagDeviceLaunch` 实例化并 `cudaGraphUpload` 之后，一张图可以在另一张图的结点内部发射，只能发射进三个命名流（fire-and-forget、tail、sibling），限制是单设备与结点类型子集（§4.2.6）。固定提交还包含一个负向测试定义：c10 的测试先给图加一个内存分配结点，再按设备端发射去实例化，断言驱动报出“Device-launched graphs and conditional nodes do not support MEM_ALLOC nodes”（`c10/cuda/test/impl/CUDATest.cpp:60-79`）。该测试描述预期错误，并非本书运行测试所得的结果。本节核对的 ATen 封装和 Inductor 图树执行路径未使用设备端发射。设备图还需遵守并发限制，更新只能在宿主进行且需重新上传（§4.2.6）。

### 代价与边界 {#graph-cuda-costs}

维护更多可执行图通常增加设备资源占用，但具体增长取决于图结构、运行时版本与内存共享。仓库文档记录了一个数值：CUDA 12.4 与驱动 550 之前，NVIDIA 在 CUDA 图里为每个内核启动占用 64 KB 设备内存（`torch.compiler_cudagraph_trees.md:179-181`，报告值）。若将文档中的 64 KB 按十进制解释，300 个内核结点对应约 19.2 MB 的历史口径估算；一般结点数不能直接替代内核结点数，也不能将这个旧版本报告用于预测新版本占用。这个成本解释了为什么“按形状重录”只在形状有限时划算，也解释了文档为什么建议把输入补齐到少数固定形状，或者干脆跳过动态形状的图化（同文 `:183-187`）。

宿主侧的要求表现为一组跳过条件：就地修改 eager 输入的函数、含 CPU 算子的函数、跨设备算子、自由的未支撑符号、被标记为 `cudagraph_unsafe` 的自定义算子（`torch.compiler_cudagraph_trees.md:203-225`）。这些是该版本 Inductor 图树的跳过条件，除 CUDA 捕获限制外，还包括框架对输入修改、设备管理与符号的处理策略；CUDA 本身支持宿主函数结点，普通 CUDA 图也不能与单设备的条件体或设备发射图限制混为一谈。

分区是另一条出路。打开图分区后，编译器把非 GPU 算子、设备拷贝、控制流算子与不安全自定义算子切出去，对剩下的部分图化（同文 `:272-293`）。同一个“切开”的动作因此发生两次：编译器按融合与内核边界切一次，运行时按可捕获性再切一次；一次融合决策在设备侧还要过一遍能不能进图的检查。

执行图要求构图或更新时提供可执行的操作、参数与依赖。动态性可以由参数更新、条件子图、输入复制、按形状重录或分区回退承担，各自增加检查、复制、存储或提交成本。短内核多、执行反复且主机提交暴露在关键路径上的负载，更有机会摊销准备成本；训练还需要处理跨图激活存活与池记账。编译器的高层优化和运行时的图提交由此作用于不同成本，不能互相替代。
