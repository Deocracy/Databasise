"""17-01 (GUI-01, D-01, D-15): Playwright launches nixpkgs Chromium under pytest. Needs no mockup."""

from __future__ import annotations


def test_chromium_launches_and_renders_a_data_page(browser):
    context = browser.new_context(offline=True)
    try:
        page = context.new_page()
        page.set_content('<p id="x">ok</p>')
        assert page.locator("#x").text_content() == "ok"
    finally:
        context.close()
