"""LIVE-03 (D-12, GUI-06): every real server answer renders through the four error shapes, with the real status.

Each screen plan appends one case set to this module; 18-04 adds the Query cases and 18-05 the Compare cases
(a duplicate-key refusal, a validation list that marks the offending selector row, a 500), and 18-06 the
Evidence & Trace cases (unknown trace, unresolvable ref, a validation 422 on the lookup ref, a 500). The row test is
``test_query_500_renders_the_generic_view``: a real 500 (``LiveApp.fail("query")``) shows the generic view,
and the server-log region follows the launch mode. ``live_app`` has no log file, so GET /log is absent;
``log_app`` is started with ``--log-file``, so the 5xx view loads ``GET /log?limit=200``.

Named deviation: LIVE-03's test text expects a two-member selector to render "a field error on the selector".
Since SEAM-02 the server answers it with the typed refusal ``MultiMemberSelectorError``, not a validation 422,
and neither UI-SPEC defines a field highlight for a refusal. So the typed banner is the contract here
(``test_query_multi_member_selector_renders_the_typed_refusal``), and the field error on the selector is proven
by a real validation 422 (``test_query_validation_marks_the_selector_field``).
"""

from __future__ import annotations

import contextlib
import json
import re
from urllib.parse import urlparse

import pytest

from databasise.tests.gui_live.conftest import HIPPORAG, open_live_ui, start_live_app
from databasise.tests.seam.test_hipporag_write_path import _DOCUMENT_TEXT

CAPS = ["reads_graph", "reads_kv"]
SELECTOR_FIELD = '[data-mock-id="screen-query"] [data-field-loc="body.selector"]'


@pytest.fixture(scope="module")
def log_app(tmp_path_factory, corpus_fake):
    live = start_live_app(tmp_path_factory.mktemp("store-log"), log_file=tmp_path_factory.mktemp("log") / "server.log")
    if live.start_error is None:
        live.ingest(_DOCUMENT_TEXT, "seed-hipporag-log", HIPPORAG)
    live.corpus = corpus_fake
    yield live
    live.stop()


@contextlib.contextmanager
def _ui(browser, app, before_goto=None):
    ui = open_live_ui(browser, app, before_goto=before_goto)
    try:
        yield ui
    finally:
        ui.close()


def _run(ui, *, alias=None):
    ui.el("query.text.input").fill("Ed Wood")
    if alias is None:
        ui.el("query.selector.kind-capability").check()
        ui.el("query.selector.capability").select_option(CAPS)
    else:
        ui.el("query.selector.alias").fill(alias)
    ui.el("query.run.submit").click()


def _rewrite_selector(selector):
    """A route handler that sends the page's own request with another selector, so the real server answers it."""

    def handler(route):
        body = route.request.post_data_json
        body["selector"] = selector
        route.continue_(post_data=json.dumps(body))

    return lambda page: page.route("**/query", handler)


def test_query_refusal_renders_the_typed_banner_with_the_real_status(seeded, live_ui):
    ui = live_ui
    _run(ui, alias="no-such-alias")
    banner = ui.el("query.error.refusal")
    ui.expect(banner).to_contain_text("UnsatisfiableSelectorError")
    ui.expect(banner.locator('[data-role="footer"]')).to_have_text(re.compile(r"^HTTP 422\."))


def test_query_multi_member_selector_renders_the_typed_refusal(seeded, browser):
    with _ui(browser, seeded, _rewrite_selector({"alias": "a", "capability": ["reads_kv"]})) as ui:
        _run(ui)
        banner = ui.el("query.error.refusal")
        ui.expect(banner).to_contain_text("MultiMemberSelectorError")
        ui.expect(banner.locator('[data-role="footer"]')).to_have_text(re.compile(r"^HTTP 422\."))
        ui.expect("query.error.validation").to_be_hidden()
        # A refusal marks no field; only a validation 422 does.
        assert ui.page.locator(SELECTOR_FIELD).get_attribute("aria-invalid") is None


