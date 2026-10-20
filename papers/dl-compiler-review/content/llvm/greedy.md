## Greedy 寄存器分配 {#greedy}

### 工作队列与分配结果的返回协议

`llvm-project/llvm/lib/CodeGen/RegAllocBase.cpp` 中的 `allocatePhysRegs` 组织分配工作队列，RAGreedy 在这个框架内实现候选选择、驱逐和切分策略。

```text
seedLiveRegs：把需要分配的区间入队
while 队列非空:
    取出一个 LI，确认它尚未分配
    若已无有效使用，清理
    使受变更影响的冲突查询缓存失效
    phys, newRanges = selectOrSplit(LI)
    有 phys → Matrix.assign
    对被驱逐、切分、spill 产生的新范围重新入队
结束后由后端完成 rewrite 和整理
```

`selectOrSplit` 并不保证每次返回一个物理寄存器。返回“没有直接分配，但产生了新范围”是正常进展，而不是失败。RegAllocBase 因此能容纳不同策略，共享区间维护与队列驱动。

### 全局范围与局部范围的排序

在 `llvm-project/llvm/lib/CodeGen/RegAllocGreedy.cpp`：

- `RAGreedy::enqueue`（本提交 420 行附近）调用 PriorityAdvisor。
- `DefaultPriorityAdvisor::getPriority`（439 行附近）编码 stage、物理 hint、寄存器类优先级、全局性和 size / 指令距离。

**全局与拆分范围通常按 long→short 排序。** 长区间跨越较多位置，需要在更多程序点保持可用资源，较早处理能提前暴露切分需求，减少后续对短区间安排的扰动。这里的 size 度量 live segments，而不是动态执行次数。

**局部原始区间存在另一套顺序。** 在满足本版本条件时，对单一 MBB 内的 singly-defined 区间按线性指令顺序分配；默认非 reverse 方向用 beginIndex 到末端的距离确定优先级。文件注释指出：没有全局干扰和其他约束时，可得到最优着色。

这与区间图的性质一致：单块连续生命周期按位置前进，释放已结束区间并复用颜色，可以做到峰值压力所需的颜色数；但加入固定资源、全局区间或不同候选集合，这个理想性质就不能直接套用。

源码还会把某些很大的 local range 强制按 global 策略处理，并提供目标/选项相关优先级。因此严格说：

> LLVM Greedy 中含有局部线性顺序策略；Greedy 整体不是传统 linear scan。

既不能说它完全不利用扫描观察，也不能把整个 allocator 称为“按起点一次扫描”。

### 队列优先级与 spill weight

队列优先级决定尝试分配的顺序，spill weight 估计将范围保留在寄存器中的价值。两者服务于不同决策，并非同一个度量。

`llvm-project/llvm/lib/CodeGen/CalcSpillWeights.cpp` 的 `VirtRegAuxInfo::weightCalcHelper` 汇总读写使用的频率相关权重，处理 COPY hints、可 rematerialize 的值、某些看起来像 induction update 的情形，并做归一化。

概念上它估计“因 spill 导致的动态工作 / 这段区间占用的空间”。实际公式有保护常数、目标因子和特殊情形，不应将教学比例当成精确源码公式。

归一化用于比较单位资源的收益：两个值同样使用十次，若一个贯穿很长区间，另一个集中在十条指令内，后者占用资源的时间较短。频率权重则区分动态执行成本，冷路径的一次 load 与热循环中的大量 load 不应按相同代价处理。

没有采样或插桩 profile 时，块频率也可能是静态估计；allocator 不是在编译时知道真实每次运行。能安全重算的常量通常比只能从内存恢复的值更便宜；induction 更新 spill 则可能每轮昂贵。

### 第一步：tryAssign 与寄存器偏好

`RAGreedy::tryAssign`（532 行附近）用 `AllocationOrder` 遍历合法候选，并问 `Matrix->checkInterference`。

`AllocationOrder` 不是简单从 R0 到 R31：它结合寄存器类、目标顺序、保留寄存器和 hints。COPY 的源/目的若用同一物理寄存器，复制可能在 rewrite 后消失。

已经发现一个空闲寄存器时，也可能继续改善：

- 若 preferred register 被可低代价驱逐的范围占用，可以为 hint 腾位置。
- 若 hint 在冷块遇到冲突，可以尝试 around-hint splitting。
- 若可用寄存器有额外 cost，可尝试腾出更便宜替代。

因此 `tryAssign` 不总是纯粹只读查询；它可能引入驱逐或切分。理解总流程时必须检查 `NewVRegs`，而不只检查返回值。

### callee-saved 的第一次使用为何单独考虑

`selectOrSplitImpl` 找到空闲 CSR 后，某些情况下还调用 `tryAssignCSRFirstTime`。原因：首次启用一个 callee-saved register 可能让函数产生额外保存恢复；对只在冷块使用的值，局部 spill 可能更便宜。

