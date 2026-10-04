# GitHub Pages reading library

## Design

- **`main`**: pipeline, tests, stylesheet/script, font source lock and Actions workflow.
- **`pages-content`**: rendered HTML, recognized public assets, font license notices and
  `site-manifest.json`, plus one deployment workflow bootstrap. No Python/PowerShell pipeline
  scripts, source Markdown, `work/`, PDFs, extraction data,
  local paths from paper manifests, or survey source tree.
- **Actions**: checks out the pipeline from main, validates the separate content branch,
  stages it without `.git` or `.github`, uploads the Pages artifact, and deploys with Pages/OIDC permissions.
  No PAT, third-party hosting or external runtime asset CDN is required. The same workflow
  bootstrap is copied to pages-content because GitHub push events load workflows from the
  pushed branch; the bootstrap always checks out trusted pipeline code from main.
- **Home**: project cards, progressive title search and centered modal cards for detail-page
  links. Each modal scrolls internally, locks background scrolling, and closes by backdrop
  click, close button or Escape; it restores the homepage scroll position and trigger focus.
  Native dialogs trap focus. Without JS/dialog support, a single original details list remains
  accessible. Shared theme and plain relative links are preserved. There is no SPA router or server requirement;
  links work under a repository Pages prefix and with JavaScript disabled.

Publishing derivative works still requires the relevant rights/permissions. The pipeline's
MIT license does not license translations or figures. Source materials remain ignored in main.
Snapshot approval does not establish the original authors' adaptation/distribution permissions.
Review licenses separately and retain required notices.

## Source and publication review

Publication boundaries use project metadata, not a maintained `.pagesignore` list.
Before translating a rights-restricted published article, first seek its corresponding arXiv
preprint and check identity, fixed
version and license. Translate the verified preprint version; cite the published paper for
revisions without reproducing its full text by default. Being a preprint does not itself
authorize adaptation or publication.

Public snapshots still require explicit review and approval. A personal knowledge library on
GitHub Pages is publicly accessible unless the hosting configuration actually restricts it.
Translation-only publication and learning-use notices do not grant extra rights.

**Paper translations are local-only.** The exporter excludes projects registered with
`work/paper.json`, and profiles whose kind is `translation` (also the default when a profile
omits kind), even with an obsolete `"public_export": true`. HTML, figures and conventional
root-level packed `<slug>.html` copies are excluded together. Mark canonical translation
profiles `"public_export": false` as well; no flag grants permission to publish translations.

For other local-only projects, set `"public_export": false` in canonical
`dist/<slug>/work/reader.json`. Generated project `manifest.json` also carries an explicit veto
when appropriate: the legacy survey builder propagates its canonical identity's flag and
defaults to local-only. These metadata fields define export eligibility; they do not record
approval history, deployment status or a current website inventory.

Publication metadata must use boolean flags and unique JSON keys. Duplicate fields or
nonboolean values stop export rather than allowing a later value to override a veto.

These filters are not semantic detection of arbitrary renamed or unregistered HTML copies,
and are not substitutes for reviewing every staged file. Missing/true flags on nontranslation
projects do not grant approval or rights. Changing metadata does not remove an already-live
snapshot; existing historical readers and withdrawals follow the procedure below.

`.gitignore` alone cannot withdraw an existing deployment or tracked historical content.
An already-published withdrawal needs a replacement snapshot and live verification; historical
removal or artifact deletion additionally requires explicit owner authorization. Never silently
rewrite a branch. Third-party clones and caches cannot be recalled by a Git rewrite.

A removal-only release must copy the existing public snapshot, omit the withdrawn trees and
refresh its homepage/inventory, preserving every remaining reader/asset. Do not mix it with
local reader redesigns or newly translated material awaiting publication approval.

Reader presentation, metadata migration and citation mapping are documented in
[`reader.md`](reader.md).

## Mobile reader

17px default prose, relaxed line spacing and ragged-right paragraphs avoid cramped or uneven
phone text. Tool buttons have 44px minimum hit areas. The mobile toolbar occupies its own
sticky row, rather than floating over the title. Font-size preferences and theme persist when
storage is available; TOC access is one tap. Long URLs wrap; tables, display MathML and code
scroll independently without widening the document. Safe-area padding accommodates notches,
reduced-motion preferences are respected, and print still uses A4.

## Fonts

Default offline builds continue to request installed fonts. The Pages exporter adds:

