## SSA 与基础优化 {#ssa-basics}

前端生成合法 IR 后，中端通过 SSA 和基础优化显式化值的定义、使用及控制关系。本章承接[编译流程](#compilation-pipeline)，分析这些表示如何支持传播、删除和控制流变换，并为[循环分析](#loop-foundations)及后续寄存器分配提供基础。

这些优化与 SSA 的关系并不相同：mem2reg 构造标量 SSA，常量传播和死代码删除利用已有的 def-use 关系，内联与尾递归消除则改变函数或控制流并维护 SSA。区分这些职责，有助于追踪每个变换的输入和结果。

### 定义命名与控制流合并

```c
int choose(bool cond, int x) {
    int y;
    if (cond) y = x + 1;
    else      y = x + 2;
    return y * 3;
}
```

SSA 的教学表示：

```llvm
define i32 @choose(i1 %cond, i32 %x) {
entry:
  br i1 %cond, label %then, label %else
then:
  %y.then = add i32 %x, 1
  br label %join
else:
  %y.else = add i32 %x, 2
  br label %join
join:
  %y = phi i32 [ %y.then, %then ], [ %y.else, %else ]
  %result = mul i32 %y, 3
  ret i32 %result
}
```

`%y.then`、`%y.else`、`%y` 是三个不同定义。PHI 表示从哪个前驱进入 join，就取该边所携带的值，不是两条路径都执行，也不是先计算两边再挑一个。

普通指令的定义应支配使用；PHI 的 incoming use 则按对应前驱边处理，这让两个分支定义能在 join 合流。只有真的存在不同来源、且结果需要在汇合后使用，才需要保留非平凡 PHI。

**SSA 的核心收益：** 一个值的使用列表直接指向同一定义；替换这个定义的所有使用，就能沿 def-use 链传播结果。不必每次都问“同名变量在到达这里之前最后被谁赋值”。但内存仍可能被任意别名写入，普通 load 不能仅靠寄存器 SSA 获得相同保证。

### mem2reg：消除不必要的内存身份

#### 从 alloca/load/store 到值

前端为了表达可修改局部变量，尤其非优化生成阶段，常产生：

```llvm
entry:
  %slot = alloca i32
  br i1 %cond, label %then, label %else
then:
  store i32 1, ptr %slot
  br label %join
else:
  store i32 2, ptr %slot
  br label %join
join:
  %v = load i32, ptr %slot
  ret i32 %v
```

若 `%slot` 的地址身份没有被程序观察，内存对象只承担“保存当前标量值”的职责，可以变为：

```llvm
join:
  %v = phi i32 [ 1, %then ], [ 2, %else ]
  ret i32 %v
```

这里的 reg 是 **SSA 虚拟值**，不是分配 RAX 或某个硬件寄存器。最终它也可能在后端被 spill。mem2reg 与[寄存器分配基础](#register-foundations)、[Greedy 寄存器分配](#greedy)中的 register allocator 是完全不同阶段。

#### 哪些对象允许提升

两个入口必须分开读：

- `llvm-project/llvm/lib/Transforms/Utils/Mem2Reg.cpp`：Pass 包装，`promoteMemoryToRegister` 扫描函数 entry 的 allocas，反复收集可提升者并调用 `PromoteMemToReg`。
- `llvm-project/llvm/lib/Transforms/Utils/PromoteMemoryToRegister.cpp`：`isAllocaPromotable`、SSA 构建、快路径和重命名的真正实现。

本提交的判断主要允许直接、非 volatile、类型一致的 load/store，以及规定范围内的 lifetime/droppable 等使用。以下三处因此不属于可直接提升的形式：

- `store ptr %slot, ptr %somewhere` 是存储地址本身，不是向 slot 存值；地址可能逃逸，不能这样提升。
- 把地址交给普通未知调用，不能当作“私有标量”忽略调用读写。
- 任意非零 GEP、聚合字段或数组索引，不属于 mem2reg 直接处理的一般模式。
- `volatile` 访问的可观察语义不能因局部对象而删除。
- **本提交并不一律拒绝 atomic load/store。** 对满足这种封闭局部 alloca 使用模式的对象，源码注释解释其原子性没有跨观察者意义；不能把这个结论推广到共享内存。
- alloca 声明的类型不必机械地等于实际访问类型；实现要求相关 load/store 访问类型一致，并按实际使用判断。

包装器在 entry 找候选，不意味着底层 API 的理论只适用于“第一块叫 entry”的形式。教学复现应以包装 Pass 的输入约束为准。

#### 理论：支配边界与 pruned SSA

若 block X 定义了变量，在一些分叉、汇合之后，哪个位置需要 PHI？支配边界 DF(X) 可理解为“X 支配某个到达这里的前驱，但不能严格支配这里”的汇合边界。多个定义的边界可能产生 PHI，而 PHI 自身又是新定义，因此需要 **iterated dominance frontier，IDF**。

但并不是在所有 IDF 点都插 PHI。若一个汇合后的值从不被读取，插入它毫无意义。LLVM 先计算 LiveInBlocks，再用其限制 IDF；这就是 **pruned SSA**：只在需要活跃值的位置合流。

本提交真实片段，位于 `PromoteMem2Reg::run`，省略上下文：

```cpp
ComputeLiveInBlocks(AI, Info, DefBlocks, LiveInBlocks);
IDF.setLiveInBlocks(LiveInBlocks);
IDF.setDefiningBlocks(DefBlocks);
SmallVector<BasicBlock *, 32> PHIBlocks;
IDF.calculate(PHIBlocks);
```

接着为相应块 `QueuePhiNode`，再由 `RenamePass` 遍历 CFG，维护当前 incoming value：遇到 store 更新当前值，遇到 load 以当前值替换，进入带 PHI 的块以 PHI 作为当前值，并填充 incoming edges。

理论教材常通过遍历支配树、为每个变量维护定义栈来解释重命名；本实现则使用工作列表、当前值与撤销状态维护遍历过程。二者表达同一类 SSA 构建问题，但数据结构与状态更新方式需要分别对照。

对于单次 store、同一 block 内所有使用等简单情形，`rewriteSingleStoreAlloca`、`promoteSingleBlockAlloca` 等快路径可以避免完整 SSA 构建。未初始化读取不能凭空变成 0：本实现以 `UndefValue` 等 IR 规则处理相关状态，源语言读取未初始化对象的规则还要另行遵守。

#### SROA 与 mem2reg 的关系

结构体、数组或按字段访问的对象，往往需要先把对象分割为更合适的小片段。`llvm-project/llvm/lib/Transforms/Scalar/SROA.cpp` 做 Scalar Replacement of Aggregates，处理切片并对合适部分进行 promotion；不是“直接对所有数组运行 mem2reg”。

默认优化管线常直接安排 SROA 及其提升能力，不一定显式列出一个独立 mem2reg。手工运行 `opt -passes=mem2reg` 可以隔离算法作用，但生产管线消除局部 load/store 的路径还包括 SROA 内部的提升。

### 常量折叠、简化与传播：三个相关但不同的问题

#### 常量折叠：已知输入，直接求值

```llvm
%a = add i32 2, 3
%b = mul i32 %a, 4
```

第一条可得到 5，替换其使用后第二条变成常量乘法，可得到 20。folding 是对已知 operands 的计算；“替换并继续传递”才是传播层面的动作。

主要路径：`llvm-project/llvm/lib/Analysis/ConstantFolding.cpp` 的 `ConstantFoldInstruction` 等入口，结合 `llvm-project/llvm/lib/IR/ConstantFold.cpp` 的常量层实现。

常量折叠必须遵守整数位宽、目标 DataLayout、浮点格式及具体 IR 语义。APInt/APFloat 等表示将这些条件与宿主机器的原生运算分开，避免把宿主环境的结果直接当成目标语义。

#### 指令简化：输入未知，也能利用恒等关系

例如整数 `%x + 0` 可简化为 `%x`，不需要知道 x 的具体数值。`llvm-project/llvm/lib/Analysis/InstructionSimplify.cpp` 提供简化查询；`llvm-project/llvm/lib/Transforms/InstCombine/InstructionCombining.cpp` 中的 InstCombine 工作列表可做更广泛的局部等价变换、规范化和持续清理。

区分两者：InstructionSimplify 的接口通常返回可替代的现有值/常量，不负责任意新建复杂指令序列；InstCombine 作为变换会构造与改写指令，并驱动后续处理。ConstantFolding 则专注常量求值。它们相互调用或协作，不是三套互不接触的编译器。

折叠能力分布在 IR 构造、InstCombine、SCCP 和克隆剪枝等环节，并非由一个统一的 `constprop` Pass 承担。分析某次常量化时，需要追踪实际执行的位置。

#### SCCP：同时推导“什么值”与“哪些边能走”

Sparse Conditional Constant Propagation 使用两个相互影响的事实：

1. 某个 SSA 值能否被确定为常量或限制在一个范围。
2. 哪些 CFG blocks/edges 可能执行。

经典教学 lattice 可以写成：

```text
尚无信息 → 常量 c → 不再能用单一常量表示
```

不同常量合流得到更不精确的状态。**这不是硬件值从未知变成常量；它是分析信息从少到多、逐渐发现更多可能性。** LLVM 当前的 `ValueLatticeElement` 更丰富，包含 unknown、undef、constant、notconstant、整数范围以及 overdefined；不能把三点格当作精确完整实现。

路径：`llvm-project/llvm/lib/Transforms/Scalar/SCCP.cpp`，求解器在 `llvm-project/llvm/lib/Transforms/Utils/SCCPSolver.cpp`，抽象状态在 `llvm-project/llvm/include/llvm/Analysis/ValueLattice.h`。

```llvm
entry:
  br i1 true, label %left, label %right
left:
  br label %join
right:
  br label %join
join:
  %v = phi i32 [ 7, %left ], [ 9, %right ]
  ret i32 %v
```

若简单地把 PHI 的所有 syntactic operands 合并，7 与 9 不同，会失去常量结论。SCCP 知道 right 边不可执行，只合并可执行 incoming edges，所以 `%v` 为 7。这正是 Conditional 的价值；Sparse 则意味着主要沿 SSA 使用链和可执行边传播，避免每轮反复扫描所有无关指令。

工作列表持续传播到固定点。相关事实变成常量后，可折叠条件、删除不可达结构；函数间版本 IPSCCP 进一步利用可追踪调用和返回，但受可见性与调用者信息限制，不能假定 externally callable 函数只收到当前分析位置出现的常量实参。

#### IR 语义的边界：数学相等未必足够

- 固定位宽整数有 wrap、`nsw` / `nuw` 等不同约束；违背 no-wrap 条件可能产生 poison。
- 浮点 `x + 0` 不应不加条件地等同于数学实数恒等式，NaN、符号零、异常环境与 flags 都影响判断。
- `undef`、`poison`、`freeze` 是 IR 概念，不等价于“一颗可随便设成任意整数的变量”。
- 未知且有副作用的普通函数调用不能仅凭结果似乎稳定而在编译时折叠。

本节是在解释证明边界，不是鼓励程序依赖未定义行为。精确语义应回到 `llvm-project/llvm/docs/LangRef.md`。

### 死代码删除：为什么“没人用结果”不是全部条件

#### DCE：从无用叶子反向剥离

```llvm
%a = add i32 %x, 1
%b = mul i32 %a, 2
ret i32 0
```

b 无使用且可安全删除；删掉 b 后，a 也失去最后使用。这种链式过程适合工作列表，不用每删一条就重扫整个函数。

`llvm-project/llvm/lib/Transforms/Scalar/DCE.cpp` 的 `DCEInstruction`：

```text
isInstructionTriviallyDead?
  → 保留可挽救的 debug info / knowledge
  → 解除 operands 的使用关系
  → 把因此变死的 operand instructions 加入 WorkList
  → 删除当前指令
```

死指令判定与相关公共实现可追 `llvm-project/llvm/lib/Transforms/Utils/Local.cpp`。

普通 store 没有 SSA 返回值，call 的返回值也可能没有使用者，但这些操作可能修改内存、执行 I/O、抛出异常或影响执行进展，不能仅凭 `use_empty` 删除。volatile/atomic 与同步语义也必须考虑。特定库调用或 intrinsic 在证明允许时有例外，判断应以精确语义为准。

#### ADCE：从有意义的根正向保留，而不是只等 use 归零

简单 DCE 容易漏掉内部互相使用、却整体没有可观察贡献的环。ADCE 乐观地把指令当 dead，从必须保留的效果、返回等根开始标 live，再沿数据依赖和控制依赖保留所需部分。

为什么控制依赖重要？若两个分支分别写入 1 和 2，决定走哪条的条件也是可观察效果所必需，不能删掉条件而随机选择其中一边。

路径：`llvm-project/llvm/lib/Transforms/Scalar/ADCE.cpp`，会使用 PostDominatorTree 和反向图上的依赖关系处理控制流。postdominate 可粗略理解为某块正常到达出口的路径都经过另一个块；具体算法还要正确处理无出口等情况。

“死循环里只有无用算术”并不自动等于可以让函数返回。终止性/进展语义也是可观察行为；本提交 ADCE 有默认关闭的 `adce-remove-loops` 选项处理 may-be-infinite 情况，其他 `mustprogress` 等事实和 Pass 也会影响能做的事。ADCE 的 optimistic dead 策略仍受终止性与进展语义约束，不允许任意改变无限循环。

#### DSE：内存写入的死活，另有一套证明

```c
*p = 1;
*p = 2;
```

若访问不是 volatile/需保留的原子操作，中间没有读取、异常或其他障碍，且第二次覆盖必然在需要的路径发生，第一次写可能死。它不是普通 use-empty DCE 的问题。

`llvm-project/llvm/lib/Transforms/Scalar/DeadStoreElimination.cpp` 文件头给出 MemorySSA-backed 方法：从较后的 MemoryDef 往上找可能被杀死的定义，再检查期间没有读取、没有阻碍、覆盖范围充分和执行条件成立。

若中间插入 `observe(p)`，必须知道该调用是否读 p；如果只覆盖半个对象，不能宣称整个旧 store 都死。**标量 SSA 解决的是值使用，MemorySSA＋别名分析帮助解决的是内存效果。**

#### SimplifyCFG 与不可达代码

不可达块、无意义跳转、常量分支、可合并块等，主要由 CFG 清理和其他变换配合处理。路径：`llvm-project/llvm/lib/Transforms/Scalar/SimplifyCFGPass.cpp`、`llvm-project/llvm/lib/Transforms/Utils/SimplifyCFG.cpp`。

因此“死代码清除”是一个家族：DCE、ADCE、DSE、unreachable/CFG cleanup、GlobalDCE 各有对象和证明，不是一个 Pass 包办。

### 函数内联：消除边界，比消除 call 更重要

#### 一个会暴露常量的调用点

```c
static int scale(int x, int mode) {
    if (mode == 0) return x * 2;
    return x * 3;
}
int caller(int x) {
    return scale(x, 0) + 1;
}
```

内联把 callee 的逻辑带进 caller，并以实参替换形参。第二个实参为 0，所以 mode 分支可折叠，最终可能只剩 `x*2+1` 的计算。

节省 call/ret 是一部分；更重要的是暴露：常量实参、对象身份与访问、可删除路径、嵌套调用目标、归约或循环体中的可优化表达式。后续 InstCombine、SROA、SCCP、DCE、LV 才能利用它们。

#### 内联决策与实际改写 {#设计依旧分策略与施工}

| 部分 | 本地路径 | 问题 |
|---|---|---|
| 调用图层驱动 | `llvm-project/llvm/lib/Transforms/IPO/Inliner.cpp` | 哪些 call sites、如何处理 SCC 和新增调用 |
| 推荐策略 | `llvm-project/llvm/lib/Analysis/InlineAdvisor.cpp` | 当前调用点是否建议内联、如何记录结果 |
| 成本估计 | `llvm-project/llvm/lib/Analysis/InlineCost.cpp` | 特化后成本、热度、体积和预算 |
| 实际改写 | `llvm-project/llvm/lib/Transforms/Utils/InlineFunction.cpp` | 克隆 callee、参数映射、返回汇合、异常与属性 |

本提交的 `InlinerPass::run` 使用 LazyCallGraph SCC；advisor 给出建议后，驱动层仍需调用 `InlineFunction` 并检查 `InlineResult`。策略建议不代替合法性判断，也不保证实际改写成功。

内联不是文本粘贴：调用点被拆成前后块，callee 基本块和指令被克隆、重新命名；形参映射实参；多个 return 跳到 continuation，并可能经 PHI 合并返回值。还要处理 byval、alloca、lifetime、invoke/异常路径、调试位置与不同函数属性约束。

#### 理论收益和代价

收益模型估计的是**这个调用点特化后的结果**，不是原函数源码行数。例如函数本体较大，但常量参数能剪掉绝大多数分支，仍可能值得；小函数位于大量冷调用点，也可能因为体积累计而不划算。

代价包含：I-cache、编译时间、caller 扩张、寄存器 live ranges、栈大小和递归展开风险。profile 可引导热调用更积极、冷调用更保守，但不是保证每个热 call 必内联。

SCC（strongly connected component）标识互相递归可达的调用组；无限把自己/互递归函数内联会指数或无限扩张。调用历史、预算、属性与策略限制必须阻止这种情况。函数声明的 C++ `inline` 也不是“一定消除所有调用”；它有语言层含义，编译器的推荐属性和 alwaysinline/noinline 又是另一层机制，仍受合法性规则约束。

间接调用需要先知道目标，或由去虚拟化/特化等形成可内联场景；只有外部声明而无可用 body，无法克隆不存在的实现。符号可替换性、链接语义、calling convention 等同样不能忽略。

**与后文连接：** 循环中的小辅助函数被内联后，LV 才看得到逐元素计算；但内联把更多值放到 caller，也可能让 Greedy 需要切分和 spill。不能仅凭 call 指令消失判断净收益。

### 尾递归换循环：把栈状态显式写成 PHI

#### 最干净的尾递归例子

```c
unsigned sum_down(unsigned n, unsigned acc) {
    if (n == 0) return acc;
    return sum_down(n - 1, acc + n);
}
```

这里自调用后只把结果返回，没有剩余的计算或析构。教学上的循环形式：

```c
unsigned sum_down_loop(unsigned n, unsigned acc) {
    while (n != 0) {
        acc += n;
        --n;
    }
    return acc;
}
```

在 IR 层，参数的当前值由 loop header PHI 表示：初始边输入函数实参，递归边输入“下一轮实参”。原来的 self-call 和对应 return 换为回边；base case 的 return 保留。

```llvm
define i32 @sum_down_loop(i32 %n0, i32 %acc0) {
entry:
  br label %loop
loop:
  %n = phi i32 [ %n0, %entry ], [ %n.next, %step ]
  %acc = phi i32 [ %acc0, %entry ], [ %acc.next, %step ]
  %done = icmp eq i32 %n, 0
  br i1 %done, label %exit, label %step
step:
  %acc.next = add i32 %acc, %n
  %n.next = sub i32 %n, 1
  br label %loop
exit:
  ret i32 %acc
}
```

这些是教学 IR，不宣称本机已经生成。前端还有 ABI、属性和局部对象信息；真实输出可能不同。

#### 源码与合法性边界

路径：`llvm-project/llvm/lib/Transforms/Scalar/TailRecursionElimination.cpp`，重点读：

- `canTRE`：本提交拒绝 dynamic allocas，因为迭代之间正确释放动态栈分配尚未在此实现。
- `AllocaDerivedValueTracker` 与 tail-call 标记逻辑：追踪指针是否派生于/逃逸自 caller 栈对象，避免下一轮破坏仍需存在的内存。
- `TailRecursionEliminator::findTRECandidate`：找当前函数的递归调用，并检查 tail-call 等条件。
- `TailRecursionEliminator::eliminateCall`：生成/更新回边、参数 PHI 和相关返回值处理。

递归语义中的“新栈帧”可能提供独立局部对象；不能在它们的地址仍被下一层使用时无条件复用同一个位置。C++ 析构、EH 清理、call 后 store 或其他效果，也可能使看起来在 return 表达式里的调用并不是真正可消除的尾位置。

尾递归消除需要维护参数状态、返回路径和对象生命周期，不只是替换函数末尾的调用。对没有额外对象约束的简单例子，递归链的调用开销与栈深可以消除；包含 allocas 的其他递归仍需逐项检查，不能据此承诺零额外栈增长。

#### 非尾递归的部分扩展：累加器

```c
unsigned fact(unsigned n) {
    if (n == 0) return 1;
    return n * fact(n - 1);
}
```

乘法在递归返回后执行，原形不是直接尾调用。但若运算与使用形状符合规则，可引入初始为 1 的 accumulator，把每次 n 乘进去，再回边。unsigned 模乘具有适用的结合、交换性质；带不同 no-wrap 或浮点语义时必须另查。

本提交 `canTransformAccumulatorRecursion` 检查关联/交换性或支持的特定 unary recurrence、identity、调用结果在 operand 中的使用方式，以及结果仅被相应 return 使用；`insertAccumulator` 创建状态 PHI。

这不意味着 LLVM 会自动把任意 Fibonacci 的两分支递归变成线性时间循环。某个尾分支被消除，不等于所有递归结构都被消除，更不等于做了动态规划。

#### TRE 与后端尾调用不是一件事

| 概念 | 典型结果 | 关键条件 |
|---|---|---|
| 自递归消除 TRE | 同一函数内的 loop/PHI | 自调用、可改写参数与状态、栈对象等安全 |
| sibling/tail call lowering | 跳转到另一函数，复用当前调用框架 | ABI、calling convention、参数传递、目标支持 |
| `musttail` | IR 强制尾调用约定 | 严格的 LangRef 约束，不是普通优化提示 |

TRE 属于中端结构变换，能让后续 LoopInfo、SCEV、LICM、展开等看到新循环；普通尾调用 lowering 则通常仍跨函数，不会因此在 caller 中形成一个可向量化 loop。

### 基础变换之间的因果关系

```text
前端 alloca / load / store
  → SROA / promotion：移除不必要内存身份，建立清晰值流
  → 内联：把调用点实参与 callee 计算放进同一推理空间
  → InstCombine / SCCP：常量与简化传播，识别不能走的路径
  → DCE / ADCE / DSE / SimplifyCFG：清掉没有贡献的计算与结构
  → TRE：把适合的递归状态转成显式 loop / PHI
  → 后续循环分析、结构变换、LV / SLP / unroll
  → 后端有限寄存器上的资源安排
```

这是解释依赖关系的图，不是声称 LLVM 默认严格按这一次序各运行一次。`llvm-project/llvm/lib/Passes/PassBuilderPipelines.cpp` 可见 SROA、InstCombine、SCCP、ADCE、SimplifyCFG 在不同阶段出现；TailCallElim 也在相应函数优化阶段安排。内联作为跨函数管线的一部分，会让后续函数级优化重新获得机会。

为什么需要多轮？内联暴露常量，常量传播删分支，删分支使 PHI 简化，PHI 简化让某个对象可提升，提升后又暴露 DCE 或循环规律。生产管线通过阶段化和固定预算获得大部分收益，而不是对所有 Pass 无限制跑到全局固定点。

### 一个小实验，把 SSA、控制流和消除连起来

下面的完整示例 IR 可保存为系统 TEMP 实验目录中的 `ssa-demo.ll`。示例不包含目标特定运算，用于观察局部状态提升和控制流清理。

```llvm
define i32 @ssa_demo() {
entry:
  %slot = alloca i32
  br i1 true, label %left, label %right
left:
  store i32 7, ptr %slot
  br label %join
right:
  store i32 9, ptr %slot
  br label %join
join:
  %v = load i32, ptr %slot
  %unused = mul i32 %v, 100
  %result = add i32 %v, 1
  ret i32 %result
}
```

沿用[优化诊断与对照实验](#practice)中的 `$Opt`、`$Exp`，可以用以下未实测的命令比较提升与清理结果：

```powershell
& $Opt -S -passes='mem2reg' "$Exp\ssa-demo.ll" `
    -o "$Exp\ssa-promoted.ll"
& $Opt -S -passes='mem2reg,sccp,dce,simplifycfg' "$Exp\ssa-demo.ll" `
    -o "$Exp\ssa-clean.ll"
```

第一步预期关注 slot 是否被消除、join 是否经 PHI 表示两条输入；第二步关注恒 true 路径使 `%v` 为 7、result 为 8、无用链与 right 路径被清理。各工具版本的清理分工和中间形状可能不同，不应把某个精确块名当正确性要求。

基础 Pass 的独立测试入口：

- `llvm-project/llvm/test/Transforms/Mem2Reg/`
- `llvm-project/llvm/test/Transforms/SROA/`
- `llvm-project/llvm/test/Transforms/InstCombine/`
- `llvm-project/llvm/test/Transforms/SCCP/`
- `llvm-project/llvm/test/Transforms/DCE/`
- `llvm-project/llvm/test/Transforms/ADCE/`
- `llvm-project/llvm/test/Transforms/DeadStoreElimination/`
- `llvm-project/llvm/test/Transforms/Inline/`
- `llvm-project/llvm/test/Transforms/TailCallElim/`

理论进一步阅读可从 Cytron 等（1991）的 SSA 构建与控制依赖工作、Wegman 与 Zadeck（1991）的条件常量传播工作出发。但当前实现的快路径、lattice、属性和内存语义要以本提交源码为准。

基础 Pass 移除多余的内存和函数边界，使值关系与控制结构更适合后续证明和成本估计。[循环优化的理论基础](#loop-foundations)进一步将这些信息抽象为循环、递推和依赖；高级优化的可用条件因此部分来自前置变换，而非单个算法独立获得。
