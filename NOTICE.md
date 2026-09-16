# Notices and scope of the license

The MIT license in `LICENSE` covers everything in this repository: the pipeline under `tools/`,
the tests under `tests/`, the page template, stylesheet and reader script under `src/templates/`,
`src/styles/` and `src/scripts/`, and the documentation beside them.

## No paper material is published here

The repository was built to translate papers, and it deliberately ships none of the material that
came out of one:

- **No translation.** `papers/<slug>/content/*.md` would be a Simplified Chinese translation of
  another author's paper. A translation is a derivative work, and the rights in the original text
  stay with its authors.
- **No figures.** `papers/<slug>/assets/figures/*.png` are figure crops extracted verbatim from
  the source PDFs.
- **No source document.** Neither the PDFs nor the page text and rasters derived from them are
  committed.

`papers/` is therefore listed in `.gitignore`, and a fresh clone contains the pipeline without a
single paper in it. The material lives only on the machine that produced it: the source PDF goes
to `.local/source/<slug>/`, `tools/extract.py` regenerates the figure crops and the page text
from it, and `tools/build.py` needs a manifest you write yourself.

If you intend to read, publish or redistribute a translation or a figure produced with this
pipeline, ask the rights holder of the original paper first. The MIT grant in this repository
does not extend to that material, because that material is not in this repository.

## Fonts are not bundled

No font ships with this repository. The reader stylesheet only names font families in priority
order — Times New Roman and metric-compatible serifs for Latin, then Source Han Sans SC, Noto
Sans SC, Microsoft YaHei and PingFang SC for Simplified Chinese — and the browser resolves each
glyph from the fonts installed on the reading machine. Nothing is downloaded at page load
either, so a packed file stays fully offline while carrying no font license obligations.

## Python dependencies

Third-party packages listed in `requirements.txt` are not vendored. Each keeps its own license
and is installed by the user into the isolated environment under `.local/`.
