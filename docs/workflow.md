# Content-first maintenance workflow

This is the operational entry point. Content quality belongs to the writing/review standards;
publication boundaries belong to `pages.md`. It does not waive either set of requirements.

## 1. Prepare once for the task

Identify the requested change and its boundary. For manuscript work, read the applicable
standards in full and the complete affected sections, project maintenance notes and terminology.
Keep this preparation for the batch; do not restart it for every question while scope and
standards are unchanged. Read an architecture/schema section only when changing that interface.

Use existing source inventories and local references. Do not regenerate manual coverage
records, rescan unrelated projects, refetch available material or read entire repositories
just to confirm a localized assertion. Canonical work/reference material is not disposable.

## 2. Read content before its representation

- Markdown/text: inspect the complete relevant paragraph or answer with necessary context.
- HTML: use `tools/read_source.py` to remove page chrome and expose prose, code and tables.
  Locate by heading or a literal phrase, then read the relevant blocks. Use raw HTML only for
  math structure, ambiguous extraction or markup/rendering defects.
- JSON/manifests: select the needed key or emit a small summary. Full schema examples belong
  in interface documentation, not repeated working context.
- Code: locate the relevant symbol, then read its complete control flow and required callers.
  A directory/file list is not implementation evidence.

```powershell
. .\tools\dev-env.ps1
& $Python tools\read_source.py C:\path\to\saved.html --outline
& $Python tools\read_source.py C:\path\to\saved.html --find "macro definitions"
& $Python tools\read_source.py C:\path\to\saved.html --start 20 --count 8
& $Python tools\read_source.py C:\path\to\saved.html --id "intrusive_ptr"
```

The view is local and read-only: it does not fetch URLs, execute page scripts or overwrite
snapshots. Blocks are extraction positions, **not source line numbers**. Code whitespace and
MathML structure are retained; SVG/image-only mathematics still needs the original source or
visual inspection. Search, scope selection, suppressed page chrome and output limits are
explicit; an excerpt or extracted view never proves full reading, coverage or correctness.
Increase the character limit or follow the printed continuation when a block is incomplete.

### Reusable evidence lookup

`tools/knowledge.py` uses installed SQLite FTS5, without new packages or network services.
The database is an absolute TEMP cache; canonical snapshots and source identities stay in
`work/reference/` and the independent checkouts. Build it once, then update changed bytes:

```powershell
$DB = Join-Path $ProjectTemp 'scratch\evidence.sqlite'
& $Python tools\knowledge.py --db $DB build --archive dist\my-review\work\reference\technical-docs\index.json `
    --reader dist\my-review\work\reader.json
& $Python tools\knowledge.py --db $DB build --repo repos\cpp-draft --file source/containers.tex `
    --reader dist\my-review\work\reader.json
& $Python tools\knowledge.py --db $DB search "already contains equivalent" --source containers.tex --limit 2
& $Python tools\knowledge.py --db $DB show --doc 12 --block 5 --count 3
```

Source files come from the resolved Git commit, not uncommitted working bytes. `--revision`
can select another local revision. Results distinguish HTML extraction blocks from real
source-line windows and identify partial representations. `--ref` searches only the reference
URL's declared line range or HTML element; missing/unsupported locations fail closed. It does
not infer additional ranges from prose notes or certify claim support. `--linked-ref` is the
explicit broader snapshot/file discovery filter, not an evidence-scope filter. Continue a
scoped result with `show --ref` as printed. Snapshot hashes and commits are identities, not
product editions. Cache migration/parser changes require rebuilding, even for unchanged input
bytes. Search hits do not complete an audit; read required adjoining context, especially code
and math. New dependencies are justified only
by an actual format/lookup gap, not by a preference for building a larger platform.

## 3. Review assertions, not source volume

Work by topic, usually 10–20 questions per batch. For each answer determine:

1. Are all requested subrequirements actually answered, including merged/split mappings?
2. Are the conclusions correct, with version, complexity, concurrency and exception conditions?
3. Does each relevant citation support the adjacent claim rather than merely the topic?

Choose the smallest sufficient evidence path:

| Situation | Evidence path |
|---|---|
| Basic assertion already supported locally | Complete answer plus existing evidence; no new search |
| Condition-sensitive or implementation-specific claim | One directly relevant primary source at a fixed scope/version |
| Genuine disagreement or source/rights ambiguity | Compare the conflicting sources; add another only to resolve the identified gap |

Before searching, state the exact unresolved assertion. A useful default time box is five
minutes per difficult point; if unresolved, record it as pending and continue the batch.
Do not use the time box to mark an unchecked requirement complete. Downloads, hash counts,
candidate matches and document tests are never semantic coverage proof.

Batch the edits and record only the conclusion, stable answer ID, evidence locator and
remaining gap. Reuse verified evidence within its actual scope instead of rereading the same
manual for each related answer. Source identity, reading scope and answer coverage stay separate.

### Record per-question time without new task scripts

`tools/review_log.py` appends actual timestamps to a new absolute TEMP log for each batch.
Mark `prepare`, then each stable `qa-...` ID, then `edit`, `validate` and finally `done`.
The next mark closes the previous interval; revisit an ID if more work is needed. Only mark
`done` after the checks finish. Summary reports keep measured question intervals separate
from equal-share estimates of common editing/checking time; preparation remains separate.

```powershell
$Log = Join-Path $ProjectTemp 'reports\batch-unique.jsonl'
& $Python tools\review_log.py --log $Log mark prepare
& $Python tools\review_log.py --log $Log mark qa-example
# Other questions, then shared edit/check phases; never infer completion from time alone.
& $Python tools\review_log.py --log $Log mark edit
& $Python tools\review_log.py --log $Log mark validate
& $Python tools\review_log.py --log $Log mark done
& $Python tools\review_log.py --log $Log summary --out "$ProjectTemp\reports\batch-unique.md"
```

## 4. Validate at the relevant boundary

| Change | Checks |
|---|---|
| Prose/references | Affected build, anchors, citations and declared coverage expectations |
| Parser/builder/runtime | Targeted synthetic tests during implementation; full tests/lint/format before commit |
| Interaction/layout | Browser regression on the affected reader or publication candidate |
| Publication | Reader-only export validation, preserved-project comparison, remote commit and selected live files |

Do not rebuild all readers or run the full suite after every answer. Preserve code, formulas,
rights and source conditions when polishing. Engineering results and content-audit results
must be reported separately, with actual failure/partial states.

## 5. Publish with maintained entry points

Use the staging/font/push commands in [pages.md](pages.md), not a new script for each release.
`tools/pages_verify.py` checks a published TEMP checkout against the approved site, accounting
only for Git text newline normalization; binaries must match exactly. It can check selected
live paths by HTTP hash without inspecting unrelated accounts or querying the Actions API.

```powershell
& $Python tools\pages_verify.py --checkout $Checkout --site $Site
& $Python tools\pages_verify.py --checkout $Checkout --site $Site `
    --base-url "https://example.github.io/library/" --path "my-review/index.html"
```

Verification prints a brief result; detailed machine evidence is optional via `--report`
under system TEMP. A live mismatch may mean deployment is pending: inspect that result,
not the already-successful push. No automatic push, retry loop, weakened TLS or history rewrite
is part of either reading or verification. For authorized GitHub metadata/PR/Actions queries,
prefer an installed and authenticated `gh` CLI to one-off API scripts. For example,
`gh run list --workflow pages.yml --branch pages-content --limit 3` shows deployment runs;
its success does not replace remote or live content checks. Availability does not authorize
pushing, rerunning production jobs or changing account settings.
