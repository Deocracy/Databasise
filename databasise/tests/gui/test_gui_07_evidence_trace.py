"""17-05 (GUI-07; D-04): Evidence & Trace screen of the operator console mockup.

Wave 0: written before the Evidence & Trace markup exists (17-08 builds it); until then each node fails
on a missing ``query.*`` or ``evidence.*`` id or an unregistered ``window.__mock`` screen hook. They pin
the 17-UI-SPEC.md ids and verbatim strings. The Debug view is a ``<template>`` clone, so the identity
panel and the node table are ABSENT from the DOM (count 0) until the toggle is on. ``stop_reason`` is
labelled ``operator diagnostics``; ``sentinel:`` values print ``not yet recorded``. Hooks used:
``setState('evidence', idle|loading|resolved|refusal|trace-loading)`` and ``loadFixture('evidence', F)``
for ``e-lightrag-chunk``, ``e-hipporag-chunk``, ``t-clean`` and ``t-partial-debug``. Later plans do not
edit this file."""

from __future__ import annotations

import re

TEXT = "When does the supplier contract renew?"
TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{43}$")


def _query_success(ui) -> None:
    ui.show("query")
    ui.el("query.text.input").fill(TEXT)
    ui.el("query.run.submit").click()
    ui.expect("query.state.success").to_be_visible()


def _open_first_evidence_row(ui) -> None:
    _query_success(ui)
    ui.el("query.evidence.open-1").click()
    ui.expect("screen-evidence").to_be_visible()


def _debug_views(ui) -> tuple[int, int]:
    return ui.el("evidence.trace.nodes").count(), ui.el("evidence.trace.identity").count()


def test_evidence_row_opens_the_inspector(ui):
    _open_first_evidence_row(ui)
    ui.expect("evidence.tabs.evidence").to_have_attribute("aria-selected", "true")
    ui.expect("evidence.state.resolved").to_be_visible()

    header = ui.el("evidence.inspector.header")
    for part in ("c-7f3a91", "chunks", "text_chunk"):
        ui.expect(header).to_contain_text(part)
    ui.expect("evidence.inspector.score").to_contain_text("0.8731")
    ui.expect("evidence.inspector.content").to_contain_text("supplier contract")
    ui.expect("evidence.inspector.kv").to_contain_text("full_doc_id")
    ui.expect("evidence.inspector.kv").to_contain_text("file_path")
    ui.expect("evidence.inspector.document-id").to_be_hidden()


def test_manual_lookup_namespace_has_two_options(ui):
    ui.show("evidence")
    ui.el("evidence.lookup.toggle").click()
    ui.expect(ui.el("evidence.lookup.namespace").locator("option")).to_have_text(
        ["chunks", "hipporag-chunks"]
    )
    ui.expect("evidence.lookup.kind").to_be_disabled()
    ui.expect("evidence.lookup.kind").to_have_value("text_chunk")

    ui.el("evidence.lookup.namespace").select_option(label="hipporag-chunks")
    ui.el("evidence.lookup.ref").fill("chunk:7f3a91")
    ui.el("evidence.lookup.submit").click()
    ui.expect("evidence.inspector.document-id").to_be_visible()
    ui.expect("evidence.inspector.ordinal").to_be_visible()


def test_identity_panel_and_node_table_exist_only_with_the_toggle(ui):
    ui.show("evidence")
    ui.load("evidence", "t-partial-debug")
    ui.expect("evidence.trace.summary").to_be_visible()
    ui.expect("evidence.trace.status").to_contain_text("partial")
    assert _debug_views(ui) == (0, 0)

    ui.el("evidence.trace.debug").check()
    ui.expect("evidence.trace.nodes").to_have_count(1)
    ui.expect("evidence.trace.identity").to_have_count(1)
    ui.expect("evidence.trace.nodes").to_be_visible()
    ui.expect("evidence.trace.identity").to_be_visible()
    nodes = ui.el("evidence.trace.nodes")
    flagged = nodes.locator('tr[data-row-state="failed"], tr[data-row-state="halted"]')
    ui.expect(flagged.first).to_be_visible()
    ui.expect(nodes).to_contain_text("placeholder")
    ui.expect("evidence.trace.sums").to_be_visible()
    for copy in ("run-id", "wiring-id", "hash", "arm-id"):
        ui.expect(f"evidence.trace.copy-{copy}").to_be_visible()
    ui.expect(ui.page.get_by_text("Do not paste this hash into a selector").first).to_be_visible()

    ui.el("evidence.trace.debug").uncheck()
    ui.expect("evidence.trace.nodes").to_have_count(0)
    ui.expect("evidence.trace.identity").to_have_count(0)


