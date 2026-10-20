# Paper Translation Library

保存阅读页源文档、页面组成与写作规范的仓库。源文档是 Markdown 与 SVG，页面组成是模板、
样式与脚本；渲染、测试与发布都在仓库之外执行，产物不进入此仓库。

## 仓库里有什么

```text
papers/<slug>/     每篇阅读页的源文档（见下）
src/               页面组成：模板、样式、脚本
docs/              写作规范、方法、阅读页规则、流水线接口
.agents/skills/    写作、翻译、综述三个可复用入口
NOTICE.md LICENSE  流水线 MIT 许可与第三方权利边界
```

`papers/<slug>/` 的结构：

| 文件 | 作用 |
|---|---|
| `meta.json` | 标题、副标题、作者、体裁、章节顺序、发布日期、导出标记 |
| `content/*.md` | 正文，按 `meta.json` 的章节顺序排列，公式为原生 MathML |
| `reader.json` | 引用表、引用样式、是否显示术语表 |
| `glossary.md` | 可见术语对照表 |
| `reader-meta.md` | 出处、许可与阅读限制说明 |
| `assets/figures/` | 插图（SVG、PNG 等真实文件，按相对路径引用） |
| `source-map.md` | 断言到来源的对应，便于复核 |
| `README.md` | 该篇的维护说明 |

## 如何把源文档渲染成页面

渲染器在仓库之外的临时流水线里（见 [docs/pipeline.md](docs/pipeline.md)）。它只依赖
Markdown 与语法高亮两个库，离线完成 Markdown、MathML、SVG 到 HTML 的转换：

```powershell
$PIPE = "$env:TEMP\PaperTranslationWork\pipeline"
$OUT  = "$env:TEMP\PaperTranslationWork\dist"
python "$PIPE\tools\dev.py" run -- "$PIPE\tools\render.py" `
    --work "<仓库路径>\papers\<slug>" --out "$OUT\<slug>" --library-root $OUT
```

输出目录里是 `index.html`、插图与共享运行时，可以直接用 `file://` 打开。<slug> 的
`meta.json` 与 `content/` 决定章节顺序，缺章节或多章节都会在渲染前报错。

## 发布

站点由 `pages-content` 分支直接发布（GitHub Pages 的分支部署，Source 设为该分支的根目录）。
渲染结果先在本地校验再推送，流程与校验项见 [docs/pipeline.md](docs/pipeline.md)。

`pages-content` 只含渲染结果与字体许可声明，不含源文档、参考材料或执行工具。翻译与其裁图
保留原作者权利，不适用本仓库的 MIT 许可。

## 边界

- 仓库保存源文档、页面组成与技能文档；参考材料（抽取的第三方文本、PDF 副本）、构建产物与
  执行工具放在外部临时目录。
- 正文改动落在 `papers/<slug>/content/`，呈现改动落在 `src/`，写作要求落在 `docs/`。
- 翻译类篇目只在本地渲染；公开分支只包含明确批准的自撰综述与源码解读。
