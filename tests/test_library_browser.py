"""Optional local Chrome regression tests for the library modal (synthetic content only).

Install Playwright and set PAPER_BROWSER_EXECUTABLE when the browser is not discovered.
All servers, profiles and generated pages stay local and temporary; no downloads are needed.
"""

from __future__ import annotations

import functools
import http.server
import os
import shutil
import threading
from pathlib import Path

import pytest

from tools import pages

playwright = pytest.importorskip("playwright.sync_api")
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def browser():
    """Launch an isolated headless instance, never the user's profile."""
    candidates = [
        os.environ.get("PAPER_BROWSER_EXECUTABLE"),
        shutil.which("chromium"),
        shutil.which("google-chrome"),
        "C:/Program Files/Google/Chrome/Application/chrome.exe",
        "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    ]
    executable = next((p for p in candidates if p and Path(p).is_file()), None)
    if executable is None:
        pytest.skip("optional browser executable is unavailable")
    with playwright.sync_playwright() as driver:
        instance = driver.chromium.launch(executable_path=executable, headless=True)
        yield instance
        instance.close()


@pytest.fixture
def library_url(tmp_path: Path):
    """Serve a generated, font-free synthetic library on loopback."""
    entries = [{"path": f"project-{i}/index.html", "title": f"项目 {i}"} for i in range(10)]
    entries.extend(
        {"path": f"project-5/papers/paper-{i}.html", "title": f"专题论文{i}：Synthetic title"}
        for i in range(66)
    )
    (tmp_path / "index.html").write_text(pages.render_home(entries), encoding="utf-8")
    for entry in entries:
        target = tmp_path / entry["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            f'<html lang="zh-Hans"><title>{entry["title"]}</title></html>', encoding="utf-8"
        )
    for source, relative in (
        ("src/styles/reader.css", "assets/styles/reader.css"),
        ("src/pages/library.css", "assets/styles/library.css"),
        ("src/scripts/reader.js", "assets/scripts/reader.js"),
        ("src/pages/library.js", "assets/scripts/library.js"),
    ):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / source, target)
    font_css = tmp_path / "assets/fonts/fonts.css"
    font_css.parent.mkdir(parents=True, exist_ok=True)
    font_css.write_text("/* synthetic fixture: use installed fonts */", encoding="utf-8")
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(tmp_path))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/"
    finally:
        server.shutdown()
        server.server_close()
        worker.join()


@pytest.mark.parametrize("width", [320, 390, 1280])
def test_modal_scroll_dismiss_focus_and_search(browser, library_url: str, width: int) -> None:
    """Exercise internal scrolling and every close path without moving the homepage."""
    with browser.new_context(
        viewport={"width": width, "height": 844}, reduced_motion="reduce"
    ) as context:
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(library_url, wait_until="networkidle")
        trigger = page.locator(".library-more")
        trigger.scroll_into_view_if_needed()
        initial_y = page.evaluate("window.scrollY")
        initial_height = page.locator(".library-grid").evaluate(
            "e => e.getBoundingClientRect().height"
        )
        for dismissal in ("backdrop", "escape", "button"):
            trigger.click()
            dialog = page.locator("dialog[open]")
            playwright.expect(dialog).to_be_visible()
            assert dialog.locator("li a").count() == 66
            bounds = dialog.bounding_box()
            assert bounds is not None
            assert abs(bounds["x"] + bounds["width"] / 2 - width / 2) <= 2
            assert abs(bounds["y"] + bounds["height"] / 2 - 844 / 2) <= 2
            assert bounds["height"] <= 844 * 0.81
            scroller = dialog.locator(".library-dialog-list")
            assert scroller.evaluate("e => e.scrollHeight > e.clientHeight")
            scroller.evaluate("e => e.scrollTop = e.scrollHeight")
            assert scroller.evaluate("e => e.scrollTop > 0")
            assert page.locator("body").evaluate("e => e.style.position") == "fixed"
            assert (
                page.locator(".library-grid").evaluate("e => e.getBoundingClientRect().height")
                == initial_height
            )
            page.keyboard.press("Tab")
            assert dialog.evaluate("e => e.contains(document.activeElement)")
            page.mouse.move(4, 4)
            page.mouse.wheel(0, 1000)
            if dismissal == "backdrop":
                page.mouse.click(4, 4)
            elif dismissal == "escape":
                page.keyboard.press("Escape")
            else:
                dialog.locator(".library-dialog-close").click()
            playwright.expect(page.locator("dialog[open]")).to_have_count(0)
            page.wait_for_function("y => Math.abs(window.scrollY - y) < 1", arg=initial_y)
            playwright.expect(trigger).to_be_focused()
            assert page.locator("body").evaluate("e => e.style.position") == ""
        page.locator("#library-search").fill("专题论文65")
        assert page.locator(".library-card:visible").count() == 1
        assert page.locator("dialog[open]").count() == 0
        trigger.click()
        page.locator("dialog[open] a").last.click()
        page.wait_for_url("**/project-5/papers/paper-65.html")
        assert not errors


@pytest.mark.parametrize("mode", ["no-js", "no-dialog"])
def test_links_remain_accessible_without_enhancement(browser, library_url: str, mode: str) -> None:
    """Keep one canonical list usable when the progressive modal cannot run."""
    with browser.new_context(java_script_enabled=mode != "no-js") as context:
        if mode == "no-dialog":
            context.add_init_script("HTMLDialogElement.prototype.showModal = undefined")
        page = context.new_page()
        page.goto(library_url, wait_until="networkidle")
        details = page.locator(".library-pages")
        details.locator("summary").click()
        assert details.locator("a:visible").count() == 66
        details.locator("a").last.click()
        page.wait_for_url("**/project-5/papers/paper-65.html")