def test_query_refusal_state_prints_the_real_status(seeded, browser):
    refusal = {"refusal_type": "StoreBusyError", "message": "store busy", "store_kind": "graph"}

    def handler(route):
        route.fulfill(status=409, content_type="application/json", body=json.dumps(refusal))

    with _ui(browser, seeded, lambda page: page.route("**/query", handler)) as ui:
        _run(ui)
        ui.expect(ui.el("query.error.refusal").locator('[data-role="footer"]')).to_have_text(re.compile(r"^HTTP 409\."))
        view = ui.el("query.state.refusal-422")
        ui.expect(view).to_contain_text("HTTP 409")
        ui.expect(view).not_to_contain_text("HTTP 422")


def test_query_validation_marks_the_selector_field(seeded, browser):
    with _ui(browser, seeded, _rewrite_selector(5)) as ui:
        _run(ui)
        ui.expect("query.error.validation").to_be_visible()
        field = ui.page.locator(SELECTOR_FIELD)
        ui.expect(field).to_have_attribute("aria-invalid", "true")
        ui.expect("query.selector.error").to_have_text(re.compile(r".+"))


def test_query_500_renders_the_generic_view(seeded, browser):
    with seeded.fail("query"), _ui(browser, seeded) as ui:
        _run(ui)
        generic = ui.el("query.error.generic")
        ui.expect(generic).to_contain_text("The server returned HTTP 500")
        region = generic.locator('[data-needs-backend="GET /log"]')
        ui.expect(region).to_contain_text("Needs GET /log.")
        ui.expect(region.locator(".badge-op")).to_be_visible()
        assert ui.count("GET", "/log") == 0


def test_query_500_loads_the_log_tail_when_mounted(log_app, browser):
    log_app.log_file.write_text("first log line\nsecond log line\n", encoding="utf-8")
    with log_app.fail("query"), _ui(browser, log_app) as ui:
        _run(ui)
        generic = ui.el("query.error.generic")
        ui.expect(generic).to_contain_text("The server returned HTTP 500")
        ui.expect(generic.locator('[data-role="log-tail"]')).to_contain_text("second log line")
        ui.expect(generic.locator('[data-role="log-caption"]')).to_have_text("Last 200 log lines. Lines are redacted.")
        ui.expect(generic).not_to_contain_text("Needs GET /log.")
        loads = [r for r in ui.requests if r["method"] == "GET" and r["path"] == "/log"]
        assert len(loads) == 1
        assert loads[0]["url"].endswith("/log?limit=200")


def _run_compare(ui):
    """Compare mode with a capability row and a Default row, then Run compare."""
    ui.el("query.mode.compare").click()
    ui.el("query.text.input").fill("Ed Wood")
    ui.el("query.row1.kind").select_option("capability")
    ui.el("query.row1.capability").select_option(CAPS)
    ui.el("query.compare.add").click()
    ui.el("query.run.submit").click()


def _rewrite_selectors(selectors):
    """Sends the page's own compare request with other selectors, so the real server answers it."""

    def handler(route):
        body = route.request.post_data_json
        body["selectors"] = selectors
        route.continue_(post_data=json.dumps(body))

    return lambda page: page.route("**/compare", handler)


def test_compare_duplicate_key_refusal_renders_the_typed_banner(seeded, browser):
    with _ui(browser, seeded, _rewrite_selectors([{}, {}])) as ui:
        _run_compare(ui)
        banner = ui.el("query.error.refusal")
        ui.expect(banner).to_contain_text("DuplicateComparisonKeyError")
        ui.expect(banner.locator('[data-role="footer"]')).to_have_text(re.compile(r"^HTTP 422\."))
        ui.expect("query.compare.columns").to_be_hidden()
        ui.expect("query.error.validation").to_be_hidden()


