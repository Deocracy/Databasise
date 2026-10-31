"""LIVE-02 (D-10, D-11): Query mode and Compare mode run against the real API.

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

import pytest

from databasise.tests.gui_live.conftest import HIPPORAG, open_live_ui

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


# ---- Task 2: the SSE stream, the disconnected state and the run history ----

HISTORY_KEY = "databasise.console.history"
HISTORY_ROWS = '[data-mock-id="query.history.table"] tbody tr:not([hidden])'
DISCONNECTED = (
    "The stream closed before the final event. Evidence received so far is shown below; "
    "the run is not complete. Run again to retry."
)


def _final(stream_text):
    for block in stream_text.split("\n\n"):
        if block.startswith("data: "):
            event = json.loads(block[len("data: ") :])
            if event["kind"] == "final":
                return event
    raise AssertionError("no final event in the stream")


def _stored(ui):
    raw = ui.page.evaluate(f"sessionStorage.getItem('{HISTORY_KEY}')")
    return json.loads(raw) if raw else []


def _not_finished(ui):
    ui.expect("query.result.promote").to_be_disabled()
    assert ui.el("query.result.trace-link").get_attribute("aria-disabled") == "true"
    ui.expect(ui.page.get_by_text("Run complete.", exact=True)).to_be_hidden()


def test_stream_renders_evidence_then_final(seeded, browser):
    held = []
    with _ui(browser, seeded, lambda page: page.route("**/query/stream", lambda route: held.append(route))) as ui:
        _fill(ui, stream=True)
        ui.el("query.run.submit").click()
        for _ in range(100):  # bounded: a console that never streams must fail, not hang
            if held:
                break
            ui.page.wait_for_timeout(50)
        assert len(held) == 1, "no POST /query/stream was sent"
        # Before the final event: running, no completion text, nothing to promote or open (WR-JSA-05).
        ui.expect("query.state.running").to_be_visible()
        ui.expect("query.result.answer").to_have_text("Receiving evidence")
        _not_finished(ui)
        held[0].continue_()

        ui.expect("query.state.success").to_be_visible()
        ui.expect(ui.page.get_by_text("Run complete.", exact=True)).to_be_visible()
        ui.expect(ui.page.locator(EVIDENCE_ROWS)).to_have_count(1)
        ui.expect("query.result.promote").to_be_enabled()
        assert ui.el("query.result.trace-link").get_attribute("aria-disabled") is None
        assert len(_posts(ui, "/query/stream")) == 1
        assert _posts(ui) == []


def test_early_closed_stream_shows_disconnected(seeded, browser):
    def handler(route):
        response = route.fetch()
        route.fulfill(response=response, body=response.text().split("\n\n")[0] + "\n\n")

    with _ui(browser, seeded, lambda page: page.route("**/query/stream", handler)) as ui:
        _fill(ui, stream=True)
        ui.el("query.run.submit").click()
        ui.expect("query.error.generic").to_contain_text(DISCONNECTED)
        ui.expect(ui.page.locator(EVIDENCE_ROWS)).to_have_count(1)
        _not_finished(ui)
        ui.expect(ui.page.get_by_text("The run did not finish.", exact=True)).to_be_visible()
        ui.expect(ui.page.locator(HISTORY_ROWS)).to_have_count(0)
        assert _stored(ui) == []


def test_stream_ignores_comment_lines(seeded, browser):
    def handler(route):
        response = route.fetch()
        route.fulfill(response=response, body=": ping\n\n" + response.text())

    with _ui(browser, seeded, lambda page: page.route("**/query/stream", handler)) as ui:
        _fill(ui, stream=True)
        ui.el("query.run.submit").click()
        ui.expect("query.state.success").to_be_visible()
        ui.expect(ui.page.get_by_text("Run complete.", exact=True)).to_be_visible()
        ui.expect(ui.page.locator(EVIDENCE_ROWS)).to_have_count(1)
        ui.expect("query.result.promote").to_be_enabled()
        assert len(_posts(ui, "/query/stream")) == 1


def test_stream_refusal_is_not_parsed_as_events(seeded, live_ui):
    ui = live_ui
    ui.el("query.text.input").fill("Ed Wood")
    ui.el("query.selector.alias").fill("no-such-alias")
    ui.el("query.run.stream").check()
    ui.el("query.run.submit").click()
    ui.expect("query.error.refusal").to_contain_text("UnsatisfiableSelectorError")
    assert len(_posts(ui, "/query/stream")) == 1
    ui.expect("query.error.generic").to_be_hidden()


def test_each_run_lands_in_the_history(seeded, live_ui):
    ui = live_ui
    _fill(ui)
    with ui.page.expect_response(_is_post("/query")) as plain:
        ui.el("query.run.submit").click()
    first = plain.value.json()["trace_token"]
    ui.expect("query.state.success").to_be_visible()

    _fill(ui, stream=True)
    with ui.page.expect_response(_is_post("/query/stream")) as streamed:
        ui.el("query.run.submit").click()
    second = _final(streamed.value.text())["trace_token"]
    ui.expect("query.state.success").to_be_visible()
    assert first != second

    ui.el("query.history.toggle").click()
    rows = ui.page.locator(HISTORY_ROWS)
    ui.expect(rows).to_have_count(2)
    ui.expect(rows.nth(0).locator("td").nth(2)).to_have_text(second[:8])
    ui.expect(rows.nth(1).locator("td").nth(2)).to_have_text(first[:8])
    entries = _stored(ui)
    assert [e["trace_token"] for e in entries] == [second, first]
    for entry in entries:
        assert sorted(entry) == ["query", "selector", "timestamp", "trace_token"]
        assert entry["query"] == "Ed Wood"
        assert sorted(entry["selector"]["capability"]) == CAPS

    ui.goto()  # a reload in the same tab keeps the history
    ui.expect(ui.page.locator(HISTORY_ROWS)).to_have_count(2)


def test_history_shows_the_50_newest_of_60(live_app, browser):
    seed = (
        f"sessionStorage.setItem('{HISTORY_KEY}', JSON.stringify(Array.from({{length: 60}}, (_, i) => ({{"
        "query: 'q' + (59 - i), selector: null, "
        "trace_token: 'tok' + String(59 - i).padStart(2, '0') + 'xxxxxxxxxxxx', "
        "timestamp: '2026-10-31T10:00:00.000Z'}))));"
    )
    with _ui(browser, live_app, lambda page: page.add_init_script(seed)) as ui:
        ui.el("query.history.toggle").click()
        rows = ui.page.locator(HISTORY_ROWS)
        ui.expect(rows).to_have_count(50)
        ui.expect(rows.nth(0).locator("td").nth(2)).to_have_text("tok59xxx")
        ui.expect(rows.nth(49).locator("td").nth(2)).to_have_text("tok10xxx")
        box = ui.el("query.history.panel").locator(".table-scroll")
        max_height, overflow_y, scrolls = box.evaluate(
            "(e) => { const s = getComputedStyle(e); return [s.maxHeight, s.overflowY, e.scrollHeight > e.clientHeight]; }"
        )
        assert (max_height, overflow_y, scrolls) == ("240px", "auto", True)


def test_history_works_when_session_storage_throws(seeded, browser):
    blocked = "Storage.prototype.setItem = function () { throw new Error('blocked'); };"
    with _ui(browser, seeded, lambda page: page.add_init_script(blocked)) as ui:
        _fill(ui)
        ui.el("query.run.submit").click()
        ui.expect("query.state.success").to_be_visible()
        ui.el("query.history.toggle").click()
        ui.expect(ui.page.locator(HISTORY_ROWS)).to_have_count(1)


def test_promote_from_result_disabled_without_trace_token(seeded, browser):
    def handler(route):
        response = route.fetch()
        env = response.json()
        env["trace_token"] = None
        route.fulfill(response=response, body=json.dumps(env))

    with _ui(browser, seeded, lambda page: page.route("**/query", handler)) as ui:
        _fill(ui)
        ui.el("query.run.submit").click()
        ui.expect("query.state.success").to_be_visible()
        ui.expect("query.result.promote").to_be_disabled()
        ui.expect(ui.page.get_by_text("No trace token on this result.", exact=True)).to_be_visible()
        assert ui.el("query.result.trace-link").get_attribute("aria-disabled") == "true"


# ---- Compare mode (18-05): one POST /compare, a bare envelope or a map keyed by the comparison key ----


@pytest.fixture(scope="module")
def answer_alias(seeded):
    """The alias ``answer`` promoted from a HippoRAG trace: a compare key literally named like the envelope field."""
    trace = seeded.query("Ed Wood", HIPPORAG)["trace_token"]
    return seeded.promote("answer", [trace])


def _open_compare(ui, text="Ed Wood"):
    ui.el("query.mode.compare").click()
    ui.el("query.text.input").fill(text)


def _row_capability(ui, i, caps=CAPS):
    ui.el(f"query.row{i}.kind").select_option("capability")
    ui.el(f"query.row{i}.capability").select_option(caps)


def _row_alias(ui, i, alias):
    ui.el(f"query.row{i}.kind").select_option("alias")
    ui.el(f"query.row{i}.alias").fill(alias)


def _two_rows(ui, second="alias"):
    """Row 1 is the HippoRAG capability set; row 2 is the alias ``answer`` (or Default)."""
    _open_compare(ui)
    _row_capability(ui, 1)
    ui.el("query.compare.add").click()
    if second == "alias":
        _row_alias(ui, 2, "answer")


def _run_compare(ui):
    with ui.page.expect_response(_is_post("/compare")) as info:
        ui.el("query.run.submit").click()
    return info.value.json()


def _sent(ui):
    posts = _posts(ui, "/compare")
    assert len(posts) == 1
    return json.loads(posts[0]["post_data"])


def _click_each_column_token(ui, columns):
    """Clicks each column's Open trace and returns the tokens the console emitted, in column order."""
    ui.page.evaluate("window.__tokens = []; Console.on('open-trace', (p) => { window.__tokens.push(p.token); })")
    for c in range(1, columns + 1):
        ui.nav("query")
        ui.el(f"query.col{c}.trace-link").click()
    return ui.page.evaluate("window.__tokens")