但不能反过来说 CSR 总是贵：一个热循环或跨大量 calls 的值，避免反复 reload 的收益可能远超一次保存恢复。这里比较的是**增量成本**，受块频率与后续 frame lowering 影响，并不是“一律先用 caller-saved”的充分策略。

### 第二步：eviction 不等于 spilling

当前区间 A 想用 p，但 B 已占有 p：

```text
若 B 是可移动的虚拟区间且驱逐代价可接受:
    Matrix.unassign(B)
    将 B 放回待处理集合
    将 A 分给 p
```

B 后续可能换寄存器、切分或最终 spill。**立即 spill 所有阻碍者的是更粗策略；Greedy 先保留修正机会。**

`RAGreedy::tryEvict` 与 `evictInterference` 在 `RegAllocGreedy.cpp`；默认判断在 `llvm-project/llvm/lib/CodeGen/RegAllocEvictionAdvisor.cpp` 的 `DefaultEvictionAdvisor::shouldEvict` 和相关成本检查。

需要考虑的不是一个 B：p 的不同 units 和不同时间段可能被多个范围占据。成本会考察多个阻碍者、被破坏 hints、权重和 urgency。某些不可 spill 的短范围或严格受限类，需要更紧急地得到寄存器。

这里的 ML advisor 文件（`llvm-project/llvm/lib/CodeGen/MLRegAllocEvictAdvisor.cpp`、`llvm-project/llvm/lib/CodeGen/MLRegAllocPriorityAdvisor.cpp`）允许用训练策略替代部分启发式，受构建和配置控制。它们不是一套完全独立 RA，也不能据目录存在就说默认启用了机器学习。

### 驱逐链与分配阶段的进展约束 {#贪心允许反悔为什么不会永远互踢}

如果 A 驱逐 B，B 再驱逐 A，两者即可循环。Greedy 用两类结构限制这种行为：

1. **cascade 编号：** 记录驱逐链，在策略判断中阻止形成无休止循环；urgent 等特殊情形有自己的规则。
2. **stage：** 区间逐渐从原始分配阶段进入等待切分、切分与 spill 等阶段，不能无限重复同一探索。

状态定义可追 `llvm-project/llvm/include/llvm/CodeGen/RegAllocEvictionAdvisor.h`；附加信息维护在 `llvm-project/llvm/lib/CodeGen/RegAllocGreedy.h` 的 `ExtraRegInfo`。

不能把它夸大为“单个启发式函数保证最优”。它们保证算法在工程预算内取得进展，并避免策略反复制造同类工作；代码质量仍是启发式结果。

### 第三步：第一次放不下，为什么不马上切分

读 `selectOrSplitImpl`（本提交 2658 行起）：

```text
tryAssign
  → 若适用，考虑首次 CSR 成本
  → tryEvict（stage 条件允许时）
  → 首轮仍放不下：标记 RS_Split，延后重新入队
  → 下一阶段 trySplit
  → 对已到末段/不可 spill 的困难范围尝试 last-chance recoloring
  → 正常可 spill 的范围，最后交 spiller
```

首轮延后为切分收集更完整的压力信息。长区间先处理时，较小区间可能尚未占用资源；立即切分只能依据当前部分安排。让其他区间先进入分配结果，再决定切分边界，可以利用更多实际冲突信息。

源码注释说明，第一轮延后 split/spill，使第二轮能够利用更完整的 interference 信息。局部策略、阶段和新范围的细节影响实际顺序，上图是主骨架而非逐分支替代源码。

**last-chance recoloring 也不是每次普通失败都立刻执行的万能一步。** 本版本在这里有 stage/unspillable 条件；它用于有限回溯式挪动一组颜色，仍有深度和搜索范围限制。

### 切分的热区驻留与边界转换 {#切分从整个人留在房间变成按使用场景留不同房间}

假设值 v 在入口定义，热循环多次读取，之后冷错误路径也读取：

```text
entry → hot loop → exit
          |
       cold error
```

一个贯穿全图的 LI 若找不到始终空闲的寄存器，不应立即把热循环每次 use 都变成 reload。可形成：

```text
入口 / 冷区：栈或其他片段
热循环区域：v_hot 长驻一个寄存器
区域边界：load / store / COPY
```

边界代价执行一次或很少次，换来热区避免大量访存。这是 Greedy 的核心观察：**资源紧缺具有时间与路径局部性，整段 spill 过于粗糙。**

`trySplit` 会按具体情形尝试 local splitting、region/global splitting、其他适用方案；相关函数如 `tryLocalSplit`、`tryRegionSplit` 可在 `RegAllocGreedy.cpp` 检索。具体编辑由 SplitKit 的 SplitAnalysis / SplitEditor 等完成。

- 局部切分沿使用点和冲突空隙寻找适合的片段。
- 区域切分尝试围绕特定物理寄存器保留一个可获益区域，其余部分成为别的范围。
- 新范围重新计算权重、约束并进入工作队列。

