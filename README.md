# Paper Translation Library

文档、写作规范与阅读页渲染资源的仓库。成稿的正文、源 PDF、参考材料与执行工具都在仓库之外，
因此一次克隆只能得到规范与呈现层，不能重建页面。

## 仓库里有什么

```text
docs/                写作规范、方法、阅读页规则、流水线接口（见 docs/README.md）
.agents/skills/      写作、翻译、综述三个可复用入口
src/                 阅读页模板、样式与脚本（页面呈现的唯一来源）
NOTICE.md/LICENSE    流水线 MIT 许可与第三方权利边界
```

`src/` 是页面呈现的权威来源：版式、术语表与出处说明的样式、原生 MathML 的排版、问答页的交互
与无脚本回退都在这里。修改样式只改 `src/`，重新发布时由本地流水线把运行时组合进快照。

## 仓库外有什么

| 位置 | 内容 |
|---|---|
| `%TEMP%\PaperTranslationWork\pipeline\` | Python 工具、测试、`pyproject.toml` 与依赖锁定 |
| `%TEMP%\PaperTranslationWork\dist\` | 各项目的正文、图、术语表与已构建的阅读页 |
| `%TEMP%\PaperTranslationWork\repos\` | 源码解读所用的固定提交检出 |
| `%TEMP%\PaperTranslationWork\sources\` | 外部原件（论文与书籍 PDF） |

流水线目录用目录联接把仓库的 `src/` 与数据根的 `dist/`、`repos/` 挂进来，所以工具看到的是同一份
数据，仓库不需要知道它们的位置。TEMP 会被系统清理，这些内容没有第二份副本。

常用命令（PowerShell，先设一次 `$PIPE`）：

```powershell
$PIPE = "$env:TEMP\PaperTranslationWork\pipeline"
python "$PIPE\tools\dev.py" setup --pages
python "$PIPE\tools\dev.py" run -- "$PIPE\dist\<slug>\work\rebuild.py"
python "$PIPE\tools\dev.py" run -- "$PIPE\tools\manuscript_check.py" --paper <slug>
```

## 发布

站点由 `pages-content` 分支直接发布（GitHub Pages 的分支部署，Source 设为该分支的根目录），
不再经过 Actions：仓库里没有部署脚本，也没有工作流。发布流程是本地导出、本地校验、推送内容
分支，具体步骤与校验项见 [docs/pipeline.md](docs/pipeline.md)。

`pages-content` 只含渲染结果与字体许可声明，不含 `work/`、源 PDF、抽取数据或本仓库的脚本。
翻译与其裁图保留原作者权利，不适用本仓库的 MIT 许可。

## 边界

- 仓库不接收 Python 脚本、系统专用配置或数据文件；它们属于流水线目录。
- 翻译类项目的阅读页仅在本地保留；公开快照只包含明确批准的自撰综述与源码解读。
- 事实与写作要求以 docs 为准；当前目录结构以 [docs/pipeline.md](docs/pipeline.md) 为准。
