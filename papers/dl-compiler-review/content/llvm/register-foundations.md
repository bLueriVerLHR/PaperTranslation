## 寄存器分配基础 {#register-foundations}

### 虚拟值与有限物理资源

LLVM IR 值的命名数量不受目标寄存器数量直接限制，目标机器的物理寄存器却有限，且具有不同用途与约束。指令选择后的 Machine IR 用虚拟寄存器表示值，寄存器分配器决定各段值如何驻留。

```text
虚拟值与机器指令
   → 每个值什么时候必须存活
   → 哪些值不能共用某个物理资源
   → 指派 / 切分 / spill / rematerialize
   → 物理寄存器与栈槽
```

它不是给源代码变量逐个选一个固定寄存器。一个源码变量可以有多个 SSA 值；一个 live range 被切开后，不同段可以用不同寄存器甚至栈。反过来，多个不同时活跃的值可以共用同一物理寄存器。

### 活跃性与反向数据流

基本块层的经典反向数据流方程：

```text
LiveOut(B) = 并集 { LiveIn(S) | S 是 B 的后继 }
LiveIn(B)  = Use(B) ∪ (LiveOut(B) − Def(B))
```

`Use(B)` 指在本块对应定义之前读取的值。循环 CFG 上通常需要迭代到固定点。往指令内部细化，可以得到每个程序点的活跃集合。

**interference（冲突）** 表示两个值在需要保存不同内容的重叠时间不能占用同一资源。COPY 关系、子指令位置和机器约束使实际冲突分析比粗略区间重叠更精细。

一个简化单块例子：

```text
0: a = ...
1: b = ...
2: use a
3: c = ...
4: use b
5: use c
```

忽略子指令 slot，a 约活到 2，b 活到 4，c 从 3 活到 5；a 与 b 冲突，b 与 c 冲突，a 与 c 可复用。分配要解决的是让同时需要的数据不互相覆盖，名字是否相同并不重要。

### LiveInterval 并不一定是一个连续区间

核心路径：

- `llvm-project/llvm/include/llvm/CodeGen/LiveInterval.h`：LiveRange、Segment、VNInfo、subrange。
- `llvm-project/llvm/lib/CodeGen/LiveIntervals.cpp`：构建与维护区间。
- `llvm-project/llvm/lib/CodeGen/SlotIndexes.cpp`：机器指令的位置编号。

LLVM 的 live range 可有多个半开 segment，存在空洞；VNInfo 区分值的不同定义来源。subranges / lane masks 又可表达部分子寄存器的活跃性。

SlotIndex 不只是源码行号：一条机器指令内部需要区分 block boundary、early-clobber、普通 register slot、dead definition 等位置。这帮助处理“输入读取与输出写入”是否可共享物理资源。

如果把所有段粗暴包成一个从 first def 到 last use 的大区间，就会把实际空洞当作活跃，产生虚假的冲突；这也是现代实现比最简线性扫描更精细的原因之一。

### 真实机器比 K 种颜色复杂

**寄存器类。** 整数、浮点、向量或特殊指令各有合法候选集合；不是任意值可进任意寄存器。

**别名与 register units。** x86 的 RAX/EAX/AX/AL 存在重叠，向量宽度也涉及资源关系。LLVM 将物理寄存器映射为共享 units，避免把重叠名字误当独立资源。某些写还带有目标特定零扩展等语义。

**固定占用。** 某些指令必须使用特定寄存器，inline asm 有约束，部分寄存器保留给栈指针等用途。

**call regmask。** 调用按约定破坏一组 caller-saved 寄存器。跨 call 活跃值不能仅凭“别的虚拟值没占它”就留在会被 call clobber 的寄存器中。

**callee-saved。** 使用它可能需要函数序言/尾声保存恢复，有第一次启用成本；但对跨调用热值可能比反复 spill 更好。

**two-address 和 tied operands。** 输入输出可能要求同一寄存器；early-clobber 输出可能在其他输入读取前就被覆盖。

这些约束解释了为何峰值活跃值数≤寄存器数，并不必然可分配：某些值共同只能选择很小的子集合。

### LiveRegMatrix：不必先建立一个巨大冲突图

路径：`llvm-project/llvm/lib/CodeGen/LiveRegMatrix.cpp`、`llvm-project/llvm/lib/CodeGen/LiveIntervalUnion.cpp`。

Greedy/Basic 通过 LiveRegMatrix 查询“当前 LI 放到物理寄存器 p 是否冲突”。每个 unit 可维护已经分配区间的 union，然后按所需时间段查询交集。

`checkInterference` 区分：

- `IK_Free`：可用。
- `IK_VirtReg`：其他已分配虚拟区间挡路，可能驱逐/切分。
- `IK_RegUnit`：固定物理占用等障碍。
- `IK_RegMask`：调用 clobber 等障碍。

**驱逐其他虚拟值不能消除 fixed 或 regmask 冲突。** 不分清这几类，就会误以为总能“把别人赶走腾位置”。

### 四种处理办法：assignment、splitting、spilling、rematerialization

