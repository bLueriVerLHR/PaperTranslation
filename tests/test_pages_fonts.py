"""Font subset and license retention tests using a generated synthetic font."""

from pathlib import Path

import pytest

pytest.importorskip("fontTools")
pytest.importorskip("brotli")

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

from tools import pages_fonts


def test_subset_renames_family_preserves_license_and_only_used_glyphs(tmp_path: Path) -> None:
    builder = FontBuilder(1000, isTTF=True)
    builder.setupGlyphOrder([".notdef", "A", "zh"])
    builder.setupCharacterMap({65: "A", 0x4E2D: "zh"})
    glyphs = {}
    for name in (".notdef", "A", "zh"):
        pen = TTGlyphPen(None)
        pen.moveTo((0, 0))
        pen.lineTo((500, 0))
        pen.lineTo((250, 700))
        pen.closePath()
        glyphs[name] = pen.glyph()
    builder.setupGlyf(glyphs)
    builder.setupHorizontalMetrics(dict.fromkeys(glyphs, (600, 0)))
    builder.setupHorizontalHeader(ascent=800, descent=-200)
    builder.setupNameTable(
        {
            "familyName": "Reserved Fixture",
            "styleName": "Regular",
            "uniqueFontIdentifier": "ReservedFixture",
            "fullName": "Reserved Fixture Regular",
            "psName": "ReservedFixture-Regular",
            "copyright": "Synthetic copyright",
            "licenseDescription": "Synthetic license text",
            "licenseInfoURL": "https://example.invalid/license",
        }
    )
    builder.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=800, usWinDescent=200)
    builder.setupPost()
    builder.setupMaxp()
    original = tmp_path / "fixture.ttf"
    builder.save(original)
    output = tmp_path / "subset.woff2"
    pages_fonts.write_subset(original, output, {65}, "Paper Fixture")
    with TTFont(output) as font:
        assert set(font.getBestCmap()) == {65}
        assert font["name"].getDebugName(1) == "Paper Fixture"
        assert font["name"].getDebugName(0) == "Synthetic copyright"
        assert font["name"].getDebugName(13) == "Synthetic license text"


def test_font_rule_swaps_text_and_limits_unicode() -> None:
    rule = pages_fonts.font_rule("Paper Fixture", "a.woff2", 700, "italic", {65, 66})
    assert "font-display: swap" in rule
    assert "unicode-range: U+41,U+42" in rule
    assert "font-weight: 700" in rule


def test_corrupt_font_cache_fails_without_using_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lock = tmp_path / "lock.json"
    lock.write_text('[{"file":"font.ttf","url":"https://example.invalid/font","sha256":"bad"}]')
    monkeypatch.setattr(pages_fonts, "LOCK", lock)
    (tmp_path / "font.ttf").write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="checksum mismatch"):
        pages_fonts.download_sources(tmp_path)