def test_compare_validation_renders_the_field_list(seeded, browser):
    with _ui(browser, seeded, _rewrite_selectors([5, {}])) as ui:
        _run_compare(ui)
        ui.expect("query.error.validation").to_contain_text("body.selectors.0")
        # The row the server named is marked and carries the server's message; the other row is not.
        ui.expect("query.row1.kind").to_have_attribute("aria-invalid", "true")
        ui.expect("query.row1.error").to_be_visible()
        ui.expect("query.row1.error").to_have_text(re.compile(r".+"))
        assert ui.el("query.row2.kind").get_attribute("aria-invalid") is None
        ui.expect("query.row2.error").to_be_hidden()
        ui.expect("query.compare.columns").to_be_hidden()


def test_compare_500_renders_the_generic_view(seeded, browser):
    with seeded.fail("compare"), _ui(browser, seeded) as ui:
        _run_compare(ui)
        ui.expect("query.error.generic").to_contain_text("The server returned HTTP 500")
        ui.expect("query.compare.columns").to_be_hidden()
        ui.expect("query.run.submit").to_be_enabled()


# ---- 18-06: Evidence & Trace ----

REF_FIELD = '[data-mock-id="screen-evidence"] [data-field-loc="body.ref"]'


def _lookup(ui, ref="nope", namespace="hipporag-chunks"):
    ui.nav("evidence")
    ui.el("evidence.lookup.toggle").click()
    ui.el("evidence.lookup.ref").fill(ref)
    ui.el("evidence.lookup.namespace").select_option(namespace)
    ui.el("evidence.lookup.submit").click()


def test_unknown_trace_reference_renders_its_typed_banner(seeded, live_ui):
    ui = live_ui
    ui.nav("evidence")
    ui.el("evidence.tabs.trace").click()
    ui.el("evidence.trace.reference").fill("no-such-trace")
    ui.el("evidence.trace.load").click()
    banner = ui.el("evidence.error.refusal")
    ui.expect(banner).to_contain_text("UnknownTraceReferenceError")
    ui.expect(banner.locator('[data-role="footer"]')).to_have_text(re.compile(r"^HTTP 404\."))


def test_unresolvable_ref_renders_record_no_longer_present(seeded, live_ui):
    ui = live_ui
    _lookup(ui)
    ui.expect("evidence.state.refusal").to_contain_text("record no longer present")
    ui.expect(ui.el("evidence.error.refusal").locator('[data-role="footer"]')).to_have_text(re.compile(r"^HTTP 404\."))


def test_evidence_validation_marks_the_lookup_ref(seeded, browser):
    def handler(route):
        body = route.request.post_data_json
        del body["ref"]
        route.continue_(post_data=json.dumps(body))

    with _ui(browser, seeded, lambda page: page.route("**/evidence/resolve", handler)) as ui:
        _lookup(ui)
        ui.expect("evidence.error.validation").to_be_visible()
        ui.expect(ui.page.locator(REF_FIELD)).to_have_attribute("aria-invalid", "true")


def test_evidence_500_renders_the_generic_view(seeded, browser):
    with seeded.fail("resolve_evidence"), _ui(browser, seeded) as ui:
        _lookup(ui)
        ui.expect("evidence.error.generic").to_contain_text("The server returned HTTP 500")


def test_query_unreachable_renders_generic_and_header_unreachable(seeded, browser):
    with _ui(browser, seeded, lambda page: page.route("**/query", lambda route: route.abort())) as ui:
        _run(ui)
        generic = ui.el("query.error.generic")
        ui.expect(generic).to_contain_text(
            "Server unreachable. No response from the server. Check that databasise-rest is running at this address, then try again."
        )
        ui.expect(generic.locator('[data-role="body"]')).to_be_hidden()
        ui.expect("shell.health.status").to_have_attribute("data-state", "error")


# ---- 18-07: Corpus & Health ----

PAGE_SIZE_FIELD = '[data-mock-id="screen-corpus"] [data-field-loc="query.limit"]'


