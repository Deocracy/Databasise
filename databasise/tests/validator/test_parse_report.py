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
from databasise.wirings.resolve import all_wirings, load_wiring

# A registered, non-fixpoint, zero-effect part: the neutral node for graph-shape tests.
_PASSTHROUGH = "parts-core/passthrough@1.0.0"


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


def _node(deps=(), *, component=_PASSTHROUGH, kind="passthrough"):
    return {"component": component, "kind": kind, "deps": list(deps)}


def _violations(doc, code):
    parsed, raised = _parse(doc)
    assert raised is None, f"parse_wiring raised {type(raised).__name__}: {raised}"
    return [v for v in parsed.report.violations if v.code == code]


def test_a_self_loop_inside_a_larger_cycle_is_listed_once():
    parsed, raised = _parse({"nodes": {"a": _node(["a", "b"]), "b": _node(["a"])}})

    assert raised is None, f"parse_wiring raised {type(raised).__name__}: {raised}"
    assert parsed.report.cycles == [["a", "b"]]


def test_a_separate_self_loop_keeps_its_own_entry():
    doc = {"nodes": {"a": _node(["b"]), "b": _node(["a"]), "c": _node(["c"])}}
    first, raised = _parse(doc)
    second, _ = _parse(doc)

    assert raised is None, f"parse_wiring raised {type(raised).__name__}: {raised}"
    assert first.report.cycles == [["a", "b"], ["c"]]
    assert second.report.cycles == first.report.cycles


@pytest.mark.parametrize(
    ("node_id", "pointer"),
    [("x/y", "/nodes/x~1y/component"), ("a~b", "/nodes/a~0b/component")],
)
def test_a_node_id_with_a_slash_or_tilde_is_escaped_in_the_pointer(node_id, pointer):
    doc = {"nodes": {node_id: _node(component="nope/missing@9.9.9")}}

    assert [v.pointer for v in _violations(doc, "unknown-component")] == [pointer]


def test_every_shipped_wiring_still_parses_ok():
    wirings = [(name, doc) for name, doc in all_wirings()]
    for family in ("lightrag", "hipporag"):
        for variant in ("corpus-ingest", "corpus-delete"):
            wirings.append((f"{family}/{variant}", load_wiring(family, variant=variant)))

    assert wirings
    for name, doc in wirings:
        parsed, raised = _parse(doc)
        assert raised is None, f"{name}: parse_wiring raised {type(raised).__name__}"
        assert parsed.report.ok, f"{name}: {parsed.report.violations}"


def test_the_unknown_component_message_leaks_no_registry_content():
    component = "nope/missing@9.9.9"
    violations = _violations({"nodes": {"a": _node(component=component)}}, "unknown-component")

    assert len(violations) == 1
    message = violations[0].message
    assert not message.startswith(("'", '"'))
    assert component in message
    assert "registered parts" not in message
    assert not [key for key in default_registry().keys() if key in message]
