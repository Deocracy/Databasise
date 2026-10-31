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
import re
from urllib.parse import parse_qs, urlparse

import pytest

from databasise.tests.gui_live.conftest import open_live_ui, start_live_app

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


# ---- polls and the health banner (D-13, WR-JSB-04) ----

CLOCK = lambda page: page.clock.install()  # noqa: E731  (time then flows normally until fast_forward)
HHMMSS = r"\d\d:\d\d:\d\d"


def _settle(ui):
    """One round trip through the page: every request a timer started before this call is in ``ui.requests``."""
    ui.page.evaluate("() => fetch('/openapi.json').then((r) => r.status)")


def _wait_for_post(ui, path):
    for _ in range(100):  # bounded: a console that never sends must fail, not hang
        if [r for r in ui.requests if r["method"] == "POST" and r["path"] == path]:
            return
        ui.page.wait_for_timeout(50)
    raise AssertionError(f"no POST {path} was sent")


def _fill_query(ui):
    ui.el("query.text.input").fill("Ed Wood")
    ui.el("query.selector.kind-capability").check()
    ui.el("query.selector.capability").select_option(CAPS)
    ui.el("query.run.stream").set_checked(False)


def test_health_poll_is_off_by_default(live_app, browser):
    with _ui(browser, live_app, CLOCK) as ui:
        ui.nav("corpus")
        ui.page.clock.fast_forward(120000)
        _settle(ui)
        assert len(_gets(ui, "/health")) == 1
        ui.expect("corpus.live.health-polled").to_have_text(re.compile(rf"^Polling off\. Last checked {HHMMSS}\.$"))


def test_health_poll_skips_ticks_while_a_query_is_in_flight(seeded, browser):
    with _ui(browser, seeded, CLOCK) as ui:
        ui.nav("corpus")
        ui.el("corpus.health.poll-interval").select_option("30")
        ui.el("corpus.health.poll").check()
        ui.nav("query")
        _fill_query(ui)
        before = len(_gets(ui, "/health"))
        with seeded.hold("query") as release:
            ui.el("query.run.submit").click()
            _wait_for_post(ui, "/query")
            ui.page.clock.fast_forward(31000)
            _settle(ui)
            assert len(_gets(ui, "/health")) == before
            ui.expect("corpus.live.health-polled").to_have_text(re.compile(rf"^Check skipped at {HHMMSS}: a request is in flight\.$"))
            release.set()
        ui.expect("query.state.success").to_be_visible()
        ui.page.clock.fast_forward(31000)
        _settle(ui)
        assert len(_gets(ui, "/health")) == before + 1
        ui.expect("corpus.live.health-polled").to_have_text(re.compile(rf"^Polling every 30 seconds\. Last checked {HHMMSS}\.$"))


def test_counts_poll_only_while_a_non_terminal_count_is_above_zero(corpus_docs, live_app, browser):
    # "pending" and not "processing": with no write holding the gate the engine folds processing into interrupted.
    corpus_docs["doc-1"]["status"] = "pending"
    with _ui(browser, live_app, CLOCK) as ui:
        ui.nav("corpus")
        ui.expect(_tile(ui, "pending")).to_have_text("1")
        ui.el("corpus.table.poll").check()
        ui.expect("corpus.live.counts-polled").to_have_text("Updating every 30 seconds while documents are in progress.")
        polled = len(_gets(ui, "/corpus/counts"))
        ui.page.clock.fast_forward(31000)
        _settle(ui)
        assert len(_gets(ui, "/corpus/counts")) == polled + 1

        corpus_docs["doc-1"]["status"] = "processed"
        ui.page.clock.fast_forward(31000)
        _settle(ui)
        assert len(_gets(ui, "/corpus/counts")) == polled + 2
        ui.expect(_tile(ui, "processed")).to_have_text("5")
        ui.expect("corpus.live.counts-polled").to_have_text("Polling paused: no documents in progress.")

        ui.page.clock.fast_forward(62000)
        _settle(ui)
        assert len(_gets(ui, "/corpus/counts")) == polled + 2


def test_health_banner_survives_table_actions(corpus_docs, live_app, browser):
    with _ui(browser, live_app, lambda page: page.route("**/health", lambda route: route.abort())) as ui:
        ui.nav("corpus")
        banner = ui.el("corpus.error.generic")
        ui.expect(banner).to_contain_text("Server unreachable")
        rows = ui.el("corpus.health.stores").locator("tbody tr")
        ui.expect(rows).to_have_count(10)
        assert all("not probed" in text for text in rows.all_inner_texts())

        ui.el("corpus.table.page-size").fill("2")
        ui.el("corpus.table.refresh").click()
        ui.expect(ui.el("corpus.table.panel").locator('[data-role="range"]')).to_have_text("Showing 1 to 2 of 5")
        ui.el("corpus.table.next").click()
        ui.expect(ui.el("corpus.table.panel").locator('[data-role="range"]')).to_have_text("Showing 3 to 4 of 5")
        ui.expect(banner).to_be_visible()
        ui.expect(banner).to_contain_text("Server unreachable")

        ui.page.unroute("**/health")
        ui.el("corpus.health.refresh").click()
        ui.expect(banner).to_be_hidden()
        ui.expect("corpus.health.state").not_to_have_text("unreachable")


# ---- operator panels, retry, absent controls, Open in Corpus (D-06, D-09, IN-JSB-06, IN-JSB-07) ----

SCREEN = '[data-mock-id="screen-corpus"]'


@pytest.fixture(scope="module")
def log_app(tmp_path_factory, corpus_fake):
    live = start_live_app(tmp_path_factory.mktemp("store-log"), log_file=tmp_path_factory.mktemp("log") / "server.log")
    live.corpus = corpus_fake
    yield live
    live.stop()


