"""LIVE-05 (D-07, D-13, D-14, D-15): Documents & Jobs run against the real API.

The row test is ``test_query_run_is_disabled_while_an_ingest_is_in_flight``: while an ingest, upload or
delete is in flight (``LiveApp.hold``), Run on Query and Compare is natively disabled with a visible reason,
and it is enabled again when the write ends (D-13 as amended 2026-10-31: LIVE-05 governs). Submit document
sends ``POST /documents``; the returned job id goes into the client job list and the drawer loads it with
``GET /jobs/{job_id}``. A delete is sent only from the dialog's Confirm and refreshes the Corpus table and
counts. The different-stores notice stays until the owner rules at the 18-11 click-through (D-15 as
amended 2026-10-31). Polls are driven with ``page.clock``, never with real waits. No test here uses the
live marker.

Named deviation (D-15, 18-RESEARCH Open Question 1): query-after-ingest is proven on the HippoRAG selector
only. The offline stub does not populate the LightRAG v2 stores, so the default path is left to the D-20
owner walkthrough.
"""

from __future__ import annotations

import contextlib
import json
import re
from urllib.parse import parse_qs, urlparse

import pytest

from databasise.tests.gui_live.conftest import open_live_ui, start_live_app

DOCS_TEXT = "Live paste ingest text for the documents screen."
CLOCK = lambda page: page.clock.install()  # noqa: E731  (time then flows normally until fast_forward)


def _is_post(path):
    return lambda response: response.request.method == "POST" and urlparse(response.url).path == path


def _posts(ui, path):
    return [r for r in ui.requests if r["method"] == "POST" and r["path"] == path]


def _gets(ui, path):
    return [r for r in ui.requests if r["method"] == "GET" and r["path"] == path]


def _job_ids(ui):
    return ui.el("documents.jobs.documents").locator('tbody tr:not([hidden]) [data-role="id"]').all_inner_texts()


def test_paste_ingest_stores_the_job_and_the_drawer_shows_its_document(live_app, live_ui):
    ui = live_ui
    ui.nav("documents")
    ui.el("documents.paste.text").fill(DOCS_TEXT)
    ui.el("documents.paste.document-id").fill("doc-live-1")
    ui.expect("documents.paste.submit").to_have_text("Submit document")
    with ui.page.expect_response(_is_post("/documents")) as info:
        ui.el("documents.paste.submit").click()
    job_id = info.value.json()["job_id"]

    posts = _posts(ui, "/documents")
    assert len(posts) == 1
    assert json.loads(posts[0]["post_data"]) == {"document": {"text": DOCS_TEXT, "document_id": "doc-live-1"}, "selector": None}

    ui.expect(ui.el("documents.result.card").locator('[data-role="job-id"]')).to_have_text(job_id)
    ui.expect("documents.jobs.list").to_contain_text(job_id)
    stored = ui.page.evaluate("() => JSON.parse(sessionStorage.getItem('databasise.console.jobs'))")
    assert stored[0]["job_id"] == job_id

    assert _gets(ui, f"/jobs/{job_id}") == []
    ui.el("documents.result.open-job").click()
    ui.expect("documents.jobs.drawer").to_be_visible()
    ui.expect(ui.el("documents.jobs.documents").locator("tbody tr:not([hidden])").first).to_contain_text("doc-live-1")
    assert _job_ids(ui) == ["doc-live-1"]
    assert len(_gets(ui, f"/jobs/{job_id}")) == 1


# ---- Task 2: upload, drawer rules, polls, absent routes ----


@contextlib.contextmanager
def _ui(browser, app, before_goto=None):
    ui = open_live_ui(browser, app, before_goto=before_goto)
    try:
        yield ui
    finally:
        ui.close()


def _settle(ui):
    """One round trip through the page: every request a timer started before this call is in ``ui.requests``."""
    ui.page.evaluate("() => fetch('/openapi.json').then((r) => r.status)")