def test_sentinel_values_read_not_yet_recorded(ui):
    ui.show("evidence")
    ui.load("evidence", "t-clean")
    for field in ("bundle-ref", "snapshot-hash"):
        ui.expect(f"evidence.trace.{field}").to_contain_text("not yet recorded")
        ui.expect(f"evidence.trace.{field}").to_have_attribute("title", re.compile(r"^sentinel:"))
    ui.expect("evidence.trace.summary").to_contain_text("operator diagnostics")
    ui.expect("evidence.trace.status").to_contain_text("clean")


def test_unknown_trace_highlights_the_reference(ui):
    ui.show("evidence")
    ui.el("evidence.tabs.trace").click()
    ui.inject(
        "evidence",
        404,
        {
            "refusal_type": "UnknownTraceReferenceError",
            "message": "unknown trace reference",
            "trace_reference": "tok-missing",
        },
    )
    ui.expect("evidence.error.refusal").to_be_visible()
    ui.expect(ui.el("evidence.error.refusal").locator("mark")).to_have_text("tok-missing")


def test_gui_07_evidence_and_trace_inspectors(ui):
    # Evidence row 1 from the query result: readable content and the key/value table.
    _open_first_evidence_row(ui)
    ui.expect("evidence.state.resolved").to_be_visible()
    ui.expect("evidence.inspector.content").to_contain_text("supplier contract")
    ui.expect("evidence.inspector.kv").to_contain_text("full_doc_id")
    ui.expect("evidence.inspector.kv").to_contain_text("file_path")

    # Manual lookup: two-option namespace select, hipporag chips.
    ui.el("evidence.lookup.toggle").click()
    ui.expect(ui.el("evidence.lookup.namespace").locator("option")).to_have_text(
        ["chunks", "hipporag-chunks"]
    )
    ui.el("evidence.lookup.namespace").select_option(label="hipporag-chunks")
    ui.el("evidence.lookup.ref").fill("chunk:7f3a91")
    ui.el("evidence.lookup.submit").click()
    ui.expect("evidence.inspector.document-id").to_be_visible()
    ui.expect("evidence.inspector.ordinal").to_be_visible()

    # Open trace from a fresh success result: the reference holds that result's token.
    _query_success(ui)
    ui.el("query.result.trace-link").click()
    ui.expect("screen-evidence").to_be_visible()
    ui.expect("evidence.tabs.trace").to_have_attribute("aria-selected", "true")
    ui.expect("evidence.trace.reference").to_have_value(TOKEN_RE)

    # Partial trace: no node table until Debug is on; failed or halted node highlighted.
    ui.load("evidence", "t-partial-debug")
    ui.expect("evidence.trace.summary").to_be_visible()
    assert _debug_views(ui) == (0, 0)
    ui.el("evidence.trace.debug").check()
    ui.expect("evidence.trace.identity").to_be_visible()
    nodes = ui.el("evidence.trace.nodes")
    ui.expect(nodes).to_be_visible()
    flagged = nodes.locator('tr[data-row-state="failed"], tr[data-row-state="halted"]')
    ui.expect(flagged.first).to_be_visible()

    # Clean trace: sentinel fields.
    ui.load("evidence", "t-clean")
    ui.expect("evidence.trace.bundle-ref").to_contain_text("not yet recorded")

    # Refusal state of the Evidence Inspector.
    ui.set_state("evidence", "refusal")
    ui.expect("evidence.state.refusal").to_contain_text("record no longer present")
