"""17-01 (GUI-01, D-01, D-15): shared fixtures for the operator-console mockup tests.

A test that uses ``mockup_path`` (directly or through ``ui``) fails, never skips and never errors,
when ``mockups/operator-console.html`` is absent: ``pytest_pyfunc_call`` raises the AssertionError
in the call phase (a failing fixture would be reported as ERROR, not failed), so a fail-first run
counts "failed" and names the missing file. ``browser`` launches nixpkgs Chromium through Playwright for Python:
a missing browser fails when ``DATABASISE_REQUIRE_BROWSER=1`` and skips otherwise. ``ui`` opens the
mockup in an offline context and records every non-local request and every page error; a JS
exception fails the test that caused it. Tests are plain synchronous functions (pytest-asyncio's
auto mode only wraps ``async def``) and never import playwright themselves; they use ``ui.expect``.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
MOCKUP = ROOT / "mockups" / "operator-console.html"
BROWSERS = Path.home() / ".cache" / "databasise" / "playwright-browsers"

_LOCAL_SCHEMES = ("file:", "data:", "blob:", "about:")


@pytest.fixture(scope="session")
def mockup_path() -> Path:
    return MOCKUP


@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem):
    # Fail, never skip: the fail-first run needs a failure that names the missing file.
    if "mockup_path" in pyfuncitem.fixturenames:
        assert MOCKUP.is_file(), f"{MOCKUP} is missing (GUI mockup not built yet)"


# Module scope: a live sync_playwright keeps its event loop registered, which breaks every async
# test that runs after tests/gui in the same session.
@pytest.fixture(scope="module")
def browser():
    if BROWSERS.exists():
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(BROWSERS))
    os.environ.setdefault("PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS", "1")
    require = os.environ.get("DATABASISE_REQUIRE_BROWSER") == "1"

    def unavailable(reason: str):
        if require:
            pytest.fail(f"browser required but unavailable: {reason}")
        pytest.skip(f"no Playwright browser: {reason}")

    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        unavailable(str(exc))

    pw = sync_playwright().start()
    try:
        instance = pw.chromium.launch()
    except PlaywrightError as exc:
        pw.stop()
        unavailable((str(exc).splitlines() or [""])[0])
    yield instance
    instance.close()
    pw.stop()


class MockUI:
    """Thin driver over one page of the mockup. Every method maps to a ``window.__mock`` hook or a locator."""

    def __init__(self, page, requests: list[str], errors: list[str]):
        self.page = page
        self.requests = requests
        self.errors = errors

    def el(self, mock_id: str):
        return self.page.locator(f'[data-mock-id="{mock_id}"]')

    def expect(self, target):
        from playwright.sync_api import expect

        return expect(self.el(target) if isinstance(target, str) else target)

    def nav(self, screen: str) -> None:
        self.el(f"shell.nav.{screen}").click()

    def show(self, screen: str) -> None:
        self.page.evaluate("(s) => window.__mock.show(s)", screen)

    def set_state(self, screen: str, state: str) -> None:
        self.page.evaluate("([s, t]) => window.__mock.setState(s, t)", [screen, state])

    def inject(self, screen: str, status: int, body) -> None:
        self.page.evaluate(
            "([s, r]) => window.__mock.inject(s, r)", [screen, {"status": status, "body": body}]
        )

    def load(self, screen: str, fixture: str) -> None:
        self.page.evaluate("([s, f]) => window.__mock.loadFixture(s, f)", [screen, fixture])

    def resize(self, width: int, height: int) -> None:
        self.page.set_viewport_size({"width": width, "height": height})

    def no_horizontal_scroll(self) -> bool:
        return self.page.evaluate(
            "() => document.documentElement.scrollWidth <= window.innerWidth"
        )


@pytest.fixture
def ui(mockup_path, request):
    if not mockup_path.is_file():
        # pytest_pyfunc_call reports the missing file as the test failure; no browser work first.
        yield None
        return
    from playwright.sync_api import expect

    browser = request.getfixturevalue("browser")

    context = browser.new_context(offline=True, viewport={"width": 1280, "height": 900})
    context.set_default_timeout(3000)
    expect.set_options(timeout=5000)
    page = context.new_page()
    requests: list[str] = []
    errors: list[str] = []
    page.on(
        "request",
        lambda request: requests.append(request.url)
        if not request.url.startswith(_LOCAL_SCHEMES)
        else None,
    )
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(mockup_path.as_uri())
    page.wait_for_function("typeof window.__mock === 'object'")
    yield MockUI(page, requests, errors)
    context.close()
    assert errors == [], f"JavaScript errors on the page: {errors}"
