# Notices and scope of the license

The MIT license in `LICENSE` covers the pipeline on the `main` branch: the code under `tools/`,
the tests under `tests/`, the page template, stylesheet and reader script under `src/templates/`,
`src/styles/` and `src/scripts/`, and the documentation beside them.

## Paper material is excluded from main

The repository was built to translate papers, and it deliberately ships none of the material that
came out of one:

- **No translation.** `dist/<slug>/work/content/*.md` would be a Simplified Chinese translation of
  another author's paper. A translation is a derivative work, and the rights in the original text
  stay with its authors.
- **No figures.** `dist/<slug>/work/assets/figures/*.png` are figure crops extracted verbatim from
  the source PDFs.
- **No source document.** Neither the PDFs nor the page text and rasters derived from them are
  committed.

`dist/` is therefore listed in `.gitignore`, including the retained `work/` tree, and a fresh
clone contains the pipeline without a single paper in it. Project materials stay local in
`dist/<slug>/work/`. The source PDF remains an external original: `tools/extract.py --pdf`
reads it in place without copying it into the workspace. `tools/build.py` rebuilds from the
retained translation, manifest and figure crops without requiring the PDF. The local survey
source under `/survey/` is ignored for the same derivative-work reason.

If you intend to read, publish or redistribute a translation or a figure produced with this
pipeline, ask the rights holder of the original paper first. The MIT grant in this repository
does not extend to that material. The separately authorized `pages-content` branch and
GitHub Pages site publish rendered translations, analyses and figure assets for reading.
They do not publish `work/`, source PDFs, extracted reference data or survey source files.
Publication does not transfer or relicense the original authors' rights.

## Fonts

No font binaries are bundled on main or in default offline builds. Those readers request
installed Times New Roman, Source Han Serif SC and Maple Mono, with system fallbacks.
The authorized Pages export self-hosts renamed, glyph-subset WOFF2 versions of Source Han
Serif SC, Maple Mono CN and the Times-compatible Tinos fallback, under SIL OFL 1.1.
Original copyright notices, full licenses, versioned source URLs and SHA-256 values accompany
those files under `assets/fonts/`. Their font licenses, not MIT, apply. Microsoft Times New
Roman is requested locally only and is never redistributed.

## Python dependencies

Third-party packages listed in `requirements.txt` are not vendored. Each keeps its own license
and is installed by the user into the isolated environment under system TEMP, initialized
by `tools/dev-env.ps1`.
