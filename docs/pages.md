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
The initial export was explicitly authorized for every rendered page under dist, excluding
work, original PDFs and source materials.

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

Rebuild locally, repeat the export and font subsetting, review and push. Actions cannot rebuild
translations absent from main; it deploys the explicitly supplied content snapshot. A CSS or
script change on main does not retroactively change the content branch: re-export to apply it.
Pushes to either branch and manual workflow dispatch deploy the latest content snapshot.
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
