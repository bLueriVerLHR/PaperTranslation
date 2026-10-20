## 自动并行化与 OpenMP {#parallel-openmp}

### 默认优化管线与线程化的职责边界

普通 LLVM 循环向量化、SLP、展开的职责不是通用线程级自动并行化。默认 C/C++ 优化管线不会仅因为看到独立循环，就普遍插入一组 OpenMP fork/join。

线程化还要考虑：运行时依赖、线程数、粒度、同步、嵌套并行、可观察副作用和内存模型。原先按确定顺序发生的调用、异常、I/O、volatile 或同步操作，不能在没有语义依据时重新分发给多个线程。

即使每个迭代独立，T 个线程的教学时间模型也有“启动＋调度＋串行部分＋并行部分/T＋同步＋内存争用”。当单次循环很短，启动和同步成本可能抵消并行执行的收益。

**SIMD 的收益门槛通常低于线程启动门槛；SIMD 合法性也不总是等价于任意线程调度合法性。** 有限距离依赖可能支持受限 VF，却不支持把所有迭代任意分发。

### Polly：用多面体统一表示迭代域和调度

对于规则嵌套：

```c
for (int i = 0; i < m; ++i)
    for (int j = 0; j < n; ++j)
        a[i][j] = b[i][j] + 1;
```

多面体模型把：

- **迭代域** 表示成整数点集合，例如 `0 <= i < m, 0 <= j < n`。
- **访问关系** 表示成迭代点到数组位置的映射。
- **依赖关系** 表示成必须保序的迭代点对。
- **schedule** 表示成迭代点到执行时间戳的映射。

传统 loop interchange 是交换时间戳维度；tiling 引入块坐标和块内坐标；fusion/distribution 调整不同语句的调度关系。合法性核心是每条依赖边在新 schedule 下仍指向未来。若某个调度维度没有携带依赖，就有并行化机会。

它不是只能表示 `a*i+b*j` 这种单一表达：实践有整数集、参数、分段关系和部分非仿射处理；但规则、可分析区域仍是强项。一般指针链、未知副作用或复杂非仿射结构会限制 SCoP 检测与优化。

源码阅读链：

1. `llvm-project/polly/lib/Analysis/ScopDetection.cpp`：哪些区域可建模。
2. `llvm-project/polly/lib/Analysis/ScopInfo.cpp`：域、访问与语句模型。
3. `llvm-project/polly/lib/Analysis/DependenceInfo.cpp`：构建依赖。
4. `llvm-project/polly/lib/Transform/ScheduleOptimizer.cpp`：修改调度。
5. `llvm-project/polly/lib/CodeGen/IslAst.cpp`：AST 与并行标记。
6. `llvm-project/polly/lib/CodeGen/IslNodeBuilder.cpp`：生成 IR，遇到并行节点转入并行循环生成。
7. `llvm-project/polly/lib/CodeGen/LoopGenerators.cpp`：标量/并行 loop 框架。

Polly 是独立可选组件，不等于普通 LLVM `-O3` 默认为任意程序开启的线程化功能。

### Polly 的并行检测与执行策略

本提交 `IslAstInfo::isParallel` 与 `isExecutedInParallel` 是两件事。后者在 `IslAst.cpp:626` 附近先检查 `PollyParallel`；除非 force，否则不把最内层循环线程化，注释理由是内层迭代常较少、不划算；还要求适用的外层并行标记，并排除这里的 reduction-parallel 情形。

这说明：

> 依赖分析的“可并行”是事实；代码生成的“实际线程化”是策略。

`LoopGenerators.cpp` 中可以看到线程数、调度策略、chunk size 设置和 `ParallelLoopGenerator::createParallelLoop`。继续追具体运行时后端，应读 `llvm-project/polly/lib/CodeGen/LoopGeneratorsKMP.cpp` 与 `llvm-project/polly/lib/CodeGen/LoopGeneratorsGOMP.cpp`。

