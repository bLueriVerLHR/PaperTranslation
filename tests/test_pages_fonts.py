"""Font subset and license retention tests using a generated synthetic font."""

from pathlib import Path

import pytest

pytest.importorskip("fontTools")
pytest.importorskip("brotli")

from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.fontBuilder import FontBuilder
from fontTools.otlLib.builder import buildMathTable
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


def test_math_face_retains_implicit_alphabets_assemblies_and_script_features(
    tmp_path: Path,
) -> None:
    builder = FontBuilder(1000, isTTF=True)
    names = [".notdef", "A", "italicA", "paren", "paren.big", "extender"]
    builder.setupGlyphOrder(names)
    builder.setupCharacterMap({65: "A", 0x1D434: "italicA", 40: "paren"})
    glyphs = {}
    for name in names:
        pen = TTGlyphPen(None)
        pen.moveTo((0, 0))
        pen.lineTo((500, 0))
        pen.lineTo((250, 700))
        pen.closePath()
        glyphs[name] = pen.glyph()
    builder.setupGlyf(glyphs)
    builder.setupHorizontalMetrics(dict.fromkeys(names, (600, 0)))
    builder.setupHorizontalHeader(ascent=800, descent=-200)
    builder.setupNameTable({"familyName": "Synthetic Math", "styleName": "Regular"})
    builder.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=800, usWinDescent=200)
    builder.setupPost()
    builder.setupMaxp()
    buildMathTable(
        builder.font,
        constants={"AxisHeight": 250, "FractionRuleThickness": 40},
        minConnectorOverlap=20,
        vertGlyphVariants={"paren": [("paren", 700), ("paren.big", 1000)]},
        vertGlyphAssembly={"paren": ([("extender", 1, 100, 100, 500)], 0)},
    )
    addOpenTypeFeaturesFromString(builder.font, "feature ssty { sub A by italicA; } ssty;")
    original = tmp_path / "math.ttf"
    builder.save(original)
    output = tmp_path / "math.woff2"
    pages_fonts.write_subset(original, output, {65}, "Paper Math", preserve_math=True)
    with TTFont(output) as font:
        assert set(font.getBestCmap()) == {65, 40, 0x1D434}
        assert len(font.getGlyphOrder()) == len(names)
        table = font["MATH"].table
        assert table.MathConstants.AxisHeight.Value == 250
        assert table.MathConstants.FractionRuleThickness.Value == 40
        assert table.MathVariants.MinConnectorOverlap == 20
        construction = table.MathVariants.VertGlyphConstruction[0]
        assert construction.MathGlyphVariantRecord[1].AdvanceMeasurement == 1000
        assert construction.GlyphAssembly.PartRecords[0].glyph in font.getGlyphOrder()
        assert "ssty" in {
            entry.FeatureTag for entry in font["GSUB"].table.FeatureList.FeatureRecord
        }
        assert font["name"].getDebugName(1) == "Paper Math"


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