def test_compare_two_selectors_fills_each_column_from_its_own_key(answer_alias, live_ui):
    ui = live_ui
    _two_rows(ui)
    ui.expect("query.run.submit").to_have_text("Run compare")
    body = _run_compare(ui)

    sent = _sent(ui)
    assert set(sent) == {"query", "selectors"}
    assert sent["query"] == {"text": "Ed Wood"}
    assert set(sent["selectors"][0]) == {"capability"}
    assert sorted(sent["selectors"][0]["capability"]) == CAPS
    assert sent["selectors"][1] == {"alias": "answer"}

    # A map keyed by the comparison key, one key literally named like the envelope field `answer`.
    keys = list(body)
    assert len(keys) == 2 and "answer" in keys
    assert "trace_token" not in body
    tokens = [body[k]["trace_token"] for k in keys]
    assert tokens[0] != tokens[1]

    for c, key in enumerate(keys, start=1):
        ui.expect(f"query.col{c}.panel").to_be_visible()
        ui.expect(f"query.col{c}.header").to_contain_text(key)
        ui.expect(f"query.col{c}.answer").to_have_text(body[key]["answer"])
    ui.expect("query.col3.panel").to_be_hidden()
    assert _click_each_column_token(ui, 2) == tokens

    ui.nav("query")
    ui.el("query.history.toggle").click()
    rows = ui.page.locator(HISTORY_ROWS)
    ui.expect(rows).to_have_count(2)
    entries = _stored(ui)
    assert sorted(e["trace_token"] for e in entries) == sorted(tokens)
    by_token = {e["trace_token"]: e["selector"] for e in entries}
    assert by_token[body[keys[0]]["trace_token"]] == sent["selectors"][0]
    assert by_token[body[keys[1]]["trace_token"]] == {"alias": "answer"}
