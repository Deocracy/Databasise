"""LIVE-07 (D-07, D-09, D-17): the Ledger runs against the real API.

The row test is ``test_promote_then_query_through_the_alias``: a HippoRAG query made in the page is promoted to the
alias ``op-test`` from the Ledger screen (``POST /promote`` is sent only after the dialog's Promote), the result
is appended to the client ledger log (``sessionStorage`` key ``databasise.console.ledger-log``), and the new
``Query this alias`` link opens Query & Compare with the Alias selector set and sends nothing; the follow-up
``POST /query`` through the alias answers 200. The timeline reads ``POST /ledger/history`` and follows the
server's ``active`` and ``tombstoned`` flags (WR-JSC-01); Roll back and Retire are sent only from Confirm and
their dialogs stay open until the answer (IN-JSC-04). The no-operator app has none of the listing routes, so
the pickers, the timeline, Preview and the trace source use their client-side fallbacks (D-09). No test here
uses the live marker.

Named deviation: LIVE-07 naive query substituted: the automated LIVE-07 test promotes the trace of a HippoRAG
query instead of a naive query. The offline stub does not populate the LightRAG v2 stores, so a naive query on a
temp store is refused (18-CONTEXT D-15, 18-RESEARCH Open Question 1); the owner walkthrough in 18-11 covers the
default (LightRAG) path with real clients.
"""

from __future__ import annotations

import json
from urllib.parse import urlparse

import pytest

from databasise.tests.gui_live.conftest import HIPPORAG, open_live_ui, start_live_app
from databasise.tests.seam.test_hipporag_write_path import _DOCUMENT_TEXT

CAPS = ["reads_graph", "reads_kv"]
LOG_KEY = "databasise.console.ledger-log"


def _is_post(path):
    return lambda response: response.request.method == "POST" and urlparse(response.url).path == path


def _posts(ui, path):
    return [r for r in ui.requests if r["method"] == "POST" and r["path"] == path]


def _run_query(ui, text="Ed Wood"):
    """Runs a HippoRAG query from the page (Stream off) and returns its trace token."""
    ui.el("query.text.input").fill(text)
    ui.el("query.selector.kind-capability").check()
    ui.el("query.selector.capability").select_option(CAPS)
    ui.el("query.run.stream").set_checked(False)
    with ui.page.expect_response(_is_post("/query")) as info:
        ui.el("query.run.submit").click()
    token = info.value.json()["trace_token"]
    ui.expect("query.state.success").to_be_visible()
    return token


def test_promote_then_query_through_the_alias(seeded, live_ui):
    ui = live_ui
    token = _run_query(ui)
    ui.nav("ledger")
    rows = ui.el("ledger.promote.traces").locator("label.trace-row:not([hidden])")
    ui.expect(rows).to_have_count(1)
    ui.expect(rows.first).to_contain_text(token[:8])
    ui.el("ledger.promote.trace-1").check()
    ui.el("ledger.promote.alias").fill("op-test")
    ui.el("ledger.promote.origin-human").check()
    ui.el("ledger.promote.submit").click()
    ui.expect("shell.dialog.promote").to_be_visible()
    assert _posts(ui, "/promote") == []  # nothing is sent before the dialog's Promote

    with ui.page.expect_response(_is_post("/promote")) as info:
        ui.el("shell.dialog.promote-confirm").click()
    result = info.value.json()
    posts = _posts(ui, "/promote")
    assert len(posts) == 1
    assert json.loads(posts[0]["post_data"]) == {"alias": "op-test", "trace_ids": [token], "change_origin": "human_edit"}

    card = ui.el("ledger.promote.result")
    ui.expect(card).to_be_visible()
    ui.expect(card.locator('[data-role="version"]')).to_have_text(result["version"])
    ui.expect(card.locator('[data-role="ordinal"]')).to_have_text(str(result["generation_ordinal"]))
    stored = ui.page.evaluate(f"() => JSON.parse(sessionStorage.getItem('{LOG_KEY}'))")
    assert len(stored) == 1
    entry = stored[0]
    assert {k: entry[k] for k in ("alias", "version", "record_kind", "generation_ordinal")} == {
        "alias": "op-test",
        "version": result["version"],
        "record_kind": result["record_kind"],
        "generation_ordinal": result["generation_ordinal"],
    }
    assert entry["created_at"]

    queries = len(_posts(ui, "/query"))
    ui.el("ledger.live.query-alias").click()
    ui.expect("screen-query").to_be_visible()
    ui.expect("query.selector.kind-alias").to_be_checked()
    ui.expect("query.selector.alias").to_have_value("op-test")
    ui.expect("query.text.input").to_have_value("Ed Wood")
    ui.page.evaluate("() => fetch('/openapi.json').then((r) => r.status)")  # a round trip: any request the click started is in the list
    assert len(_posts(ui, "/query")) == queries  # the link does not run the query

    with ui.page.expect_response(_is_post("/query")) as follow:
        ui.el("query.run.submit").click()
    assert follow.value.status == 200
    assert json.loads(_posts(ui, "/query")[-1]["post_data"])["selector"] == {"alias": "op-test"}
    ui.expect("query.state.success").to_be_visible()