def _query_of(request):
    return {key: values[0] for key, values in parse_qs(urlparse(request["url"]).query).items()}


def _range(ui):
    return ui.el("documents.jobs.drawer").locator('[data-role="range"]')


def _paste(ui, document_id, text=DOCS_TEXT):
    ui.nav("documents")
    ui.el("documents.paste.text").fill(text)
    ui.el("documents.paste.document-id").fill(document_id)
    with ui.page.expect_response(_is_post("/documents")) as info:
        ui.el("documents.paste.submit").click()
    ui.expect(ui.el("documents.result.card").locator('[data-role="job-id"]')).to_have_text(info.value.json()["job_id"])
    return info.value.json()["job_id"]


def _three_documents(live_app, ui, prefix):
    """Ingests one document through the page and adds two more under the same job, so the job holds three."""
    job_id = _paste(ui, f"{prefix}-1")
    for n in (2, 3):
        live_app.corpus[f"{prefix}-{n}"] = {"track_id": job_id, "status": "processed"}
    return job_id


def test_upload_sends_multipart_and_shows_indeterminate_progress(live_app, live_ui):
    ui = live_ui
    ui.nav("documents")
    ui.el("documents.tabs.upload").click()
    ui.el("documents.upload.file").set_input_files({"name": "note.txt", "mimeType": "text/plain", "buffer": b"an uploaded note"})
    ui.el("documents.upload.document-id").fill("doc-upload-1")
    ui.expect("documents.upload.submit").to_be_enabled()
    # Chromium streams a File part, so Playwright cannot read the body; the page's own fetch call is recorded instead.
    ui.page.evaluate(
        """() => {
            const original = window.fetch;
            window.__uploads = [];
            window.fetch = function (path, init) {
                if (init && init.body instanceof FormData) {
                    window.__uploads.push({ path, fields: Array.from(init.body.keys()), document_id: init.body.get('document_id'), headers: Object.keys(init.headers || {}) });
                }
                return original.apply(this, arguments);
            };
        }"""
    )
    with live_app.hold("ingest") as release:
        with ui.page.expect_request(lambda r: r.method == "POST" and urlparse(r.url).path == "/documents/upload") as sent:
            ui.el("documents.upload.submit").click()
        ui.expect("documents.upload.progress").to_be_visible()
        # Indeterminate: the <progress> carries no value attribute, and no percentage is shown.
        assert ui.page.evaluate("() => document.querySelector('[data-mock-id=\"documents.upload.progress\"] progress').hasAttribute('value')") is False
        ui.expect("documents.upload.progress").to_contain_text("Uploading and processing. A LightRAG ingest waits for the model and can take minutes.")
        assert not re.search(r"\d\s*%", ui.el("documents.upload.progress").inner_text())
        release.set()
    request = sent.value
    assert re.match(r"^multipart/form-data; boundary=", request.headers["content-type"])
    uploads = ui.page.evaluate("() => window.__uploads")
    assert uploads == [{"path": "/documents/upload", "fields": ["file", "document_id"], "document_id": "doc-upload-1", "headers": []}]
    assert len(_posts(ui, "/documents/upload")) == 1
    ui.expect(ui.el("documents.result.card").locator('[data-role="job-id"]')).to_have_text(re.compile(r".+"))
    ui.expect("documents.upload.progress").to_be_hidden()


