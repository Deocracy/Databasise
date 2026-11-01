"""LIVE-08 (D-12, D-19): the Graph/vector browser runs against the real operator routes.

The row test is ``test_nodes_list_and_node_edges_by_selector``: choosing a capability set sends one
``POST /graph/nodes`` whose body carries a ``selector`` and no namespace, the table shows the response
rows with their degrees, and Open on a node sends ``POST /graph/node`` and shows its edges. Lists page by
``next_offset`` with the requested offset kept on the client, a chunk row opens the Evidence Inspector with
its ``EvidenceRef`` unchanged, an unknown node id renders ``UnknownGraphNodeError``, and a graph held by
another process renders ``StoreBusyError`` (a raw pycozo client on the graph directory, D-19) with a Retry
request that repeats the last read. ``POST /graph/node/attrs`` and ``POST /stores/counts`` do not exist, so
their controls stay badged and disabled. No test here uses the live marker.
"""

from __future__ import annotations

import json
import re
import time
from urllib.parse import urlparse

import pycozo
import pytest

from databasise.tests.gui_live.conftest import HIPPORAG, open_live_ui, start_live_app
from databasise.tests.seam.test_hipporag_write_path import _DOCUMENT_TEXT

CAPS = ["reads_graph", "reads_kv"]


def _is_post(path):
    return lambda response: response.request.method == "POST" and urlparse(response.url).path == path


def _posts(ui, path):
    return [r for r in ui.requests if r["method"] == "POST" and r["path"] == path]


def _rows(ui, table):
    return ui.el(table).locator("tbody tr:not([hidden])")


def _pick_hipporag(ui):
    """Opens the Graph screen and chooses the HippoRAG capability set; returns the POST /graph/nodes answer."""
    ui.nav("graph")
    ui.el("graph.selector.kind-capability").check()
    with ui.page.expect_response(_is_post("/graph/nodes")) as info:
        ui.el("graph.selector.capability").select_option(CAPS)
    return info.value.json()


def test_nodes_list_and_node_edges_by_selector(seeded, live_ui):
    ui = live_ui
    page = _pick_hipporag(ui)
    posts = _posts(ui, "/graph/nodes")
    assert len(posts) == 1
    body = json.loads(posts[0]["post_data"])
    assert sorted(body["selector"]["capability"]) == sorted(CAPS)
    assert not [key for key in body if "namespace" in key.lower()]

    nodes = page["nodes"]
    assert nodes, "the seeded HippoRAG graph has nodes"
    rows = _rows(ui, "graph.nodes.table")
    ui.expect(rows).to_have_count(len(nodes))
    shown = [(r.locator('[data-role="id"]').inner_text(), r.locator('[data-role="degree"]').inner_text()) for r in rows.all()]
    assert shown == [(n["id"], str(n["degree"])) for n in nodes]
    ui.expect("graph.nodes.total").to_contain_text(str(page["total"]))

    pick = max(range(len(nodes)), key=lambda i: nodes[i]["degree"])
    with ui.page.expect_response(_is_post("/graph/node")) as info:
        ui.el(f"graph.nodes.open-{pick + 1}").click()
    node = info.value.json()
    sent = json.loads(_posts(ui, "/graph/node")[0]["post_data"])
    assert sent["node_id"] == nodes[pick]["id"]
    assert sorted(sent["selector"]["capability"]) == sorted(CAPS)
    ui.expect("graph.node.degree").to_have_text(str(node["degree"]))
    edge_rows = _rows(ui, "graph.edges.table")
    ui.expect(edge_rows).to_have_count(len(node["edges"]))
    pairs = [(r.locator('[data-role="src"]').inner_text(), r.locator('[data-role="tgt"]').inner_text()) for r in edge_rows.all()]
    assert pairs == [(e["src"], e["tgt"]) for e in node["edges"]]
    assert node["id"] == nodes[pick]["id"]


# ---- Task 2: paging, chunks, unknown node, absent routes, page size ----


def _settle(ui):
    """One round trip through the page: every request a handler started before this call is in ``ui.requests``."""
    ui.page.evaluate("() => fetch('/openapi.json').then((r) => r.status)")


def test_node_paging_follows_next_offset(seeded, live_ui):
    ui = live_ui
    ui.nav("graph")
    ui.el("graph.nodes.page-size").fill("1")
    first = _pick_hipporag(ui)
    assert first["next_offset"] == 1
    ui.expect(_rows(ui, "graph.nodes.table")).to_have_count(1)

    with ui.page.expect_response(_is_post("/graph/nodes")) as info:
        ui.el("graph.nodes.next").click()
    second = info.value.json()
    offsets = [json.loads(p["post_data"])["offset"] for p in _posts(ui, "/graph/nodes")]
    assert offsets == [0, first["next_offset"]]
    ui.expect(_rows(ui, "graph.nodes.table").first.locator('[data-role="id"]')).to_have_text(second["nodes"][0]["id"])
    ui.expect("graph.nodes.prev").to_be_enabled()

    with ui.page.expect_response(_is_post("/graph/nodes")):
        ui.el("graph.nodes.prev").click()
    assert [json.loads(p["post_data"])["offset"] for p in _posts(ui, "/graph/nodes")] == [0, first["next_offset"], 0]
    ui.expect(_rows(ui, "graph.nodes.table").first.locator('[data-role="id"]')).to_have_text(first["nodes"][0]["id"])
    ui.expect("graph.nodes.prev").to_be_disabled()