# ---- Task 2: timeline, Roll back, Retire, dialog safety, findings ----


def _gets(ui, path):
    return [r for r in ui.requests if r["method"] == "GET" and r["path"] == path]


def _settle(ui):
    """One round trip through the page: every request a handler started before this call is in ``ui.requests``."""
    ui.page.evaluate("() => fetch('/openapi.json').then((r) => r.status)")


def _make_lineage(app, alias, texts=("Ed Wood", "Bela Lugosi")):
    """Two HippoRAG queries made over httpx, promoted one after the other to ``alias``."""
    a = app.query(texts[0], HIPPORAG)["trace_token"]
    b = app.query(texts[1], HIPPORAG)["trace_token"]
    v1 = app.promote(alias, [a])["version"]
    v2 = app.promote(alias, [b])["version"]
    return {"alias": alias, "a": a, "b": b, "v1": v1, "v2": v2}


@pytest.fixture(scope="module")
def lineage(seeded):
    return _make_lineage(seeded, "lin")


def _timeline_rows(ui):
    return ui.el("ledger.timeline.table").locator("tbody tr:not([hidden])")


def _statuses(ui):
    return [t.strip() for t in _timeline_rows(ui).locator('[data-role="status"]').all_inner_texts()]


def _open_timeline(ui, alias, rows=None):
    """Chooses ``alias`` in the timeline; ``rows=None`` waits for any rows (the shared lineage may have been changed)."""
    ui.nav("ledger")
    ui.el("ledger.timeline.alias").select_option(alias)
    if rows is None:
        ui.expect(_timeline_rows(ui).first).to_be_visible()
    else:
        ui.expect(_timeline_rows(ui)).to_have_count(rows)


def _fill_promote_form(ui, token, alias):
    """Sends ``token`` to the promote form the way Query and Compare do, then fills the rest."""
    ui.nav("ledger")
    ui.page.evaluate("(t) => Console.emit('promote', { trace: t })", token)
    ui.el("ledger.promote.alias").fill(alias)
    ui.el("ledger.promote.origin-human").check()


def test_rollback_and_retire_through_the_timeline_update_the_rows(lineage, live_ui):
    ui = live_ui
    _open_timeline(ui, "lin", 2)
    assert len(_posts(ui, "/ledger/history")) == 1
    assert json.loads(_posts(ui, "/ledger/history")[0]["post_data"]) == {"alias": "lin", "limit": 50, "offset": 0}
    assert _statuses(ui) == ["—", "active"]

    ui.el("ledger.timeline.rollback-1").click()
    ui.expect("shell.dialog.rollback").to_be_visible()
    assert _posts(ui, "/rollback") == []
    # With the server history the 17-UI-SPEC body names the active version.
    ui.expect(ui.el("shell.dialog.rollback").locator('[data-role="body"]')).to_have_text(
        f"Roll back lin from active version {lineage['v2']} to {lineage['v1']}? A new version will be minted."
    )
    ui.el("shell.dialog.rollback-traces").select_option(lineage["a"])
    ui.el("shell.dialog.rollback-origin-human").check()
    history, aliases = len(_posts(ui, "/ledger/history")), len(_gets(ui, "/ledger/aliases"))
    with ui.page.expect_response(_is_post("/rollback")) as info:
        ui.el("shell.dialog.rollback-confirm").click()
    assert info.value.status == 200
    assert len(_posts(ui, "/rollback")) == 1
    assert json.loads(_posts(ui, "/rollback")[0]["post_data"]) == {
        "alias": "lin",
        "version": lineage["v1"],
        "trace_ids": [lineage["a"]],
        "change_origin": "human_edit",
    }
    ui.expect("shell.dialog.rollback").to_be_hidden()
    ui.expect(_timeline_rows(ui)).to_have_count(3)
    assert len(_posts(ui, "/ledger/history")) == history + 1
    assert len(_gets(ui, "/ledger/aliases")) == aliases + 1
    assert _statuses(ui) == ["target of active rollback", "—", "active"]

    ui.el("ledger.timeline.retire-2").click()
    ui.expect("shell.dialog.retire").to_be_visible()
    ui.el("shell.dialog.retire-version").fill(lineage["v2"])
    ui.el("shell.dialog.retire-traces").select_option(lineage["b"])
    ui.el("shell.dialog.retire-origin-human").check()
    with ui.page.expect_response(_is_post("/retire")) as info:
        ui.el("shell.dialog.retire-confirm").click()
    assert info.value.status == 200
    assert len(_posts(ui, "/retire")) == 1
    assert json.loads(_posts(ui, "/retire")[0]["post_data"])["version"] == lineage["v2"]
    ui.expect(_timeline_rows(ui)).to_have_count(4)
    assert _statuses(ui) == ["target of active rollback", "tombstoned", "active", "—"]
    for n in (1, 2, 3):
        ui.expect(f"ledger.timeline.retire-{n}").to_be_disabled()


