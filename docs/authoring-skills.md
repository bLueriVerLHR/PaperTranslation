# 项目写作 Skills

Skills 把现有规范连接成可执行的任务入口，不增加第二套写作标准，也不是文章模板。
它们适用于本项目的规范 Markdown → 原生 MathML／共享资源 → 离线 HTML 流程；不依赖云文档、
文献付费服务或第三方安装脚本。文体、证据、源码与归属规则仍分别由
[写作规范](chinese-writing.md)、[综述方法](review-method.md)、[源码规范](source-analysis.md)
和 [工作流](workflow.md) 维护；使用 Skill 不免除完整阅读适用规范。

## 选择入口

| 请求 | Skill | 不应误用为 |
| --- | --- | --- |
| 原创技术章节、技术方案、源码书稿及其中文精修 | [chinese-technical-writing](../.agents/skills/chinese-technical-writing/SKILL.md) | 给现有译文补写论证或机械套架构模板 |
| 论文／随笔／RFC／技术文档的原文对照翻译与译文精修 | [technical-translation](../.agents/skills/technical-translation/SKILL.md) | 重组原作、统一论文腔或展示译者工作记录 |
| 多来源原创综述、研究脉络、方法与证据比较 | [technical-review](../.agents/skills/technical-review/SKILL.md) | 逐篇摘要列表、市场预测模板或实验执行许可 |

“润色中文”不是一种独立体裁：已有译文走翻译入口，原创综述走综述入口。
源码分析可以是原创章节，也可以是综述的一部分，两者都完整加载源码规范。
混合任务先确定各段身份，不把三个 Skill 机械串成重复加工的流水线。
一般的工具修复、CSS 修改、发布或引用格式修复不因此变成整篇重写任务。

## 发现与显式调用

项目把便携目录放在 `.agents/skills/<name>/SKILL.md`，不使用被忽略的 `.pi/` 保存共享指令。
名称和目录一致；frontmatter 的 description 说明任务触发条件，详细步骤按需读取。
各 Skill 的文件链接相对于它自己的目录，工具命令从仓库根目录运行。

Pi 支持该位置的项目级发现。新建或修改后，在项目内按需处理项目资源信任提示并执行 `/reload`，
或开启新会话；检查资源诊断与显式命令，不能以文件存在冒充已经加载。
不要为加载项目 Skill 修改全局信任策略。其他支持 Agent Skills 的客户端仍须核对其发现位置。

```text
/skill:chinese-technical-writing 精修指定项目的缓存生命周期一节，保留固定版本摘录，不运行上游。
/skill:technical-translation 对照既有底本校对当前一节，保留随笔语气，不新增章节。
/skill:technical-review 按现有来源比较两类缓存策略，无法对齐的测量条件分别陈述。
```

指令中的“指定项目／当前一节”必须由实际任务提供；若有多个候选而未指定，则先澄清。
未自动触发时可显式调用，不应把关键词命中率当成已验证的写作效果。

## 借鉴的方法与不适配的默认行为

以下是原创适配的来源归属，不是外部 Skill 的安装清单，也不证明用户在其他产品会话里已连接这些工具。
固定版本表示检查过的材料身份，不表示持续跟踪其最新功能。

