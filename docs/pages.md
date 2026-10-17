# GitHub Pages reading library

## Design

- **`main`**: pipeline, tests, stylesheet/script, font source lock and Actions workflow.
- **`pages-content`**: rendered HTML, recognized public assets, font license notices and
  `site-manifest.json`, plus one deployment workflow bootstrap. No Python/PowerShell pipeline
  scripts, source Markdown, `work/`, PDFs, extraction data,
  local paths from paper manifests, or survey source tree.
- **Actions**: checks out the pipeline from main, validates the separate content branch,
  stages it without `.git` or `.github`, uploads the Pages artifact, and deploys with Pages/OIDC permissions.
  `tools/pages_deploy.py` consumes the uploader's exact artifact ID, validates its name,
  run identity, expiry and size through the single-artifact REST endpoint, then creates one
  deployment using the normal job token and OIDC. It does not trust artifact-list counts
  or rediscover an upload by name. Missing read-only metadata gets a bounded readiness
  check; deployment creation is never automatically replayed. Deployment status is observed
  with a deadline, cancelling only that invocation's own deployment on timeout. The job
  grants `actions: read` plus scoped Pages/OIDC write permissions; credentials are not logged.
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
- Native MathML: **STIX Two Math 2.13b171**, pinned to commit
  `744a22a4dd626cd14d75728aef34fc8ad7c85db0`, renamed **Paper Math**. Its complete
  glyph coverage, layout features and OpenType MATH table are retained: implicit math
  alphabets, radicals and stretchy assemblies are not determined by visible text alone.

Sources and SHA-256 checksums are pinned in `tools/font-sources.json`. Originals download
only into system TEMP; failed hashes stop the export. Text/code WOFF2 subsets contain actual
used glyphs; Chinese text is split into frequency-ordered chunks, and code fonts contain only
used code characters. The separate math WOFF2 face deliberately retains complete coverage. `font-display: swap` keeps text immediately readable. Files are real, same-origin
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

The commands below do not require PowerShell or shell activation. Run `env` to find the
external `project_temp`; replace `ABS_TEMP_SITE`, `ABS_TEMP_CACHE` and `ABS_TEMP_CHECKOUT`
with actual absolute paths under system TEMP. Choose an unused site directory and build only
explicitly approved original readers before staging. Repeat `--project` for multiple approvals.

```text
python tools/dev.py setup --pages
python tools/dev.py env
python tools/dev.py run -- tools/pages.py --project my-review --out "ABS_TEMP_SITE"
python tools/dev.py run -- tools/pages_fonts.py --site "ABS_TEMP_SITE" --cache "ABS_TEMP_CACHE"
python tools/dev.py run -- tools/pages.py --check "ABS_TEMP_SITE"
```

Inspect `ABS_TEMP_SITE/site-manifest.json` and preview on a phone-sized browser. It enumerates every
page and hashes all public files. The exporter copies only HTML outside private directories
and recognized asset types; it refuses symlinks, non-empty output directories, and non-TEMP
output. Public copies anonymize Windows user-specific repository paths under Documents
as `$LOCAL_REPOS/…`, leaving original prose and exact inspected commits intact locally.
The validator rejects sources, PDFs, unexpected file types, broken/escaping links,
root-relative links and external HTML render dependencies. It never cleans dist.

Then commit/push main normally and publish the reviewed content:

```text
python tools/dev.py run -- tools/publish_pages.py --site "ABS_TEMP_SITE" --push
```

The legacy `publish-pages.ps1 -Site ... -Push` command forwards to this Python entry point.

The helper creates a fresh TEMP checkout based on the remote content branch (or a new,
parentless branch initially), replaces only that disposable checkout's public files, validates
again, commits and pushes without force. It never adds dist to main.

Public text (HTML, CSS, JS, JSON, notices, workflow YAML and SVG XML) is normalized from
CRLF to LF **before** inventory hashes are computed. This finalization is restricted to
validated absolute TEMP snapshots; Git internals, canonical manuscripts and binary assets
are not rewritten. Text must be UTF-8. New text/font stylesheet writers also emit LF directly.
The fresh publication checkout sets local `core.autocrlf=false` and `core.eol=lf`, so Git
stages the already-approved bytes instead of converting them after hashing. No global Git
configuration changes or content-branch `.gitattributes` exception are needed. The verifier's
CRLF/LF allowance remains for older snapshots; newly finalized snapshots should require
zero newline exceptions, with fonts and raster images still byte-exact. Omitting `--push` prepares
a commit for inspection and prints its checkout path. A non-fast-forward push fails safely;
re-run from the latest remote branch rather than forcing.

