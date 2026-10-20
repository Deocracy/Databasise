"""WIRE-02 row tests: ``parse_wiring`` reports top-level references that name a missing node.

A ``provides`` entry or an ``evidence_position.node`` that is not among the wiring's ``nodes`` is a
named violation (``unknown-provides`` / ``unknown-evidence-node``), and every resolved wiring the
seam can select, full and pruned, names only its own nodes. The KG-arm evidence tests live in
``tests/seam/test_evidence_position.py``. This file is new because the neighbouring validator tests
may become ledger-protected. Every test imports only names that exist at the phase base and
captures exceptions, so a failure at the base is a plain ``AssertionError`` (Phase 13 fail-first rule).
"""

from __future__ import annotations

import pytest
from databasise.parts.registry import default_registry
from databasise.validator.parse import parse_wiring
from databasise.wirings.resolve import (
    all_wirings,
    load_wiring,
    resolve_arm,
    without_recipe_only_nodes,
)

_PASSTHROUGH = "parts-core/passthrough@1.0.0"
_GHOST_CODES = {"unknown-provides", "unknown-evidence-node"}


def _doc(**top_level):
    return {"nodes": {"a": {"component": _PASSTHROUGH, "kind": "passthrough", "deps": []}}, **top_level}


def _parse(doc):
    """(parsed, raised): the parse result, or the exception ``parse_wiring`` raised."""
    try:
        return parse_wiring(doc, default_registry()), None
    except Exception as exc:  # noqa: BLE001 - the test asserts on what was raised
        return None, exc


def _violations(doc):
    parsed, raised = _parse(doc)
    assert raised is None, f"parse_wiring raised {type(raised).__name__}: {raised}"
    return [(v.code, v.pointer) for v in parsed.report.violations]


def test_a_ghost_provides_entry_is_a_violation():
    assert ("unknown-provides", "/provides/0") in _violations(_doc(provides=["ghost"]))


def test_only_the_ghost_provides_entry_is_reported():
    found = _violations(_doc(provides=["a", "ghost"]))

    assert ("unknown-provides", "/provides/1") in found
    assert ("unknown-provides", "/provides/0") not in found


def test_a_ghost_evidence_node_is_a_violation():
    doc = _doc(evidence_position={"node": "ghost", "namespace": "chunks"})

    assert ("unknown-evidence-node", "/evidence_position/node") in _violations(doc)


def test_a_real_provides_and_evidence_node_are_fine():
    doc = _doc(provides=["a"], evidence_position={"node": "a", "namespace": "chunks"})

    assert not {code for code, _ in _violations(doc)} & _GHOST_CODES


@pytest.mark.parametrize("top_level", [{"provides": [], "evidence_position": None}, {}], ids=["empty-and-null", "absent"])
def test_empty_provides_and_null_evidence_position_add_no_ghost_violation(top_level):
    assert not {code for code, _ in _violations(_doc(**top_level))} & _GHOST_CODES


def test_a_node_removed_by_a_patch_but_still_named_is_a_violation():
    # bypass's old shape: base.json's chunk-vector evidence node, gone from the resolved nodes.
    doc = resolve_arm("bypass")
    doc["evidence_position"] = {"node": "chunk-vector", "namespace": "chunks"}

    assert ("unknown-evidence-node", "/evidence_position/node") in _violations(doc)


_CORPUS = [("lightrag", "corpus-ingest"), ("lightrag", "corpus-delete"), ("hipporag", "corpus-ingest"), ("hipporag", "corpus-delete")]
_CASES = [(name, doc) for name, doc in all_wirings()] + [(f"{m}/{v}", load_wiring(m, variant=v)) for m, v in _CORPUS]


@pytest.mark.parametrize("pruned", [False, True], ids=["full", "pruned"])
@pytest.mark.parametrize("name,doc", _CASES, ids=[name for name, _ in _CASES])
def test_every_resolved_wiring_names_only_its_own_nodes(name, doc, pruned):
    candidate = without_recipe_only_nodes(doc) if pruned else doc

    nodes = candidate["nodes"]
    named = list(candidate.get("provides") or []) + [(candidate.get("evidence_position") or {}).get("node")]
    ghosts = [node for node in named if node is not None and node not in nodes]
    found = _violations(candidate)  # the validator must agree with the direct check above

    assert ghosts == [], f"{name} ({'pruned' if pruned else 'full'}) names missing nodes {ghosts}"
    assert found == [], f"{name} ({'pruned' if pruned else 'full'}): {found}"


def test_bypass_names_no_removed_node():
    assert resolve_arm("bypass")["evidence_position"] is None
