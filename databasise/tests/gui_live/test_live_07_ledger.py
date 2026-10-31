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

from databasise.tests.gui_live.conftest import HIPPORAG, open_live_ui, start_live_app  # noqa: F401

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