@pytest.fixture(scope="module")
def dismiss_lineage(seeded):
    return _make_lineage(seeded, "dis")


def test_dialog_dismiss_after_open_sends_nothing(dismiss_lineage, live_ui):
    info = dismiss_lineage
    ui = live_ui
    _open_timeline(ui, "dis", 2)
    _fill_promote_form(ui, info["a"], "dis-new")
    openers = [
        ("shell.dialog.promote", lambda: ui.el("ledger.promote.submit").click(), "shell.dialog.promote-cancel"),
        ("shell.dialog.rollback", lambda: ui.el("ledger.timeline.rollback-1").click(), "shell.dialog.rollback-cancel"),
        ("shell.dialog.retire", lambda: ui.el("ledger.timeline.retire-1").click(), "shell.dialog.retire-cancel"),
    ]
    for dialog, open_it, cancel in openers:
        open_it()
        ui.expect(dialog).to_be_visible()
        ui.el(cancel).click()
        ui.expect(dialog).to_be_hidden()
        open_it()
        ui.expect(dialog).to_be_visible()
        ui.page.keyboard.press("Escape")
        ui.expect(dialog).to_be_hidden()
    _settle(ui)
    for path in ("/promote", "/rollback", "/retire"):
        assert _posts(ui, path) == []


def test_dialog_stays_open_while_the_write_is_in_flight(seeded, live_ui):
    ui = live_ui
    token = _run_query(ui)
    ui.nav("ledger")
    ui.el("ledger.promote.trace-1").check()
    ui.el("ledger.promote.alias").fill("hold-test")
    ui.el("ledger.promote.origin-human").check()
    ui.el("ledger.promote.submit").click()
    ui.expect("shell.dialog.promote").to_be_visible()
    with seeded.hold("promote") as release:
        ui.el("shell.dialog.promote-confirm").click()
        ui.expect("shell.dialog.promote-confirm").to_be_disabled()
        ui.expect("shell.dialog.promote-cancel").to_be_disabled()
        ui.expect(ui.el("shell.dialog.promote").locator('[data-role="sending"]')).to_have_text(
            "Sending. A request that has been sent cannot be cancelled."
        )
        ui.page.keyboard.press("Escape")
        ui.page.keyboard.press("Escape")
        ui.expect("shell.dialog.promote").to_be_visible()
        release.set()
    ui.expect("shell.dialog.promote").to_be_hidden()
    ui.expect("ledger.promote.result").to_be_visible()
    assert len(_posts(ui, "/promote")) == 1
    assert json.loads(_posts(ui, "/promote")[0]["post_data"])["trace_ids"] == [token]


def test_preview_reads_the_checked_traces_when_it_arrives(seeded, live_ui):
    ui = live_ui
    _run_query(ui)
    ui.nav("ledger")
    ui.el("ledger.promote.trace-1").check()
    ui.el("ledger.promote.alias").fill("preview-test")
    ui.el("ledger.promote.origin-human").check()
    with seeded.hold("preview_promotion") as release:
        with ui.page.expect_request(lambda r: r.method == "POST" and urlparse(r.url).path == "/promote/preview"):
            ui.el("ledger.promote.preview").click()
        # The boxes are disabled while Preview is pending, so the race is made through the DOM: no trace is checked
        # when the answer arrives.
        ui.page.evaluate(
            """() => {
                const box = document.querySelector('[data-mock-id="ledger.promote.trace-1"]');
                box.checked = false;
                box.dispatchEvent(new Event('change', { bubbles: true }));
            }"""
        )
        with ui.page.expect_response(_is_post("/promote/preview")):
            release.set()
    _settle(ui)
    ui.expect("ledger.promote.preview-result").to_be_hidden()
    assert ui.el("ledger.promote.preview-result").locator("dl dt").count() == 0


