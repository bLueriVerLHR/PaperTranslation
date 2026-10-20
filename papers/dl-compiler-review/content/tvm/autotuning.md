## 自动调优：把调度选择变成可测量的搜索 {#tvm-autotuning}

手工调度需要同时掌握算法、硬件与一长串原语的副作用，于是 TVM 把这部分变成搜索：生成候选调度、编译并测量、按测量结果决定下一步试什么。入口 `tune_tasks` 的签名就是这套分工的清单（`python/tvm/s_tir/meta_schedule/tune.py:29`）：

```python
# 编者定位：repos/tvm · 2bb1a553be19 · python/tvm/s_tir/meta_schedule/tune.py:29-45（签名节选）
def tune_tasks(
    *,
    tasks: list[TuneContext],
    task_weights: list[float],
    work_dir: str,
    max_trials_global: int,
    max_trials_per_task: int | None = None,
    num_trials_per_iter: int = 64,
    builder: Builder.BuilderType = "local",
    runner: Runner.RunnerType = "local",
    database: Database.DatabaseType = "json",
    cost_model: CostModel.CostModelType = "xgb",
    measure_callbacks: MeasureCallback.CallbackListType = "default",
    task_scheduler: TaskScheduler.TaskSchedulerType = "gradient",
    module_equality: str = "structural",
    post_optimization: bool | None = False,
) -> Database:
```

四类角色在这里直接可见。`builder` 与 `runner` 负责把候选调度编译出来并真实运行，默认都在本机按核数并行；`database` 存放测量记录；`cost_model` 默认取 `"xgb"`，用提取出的特征训练一个梯度提升模型，预测尚未测量的候选值多少代价，从而把真实测量留给更值得试的那部分候选；`measure_callbacks` 决定一次测量结束后要做什么。

生成候选、真实测量、再用学到的模型筛选，这套组合在 Ansor 中提出并评估（Zheng et al. 2020）；本节说明的是这个提交里各角色如何分工。

搜索空间与搜索策略各自有实现清单。空间生成器位于 `src/s_tir/meta_schedule/space_generator/`（`post_order_apply.cc`、`schedule_fn.cc`、`space_generator_union.cc`），搜索策略位于 `search_strategy/`（`evolutionary_search.cc`、`replay_func.cc`、`replay_trace.cc`）。这些实现的内部算法本章不做推测；能确定的是分工本身——空间负责“有哪些候选”，策略负责“下一批试哪些”。

把有限的试验次数分给多个任务，是另一层决策。`max_trials_global`、`max_trials_per_task` 与 `num_trials_per_iter` 给出预算与批大小，`task_scheduler` 决定这些批次落在哪个任务上，其默认实现名为 `"gradient"`，同目录下另有 `round_robin.cc`。参数 `task_weights` 是调用方给出的权重，与预算一起决定搜索的注意力分配。

`module_equality` 这个参数容易被忽略，它决定一条测量记录能否被另一个模块复用，因此直接决定调优投入的可复用范围。默认 `"structural"` 用结构等价与哈希；`"ignore-tensor"` 在等价与哈希时忽略张量原始数据；`"anchor-block"` 只在从模块中抽出的锚块上做等价与哈希（`python/tvm/s_tir/meta_schedule/tune.py:74-84`）。判定过松会把不适用的记录当成可用，判定过严则同一个算子换一个上游形状就要重测一遍。`post_optimization` 打开后在已选出的方案附近再做一轮开发式搜索，文档把它称为 Droplet Search（同文件 `:86`）。

这套框架的代价不在生成的代码里，而在编译与测量的次数上：每个候选都要编译、装载、运行、计时，因此调优时间与硬件占用是实打实的开支；代价模型只能减少测量次数，不能免除测量。搜索产物存放在数据库里，同一目标与同类模块可以复用，这也是 `module_equality` 值得单独说明的原因。
