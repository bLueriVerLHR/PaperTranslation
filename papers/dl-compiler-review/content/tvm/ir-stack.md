## 表示层：一个 IRModule，两类函数 {#tvm-ir-stack}

TVM 把整条编译链的输入输出压在同一个容器上。仓库自带的架构文档用两句话交代了容器里装什么：`IRModule` 含 `relax.Function` 与 `tirx::PrimFunc`（`docs/arch/index.rst:187`）。前者是高层函数式表示，对应整个模型或其子图，支持控制流与复杂数据结构；后者是低层程序表示，含循环嵌套选择、多维访存、线程绑定以及向量与张量指令，通常对应模型中一个层。

两类函数的连接方式决定了图级优化能做什么。relax 算子被降为 `tirx::PrimFunc` 或 `TVM PackedFunc`，调用点在图上表现为 `R.call_tir` 与 `R.call_dps_packed`（`docs/arch/index.rst:70-72`）。图级函数保留对低层函数的调用，自身不展开成循环。于是算子边界同时承担两件事：融合决策的落点是它，后端分派（例如把整个算子交给外部库）的落点也是它。把边界留在图上，图级变换才有东西可以搬动。

在这个提交上，张量层有两套表示并存：

| 目录 | 承载 |
|---|---|
| `src/s_tir` | 调度体系（`schedule`）、变换（`transform`）、自动调优（`meta_schedule`） |
| `src/tirx` | 正在成形的张量 IR：`ir`、`op`、`analysis`、`script`、`transform`，含 `RegionStmt`、tile 原语与执行作用域（`include/tvm/tirx/{stmt.h,exec_scope.h,exec_context.h,tile_primitive.h}`） |
| `src/te`、`src/topi` | 张量表达式层与算子库 |

这个提交的信息写着 `[REFACTOR][TIRx] Add RegionStmt and migrate thread launches (#20555)`，迁移尚在进行：仓库根下已经没有 `src/tir` 与 `src/meta_schedule`，调度与自动调优现在位于 `src/s_tir/meta_schedule`。按旧文档或旧教程里 `src/tir/...` 的路径检索，在这个提交上会落空，路径要改成 `s_tir`。

文档里还留了一条区分（`docs/arch/index.rst:192`）：`relax/transform` 与 `tirx/transform` 是确定性的规则式变换。把这句话与旁边的自动调优放在一起看，TVM 对两类决策的分工就清楚了——保序改写交给固定管线，性能选择交给可测量、可重复的搜索。下一节从调度开始，说明搜索在搜什么。