def test_page_size_message_survives_hide_errors(lineage, live_ui):
    ui = live_ui
    ui.nav("ledger")
    ui.el("ledger.timeline.page-size").fill("101")
    ui.expect("ledger.timeline.page-size-error").to_have_text("Page size must be between 1 and 100.")
    _fill_promote_form(ui, lineage["a"], "size-test")
    with ui.page.expect_response(_is_post("/promote/preview")):
        ui.el("ledger.promote.preview").click()  # hideErrors runs when Preview starts
    ui.expect("ledger.promote.preview-result").to_be_visible()
    ui.expect("ledger.timeline.page-size-error").to_have_text("Page size must be between 1 and 100.")
    ui.expect("ledger.timeline.page-size").to_have_attribute("aria-invalid", "true")


def test_invalid_page_size_during_an_in_flight_load_leaves_no_loading_state(lineage, dismiss_lineage, seeded, live_ui):
    """A new alias choice drops the read in flight; when the page size then blocks the new read, nothing is loading."""
    ui = live_ui
    _open_timeline(ui, "lin")
    with seeded.hold("ledger_history"):
        ui.el("ledger.timeline.alias").select_option("dis")
        ui.expect("ledger.timeline.loading").to_be_visible()
        ui.el("ledger.timeline.page-size").fill("101")
        ui.expect("ledger.timeline.page-size-error").to_have_text("Page size must be between 1 and 100.")
        ui.el("ledger.timeline.alias").select_option("lin")
        ui.expect("ledger.timeline.loading").to_be_hidden()
        ui.expect("ledger.timeline.table").to_have_attribute("aria-busy", "false")


def test_promote_event_replaces_the_preselection(seeded, live_ui):
    ui = live_ui
    first = _run_query(ui, "Ed Wood")
    ui.expect("query.result.promote").to_be_enabled()
    ui.el("query.result.promote").click()
    ui.expect("screen-ledger").to_be_visible()
    ticked = ui.el("ledger.promote.traces").locator("label[data-token]:not([hidden]) input:checked")
    ui.expect(ticked).to_have_count(1)
    ui.nav("query")
    second = _run_query(ui, "Bela Lugosi")
    assert second != first
    ui.expect("query.result.promote").to_be_enabled()
    ui.el("query.result.promote").click()
    ui.expect("screen-ledger").to_be_visible()
    ui.expect(ticked).to_have_count(1)
    ui.expect(ui.el("ledger.promote.traces").locator(f'label[data-token="{second}"] input')).to_be_checked()
    ui.expect(ui.el("ledger.promote.traces").locator(f'label[data-token="{first}"] input')).not_to_be_checked()


def test_recent_runs_source_lists_server_traces(seeded, browser):
    a = seeded.query("Ed Wood", HIPPORAG)["trace_token"]
    b = seeded.query("Bela Lugosi", HIPPORAG)["trace_token"]
    fake = "f" * 64

    def handler(route):
        response = route.fetch()
        body = response.json()
        body["items"].append({"trace_reference": fake, "created_at": "2026-10-31T10:00:00Z", "partial": True, "degraded": False, "stop_reason": "budget"})
        route.fulfill(response=response, body=json.dumps(body))

    ui = open_live_ui(browser, seeded, before_goto=lambda page: page.route(lambda url: urlparse(url).path == "/traces", handler))
    try:
        ui.nav("ledger")
        assert _gets(ui, "/traces") == []
        ui.el("ledger.promote.source-recent").check()
        rows = ui.el("ledger.promote.traces").locator("label.trace-row:not([hidden])")
        ui.expect(rows.filter(has_text=a[:8])).to_have_count(1)
        ui.expect(rows.filter(has_text=b[:8])).to_have_count(1)
        assert len(_gets(ui, "/traces")) == 1
        assert _gets(ui, "/traces")[0]["url"].endswith("/traces?limit=50&offset=0")
        partial = rows.filter(has_text=fake[:8])
        ui.expect(partial.locator(".chip")).to_contain_text("partial")
        partial.locator("input").check()
        ui.expect(ui.el("ledger.promote.preflight")).to_contain_text("is a partial run and cannot be promoted")
        ui.expect("ledger.promote.submit").to_be_disabled()
        ui.el("ledger.promote.source-history").check()
        ui.expect(rows).to_have_count(0)
        _settle(ui)
        assert len(_gets(ui, "/traces")) == 1
        assert ui.page.locator('[data-mock-id="screen-ledger"] [data-needs-backend="GET /traces"]').count() == 0
    finally:
        ui.close()


