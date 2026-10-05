# Documentation responsibilities

Documentation describes the maintained project, not a transcript of its development.

| Document | Responsibility | Excludes |
|---|---|---|
| Root `README.md` | Capabilities, setup, layout and entry-point commands | Release history, task progress |
| `AGENTS.md` | Durable agent execution and safety constraints | One-off approvals, execution logs |
| `CONTRIBUTING.md` | Development, review and contribution workflow | Current task inventory |
| `CHANGELOG.md` | Actual version changes and their historical context | Unperformed plans or current interface specification |
| `NOTICE.md` / `LICENSE` | License scope and third-party rights | Deployment status or approval history |
| `architecture.md` | Current data model, invariants and interfaces | Old paths presented as active, task-specific experiments |
| `reader.md` | Presentation metadata, citations and progressive behavior | Manuscript progress or source acceptance logs |
| `pages.md` | Publication boundary, staging, validation and deployment procedure | Current public inventory or one-off authorization |
| `chinese-writing.md` | Genre, terminology and prose conventions | A reader-body template or revision diary |
| `review-method.md` | Evidence organization and research review methods | Per-project findings or mandatory agent invocation |
| `source-analysis.md` | Source structure, design comparisons, excerpt provenance and Markdown composition | Reader-body boilerplate or unverified performance claims |
| Local `dist/<slug>/work/README.md` | Project-specific maintenance and rebuild instructions | Reader prose or current task progress |
| Local `work/reference/` and source map | Useful source identities, evidence and research limits | Disposable tool output |
| System TEMP task/report files | Plans, approvals, scans, logs and trial outputs | The only copy of canonical manuscript material |

Architecture may explain why an invariant is useful, but named migration rounds, former
implementations and before/after measurements belong in CHANGELOG or retained research
records. Historical paths in CHANGELOG are not instructions to recreate those directories.

Before editing documentation, check the complete paragraph and its purpose. Move only genuine
history or task records; retain conditions, rights notices and verification limits. Compare
commands and paths with the current code, and link to the owning specification rather than
maintaining conflicting copies. Public inventory is generated as `site-manifest.json`.