def _rewrite_corpus_query(query):
    """Sends the page's own GET /corpus with another query string, so the real server answers it."""

    def handler(route):
        route.continue_(url=route.request.url.split("?")[0] + "?" + query)

    return lambda page: page.route(lambda url: urlparse(url).path == "/corpus", handler)


def test_corpus_page_size_101_renders_page_size_exceeded(live_app, browser):
    with _ui(browser, live_app, _rewrite_corpus_query("limit=101&offset=0")) as ui:
        ui.nav("corpus")
        banner = ui.el("corpus.error.refusal")
        ui.expect(banner).to_contain_text("PageSizeExceededError")
        ui.expect(banner.locator('[data-role="attrs"]')).to_contain_text(re.compile(r"requested\s*101\s*limit\s*100"))
        ui.expect(banner.locator('[data-role="footer"]')).to_have_text(re.compile(r"^HTTP 422\."))


def test_corpus_validation_marks_the_page_size(live_app, browser):
    with _ui(browser, live_app, _rewrite_corpus_query("limit=abc&offset=0")) as ui:
        ui.nav("corpus")
        ui.expect("corpus.error.validation").to_be_visible()
        ui.expect(ui.page.locator(PAGE_SIZE_FIELD)).to_have_attribute("aria-invalid", "true")


def test_corpus_500_renders_the_generic_view(live_app, browser):
    with live_app.fail("corpus_status"), _ui(browser, live_app) as ui:
        ui.nav("corpus")
        ui.expect("corpus.error.generic").to_contain_text("The server returned HTTP 500")


# ---- 18-08: Documents & Jobs ----

PASTE_FIELD = '[data-mock-id="screen-documents"] [data-field-loc="body.document.text"]'


def _paste_submit(ui):
    ui.nav("documents")
    ui.el("documents.paste.text").fill("Text for the documents error cases.")
    ui.el("documents.paste.submit").click()


def test_documents_unknown_job_renders_its_typed_banner(live_app, live_ui):
    ui = live_ui
    ui.nav("documents")
    ui.el("documents.jobs.open").click()
    ui.el("documents.jobs.job-id").fill("no-such-job")
    ui.el("documents.jobs.load").click()
    banner = ui.el("documents.error.refusal")
    ui.expect(banner).to_contain_text("UnknownJobError")
    ui.expect(banner.locator('[data-role="footer"]')).to_have_text(re.compile(r"^HTTP 404\."))


def test_documents_validation_marks_the_paste_text(live_app, browser):
    def handler(route):
        body = route.request.post_data_json
        body["document"]["text"] = ["a"]
        route.continue_(post_data=json.dumps(body))

    with _ui(browser, live_app, lambda page: page.route("**/documents", handler)) as ui:
        _paste_submit(ui)
        ui.expect("documents.error.validation").to_be_visible()
        ui.expect(ui.page.locator(PASTE_FIELD)).to_have_attribute("aria-invalid", "true")


def test_documents_500_renders_the_generic_view(live_app, browser):
    with live_app.fail("ingest"), _ui(browser, live_app) as ui:
        _paste_submit(ui)
        ui.expect("documents.error.generic").to_contain_text("The server returned HTTP 500")


# ---- 18-09: Ledger ----

PROMOTE_ALIAS_FIELD = '[data-mock-id="screen-ledger"] [data-field-loc="body.alias"]'


def _promote_form(ui, alias="err-test"):
    """Runs a query in the page, then fills the promote form with it and presses Promote alias (the dialog opens)."""
    ui.el("query.text.input").fill("Ed Wood")
    ui.el("query.selector.kind-capability").check()
    ui.el("query.selector.capability").select_option(CAPS)
    ui.el("query.run.submit").click()
    ui.expect("query.state.success").to_be_visible()
    ui.nav("ledger")
    ui.el("ledger.promote.trace-1").check()
    ui.el("ledger.promote.alias").fill(alias)
    ui.el("ledger.promote.origin-human").check()
    ui.el("ledger.promote.submit").click()
    ui.expect("shell.dialog.promote").to_be_visible()


