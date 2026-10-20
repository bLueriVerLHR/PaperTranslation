## 自动调优：几个旋钮与一份缓存 {#triton-autotune}

Triton 也做自动调优，规模比 TVM 小得多。`python/triton/runtime/autotuner.py:19` 的 `Autotuner` 接收候选配置列表与一组键参数名（`:21`），候选的字段就是全部的搜索维度：

```python
# 编者定位：repos/triton · ebdd5b6b4856 · python/triton/runtime/autotuner.py:366
    def __init__(self, kwargs, num_warps=4, num_stages=3, num_ctas=1, maxnreg=None, pre_hook=None, post_hook=None, ir_override=None):
```

可调的量是四类：warp 数、流水级数、CTA 数、寄存器上限。调度本身不在候选集里，它由后端按固定管线决定，候选只影响后端做决策时的输入参数。把这一点与 TVM 那份充满 `compute_at`、`cache_read_write`、`tensorize` 的搜索空间对照，两个项目对“谁来调度”给出了不同答案。

搜索过程由键决定复用范围。每次调用从被标注为键的参数取值，再把所有张量参数的 dtype 追加进去，拼成一个元组（`:237-242`）；该元组命中缓存就直接采用上次的优胜配置。未命中时先按当前参数剪掉不兼容的候选（`prune_configs`，`:299`），再逐个测量：`_bench` 对每个候选真实运行并计时（`:148`），取最小值记入缓存（`:253-260`）。剪枝后只剩一个候选时走一条捷径——不测量，直接采用（`:247-250`）。

真实测量在这里同样不可避免：每个候选都要编译并在设备上跑一遍，调优时间与设备占用是实打实的成本。可选项 `cache_results` 打开后会把结果落到磁盘（`check_disk_cache`，`:190`），使跨进程的重复启动不必重测。键的设计因此变得关键：键里的参数少了，不同形状会共用一个优胜配置；键里的参数多了，每次新形状都要重新测一遍。这套取舍在 Triton 里以 dtype 自动入键的方式被固定下来一部分：同形状而不同类型的张量不会被当成同一个场景。

不用自动调优时，`Heuristics`（`:493`）按给定取值直接指定配置。两条路都不改变编译管线，改变的只是管线入口处的几个参数。
