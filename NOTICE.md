# Notices and scope of the license

The MIT license in `LICENSE` covers the **software** in this repository: the pipeline under
`tools/`, the tests under `tests/`, and the page template, stylesheet, and reader script under
`src/templates/`, `src/styles/`, and `src/scripts/`.

It does **not** cover the translated document itself.

## Material that is not ours to license

- `papers/deepseek-v41-flash/` contains a Simplified Chinese translation of
  *DeepSeek-V4.1-Flash: Pushing the Limits of KV Cache Compression* by DeepSeek-AI, and
  `papers/mamba-survey/` contains a Simplified Chinese translation of *A comprehensive survey
  and taxonomy of mamba: Applications, Challenges, and Future Directions* by Qiguang Miao et
  al. (Information Fusion 130, 2026, 104094). A translation is a derivative work, and the
  rights in the original text remain with its authors. This content is included for personal
  study and reading; it is not covered by the MIT grant, and redistributing it may require
  permission from the rights holder.
- `papers/*/assets/figures/` contains figure images extracted verbatim from those papers' PDFs.
  They are the original authors' material for the same reason.
- The translated text also reproduces the papers' numerical results, benchmark names, model
  names, and citation markers, which remain attributed to their sources.

If you intend to publish or redistribute this repository, publish the pipeline and keep the
translated content and figures out of the public copy, or obtain the rights holder's
permission first.

## Bundled third-party font

`src/assets/fonts/` contains a subset of Source Han Sans SC (Adobe), which is licensed under
the SIL Open Font License, Version 1.1. The full license text ships beside it as
`src/assets/fonts/OFL.txt`. The subsetting tool (`tools/fonts.py`) only removes glyphs; it does
not change the license of the font.

## Python dependencies

Third-party packages listed in `requirements.txt` are not vendored. Each keeps its own license
and is installed by the user into the isolated environment under `.local/`.
