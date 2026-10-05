"""Regression tests for modular manuscripts and offline code rendering."""

import re
from html import unescape
from pathlib import Path

import pytest

from tools import build, manuscript


def test_nested_includes_share_toc_and_change_hash(tmp_path: Path) -> None:
    content = tmp_path / "work/content"
    fragments = content / "frameworks"
    fragments.mkdir(parents=True)
    (content / "05-frameworks.md").write_text(
        "## 框架\n\n{{include:frameworks/vllm.md}}\n", encoding="utf-8"
    )
    (fragments / "vllm.md").write_text("### vLLM\n\n{{include:cache.md}}\n", encoding="utf-8")
    cache = fragments / "cache.md"
    cache.write_text("#### 分页缓存\n\n缓存正文。\n", encoding="utf-8")
    output = tmp_path / "reader"
    metadata = {"title": "测试", "kind": "analysis"}
    first = build.build(output, content, metadata=metadata)
    page = (output / "index.html").read_text(encoding="utf-8")
    assert page.count("<section id=") == 1
    assert 'href="#分页缓存"' in page
    assert first["sections"] == ["05-frameworks.md"]
    assert first["content_dependencies"]["05-frameworks.md"] == [
        "05-frameworks.md",
        "frameworks/vllm.md",
        "frameworks/cache.md",
    ]
    cache.write_text("#### 分页缓存\n\n修改后的缓存。\n", encoding="utf-8")
    second = build.build(output, content, metadata=metadata)
    assert first["content_hash"] != second["content_hash"]
    assert second["content_hash"] == build.build(output, content, metadata=metadata)["content_hash"]


@pytest.mark.parametrize(
    "target", ["../outside.md", "/outside.md", "C:/secret.md", r"..\secret.md", "bad.txt"]
)
def test_include_rejects_unsafe_paths(tmp_path: Path, target: str) -> None:
    source = tmp_path / "01.md"
    source.write_text("{{include:" + target + "}}", encoding="utf-8")
    with pytest.raises(ValueError):
        manuscript.expand(source, tmp_path)


def test_include_rejects_missing_and_cycles(tmp_path: Path) -> None:
    a, b = tmp_path / "a.md", tmp_path / "b.md"
    a.write_text("{{include:b.md}}", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="missing include"):
        manuscript.expand(a, tmp_path)
    b.write_text("{{include:a.md}}", encoding="utf-8")
    with pytest.raises(ValueError, match=r"include cycle: a\.md -> b\.md -> a\.md"):
        manuscript.expand(a, tmp_path)


def test_include_is_literal_in_code_and_inline_text(tmp_path: Path) -> None:
    source = tmp_path / "a.md"
    text = (
        "```markdown\n{{include:absent.md}}\n```\n"
        "~~~\n{{include:absent.md}}\n~~~\n"
        "    {{include:absent.md}}\n"
        "正文 {{include:absent.md}}\n"
    )
    source.write_text(text, encoding="utf-8")
    expanded, deps = manuscript.expand(source, tmp_path)
    assert expanded == text
    assert deps == [source]


def test_include_rejects_symlink_escape(tmp_path: Path) -> None:
    root = tmp_path / "content"
    root.mkdir()
    outside = tmp_path / "secret.md"
    outside.write_text("private", encoding="utf-8")
    try:
        (root / "linked.md").symlink_to(outside)
    except OSError:
        pytest.skip("Creating symlinks requires platform privileges")
    source = root / "01.md"
    source.write_text("{{include:linked.md}}", encoding="utf-8")
    with pytest.raises(ValueError, match="escapes content root"):
        manuscript.expand(source, root)


def test_include_expansion_limits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "a.md"
    child = tmp_path / "b.md"
    source.write_text("{{include:b.md}}", encoding="utf-8")
    child.write_text("body", encoding="utf-8")
    monkeypatch.setattr(manuscript, "MAX_DEPTH", 1)
    with pytest.raises(ValueError, match="depth exceeds"):
        manuscript.expand(source, tmp_path)
    monkeypatch.setattr(manuscript, "MAX_DEPTH", 24)
    monkeypatch.setattr(manuscript, "MAX_BYTES", 1)
    with pytest.raises(ValueError, match="manuscript exceeds"):
        manuscript.expand(source, tmp_path)


def test_offline_highlight_preserves_code_and_escapes_html() -> None:
    code = "// include/utils.c:32 — add\nint add(int a, int b) { return a < b ? a : b; }\n"
    html = build.make_markdown().convert("```c\n" + code + "```")
    assert '<pre><code class="language-c">' in html
    assert 'class="syn-kt"' in html
    visible = unescape(re.sub("<[^>]+>", "", html))
    assert visible == code
    html = build.make_markdown().convert('```html\n<script>alert("x")</script>\n```')
    assert "<script>" not in html
    assert "&lt;" in html
    assert "alert" in html
    assert "data:" not in html


def test_unknown_and_unlabelled_code_remain_plaintext() -> None:
    md = build.make_markdown()
    assert "syn-" not in md.convert("```invented-language\nx < 2\n```")
    assert "syn-" not in md.reset().convert("```\nx < 2\n```")
