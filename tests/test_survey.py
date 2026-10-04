"""Tests for the survey builder: folder deliverable, card invariant and failure guards."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools import build, survey

REPO_ROOT = Path(__file__).resolve().parents[1]

HUB_TEMPLATE = REPO_ROOT / "src" / "templates" / "survey-hub.html"
PAPER_TEMPLATE = REPO_ROOT / "src" / "templates" / "survey-paper.html"

INFO = {
    "title": "示例调研",
    "subtitle": "两条方向",
    "author": "某人",
    "directions": [{"id": "systems", "name": "系统"}, {"id": "vla", "name": "VLA"}],
}

SLUGS = {
    "gpipe": {
        "title_en": "GPipe: Efficient Training of Giant Neural Networks",
        "title_zh": "GPipe：巨型神经网络的高效训练",
        "venue": "NeurIPS",
        "year": 2019,
        "stage": "预训练",
        "cites": 2275,
        "influential_cites": 233,
        "cites_asof": "2026-09-19",
        "arxiv": "1811.06965",
        "motivation": "**动机**：模型放不进单卡",
        "approach": "流水线并行",
    },
    "lora": {
        "title_en": "LoRA: Low-Rank Adaptation of Large Language Models",
        "title_zh": "LoRA：大语言模型的低秩适配",
        "venue": "ICLR",
        "year": 2022,
        "stage": "后训练",
        "cites": 23074,
        "influential_cites": 3207,
        "cites_asof": "2026-09-19",
        "arxiv": "2106.09685",
        "motivation": "全量微调成本过高",
        "approach": "低秩增量",
    },
}


def _make_survey(
    root: Path,
    *,
    hub: str = "## 1 系统\n\n正文。\n\n{{paper:gpipe}}\n\n{{paper:lora}}\n",
    slugs: list[str] | None = None,
) -> Path:
    """Materialise a small survey tree and return its hub directory."""
    hub_dir = root / "hub"
    hub_dir.mkdir(parents=True, exist_ok=True)
    (hub_dir / "01-systems.md").write_text(hub, encoding="utf-8")

    papers_dir = root / "papers"
    for slug in slugs if slugs is not None else ["gpipe", "lora"]:
        directory = papers_dir / slug
        directory.mkdir(parents=True, exist_ok=True)
        meta = dict(SLUGS[slug])
        meta["links"] = []
        (directory / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        (directory / "abstract.md").write_text(
            f"## 摘要\n\n{slug} 的原文摘要译文。\n", encoding="utf-8"
        )
    return hub_dir


def _build(root: Path, dist: Path) -> dict:
    hub_dir = _make_survey(root)
    return survey.build(
        dist=dist,
        hub_dir=hub_dir,
        papers_dir=root / "papers",
        info=INFO,
        hub_template=HUB_TEMPLATE,
        paper_template=PAPER_TEMPLATE,
        build_date="2026-09-19",
    )


def test_deliverable_is_a_folder_with_a_page_per_paper(tmp_path: Path) -> None:
    """dist/llm-survey/ holds the hub, detail pages and a real assets/ tree."""
    assert survey.DEFAULT_DIST == survey.ROOT / "dist" / "llm-survey"
    dist = tmp_path / "dist" / "llm-survey"
    manifest = _build(tmp_path / "survey", dist)

    assert (dist / "index.html").is_file()
    assert (dist / "manifest.json").is_file()
    assert (dist / "papers" / "gpipe.html").is_file()
    assert (dist / "papers" / "lora.html").is_file()
    # Real files reached by relative path, never an inlined payload.
    assert (dist.parent / "assets" / "styles" / "reader.css").is_file()
    assert (dist.parent / "assets" / "styles" / "survey.css").is_file()
    assert (dist.parent / "assets" / "scripts" / "reader.js").is_file()
    assert not (dist / "assets/styles/reader.css").exists()
    detail = (dist / "papers/gpipe.html").read_text(encoding="utf-8")
    assert 'href="../../assets/styles/reader.css"' in detail
    assert 'href="../index.html"' in detail
    page = (dist / "index.html").read_text(encoding="utf-8")
    assert "data:image" not in page
    assert "base64" not in page

    # Reading order comes from the hub, not from the directory listing.
    assert manifest["papers"] == ["gpipe", "lora"]
    assert manifest["directions"] == ["系统", "VLA"]
    assert manifest["papers_without_abstract"] == []
    assert manifest["public_export"] is False
    assert (
        json.loads((dist / "manifest.json").read_text(encoding="utf-8"))["public_export"] is False
    )
    assert manifest["pages"] == ["index.html", "papers/gpipe.html", "papers/lora.html"]


def test_card_and_detail_page_come_from_the_same_metadata(tmp_path: Path) -> None:
    """One meta.json feeds both the hub card and the detail page, so they cannot drift."""
    dist = tmp_path / "dist" / "llm-survey"
    _build(tmp_path / "survey", dist)

    hub = (dist / "index.html").read_text(encoding="utf-8")
    detail = (dist / "papers" / "gpipe.html").read_text(encoding="utf-8")
    facts = SLUGS["gpipe"]

    # Metadata both views render, from the one meta.json: identity, venue, year and the count.
    for text in (facts["title_en"], facts["title_zh"], facts["venue"], "2019", "2,275"):
        assert text in hub, f"{text!r} missing from the hub"
        assert text in detail, f"{text!r} missing from the detail page"
    # The card's meta line is venue . year . citations; the stage is a detail-page field.
    assert facts["stage"] in detail
    assert "2,275" in detail

    # The card carries the motivation and the approach; the detail page carries the abstract.
    # Both are markdown, rendered rather than pasted raw.
    assert "<strong>动机</strong>：模型放不进单卡" in hub
    assert "流水线并行" in hub
    assert "gpipe 的原文摘要译文。" in detail

    # The count is date-stamped on the detail page because that is what rots fastest.
    assert "2,275" in detail
    assert facts["cites_asof"] in detail

    assert "{{paper:" not in hub
    assert "{{" not in hub
    assert "{{PAPER_TITLE}}" not in detail
    assert detail.count('class="paper-facts"') == 1
    assert 'href="../index.html"' in detail
    # Prev/next walks the hub's reading order.
    assert 'href="lora.html"' in detail


def test_a_paper_may_be_referenced_more_than_once(tmp_path: Path) -> None:
    """A problem-first hub repeats a paper under several problems without breaking prev/next.

    Reading order deduplicates, so the paper keeps one detail page and one place in the
    sequence; repeating it just renders the card again where the narrative needs it.
    """
    dist = tmp_path / "dist" / "llm-survey"
    manifest = _build(
        tmp_path / "survey",
        dist,
    )
    # Baseline: each paper is referenced once, in hub order.
    assert manifest["papers"] == ["gpipe", "lora"]

    root = tmp_path / "repeated"
    hub_dir = _make_survey(
        root,
        hub="## 1 系统\n\n{{paper:gpipe}}\n\n### 1.1 问题\n\n{{paper:gpipe}}\n\n{{paper:lora}}\n",
    )
    repeated = survey.build(
        dist=tmp_path / "dist-repeated",
        hub_dir=hub_dir,
        papers_dir=root / "papers",
        info=INFO,
        hub_template=HUB_TEMPLATE,
        paper_template=PAPER_TEMPLATE,
    )
    # Still two papers and two pages - the repeat is a card, not a second entry.
    assert repeated["papers"] == ["gpipe", "lora"]
    assert repeated["pages"] == ["index.html", "papers/gpipe.html", "papers/lora.html"]

    hub = (tmp_path / "dist-repeated" / "index.html").read_text(encoding="utf-8")
    assert hub.count("GPipe: Efficient Training of Giant Neural Networks") > 1

    # The repeated paper still sits between the start and lora, so nav is unaffected.
    detail = (tmp_path / "dist-repeated" / "papers" / "gpipe.html").read_text(encoding="utf-8")
    assert 'href="lora.html"' in detail
    assert 'href="gpipe.html"' not in detail


def test_hub_referencing_an_unknown_paper_fails_loudly(tmp_path: Path) -> None:
    """A ``{{paper:<slug>}}`` marker with no folder must not build a half-empty card."""
    root = tmp_path / "survey"
    hub_dir = _make_survey(
        root, hub="正文。\n\n{{paper:gpipe}}\n\n{{paper:nope}}\n", slugs=["gpipe"]
    )
    with pytest.raises(survey.SurveyError, match="hub references unknown papers"):
        survey.build(
            dist=tmp_path / "dist",
            hub_dir=hub_dir,
            papers_dir=root / "papers",
            info=INFO,
            hub_template=HUB_TEMPLATE,
            paper_template=PAPER_TEMPLATE,
        )


def test_surveyed_paper_the_hub_never_references_fails_loudly(tmp_path: Path) -> None:
    """An orphaned folder would otherwise be built and never linked."""
    root = tmp_path / "survey"
    hub_dir = _make_survey(root, hub="正文。\n\n{{paper:gpipe}}\n")
    with pytest.raises(survey.SurveyError, match="never references"):
        survey.build(
            dist=tmp_path / "dist",
            hub_dir=hub_dir,
            papers_dir=root / "papers",
            info=INFO,
            hub_template=HUB_TEMPLATE,
            paper_template=PAPER_TEMPLATE,
        )


def test_unresolved_template_placeholder_fails_loudly(tmp_path: Path) -> None:
    """A forgotten token must not reach the reader as literal braces."""
    template = tmp_path / "page.html"
    template.write_text("<title>{{TITLE}}</title>{{FORGOTTEN}}", encoding="utf-8")
    with pytest.raises(survey.SurveyError, match=r"unresolved template placeholders.*FORGOTTEN"):
        survey.render(template, {"{{TITLE}}": "标题"})


def test_survey_stylesheet_is_kept_out_of_the_shared_style_directory() -> None:
    """build.copy_assets copies all of src/styles/, so survey.css must live elsewhere."""
    assert survey.SURVEY_STYLES.parent != build.STYLES_DIR
    assert survey.SURVEY_STYLES.is_file()


def test_missing_survey_identity_file_fails_loudly(tmp_path: Path) -> None:
    """Building without an identity file names the missing path."""
    with pytest.raises(survey.SurveyError, match="missing survey identity file"):
        survey.load_info(tmp_path / "absent.json")
