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


def test_figure_crop_stops_below_a_vector_running_head(tmp_path: Path) -> None:
    """InDesign renders running-head digits as artwork that sits on top of its own text block.

    The artwork must not join the figure cluster, or the crop starts above the page header.
    """
    doc = fitz.open()
    page = doc.new_page(width=439, height=666)
    page.insert_text((47, 40), "191  Page 1 of 60  W. Chen et al.", fontsize=10)
    head = page.get_text("blocks", sort=True)[0]
    header = fitz.Rect(head[0], head[1], head[2], head[3])
    # The digit artwork hugs the header text and sits just above the figure.
    page.draw_rect(fitz.Rect(header.x0, header.y0, header.x0 + 100, header.y1), color=(0, 0, 0))
    page.draw_rect(fitz.Rect(49, 52, 390, 300), color=(0, 0, 0), fill=(0.9, 0.9, 0.9))
    page.insert_text((47, 330), "Fig. 1\u2002A synthetic caption.", fontsize=10)
    records = extract.extract_figures(doc, dpi=72, out_dir=tmp_path)
    assert len(records) == 1
    assert records[0].bbox[1] > header.y1
    doc.close()


def test_figure_extraction_accepts_elsevier_caption_style(tmp_path: Path) -> None:
    """Elsevier prints ``Fig. 1. Caption`` rather than ``Figure 1 | Caption``."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.draw_rect(fitz.Rect(100, 120, 500, 300), color=(0, 0, 0), fill=(0.9, 0.9, 0.9))
    page.insert_text((72, 360), "Fig. 1. The layout of Mamba-2 and Mamba model.", fontsize=10)
    records = extract.extract_figures(doc, dpi=72, out_dir=tmp_path)
    assert [r.number for r in records] == [1]
    assert records[0].bbox[1] <= 120
    doc.close()


def test_figure_extraction_accepts_springer_caption_style(tmp_path: Path) -> None:
    """Springer/Springer-Nature print ``Fig. 1\u2002Caption`` with an EN SPACE, not punctuation."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.draw_rect(fitz.Rect(100, 120, 500, 300), color=(0, 0, 0), fill=(0.9, 0.9, 0.9))
    page.insert_text(
        (72, 360), "Fig. 1\u2002An overview of the topic.", fontsize=10, fontname="helv"
    )
    records = extract.extract_figures(doc, dpi=72, out_dir=tmp_path)
    assert [r.number for r in records] == [1]
    assert records[0].bbox[1] <= 120
    doc.close()


def test_figure_extraction_rejects_a_plain_space_separator(tmp_path: Path) -> None:
    """``Fig. 1 shows ...`` is prose; only punctuation or a non-ASCII space marks a caption."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.draw_rect(fitz.Rect(100, 120, 500, 300), color=(0, 0, 0), fill=(0.9, 0.9, 0.9))
    page.insert_text((72, 360), "Fig. 1 An overview of the topic.", fontsize=10)
    assert extract.extract_figures(doc, dpi=72, out_dir=tmp_path) == []
    doc.close()


def test_body_text_mentioning_a_figure_is_not_a_caption(tmp_path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.draw_rect(fitz.Rect(100, 120, 500, 300), color=(0, 0, 0), fill=(0.9, 0.9, 0.9))
    page.insert_text((72, 360), "Fig. 1 shows the layout of the Mamba block.", fontsize=10)
    assert extract.extract_figures(doc, dpi=72, out_dir=tmp_path) == []
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


def test_find_equations_ignores_prose_enumerations() -> None:
    """A line-final ``(N)`` after a colon or a sentence end is prose, not an equation label.

    Both patterns occur in the on-device LLM survey, which has no numbered display equations.
    """
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 72), "They fall into two groups: (1)", fontsize=11)
    page.insert_text((72, 100), "early exit to reduce cloud calls by 40\u201350%. (2)", fontsize=11)
    page.insert_text((72, 128), "x = y + z (3)", fontsize=11)
    equations = extract.find_equations(doc)
    assert [e.number for e in equations] == [3]
    doc.close()


def test_page_text_orders_two_columns_left_first() -> None:
    """Two-column pages must read left column first, not interleaved line by line."""
    doc = fitz.open()
    page = doc.new_page(width=600, height=800)
    page.insert_text((330, 100), "R1", fontsize=11)
    page.insert_text((330, 130), "R2", fontsize=11)
    page.insert_text((40, 100), "L1", fontsize=11)
    page.insert_text((40, 130), "L2", fontsize=11)
    text = extract._page_text(page, columns=2)
    assert text.index("L1") < text.index("L2") < text.index("R1") < text.index("R2")
    doc.close()


def test_page_text_keeps_single_column_order() -> None:
    doc = fitz.open()
    page = doc.new_page(width=600, height=800)
    page.insert_text((40, 100), "first", fontsize=11)
    page.insert_text((40, 130), "second", fontsize=11)
    text = extract._page_text(page, columns=1)
    assert text.index("first") < text.index("second")
    doc.close()


def test_page_text_bands_around_a_full_width_block() -> None:
    """A full-width block splits the page: bands above and below are read in column order."""
    doc = fitz.open()
    page = doc.new_page(width=600, height=800)
    caption = "SPANNING CAPTION LONG ENOUGH TO CROSS THE MIDDLE OF THE PAGE"
    page.insert_textbox(fitz.Rect(20, 290, 580, 330), caption, fontsize=11)
    page.insert_textbox(fitz.Rect(20, 60, 280, 200), "L1 line one\nL1 line two", fontsize=11)
    page.insert_textbox(fitz.Rect(320, 60, 580, 200), "R1 line one\nR1 line two", fontsize=11)
    page.insert_textbox(fitz.Rect(20, 400, 280, 540), "L2 line one\nL2 line two", fontsize=11)
    page.insert_textbox(fitz.Rect(320, 400, 580, 540), "R2 line one\nR2 line two", fontsize=11)

    text = extract._page_text(page, columns=2)
    order = [text.index(token) for token in ("L1", "R1", "SPANNING", "L2", "R2")]
    assert order == sorted(order), text
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