def _rewrite_body(path, change):
    """A route handler that sends the page's own request with ``change(body)`` applied, so the real server answers it."""

    def handler(route):
        body = route.request.post_data_json
        change(body)
        route.continue_(post_data=json.dumps(body))

    return lambda page: page.route(f"**/{path}", handler)


def test_ledger_active_retirement_refusal_links_to_the_head_row(seeded, browser):
    first = seeded.query("Ed Wood", HIPPORAG)["trace_token"]
    second = seeded.query("Bela Lugosi", HIPPORAG)["trace_token"]
    old = seeded.promote("ret", [first])["version"]
    head = seeded.promote("ret", [second])["version"]
    # The page asks to retire the old version; the rewrite names the active head instead.
    with _ui(browser, seeded, _rewrite_body("retire", lambda body: body.update(version=head))) as ui:
        ui.nav("ledger")
        ui.el("ledger.timeline.alias").select_option("ret")
        ui.expect(ui.el("ledger.timeline.table").locator("tbody tr:not([hidden])")).to_have_count(2)
        ui.el("ledger.timeline.retire-1").click()
        ui.el("shell.dialog.retire-version").fill(old)
        ui.el("shell.dialog.retire-traces").select_option(first)
        ui.el("shell.dialog.retire-origin-human").check()
        ui.el("shell.dialog.retire-confirm").click()
        banner = ui.el("ledger.error.refusal")
        ui.expect(banner).to_contain_text("ActiveGenerationRetirementError")
        ui.expect(banner.locator('[data-role="footer"]')).to_have_text(re.compile(r"^HTTP 422\."))
        ui.el("ledger.error.roll-back-first").click()
        assert ui.page.evaluate("() => document.activeElement.getAttribute('data-status')") == "active"
        assert ui.page.evaluate("() => document.activeElement.querySelector('[data-role=\"minted\"]').textContent") == head


def test_ledger_validation_marks_the_promote_alias(seeded, browser):
    with _ui(browser, seeded, _rewrite_body("promote", lambda body: body.update(alias=5))) as ui:
        _promote_form(ui)
        ui.el("shell.dialog.promote-confirm").click()
        ui.expect("ledger.error.validation").to_be_visible()
        ui.expect(ui.page.locator(PROMOTE_ALIAS_FIELD)).to_have_attribute("aria-invalid", "true")


def test_ledger_500_renders_the_generic_view(seeded, browser):
    with seeded.fail("promote"), _ui(browser, seeded) as ui:
        _promote_form(ui)
        ui.el("shell.dialog.promote-confirm").click()
        ui.expect("ledger.error.generic").to_contain_text("The server returned HTTP 500")
        ui.expect("shell.dialog.promote").to_be_hidden()


# ---- 18-10: Graph/vector browser ----

GRAPH_LIMIT_FIELD = '[data-mock-id="screen-graph"] [data-field-loc="body.limit"]'


def _pick_graph(ui):
    ui.nav("graph")
    ui.el("graph.selector.kind-capability").check()
    ui.el("graph.selector.capability").select_option(CAPS)


def test_graph_validation_marks_the_page_size(seeded, browser):
    with _ui(browser, seeded, _rewrite_body("graph/nodes", lambda body: body.update(limit="x"))) as ui:
        _pick_graph(ui)
        ui.expect("graph.error.validation").to_be_visible()
        ui.expect(ui.page.locator(GRAPH_LIMIT_FIELD)).to_have_attribute("aria-invalid", "true")


def test_graph_500_renders_the_generic_view(seeded, browser):
    with seeded.fail("graph_nodes"), _ui(browser, seeded) as ui:
        _pick_graph(ui)
        ui.expect("graph.error.generic").to_contain_text("The server returned HTTP 500")