某处 force 选项也不应被理解为通用地“无视依赖强行线程化”；这里描述的是策略门槛，是否合法仍是前置事实。

### MLIR AffineParallelize：在更高层 IR 保留结构

`llvm-project/mlir/lib/Dialect/Affine/Transforms/AffineParallelize.cpp` 将候选分析与并行 IR 改写分开组织：

```text
按 pre-order 访问 affine.for（先外层）
  → isLoopParallel：判断独立性，按选项识别 reductions
  → 收集候选
  → 计算父级 affine.parallel 数量
  → 不超过 maxNested 时 affineParallelize
  → 得到 affine.parallel
```

分析入口位于 `llvm-project/mlir/lib/Dialect/Affine/Analysis/LoopAnalysis.cpp`。仿射循环与访存信息尚未被低层指令淹没，适合直接进行域和依赖推理。

**得到 affine.parallel 不等于操作系统线程已经启动。** 它表达并行语义；后续要选择 lowering 到 SCF/OpenMP/其他执行模型并链接适当运行时。OpenMP 转换的一条相关路径是 `llvm-project/mlir/lib/Conversion/SCFToOpenMP/SCFToOpenMP.cpp`，但具体 pipeline 还需要先把对应 affine 结构降低到合适形式。

这是高层 IR 的价值：先决定“哪些工作可并行”，后决定“在哪种硬件和运行时执行”。

### OpenMP：程序员提供语义，编译器负责实现

```c
#pragma omp parallel for schedule(static)
for (int i = 0; i < n; ++i)
    y[i] = f(x[i]);
```

这里程序员承担符合 OpenMP 规则、无非法数据竞争的责任；编译器不需要重新证明整段普通 C 循环在任意线程下无竞争，但仍需检查 directive、canonical loop、数据环境等语言要求，并按规范生成实现。

典型 CPU 路线：

```text
#pragma omp parallel for
  ↓ Clang Sema：检查规范、循环和 shared/private/reduction
  ↓ CodeGen：outline 出 worker（microtask）
  ↓ 生成 runtime fork 调用，传捕获的参数
  ↓ worker 从运行时得到线程负责的迭代范围
  ↓ 执行本线程 loop；按构造语义同步和归约
```

关键源码：

- `llvm-project/clang/lib/Sema/SemaOpenMP.cpp`：前端语义。
- `llvm-project/clang/lib/CodeGen/CGStmtOpenMP.cpp`：`EmitOMPParallelDirective`、`EmitOMPParallelForDirective`、`EmitOMPWorksharingLoop`、`EmitOMPSimdDirective`。
- `llvm-project/clang/lib/CodeGen/CGOpenMPRuntime.cpp`：`emitParallelCall`、`emitForStaticInit`、`emitForDispatchInit`、`emitReduction`。
- `llvm-project/llvm/lib/Frontend/OpenMP/OMPIRBuilder.cpp`：构造 OpenMP IR 的共享基础设施；不同构造和配置使用的路径不完全相同。

`emitParallelCall` 构造 `__kmpc_fork_call(loc, n, microtask, ...)` 调用，把 outlined 函数与捕获参数交给运行时。捕获数组指针不意味着复制整个数组；传递与私有化方式取决于数据环境。

### runtime 真正做了哪些事

主要 CPU 运行时在 `llvm-project/openmp/runtime/src/`：

| 文件 | 阅读焦点 |
|---|---|
| `llvm-project/openmp/runtime/src/kmp_csupport.cpp` | `__kmpc_fork_call` 等编译器 ABI 入口 |
| `llvm-project/openmp/runtime/src/kmp_runtime.cpp` | team、线程生命周期、fork/join 框架 |
| `llvm-project/openmp/runtime/src/kmp_sched.cpp` | static 循环范围计算 |
| `llvm-project/openmp/runtime/src/kmp_dispatch.cpp` | dynamic/guided 等 work dispatch |
| `llvm-project/openmp/runtime/src/kmp_barrier.cpp` | barrier 与相关同步 |
| `llvm-project/openmp/runtime/src/kmp_tasking.cpp` | task 执行与调度 |

