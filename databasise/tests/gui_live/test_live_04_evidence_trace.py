"""LIVE-04 (D-05, D-07, D-14): Evidence & Trace run against the real API.

The row test is ``test_open_resolves_the_envelope_ref_unchanged_once_per_session``: Open on an evidence
row of a live query sends one ``POST /evidence/resolve`` whose body is the envelope's EvidenceRef copied
unchanged (18-RESEARCH Pitfall 2), and a second Open of the same ref is served from the per-session
cache, with no request and no loading view (D-07). Trace loading, the Debug re-request, the inspector's
Open trace link to the originating run, Open in Corpus and the abort rules (D-14) follow.

Named deviation: LIVE-04 naive query substituted. The tests open evidence and traces from a HippoRAG
query instead of a naive query on a populated temp store, because the offline stub does not populate the
LightRAG v2 stores (18-CONTEXT D-15, 18-RESEARCH Open Question 1). The owner walkthrough in 18-11 opens
them on the default (LightRAG) path with real clients. No test here uses the live marker.
"""

from __future__ import annotations

import json
from urllib.parse import urlparse

CAPS = ["reads_graph", "reads_kv"]


def _is_post(path):
    return lambda response: response.request.method == "POST" and urlparse(response.url).path == path


def _posts(ui, path):
    return [r for r in ui.requests if r["method"] == "POST" and r["path"] == path]


def _query(ui, text="Ed Wood"):
    """Runs a HippoRAG query with Stream off and returns the response envelope."""
    ui.el("query.text.input").fill(text)
    ui.el("query.selector.kind-capability").check()
    ui.el("query.selector.capability").select_option(CAPS)
    ui.el("query.run.stream").set_checked(False)
    with ui.page.expect_response(_is_post("/query")) as info:
        ui.el("query.run.submit").click()
    env = info.value.json()
    ui.expect("query.state.success").to_be_visible()
    assert env["evidence"], "the seeded HippoRAG query returned no evidence"
    return env


def test_open_resolves_the_envelope_ref_unchanged_once_per_session(seeded, live_ui):
    ui = live_ui
    env = _query(ui)

    with ui.page.expect_response(_is_post("/evidence/resolve")) as info:
        ui.el("query.evidence.open-1").click()
    record = info.value.json()
    ui.expect("screen-evidence").to_be_visible()
    ui.expect("evidence.state.resolved").to_be_visible()

    posts = _posts(ui, "/evidence/resolve")
    assert len(posts) == 1
    assert posts[0]["post_data"] == json.dumps(env["evidence"][0], separators=(",", ":"), ensure_ascii=False)
    assert "id" not in json.loads(posts[0]["post_data"])
    ui.expect("evidence.inspector.content").to_contain_text(record["content"])
    ui.expect(ui.el("evidence.inspector.panel").get_by_text("Cached for this session by namespace and ref.")).to_be_visible()

    ui.nav("query")
    ui.page.evaluate(
        """() => {
            window.__loadingSeen = false;
            const el = document.querySelector('[data-mock-id="evidence.state.loading"]');
            new MutationObserver(() => { if (!el.hidden) window.__loadingSeen = true; })
                .observe(el, { attributes: true, attributeFilter: ['hidden'] });
        }"""
    )
    ui.el("query.evidence.open-1").click()
    ui.expect("evidence.state.resolved").to_be_visible()
    ui.expect("evidence.inspector.content").to_contain_text(record["content"])
    assert len(_posts(ui, "/evidence/resolve")) == 1
    assert ui.page.evaluate("window.__loadingSeen") is False
