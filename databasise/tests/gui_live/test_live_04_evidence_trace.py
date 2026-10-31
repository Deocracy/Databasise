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

from databasise.tests.gui_live.conftest import HIPPORAG

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
    # The same keys, values and order. JavaScript writes the score 1.0 as 1, so the text is compared as parsed pairs.
    sent = json.loads(posts[0]["post_data"], object_pairs_hook=lambda pairs: pairs)
    assert [key for key, _ in sent] == list(env["evidence"][0])
    assert dict(sent) == env["evidence"][0]
    assert "id" not in dict(sent)
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


# ---- Task 2: the trace, the origin link, recent runs, Open in Corpus and the abort rules ----


def _trace_bodies(ui):
    return [json.loads(p["post_data"]) for p in _posts(ui, "/trace/resolve")]


def _lookup(ui, ref):
    """Resolves a ref through Manual lookup, which carries no trace token."""
    ui.nav("evidence")
    ui.el("evidence.lookup.toggle").click()
    ui.el("evidence.lookup.ref").fill(ref["ref"])
    ui.el("evidence.lookup.namespace").select_option(ref["namespace"])
    ui.el("evidence.lookup.submit").click()


def test_trace_loads_then_re_requests_in_detail_mode(seeded, live_ui):
    ui = live_ui
    token = _query(ui)["trace_token"]

    ui.el("query.result.trace-link").click()
    ui.expect("screen-evidence").to_be_visible()
    ui.expect("evidence.trace.summary").to_be_visible()
    assert _trace_bodies(ui) == [{"trace_reference": token, "debug": False}]
    ui.expect(ui.el("evidence.trace.nodes")).to_have_count(0)

    ui.el("evidence.trace.debug").check()
    ui.expect("evidence.trace.nodes").to_be_visible()
    assert _trace_bodies(ui)[1:] == [{"trace_reference": token, "debug": True}]
    assert ui.el("evidence.trace.nodes").locator("tbody tr").count() >= 1

    ui.el("evidence.trace.debug").uncheck()
    ui.expect(ui.el("evidence.trace.nodes")).to_have_count(0)
    ui.expect("evidence.trace.summary").to_be_visible()
    assert _trace_bodies(ui)[2:] == [{"trace_reference": token, "debug": False}]
    assert len(_trace_bodies(ui)) == 3


def test_inspector_open_trace_targets_the_originating_run(seeded, live_ui):
    ui = live_ui
    token_a = _query(ui, "Ed Wood")["trace_token"]
    ui.el("query.evidence.open-1").click()
    ui.expect("evidence.state.resolved").to_be_visible()

    ui.nav("query")
    token_b = _query(ui, "Bela Lugosi")["trace_token"]
    assert token_a != token_b

    ui.nav("evidence")
    ui.el("evidence.inspector.trace-link").click()
    ui.expect("evidence.trace.summary").to_be_visible()
    assert _trace_bodies(ui) == [{"trace_reference": token_a, "debug": False}]
    ui.expect("evidence.trace.reference").to_have_value(token_a)


def test_inspector_trace_link_disabled_without_token(seeded, live_ui):
    ui = live_ui
    ref = _query(ui)["evidence"][0]
    _lookup(ui, ref)
    ui.expect("evidence.state.resolved").to_be_visible()
    link = ui.el("evidence.inspector.trace-link")
    ui.expect(link).to_have_attribute("aria-disabled", "true")
    assert link.get_attribute("href") is None
    ui.expect(ui.el("evidence.inspector.panel").get_by_text("No trace token on this result.")).to_be_visible()
    link.click(force=True)
    assert _posts(ui, "/trace/resolve") == []


def test_open_in_corpus_only_for_lightrag_records(seeded, live_ui):
    ui = live_ui
    _query(ui)
    ui.el("query.evidence.open-1").click()
    ui.expect("evidence.state.resolved").to_be_visible()
    ui.expect("evidence.inspector.document-link").to_be_hidden()

    record = {"id": "c-1", "full_doc_id": "doc-1", "content": "x", "file_path": None}
    ui.page.route("**/evidence/resolve", lambda route: route.fulfill(status=200, content_type="application/json", body=json.dumps(record)))
    _lookup(ui, {"ref": "c-1", "namespace": "chunks"})
    ui.expect("evidence.inspector.document-link").to_be_visible()
    ui.el("evidence.inspector.document-link").click()
    ui.expect("screen-corpus").to_be_visible()


def test_abandoned_resolve_restores_the_opener(seeded, live_ui):
    ui = live_ui
    _query(ui)
    button = ui.el("query.evidence.open-1")
    with seeded.hold("resolve_evidence"):
        button.click()
        ui.expect("evidence.state.loading").to_be_visible()
        ui.expect(button).to_have_attribute("aria-label", "Opening")
        ui.expect(button).to_have_attribute("aria-busy", "true")
        ui.nav("query")
        ui.expect(button).to_have_text("Open")
        assert button.get_attribute("aria-busy") is None
        assert button.get_attribute("aria-label") is None
        ui.expect("evidence.state.loading").to_be_hidden()
        ui.expect("evidence.state.resolved").to_be_hidden()


def test_recent_runs_list_history_and_server_traces(seeded, live_ui):
    ui = live_ui
    token = _query(ui)["trace_token"]
    server_only = seeded.query("Ed Wood", HIPPORAG)["trace_token"]
    assert server_only != token

    ui.nav("evidence")
    ui.el("evidence.tabs.trace").click()
    options = ui.el("evidence.trace.recent").locator("option")
    ui.expect(options.locator(f"xpath=self::option[@value='{token}']")).to_have_count(1)
    ui.expect(options.locator(f"xpath=self::option[@value='{server_only}']")).to_have_count(1)
    assert ui.count("GET", "/traces") >= 1
    # Only this screen's wrapper: the Ledger picker is wired in 18-09.
    ui.expect(ui.page.locator('[data-mock-id="screen-evidence"] [data-needs-backend="GET /traces"]')).to_have_count(0)


def test_resolve_all_evidence_is_disabled_with_its_route(seeded, live_ui):
    ui = live_ui
    ui.nav("evidence")
    ui.expect("evidence.batch.submit").to_be_disabled()
    ui.expect(ui.page.get_by_text("Needs POST /evidence/resolve-batch.")).to_be_visible()
    ui.expect("evidence.batch.status").to_be_hidden()
    ui.expect("evidence.batch.status").to_have_text("")
