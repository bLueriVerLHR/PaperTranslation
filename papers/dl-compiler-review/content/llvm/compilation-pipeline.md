## 从 C/C++ 到优化 LLVM IR {#compilation-pipeline}

本章沿一个小 C 函数分析编译各阶段的程序表示：带语义的 AST、含局部内存的 LLVM IR、提升后的 SSA，以及适合循环分析和向量化的控制流。阶段之间的输入输出关系说明了分析事实从何而来，也为[SSA 与基础优化](#ssa-basics)中的算法提供背景。

### 前端生成、中端优化与后端降低

Clang 前端完成预处理、语法与语义分析、类型及 ABI 处理，再生成 LLVM IR。LLVM 中端通常在 IR 上执行优化，后端才将其降低为目标指令并分配寄存器。

mem2reg 接收的已经是合法 LLVM IR，其作用是把符合条件的局部内存状态提升为 SSA 值。它不承担 C 源码解析或 AST 到 IR 的生成工作。

生产管线按优化级别、目标、LTO、profile、语言功能和插件配置组装。某些步骤会重复运行，某些管线不显式安排 mem2reg，部分循环也可能在向量化前已被完整展开或删除。因此，编译过程需要按实际输入和执行路径分析，而非理解为若干 Pass 各运行一次的固定序列。

### 编译任务与阶段产物 {#一张带产物的流程图}

```text
编译命令：clang -O2 example.c -o example.exe
│
├─ Driver：解析选项，选择目标、工具链和编译/链接任务
│   产物：内部 compilation actions / jobs，而非 LLVM IR
│
├─ Clang 前端任务（常称 cc1）
│   ├─ 预处理 + 词法：include、宏、条件编译、token
│   ├─ Parser + Sema：语法结构、类型、名字查找、隐式转换等
│   │   产物：带类型与语义的 AST
│   └─ AST CodeGen：函数 ABI、表达式、变量、控制流、清理路径
│       产物：LLVM Module，内部有 Function / BasicBlock / Instruction
│       此时可能有 alloca/load/store，但已经是合法 IR
│
├─ LLVM 中端优化管线
│   ├─ 模块/调用图整理、属性推导、内联等
│   ├─ SROA / promotion、表达式与 CFG 清理等（可能多轮）
│   ├─ 循环识别、规范化、分析与前期结构优化
│   └─ 合适阶段执行完整展开、LV、一般展开、SLP 等
│       产物：优化 LLVM IR；不同循环走不同路线
│
├─ LLVM 后端（若没有选择停在 IR）
│   ├─ 目标合法化与指令选择
│   ├─ Machine IR 优化、调度、寄存器分配
│   └─ 栈帧、后端整理、机器码/汇编输出
│       产物：.s 或含机器码和重定位的 .o/.obj
│
└─ 链接器：合并目标文件/库、解析符号与重定位
    产物：可执行文件或共享库
```

这张图表示职责边界，不表示每步必然启动独立进程或先写一个中间文件。Clang 常把预处理、解析、IR 生成和后端放在同一编译任务中；一些顶层声明还会在解析过程中交给 ASTConsumer 逐步处理，未必先把完整 AST 写盘再读回。

`.ll` 是 LLVM IR 的文本序列化，`.bc` 是 bitcode。正常编译并不需要在磁盘上出现它们。中端 Pass 通常修改内存中的 IR 对象，不是用字符串替换 `.ll` 文件。

### Driver 的任务构建与 cc1 前端入口

运行 `clang` 或 `clang++` 时，首先进入 driver。它根据 `-E`、`-S`、`-c`、`-emit-llvm`、目标、输入语言等决定建哪些任务，也选择 include 搜索、sysroot、运行库和链接器配置。

源码路径：

- `llvm-project/clang/lib/Driver/Driver.cpp`：`Driver::BuildCompilation`、`BuildActions`、`BuildJobs`。
- `llvm-project/clang/lib/Driver/ToolChains/Clang.cpp`：`Clang::ConstructJob`，为编译任务构造参数。
- `llvm-project/clang/lib/FrontendTool/ExecuteCompilerInvocation.cpp`：`CreateFrontendAction`、`ExecuteCompilerInvocation`。
- `llvm-project/clang/lib/Frontend/CompilerInstance.cpp`：承载 diagnostics、目标、预处理器、ASTContext、Sema，并执行 FrontendAction。

cc1 主要指 Clang 的内部前端入口或任务模式，是否作为独立进程执行受 driver 配置影响。Driver 同时配置工具链、系统头文件与 ABI 相关参数；直接调用 `clang -cc1` 时，这些设置需要单独处理，因此它与普通编译命令的条件并不相同。

同一个 C 文件针对 Windows x64 与 Linux x86-64，可能有不同 ABI、目标 triple、DataLayout 和属性，即使都叫 x86-64。**LLVM IR 也不是完全与目标无关的通用源码。** 目标无关优化很多，但前端已经选择了类型布局、参数传递和若干目标事实。

### 预处理与词法：此时尚未出现 LLVM 指令

```c
#define STEP 1
#include "config.h"
#if ENABLE_KERNEL
void f(void) { /* ... */ }
#endif
```

预处理决定哪些 token 真正进入编译：展开宏、处理 include、选择条件分支，并保留源位置用于诊断。词法把字符变成标识符、数字、运算符等 tokens。

路径：`llvm-project/clang/lib/Lex/Lexer.cpp`、`llvm-project/clang/lib/Lex/Preprocessor.cpp`、`llvm-project/clang/lib/Lex/PPMacroExpansion.cpp`。

宏展开和 `#if` 条件选择发生在类型检查之前，分别不同于 LLVM 的函数内联和 SCCP。头文件在预处理及后续语义处理中提供声明或定义；包含头文件与链接阶段加载库是不同操作。

### Parser 与 Sema：从语法树到具有 C/C++ 意义的程序

Parser 解析 `for`、函数声明、表达式与语句的语法结构；Sema 处理名字查找、类型检查、重载决议、隐式转换及模板相关语义。两者在解析过程中协作，语义处理并不是在整棵无类型语法树构造完毕后才统一开始。

路径：

- `llvm-project/clang/lib/Parse/ParseAST.cpp`：`ParseAST`，循环调用 `ParseTopLevelDecl`，并通知 ASTConsumer。
- `llvm-project/clang/lib/Parse/ParseStmt.cpp`：语句解析。
- `llvm-project/clang/lib/Sema/SemaExpr.cpp`：表达式语义。
- `llvm-project/clang/lib/Sema/SemaStmt.cpp`：语句语义。
- `llvm-project/clang/include/clang/AST/`：AST 表示。

C++ 会带来额外语义：构造/析构、引用、虚调用、模板实例化、异常和清理等。有些语言要求的常量求值也在此阶段进行，例如 constexpr 场景；它不是之后把两个 LLVM 常量相加的同一种职责。

#### AST 里保留源码的结构

考虑下面贯穿本章的例子：

```c
static float scale_one(float x, float a) {
    float t = a * x;
    return t + 1.0f;
}

void scale(float *restrict out, const float *restrict in,
           unsigned n, float a) {
    for (unsigned i = 0; i < n; ++i)
        out[i] = scale_one(in[i], a);
}
```

这是 C 示例；`restrict` 不应直接当作标准 C++ 关键字使用。数组有效范围与 restrict 约定仍由调用者满足。

AST 的简化示意：

```text
FunctionDecl scale
└─ CompoundStmt
   └─ ForStmt
      ├─ DeclStmt：unsigned i = 0
      ├─ 条件：i < n
      ├─ 更新：++i
      └─ 赋值
         ├─ ArraySubscriptExpr：out[i]（写入位置）
         └─ CallExpr：scale_one
            ├─ in[i] 经读取转换得到 float 值
            └─ a 经读取转换得到 float 值
```

真实 AST 还会显示 `DeclRefExpr`、`ImplicitCastExpr` 等。它们很有意义：名字引用可指向一个变量位置，而计算 `a * x` 需要读取其值；Sema 用隐式转换节点记录这些语言语义。

此时依然有 ForStmt、源码变量和函数调用。LLVM IR 里则没有普通 C 的 ForStmt；循环会变成基本块与分支。

### AST CodeGen：变量、表达式和语句各怎样降低

#### 从 ASTConsumer 到一个 LLVM Function

沿这条源码路线阅读：

```text
ParseAST 通知 ASTConsumer
  → BackendConsumer / CodeGenerator
  → CodeGenModule：顶层声明、全局对象、函数及 ABI
  → CodeGenFunction：某个函数的入口、body、结束处理
  → 具体语句/表达式 emitter
```

对应路径与符号：

- `llvm-project/clang/lib/CodeGen/CodeGenAction.cpp`：`BackendConsumer::HandleTopLevelDecl`、`HandleTranslationUnit`。
- `llvm-project/clang/lib/CodeGen/ModuleBuilder.cpp`：`CreateLLVMCodeGen`、`HandleTopLevelDecl`。
- `llvm-project/clang/lib/CodeGen/CodeGenModule.cpp`：`EmitTopLevelDecl`、`EmitGlobalDefinition`、`EmitGlobalFunctionDefinition`。
- `llvm-project/clang/lib/CodeGen/CodeGenFunction.cpp`：`GenerateCode`、`StartFunction`、`EmitFunctionBody`、`FinishFunction`。

ABI lowering 也发生在这里：一个 C++ 结构体参数可能拆成几个 IR 参数、经指针传递，或通过隐藏返回值指针返回。IR Function 的签名不总与源语言函数签名一一对应。相关入口在 `llvm-project/clang/lib/CodeGen/CGCall.cpp`，目标差异的实现集中于 `llvm-project/clang/lib/CodeGen/Targets/`。

#### 声明：给可修改局部量一个位置

`llvm-project/clang/lib/CodeGen/CGDecl.cpp` 中，`EmitAutoVarDecl` 会调用 `EmitAutoVarAlloca`、`EmitAutoVarInit` 等处理局部对象的存储与初始化；还要考虑 alignment、debug info、lifetime 和语言清理。

对于容易理解的普通自动局部标量，前端可以先用 alloca 提供地址，以 load/store 实现每次读写。这避免让 AST emitter 自己为每个源码变量运行完整 SSA 构建算法。

但“所有变量永远先产生一个 alloca”也不准确：常量、表达式临时值、不同 storage duration、参数、优化选项和特殊语言构造有不同路径。前端可以直接产生 SSA 临时值，或做局部简化。

#### 表达式：先区分“地址”与“值”

对 `out[i] = in[i] * a`：

1. 计算 `in[i]` 的位置：通常生成带元素类型的 GEP 地址运算。
2. 从该位置 load，得到一个 float SSA 值。
3. 与 a 的值计算 fmul，得到另一个 SSA 值。
4. 计算 `out[i]` 的位置，再 store 结果。

路径：`llvm-project/clang/lib/CodeGen/CGExpr.cpp` 的 `EmitLValue`、数组下标与 load/store 发射；`llvm-project/clang/lib/CodeGen/CGExprScalar.cpp` 的标量表达式发射。

**GEP 是地址计算，不是访问数组内容。** `getelementptr float, ptr %in, i64 %index` 按 float 元素步长计算地址；读取数据还需要 load。opaque pointer 的 `ptr` 不带 pointee type，并不意味着元素大小可以不知道，GEP 仍有显式源元素类型。

#### 语句：for 变成 CFG

`llvm-project/clang/lib/CodeGen/CGStmt.cpp` 的 `EmitStmt` 分派到 `EmitForStmt`、`EmitIfStmt`、`EmitReturnStmt` 等。

教学上一个 for 被拆成：

```text
entry：初始化 i
  ↓
cond：读 i，判断 i < n ── false ──→ exit：返回
  │ true
  ↓
body：读取 in[i]、调用 helper、写 out[i]
  ↓
inc：更新 i
  └──────────────────────────────→ cond
```

`break`、`continue`、return、异常与析构会增加或改变边。对于 C++，跳出某作用域前可能必须发射 cleanup；不是简单把每个 break 都替换成一条裸 branch。

### 快照：mem2reg 前的 IR 已经包含什么

下面是**人为压缩的完整教学 IR**，用 64 位指针目标常见的索引形式示意，并非该提交或本机工具的实际输出。为集中展示局部变量，直接使用参数 SSA 值，不展示 Clang 可能产生的参数栈槽、属性、metadata 与清理。

```llvm
define internal float @scale_one(float %x, float %a) {
entry:
  %t.slot = alloca float, align 4
  %product = fmul float %a, %x
  store float %product, ptr %t.slot, align 4
  %t = load float, ptr %t.slot, align 4
  %result = fadd float %t, 1.000000e+00
  ret float %result
}

define void @scale(ptr noalias %out, ptr noalias %in, i32 %n, float %a) {
entry:
  %i.slot = alloca i32, align 4
  store i32 0, ptr %i.slot, align 4
  br label %cond
cond:
  %i.cond = load i32, ptr %i.slot, align 4
  %more = icmp ult i32 %i.cond, %n
  br i1 %more, label %body, label %exit
body:
  %i.body = load i32, ptr %i.slot, align 4
  %index = zext i32 %i.body to i64
  %src = getelementptr float, ptr %in, i64 %index
  %x = load float, ptr %src, align 4
  %y = call float @scale_one(float %x, float %a)
  %dst = getelementptr float, ptr %out, i64 %index
  store float %y, ptr %dst, align 4
  br label %inc
inc:
  %i.old = load i32, ptr %i.slot, align 4
  %i.next = add i32 %i.old, 1
  store i32 %i.next, ptr %i.slot, align 4
  br label %cond
exit:
  ret void
}
```

逐项看已有的信息：

- **函数与类型已经确定：** out/in 是指针，n 是 i32，计算是 float。
- **控制流已经确定：** entry/cond/body/inc/exit 和 branch 就是循环。
- **每个临时值已经是 SSA：** `%product`、`%x`、`%i.next` 都只有一个定义。
- **源码变量 i 的“当前内容”还在内存中：** 修改它使用 store，读取它使用 load。
- **真正的数组访问仍在内存中：** in/out 并不是局部 slot，不能期待 mem2reg 消灭数组读写。
- **语言约定已开始进入 IR：** 示意的 noalias 表达相关参数事实；实际属性和 metadata 的生成细节仍要看具体 CodeGen。

所以，“LLVM IR 已是 SSA，为什么还要 mem2reg”并不矛盾。**原 IR 的指令结果符合 SSA；mem2reg 把符合条件的内存状态也重编码成 SSA 值。**

### mem2reg 输入的来源与已有处理

进入 mem2reg 之前，必然已经完成足以生成合法 IR 的语言处理：目标选择、预处理/词法、解析/Sema、AST CodeGen、ABI 与基本控制流/访存发射。

输入是否已经经过其他 LLVM Pass，取决于其生成方式：

| 输入来源 | mem2reg 之前的处理 |
|---|---|
| 教学手写 `.ll` | 只需先有合法 IR，不存在 Clang AST 步骤 |
| Clang `-O0 -S -emit-llvm` | 已有前端生成与必要整理；常带 optnone，普通优化 Pass 可能跳过 |
| 禁用 LLVM Pass 的前端输出 | 保留 AST CodeGen 与其局部工作，不代表完全没有折叠/简化 |
| 普通 `clang -O2/-O3` 的中间状态 | 管线可能已做模块处理、属性推导、内联、SROA/promotion 等 |
| 从另一前端导入的 `.bc` | 初始 IR 风格与已有优化可能不同 |

最重要的是：**“mem2reg 前”是一个观察切面，不是所有编译任务都有的唯一时间点。**

默认优化经常由 SROA 内部调用 promotion，而不是显式安排名为 mem2reg 的独立 Pass。因而，debug-pass-manager 输出中没有 PromotePass，并不能说明未发生 SSA 提升；局部 load/store 的变化还需要与 SROA 等实际执行步骤对应。

### 快照：提升以后，i 的状态成为循环 PHI

对上面的教学 IR 运行 promotion 后，helper 的 `%t.slot` 可消失，scale 的 `%i.slot` 可变成：

```llvm
entry:
  br label %cond
cond:
  %i = phi i32 [ 0, %entry ], [ %i.next, %inc ]
  %more = icmp ult i32 %i, %n
  br i1 %more, label %body, label %exit
body:
  %index = zext i32 %i to i64
  %src = getelementptr float, ptr %in, i64 %index
  %x = load float, ptr %src, align 4
  %y = call float @scale_one(float %x, float %a)
  %dst = getelementptr float, ptr %out, i64 %index
  store float %y, ptr %dst, align 4
  br label %inc
inc:
  %i.next = add i32 %i, 1
  br label %cond
exit:
  ret void
```

这是对应函数 body 的片段。初始边带来 0，回边带来 i.next；body、inc 使用同一个当前 `%i`。

提升后，循环状态每次经回边递增 1 的关系由 PHI 和更新指令显式表达。SCEV 可直接分析这种 recurrence，不必在 i.slot 的 load/store 链中反复寻找最后写入者。

但是 promotion 没有做三件事：没有自动删除 helper call、没有生成向量指令、没有给 i 分配硬件寄存器。

### 内联与清理：让循环体显露计算，而不是隐藏调用

内联 helper 并清理后，循环体可出现：

```llvm
%x = load float, ptr %src, align 4
%product = fmul float %a, %x
%y = fadd float %product, 1.000000e+00
store float %y, ptr %dst, align 4
```

这一步为向量化提供一个很简单的逐元素模式。若 helper 没内联，LV 需要理解该调用是否安全、有无向量版本、是否支持相应处理，不能把任意 call 当成无副作用的乘加。

这里没有把浮点运算擅自变成实数代数或 FMA。是否 contract、是否允许 reassociation，都需要保留前端传来的浮点语义与目标约束。

内联也可能把 helper 的 alloca 带进 caller，因此 **inline → SROA/promotion → InstCombine** 之类的后续整理很自然。生产管线不是“一次提升后永不再提升”。

### Pass Manager 的组织与分析维护

Clang 前端完成 Module 后，把它交给后端入口；中端优化与机器 codegen 是这里的不同子阶段。

`llvm-project/clang/lib/CodeGen/BackendUtil.cpp` 的 `EmitAssemblyHelper::RunOptimizationPipeline`：

1. 根据目标/选项构造 PassBuilder。
2. 注册 Module、CGSCC、Function、Loop analyses 及 manager proxies。
3. 按优化级别、LTO 等选择管线；普通路径调用 `buildPerModuleDefaultPipeline`。
4. 执行 ModulePassManager；选择输出 IR 时序列化结果，选择机器输出时继续 codegen。

对应管线定义在 `llvm-project/llvm/lib/Passes/PassBuilderPipelines.cpp`。四个层次按 Pass 处理对象的粒度划分，与 IR 语言的种类无关：

| 层 | 处理范围 | 例子 |
|---|---|---|
| Module | 一个 IR 模块中的函数与全局对象 | 模块属性、全局清理 |
| CGSCC | 调用图的强连通分量 | 内联及调用图更新 |
| Function | 单函数 CFG 与指令 | SROA、InstCombine、SCCP、LV |
| Loop | 单个循环或相关 loop nest | LICM、rotate、部分展开/循环变换 |

LV 虽然名字是 LoopVectorize，却以 Function Pass 驱动并自行处理循环；Pass 名字不能直接用来猜它的 manager 层次。

AnalysisManager 按请求计算并缓存事实。Transform 声称保留的分析可复用，否则失效/重算；“某个 analysis 在这里可用”并不意味着它一定在固定前一行运行。阅读管线时应分清**安排了一个变换**和**按需取得一份分析结果**。

### 进入循环优化之前：三个层面的准备

#### 语义事实：知道什么不能动

目标循环需要带着正确事实进入中端：

- 整数位宽、signedness 相关比较、溢出规则。
- 浮点 flags/环境、是否允许 contraction/reassociation。
- 调用副作用、异常、volatile/atomic/同步。
- 指针别名、参数/对象信息、对齐、已知范围和 assumptions。

有些由前端直接产生，有些由跨函数属性推导、内联、AA 等后续推导。它们是证明基础，不只是优化速度开关。

#### 表示形状：让循环成为可处理的对象

常见准备包括：

- SROA/promotion 使可提升的局部状态变成 SSA。
- InstCombine、EarlyCSE、SimplifyCFG 等去掉冗余和多余 CFG。
- 内联暴露隐藏计算；TRE 可以把某些自递归变成循环。
- LoopSimplify 整理 preheader、latch、dedicated exits 等可达规范形式。
- LCSSA 把 loop 内定义、loop 外使用的值经退出 PHI 表达。

**这些不是每种优化都必须逐项重新执行的全称清单。** 输入可能早已满足形状；一些不可约 CFG 无法直接规范成所需自然循环；某 Pass 可自行处理特例。

#### 分析事实：知道循环如何运行、机器支持什么

DominatorTree/LoopInfo、ScalarEvolution、AA、TTI/TLI 和按需要的 MemorySSA 等，回答：

```text
哪里是循环，入口和回边在哪里？
谁支配谁，某条指令是不是必定执行？
诱导变量如何递推，trip count 有没有上界或倍数？
哪些访问可能重叠，哪些写会影响读取？
目标的向量、访存、指令成本如何？
```

这些分析结果共同约束展开因子、向量通道数量及运行时守卫的成本选择。

### Loop adaptor 中的规范化准备

函数管线通过以下 adaptor 执行循环 Pass：

```cpp
FPM.addPass(createFunctionToLoopPassAdaptor(std::move(LPM1),
                                            /*UseMemorySSA=*/true));
```

LoopSimplify 和 LCSSA 不必在调用处单独列出。该提交的 `FunctionToLoopPassAdaptor` 在构造时准备了一段 canonicalization pipeline。

位置：`llvm-project/llvm/include/llvm/Transforms/Scalar/LoopPassManager.h`：

```cpp
LoopCanonicalizationFPM.addPass(LoopSimplifyPass());
LoopCanonicalizationFPM.addPass(LCSSAPass());
```

执行位置：`llvm-project/llvm/lib/Transforms/Scalar/LoopPassManager.cpp` 的 `FunctionToLoopPassAdaptor::run`。有循环时先运行 canonicalization，再取得新的 LoopInfo 和标准分析集合；若请求 UseMemorySSA，再取得并传递 MemorySSA。

它体现一种很重要的设计：**变换所需的输入形式可由执行框架统一保证，而不必在每个 Pass 前手写一遍准备步骤。**

同时这不是对所有带“loop”字样的 Pass 的普遍承诺；例如 Function 级 LV 自己获取/整理有关循环状态。应追当前实际使用的入口。

### 前期循环管线与多轮标量清理

看 `PassBuilder::buildFunctionSimplificationPipeline`，排除 O1 的专门分支、按固定提交中的普通相应路径：

```text
SROA → EarlyCSE
  → 分支/相关值等简化（部分步骤受选项控制）
  → SimplifyCFG → InstCombine / AggressiveInstCombine 等
  → TailCallElim → SimplifyCFG → Reassociate
  → [Loop adaptor 的 LoopSimplify + LCSSA]
  → LPM1：LoopInstSimplify、LoopSimplifyCFG、LICM、Rotate、LICM、Unswitch 等
  → 函数级 SimplifyCFG、InstCombine
  → LPM2：Idiom、IndVarSimplify、LoopDeletion、FullUnroll 等
  → SROA 与后续标量清理，包括相应位置的 SCCP、DCE 家族等
```

图中仅列出主要步骤；PGO/LTO、选项、目标 callbacks 和优化级别会改变完整管线。该版本在前期 loop passes 后仍安排 SCCP 等标量清理，更早的折叠与简化也可由其他步骤完成。常量传播、死代码删除和循环变换由此交错运行，而非各自一次性完成。

为什么完整展开可能在这里很早？小常数循环完全展开后能暴露常量和数组固定索引，再由 SROA、InstCombine 等删除大量工作。等到向量化阶段，它可能已不再是循环。

为什么向量化常较晚？前期内联、别名/属性推导、结构整理能改善可分析性；向量化会生成主体、guard、fallback、尾部等更复杂结构，太早做可能妨碍其他标量变换。

### 不同变换的输入条件

| 变换 | 所需证明与准备 | 并非必需的条件 |
|---|---|---|
| 保序展开 | 当前实现支持的 loop/CFG、正确克隆和退出、trip count/倍数/上界或 runtime 策略、大小与目标成本 | 所有迭代必须独立；必须先向量化 |
| Loop Vectorizer | 能解释的循环状态/指令、内存依赖和浮点合法性、可行 VF 与检查/尾部方案、收益 | helper 必须无条件内联；必须先经过通用 LoopUnroll |
| SLP | 同形指令组、可共同调度、访存与外部 uses 合法、打包/shuffle 成本 | 必须有 loop；必须先有 trip count |
| Polly 线程化 | 可建模 SCoP、依赖与 schedule、并行检测、实际线程化策略与运行时生成 | 普通 `-O3` 自动插入所有 OpenMP fork |
| MLIR affine parallelization | 保留的 affine loop/access 信息、parallel/reduction 检查、后续 lowering 路线 | 必须先从 C 降成普通 LLVM IR 再恢复高层结构 |
| OpenMP parallel/for | 前端接受规范构造、数据环境与线程语义、outline 和 runtime lowering；再做已有 IR 的优化 | LLVM 必须先从普通循环静态证明所有线程完全独立 |

这里的 helper 内联是强有力的机会提供者，不是逻辑上唯一道路；有向量函数库等支持时，LV 也可能处理适用调用。

线程并行尤其不是“在 LV 之后再运行一个普通并行化 Pass”。OpenMP 在前端就有显式并行语义；MLIR 路线可以在高层 IR 分支；Polly 对 LLVM IR 的可分析区域另建模型。它们是不同入口，不应画成一个所有 C 函数都顺序经过的必经步骤。

### 快照：一个已经方便分析的标量循环

经过适用的 promotion、内联和规范化后，可得到下面**教学示意**形状；具体目标/版本也可能使用不同计数方式：

```text
entry guard：n 是否为 0？
      / false（有工作）             \ true
preheader                            exit
      |
header/body：i = phi(0, i.next)
  连续读取 in[i]
  计算 a*x+1
  连续写入 out[i]
      |
latch：i.next = i+1；是否还小于 n？
      └─ 是 → header/body
      └─ 否 → exit
```

这时能把每层信息明确说出来：

- SSA 说明 i 的定义/使用和回边状态。
- LoopInfo 说明循环区域，preheader 与 latch。
- SCEV 尝试识别 i 的 `{0,+,1}` 递推及计数规律。
- AA/LoopAccessAnalysis 综合数组关系，决定是否独立、是否要检查。
- TTI 提供 SIMD 成本与目标限制。
- LV 根据这些事实规划 VPlan，而不是直接读取 C 的 ForStmt。

将含 slot 的 IR 与此图对照，可以看到基础优化如何显式化定义、使用和循环状态，为后续分析提供更直接的输入。

### 快照：最终向量方案比“一条 SIMD 指令”复杂

假设一个候选使用 VF=4、IC=1，普通 fixed-width 主体可概念化为：

```text
入口检查 n
  → 计算能处理多少完整 4 元素批次
  → 按需要执行 SCEV/alias/runtime 收益 guard
  → vector body：向量 load → splat(a)*X+1 → 向量 store，索引加 4
  → 剩余元素：标量或其他向量尾部
  → exit
```

对 noalias 足够的教学参数，不一定需要额外 alias guard。若失去相关事实，可加快路径/原标量 fallback；如果目标选择 tail folding，结构也会改变。

对照各阶段，可以区分五类表示变化：

1. 前端的 `++i` 最初是变量位置上的更新；后面成为 SSA recurrence，再成为向量索引步进。
2. helper 最初是一个 call；适用内联后才显露 fmul/fadd。
3. 本来每次读一个 float，向量主体可每次读多个；但最终还要经过后端目标合法化。
4. i.slot 被提升并不意味着 out/in 的实际数据也从内存消失。
5. 优化后的向量 IR 仍无最终物理寄存器；Greedy 在更后面的 Machine IR 上安排资源。

### C++ 额外复杂性：不能把语言语义当作“优化噪声”

在简单 C 示例里看不到的内容，真实 C++ CodeGen 可能已放进 IR：

- 引用绑定与对象生命周期。
- 构造、析构与作用域 cleanup。
- 虚调用、对象布局、this 与隐藏 ABI 参数。
- 异常的 invoke、unwind 和异常处理块。
- 模板实例化后实际可发射的函数体。

这些语言语义可能限制加载的推测执行、尾递归消除、内联或循环向量化。删除相关处理需要证明，例如调用不会抛出异常、对象状态不逃逸；仅凭它们不参与主要数值运算，不能判定其效果不可观察。

此外，Clang 的 C/C++ 前端通常直接走 AST→LLVM IR，**不是默认先经过 MLIR**。MLIR 很适合某些高层域和转换流程，但不能把它插进普通 Clang 默认编译路线当必经层。

### 链接与 LTO：为什么有时优化又跨过目标文件边界

普通分离编译中，某个 `.c/.cpp` 编译任务只能优化当前可用 Module 里的内容；外部函数若仅有声明，不能任意克隆它的 body。链接器合并普通机器目标文件，不会自动让已结束的中端重新看到所有函数源码。

LTO 使 bitcode/摘要等参与链接时的优化阶段：Full LTO 和 ThinLTO 用不同方式获得跨模块信息和进行后续优化，可能打开跨文件内联、属性推导等机会。所以有 pre-link/post-link 管线，而不是一个固定 `-O3` 清单。

普通 `.ll/.bc` 输出也不自动等于已配置 LTO 可执行链接。要区分“保存 IR”“以 IR 参与 LTO”与“链接机器目标文件”三件事。

### 各阶段表示的观察方法 {#怎样亲眼观察每个边界}

以下为未实测的验证命令。沿用[优化诊断与对照实验](#practice)中的 `$Clang`、`$Opt`、`$Exp`，将本章 C 示例保存为临时实验目录中的 `pipeline.c`。已安装的工具可用于观察编译表示；对照固定提交的实现时，需要使用匹配版本。

```powershell
# 看 driver 准备的命令，不真正执行编译。
& $Clang '-###' -O2 -c "$Exp\pipeline.c"

# 观察预处理后的 C 与 AST，不启动常规机器输出。
& $Clang -E "$Exp\pipeline.c" -o "$Exp\pipeline.i"
& $Clang -Xclang -ast-dump -fsyntax-only "$Exp\pipeline.c" `
    > "$Exp\pipeline-ast.txt"

# 保留 O1 的前端设置，但禁用 LLVM 中端 Pass。
# 这是接近中端入口的观察方式，不是绝对无简化的原始 AST。
& $Clang -O1 -Xclang -disable-llvm-passes -S -emit-llvm `
    "$Exp\pipeline.c" -o "$Exp\frontend.ll"

# 单独看 promotion，再看生产式 O2 管线。
& $Opt -S -passes='mem2reg' "$Exp\frontend.ll" `
    -o "$Exp\promoted.ll"
& $Opt -S -passes='default<O2>' "$Exp\frontend.ll" `
    -o "$Exp\optimized.ll"

# 对照 Clang 自己的 O2 输出；它不保证与上面的 opt 管线完全相同。
& $Clang -O2 -S -emit-llvm "$Exp\pipeline.c" `
    -o "$Exp\clang-o2.ll"
```

`-O0` 也是有用的观察点，但常带 `optnone`；普通可选优化可能因此跳过。可研究 `-Xclang -disable-O0-optnone`，但这不把 O0 的前端设置变成 O2。也不能保证 `-O0` 输出完全没有 folding，因为 AST CodeGen、IR 构造和必要整理仍会做工作。

#### 看“某个 Pass 前”的 IR，而不是猜测

```powershell
# 新 PM 执行日志；看实际 manager、analysis 与 pass。
& $Opt -disable-output -debug-pass-manager -passes='default<O2>' `
    "$Exp\frontend.ll" 2> "$Exp\pass-manager.txt"

# 只打印若干指定 Pass 前后的 IR，避免无限大的 print-all 日志。
# 标识名随工具版本变化；下列为对应功能的常用标识。
& $Opt -disable-output -passes='default<O2>' `
    -print-before=loop-vectorize -print-after=loop-vectorize `
    "$Exp\frontend.ll" 2> "$Exp\around-vectorize.txt"
& $Opt -disable-output -passes='mem2reg' `
    -print-before=mem2reg -print-after=mem2reg `
    "$Exp\frontend.ll" 2> "$Exp\around-promotion.txt"
```

区别如下：

- AST dump 回答前端理解了什么。
- frontend.ll 回答 AST 降低成了什么。
- promoted.ll 回答哪些局部内存已成为 SSA。
- around-vectorize 回答 LV 真正接收了哪种 loop，而不是原 C 的形状。
- 最终 `.s` / MIR 回答后端把方案实现成什么、有没有 spill。

最终 `-O3` IR 已经过中端管线，不能作为 AST 刚降低后的表示。比较快照时，需要同时记录生成选项与捕获位置。

### 输入事实与可执行的变换

各阶段提供的信息及其支持的后续工作如下：

| 阶段 | 得到的关键信息 | 因而能做的事 |
|---|---|---|
| Sema | 正确类型、绑定、隐式转换与语言规则 | 构造语义正确的 AST |
| AST CodeGen | ABI、对象位置、表达式与控制流 | 发射合法 LLVM IR |
| promotion | 局部状态的明确 SSA 定义/使用 | 稀疏传播、识别 recurrence |
| 内联/属性/清理 | 实参事实、可见计算与更简单 CFG | 折叠、去副作用障碍、暴露 loop body |
| canonicalization | 可处理的入口、回边、退出与数据接口 | 通用 loop transforms |
| SCEV/AA/TTI 等 | 计数、依赖、目标能力与成本 | 选择合法且值得的展开/向量方案 |
| 并行专门路线 | 独立性证明或显式并行语义、执行模型 | 线程划分与 runtime lowering |
| 后端 | 目标指令约束和真实活跃范围 | 调度、分配寄存器、生成机器码 |

管线分析的关键是追踪事实的来源和使用：每个变换接收何种表示、依赖哪些分析、改变哪些结构，以及输出由后续哪个阶段接收。这个关系比单独的 Pass 名称顺序更能解释实际编译行为。