def test_history_source_blocks_a_partial_run(seeded, browser):
    """R18-02: a remembered run carries partial and degraded, so the History source can block a partial trace."""

    def handler(route):
        response = route.fetch()
        body = response.json()
        body["partial"] = True
        body["stop_reason"] = "budget"
        route.fulfill(response=response, body=json.dumps(body))

    ui = open_live_ui(browser, seeded, before_goto=lambda page: page.route("**/query", handler))
    try:
        ui.el("query.text.input").fill("Ed Wood")
        ui.el("query.selector.kind-capability").check()
        ui.el("query.selector.capability").select_option(CAPS)
        ui.el("query.run.stream").set_checked(False)
        with ui.page.expect_response(_is_post("/query")) as info:
            ui.el("query.run.submit").click()
        env = info.value.json()
        token = env["trace_token"]
        ui.expect("query.state.partial").to_be_visible()
        stored = ui.page.evaluate("() => JSON.parse(sessionStorage.getItem('databasise.console.history'))")
        assert [(e["trace_token"], e["partial"], e["degraded"]) for e in stored] == [(token, True, bool(env["degraded"]))]

        ui.nav("ledger")
        row = ui.el("ledger.promote.traces").locator(f'label[data-token="{token}"]')
        ui.expect(row.locator('[data-role="chips"]')).to_contain_text("partial")
        row.locator("input").check()
        ui.el("ledger.promote.alias").fill("partial-run")
        ui.el("ledger.promote.origin-human").check()
        ui.expect("ledger.promote.preflight").to_contain_text("is a partial run and cannot be promoted")
        ui.expect("ledger.promote.submit").to_be_disabled()
    finally:
        ui.close()


def test_timeline_cells_do_not_wrap_at_1440(lineage, live_ui):
    ui = live_ui
    ui.page.set_viewport_size({"width": 1440, "height": 900})
    _open_timeline(ui, "lin")
    probe = """() => {
        const row = document.querySelector('[data-mock-id="ledger.timeline.table"] tbody tr:not([hidden])');
        const white = (el) => getComputedStyle(el).whiteSpace;
        const status = row.querySelector('[data-role="status"]');
        const ruler = document.createElement('span');
        ruler.style.width = '16ch';
        ruler.style.display = 'inline-block';
        status.appendChild(ruler);
        const sixteen = ruler.getBoundingClientRect().width;
        ruler.remove();
        return {
            kind: white(row.querySelector('[data-role="kind"]').parentElement),
            origin: white(row.querySelector('[data-role="origin"]')),
            created: white(row.querySelector('[data-role="created"]')),
            minWidth: parseFloat(getComputedStyle(status).minWidth),
            sixteen,
            gap: getComputedStyle(row.querySelector('.row-actions')).columnGap,
        };
    }"""
    got = ui.page.evaluate(probe)
    assert (got["kind"], got["origin"], got["created"]) == ("nowrap", "nowrap", "nowrap")
    assert abs(got["minWidth"] - got["sixteen"]) < 1
    assert got["gap"] == "8px"


# ---- Task 3: no listing routes (no --operator) ----


@pytest.fixture(scope="module")
def plain_app(tmp_path_factory, corpus_fake):
    """No ``--operator``: GET /ledger/aliases, POST /ledger/history, POST /promote/preview and GET /traces are not mounted."""
    live = start_live_app(tmp_path_factory.mktemp("store-plain"), operator=False)
    live.corpus = corpus_fake
    if live.start_error is None:
        live.ingest(_DOCUMENT_TEXT, "seed-plain", HIPPORAG)
    yield live
    live.stop()


