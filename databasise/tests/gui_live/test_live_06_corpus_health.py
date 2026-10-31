"""LIVE-06 (D-05, D-13): Corpus & Health runs against the real API.

The row test is ``test_health_poll_skips_ticks_while_a_query_is_in_flight``: with Poll health on, a tick
that falls while a query is in flight is skipped, the indicator says so, and the next tick after the
query ends sends ``GET /health`` again. The first show of the screen sends ``GET /corpus?limit=&offset=``
and ``GET /corpus/counts``; paging follows the response's ``next_offset`` (the client keeps the offset it
asked for, because neither route echoes it). The counts poll runs only while a non-terminal count is above
zero. Polls are driven with ``page.clock``, never with real waits. No test here uses the live marker.
"""

from __future__ import annotations

import contextlib
from urllib.parse import parse_qs, urlparse

import pytest

from databasise.tests.gui_live.conftest import open_live_ui

CAPS = ["reads_graph", "reads_kv"]
DOCS = ["doc-1", "doc-2", "doc-3", "doc-4", "doc-5"]


@pytest.fixture
def corpus_docs(live_app):
    """Resets the shared fake before every test: five processed documents, in this order."""
    live_app.corpus.clear()
    for doc_id in DOCS:
        live_app.corpus[doc_id] = {"track_id": None, "status": "processed"}
    return live_app.corpus


@contextlib.contextmanager
def _ui(browser, app, before_goto=None):
    ui = open_live_ui(browser, app, before_goto=before_goto)
    try:
        yield ui
    finally:
        ui.close()


def _gets(ui, path):
    return [r for r in ui.requests if r["method"] == "GET" and r["path"] == path]


def _query_of(request):
    return {key: values[0] for key, values in parse_qs(urlparse(request["url"]).query).items()}


def _is_get(path):
    return lambda response: response.request.method == "GET" and urlparse(response.url).path == path


def _row_ids(ui):
    return ui.el("corpus.table.documents").locator('tbody tr:not([hidden]) [data-role="id"]').all_inner_texts()


def _tile(ui, status):
    return ui.el(f"corpus.kpi.{status}").locator('[data-role="count"]')


def test_corpus_first_show_loads_rows_and_counts(corpus_docs, live_ui):
    ui = live_ui
    ui.nav("corpus")
    ui.expect(_tile(ui, "total")).to_have_text("5")
    ui.expect(_tile(ui, "processed")).to_have_text("5")
    assert _row_ids(ui) == DOCS
    pages = _gets(ui, "/corpus")
    assert len(pages) == 1
    assert _query_of(pages[0]) == {"limit": "50", "offset": "0"}
    assert len(_gets(ui, "/corpus/counts")) == 1


def test_corpus_paging_follows_next_offset(corpus_docs, live_app, live_ui):
    ui = live_ui
    ui.nav("corpus")
    ui.expect(_tile(ui, "total")).to_have_text("5")
    ui.el("corpus.table.page-size").fill("2")
    with ui.page.expect_response(_is_get("/corpus")) as first:
        ui.el("corpus.table.refresh").click()
    next_offset = first.value.json()["next_offset"]
    assert next_offset == 2
    ui.expect("corpus.table.next").to_be_enabled()

    with live_app.hold("corpus_status") as release:
        ui.el("corpus.table.next").click()
        ui.expect("corpus.table.panel").to_have_attribute("aria-busy", "true")
        ui.expect("corpus.table.prev").to_be_disabled()
        ui.expect("corpus.table.next").to_be_disabled()
        ui.expect("corpus.table.refresh").to_be_disabled()
        release.set()
    ui.expect("corpus.table.panel").not_to_have_attribute("aria-busy", "true")
    ui.expect(ui.el("corpus.table.panel").locator('[data-role="range"]')).to_have_text("Showing 3 to 4 of 5")
    assert _row_ids(ui) == ["doc-3", "doc-4"]
    assert _query_of(_gets(ui, "/corpus")[-1]) == {"limit": "2", "offset": str(next_offset)}

    ui.el("corpus.table.prev").click()
    ui.expect(ui.el("corpus.table.panel").locator('[data-role="range"]')).to_have_text("Showing 1 to 2 of 5")
    assert _query_of(_gets(ui, "/corpus")[-1]) == {"limit": "2", "offset": "0"}
