"""Unit and integration tests for the PDF extraction helpers."""

from __future__ import annotations

from pathlib import Path

import fitz

from tools import extract


def _synthetic_pdf() -> fitz.Document:
    """Build a one-page PDF that mimics a figure with sub-labels above a caption."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 72), "Body paragraph above the figure.", fontsize=11)
    page.draw_rect(fitz.Rect(100, 120, 500, 300), color=(0, 0, 0), fill=(0.9, 0.9, 0.9))
    page.insert_text((110, 330), "(a)", fontsize=10)
    page.insert_text((480, 330), "(b)", fontsize=10)
    page.insert_text((72, 360), "Figure 1 | A synthetic caption.", fontsize=10)
    page.insert_text((72, 400), "trailing body text with an equation (7)", fontsize=11)
    return doc


def test_expand_grows_all_sides() -> None:
    rect = fitz.Rect(10, 20, 30, 40)
    grown = extract._expand(rect, 5)
    assert (grown.x0, grown.y0, grown.x1, grown.y1) == (5, 15, 35, 45)


def test_figure_crop_covers_art_and_excludes_caption(tmp_path: Path) -> None:
    doc = _synthetic_pdf()
    records = extract.extract_figures(doc, dpi=72, out_dir=tmp_path)
    assert len(records) == 1
    record = records[0]
    assert record.number == 1
    assert record.page == 1
    # The crop starts at or above the artwork and stops before the caption baseline.
    assert record.bbox[1] <= 120
    assert record.bbox[3] <= 352
    assert record.bbox[1] < record.bbox[3]
    assert (tmp_path / "figure-01.png").exists()
    assert record.changed is True
    doc.close()


def test_figure_extraction_is_idempotent(tmp_path: Path) -> None:
    doc = _synthetic_pdf()
    extract.extract_figures(doc, dpi=72, out_dir=tmp_path)
    second = extract.extract_figures(doc, dpi=72, out_dir=tmp_path)
    assert all(record.changed is False for record in second)
    doc.close()


def test_find_equations_reads_trailing_numbers() -> None:
    doc = _synthetic_pdf()
    equations = extract.find_equations(doc)
    assert [e.number for e in equations] == [7]
    assert equations[0].page == 1
    doc.close()


def test_write_if_changed_reports_changes(tmp_path: Path) -> None:
    target = tmp_path / "a.bin"
    assert extract._write_if_changed(target, b"one") is True
    assert extract._write_if_changed(target, b"one") is False
    assert extract._write_if_changed(target, b"two") is True
    assert target.read_bytes() == b"two"


def test_block_texts_skips_blank_blocks() -> None:
    doc = _synthetic_pdf()
    blocks = extract._block_texts(doc[0])
    assert blocks
    assert all(text.strip() for _rect, text in blocks)
    doc.close()