运行时会管理线程团队并复用资源，因此一个 parallel region 不必每次从零创建全部 OS 线程。不过，唤醒、调度和同步仍有成本。

- **static：** 预先划分迭代，调度开销低；工作均匀时合适。
- **dynamic：** 工作线程不断领取 chunk，应对负载不均，但有更多调度/同步。
- **guided：** 常用递减 chunk 在前期低开销和后期平衡之间取折中。

chunk 过小会增加调度和可能的 false sharing。两个线程写不同元素也可能写同一 cache line，导致一致性流量；“没有数据竞争”不等于“没有共享代价”。

### parallel、for、simd 与组合构造

| 构造 | 含义 |
|---|---|
| `omp parallel` | 建立并行 team，多个线程执行区域 |
| `omp for` | 把迭代分配给既有 team，不单独等价于创建 team |
| `omp simd` | SIMD 语义与相关承诺，不创建 CPU team |
| `omp parallel for` | 创建 team 并分配循环 |
| `omp parallel for simd` | 线程间分工，每个线程内再 SIMD |
| `omp task` | 建立任务，调度不等于固定迭代静态分片 |
| `omp target` | offload 执行模型，还涉及设备与映射 |

`simd` 也不保证最终一定是一条宽 SIMD 指令：目标支持、构造语义和实现限制仍影响 codegen。相反，明确的并行语义可能给优化提供原本难以从普通源码推导的事实。

归约例子：

```c
float sum = 0;
#pragma omp parallel for reduction(+:sum)
for (int i = 0; i < n; ++i)
    sum += x[i];
```

线程持有私有部分结果，结束时组合。相比把共享 sum 每轮 atomic，通常减少同步。浮点最终结果可随组合顺序和线程数变化；应用是否接受，需要用户设计，而不是默认把串行 bitwise 一致性当作保证。

### OpenMPOpt 对已有并行语义的优化

路径：`llvm-project/llvm/lib/Transforms/IPO/OpenMPOpt.cpp`。

本提交 `OpenMPOpt::run` 的可见结构包括：运行 Attributor、重新收集运行时调用使用、删除适用的并行区、去重 runtime 查询，以及在开关允许时合并 parallel regions。module 路径还有设备状态机改写与 SPMD wrapper 等设备相关处理。

前端为满足并行构造的不同情况，可能生成较保守的运行时调用框架。中端结合 runtime 函数和 worker 的语义，能够证明部分调用、区域或同步安排可以进一步简化。

- 相同、可合法共用的运行时查询可能去重。
- 可证明无相关效果的区域可能移除。
- 邻近区域若满足同步、数据环境等条件，可减少 fork/join；合并不能破坏原 barrier 所建立的顺序。
- Attributor 通过跨函数推导属性与行为提供证明；不是猜测 worker 没副作用。

OpenMPOpt 以已有 OpenMP 语义为输入，与 Polly、MLIR 中检测并行机会并生成相应表示的路线承担不同职责。

### 线程化的语义条件与资源约束

线程化首先需要明确 private/shared 数据环境及别名关系，分析跨迭代 RAW、WAR、WAW 和归约。副作用、异常、I/O、同步以及原执行顺序决定哪些调度保持语义；独立的变量名并不能替代独立的存储对象证明。

合法性成立后，还要评价粒度和资源。每个线程的工作量需要足以摊薄启动与同步，false sharing 可能增加缓存一致性开销，访存带宽也可能限制扩展。外部线程池、嵌套 parallel、亲和性和 NUMA 则影响实际调度与数据位置。这些条件共同决定线程化是否适用，而非仅由循环语法决定。
