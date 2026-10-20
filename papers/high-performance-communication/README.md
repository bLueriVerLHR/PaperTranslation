# 高性能通信与数据移动：维护入口

原创综述，身份见 `meta.json`，术语唯一源稿为 `glossary.md`；17 个有序章节位于 `content/`，来源定位与研读边界见 `source-map.md`。`reference/` 是本地研究资料，不进入公开快照。PDF 只读取外部原件，未复制入项目。

## 结构

全书按“数据移动”组织，分四篇：

| 篇 | 章节 | 内容 |
|---|---|---|
| 数据移动的账本 | 01–02 | 算术强度与机器平衡；各层速率、延迟与共享方式 |
| 节点内移动 | 03–06 | DRAM/HBM 的物理约束；PCIe 与 CXL；DMA 与队列；量化、稀疏与压缩 |
| 节点间移动 | 07–15 | 集合算子语义与算法；分层与拓扑；训练依赖；库；内核路径；RDMA；拥塞与 DCQCN |
| 归因 | 16 | 指标口径与系统归因 |

主题子稿位于 `content/algorithms/`、`hierarchy/`、`libraries/`、`hccl/` 与 `dcqcn/`，父稿用共享 include 接口控制顺序。`coverage-map.md` 对应 xCCL 各节与 HCCL 文档主题；它记录正文覆盖，不代表被引全部论文或上游实现均已核验。

## 图与术语

`figures.py` 生成原创 SVG 到 `assets/figures/`，编号与章节顺序一致：01–10 属于前两篇（数据移动与节点内），11–33 属于节点间与归因。图中不含论文裁图、书页或第二套 CSS/JS。图示的 rank、分块、求和结果、速率与正文同步修改——改动正文数值时先改 `figures.py` 再重建。

术语唯一来源为 `glossary.md`；新增术语（例如 DRAM 的 rank 与通信域的 rank 同名不同义）必须在该表分列后写入正文。

## 来源

- 论文与外部原件：`reference/*.txt` 是 PDF 文本摘录，原件只读外部路径（见 `source-map.md` 的身份记录）。
- 官方文档：`reference/technical-docs/` 保存访问时的 HTML/PDF 快照与 `index.json`（id、url、sha256、bytes、fetched_at）。新增官方来源时用同一格式登记，哈希只标识字节，不证明算法正确。

## 重建

```powershell
. .\tools\dev-env.ps1
& $Python dist\high-performance-communication\work\figures.py
& $Python dist\high-performance-communication\work\rebuild.py
```

重建只使用共享阅读器，不执行上游库或任何硬件测试，不自动发布。`--dist` 可指定 TEMP 试验输出。公开快照仅包含此项目原创页面与 SVG，发布按 `docs/pages.md` 的 selected-project 流程，保持其他既有读者不变。
