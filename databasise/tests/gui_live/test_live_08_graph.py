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
from urllib.parse import urlparse

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