def test_job_drawer_pages_by_next_offset_without_a_total(live_app, live_ui):
    ui = live_ui
    job_id = _three_documents(live_app, ui, "doc-page")
    ui.el("documents.jobs.open").click()
    ui.el("documents.jobs.page-size").fill("2")
    ui.el("documents.result.open-job").click()
    ui.expect(_range(ui)).to_have_text("Showing 1 to 2")
    ui.expect("documents.jobs.prev").to_be_disabled()
    ui.expect("documents.jobs.next").to_be_enabled()
    assert _query_of(_gets(ui, f"/jobs/{job_id}")[-1]) == {"limit": "2", "offset": "0"}

    ui.el("documents.jobs.next").click()
    ui.expect(_range(ui)).to_have_text("Showing 3 to 3")
    assert _query_of(_gets(ui, f"/jobs/{job_id}")[-1]) == {"limit": "2", "offset": "2"}
    assert " of " not in _range(ui).inner_text()
    assert _job_ids(ui) == ["doc-page-3"]
    ui.expect("documents.jobs.next").to_be_disabled()
    ui.expect("documents.jobs.prev").to_be_enabled()

    ui.el("documents.jobs.prev").click()
    ui.expect(_range(ui)).to_have_text("Showing 1 to 2")
    assert _query_of(_gets(ui, f"/jobs/{job_id}")[-1]) == {"limit": "2", "offset": "0"}


def test_failed_job_load_keeps_the_previous_page(live_app, live_ui):
    ui = live_ui
    job_id = _three_documents(live_app, ui, "doc-keep")
    ui.el("documents.jobs.open").click()
    ui.el("documents.jobs.page-size").fill("2")
    ui.el("documents.result.open-job").click()
    ui.expect(_range(ui)).to_have_text("Showing 1 to 2")
    ui.el("documents.jobs.next").click()
    ui.expect(_range(ui)).to_have_text("Showing 3 to 3")

    ui.el("documents.jobs.job-id").fill("no-such-job")
    ui.el("documents.jobs.load").click()
    banner = ui.el("documents.error.refusal")
    ui.expect(banner).to_contain_text("UnknownJobError")
    ui.expect(banner.locator('[data-role="footer"]')).to_have_text(re.compile(r"^HTTP 404\."))
    # The previous page, its pager state and its job id are back.
    assert _job_ids(ui) == ["doc-keep-3"]
    ui.expect(_range(ui)).to_have_text("Showing 3 to 3")
    ui.expect("documents.jobs.prev").to_be_enabled()
    ui.expect("documents.jobs.next").to_be_disabled()
    ui.expect("documents.jobs.job-id").to_have_value(job_id)
    ui.expect("documents.jobs.documents").to_be_visible()


def test_jobs_poll_runs_only_while_the_drawer_is_open(live_app, browser):
    job_id = live_app.ingest("poll text", "doc-poll-1")["job_id"]
    live_app.corpus["doc-poll-1"]["status"] = "pending"  # not folded into interrupted, and not terminal
    with _ui(browser, live_app, CLOCK) as ui:
        ui.nav("documents")
        ui.el("documents.jobs.open").click()
        ui.el("documents.jobs.job-id").fill(job_id)
        ui.el("documents.jobs.load").click()
        ui.expect(ui.el("documents.jobs.documents").locator("tbody tr:not([hidden])").first).to_contain_text("doc-poll-1")
        ui.expect("documents.live.jobs-polled").to_have_text("")
        ui.el("documents.jobs.poll").check()
        ui.expect("documents.live.jobs-polled").to_have_text("Refreshing every 30 seconds.")
        loads = len(_gets(ui, f"/jobs/{job_id}"))
        ui.page.clock.fast_forward(31000)
        _settle(ui)
        assert len(_gets(ui, f"/jobs/{job_id}")) == loads + 1

        # Closing the drawer stops the poll, unchecks the box and does not reopen the drawer.
        ui.el("documents.jobs.close").click()
        ui.expect("documents.jobs.poll").not_to_be_checked()
        ui.expect("documents.live.jobs-polled").to_have_text("")
        ui.page.clock.fast_forward(62000)
        _settle(ui)
        assert len(_gets(ui, f"/jobs/{job_id}")) == loads + 1
        ui.expect("documents.jobs.drawer").to_be_hidden()

        # Leaving the screen does the same, and the drawer is not reopened on return.
        ui.el("documents.jobs.open").click()
        ui.el("documents.jobs.poll").check()
        ui.expect("documents.live.jobs-polled").to_have_text("Refreshing every 30 seconds.")
        ui.nav("corpus")
        ui.nav("documents")
        ui.expect("documents.jobs.poll").not_to_be_checked()
        ui.page.clock.fast_forward(62000)
        _settle(ui)
        assert len(_gets(ui, f"/jobs/{job_id}")) == loads + 1

        # A job whose documents all have a final status stops the poll by itself.
        live_app.corpus["doc-poll-1"]["status"] = "processed"
        ui.el("documents.jobs.load").click()
        ui.expect(ui.el("documents.jobs.documents").locator('tbody tr:not([hidden]) [data-role="status"]').first).to_contain_text("processed")
        ui.el("documents.jobs.poll").check()
        ui.expect("documents.live.jobs-polled").to_have_text("Stopped: every document has a final status.")
        loads = len(_gets(ui, f"/jobs/{job_id}"))
        ui.page.clock.fast_forward(62000)
        _settle(ui)
        assert len(_gets(ui, f"/jobs/{job_id}")) == loads


