"""LIVE-09 (D-06, D-08, D-09): badges follow the live OpenAPI spec, no control is removed, mock chrome is hidden.

The row test is ``test_badge_kept_exactly_when_the_route_is_absent``: a ``data-needs-backend`` element keeps
its attribute and badge if and only if its route (and every parenthesised parameter) is absent from that
app's ``/openapi.json``. It runs in the three launch modes (no ``--operator``, ``--operator``, and
``--operator --log-file``). This file is written first in plan 18-03 and is the fail-first base, so several
nodes stay red until the screen plans wire their routes:

- ``test_badge_kept_exactly_when_the_route_is_absent`` and ``test_expected_badge_counts_per_launch_mode``:
  green in 18-11, when every screen has added its keys to WIRED (18-03 wires only the header ``GET /info``).
- ``test_no_visible_text_says_fixture_or_mockup``: green in 18-11, after every screen drops fixture text.
- ``test_no_live_button_is_labelled_run_or_submit``: green after 18-08.
- ``test_store_busy_chips_zero_one_many`` and ``test_shell_info_badge_follows_the_launch_mode``: green after
  Task 3 of 18-03 (the ``GET /info`` chips).

The rest (mock chrome hidden but present, every frozen id present, an unloadable spec keeps every badge, the
two id gates) turn green in Task 2 of 18-03. No test here uses the live marker.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter
from html.parser import HTMLParser

import pytest

from databasise.tests.gui_live.conftest import BUILT, ROOT, open_live_ui, start_live_app

MODES = ["plain", "operator", "operator-log"]
EXPECTED_BADGES = {"plain": 54, "operator": 29, "operator-log": 22}
SCREENS = ["query", "evidence", "documents", "corpus", "ledger", "graph"]
ROUTE = re.compile(r"^(GET|POST|PUT|DELETE)\s+(\S+)(?:\s*\(([^)]*)\))?\s*$")
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
MOCK_IDS = json.loads((ROOT / "docs" / "gui" / "MOCK-IDS.json").read_text(encoding="utf-8"))

_ANCHORS = """() => Array.from(document.querySelectorAll('[data-needs-backend]')).map((el) => {
  const inner = el.querySelector('[data-mock-id]');
  const own = el.getAttribute('data-mock-id') || (inner && inner.getAttribute('data-mock-id')) || '';
  return [own, el.getAttribute('data-needs-backend')];
})"""

_WITHOUT_OWN_BADGE = """() => Array.from(document.querySelectorAll('[data-needs-backend]')).filter(
  (el) => !Array.from(el.querySelectorAll('.badge-nb, .badge-op')).some((b) => b.closest('[data-needs-backend]') === el)
).map((el) => el.getAttribute('data-needs-backend'))"""

# Ids inside a <template> (the evidence debug template) are in its content fragment, not in the document tree.
_ALL_IDS = """() => {
  const ids = new Set();
  const walk = (root) => {
    root.querySelectorAll('[data-mock-id]').forEach((e) => ids.add(e.getAttribute('data-mock-id')));
    root.querySelectorAll('template').forEach((t) => walk(t.content));
  };
  walk(document);
  return Array.from(ids);
}"""

_MOCK_CHROME ="""(ids) => {
  const visible = [];
  const missing = [];
  ids.forEach((id) => {
    const el = document.querySelector('[data-mock-id="' + id + '"]');
    if (!el) missing.push(id);
    else if (!el.hidden) visible.push(id);
  });
  const only = Array.from(document.querySelectorAll('[data-mock-only]')).filter((el) => !el.hidden).length;
  return { missing, visible, only, mock: typeof window.__mock };
}"""

_BUTTON_LABELS = """() => Array.from(document.querySelectorAll('button'))
  .filter((b) => b.getClientRects().length > 0)
  .map((b) => b.textContent.trim())
  .filter((t) => t === 'Run' || t === 'Submit')"""


class _Wrappers(HTMLParser):
    """Lists every data-needs-backend element of the built file with its anchor id: its own data-mock-id,
    else the first data-mock-id of a descendant (the same rule the page-side script uses)."""

    def __init__(self) -> None:
        super().__init__()
        self.stack: list[tuple[str, list | None]] = []
        self.found: list[list] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        mock_id = attrs.get("data-mock-id")
        if mock_id:
            for _, record in self.stack:
                if record is not None and not record[0]:
                    record[0] = mock_id
        record = None
        if "data-needs-backend" in attrs:
            record = [mock_id or "", attrs["data-needs-backend"]]
            self.found.append(record)
        if tag not in VOID:
            self.stack.append((tag, record))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                return


def _built_wrappers() -> list[tuple[str, str]]:
    parser = _Wrappers()
    parser.feed(BUILT.read_text(encoding="utf-8"))
    return [(anchor, value) for anchor, value in parser.found]


def _normal(path: str) -> str:
    return re.sub(r"\{[^}]*\}", "{}", path)


def _route_present(spec: dict, value: str) -> bool:
    method, path, params = ROUTE.match(value).groups()
    for key, item in spec["paths"].items():
        if _normal(key) == _normal(path):
            operation = item.get(method.lower())
            if operation is None:
                return False
            names = {p["name"] for p in operation.get("parameters", [])}
            return all(n.strip() in names for n in (params or "").split(",") if n.strip())
    return False


def _remaining(ui) -> Counter:
    return Counter((anchor, value) for anchor, value in ui.page.evaluate(_ANCHORS))


@pytest.fixture(scope="module", params=MODES)
def mode_app(request, tmp_path_factory, corpus_fake):
    log = tmp_path_factory.mktemp("log") / "server.log" if request.param == "operator-log" else None
    live = start_live_app(tmp_path_factory.mktemp("store"), operator=request.param != "plain", log_file=log)
    live.corpus = corpus_fake
    live.mode = request.param
    yield live
    live.stop()


def test_badge_kept_exactly_when_the_route_is_absent(mode_app, browser):
    spec = mode_app.http.get("/openapi.json").json()
    expected = Counter((anchor, value) for anchor, value in _built_wrappers() if not _route_present(spec, value))
    ui = open_live_ui(browser, mode_app)
    try:
        assert _remaining(ui) == expected
        assert ui.page.evaluate(_WITHOUT_OWN_BADGE) == [], "a remaining element lost its own badge"
    finally:
        ui.close()


def test_expected_badge_counts_per_launch_mode(mode_app, browser):
    ui = open_live_ui(browser, mode_app)
    try:
        assert sum(_remaining(ui).values()) == EXPECTED_BADGES[mode_app.mode]
    finally:
        ui.close()


def test_no_mockup_control_is_removed(live_app, live_ui):
    present = set(live_ui.page.evaluate(_ALL_IDS))
    assert [i for i in MOCK_IDS if i not in present] == []


def test_mock_only_controls_are_hidden_but_present(live_app, live_ui):
    mock_ids = [i for i in MOCK_IDS if ".mock." in i]
    assert "shell.mock.banner" in mock_ids and "shell.mock.health-fixture" in mock_ids
    state = live_ui.page.evaluate(_MOCK_CHROME, mock_ids)
    assert state["missing"] == []
    assert state["visible"] == []
    assert state["only"] == 0
    assert state["mock"] == "undefined"


def test_no_visible_text_says_fixture_or_mockup(live_app, live_ui):
    offenders = {}
    for screen in SCREENS:
        live_ui.nav(screen)
        text = live_ui.page.evaluate("() => document.body.innerText").lower()
        hits = [w for w in ("fixture", "mockup", "layout sample") if w in text]
        if hits:
            offenders[screen] = hits
    assert offenders == {}


def test_no_live_button_is_labelled_run_or_submit(live_app, live_ui):
    offenders = {}
    for screen in SCREENS:
        live_ui.nav(screen)
        labels = live_ui.page.evaluate(_BUTTON_LABELS)
        if labels:
            offenders[screen] = labels
    assert offenders == {}


@pytest.mark.parametrize("how", ["abort", "http500"])
def test_openapi_failure_keeps_every_badge(live_app, browser, how):
    def fail_openapi(page):
        if how == "abort":
            page.route("**/openapi.json", lambda route: route.abort())
        else:
            page.route("**/openapi.json", lambda route: route.fulfill(status=500, body="boom"))

    ui = open_live_ui(browser, live_app, before_goto=fail_openapi)
    try:
        assert sum(_remaining(ui).values()) == 54
        assert any(m.startswith("GET /openapi.json") for m in ui.console), ui.console
    finally:
        ui.close()


@pytest.mark.parametrize("write,graph", [(False, False), (True, False), (False, True), (True, True)])
def test_store_busy_chips_zero_one_many(live_app, browser, write, graph):
    info = {"version": "9.9.9", "workspace": "ws-x", "clients": {}, "write_in_flight": write, "graph_busy": graph}
    ui = open_live_ui(browser, live_app, before_goto=lambda page: page.route("**/info", lambda route: route.fulfill(json=info)))
    try:
        ui.expect("shell.instance.chip").to_have_text("version 9.9.9 · workspace ws-x")
        wanted = [label for label, on in (("write in flight", write), ("graph in use", graph)) if on]
        if not wanted:
            ui.expect("shell.live.busy").to_be_hidden()
        else:
            ui.expect("shell.live.busy").to_be_visible()
        chips = [t.strip() for t in ui.el("shell.live.busy").locator(".chip").all_text_contents()]
        assert len(chips) == len(wanted) and all(w in c for w, c in zip(wanted, chips)), chips
    finally:
        ui.close()


def test_shell_info_badge_follows_the_launch_mode(mode_app, browser):
    ui = open_live_ui(browser, mode_app)
    try:
        header = ui.page.locator('header [data-needs-backend="GET /info"]')
        if mode_app.mode == "plain":
            assert header.count() == 1
            assert header.locator(".badge-op").count() == 1
            ui.expect("shell.instance.chip").to_have_text("version — · workspace —")
            assert ui.count("GET", "/info") == 0
        else:
            ui.expect("shell.instance.chip").to_have_text(re.compile(r"^version \S+ · workspace ws$"))
            assert header.count() == 0
            assert ui.count("GET", "/info") >= 1
    finally:
        ui.close()


def test_mockup_id_check_exits_0():
    run = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "mockup-id-check.py"), "--root", str(ROOT)],
        capture_output=True,
        text=True,
    )
    assert run.returncode == 0, run.stdout + run.stderr
    assert run.stdout == ""


def test_check_ledger_reports_no_mockup_violation():
    # Only --complete runs mockup_id_violations. The exit code is not asserted: open LIVE rows are due until 18-11.
    run = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check-ledger.py"), "--root", str(ROOT), "--complete"],
        capture_output=True,
        text=True,
    )
    assert [line for line in run.stdout.splitlines() if line.startswith("mockup")] == []
