"""The blast-radius rule (CONTRACT §3): a node MAY write a shared artifact namespace only at
effective depth ``stage``. Covers plan 01-03 Task 2's blast-radius <behavior> (Tests 1-7).
"""

from __future__ import annotations

from types import MappingProxyType

from databasise.parts.schema import Part, WiringNode
from databasise.validator.blast_radius import blast_radius_violations
from databasise.validator.parse import ParsedWiring


def _single_node_parsed(effects: list[str], scope: str | None) -> ParsedWiring:
    """A one-node wiring — the only shape the blast-radius predicate needs, since it evaluates
    each node independently against a precomputed depth map.
    """
    node = WiringNode(component="fixture@1.0", kind="stage", effects=effects, deps=[])
    part = Part(
        name_at_version="fixture@1.0",
        kind="stage",
        structural_depth="stage",  # irrelevant here — the depth map below is what is under test
        effects=effects,
        upstream_ref=None,
    )
    # ``Part`` does not (yet, in this worktree) declare ``artifact_scope`` as a dataclass field —
    # that field lands via plan 01-04's Task 3 (databasise/parts/schema.py, this wave's sibling
    # lane). ``Part`` is a plain, non-frozen, non-slotted dataclass, so attribute assignment works
    # regardless of whether the field is declared, and blast_radius.py reads it back via
    # ``getattr(part, "artifact_scope", "shared")`` — see that module's docstring.
    if scope is not None:
        part.artifact_scope = scope
    return ParsedWiring(
        nodes=MappingProxyType({"n": node}),
        parts=MappingProxyType({"n": part}),
        deps=MappingProxyType({"n": ()}),
        node_order=("n",),
    )


def test_shared_write_at_stage_depth_is_no_violation():
    """Test 1."""
    parsed = _single_node_parsed(["writes_artifact"], scope="shared")
    violations = blast_radius_violations(parsed, {"n": "stage"})
    assert violations == []


def test_shared_write_at_opaque_depth_is_refused_naming_node_and_depth():
    """Test 2."""
    parsed = _single_node_parsed(["writes_artifact"], scope="shared")
    violations = blast_radius_violations(parsed, {"n": "opaque"})
    assert len(violations) == 1
    assert "n" in violations[0].message
    assert "opaque" in violations[0].message


def test_shared_write_at_evidence_depth_is_also_refused():
    """Test 3: evidence < stage, so evidence-derived shared writes are refused too."""
    parsed = _single_node_parsed(["writes_artifact"], scope="shared")
    violations = blast_radius_violations(parsed, {"n": "evidence"})
    assert len(violations) == 1
    assert "evidence" in violations[0].message


def test_quarantined_write_at_opaque_depth_is_permitted():
    """Test 4."""
    parsed = _single_node_parsed(["writes_artifact"], scope="quarantined")
    violations = blast_radius_violations(parsed, {"n": "opaque"})
    assert violations == []


def test_self_storage_write_at_opaque_depth_is_permitted():
    """Test 5."""
    parsed = _single_node_parsed(["writes_artifact"], scope="self_storage")
    violations = blast_radius_violations(parsed, {"n": "opaque"})
    assert violations == []


def test_transient_store_writes_are_outside_the_rule_at_any_depth():
    """Test 6: writes_kv/writes_vector/writes_graph/writes_lexical never trigger a violation,
    however shallow the effective depth, because they carry no artifact namespace at all
    (PARTS-04 D1) — checked independently for each of the four.
    """
    for transient_effect in ("writes_kv", "writes_vector", "writes_graph", "writes_lexical"):
        parsed = _single_node_parsed([transient_effect], scope=None)
        violations = blast_radius_violations(parsed, {"n": "opaque"})
        assert violations == [], transient_effect


def test_unstated_artifact_scope_defaults_to_shared_in_both_directions():
    """Test 7: a writes_artifact node with no scope stated is judged shared — refused when the
    effective depth is not stage, and permitted when it is.
    """
    parsed = _single_node_parsed(["writes_artifact"], scope=None)

    refused = blast_radius_violations(parsed, {"n": "opaque"})
    assert len(refused) == 1

    permitted = blast_radius_violations(parsed, {"n": "stage"})
    assert permitted == []