def test_absent_job_routes_are_disabled(live_ui):
    ui = live_ui
    ui.nav("documents")
    ui.el("documents.jobs.open").click()
    ui.expect("documents.jobs.all").to_be_disabled()
    ui.expect("documents.pipeline.cancel").to_be_disabled()
    for line in ("Needs GET /jobs.", "Needs POST /jobs/{job_id}/cancel.", "Needs GET /pipeline."):
        ui.expect(ui.page.get_by_text(line, exact=True)).to_be_visible()


# ---- Task 3: the write gate, the delete flow, the corpus refresh, HippoRAG query-after-ingest ----

CAPS = ["reads_graph", "reads_kv"]
WRITING = "A document write is in progress. Queries are unavailable until the ingest or delete finishes."
ANOTHER = "Another write is in progress."
SENDING = "Sending. A request that has been sent cannot be cancelled."
SPLIT_NOTICE = (
    "LightRAG documents ingested here appear in Corpus & Health and in Jobs. "
    "They are not visible in Query & Compare or Evidence & Trace."
)


@pytest.fixture
def corpus_doc(live_app):
    """Resets the shared fake before every test: one processed document, ``doc-del-1``."""
    live_app.corpus.clear()
    live_app.corpus["doc-del-1"] = {"track_id": None, "status": "processed"}
    return live_app.corpus


@pytest.fixture(scope="module")
def hippo_app(tmp_path_factory, corpus_fake):
    """A store with no other HippoRAG document, so a query can only return what the test ingested."""
    live = start_live_app(tmp_path_factory.mktemp("store-hippo"))
    live.corpus = corpus_fake
    yield live
    live.stop()


def _deletes(ui):
    return [r for r in ui.requests if r["method"] == "DELETE"]


def _ask_delete(ui, document_id):
    ui.nav("documents")
    ui.el("documents.delete.document-id").fill(document_id)
    ui.el("documents.delete.submit").click()
    ui.expect("shell.dialog.delete").to_be_visible()


def test_query_run_is_disabled_while_an_ingest_is_in_flight(live_app, live_ui):
    ui = live_ui
    ui.nav("documents")
    ui.el("documents.paste.text").fill("Text that keeps the ingest in flight.")
    with live_app.hold("ingest") as release:
        ui.el("documents.paste.submit").click()
        ui.nav("query")
        ui.expect("query.run.submit").to_be_disabled()
        ui.expect("query.run.submit").to_have_attribute("aria-disabled", "true")
        ui.expect("query.run.message").to_be_visible()
        ui.expect("query.run.message").to_have_text(WRITING)
        ui.el("query.mode.compare").click()
        ui.expect("query.run.submit").to_be_disabled()
        ui.expect("query.run.submit").to_have_attribute("aria-disabled", "true")
        ui.expect("query.run.message").to_have_text(WRITING)
        release.set()
    ui.expect("query.run.submit").to_be_enabled()
    ui.expect("query.run.submit").not_to_have_attribute("aria-disabled", "true")
    ui.expect("query.run.message").to_be_hidden()
    ui.el("query.mode.query").click()
    ui.expect("query.run.submit").to_be_enabled()
    ui.nav("documents")
    ui.expect("documents.result.card").to_be_visible()


