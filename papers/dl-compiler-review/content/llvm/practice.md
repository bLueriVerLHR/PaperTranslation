## 优化诊断与对照实验 {#practice}

### 三类循环的变换条件

以下三个函数分别包含独立元素计算、循环携带递推和浮点归约，可以用于比较不同依赖对优化的影响。实验需使用同一套构建或安装的 Clang、opt、llc 及相应 OpenMP runtime；复现固定提交的实现时，工具版本也应匹配。示例和命令是验证方案，并非本书已测得的编译结果。实验输出保存到独立的临时目录，与源码检出目录分开。

```c
// demo.c
void axpy(float *restrict y, const float *restrict x,
          float a, int n) {
    for (int i = 0; i < n; ++i)
        y[i] = a * x[i] + y[i];
}

void recurrence(float *a, const float *b, int n) {
    for (int i = 1; i < n; ++i)
        a[i] = a[i - 1] + b[i];
}

float sum(const float *a, int n) {
    float s = 0;
    for (int i = 0; i < n; ++i)
        s += a[i];
    return s;
}
```

`axpy` 的元素计算彼此独立，`recurrence` 包含距离 1 的跨迭代递推，`sum` 则形成浮点归约。它们的优化条件不同：递推约束数据的执行顺序，浮点有序归约还受目标能力与变换策略影响，未生成向量代码并不对应同一种原因。

### 从优化诊断到 IR 与汇编

```powershell
# 指定与分析版本匹配的 LLVM 工具目录。
$LlvmBin = 'C:\path\to\matching-llvm\bin'
$Clang = Join-Path $LlvmBin 'clang.exe'
$Opt = Join-Path $LlvmBin 'opt.exe'
$Llc = Join-Path $LlvmBin 'llc.exe'
$Exp = Join-Path ([IO.Path]::GetTempPath()) 'llvm-optimization-demo'
New-Item -ItemType Directory -Force $Exp | Out-Null
# 将示例保存为 $Exp\demo.c 后再运行：
& $Clang --version
& $Clang -O3 -S -emit-llvm "$Exp\demo.c" -o "$Exp\demo-o3.ll" `
    -Rpass=loop-vectorize -Rpass-missed=loop-vectorize `
    -Rpass-analysis=loop-vectorize
& $Clang -O3 -S "$Exp\demo.c" -o "$Exp\demo-o3.s"

# 显式指定可比较的目标，例如 x86-64；按本机工具支持修改。
& $Clang -O3 -march=x86-64 -S -emit-llvm "$Exp\demo.c" `
    -o "$Exp\demo-x86.ll"
```

Windows 环境的汇编格式、target triple 和 ABI 与 Linux 示例可能不同。`-march=native` 可展示本机特化，但不便于跨机器比较，也不应把其结果声称为 portable baseline。

IR 观察对象包括向量类型、vector.body、remainder、alias guard、reduction intrinsics 与 loop metadata。机器码则需要核对实际 SIMD 指令宽度、shuffle、循环分支、栈存取及 ABI 保存恢复。

基本块名称只是定位线索，可能随管线变化；判断变换结果还需要核对控制流结构与指令语义。

### 最小 Pass 管线与默认管线的区别

```powershell
# O0 常有 optnone；禁掉它，让后续 opt 可以优化。
& $Clang -O0 -Xclang -disable-O0-optnone -S -emit-llvm `
    "$Exp\demo.c" -o "$Exp\raw.ll"
& $Opt -S -passes='mem2reg,loop-simplify,lcssa,loop-vectorize' `
    "$Exp\raw.ll" -o "$Exp\lv-only.ll"
& $Opt -S -passes='mem2reg,loop-simplify,lcssa,loop-unroll' `
    "$Exp\raw.ll" -o "$Exp\unroll-only.ll"
& $Opt -S -passes='default<O3>' "$Exp\raw.ll" `
    -o "$Exp\default-o3.ll"
```

这些是教学用最小管线；实际某个 Pass 可能还需要 canonical induction、常量化、TTI 属性等辅助准备。运行合法不意味着与 Clang `-O3` 等价，后者还涉及前端 flags、目标属性和完整管线配置。

用 `-debug-pass-manager` 可以观察新 PM 执行过程。开发构建可使用相关 `-debug-only` 标签，但 release build 不保证保留调试输出。Pass 名称与选项可能随提交变化；验证时需要核对匹配工具支持的参数，不能将旧版本的内部选项直接视为当前接口。

### 别名、展开与向量宽度的因果对照

#### 对照 A：别名证据

去掉 axpy 的 restrict，检查是否出现 runtime pointer checks 或失去向量化。再测试实际不重叠、短循环、长循环三种输入。

区分 guard 摊薄与其他收益来源，需要记录优化诊断、IR 分支结构和测量输入。restrict 版本的测试输入必须满足其别名约束，否则产生的未定义行为会使正确性和性能对照失去意义。

#### 对照 B：展开因子与归约链

用 `#pragma clang loop unroll_count(4)` 与禁用展开等构造观察变化。pragma 仍需合法且实现支持，不保证所有要求都无条件完成。

