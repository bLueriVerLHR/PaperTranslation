# 阅读页与渲染

本文合并了阅读页的呈现规则：HTML 优先的版式、可见术语与出处说明、支持的 Markdown 语义、问答页面的交互与无脚本回退。表现层由共享模板与样式负责，不逐篇手写。构建与发布命令在仓库之外，见 [pipeline.md](pipeline.md)。


<!-- merged from reader.md -->

The reader is a learning aid, not a publisher's edition. Attribution and a learning-use
notice do not grant permission to distribute translations or extracted figures. Verify the
original license and any necessary permission before public sharing; never describe a
personal-use disclaimer as a legal guarantee.

## HTML-first layout guidance

HTML is the delivery target; a browser print stylesheet is a fallback, not a requirement to
produce PDF editions. Screen layout must not inherit A4 dimensions, millimetre-based page
widths or simulated paper margins. Screen articles use the available viewport width with
responsive side gutters, not a fixed `rem`, character-count or paper-size content ceiling.
Paragraphs, headings, title notes and equations share that fluid content area. Chapter
navigation is closed by default at every screen width and opens from the toolbar; there is
no permanent side rail or duplicated outline. Use only source syntax actually supported by
the builder; a design recommendation is not a new directive.

- Let article content expand with the screen instead of centering a fixed-width reading
  strip inside a larger shell. Keep side gutters responsive and bounded; do not bound the
  article width itself. Phone safe-area padding remains available. Dialogs and the library
  card grid are separate UI regions and may retain their own size constraints.
- Collapse to one reading column on phones. Navigation must not consume the narrow content
  area or cover headings. Keep touch targets usable and preserve start-aligned Chinese/Latin
  prose instead of adding justification, forced line breaks or global text shrinking.
- Contain horizontal overflow in the code, table or equation that needs it, not the whole
  page. A scrollable region needs a visible affordance and keyboard access; a clipped right
  edge or a hover-only explanation is not a mobile fallback.
- Keep layout decisions in the shared runtime. Manuscripts supply structure and content, not
  local font sizes, fixed widths or copies of reader CSS/JS. Do not rewrite source paragraphs,
  mathematics or stable anchors just to match one screenshot.

## Markdown sources, generated HTML

Author new Markdown-first projects using the supported [document syntax](reader.md), not
hand-written layout HTML. An explicit Pandoc profile converts semantic figures, footnotes,
tables and math at build time; it uses this same reader/template and shared runtime. Existing
projects retain their parser unless deliberately migrated. The Pandoc path does not infer
that an original author's headings should be relocated: header notes are explicit maintenance
inputs, while original body material stays in source order. The compatibility extraction rules
below describe the Python-Markdown path, not new author instructions.

## One shared reader

`src/styles/reader.css` owns typography for papers, source analyses and surveys. Mixed
Chinese/English prose uses start alignment, normal letter/word spacing and no justification,
including forced line breaks. Do not append project-specific font, fixed-size or alignment
overrides that disappear when the Pages exporter installs the shared stylesheet. Reading-size
controls use `--reading-scale`; code and ASCII diagrams remain monospaced.

The script's modal service is shared by the library, article TOC, citation details and
Markdown footnotes. Footnote links retain their native target/backlink fallback, and complete
note text remains in the saved document; a dialog never becomes its only copy. Cards
are centered in the native top layer, scroll internally and lock the background. Backdrop,
close button and Escape restore the opener and original scroll position. Tab and Shift+Tab
cycle within the card. Choosing a TOC heading closes the card *before* scrolling to and
focusing that heading; it does not restore the old position over the intended destination.

The TOC uses one canonical nested list, moved into its dialog rather than cloned for a second
navigation. Major chapters use larger, stronger labels; nested subjects use smaller text,
indentation and a quiet branch rule. Sibling entries within a subject are compact, while
chapter groups have an extra gap. Avoid equal large margins on every row or a global font
reduction. Touch pointers retain usable targets; long outlines scroll only in the opened
panel, with a subtle visible scrollbar. Native-details and dialog outlines share these styles.
Current-location highlighting updates only the previous/new entry and retains `aria-current`.