def test_second_write_is_blocked_while_one_is_in_flight(live_app, live_ui):
    ui = live_ui
    ui.nav("documents")
    ui.el("documents.paste.text").fill("Text that keeps the ingest in flight.")
    ui.el("documents.delete.document-id").fill("doc-other")
    ui.el("documents.tabs.upload").click()
    ui.el("documents.upload.file").set_input_files({"name": "note.txt", "mimeType": "text/plain", "buffer": b"an uploaded note"})
    ui.expect("documents.upload.submit").to_be_enabled()
    ui.expect("documents.delete.submit").to_be_enabled()
    ui.el("documents.tabs.paste").click()
    with live_app.hold("ingest") as release:
        ui.el("documents.paste.submit").click()
        ui.expect("documents.paste.submit").to_be_disabled()
        ui.expect("documents.upload.submit").to_be_disabled()
        ui.expect("documents.delete.submit").to_be_disabled()
        ui.expect(ui.el("documents.ingest.panel").get_by_text(ANOTHER)).to_be_visible()
        ui.expect(ui.el("documents.delete.panel").get_by_text(ANOTHER)).to_be_visible()
        release.set()
    ui.expect("documents.paste.submit").to_be_enabled()
    ui.expect("documents.upload.submit").to_be_enabled()
    ui.expect("documents.delete.submit").to_be_enabled()
    ui.expect(ui.el("documents.ingest.panel").get_by_text(ANOTHER)).to_be_hidden()


def test_dialog_dismiss_sends_nothing(live_app, live_ui):
    ui = live_ui
    _ask_delete(ui, "doc-keep-me")
    ui.el("shell.dialog.delete-cancel").click()
    ui.expect("shell.dialog.delete").to_be_hidden()
    _ask_delete(ui, "doc-keep-me")
    ui.page.keyboard.press("Escape")
    ui.expect("shell.dialog.delete").to_be_hidden()
    _settle(ui)
    assert _deletes(ui) == []
    ui.expect("documents.delete.outcome").to_be_hidden()


def test_dialog_stays_open_while_the_delete_is_in_flight(corpus_doc, live_app, live_ui):
    ui = live_ui
    _ask_delete(ui, "doc-del-1")
    dialog = ui.el("shell.dialog.delete")
    with live_app.hold("delete_document") as release:
        ui.el("shell.dialog.delete-confirm").click()
        ui.expect("shell.dialog.delete-confirm").to_be_disabled()
        ui.expect("shell.dialog.delete-cancel").to_be_disabled()
        ui.expect(dialog.get_by_text(SENDING)).to_be_visible()
        # Escape is ignored; a second press (which Chromium may let through) must not close the dialog either.
        ui.page.keyboard.press("Escape")
        ui.page.keyboard.press("Escape")
        ui.expect(dialog).to_be_visible()
        assert len(_deletes(ui)) == 1
        release.set()
    ui.expect(dialog).to_be_hidden()
    ui.expect(ui.el("documents.delete.outcome")).to_contain_text("success")
    assert len(_deletes(ui)) == 1
    assert "doc-del-1" not in corpus_doc