比较单累加器与多个累加器；浮点多累加器会改变舍入顺序，只有在应用允许时才是等价对照。看控制减少之外是否实际缩短依赖链，是否出现更高寄存器压力。

#### 对照 C：向量宽度与 IC

控制目标能力和 loop hints，观察 wider SIMD 是否带来更多 shuffle、掩码和 spill。`-ffast-math` 同时改变多项浮点语义，不适合用作仅比较向量宽度的单一变量。

### 比较 LLVM 的多种分配器

分配器对照使用相同且适合目标的输入 IR，并在一致的优化 codegen 等级下改变 llc allocator。Fast 的局部处理与 Greedy 的前置流程可能不同，这些管线差异也需要记录，不能把所有差异归因于单个分配启发式。

```powershell
& $Llc -O2 -regalloc=greedy "$Exp\demo-x86.ll" -o "$Exp\greedy.s"
& $Llc -O2 -regalloc=basic  "$Exp\demo-x86.ll" -o "$Exp\basic.s"
& $Llc -O2 -regalloc=pbqp   "$Exp\demo-x86.ll" -o "$Exp\pbqp.s"
& $Llc -O2 -regalloc=fast   "$Exp\demo-x86.ll" -o "$Exp\fast.s"

# 在匹配并支持该 pass 的构建上，保存分配前后 MIR。
& $Llc -O2 -stop-before=greedy "$Exp\demo-x86.ll" `
    -o "$Exp\before-ra.mir"
& $Llc -O2 -stop-after=greedy "$Exp\demo-x86.ll" `
    -o "$Exp\after-ra.mir"
```

目标覆盖、pass 注册和 allocator 支持会影响这些命令；若工具拒绝，应以错误信息与该构建的管线为准。`-stop-after=greedy` 并非整个后端的结束位置，虚拟 operand 可能尚未全部改写；该快照用于分析分配状态，不能直接等同于最终汇编。

对比指标：

- 被切出的新虚拟范围与 COPY。
- 新栈槽、store/reload、可折叠访存和 rematerialization。
- 热循环内动态发生的 spill，不只统计整个函数静态条数。
- 额外 callee-saved 保存恢复。
- 编译耗时、最终代码大小、执行时间。

仅看到 `[rsp+...]` 不能证明它一定是 allocator spill：也可能是 ABI 参数、显式局部对象或其他栈访问。应与 MIR stack objects 和新指令对应。

### OpenMP 实验要分清 SIMD 与线程

```c
void parallel_axpy(float *restrict y, const float *restrict x,
                   float a, int n) {
#pragma omp parallel for simd schedule(static)
    for (int i = 0; i < n; ++i)
        y[i] = a * x[i] + y[i];
}
```

```powershell
# 只看 IR 可以先不链接可执行程序。
& $Clang -O3 -fopenmp -S -emit-llvm "$Exp\omp-demo.c" `
    -o "$Exp\omp-demo.ll"
