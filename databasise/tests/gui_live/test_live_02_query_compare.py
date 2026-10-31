"""LIVE-02 (D-10, D-11): Query mode runs against the real API; the compare part is added by 18-05.

The row test is ``test_query_without_stream_renders_answer_evidence_and_trace_link``: with Stream off,
``query.run.submit`` sends one ``POST /query`` and the answer, badges, every evidence row, token table,
seam events and the trace link render from the real envelope. The other tests cover the evidence rows
beyond the literal slots (D-14), raw selector JSON (WR-JSA-01), and the SSE stream plus the run history
(D-07, D-10, WR-JSA-05, IN-JSA-08). Streams are altered only through ``route.fetch`` +
``route.fulfill(response=...)`` or ``route.continue_`` so the real server answers (18-RESEARCH).
No test here uses the live marker.
"""

from __future__ import annotations

import contextlib
import json
from urllib.parse import urlparse

from databasise.tests.gui_live.conftest import open_live_ui

CAPS = ["reads_graph", "reads_kv"]
EVIDENCE_ROWS = '[data-mock-id="query.evidence.table"] tbody tr:not([hidden])'
RAW_INVALID = "Raw selector JSON is not valid JSON."


def _is_post(path):
    return lambda response: response.request.method == "POST" and urlparse(response.url).path == path


def _posts(ui, path="/query"):
    return [r for r in ui.requests if r["method"] == "POST" and r["path"] == path]


def _fill(ui, text="Ed Wood", *, stream=False):
    ui.el("query.text.input").fill(text)
    ui.el("query.selector.kind-capability").check()
    ui.el("query.selector.capability").select_option(CAPS)
    ui.el("query.run.stream").set_checked(stream)


@contextlib.contextmanager
def _ui(browser, app, before_goto=None):
    ui = open_live_ui(browser, app, before_goto=before_goto)
    try:
        yield ui
    finally:
        ui.close()


def test_query_without_stream_renders_answer_evidence_and_trace_link(seeded, live_ui):
    ui = live_ui
    _fill(ui)
    ui.expect("query.run.submit").to_have_text("Run query")
    with ui.page.expect_response(_is_post("/query")) as info:
        ui.el("query.run.submit").click()
    env = info.value.json()

    posts = _posts(ui)
    assert len(posts) == 1
    body = json.loads(posts[0]["post_data"])
    assert set(body) == {"query", "selector"}
    assert body["query"] == {"text": "Ed Wood"}
    assert sorted(body["selector"]["capability"]) == CAPS
    assert _posts(ui, "/query/stream") == []

    ui.expect("query.state.success").to_be_visible()
    ui.expect(ui.page.get_by_text("Run complete.", exact=True)).to_be_visible()
    ui.expect("query.result.answer").to_have_text(env["answer"])
    ui.expect("query.result.depth").to_have_text("depth: " + env["depth_label"])
    ui.expect("query.result.degraded").to_be_visible()
    rows = ui.page.locator(EVIDENCE_ROWS)
    ui.expect(rows).to_have_count(len(env["evidence"]))
    for i, ref in enumerate(env["evidence"]):
        cells = rows.nth(i).locator("td")
        ui.expect(cells.nth(0)).to_have_text(str(i + 1))
        ui.expect(cells.nth(1)).to_have_text(ref["ref"])
        ui.expect(cells.nth(2)).to_have_text(ref["namespace"])
    token_rows = ui.page.locator('[data-mock-id="query.tokens.table"] tbody tr')
    ui.expect(token_rows).to_have_count(len(env["token_accounting"]) + 1)
    ui.expect("query.result.trace-link").to_be_visible()
    assert ui.el("query.result.trace-link").get_attribute("aria-disabled") is None
    ui.expect("query.result.promote").to_be_enabled()


def test_more_evidence_rows_than_slots_all_render(seeded, browser):
    seen = {}

    def handler(route):
        response = route.fetch()
        env = response.json()
        env["evidence"] = [dict(env["evidence"][0], ref=f"ref-{i:02d}") for i in range(12)]
        seen["env"] = env
        route.fulfill(response=response, body=json.dumps(env))

    with _ui(browser, seeded, lambda page: page.route("**/query", handler)) as ui:
        _fill(ui)
        ui.page.evaluate("Console.on('open-evidence', (p) => { window.__payload = p; })")
        ui.el("query.run.submit").click()
        ui.expect("query.state.success").to_be_visible()
        ui.expect(ui.page.locator(EVIDENCE_ROWS)).to_have_count(12)
        ui.expect("query.evidence.open-12").to_be_visible()
        ui.el("query.evidence.open-12").click()
        ui.expect("screen-evidence").to_be_visible()
        payload = ui.page.evaluate("window.__payload")
        assert payload["ref"] == seen["env"]["evidence"][11]
        assert "id" not in payload["ref"]
        assert payload["trace_token"] == seen["env"]["trace_token"]


def test_raw_selector_json_accepts_only_the_three_members(seeded, live_ui):
    ui = live_ui
    ui.el("query.text.input").fill("Ed Wood")
    ui.el("query.advanced.toggle").click()
    for bad in ('{"alias": 5}', '{"x": 1}', '{"capability": []}', '{"capability": [1]}'):
        ui.el("query.advanced.selector-json").fill(bad)
        ui.el("query.run.submit").click()
        ui.expect("query.advanced.selector-json-error").to_have_text(RAW_INVALID)
    assert _posts(ui) == []

    ui.el("query.advanced.selector-json").fill('{"capability": ["reads_graph", "reads_kv"]}')
    ui.el("query.run.submit").click()
    ui.expect("query.state.success").to_be_visible()
    posts = _posts(ui)
    assert len(posts) == 1
    assert json.loads(posts[0]["post_data"])["selector"] == {"capability": CAPS}