def test_confirmed_delete_refreshes_corpus_and_counts_and_the_row_is_gone(corpus_doc, live_ui):
    ui = live_ui
    ui.nav("corpus")
    ui.expect(ui.el("corpus.table.documents").locator("tbody tr:not([hidden])")).to_have_count(1)
    _ask_delete(ui, "doc-del-1")
    with ui.page.expect_response(lambda r: r.request.method == "GET" and urlparse(r.url).path == "/corpus/counts"):
        ui.el("shell.dialog.delete-confirm").click()
    ui.expect(ui.el("documents.delete.outcome")).to_contain_text("success")
    first = next(i for i, r in enumerate(ui.requests) if r["method"] == "DELETE")
    after = ui.requests[first + 1 :]
    assert any(r["method"] == "GET" and r["path"] == "/corpus" for r in after)
    assert any(r["method"] == "GET" and r["path"] == "/corpus/counts" for r in after)

    ui.nav("corpus")
    ui.expect(ui.el("corpus.table.documents").locator("tbody tr:not([hidden])")).to_have_count(0)
    ui.expect(ui.el("corpus.kpi.total").locator('[data-role="count"]')).to_have_text("0")


def test_delete_with_a_hipporag_selector_sends_the_selector(seeded, live_ui):
    ui = live_ui
    ui.nav("documents")
    ui.el("documents.selector.kind-capability").check()
    ui.el("documents.selector.capability").select_option(CAPS)
    ui.el("documents.delete.document-id").fill("seed-hipporag")
    ui.el("documents.delete.submit").click()
    ui.expect("shell.dialog.delete").to_be_visible()
    ui.el("shell.dialog.delete-confirm").click()
    ui.expect(ui.el("documents.delete.outcome")).to_contain_text("success")
    sent = _deletes(ui)
    assert [r["path"] for r in sent] == ["/documents/seed-hipporag"]
    body = json.loads(sent[0]["post_data"])
    assert list(body) == ["selector"] and sorted(body["selector"]["capability"]) == CAPS


def test_alias_delete_dialog_names_no_store_type(live_ui):
    """R18-05: an alias's arm is known only to the server, so the dialog must not claim a LightRAG or HippoRAG consequence."""
    ui = live_ui
    tail = ui.el("shell.dialog.delete").locator('[data-role="tail"]')
    _ask_delete(ui, "doc-keep-me")
    ui.expect(tail).to_contain_text("v1 corpus")
    ui.el("shell.dialog.delete-cancel").click()

    ui.el("documents.selector.kind-alias").check()
    ui.el("documents.selector.alias").fill("op-alias")
    ui.el("documents.delete.submit").click()
    ui.expect("shell.dialog.delete").to_be_visible()
    text = ui.el("shell.dialog.delete").inner_text()
    assert "LightRAG" not in text and "HippoRAG" not in text and "v1 corpus" not in text, text
    ui.el("shell.dialog.delete-cancel").click()
    assert _deletes(ui) == []


def test_query_after_hipporag_ingest_returns_that_documents_evidence(hippo_app, browser):
    assert hippo_app.start_error is None, hippo_app.start_error
    word = "zanzibarquartz"
    with _ui(browser, hippo_app) as ui:
        ui.nav("documents")
        ui.el("documents.selector.kind-capability").check()
        ui.el("documents.selector.capability").select_option(CAPS)
        ui.el("documents.paste.text").fill(f"The {word} expedition mapped the coast of the island.")
        ui.el("documents.paste.document-id").fill("doc-hippo-q")
        ui.el("documents.paste.submit").click()
        ui.expect("documents.result.card").to_be_visible()

        ui.nav("query")
        ui.el("query.text.input").fill(word)
        ui.el("query.selector.kind-capability").check()
        ui.el("query.selector.capability").select_option(CAPS)
        ui.el("query.run.stream").set_checked(False)
        ui.el("query.run.submit").click()
        ui.expect("query.state.success").to_be_visible()
        ui.el("query.evidence.open-1").click()
        ui.expect("evidence.state.resolved").to_be_visible()
        ui.expect("evidence.inspector.content").to_contain_text(word)


def test_store_split_notice_stays_visible(live_ui):
    ui = live_ui
    ui.nav("documents")
    ui.expect("documents.notice.store-split").to_be_visible()
    ui.expect("documents.notice.store-split").to_have_text(SPLIT_NOTICE)
