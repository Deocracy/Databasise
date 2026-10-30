"""17-03 (GUI-03, D-10, D-14): the badge registry docs/gui/GAP-ROUTES.json against the live FastAPI
route table and against the badges in the mockup.

Kinds: ``operator`` routes exist but are mounted only under ``--operator`` (their set is computed
from ``create_app``); ``missing`` routes do not exist. A badge belongs to its nearest
``[data-needs-backend]`` wrapper. Nothing here starts a server.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from databasise.seam.rest import create_app

ROOT = Path(__file__).resolve().parents[3]
GAP_ROUTES = ROOT / "docs" / "gui" / "GAP-ROUTES.json"

_ROUTE = re.compile(r"^([A-Z]+) (\S+)(?: \(([^)]*)\))?$")

# Nearest-wrapper badge collection, run in the page for every wrapper.
_WRAPPERS_JS = """
() => [...document.querySelectorAll('[data-needs-backend]')].map((el) => ({
  route: el.getAttribute('data-needs-backend'),
  state: el.getAttribute('data-backend-state'),
  title: el.getAttribute('title') || '',
  badges: [...el.querySelectorAll('.badge-nb, .badge-op')]
    .filter((b) => b.closest('[data-needs-backend]') === el)
    .map((b) => ({
      cls: b.classList.contains('badge-op') ? 'op' : 'nb',
      text: b.textContent.trim(),
      hidden: b.hasAttribute('hidden'),
    })),
}))
"""


def _entries() -> list[dict]:
    return json.loads(GAP_ROUTES.read_text(encoding="utf-8"))


def _parse(route: str) -> tuple[str, str, list[str]]:
    match = _ROUTE.match(route)
    assert match, f"unparseable route string: {route!r}"
    params = [p.strip() for p in (match.group(3) or "").split(",") if p.strip()]
    return match.group(1), match.group(2), params


def _pairs(app) -> set[tuple[str, str]]:
    return {
        (method, route.path)
        for route in app.routes
        for method in (getattr(route, "methods", None) or ())
        if method not in ("HEAD", "OPTIONS")
    }


def _wrapper_problems(wrappers: list[dict], kinds: dict[str, str]) -> list[str]:
    problems = []
    for w in wrappers:
        route, badges = w["route"], w["badges"]
        if route not in kinds:
            problems.append(f"{route!r}: not a GAP-ROUTES.json route")
            continue
        if any(b["hidden"] for b in badges):
            problems.append(f"{route!r}: a badge carries hidden")
        if kinds[route] == "operator":
            expected = [b for b in badges if b["cls"] == "op" and b["text"] == "operator route"]
            ok = (
                w["state"] == "operator"
                and w["title"].startswith("Mounted only with --operator")
                and len(expected) == 1
                and len(badges) == 1
            )
        else:
            expected = [b for b in badges if b["cls"] == "nb" and b["text"] == "needs backend"]
            ok = (
                w["state"] is None
                and w["title"] == f"Not implemented yet: {route}"
                and len(expected) == 1
                and len(badges) == 1
            )
        if not ok:
            problems.append(f"{route!r} ({kinds[route]}): wrong state, title or badges: {w}")
    return problems


def test_gap_routes_file_is_sorted_and_unique():
    entries = _entries()
    assert isinstance(entries, list) and entries
    for entry in entries:
        assert set(entry) == {"route", "kind"}, entry
        assert entry["kind"] in {"operator", "missing"}, entry
        _parse(entry["route"])
    routes = [e["route"] for e in entries]
    assert routes == sorted(routes), "GAP-ROUTES.json must be sorted by route"
    assert len(routes) == len(set(routes)), "GAP-ROUTES.json routes must be unique"


def test_operator_kind_equals_the_operator_only_routes(tmp_path):
    default = _pairs(create_app(store_root=tmp_path / "a", workspace="ws"))
    operator = _pairs(
        create_app(
            store_root=tmp_path / "b", workspace="ws", operator=True, log_path=tmp_path / "log.txt"
        )
    )
    listed = {
        _parse(e["route"])[:2] for e in _entries() if e["kind"] == "operator"
    }
    assert operator - default == listed


def test_missing_kind_routes_are_absent_from_the_operator_app(tmp_path):
    app = create_app(
        store_root=tmp_path / "b", workspace="ws", operator=True, log_path=tmp_path / "log.txt"
    )
    pairs = _pairs(app)
    paths = app.openapi()["paths"]
    for entry in _entries():
        if entry["kind"] != "missing":
            continue
        method, path, params = _parse(entry["route"])
        if not params:
            assert (method, path) not in pairs, f"{entry['route']} exists in the operator app"
            continue
        assert (method, path) in pairs, f"{entry['route']}: the route itself must exist"
        names = {p["name"] for p in paths[path][method.lower()].get("parameters", [])}
        assert not names & set(params), f"{entry['route']}: parameters {names & set(params)} exist"


def test_present_wrappers_carry_the_badge_of_their_kind(ui):
    kinds = {e["route"]: e["kind"] for e in _entries()}
    wrappers = ui.page.evaluate(_WRAPPERS_JS)
    assert _wrapper_problems(wrappers, kinds) == []


def test_gui_03_every_gap_route_is_marked_and_badged(ui, mockup_path):
    kinds = {e["route"]: e["kind"] for e in _entries()}
    present = set(re.findall(r'data-needs-backend="([^"]+)"', mockup_path.read_text(encoding="utf-8")))
    missing = sorted(set(kinds) - present)
    assert not missing, f"{len(missing)} route strings not yet in the mockup: {missing}"
    assert present <= set(kinds), f"not GAP-ROUTES routes: {sorted(present - set(kinds))}"
    assert _wrapper_problems(ui.page.evaluate(_WRAPPERS_JS), kinds) == []
    # D-14: client presence and failure reasons are GET /health fields with no badge; busy is GET /info.
    for mock_id in ("corpus.health.clients", "corpus.health.reasons"):
        assert ui.el(mock_id).count() == 1, mock_id
        assert ui.el(mock_id).evaluate("e => e.closest('[data-needs-backend]') === null"), mock_id
    assert ui.el("corpus.health.busy").count() == 1
    assert ui.el("corpus.health.busy").evaluate(
        "e => { const w = e.closest('[data-needs-backend]'); return !!w && w.getAttribute('data-needs-backend') === 'GET /info'; }"
    )
