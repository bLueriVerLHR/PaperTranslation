"""Synthetic fixed-version caption compatibility and source preservation tests."""

import re
from html import unescape
from pathlib import Path

import pytest

from tools import assets, build, source_cards

COMMIT = "a" * 40
CODE = "            value = request.count\n            return value\n"


def caption(url: str | None = None, last: int = 14) -> str:
    """Render the exact legacy format with a fictional repository and source."""
    url = url or f"https://github.com/example/repo/blob/{COMMIT}/src/main.py#L13-L{last}"
    return (
        "**源码摘录：约束请求预算。** "
        f"仓库 `repo`，固定提交 `{COMMIT}`；文件 `src/main.py`，"
        f"第 13–{last} 行，符号 `Scheduler.run`。[对应源码]({url})。\n\n"
        f"```python\n{CODE}```\n"
    )


def test_complete_caption_becomes_native_card_without_modifying_code() -> None:
    original = build.make_markdown().convert(caption())
    upgraded = source_cards.upgrade(original)
    assert '<figure class="source-excerpt">' in upgraded
    assert '<details class="code-source">' in upgraded
    assert '<span class="source-file">main.py</span>' in upgraded
    assert COMMIT in upgraded and "src/main.py" in upgraded and "Scheduler.run" in upgraded
    before = re.search(r"<pre>.*?</pre>", original, re.S)[0]
    after = re.search(r"<pre>.*?</pre>", upgraded, re.S)[0]
    assert before == after
    assert unescape(re.sub(r"<[^>]+>", "", after)) == CODE
    assert source_cards.upgrade(upgraded) == upgraded


@pytest.mark.parametrize(
    "url",
    [
        f"http://github.com/example/repo/blob/{COMMIT}/src/main.py#L13-L14",
        f"https://github.com/example/repo/blob/{'b' * 40}/src/main.py#L13-L14",
        f"https://github.com/example/repo/blob/{COMMIT}/other.py#L13-L14",
        f"https://github.com/example/repo/blob/{COMMIT}/src/main.py#L1-L2",
        f"https://github.com.example.org/example/repo/blob/{COMMIT}/src/main.py#L13-L14",
        f"https://github.com:8443/example/repo/blob/{COMMIT}/src/main.py#L13-L14",
        "https://[invalid-ipv6/",
    ],
)
def test_disagreeing_or_unsafe_locators_remain_unmodified(url: str) -> None:
    original = build.make_markdown().convert(caption(url))
    assert source_cards.upgrade(original) == original


def test_incomplete_caption_and_wrong_line_count_are_not_guessed() -> None:
    for text in (caption().replace("，符号 `Scheduler.run`", ""), caption(last=15)):
        original = build.make_markdown().convert(text)
        assert source_cards.upgrade(original) == original


def test_runtime_refresh_preserves_private_sources(tmp_path: Path) -> None:
    project = tmp_path / "legacy"
    work = project / "work"
    work.mkdir(parents=True)
    original = caption()
    (work / "source.md").write_text(original, encoding="utf-8")
    page = project / "index.html"
    legacy = build.make_markdown().convert(original)
    page.write_text(legacy, encoding="utf-8")
    result = assets.refresh(tmp_path)
    assert result["pages"] == ["legacy/index.html"]
    assert 'class="source-excerpt"' in page.read_text(encoding="utf-8")
    assert (work / "source.md").read_text(encoding="utf-8") == original
    assert not assets.refresh(tmp_path)["pages"]


def test_builder_and_runtime_refresh_apply_the_same_idempotent_upgrade(tmp_path: Path) -> None:
    content = tmp_path / "work/content"
    content.mkdir(parents=True)
    (content / "01-code.md").write_text("## 源码\n\n" + caption(), encoding="utf-8")
    out = tmp_path / "reader"
    build.build(out, content, metadata={"title": "合成稿", "kind": "analysis"})
    first = (out / "index.html").read_text(encoding="utf-8")
    assert 'class="source-excerpt"' in first
    assets.refresh(tmp_path)
    assert (out / "index.html").read_text(encoding="utf-8") == first