def _promote_in_ui(ui, alias):
    """Runs a query in the page and promotes it to ``alias`` through the dialog; returns the minted version."""
    _run_query(ui)
    ui.nav("ledger")
    ui.el("ledger.promote.trace-1").check()
    ui.el("ledger.promote.alias").fill(alias)
    ui.el("ledger.promote.origin-human").check()
    ui.el("ledger.promote.submit").click()
    with ui.page.expect_response(_is_post("/promote")) as info:
        ui.el("shell.dialog.promote-confirm").click()
    ui.expect("ledger.promote.result").to_be_visible()
    return info.value.json()["version"]


def test_without_listing_routes_the_ledger_uses_the_client_log(plain_app, browser):
    assert plain_app.start_error is None, plain_app.start_error
    ui = open_live_ui(browser, plain_app)
    try:
        version = _promote_in_ui(ui, "fb-test")

        # The alias list comes from the client log; its wrapper keeps the badge.
        ui.expect("ledger.aliases.table").to_contain_text("fb-test")
        ui.expect("ledger.aliases.panel").to_contain_text("From this browser's ledger log; no route lists aliases.")
        wrapper = ui.page.locator('[data-needs-backend="GET /ledger/aliases"]:has([data-mock-id="ledger.aliases.panel"])')
        assert wrapper.count() == 1
        assert wrapper.locator(".badge-op").count() >= 1

        # The timeline shows the log row, with no server status.
        ui.el("ledger.timeline.alias").select_option("fb-test")
        ui.expect(_timeline_rows(ui)).to_have_count(1)
        assert _statuses(ui) == ["—"]
        ui.expect("ledger.timeline.notice").to_have_text("Showing this browser's ledger log only; the server history route is not mounted.")
        ui.expect("ledger.timeline.retire-1").to_be_disabled()
        ui.expect(ui.el("ledger.timeline.region").locator('[data-role="retire-wrap"]').first).to_have_attribute(
            "title", "Needs the server history to confirm this version is not active."
        )
        ui.expect("ledger.timeline.rollback-1").to_be_enabled()
        ui.el("ledger.timeline.rollback-1").click()
        ui.expect(ui.el("shell.dialog.rollback").locator('[data-role="body"]')).to_have_text(
            f"Roll back fb-test from the active version (not known in this browser) to {version}? A new version will be minted."
        )
        ui.el("shell.dialog.rollback-cancel").click()
        assert _posts(ui, "/ledger/history") == []

        # Preview is not mounted: the button works and prints the unavailable line.
        ui.expect("ledger.promote.preview").to_be_enabled()
        ui.el("ledger.promote.preview").click()
        preview = ui.el("ledger.promote.preview-result")
        ui.expect(preview).to_contain_text("Preview unavailable: POST /promote/preview is not mounted.")
        ui.expect(preview).to_contain_text(f"Last known active version in this browser: {version}.")
        assert _posts(ui, "/promote/preview") == []

        # GET /traces is not mounted: the source is disabled with its reason, and the history source works.
        ui.expect("ledger.promote.source-recent").to_be_disabled()
        ui.expect(ui.el("screen-ledger").get_by_text("Needs GET /traces.", exact=True)).to_be_visible()
        ui.expect("ledger.promote.source-history").to_be_checked()
        ui.expect(ui.el("ledger.promote.traces").locator("label.trace-row:not([hidden])")).to_have_count(1)
        assert _gets(ui, "/traces") == []
    finally:
        ui.close()


def test_query_alias_picker_falls_back_to_the_client_log(plain_app, browser):
    assert plain_app.start_error is None, plain_app.start_error
    ui = open_live_ui(browser, plain_app)
    try:
        version = _promote_in_ui(ui, "fb-pick")
        stored = ui.page.evaluate(f"() => JSON.parse(sessionStorage.getItem('{LOG_KEY}'))")
        assert [(e["alias"], e["version"]) for e in stored] == [("fb-pick", version)]

        ui.nav("query")
        ui.el("query.selector.kind-alias").check()
        picker = ui.el("query.selector.alias-picker")
        ui.expect(picker.locator("option")).to_have_text(["Choose an alias", f"fb-pick ({version})"])
        wrapper = ui.page.locator('[data-mock-id="screen-query"] [data-needs-backend="GET /ledger/aliases"]')
        assert wrapper.count() >= 1
        ui.expect(wrapper.first).to_contain_text("From this browser's ledger log; no route lists aliases.")
        assert wrapper.first.locator(".badge-op").count() >= 1
        picker.select_option("fb-pick")
        ui.expect("query.selector.alias").to_have_value("fb-pick")
    finally:
        ui.close()
