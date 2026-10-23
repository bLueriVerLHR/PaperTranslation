## 术语对应表

本书采用以下中文用语。IR 名称、类名、pass 名称、指令名与仓库路径保留原名，便于与固定提交的源码对照。同一个词在不同栈里的含义可能不同，下表按栈分别注明。

| 英文术语 | 本书用语 | 区别与范围 |
|---|---|---|
| IR (intermediate representation) | 中间表示 | 一层可检查、可变换的程序表示，层次由所处阶段决定 |
| lowering | 降低（lowering） | 把较高层表示改写为更接近执行目标的形式，与“质量下降”无关 |
| pass / pass pipeline | 变换／变换管线 | 单个改写步骤／步骤的固定次序；次序本身影响结果 |
| dialect | 方言 | 同一 IR 框架内针对某层次定义的操作与类型集合 |
| kernel | 内核 | 一次设备端启动所执行的完整计算 |
| tile / tiling | 分块 | 把张量计算切成可放入片上存储或寄存器的小块 |
| layout | 布局 | 逻辑坐标到物理位置的映射，决定线程访问与合并方式 |
| layout conversion | 布局转换 | 改变映射；跨内存层次时通常要经过共享内存或寄存器重排 |
| coalescing | 合并访问 | 相邻线程访问相邻地址，使一次内存事务覆盖多元素 |
| predication / masking | 谓词化／掩码 | 用条件决定哪些线程或元素参与读写 |
| thread–value mapping | 线程—元素映射 | 哪个线程负责哪些逻辑元素 |
| pipeline / multibuffering | 流水／多缓冲 | 重叠搬运与计算，代价是额外缓冲与同步 |
| autotuning / search space | 自动调优／搜索空间 | 由调度参数构成的候选集合及其评测方式 |
| cost model | 代价模型 | 预测候选方案好坏；可解析、可测量或两者结合 |
| tensorization | 张量化 | 把细粒度运算组合成一条矩阵或向量指令 |
| quantization | 量化 | 用低位宽表示数值；与调度层次无关 |
| dispatch / operator registration | 分发／算子注册 | 依据输入类型选择具体实现 |
| graph capture | 图捕获 | 把执行过程中的算子序列记录成可变换的图 |
| CUDA Graph | CUDA 图 | 运行时工作与依赖的图，可显式构造或从流捕获；支持受限更新和条件结点，与算子级编译器图不同层 |
| graph description / executable graph | 描述图／可执行图 | `cudaGraph_t` 是可检查的描述，`cudaGraphExec_t` 是实例化后可发射的形式 |
| graph node / dependency | 图结点／依赖 | 结点是启动单元，边是“谁等谁”；调度时机由运行时决定，流只负责与外部排序 |
| graph memory node | 图内存结点 | 可显式构造，也可由捕获异步分配与释放生成；图内存池与框架缓存分配器私有池需区分 |
| conditional node | 条件结点 | IF／WHILE／SWITCH 三类，条件体是子图，条件值由设备内核写入 |
| device graph launch | 设备端发射 | 从另一张图的结点内部发射，只能发射进三个命名流 |
| pool checkpoint | 池检查点 | 录制时存下的分配器记账状态；回放不更新记账，继续录制前需要恢复 |
| CUDA Graph Trees | CUDA 图树（保留英文） | 按路径分裂的多份录制与它们的池共享结构；同一段代码可能对应多份 |
| graph partition（CUDA 图） | 图分区 | 把 CPU 算子、设备拷贝、控制流与不安全自定义算子切出，只对剩余部分做图化；与图级分区不同层 |
| guard | 守卫 | 运行前检查假设是否仍成立，不成立则回退 |
| backend / target | 后端／目标 | 针对具体硬件生成代码的部分 |
| shared memory | 共享内存 | 片上、块内可见的存储 |
| compile-time vs runtime | 编译期／运行期 | 决定信息在哪一阶段已知；多数代价由此划分 |
| graph-level IR / loop-level IR | 图级 IR／循环级 IR | 前者以算子为结点，后者以循环与缓冲为结点 |
| MLIR | MLIR | 提供方言机制、pass 管理器与转换框架的基础设施，本身不规定 IR 层次 |
| FX graph | FX 图 | PyTorch 捕获产物的表示形式，由 Python 对象构成 |
| ANF / FuncGraph | ANF 函数图 | MindSpore 的图表示，以函数与规范化赋值形式组织 |
| MindIR | MindIR | MindSpore 可序列化的图格式 |
| graph break | 图断裂 | 捕获失败处结束当前图，其余部分按解释执行 |
| partition | 分区 | 把图切成可独立处理的部分，边界两侧各自优化 |
| rematerialization | 重算 | 反向重新计算前向中间值，用计算换内存 |
| liveness | 活跃性 | 中间值从产生到使用之间是否存活，决定内存可否复用 |
| TVM | TVM | 本书指 TVM 编译器栈（图级 Relax 与调度／TIR 层），不指某个发行版 |
| CUDA | CUDA | NVIDIA 的设备编程模型与工具链；与 HIP、Metal、Ascend 并列为目标，不是某个库名 |
| DSL | 领域特定语言 | 为某类计算或硬件设计的受限表达形式；这里的 Triton／TileLang 都是嵌入 Python 的 DSL |
| TTGIR | TTGIR | Triton GPU 层方言上的 IR；布局与共享内存分配在这一层被确定 |
| TTIR | TTIR | Triton 顶层方言上的 IR；尚未绑定布局与线程映射 |
| GEP | GEP | LLVM 的 `getelementptr` 地址计算指令；非零偏移常让分析放弃一般模式 |
| AA | 别名分析（alias analysis） | 判断两个访问是否可能指向同一位置的框架，具体答案取决于实现与分析链 |
| ADCE | 激进死代码消除（ADCE） | 以控制流可观察性为判据的 DCE 变体，与普通 DCE 的保守程度不同 |
| TRE | 尾递归消除（TRE） | 把尾递归改写为循环；与展开、内联属于不同的变换目标 |
| SROA | SROA | 标量替换聚合体的 Pass；与 mem2reg 作用对象不同 |
| SCCP | SCCP | 稀疏条件常量传播；与 DCE 常在同一轮清理中出现 |
| DCE | 死代码消除（DCE） | 删除无副作用且结果未使用的代码；不等于删除未被观察的状态 |
| LV | 循环向量化器（LoopVectorize） | LLVM 的循环级向量化 Pass；与 SLP 的入口和候选范围不同 |
| LTO | 链接时优化（LTO） | 把优化推迟到链接阶段以跨目标文件分析；不是运行时机制 |
| layout inference | 布局推导 | 由算子提出的约束求解线程与寄存器映射的编译期过程，不是运行时数据搬运 |
| fragment layout | 片布局（fragment layout） | 逻辑计算块到（线程，寄存器）位置的映射；与 KV 页、共享内存布局不等价 |
| warp specialization | warp 特化 | 把搬运与计算分给不同 warp 以拉长流水；增加同步与寄存器／共享内存预算 |
| token（前端语境） | 词法单位 | 仅在 LLVM 前端指词法 token，不等同于语言模型分词结果 |
| AST / Machine IR | 抽象语法树／机器中间表示 | 依次保留不同层次的语言与目标信息 |
| CodeGen | 代码生成 | Clang 的 AST→IR 与 LLVM 后端的机器代码生成需区分 |
| analysis / transform | 分析／变换 | 推导事实／修改程序结构；二者职责不同 |
| SSA | 静态单赋值形式 | 每个 SSA 值只有一个定义；不自动解决内存别名 |
| def-use chain | 定义—使用链 | 连接值的定义与使用位置 |
| promotion / mem2reg | 提升／mem2reg | 将适用的局部内存状态变为 SSA 值，不是硬件寄存器分配 |
| PHI / phi | PHI／phi 指令 | 按到达的前驱边选择输入值 |
| dominance / dominance frontier | 支配关系／支配边界 | 路径必经关系／SSA 合流位置分析 |
| basic block / CFG | 基本块／控制流图 | 指令区域／基本块之间的控制边 |
| header / latch / preheader | 循环头／回边块／前置块 | 循环汇合点／回边所在块／循环外准备入口 |
| LCSSA | 循环封闭 SSA | 循环内定义、外部使用经退出 PHI 传递 |
| SCEV / recurrence | 标量演化／递推 | 循环值规律的抽象／跨迭代状态关系 |
| alias / dependence | 别名／依赖 | 访问位置是否可能重叠／执行顺序约束 |
| loop-carried dependence | 循环携带依赖 | 跨不同迭代的依赖 |
| versioning / fallback | 版本化／回退路径 | 为不同条件生成多种实现／条件不满足时的保守执行方案 |
| reduction / induction variable | 归约／诱导变量 | 聚合递推／按迭代规律变化的变量 |
| SLP | 超字级并行向量化 | 把局部同形标量指令组合成向量指令，与循环向量化不同入口 |
| lane / VF / IC | 向量通道／向量化因子／交错计数 | 元素位置／单组覆盖量／每轮的向量组数 |
| scalable vector / vscale | 可伸缩向量／vscale | 实际通道数由目标与运行时比例决定 |
| tail folding | 尾部折叠 | 用掩码覆盖向量化余数，与谓词化执行相关但不等同 |
| TTI | 目标变换接口 | 向变换提供目标能力与估价，不是精确耗时 |
| unrolling / peeling | 展开／剥离 | 复制多次迭代／单独处理特定迭代 |
| LICM | 循环不变代码移动 | 涉及外提、下沉及适用的内存提升 |
| interchange / distribution / fusion | 交换／分裂／融合 | 改变嵌套顺序／划分工作分区／合并循环；与图级融合不同层 |
| SIMD / ILP / thread parallelism | 数据级并行／指令级并行／线程级并行 | 不把向量化或展开等同于创建线程 |
| outline / runtime | 函数提取（outline）／运行时 | 将区域提成 worker／执行支持，不等于函数内联 |
| live range / live interval | 活跃范围／活跃区间 | 所需值的时间范围／实现表示可含多个段与空洞 |
| virtual / physical register | 虚拟／物理寄存器 | 机器 IR 值名／有限机器资源 |
| interference / register unit | 冲突／寄存器单元 | 不能共享的驻留需求／表达重叠物理资源 |
| spill / reload | 溢出到栈（spill）／重载 | 将值转入栈驻留／在使用附近取回 |
| splitting / eviction / recoloring | 切分／驱逐／重着色 | 拆开范围／撤销现有分配并重排／有限调整候选 |
| hint / spill weight / stage | 偏好提示／溢出权重／分配阶段 | 不同的决策依据，不是同一优先级度量 |
| caller-saved / callee-saved | 调用者保存／被调用者保存寄存器 | 保存责任依 ABI；使用成本还受调用与频率影响 |
| linear scan / greedy / PBQP | 线性扫描／贪心／分区布尔二次规划 | 不同分配组织与模型，均需考虑机器约束 |
| rematerialization（寄存器分配） | 重物化 | 在语义允许时重新计算值而非从栈取回；与反向传播中的“重算”同词不同义 |