## Update selected readers without replacing other projects

Use the existing public branch as the baseline; do not export every local reader when only
one project is approved. Both baseline and output are disposable absolute TEMP directories.
The selected project must still pass the normal source/rights eligibility filters.

Read the configured origin with `git remote get-url origin`; substitute that value for
`ORIGIN_URL` and choose a fresh absolute `ABS_TEMP_BASELINE` alongside the output site.

```text
git clone --config core.autocrlf=false --config core.eol=lf --depth 1 --single-branch --branch pages-content "ORIGIN_URL" "ABS_TEMP_BASELINE"
python tools/dev.py run -- tools/pages.py --project my-review --baseline "ABS_TEMP_BASELINE" --out "ABS_TEMP_SITE"
python tools/dev.py run -- tools/pages_fonts.py --site "ABS_TEMP_SITE" --cache "ABS_TEMP_CACHE"
python tools/dev.py run -- tools/pages.py --check "ABS_TEMP_SITE"
```

`--project` can be repeated. The exporter replaces only those project trees in the TEMP
snapshot, updates its homepage/inventory and installs the shared runtime; other project
readers and assets are preserved. It never deletes canonical work or grants publication rights.

## Verify push and selected live files

After `publish_pages.py --push`, the helper verifies the remote content commit against the
approved site automatically. Reuse its printed `Content checkout` path; do not clone again just
to check the same push. For live verification, inspect only the requested paths:

```text
python tools/dev.py run -- tools/pages_verify.py --checkout "ABS_TEMP_CHECKOUT" --site "ABS_TEMP_SITE" --base-url "https://example.github.io/library/" --path "my-review/index.html"
```

The verifier checks Git object bytes, allowing only text CRLF/LF normalization, and requires
binary assets to match exactly. Live verification predicts canonical LF bytes for text
(including legacy CRLF Git blobs), then compares exact HTTP body hashes with normal TLS;
received bodies are not normalized to hide mismatches.
Verification is one-shot, without an Actions API dependency or retry loop. A mismatch after a verified
push may indicate pending deployment: do not repush automatically. Optional detailed evidence
uses `--report` with an absolute TEMP path; default output is a compact summary.

## Updates and limitations

Content changes: rebuild locally, repeat the export/font subsetting, review and push.
Actions cannot rebuild translations absent from main. It composes the explicitly approved
content snapshot with one current `assets/{styles,scripts}/` runtime from main, validates the
result, and deploys from system TEMP. Thus a shared UI fix on main updates every reader without
rebuilding/re-exporting any article or copying code to project folders. Page text, figures and
licensed fonts remain in the approved content snapshot; no new translation is published by a UI push.

Local runtime refresh: `python tools/dev.py run -- tools/assets.py`. To migrate or update a
reader-only TEMP snapshot explicitly, run `python tools/dev.py run -- tools/pages.py
--refresh-shared "ABS_TEMP_SITE"` on one command line. The first migration
rewrites standard resource URLs, removes duplicate generated copies and upgrades complete,
verified-locator legacy source captions into native source cards without changing code.
Already converted cards are unchanged; other prose is not rebuilt or replaced. Later
refreshes update root assets/inventory. The validator rejects reintroduced copies/noncanonical URLs.
Pushes to either branch and manual workflow dispatch deploy the latest approved snapshot.
The deployment is serialized; deployment failure leaves the previous live version untouched.

The content branch's Git history remains public even if a later export removes a page. Never
put a source or sensitive file there. If disclosure occurs, removal in a new commit is not
sufficient; contact the repository owner to plan history cleanup.

Validation: `python tools/dev.py run -- -m pytest`, `python tools/dev.py run -- -m ruff check .`,
`python tools/dev.py run -- -m ruff format --check .`, plus the mandatory exported-site `--check`.
Optional modal browser regressions use Playwright with an installed local Chrome/Chromium,
not a signed-in profile or a downloaded browser. Run `python tools/dev.py setup --browser`
to install the pinned optional package, optionally set `PAPER_BROWSER_EXECUTABLE`, then run
`python tools/dev.py run -- -m pytest tests/test_library_browser.py`. Tests cover 320/390/1280px layouts,
internal scrolling, all three close paths, focus/scroll restoration, detail-title search,
navigation and no-JS/no-dialog fallbacks. They skip when optional tooling is absent.