Without JavaScript or native dialog support, the original details/TOC tree remains usable.
The same scripts work with `file://`. Print hides interactive cards and overrides background
scroll locking so an open modal cannot clip the printed article.

## Opt-in question/answer chapters

Explicit question banks can switch between complete paired reading and question-only
self-testing with answer cards. They also offer topic-scoped random practice: the reader
chooses themes derived from the bank's own heading levels, draws one question, and keeps
its answer folded until asked. They reuse the shared modal, preserve no-JS/no-dialog
readability and print all canonical answers. Only marked banks are enhanced; ordinary
chapters are unchanged. See [question-bank authoring and interaction](reader.md) for
the HTML/Markdown contract, `data-level` metadata, search and random-practice semantics,
manifest inventory and validation scope.

## Native mathematics

Keep MathML's native `math` layout and text baseline. Inline expressions must not be
`inline-block` scroll boxes. Use a platform MATH-table font independently of prose fonts;
never download or redistribute proprietary system fonts. Ordinary inline math remains in
prose. Display equations and expressions wider than the reading column use a padded,
keyboard-accessible block scroller; resize and reading-scale changes recompute that layout
without modifying the MathML expression. Without scripts, native MathML width caps keep
oversized expressions local without turning ordinary inline symbols into inline-blocks.
Print restores visible overflow.

For authoring and typography changes:

- Keep variables, operators, subscripts, fractions, delimiters and upright function names
  semantically correct. Use aligned rows only for a meaningful derivation or mathematical
  grouping, not as a page-layout table. Do not insert arbitrary spacing or split expressions
  by text matching to make them fit a phone.
- Give display mathematics sufficient size and vertical clearance without inflating inline
  symbols or compressing every long formula. Keep equation numbers outside the scrollable
  expression so they neither overlap nor disappear with it.
- Inspect the actual font result, not just the configured `font-family` list. STIX Two Math
  and Latin Modern Math are possible MATH-table fonts; their presence on a desktop says
  nothing about availability on a phone. Offline builds still use installed fonts only.
  Any authorized Pages math-font addition must follow `pages.md`'s licensing, version/hash
  pinning and naming requirements, and verify mathematical variants and stretchy assemblies
  after conversion. The Pages exporter now supplies a renamed STIX Two Math face with its
  complete glyph/feature coverage and OpenType MATH table: visible-text-only subsetting
  would miss implicit math alphabets, radicals, script forms and stretchy assemblies.
  Do not download a font from article code or silently change the offline policy.
- A different generator does not by itself fix formula typography. The documented Pandoc
  profile supports build-time TeX-to-MathML; this changes author syntax, not the delivered
  native layout or font policy. It is not permission to replace existing math with images
  during polishing. Other math outputs or runtime renderers need a separate interface decision.

Reader fixes must be tested against the staged public snapshot as well as local builds.
Every reader references one library-root asset tree, not a project copy. `tools/assets.py`
refreshes local runtime code without rebuilding prose. Actions composes the current runtime
from main into the approved snapshot, so pipeline UI fixes update all readers automatically;
this never authorizes publishing new article content.

## Compact source-code presentation

A source excerpt should lead with its technical purpose and readable code, not a paragraph
of version/path bookkeeping. For a source-card design, a short repository label, file basename
and real line range can form the default summary; keep the complete evidence required by
[source-analysis.md](method.md) beside the same excerpt in an expandable source record.
Do not shorten the canonical commit or source URL, discard the repository-relative path, or
move all identity into inaccessible machine metadata. Full records must remain available in
the saved HTML without fetching GitHub or relying on JavaScript.

Native `details`/`summary` is a compatible progressive disclosure option. Its summary must be
meaningful on a phone, work with touch and keyboard, and leave the code visible when closed.
Existing plain Markdown captions remain valid. `tools/source_cards.py` provides a bounded
compatibility upgrade for the complete legacy caption emitted by the excerpt generator:
`源码摘录` purpose, repository, full commit, path, real line range, symbol and a matching
HTTPS GitHub fixed-version permalink, immediately followed by code. Commit/path/range and
code line count must agree; partial or inconsistent captions remain untouched. This is not a
general prose recognizer or a new Markdown directive. The builder and explicit runtime
refresh use the same idempotent upgrade; the original `pre`/`code` subtree is retained
verbatim. Source verification still belongs to the research records and excerpt generator,
not to this presentation adapter. Reuse structured records when authoring new generators.