def _row(ui, document_id):
    return ui.page.locator(f'{SCREEN} tbody tr:has([data-role="id"]:text-is("{document_id}"))')


def test_operator_panels_read_info_wirings_and_log(log_app, browser):
    log_app.log_file.write_text("first log line\nsecond log line\n", encoding="utf-8")
    info = log_app.http.get("/info").json()
    wirings = log_app.http.get("/wirings").json()
    with _ui(browser, log_app) as ui:
        ui.nav("corpus")
        ui.expect("corpus.instance.version").to_have_text(info["version"])
        ui.expect("corpus.instance.workspace").to_have_text(info["workspace"])

        ui.el("corpus.wirings.toggle").click()
        ui.expect(ui.el("corpus.wirings.table").locator("tbody tr")).to_have_count(len(wirings))
        ui.expect(ui.el("corpus.wirings.table").locator("tbody tr").first).to_contain_text(wirings[0]["name"])

        ui.el("corpus.log.toggle").click()
        ui.el("corpus.log.refresh").click()
        ui.expect("corpus.log.lines").to_contain_text("second log line")
        assert _gets(ui, "/log")[-1]["url"].endswith("/log?limit=100")

        for route in ("GET /info", "GET /wirings", "GET /log"):
            assert ui.page.locator(f'{SCREEN} [data-needs-backend="{route}"]').count() == 0, route


def test_busy_mirror_shows_the_header_chips(corpus_docs, live_app, browser):
    info = {**live_app.http.get("/info").json(), "write_in_flight": True, "graph_busy": False}

    def busy(page):
        page.route("**/info", lambda route: route.fulfill(json=info))

    with _ui(browser, live_app, busy) as ui:
        ui.nav("corpus")
        ui.expect("corpus.health.busy").to_contain_text("write in flight")
        ui.expect("shell.live.busy").to_contain_text("write in flight")
        ui.expect("corpus.health.busy").not_to_contain_text("graph in use")


def test_retry_targets_the_document_captured_at_press_time(corpus_docs, live_app, browser):
    # "processing" is listed as interrupted when no write holds the gate.
    corpus_docs["doc-3"]["status"] = "processing"
    held = []
    with _ui(browser, live_app, lambda page: page.route("**/documents/*/retry", lambda route: held.append(route))) as ui:
        ui.nav("corpus")
        ui.expect(_row(ui, "doc-3").locator('[data-role="status"]')).to_contain_text("interrupted")
        _row(ui, "doc-3").locator('[data-mock-id^="corpus.table.retry-"]').click()
        for _ in range(100):  # bounded: the press must send the request
            if held:
                break
            ui.page.wait_for_timeout(50)
        assert len(held) == 1

        # The row order changes while the answer is outstanding: doc-3 moves from the third row to the second.
        corpus_docs["doc-1"] = corpus_docs.pop("doc-1")
        ui.el("corpus.table.refresh").click()
        ui.expect(ui.page.locator(f'{SCREEN} tbody tr:not([hidden]) [data-role="id"]').first).to_have_text("doc-2")
        held[0].fulfill(json={"job_id": "j-retry", "enqueued": 1, "seam_events": []})

        ui.expect(_row(ui, "doc-3").locator('[data-role="retry-msg"]')).to_contain_text("j-retry")
        for other in ("doc-2", "doc-4", "doc-5", "doc-1"):
            ui.expect(_row(ui, other).locator('[data-role="retry-msg"]')).to_be_hidden()
        posts = [r for r in ui.requests if r["method"] == "POST" and r["path"].endswith("/retry")]
        assert [r["path"] for r in posts] == ["/documents/doc-3/retry"]


def test_absent_corpus_controls_are_disabled_with_their_route(corpus_docs, live_app, live_ui):
    ui = live_ui
    corpus_docs["doc-2"]["status"] = "failed"
    ui.nav("corpus")
    ui.expect(_tile(ui, "failed")).to_have_text("1")
    for control in ("status-filter", "sort", "search", "reprocess"):
        ui.expect(f"corpus.table.{control}").to_be_disabled()
    ui.expect(ui.page.get_by_text("Needs GET /corpus (status, sort, search).")).to_be_visible()
    ui.expect(ui.page.get_by_text("Needs POST /documents/reprocess.")).to_be_visible()

    before = len(_gets(ui, "/corpus"))
    ui.el("corpus.kpi.processed").click()
    assert _row_ids(ui) == ["doc-1", "doc-3", "doc-4", "doc-5"]
    ui.el("corpus.kpi.failed").click()
    assert _row_ids(ui) == ["doc-2"]
    assert len(_gets(ui, "/corpus")) == before  # the tile filter is client-side

    ui.el("corpus.catalogue.toggle").click()
    ui.expect(ui.el("corpus.catalogue.table").locator("tbody tr").first).to_be_visible()
    ui.expect(ui.page.locator(f'{SCREEN} [data-needs-backend="GET /refusals"] .badge-nb')).to_be_visible()


def test_focus_document_marks_the_row_or_says_not_on_page(corpus_docs, live_ui):
    ui = live_ui
    # Evidence shows Corpus and emits in the same tick, before the first page has loaded: the focus waits for the page.
    ui.page.evaluate("() => { Console.show('corpus'); Console.emit('focus-document', 'doc-2'); }")
    ui.expect(_row(ui, "doc-2")).to_have_attribute("aria-current", "true")
    ui.expect(_row(ui, "doc-2")).to_be_focused()
    ui.page.evaluate("() => Console.emit('focus-document', 'doc-99')")
    ui.expect(ui.page.get_by_text("Document doc-99 is not on the loaded page.")).to_be_visible()
    ui.expect(_row(ui, "doc-2")).not_to_have_attribute("aria-current", "true")