# 只有 simd 需求时，可研究 -fopenmp-simd 对应的构造和 IR。
```

观察 outlined worker、`__kmpc_*`、范围计算和 worker 内 SIMD。完整可执行程序需要环境具备合适 OpenMP runtime，不能把缺少 libomp 的链接失败理解成并行分析失败。

性能实验需要控制线程数、输入规模、预热、结果消费以防 DCE、运行重复、亲和性/NUMA 和同机后台负载，并分别报告短循环与长循环。对受带宽限制的 kernel，线程扩展曲线可能趋平；解释这一现象需要结合访存与同步成本，不能直接归因于调度器错误。

### 从回归测试定位变换条件

LLVM 的回归测试提供了具体输入、运行配置与预期结构。IR 测试中的 CHECK 验证生成结果，MIR 测试则表达固定寄存器与压力等约束。它们可以与实现相互对照，帮助区分支持条件与算法限制。

| 主题 | 本地入口 |
|---|---|
| 循环向量化 | `llvm-project/llvm/test/Transforms/LoopVectorize/` |
| SLP | `llvm-project/llvm/test/Transforms/SLPVectorizer/` |
| 展开 | `llvm-project/llvm/test/Transforms/LoopUnroll/` |
| 交换 | `llvm-project/llvm/test/Transforms/LoopInterchange/` |
| 分裂 | `llvm-project/llvm/test/Transforms/LoopDistribute/` |
| OpenMP 优化 | `llvm-project/llvm/test/Transforms/OpenMP/` |
| Clang OpenMP 降级 | `llvm-project/clang/test/OpenMP/` |
| MLIR 仿射变换 | `llvm-project/mlir/test/Dialect/Affine/` |
| Greedy 基础案例 | `llvm-project/llvm/test/CodeGen/X86/` 内搜索 greedy、spill、split、recolor |

测试的 RUN 行规定 target 与 Pass 配置，输入提供具体依赖或活跃区间，CHECK 则限定预期生成结构。三者需要一起分析，才能确认测试覆盖的条件；单个用例通过不证明整个功能普遍受支持。

### 源码阅读中的表示与证据

沿[编译流程](#compilation-pipeline)追踪同一个函数，可以对照 AST、内存形式 IR、SSA 和循环 CFG 的变化。[SSA 与基础优化](#ssa-basics)中的 alloca 提升、PHI 插入、常量传播和死代码删除，解释了循环状态为何更适合后续分析；内联与尾递归消除则会进一步改变 CFG。

分析循环变换时，应先确定依赖和语言语义，再进入成本选择。保序展开可以保留跨迭代依赖，但这不等于同一循环能直接 SIMD 化或分配到多个线程。restrict 提供部分别名证据，递推、调用、浮点语义和循环形状仍可能限制向量化。沿 processLoop、legality、VPlan 到生成阶段追踪，能把这些条件对应到运行时检查、快路径、fallback 与尾部处理。

结构变换和并行生成涉及另一组证据：interchange 需要分析依赖方向；OpenMP pragma 经前端降级后具有运行时调用和并行语义；OpenMPOpt 主要优化这种已有语义。Polly 与 MLIR 的特定路线则在不同表示层次进行并行检测和生成，不能与普通循环管线混为一体。

寄存器分配需要继续追踪变换后的活跃范围。Greedy 的 enqueue/getPriority、selectOrSplitImpl、eviction advisor、SplitKit 和 SpillPlacement 分别参与排序、候选选择、驱逐和切分。队列优先级并不等同于 spill weight；stage、global/local 属性、size、hints 和寄存器类优先级共同影响顺序。其工作队列支持重新入队与区域切分，不按活跃区间起点单调推进；线性顺序策略只用于部分局部范围。

### 从生成结构解释实际性能

运行时 guard、尾部处理和线程启动具有固定成本，短循环可能难以摊薄，较长循环又可能改变工作集的缓存行为。比较输入规模时，需要同时观察路径选择和缓存条件，才能解释加速曲线的变化。

生成向量循环也不直接保证吞吐提升。目标降低后的指令、shuffle、mask、spill、访存带宽和输入规模都可能主导执行时间。类似地，SpillPlacement 的能量不增与收敛性质不意味着证明了全局最优；局部选择的效果仍需放回完整分配和生成代码中评价。

### 优化结果的完整因果链

```text
程序语义与依赖
  → 限制哪些重排合法
SSA promotion / 内联 / 常量传播 / 死代码删除 / TRE
  → 去掉多余边界，把计算和循环状态显式化
规范化 / SCEV / AA / MemorySSA
  → 给出可使用的证明
结构变换
  → 暴露连续访问、独立工作、常量与归约
LV / SLP / 展开 / 特定并行路线
  → 选择数据级、指令级或线程级方案
目标降低与调度
  → 决定实际指令和活跃峰值
Greedy / Fast / Basic / PBQP
  → 把虚拟资源需求放进有限寄存器，必要时切分或访存
运行时与硬件
  → 决定真实吞吐、带宽、同步和延迟
```

这条链表明，中端证明、目标成本和后端资源分配共同约束优化结果。并行性只是可利用的机会之一；安排计算顺序、减少数据访问和控制活跃峰值同样影响最终执行成本。

### 进一步阅读：本地文档与理论文献

本地文档适合与源码对照，不代替具体提交实现：

- `llvm-project/llvm/docs/Vectorizers.md`：LV 与 SLP 概览。
- `llvm-project/llvm/docs/TransformMetadata.md`：循环 hints、follow-up 与变换 metadata。
- `llvm-project/llvm/docs/LangRef.md`：浮点标志、内存、向量与 IR 精确语义。
- `llvm-project/llvm/docs/CodeGenerator.md`：后端分层。
- `llvm-project/clang/docs/OpenMPSupport.md`：OpenMP 支持状态。

理论阅读建议：Allen 与 Kennedy 的《Optimizing Compilers for Modern Architectures》帮助系统学习依赖与循环变换；Poletto 与 Sarkar（1999）的 Linear Scan Register Allocation 解释经典扫描；Larsen 与 Amarasinghe（2000）的 SLP 工作解释局部指令打包；PBQP 文献见 RegAllocPBQP.cpp 文件头。

理论文献给出算法模型，具体提交则包含工程策略和实现条件。对照阅读时，需要区分模型假设与实际控制流，尤其关注保守近似、目标成本以及版本相关的实现选择。
