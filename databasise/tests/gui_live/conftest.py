"""18-02 (LIVE-01, D-18, D-19): the in-process live harness for the operator console.

``start_live_app`` binds a loopback socket first, so ``build_app`` knows the real port for its Origin
guard, then runs the launcher app under uvicorn in a daemon thread with a temp store root, stub
clients and the shared corpus fake (``_corpus_fake``). No provider is called and no test here uses
the live marker (18-RESEARCH Pattern 5). A page error or a non-loopback request fails the test
itself in the call phase, not its teardown (D-18, 18-RESEARCH Pattern 6; the Phase 17 conftest
asserts in teardown, which reports an error instead of a failure). A harness start failure is kept
in ``LiveApp.start_error`` and raised from ``pytest_pyfunc_call``, so a fail-first run counts
"failed", not "error".
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import socket
import threading
import time
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

import httpx
import pytest

from databasise.tests.gui_live import _corpus_fake
from databasise.tests.seam.test_hipporag_write_path import (
    _DOCUMENT_TEXT,
    _StubEmbeddingClient,
    _StubIngestQueryLLMClient,
)

ROOT = Path(__file__).resolve().parents[3]
BUILT = ROOT / "databasise" / "console" / "operator-console.html"
BROWSERS = Path.home() / ".cache" / "databasise" / "playwright-browsers"
HIPPORAG = {"capability": ["reads_graph", "reads_kv"]}
SEED_DOCUMENT_ID = "seed-hipporag"

_LOCAL_SCHEMES = ("data:", "blob:", "about:")
_LOCAL_HOSTS = ("127.0.0.1", "localhost")


def stub_clients() -> dict[str, Any]:
    return {"embedding": _StubEmbeddingClient(), "llm": _StubIngestQueryLLMClient()}


class LiveApp:
    """One launcher app served by uvicorn on a pre-bound loopback socket."""

    def __init__(self, root: Path):
        self.root = root
        self.app: Any = None
        self.port = 0
        self.base = ""
        self.corpus: dict[str, dict[str, Any]] = {}
        self.log_file: Path | None = None
        self.start_error: str | None = None
        self.http: httpx.Client | None = None
        self.server: Any = None
        self.thread: threading.Thread | None = None
        self.sock: socket.socket | None = None

    def _ok(self, response: httpx.Response) -> dict[str, Any]:
        assert 200 <= response.status_code < 300, f"{response.request.method} {response.request.url}: {response.status_code} {response.text}"
        return response.json()

    def ingest(self, text: str, document_id: str, selector: dict | None = None) -> dict[str, Any]:
        body = {"document": {"document_id": document_id, "text": text}, "selector": selector}
        return self._ok(self.http.post("/documents", json=body))

    def query(self, text: str, selector: dict | None = None) -> dict[str, Any]:
        return self._ok(self.http.post("/query", json={"query": {"text": text}, "selector": selector}))

    def promote(self, alias: str, trace_ids: list[str], change_origin: str = "human_edit") -> dict[str, Any]:
        body = {"alias": alias, "trace_ids": trace_ids, "change_origin": change_origin}
        return self._ok(self.http.post("/promote", json=body))

    def _swap(self, method: str, replacement: Callable[..., Any]):
        engine = self.app.state.engine
        had_own = method in vars(engine)
        original = getattr(engine, method)
        setattr(engine, method, replacement(original))
        return engine, had_own, original

    @contextlib.contextmanager
    def hold(self, method: str):
        """Keeps every call of ``engine.<method>`` in flight until the yielded event is set."""
        release = threading.Event()

        async def wait_then_call(original, *args, **kwargs):
            while not release.is_set():
                await asyncio.sleep(0.02)
            return await original(*args, **kwargs)

        def replacement(original):
            async def held(*args, **kwargs):
                return await wait_then_call(original, *args, **kwargs)

            return held

        engine, had_own, original = self._swap(method, replacement)
        try:
            yield release
        finally:
            release.set()  # never leave a request blocked at shutdown
            if had_own:
                setattr(engine, method, original)
            else:
                vars(engine).pop(method, None)

    @contextlib.contextmanager
    def fail(self, method: str):
        """Makes ``engine.<method>`` raise, so the server answers a real 500."""

        def replacement(_original):
            async def failing(*_args, **_kwargs):
                raise RuntimeError("forced failure")

            return failing

        engine, had_own, original = self._swap(method, replacement)
        try:
            yield
        finally:
            if had_own:
                setattr(engine, method, original)
            else:
                vars(engine).pop(method, None)

    def stop(self) -> None:
        if self.http is not None:
            self.http.close()
        if self.server is not None:
            self.server.should_exit = True
        if self.thread is not None:
            self.thread.join(15)
        if self.sock is not None:
            self.sock.close()


def start_live_app(root: Path, *, operator: bool = True, log_file: Path | None = None) -> LiveApp:
    """Starts the launcher app in-process. Any failure, including the ``SystemExit`` of an unknown
    flag, is kept in ``start_error`` instead of propagating (D-18)."""
    live = LiveApp(root)
    live.log_file = log_file
    try:
        import uvicorn
        from databasise.launcher import serve_rest

        sock = socket.socket()
        live.sock = sock
        sock.bind(("127.0.0.1", 0))
        sock.listen()
        live.port = sock.getsockname()[1]
        live.base = f"http://127.0.0.1:{live.port}"
        argv = ["--store-root", str(root), "--workspace", "ws", "--console", "--port", str(live.port)]
        if operator:
            argv.append("--operator")
        if log_file is not None:
            argv += ["--log-file", str(log_file)]
        args = serve_rest.build_parser().parse_args(argv)
        live.app = serve_rest.build_app(args, stub_clients())
        live.server = uvicorn.Server(uvicorn.Config(live.app, log_level="warning"))
        live.thread = threading.Thread(target=live.server.run, kwargs={"sockets": [sock]}, daemon=True)
        live.thread.start()
        deadline = time.monotonic() + 30
        while not live.server.started and time.monotonic() < deadline:
            time.sleep(0.05)
        assert live.server.started, "uvicorn did not start within 30 s"
        live.http = httpx.Client(base_url=live.base, timeout=60)
    except BaseException as exc:  # SystemExit from argparse is a BaseException
        live.start_error = f"{type(exc).__name__}: {exc}"
        live.stop()
    return live


@pytest.fixture(scope="module")
def corpus_fake():
    mp = pytest.MonkeyPatch()
    corpus = _corpus_fake.install(mp)
    yield corpus
    mp.undo()


@pytest.fixture(scope="module")
def live_app(tmp_path_factory, request, corpus_fake):
    live = start_live_app(
        tmp_path_factory.mktemp("store"),
        operator=getattr(request.module, "OPERATOR", True),
        log_file=tmp_path_factory.mktemp("log") / "server.log" if getattr(request.module, "LOG_FILE", False) else None,
    )
    live.corpus = corpus_fake
    yield live
    live.stop()


@pytest.fixture(scope="module")
def seeded(live_app):
    if live_app.start_error is None:
        live_app.ingest(_DOCUMENT_TEXT, SEED_DOCUMENT_ID, HIPPORAG)
    return live_app


# Module scope: a live sync_playwright keeps its event loop registered, which breaks every async
# test that runs after it in the same session (copied from tests/gui/conftest.py).
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


_OPENED: list["LiveUI"] = []


class LiveUI:
    """Thin driver over one page of the live console, plus what the page did on the wire."""

    def __init__(self, context, page, base: str):
        self.context = context
        self.page = page
        self.base = base
        self.requests: list[dict[str, Any]] = []
        self.errors: list[str] = []
        self.console: list[str] = []
        self.foreign: list[str] = []

    def el(self, mock_id: str):
        return self.page.locator(f'[data-mock-id="{mock_id}"]')

    def expect(self, target):
        from playwright.sync_api import expect

        return expect(self.el(target) if isinstance(target, str) else target)

    def nav(self, screen: str) -> None:
        self.el(f"shell.nav.{screen}").click()

    def count(self, method: str, path: str) -> int:
        return sum(1 for r in self.requests if r["method"] == method and r["path"] == path)

    def cors_messages(self) -> list[str]:
        return [m for m in self.console if any(w in m for w in ("CORS", "Access-Control", "Content Security Policy"))]

    def goto(self) -> None:
        self.page.goto(f"{self.base}/console")
        self.page.wait_for_function("typeof window.Console === 'object'")

    def close(self) -> None:
        self.context.close()

    def _on_request(self, request) -> None:
        url = request.url
        if url.startswith(_LOCAL_SCHEMES):
            return
        parsed = urlparse(url)
        if parsed.hostname not in _LOCAL_HOSTS:
            self.foreign.append(url)
        try:
            post_data = request.post_data
        except UnicodeDecodeError:  # multipart upload bodies are binary
            post_data = None
        self.requests.append({"method": request.method, "url": url, "path": parsed.path, "post_data": post_data})


def open_live_ui(browser, app: LiveApp, *, before_goto: Callable[[Any], None] | None = None) -> LiveUI:
    """Opens an online context on the console. ``before_goto(page)`` runs before the first request, so a
    test can install ``page.route`` handlers or ``page.clock`` first."""
    from playwright.sync_api import expect

    context = browser.new_context(viewport={"width": 1280, "height": 900})
    context.set_default_timeout(15000)
    expect.set_options(timeout=15000)
    page = context.new_page()
    ui = LiveUI(context, page, app.base)
    page.on("request", ui._on_request)
    page.on("pageerror", lambda error: ui.errors.append(str(error)))
    page.on("console", lambda message: ui.console.append(message.text))
    _OPENED.append(ui)
    if before_goto is not None:
        before_goto(page)
    ui.goto()
    return ui


@pytest.fixture
def live_ui(browser, live_app):
    ui = open_live_ui(browser, live_app) if live_app.start_error is None else None
    yield ui
    if ui is not None:
        ui.close()


@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem):
    # Fail, never error: a failing fixture is reported as ERROR, an assert here as failed.
    for name in ("live_app", "seeded"):
        live = pyfuncitem.funcargs.get(name)
        if live is not None:
            assert live.start_error is None, f"the live app did not start: {live.start_error}"


@pytest.hookimpl(wrapper=True)
def pytest_runtest_call(item):
    opened_before = len(_OPENED)
    result = yield
    seen = list(_OPENED[opened_before:])
    fixture_ui = item.funcargs.get("live_ui")
    if fixture_ui is not None and fixture_ui not in seen:
        seen.append(fixture_ui)
    errors = [e for ui in seen for e in ui.errors]
    foreign = [u for ui in seen for u in ui.foreign]
    assert errors == [], f"JavaScript errors on the page: {errors}"
    assert foreign == [], f"requests to non-loopback hosts: {foreign}"
    return result