- Chinese: **Source Han Serif SC / 思源宋体 2.003** (regular and bold).
- Code, including Chinese comments: **Maple Mono CN v7.9**, regular/bold/italic/bold italic.
- English: locally installed **Times New Roman** first; **Tinos** as a self-hosted,
  Times-compatible substitute when Times New Roman is absent (usual on phones).
  This is not an identical Microsoft face; no Microsoft font files are redistributed.

Sources and SHA-256 checksums are pinned in `tools/font-sources.json`. Originals download
only into system TEMP; failed hashes stop the export. WOFF2 subsets contain actual used glyphs;
Chinese text is split into frequency-ordered chunks, and code fonts contain only used code
characters. `font-display: swap` keeps text immediately readable. Files are real, same-origin
assets, not data URIs. Subsets are renamed to respect OFL Reserved Font Names; original
copyright and full SIL OFL 1.1 licenses accompany them in `assets/fonts/`.

The website fetches its own font assets on first load; default local offline readers do not.
There is no service worker/offline-after-first-visit promise. Downloading the complete exported
site still permits local reading.

## First deployment

In GitHub **Settings → Pages → Build and deployment**, set **Source: GitHub Actions**.
Ensure Actions is enabled and the `github-pages` environment allows `main` and `pages-content`
(or all branches). Protect main as desired; do not make pages-content the default branch.

Use an empty absolute TEMP directory to prepare publication:

```powershell
. .\tools\dev-env.ps1
& $Python -m pip install -r requirements-pages.txt
# Rebuild registered papers first, plus tools/survey.py and any local work/rebuild.py.
$Site = Join-Path $ProjectTemp ('scratch\pages-' + [guid]::NewGuid().ToString('N'))
& $Python tools\pages.py --out $Site
& $Python tools\pages_fonts.py --site $Site --cache "$ProjectTemp\scratch\font-originals"
& $Python tools\pages.py --check $Site
```

Inspect `$Site\site-manifest.json` and preview on a phone-sized browser. It enumerates every
page and hashes all public files. The exporter copies only HTML outside private directories
and recognized asset types; it refuses symlinks, non-empty output directories, and non-TEMP
output. Public copies anonymize Windows user-specific repository paths under Documents
as `$LOCAL_REPOS/…`, leaving original prose and exact inspected commits intact locally.
The validator rejects sources, PDFs, unexpected file types, broken/escaping links,
root-relative links and external HTML render dependencies. It never cleans dist.

Then commit/push main normally and publish the reviewed content:

```powershell
.\tools\publish-pages.ps1 -Site $Site -Push
```

The helper creates a fresh TEMP checkout based on the remote content branch (or a new,
parentless branch initially), replaces only that disposable checkout's public files, validates
again, commits and pushes without force. It never adds dist to main. Omitting `-Push` prepares
a commit for inspection and prints its checkout path. A non-fast-forward push fails safely;
re-run from the latest remote branch rather than forcing.

## Updates and limitations

Content changes: rebuild locally, repeat the export/font subsetting, review and push.
Actions cannot rebuild translations absent from main. It composes the explicitly approved
content snapshot with one current `assets/{styles,scripts}/` runtime from main, validates the
result, and deploys from system TEMP. Thus a shared UI fix on main updates every reader without
rebuilding/re-exporting any article or copying code to project folders. Page text, figures and
licensed fonts remain in the approved content snapshot; no new translation is published by a UI push.

Local runtime refresh: `& $Python tools\assets.py`. To migrate or update a reader-only TEMP
snapshot explicitly: `& $Python tools\pages.py --refresh-shared $Site`. The first migration
changes only standard resource URLs and removes duplicate generated copies; later refreshes
change only root assets/inventory. The validator rejects reintroduced copies/noncanonical URLs.
Pushes to either branch and manual workflow dispatch deploy the latest approved snapshot.
The deployment is serialized; deployment failure leaves the previous live version untouched.

The content branch's Git history remains public even if a later export removes a page. Never
put a source or sensitive file there. If disclosure occurs, removal in a new commit is not
sufficient; contact the repository owner to plan history cleanup.

Validation: `& $Python -m pytest`, `& $Python -m ruff check .`,
`& $Python -m ruff format --check .`, plus the mandatory exported-site `--check`.
Optional modal browser regressions use Playwright with an installed local Chrome/Chromium,
not a signed-in profile or a downloaded browser. Initialize the external environment, install
`playwright==1.58.0` with `$Python -m pip`, optionally set `PAPER_BROWSER_EXECUTABLE`, then run
`& $Python -m pytest tests/test_library_browser.py`. Tests cover 320/390/1280px layouts,
internal scrolling, all three close paths, focus/scroll restoration, detail-title search,
navigation and no-JS/no-dialog fallbacks. They skip when optional tooling is absent.