Enhanced source cards visually hide common leading spaces without changing `textContent`.
Their copy control writes the original text, with an original-text selection fallback when
clipboard access fails. No-JS readers retain visible code and native source disclosure; they
do not show an unusable copy button. Source ranges are shown, not synthetic gutter numbers.

Display line numbers and copy controls must not contaminate the copied source. Visual removal
of common indentation must preserve the original text and relative indentation, be disclosed,
and leave an original-text copy/fallback. Editing code is not a typography fix. The source
analysis specification owns excerpt verification and permission requirements.

## Presentation review

Check representative narrow and wide views, for example 320/390/768/1440 CSS pixels, as well
as light/dark themes and supported reading-size changes. Verify that:

- prose and the document root do not overflow horizontally; wide content scrolls locally;
- inline math retains its baseline, display symbols are not clipped, equation numbers remain
  readable, and scroll regions can be operated without a pointer;
- source records expand by touch and keyboard, retain full fixed-version identity offline,
  and remain usable with no scripts; unavailable enhanced controls are not left as dead buttons;
- code text, mathematical structure, citations and stable IDs survive the presentation change;
  any display-only normalization is kept separate from canonical content and verification;
- the inspected browser/font environment and any untested mobile engines are reported honestly.
  Desktop viewport emulation is not a real-device or cross-browser typography test.

Use synthetic fixtures and TEMP comparison pages before touching canonical manuscripts.
Passing these checks establishes presentation behavior, not mathematical or technical validity.

## Compact metadata without lost originals

Classify material by authorship and purpose, not merely by a heading's wording. The source
author's technical definitions, glossary chapter or discussion of its title remain manuscript
content in their original position. Editorial term choices and brief genre notes belong below
the title; chapter-title translation maps and authoring instructions belong in non-rendered
maintenance files, not even in source notes.

The shared builder recognizes explicit auxiliary headings such as paper information,
acknowledgements/declarations, publication notes and references. It preserves technical
headings (for example a discussion of variable declarations). Source/rights blocks move
beneath the title in small, optionally expanded source notes, and leave the body TOC.
Publisher-neutrality boilerplate is not represented as the reader's own declaration.
Copyright and licensing restrictions remain intact in the source and source notes.

A project's canonical `work/reader-meta.md` holds header-only Markdown: actual source,
version, applicable license and genuinely relevant reading limitations. Keep operational
history (rejected sources, export status, tool checks, local paths and editorial correction
logs) out of reading pages. Review paragraphs semantically, not by keyword alone: experimental
conditions and technical qualifications are not workflow chatter. Avoid repeating title,
author or source fields already shown immediately above. Move existing notes there without rewriting the
translated argument. The builder's content hash includes this file and `work/reader.json`;
the hash remains a machine-readable HTML attribute rather than a prominent colophon.

Source-code analyses pass `kind: analysis` in builder metadata; they are not labeled as
translations. They retain their real inspected repository, commit and verification limits.
Self-authored reviews use `kind: review`, labeled 原创综述 rather than a translation or source-code
analysis. Keep project identity in canonical `work/meta.json`; do not invent a PDF/web source
manifest or an inspected repository. Publication eligibility is separate from presentation kind;
see `pages.md` for explicit local-only flags and snapshot approval.

## Visible terminology from one canonical glossary

Set `"show_glossary": true` in `work/reader.json` to render the reader-facing
`work/glossary.md` inside the title's **出处与说明**, after `reader-meta.md`. This does **not**
create a body section or add glossary headings to the body TOC. Use a level-two heading such
as `## 译名与文体约定`; keep only reader-relevant term pairs, distinctions and brief descriptive
notes there. Do not copy the table into `content/` or `reader-meta.md`.

