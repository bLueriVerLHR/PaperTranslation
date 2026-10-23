# 维护说明（不进入阅读页）

## 身份与边界

- slug：`ml-sre-ha-review`；类型：原创综述（`kind: review`）。
- 主题：机器学习系统的站点可靠性工程与高可用，重点是容器与编排，以及与 AI 负载相关的存储、网络、混算力与可观测性。
- 正文只放技术论述。来源、权利与阅读限制在 `reader-meta.md`；可见术语在 `glossary.md`；断言到来源的对应在 `source-map.md`；本文件只记维护信息，不进入阅读页。
- 本稿与仓库内其他阅读页相互独立：不引用其他项目页面，需要某个结论时在本文内把结论与适用条件写全。

## 重建

```powershell
python "$env:TEMP\PaperTranslationWork\pipeline\tools\dev.py" run -- "$env:TEMP\PaperTranslationWork\pipeline\tools\render.py" --work "papers\ml-sre-ha-review" --out "$env:TEMP\PaperTranslationWork\dist\ml-sre-ha-review" --library-root "$env:TEMP\PaperTranslationWork\dist"
```

规范源稿位于本仓库 `papers/ml-sre-ha-review/`；工具、输出和第三方参考资料位于外部数据根。具体接口以 `docs/pipeline.md` 为准，重建不执行发布。

## 章节与写作批次

| 批次 | 章节 | 状态 |
|---|---|---|
| 1 | 01–03 可靠性对象、错误预算、容量与排队 | 完成 |
| 2 | 04–06 故障处理、容器机制、控制回路与探针 | 完成 |
| 3 | 07–09 调度、异构算力、副本与共识 | 完成 |
| 4 | 10–12 存储、网络故障域、并池与混部 | 完成 |
| 5 | 13–14 可观测性、变更与交付 | 完成 |
| 6 | 15 案例：Prometheus 集群与硬件质量 | 完成 |

## 材料归属

- `content/`：本文正文，按主题顺序。
- 外部数据根的 `dist/ml-sre-ha-review/work/reference/`：从外部原件抽取的页面文本与仓库文档快照，仅供核对，不作为正文转载。
  - `ha-book-*`：系统设计书按主题切分的页面文本（含页码标记）。
  - `mysql-book-*`：复制与故障切换章节的页面文本。
  - `sre-book-*`：Google SRE 书的第 3–4 章与第 6、15 章页面文本。
  - `paper-*`：Borg、MuxFlow、SpotServe、Mooncake 的首批页面。
  - `3fs-design-notes.md`、`3fs-readme.md`：固定提交的仓库文档。
  - 两篇 Meta 工程博客按链接、作者和日期引用；正文区分报告值、条件换算与教学算例，不把归一化假设或未定义指标当作实测结论。
- 外部原件保存在数据根的 `sources/`，不复制进仓库。

## 未决项

- XID、静默数据损坏与慢节点缺少可对齐的故障率统计；第 15 章引用的 66% 是 Llama 3 训练中断的硬件来源构成，不是 SDC 占比或器件故障概率。
- 国产算力与异构设备的编排差异只按设备抽象层讨论，未核对具体厂商插件的实现。
