"""Check the project's instruction-only skill interface, not model writing quality."""

import json
import re
from pathlib import Path

import pytest

from tools import build

ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / ".agents" / "skills"
REQUIRED = {
    "chinese-technical-writing": {"chinese-writing.md", "source-analysis.md"},
    "technical-translation": {"chinese-writing.md", "reader.md"},
    "technical-review": {
        "chinese-writing.md",
        "review-method.md",
        "source-analysis.md",
    },
}


@pytest.mark.parametrize("name", REQUIRED)
def test_portable_skill_metadata(name):
    """Keep a deliberately simple frontmatter subset without another YAML dependency."""
    path = SKILL_ROOT / name / "SKILL.md"
    raw = path.read_bytes()
    assert b"\r" not in raw
    text = raw.decode("utf-8")
    opening, frontmatter, body = text.split("---\n", 2)
    assert opening == ""
    fields = dict(line.split(": ", 1) for line in frontmatter.strip().splitlines())
    assert fields["name"] == name
    assert re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name)
    assert len(name) <= 64
    description = json.loads(fields["description"])
    assert isinstance(description, str)
    assert 1 <= len(description) <= 1024
    assert fields["license"] == "MIT"
    assert body.strip()
    assert len(text.splitlines()) < 500


@pytest.mark.parametrize("name", REQUIRED)
def test_skills_link_to_the_owning_standards(name):
    """Resolve links from the skill directory, not from a caller's working directory."""
    path = SKILL_ROOT / name / "SKILL.md"
    links = re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8"))
    targets = []
    for link in links:
        assert "://" not in link, "External method attribution belongs in the guide"
        target = (path.parent / link.split("#", 1)[0]).resolve()
        assert target.is_relative_to(ROOT / "docs")
        assert target.is_file()
        targets.append(target.name)
        if "#" in link:
            fragment = link.split("#", 1)[1]
            html = build.make_markdown().convert(target.read_text(encoding="utf-8"))
            assert fragment in re.findall(r'\bid="([^"]+)"', html)
    assert REQUIRED[name] <= set(targets)
    assert "workflow.md" in targets


def test_shared_skills_are_instruction_only_and_documented():
    """Do not silently turn these workflows into installers or executable integrations."""
    files = sorted(SKILL_ROOT.rglob("*"))
    assert {p.parent.name for p in files if p.is_file()} == set(REQUIRED)
    assert all(p.name == "SKILL.md" for p in files if p.is_file())
    guide = (ROOT / "docs" / "authoring-skills.md").read_text(encoding="utf-8")
    for name in REQUIRED:
        assert f"/skill:{name} " in guide
        assert f"../.agents/skills/{name}/SKILL.md" in guide