切分会制造 COPY 与边界转换；若收益不能超过它们，切分并不划算。不能把“切得越碎越好”当成策略。

### SpillPlacement 的驻留成本模型 {#spillplacement这里竟然有-hopfield-网络}

`llvm-project/llvm/lib/CodeGen/SpillPlacement.cpp` 的文件头说明了基于 Hopfield 网络的组合优化模型：

- CFG 的 edge bundle 对应一个节点。
- 节点状态表示该边束上更偏向 register 还是 stack；实现还保留 undecided 状态。
- 必须/偏好寄存器或栈的块给节点 bias，按块频率加权。
- transparent blocks 对两端状态施加连接：两端驻留状态不同，可能需要转换。
- 通过迭代更新，降低表示 spill 执行频率的能量函数。

这里的 Hopfield 网络是**确定性组合优化模型**，而非训练得到的预测器。其能量作为 Lyapunov 函数，在更新时不增加，并收敛到局部最小；文件标题虽然包含 Optimal，注释仍明确限制为可能的局部最小，不能据此宣称全局最优。

数学上可理解为两类代价的折中：某块不用寄存器会多执行多少 reload，邻接驻留状态改变会多执行多少转换。热边上频繁切换代价大，因而倾向在一整个热区域保持同一种状态。

`llvm-project/llvm/lib/CodeGen/EdgeBundles.cpp` 与 `llvm-project/llvm/lib/CodeGen/SplitKit.cpp` 说明了边界约束如何参与选择：bundle 将需要一致处理的边界组织成节点，因此不能对 CFG 每条边独立决定驻留状态。

### Spill 与 rematerialization 的最终落地

`InlineSpiller.cpp` 不只负责插 `store` 和 `load`：它还可能折叠 memory operand、消除冗余、追踪可重算定义、合并某些片段，并维护 LiveIntervals 与调试位置。

一个常量 materialization 值若被 spill，某次 use 附近重新生成常量可能比 stack load 便宜。若它依赖其他已经不活跃的输入或不安全操作，则不能任意重算。

reload 形成的片段往往已经很短，无法通过反复 spill 无限制缩小；某些范围成为 unspillable，需要结合严格约束与有限 recoloring 处理。不相容的 inline asm 约束仍可能使分配无解，LLVM 会报告错误，Greedy 并不保证任意约束都可满足。

最终 VirtRegRewriter 根据映射改写 operand，后续栈帧/序言尾声处理把栈槽和保存恢复变成真实目标指令。分配器作出的栈槽选择，不等于那一刻已经确定了最终栈偏移。

### 驱逐与重新分配的简化示例

**教学简化：** 只有 R0/R1，无别名和固定限制。

```text
L: 很长，全局值，只在入口、出口与冷块少量使用
H: 热循环里高频使用，中等长度
S: 某个局部短值
```

可能过程：

1. 长范围 L 先被安排到 R0；别的范围占 R1。
2. H 入队，空闲检查失败；H spill weight 高。
3. 若符合驱逐策略，H 驱逐 L，得到 R0；L 重新入队。
4. L 不一定马上 spill：可能 R1 某区域空闲，或被切成冷区/出口短片段。
5. 热循环维持 H 在寄存器；只在冷区或边界为 L 做转换。

传统最简 linear scan 不采用同样的全局重新分配过程：它按 start 单调走、依据当前 active 集合处理。增强型 linear scan 也可以通过 splitting 改善，但 Greedy 的工作顺序和可修正分配从一开始就是主结构。

这不是声称 LLVM 对该抽象例子一定走这个路径；真实 cascade、hints、stage、成本和物理约束可改变决定。例子用来解释 **“先分配≠永远保住寄存器”**。

### 分配质量与编译成本的取舍

| 观察 | 实现对应 | 解决的问题 |
|---|---|---|
| 长范围难安排 | global long→short 优先级 | 提前发现大压力源 |
| 局部区间结构简单 | 部分 local 线性指令顺序 | 利用便宜的区间着色性质 |
| 初始选择可能需要调整 | eviction、有限 recoloring | 为后续高价值范围调整已有分配 |
| 压力并非全程都高 | local/region splitting | 保住热区，避免整段 spill |
| 冷热代价差很多 | 块频率、spill weight、SpillPlacement | 优化动态成本而非静态条数 |
| copy 和 ABI 也有成本 | hints、CSR 首次成本 | 降低搬运及保存恢复 |
| 反复调整可能循环 | cascade、stage、预算 | 保障进展与编译时间 |

LLVM Greedy 基于活跃区间和物理资源冲突查询，以迭代修正的启发式组织全局分配。局部顺序策略、驱逐和切分改善候选选择，stage、cascade 与预算则限制调整成本。它既不同于传统线性扫描，也不提供全局最优保证。