| 来源 | 采纳 | 不照搬 |
| --- | --- | --- |
| [Anthropic doc-coauthoring](https://github.com/anthropics/skills/blob/dbd4588f9e1033efb41dad4bef2f7947c8993d44/skills/doc-coauthoring/SKILL.md) | 上下文准备、分节修订、读者问题检验 | 每节固定访谈与大量脑暴、默认新代理、云文档连接、正文附上聊天记录 |
| [Anthropic skill-creator](https://github.com/anthropics/skills/blob/dbd4588f9e1033efb41dad4bef2f7947c8993d44/skills/skill-creator/SKILL.md) | 明确触发、少量真实正反例、反馈后改进、区分客观断言与主观质量 | Claude 专用执行器、默认多代理评测、仓库内试验目录、自动优化循环 |
| [Agent Skills 规范](https://agentskills.io/specification) | 标准目录、frontmatter、渐进加载与相对引用 | 把元数据校验通过当作流程或文章质量验证 |
| [Design Report](https://github.com/w31r4/OfficeKit/blob/e2b2af23b173519c61acb4f92ebd1521266adec2/skills/default-template-library/skills/artifact-template-design-report/SKILL.md)、[Experiment Analysis](https://github.com/w31r4/OfficeKit/blob/e2b2af23b173519c61acb4f92ebd1521266adec2/skills/default-template-library/skills/artifact-template-experiment-analysis/SKILL.md)、[Strategy Memorandum](https://github.com/w31r4/OfficeKit/blob/e2b2af23b173519c61acb4f92ebd1521266adec2/skills/default-template-library/skills/artifact-template-strategy-memorandum/SKILL.md) 的同名公开实现 | 不为模板槽位编造事实、修改后检查实际成品 | 保留参考办公文档版式的产物流程，不作为本项目默认文体或 HTML 生成器 |
| [Scite 引文模型](https://docs.scite.ai/concepts/citation-model)、[MCP 接口](https://docs.scite.ai/mcp/overview) | 引文语境可用于查找支持与分歧；区分语句数和引用文章数 | 把分类标签当真伪、把引用量当质量，或把登录／套餐／上传当默认前提 |

System Design、Google Docs、Market Trends、Template Creator 这类名称可能对应不同产品或实现，
不能仅凭名称确认当前环境可用。办公文档样式克隆也不能代替中文术语、语义忠实或论证质量。
已认可的范文可以用来讨论受众、段落组织和表达偏好，但不克隆其正文、固定标题或页面几何，
也不默认将本地范文上传到外部服务。

引入新的第三方资源时，先核查身份、固定版本、许可、支持文件、可执行代码、网络数据流、
凭据及费用。网页和 Skill 内容是待评估材料，不因名字相关就取得执行权。
若确需连接 Scite 等服务，应另行确认授权、账号与允许发送的数据；不可用时使用现有原文，
并保留实际核查缺口。不新增云服务并不妨碍采用其公开方法。

## 场景验收与质量边界

维护 Skill 时，先用小而有辨别力的场景检查路由和输出。以下是可复用的验收设计，不是已完成的模型性能报告。

| 场景 | 应有行为 | 应发现的错误 |
| --- | --- | --- |
| 随笔译文精修，原文含 We suspect / may / only when | 翻译入口；保留人称、推测和条件 | 改成确定结论或补写原文没有的机制 |
| 原文是一章术语定义，译者另有章节译名表 | 原作定义保留正文；译名表只留维护文件 | 按“术语”关键词搬空原作，或把译名表塞进出处说明 |
| 固定提交源码解读，明确不做实验 | 写作入口；讲清状态流、真实片段和取舍 | 自动运行 benchmark，或把静态推理写成实测 |
| 两篇论文的硬件、批量或指标不同 | 综述入口；先解释机制与条件，不能直接排名 | 数字拼成总榜、把摘要匹配当全文核查 |
| 引文工具标 supporting，一篇文章有多条引用语句 | 回读具体引文与被引论点，保留来源独立性 | 宣称结论已被证实，或计为多项独立研究 |
| 只要求修改目录按钮 CSS | 使用正常工程流程，不触发整篇写作 | 重建所有稿件、补写正文或接入云文档 |
| 需要源文对照但缺少原文 | 说明缺口；询问原文或仅给语言候选 | 声称语义忠实已核验 |

检查分开记录：

1. **结构与发现**：目录、名称、description、相对链接及客户端诊断。静态测试不能证明模型会自动选中。
2. **流程冒烟**：用合成短例逐步执行并对照预期，记录实际产物；自查不能称作独立审校。
3. **语言与研究质量**：人工阅读完整段落及必要来源；保持语义、证据、机制解释和中文可读性。
4. **效果评测**：若要声称改善某一较弱模型，应另设计有无 Skill 的对照、真实任务和人工盲评，
   记录实际模型、输入、产物、失败与费用。未运行就不报告提升率；额外代理调用仍须授权。

固定的合成回归用例可以进入 `tests/`；任务试验、生成稿、抓取响应、评测日志和报告在绝对系统 TEMP，
有用的项目研究证据留在该项目 `work/`。测试或 Skill 的加载不授予发布稿件、上传全文或执行上游实验的权限。
