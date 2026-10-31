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

import json
from urllib.parse import urlparse

DOCS_TEXT = "Live paste ingest text for the documents screen."


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