def test_chunks_open_in_the_evidence_inspector(seeded, live_ui):
    ui = live_ui
    ui.nav("graph")
    ui.el("graph.selector.kind-capability").check()
    with ui.page.expect_response(_is_post("/chunks")) as info:
        ui.el("graph.selector.capability").select_option(CAPS)
    refs = info.value.json()["refs"]
    assert refs, "the seeded HippoRAG store has chunks"
    body = json.loads(_posts(ui, "/chunks")[0]["post_data"])
    assert sorted(body["selector"]["capability"]) == sorted(CAPS)
    assert not [key for key in body if "namespace" in key.lower()]
    ui.expect(_rows(ui, "graph.chunks.table")).to_have_count(len(refs))

    with ui.page.expect_response(_is_post("/evidence/resolve")):
        ui.el("graph.chunks.open-1").click()
    ui.expect("screen-evidence").to_be_visible()
    posted = _posts(ui, "/evidence/resolve")
    assert len(posted) == 1
    assert posted[0]["post_data"] == json.dumps(refs[0], separators=(",", ":"))


def test_unknown_node_renders_its_state(seeded, live_ui):
    ui = live_ui
    _pick_hipporag(ui)
    ui.el("graph.node.lookup").fill("no-such-node")
    ui.el("graph.node.lookup-submit").click()
    state = ui.el("graph.state.unknown-node")
    ui.expect(state).to_contain_text("UnknownGraphNodeError")
    ui.expect(state.locator("mark")).to_have_text("no-such-node")
    ui.expect(state.locator('[data-role="footer"]')).to_have_text(re.compile(r"^HTTP 422\."))
    ui.expect("graph.error.generic").to_be_hidden()


def test_refused_selector_change_clears_the_previous_lists(seeded, live_ui):
    """R18-06: the node and chunk pages of the previous selector leave the screen when the new selector's read is refused."""
    ui = live_ui
    page = _pick_hipporag(ui)
    assert page["nodes"]
    ui.expect(_rows(ui, "graph.nodes.table")).to_have_count(len(page["nodes"]))
    ui.expect(_rows(ui, "graph.chunks.table")).not_to_have_count(0)

    ui.el("graph.selector.kind-alias").check()
    with ui.page.expect_response(_is_post("/graph/nodes")) as info:
        ui.el("graph.selector.alias").fill("no-such-alias")
    assert info.value.status == 422
    ui.expect("graph.error.refusal").to_contain_text("UnsatisfiableSelectorError")
    ui.expect(_rows(ui, "graph.nodes.table")).to_have_count(0)
    ui.expect(_rows(ui, "graph.chunks.table")).to_have_count(0)
    ui.expect("graph.nodes.empty").to_be_hidden()


def test_absent_graph_routes_are_disabled(seeded, live_ui):
    ui = live_ui
    page = _pick_hipporag(ui)
    assert page["nodes"]
    with ui.page.expect_response(_is_post("/graph/node")):
        ui.el("graph.nodes.open-1").click()
    ui.expect("graph.node.attrs-load").to_be_disabled()
    ui.expect(ui.page.locator('[data-needs-backend="POST /graph/node/attrs"]')).to_contain_text("Needs POST /graph/node/attrs.")
    for key in ("nodes", "edges", "chunks"):
        ui.expect(ui.el(f"graph.counts.{key}").locator('[data-role="count"]')).to_have_text("—")
    counts = ui.page.locator('[data-needs-backend="POST /stores/counts"]')
    ui.expect(counts.locator(".badge-nb")).to_be_visible()


def test_page_size_101_is_refused_on_the_client(seeded, live_ui):
    ui = live_ui
    ui.nav("graph")
    ui.el("graph.nodes.page-size").fill("101")
    ui.expect("graph.nodes.page-size-error").to_have_text("Page size must be between 1 and 100.")
    ui.el("graph.selector.kind-capability").check()
    ui.el("graph.selector.capability").select_option(CAPS)
    _settle(ui)
    assert _posts(ui, "/graph/nodes") == []
    assert _posts(ui, "/graph/node") == []