The glossary remains a canonical input: it contributes to the content hash and is listed in
`reader_inputs`, not `sections`. The existing `sec-glossary` anchor remains available in the
header for saved links. The field must be boolean; a missing glossary or a colliding
`sec-glossary` content section stops the build. Default/false does not render this editorial
file. An original author's glossary written in `content/` remains body content independently
of this switch.

Before enabling the switch on an old mixed maintenance glossary, separate its contents:
keep English/translated term pairs in `glossary.md`, source/rights and genre descriptions in
`reader-meta.md`, and move chapter-title maps, batch instructions and review records to the
appropriate non-rendered maintenance files. The renderer does not infer or delete those
passages by keyword. Full ownership rules and contrasting examples are in
[chinese-writing.md](writing.md#正文与维护材料的边界).

## Contextual citations, not a full visible bibliography

Original bibliography files and extracted reference text stay under local `work/`. The
rendered body omits their list/heading. Numbered citations (including ranges) and explicitly
mapped author-year citations gain source links, native hover descriptions, accessible names
and an optional citation card with direct source links. Code, MathML and existing hyperlinks
are not rewritten. No JavaScript still leaves real HTTP(S) hyperlinks.

Optional `work/reader.json` supplies presentation metadata, without any project constants:

```json
{
  "kind": "translation",
  "source_url": "https://example.org/original",
  "citation_style": "mixed",
  "references": {
    "1": {
      "text": "A. Author. Original title (2024).",
      "url": "https://example.org/cited-work",
      "aliases": ["Author et al., 2024"]
    }
  }
}
```

Set `citation_style` to `numeric`, `author-year` or the default `mixed` for the original
citation convention. In author-year papers, ordinary numerical intervals must not turn into
numbered references. Prose entity boundaries (such as `&amp;` in author names) are handled
without rewriting protected code or MathML.

Keep reference text as printed. Normalize extraction whitespace, not facts, dates or apparent
source mistakes. Never invent URLs or pick an ambiguous author/year match. Missing/unmapped
entries must point to the original paper with an explicit limitation, not fabricated metadata.
Bibliographic accuracy and network reachability are separate verification steps.

The build manifest records linked citations and unmapped entries. Deferred citation-card text
also contributes glyphs to a licensed Pages font subset, so accented author names are not lost.

## Source selection and publication

For a rights-restricted published paper, first seek its corresponding arXiv preprint. Verify
identity, authors, fixed version and the applicable license; a similarly titled paper is not
an alternate version, and arXiv availability alone does not permit sharing adaptations. Translate
that verified preprint version in full. Use the published edition only for cited revisions,
without reproducing its complete content by default.

The project no longer maintains `.pagesignore`. Review publication scope explicitly rather
than treating an ignore list as a rights decision. Export only approved readers/assets, never
source PDFs, full English papers, extraction data or canonical work.

`.gitignore` cannot retract a current deployment or remove tracked history. To withdraw previously published material, replace the content
snapshot, verify the live URLs are unavailable and, only with explicit owner authorization,
rewrite affected content-branch history and remove old deployment artifacts. Never silently
force-push. Rewrites cannot recall third-party clones or external caches.

Other reader changes may be built and tested locally without publishing a new translation
snapshot. A removal-only update must preserve every remaining public reader and asset.


<!-- merged from markdown.md -->

HTML is the deliverable, not the manuscript source format. Prefer ordinary Markdown and the
selected renderer's documented semantic extensions. Layout, colors, overflow and disclosure
belong to the shared theme/template, not per-paragraph `div`, `style` or JSX components.
Writing, translation and rights requirements remain in [chinese-writing.md](writing.md).

## Select one renderer per project

The existing `tools/build.py` entry point, canonical `work/` tree, shared assets and publication
boundary do not change. Choose the document renderer in `work/reader.json`:

```json
{
  "renderer": "pandoc",
  "kind": "translation",
  "public_export": false
}
```

- `pandoc` is the Markdown-first path for new projects. It delegates document parsing, figures,
  tables, footnotes, code highlighting and math conversion to Pandoc rather than project-specific
  Markdown preprocessors. It converts the complete document once, including source notes,
  so headings, code anchors and footnotes have one namespace across chapters.
- Omitted `renderer`, or `python-markdown`, retains the existing compatibility behavior. Do not
  silently reinterpret an old manuscript or mechanically change its HTML/MathML during cleanup.
  Switching an existing project requires reviewing its actual constructs and stable anchors.
- Unknown values fail; a missing Pandoc installation does not silently select another parser.

Install the optional pinned renderer with `python tools/dev.py setup --pandoc`, then use the
normal build command. It installs `pypandoc_binary` into the external TEMP venv, not system
locations or reader output. The verified wheel contains Pandoc 3.9; the build manifest records
its actual version. Pip requires a binary wheel for this package rather than building an
unsupported platform from source. Pandoc and its wrapper have separate licenses; see
[NOTICE](../NOTICE.md#document-renderer). No browser, Node framework, TeX distribution or
runtime mathematical renderer is needed. Builds do not download dependencies.

## Everyday syntax

These examples describe the **Pandoc** profile, not additional syntax for the legacy parser.

### Headings, links and code

Use normal headings and links. Give long-lived targets explicit labels instead of hand-writing
HTML anchors; automatic slugs can differ between parsers:

```markdown
## 状态转换 {#state-transition}

参见[状态转换](#state-transition)。
```

Use language-tagged code fences. Pandoc highlights during the build; the shared stylesheet
uses the reader's light/dark palette. Preserve original indentation and verified source
provenance as required by [source-analysis.md](method.md). The legacy source-caption
card upgrader is not a new author syntax or a promise to infer incomplete records.

### Figures, tables and footnotes

A standalone image with a description becomes a figure with a caption:

```markdown
![图 1 | 状态流转示意。](assets/figures/figure-01.png){#fig-state}

参见[图 1](#fig-state)。
```

Use pipe tables and a native table caption, rather than a hand-written HTML table:

```markdown
| 输入 | 输出 |
| --- | --- |
| 文档源稿 | 阅读页 |

: 表 1 | 输入与输出。
```

Footnotes use `[^label]` and `[^label]: 内容`. Choose meaningful, document-wide unique labels;
Pandoc creates the numbers, endnotes and backlinks. Complete notes remain in saved HTML and
work without scripts. Source notes in `reader-meta.md` can refer to footnotes too.

### Mathematics

In this profile, `$x_i$` and `$$ ... $$` are **source syntax**. Pandoc converts them to native
MathML during the build, including supported fractions, scripts, matrices and aligned rows.
The delivered page has no unresolved TeX, generated TeX annotations or runtime MathJax/KaTeX.
Unknown/unsupported math raises a build error instead of silently shipping a fallback.
Existing native MathML can still be supplied; do not rewrite old expressions just to use a
new renderer. A successful conversion is not a mathematical-correctness review.

For an explicitly numbered expression and stable target, use standard fenced-div/span syntax:

```markdown
::: {.equation #eq-update}
$$
x_{t+1} = x_t + \Delta x_t
$$
[(1)]{.eqno}
:::

参见[式（1）](#eq-update)。
```

The explicit `(N)` span matches the existing coverage expectation, without requiring HTML.
This first interface does not provide automatic figure/equation numbering or a new
cross-reference language; keep source numbers and explicit links rather than inventing a
custom parser. Pandoc's supported TeX math is not a complete LaTeX engine: do not paste
arbitrary document commands or packages into a formula.

### Semantic blocks, not local layout

A short note can use Pandoc's native fenced divs:

```markdown
::: {.note}
**条件**：此处填写与相邻论点有关的适用范围。
:::
```

Use such blocks only for genuine content roles, not to turn every paragraph into a card.
Do not add width, font, flex/grid or color utilities to source prose. Unsupported complex
content is a renderer decision or a reason to simplify the presentation, not permission to
sprinkle one-off HTML/CSS through every chapter.

## Explicit ownership, limited migration

On the Pandoc path, manuscript headings do not trigger heuristic relocation/deletion. An
original author's acknowledgements, definitions, bibliography and body contents stay body
material in source order. Place editorial source/rights notes in `reader-meta.md`; the optional
reader glossary stays under title source notes. Existing citation records in `reader.json`
continue to support contextual links, independently of visible bibliography content. Pandoc
CSL bibliographies and additional filters are not silently enabled.

Existing `{{include:path.md}}` composition still uses the shared bounded include expander;
only top-level files become chapters. The builder, assets, reader and publisher remain one
pipeline, not a second site or source tree. The two parsers are an explicit compatibility
boundary, not an extensible plugin framework. Retire old workarounds only after their actual
users are migrated; do not copy them into the new path to reproduce historical markup.

## Validate at the relevant boundary

Normal manuscript work checks the affected document, its declared elements and actual reading
result. It does not add unit tests for each paragraph or rerun all publication tests. A renderer
change uses a representative synthetic document plus key failure contracts; upstream Markdown
syntax does not need a second local conformance suite. Source fidelity, mathematical correctness
and rights review remain separate from rendering checks. Follow [workflow.md](pipeline.md#4-validate-at-the-relevant-boundary).

## Upstream references

- [Pandoc User's Guide](https://pandoc.org/MANUAL.html): Markdown, figure/table captions, fenced
  divs, footnotes and build-time MathML.
- [Pandoc FAQ](https://pandoc.org/faqs.html): Pandoc does not extract content from PDF inputs.
  PDF extraction remains a distinct pipeline stage.
- [pypandoc](https://pypi.org/project/pypandoc-binary/): the thin executable wrapper and bundled
  binary distribution. No upstream source or binaries are vendored in this repository.


<!-- merged from questions.md -->

这是明确规划的问答体裁，不是把所有综述或源码书稿改成面试脚本。问题组织知识入口，回答仍解释机制、条件、取舍与证据；不照抄外部题库或将未核对的口诀作为保证。写作仍遵守 [中文规范](writing.md) 和 [研读方法](method.md)。题库按“部分—主题”分层，同一主题内先基础、再原理、最后场景，使顺序阅读和按主题随机练习都能落在相关问题上。

## 同一正文，两种阅读方式

默认展示问题与回答配对的完整正文。支持原生 dialog 的浏览器加载共享脚本后，在题库顶部提供：

- **折叠全部回答 · 自测**：隐藏本题库全部内联答案，问题变成可用键盘操作的按钮；点击对应问题打开其答案卡片。
- **展开全部回答**：恢复全部配对答案，问题回到阅读标题状态。
- **搜索问题**：仅匹配问题文字，不搜索隐藏答案，避免自测时泄露提示；显示匹配题数与空结果说明。清空搜索恢复所有题目。
- **随机抽题**：打开主题范围选择，可多选、全选或清空；从所选主题里随机抽一道当前未被搜索隐藏的题目，显示在卡片内，答案默认折叠，可展开、收起或跳到原题位置。抽题只在当前页面内进行，不保存“熟悉度”或抽题记录。

切换仅影响显式题库，不折叠其他章节，不修改源稿。每次打开页面默认完整阅读，不保存“熟悉度”或将浏览次数当作掌握程度。多个题库独立切换和搜索。

随机抽题的“主题范围”由题库自身的标题层级推导：紧邻题目之前的最后一级标题是一个主题，其上级标题是所属部分；题库没有标题时全部题目同属一个范围。因此主题划分属于规范稿结构，不由脚本按关键词猜测，也不在运行时写死在共享脚本里。

答案卡片复用共享 modal 服务：内部滚动、锁定背景、Tab/Shift+Tab 焦点约束、关闭按钮、Escape、点击遮罩关闭，关闭后恢复原问题焦点和滚动位置。随机抽题卡片使用同一个 modal 服务，因此两款卡片不会同时打开：答案卡片内的引用保留真实来源链接，随机抽题卡片内的引用同样按阅读页处理，并在关闭或跳转时把答案节点归还题目。它移动原有答案节点而不是复制正文，避免重复锚点、重复公式和引文处理器丢失；题目文字在抽题卡片中是显示副本，题目本身不含稳定 ID、链接或表单控件。在已打开的卡片内，引用保留真实来源链接；HTTP(S) 来源在新标签打开，保留答题状态，不堆叠第二层引用弹窗。跨章链接关闭卡片后转到目标，卡片内部锚点只滚动卡片内容。

没有 JavaScript 或原生 dialog 支持时，所有答案仍可阅读，不显示不可用的切换按钮。打印包含全部问题与答案，包括搜索隐藏的题目和正打开卡片的答案；搜索和自测不是打印范围选择器。公式仍使用原生 MathML，代码仍由构建器离线着色。

## 规范稿接口

在常规章节或 include 子稿中显式编写下列 HTML 容器。`markdown="1"` 由现有 Markdown 构建器解析，生成 HTML 不保留该属性：

```html
<div class="qa-bank" id="backend-questions" markdown="1">

### 对象与所有权

<article class="qa-item" id="qa-raii" markdown="1">
<p class="qa-question">RAII 为什么能把异常路径与资源释放联系起来？</p>
<div class="qa-answer" markdown="1">

资源由对象持有，退出作用域时销毁已构造完成的局部对象。

正常返回与异常栈展开共享析构路径，但前提是所有权和销毁依赖正确。

</div>
</article>

</div>
```

- 题库为 `div.qa-bank`，题目为其直接子元素 `article.qa-item`。
- `qa-item` 可带 `data-level` 编辑层级，取值仅为 `basic`、`principle`、`scenario`（基础、原理、场景）。层级用于阅读顺序和“基础→原理→场景”的递进检查，不参与题目身份，也不改变答案的技术断言；同一主题内按层级递增排列，缺层级时不显示层级标记。显示层级的角标由共享样式按属性生成，不写进问题文字，因此搜索和卡片标题只读到题目本身。
- 题目显示编号是阅读顺序编号，可按新顺序重新编号；稳定身份始终是 `qa-*` ID，重排不改变 ID 与锚点。
- 主题标题使用 `h3`（部分）与 `h4`（主题）两级，主题 ID 稳定；随机抽题按这一层级划分范围。
- 每题恰有两个直接子元素：`p.qa-question`、`div.qa-answer`，顺序固定，内容非空。问题可有非交互的行内代码或强调，不能嵌入链接、按钮或表单控件。
- 题库和题目使用稳定 ASCII ID，匹配 `[a-z][a-z0-9-]*`；整个阅读页的 ID 唯一，包括模板目录等元素。题库不能嵌套，题目不能跨组配对，每个结构元素只能有一种问答角色。规范稿不在题库、题目、问题或答案上写 `hidden`。
- 答案允许段落、列表、代码、表格、MathML、引文及跨章链接。相对资源路径仍以输出阅读页为基准，不以子稿为基准。
- 主题标题进入常规目录；问题用段落与稳定题目 ID，不把大量题名灌入四级标题目录。章节可按主题拆分子稿，父稿只保留标题、阅读顺序和组合指令。

构建阶段的 `tools/questions.py` 验证显式结构，包括可选的 `data-level` 取值；普通正文不会因为含有问号或“回答”而自动变成题库。`manifest.json` 的 `question_banks` 记录各题库 ID 与题目 ID 顺序，内容与 include 依赖仍由原有哈希覆盖。样式和交互只维护在共享 `src/styles/reader.css`、`src/scripts/reader.js`。

## 检查边界

结构测试检查配对、ID、非空内容、组合、代码、引文和层级取值。浏览器回归检查阅读／自测切换、答案移动与归还、键盘关闭和焦点、搜索、随机抽题的主题范围与答案折叠、打印、无脚本／无 dialog 回退以及普通章节不受影响。测试使用临时合成稿和本地浏览器，不执行被研读项目，不访问真实用户账户。

页面交互通过不证明答案正确。内容审校另外核对语言标准、实现版本、协议和数据库语义，区分题库选题来源与答案的技术依据。只读题库范围、来源许可与未核对主题保留在项目维护记录；新正文发布仍须单独授权。
