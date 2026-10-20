"""WIRE-06 row tests: ``parse_wiring`` reports every malformed document instead of raising.

This file is new because the neighbouring validator tests may become ledger-protected. Every test
imports only names that exist at the phase base and captures exceptions, so a failure at the base
is a plain ``AssertionError`` (Phase 13 fail-first rule).
"""

from __future__ import annotations

import pytest
from databasise.parts.registry import default_registry
from databasise.seam.engine import Databasise
from databasise.seam.query import QueryObject
from databasise.validator.parse import parse_wiring


def _parse(doc):
    """(parsed, raised): the parse result, or the exception ``parse_wiring`` raised."""
    try:
        return parse_wiring(doc, default_registry()), None
    except Exception as exc:  # noqa: BLE001 - the test asserts on what was raised
        return None, exc


@pytest.mark.parametrize("doc", [[], {"nodes": None}, {"nodes": [1]}], ids=["list", "none", "list-nodes"])
def test_a_malformed_document_is_reported_not_raised(doc):
    parsed, raised = _parse(doc)

    assert raised is None, f"parse_wiring raised {type(raised).__name__}: {raised}"
    assert parsed.report.ok is False
    assert parsed.report.violations


async def test_a_query_on_a_malformed_document_is_refused_by_name(tmp_path):
    engine = Databasise(store_root=tmp_path, workspace="w13-01", clients={})
    caught = None
    try:
        await engine._execute_resolved(QueryObject(text="x"), {"nodes": None})
    except Exception as exc:  # noqa: BLE001
        caught = exc

    assert type(caught).__name__ == "UnparseableWiringError", repr(caught)
    assert "invalid-wiring-document" in caught.violations


@pytest.mark.parametrize("doc", [{}, {"nodes": {}}], ids=["no-nodes-key", "empty-nodes"])
def test_an_empty_document_reports_empty_wiring(doc):
    parsed, raised = _parse(doc)

    assert raised is None, f"parse_wiring raised {type(raised).__name__}: {raised}"
    assert "empty-wiring" in {v.code for v in parsed.report.violations}
