# Markdown authoring and document rendering

HTML is the deliverable, not the manuscript source format. Prefer ordinary Markdown and the
selected renderer's documented semantic extensions. Layout, colors, overflow and disclosure
belong to the shared theme/template, not per-paragraph `div`, `style` or JSX components.
Writing, translation and rights requirements remain in [chinese-writing.md](chinese-writing.md).

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
provenance as required by [source-analysis.md](source-analysis.md). The legacy source-caption
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
and rights review remain separate from rendering checks. Follow [workflow.md](workflow.md#4-validate-at-the-relevant-boundary).

## Upstream references

- [Pandoc User's Guide](https://pandoc.org/MANUAL.html): Markdown, figure/table captions, fenced
  divs, footnotes and build-time MathML.
- [Pandoc FAQ](https://pandoc.org/faqs.html): Pandoc does not extract content from PDF inputs.
  PDF extraction remains a distinct pipeline stage.
- [pypandoc](https://pypi.org/project/pypandoc-binary/): the thin executable wrapper and bundled
  binary distribution. No upstream source or binaries are vendored in this repository.