1. **assignment：** 一整段当前区间分给某个物理寄存器。
2. **splitting：** 切开区间，在边界插 COPY 或必要的内存转换，让热区与冷区、不同压力区域独立分配。
3. **spilling：** 部分值驻留栈槽，定义后 store、使用前 reload；reload 后仍然需要一个短生命周期寄存器。
4. **rematerialization：** 对可廉价且语义安全地重算的值，在使用附近再算，如某些常量生成；不一定非得先存再读。

“spill 一个虚拟寄存器”不是把所有用途都变成直接内存操作。指令可能允许折叠内存 operand，也可能必须新建 reload vreg。spiller 因而会产生新的分配任务，这些短范围需要重新进入分配流程。

路径：`llvm-project/llvm/lib/CodeGen/SplitKit.cpp`、`llvm-project/llvm/lib/CodeGen/LiveRangeEdit.cpp`、`llvm-project/llvm/lib/CodeGen/InlineSpiller.cpp`、`llvm-project/llvm/lib/CodeGen/VirtRegMap.cpp`。

### LLVM 本提交提供的主要方案

| 方案 | 核心设计 | 优点与定位 | 源码 |
|---|---|---|---|
| Fast | 基本块局部、反向扫描，跨块值经栈 | 编译速度与调试路径优先，代码质量较保守 | `llvm-project/llvm/lib/CodeGen/RegAllocFast.cpp` |
| Basic | 区间优先队列＋冲突查询，不能放时 spill 当前或阻碍者 | 清晰展示共享基础设施，策略较简单 | `llvm-project/llvm/lib/CodeGen/RegAllocBasic.cpp` |
| Greedy | 优先级分配＋驱逐＋区域/局部切分＋有限重着色 | 常用优化路径，质量与编译成本折中 | `llvm-project/llvm/lib/CodeGen/RegAllocGreedy.cpp` |
| PBQP | 将候选寄存器和 spill 建模为带成本选择问题 | 适合表达不规则资源与偏好，有求解代价 | `llvm-project/llvm/lib/CodeGen/RegAllocPBQP.cpp` |

该版本的 Basic 共享 RegAllocBase/LiveRegMatrix，并使用 spill weight 优先队列组织分配。它不按区间起点单调扫描，因此与经典线性扫描的执行顺序不同。

Fast 文件开头说明，它不构建完整的数据流活跃性、活跃范围切分或冲突图/coalescer。它反向扫描各基本块，遇到 use 时取得寄存器，遇到对应 def 时释放，跨块值经栈槽连接。这与 Greedy 的全局区间策略有结构性区别，不只是减少同一算法的搜索预算。

Basic 的 `spillInterferences` 要求阻碍者可 spill 且权重不高于当前值，再将其交给 spiller；否则最后 spill 当前值。Greedy 的重要进步是：**不必把驱逐直接等同于 spill；先让被驱逐者重新找位置，并尝试更精细切分。**

### 经典线性扫描的排序与 active 集合

Poletto–Sarkar 风格最简算法：

```text
按 interval.start 排序
active = 按结束位置排序的已分配区间
for current:
    释放所有 end <= current.start 的 active
    有空闲寄存器 → 分配
    没有 → 从 current 与 active 选择牺牲者
           常见简单启发式：结束最晚者
```

线性扫描利用位置单调推进的性质：已经结束的区间不再影响后续位置，active 集合据此维护当前占用，而无需预先建立完整冲突图。排序和集合操作仍有成本，因此名称不保证整个实现严格 O(n)，加入机器约束后也未必只需一轮处理。

最简形式损失来源：CFG 被线性化、区间空洞、冷热差异、固定寄存器、复制偏好、跨调用选择。现代 linear scan 可以加入 inactive、拆分和位置约束，不能把整个算法家族都说成只能一次粗暴 spill。

### 图着色与 PBQP：两种更全局的理解

图着色把值作为节点、冲突作为边、物理寄存器作为颜色。经典 simplify/spill/select 方案在难处做启发式决定；真实分配还要处理预着色、不同候选集合与复制合并。一般寄存器分配的困难不能靠“LLVM IR 是 SSA”完全消除，因为实际机器约束和后端 PHI/两地址处理已经改变问题。

**PBQP（Partitioned Boolean Quadratic Programming）** 的教学模型：每个节点 i 从候选寄存器或 spill 选一个 one-hot 方案；单点成本向量给出选择费用，成对成本矩阵给出相互选择费用。

```text
总成本 = 所有节点所选项成本 + 所有相关边所选组合成本
冲突值选重叠物理寄存器 → 无穷大 / 不允许
复制相关值选择相同资源 → 可降低复制成本
spill 项 → 估计的内存代价
```

`RegAllocPBQP.cpp` 文件头明确说明：建问题、求解、映射回分配；若选择 spill，插入 spill code 后重复。实际求解器采用寄存器分配特化启发式，不是证明所有函数都求到全局最优。

继续读 `llvm-project/llvm/include/llvm/CodeGen/PBQP/`。原理文献在实现文件头给出：Scholz 与 Eckstein（2002），Hames 与 Scholz（2006）。图着色、PBQP 是理解问题的模型；它们不意味着 LLVM Greedy 默认先构造并求解一张完整着色图。