def test_no_namespace_input_on_the_graph_screen(live_ui):
    ui = live_ui
    ui.nav("graph")
    hits = ui.page.evaluate(
        """() => {
  const root = document.querySelector('[data-mock-id="screen-graph"]');
  const hits = [];
  root.querySelectorAll('input, select, textarea, label, [aria-label]').forEach((el) => {
    const parts = [el.getAttribute('name'), el.id, el.getAttribute('placeholder'), el.getAttribute('aria-label')];
    if (el.tagName === 'LABEL') parts.push(el.textContent);
    Array.from(el.labels || []).forEach((label) => parts.push(label.textContent));
    if (parts.some((part) => part && /namespace/i.test(part))) hits.push(el.outerHTML.slice(0, 80));
  });
  return hits;
}"""
    )
    assert hits == []


# ---- Task 3: store busy under a raw pycozo lock, and no --operator ----


@pytest.fixture(scope="module")
def busy_app(tmp_path_factory, corpus_fake):
    """A fresh store root seeded only through an ingest; no graph read has happened, so a raw client can hold the graph."""
    live = start_live_app(tmp_path_factory.mktemp("store-busy"))
    live.corpus = corpus_fake
    if live.start_error is None:
        live.ingest(_DOCUMENT_TEXT, "seed-busy", HIPPORAG)
    yield live
    live.stop()


@pytest.fixture(scope="module")
def plain_app(tmp_path_factory, corpus_fake):
    """No ``--operator``: the graph, node and chunk routes are not mounted."""
    live = start_live_app(tmp_path_factory.mktemp("store-plain"), operator=False)
    live.corpus = corpus_fake
    yield live
    live.stop()


def _hold(path):
    """A raw pycozo client on the graph directory; retried for up to 10 s in case a health probe holds the path."""
    deadline = time.monotonic() + 10
    while True:
        try:
            return pycozo.Client("rocksdb", str(path.resolve()), dataframe=False)
        except Exception:
            if time.monotonic() > deadline:
                raise
            time.sleep(0.1)


def test_store_busy_renders_the_refusal_and_retry_recovers(busy_app, browser):
    path = busy_app.root / "ws" / "hipporag-graph" / "graph.cozo"
    ui = open_live_ui(browser, busy_app)
    try:
        # The header health check probes the graph path through the registry while it runs, so the raw client waits for it.
        ui.expect("shell.health.status").not_to_have_attribute("data-state", "loading")
        held = _hold(path)
        try:
            ui.nav("graph")
            ui.el("graph.selector.kind-capability").check()
            ui.el("graph.selector.capability").select_option(CAPS)
            state = ui.el("graph.state.store-busy")
            ui.expect(state).to_be_visible()
            ui.expect(state).to_contain_text("StoreBusyError")
            ui.expect(state).to_contain_text("store busy")
            ui.expect(state.locator('[data-role="footer"]')).to_have_text(re.compile(r"^HTTP 409\."))
            ui.expect("graph.error.generic").to_be_hidden()
            ui.expect(_rows(ui, "graph.nodes.table")).to_have_count(0)
        finally:
            held.close()

        with ui.page.expect_response(_is_post("/graph/nodes")) as info:
            ui.el("graph.state.retry").click()
        assert info.value.status == 200
        page = info.value.json()
        assert page["nodes"], "the seeded HippoRAG graph has nodes"
        posts = _posts(ui, "/graph/nodes")
        assert len(posts) == 2
        assert json.loads(posts[0]["post_data"]) == json.loads(posts[1]["post_data"])  # Retry repeats the last request
        ui.expect(_rows(ui, "graph.nodes.table")).to_have_count(len(page["nodes"]))
        ui.expect("graph.state.store-busy").to_be_hidden()
        ui.expect("graph.nodes.panel").not_to_have_attribute("aria-busy", "true")
    finally:
        ui.close()


def test_without_operator_every_graph_control_is_disabled(plain_app, browser):
    ui = open_live_ui(browser, plain_app)
    try:
        ui.nav("graph")
        controls = ui.page.locator('[data-mock-id="screen-graph"]').locator("button, input, select").all()
        checked = 0
        for control in controls:
            mock_id = control.get_attribute("data-mock-id") or ""
            if not control.is_visible() or mock_id.startswith("graph.selector."):
                continue
            assert control.is_disabled(), f"{mock_id} is enabled without --operator"
            checked += 1
        assert checked >= 5  # prefix, two page sizes, node id, Open node
        line = ui.page.locator('[data-mock-id="screen-graph"] .needs-route:visible', has_text="Needs POST /graph/nodes.")
        ui.expect(line.first).to_be_visible()
        for key in ("nodes", "edges", "chunks"):
            ui.expect(ui.el(f"graph.counts.{key}").locator('[data-role="count"]')).to_have_text("—")
        _settle(ui)
        assert [r for r in ui.requests if r["path"] in ("/graph/nodes", "/graph/node", "/chunks")] == []
    finally:
        ui.close()
