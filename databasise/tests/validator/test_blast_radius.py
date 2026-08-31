"""The blast-radius rule (CONTRACT §3): a node MAY write a shared artifact namespace only at
effective depth ``stage``. Covers plan 01-03 Task 2's blast-radius <behavior> (Tests 1-7), plus
01-10-PLAN.md Task 3's regression (the third ``missing:`` bullet in ``01-VERIFICATION.md``'s Gap
1 finding): unlike Tests 1-7 above, which construct a ``ParsedWiring`` directly, the new test
below goes through ``parse_wiring`` end to end, so it exercises the real component-resolution
path a hostile wiring would actually have to go through.
"""

from __future__ import annotations

from types import MappingProxyType

from databasise.parts.registry import PartRegistry
from databasise.parts.schema import NodeContext, Part, WiringNode
from databasise.validator.blast_radius import blast_radius_violations
from databasise.validator.errors import CODE_BLAST_RADIUS_REFUSAL
from databasise.validator.parse import ParsedWiring, parse_wiring


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


async def _shared_writer_body(ctx: NodeContext) -> dict:
    return {}


def _opaque_shared_writer_part(structural_depth: str) -> Part:
    return Part(
        name_at_version="test/opaque-shared-writer@1.0.0",
        kind="stage",
        structural_depth=structural_depth,
        effects=["writes_artifact"],
        upstream_ref=None,
        artifact_scope="shared",
        body=_shared_writer_body,
    )


def test_under_declaring_wiring_cannot_route_a_shared_artifact_write_around_the_rule():
    """01-VERIFICATION.md's third Gap-1 ``missing:`` bullet: a Part declaring
    ``writes_artifact``/scope ``shared``/depth ``opaque``, wired with its ``effects`` key omitted
    entirely (legal under ``parse_wiring``'s subset rule — ``WiringNode.effects`` defaults to an
    empty list), must still trip the blast-radius refusal through the real ``parse_wiring`` path.
    Against a tree where ``blast_radius_violations`` gated on the wiring node's own declared
    effects instead of the registry's resolved ``Part.effects`` (CR-01), this wiring would clear
    validation with zero violations — that is the fail-without-the-fix condition this test proves
    against by construction (the real ``blast_radius.py`` gates on ``parsed.parts.items()``, never
    ``parsed.nodes[...].effects``; see ``tests/test_trusted_source_invariant.py`` for the
    structural pin on that sourcing).
    """
    registry = PartRegistry(seed_tracer_parts=False)
    registry.register(_opaque_shared_writer_part("opaque"))
    doc = {
        "nodes": {
            "writer": {
                "component": "test/opaque-shared-writer@1.0.0",
                "kind": "stage",
                # "effects" deliberately omitted — WiringNode.effects defaults to [], a strict
                # under-declaration relative to the Part's own real ["writes_artifact"].
                "deps": [],
            }
        }
    }

    parsed = parse_wiring(doc, registry)

    assert parsed.report.ok is False
    blast_radius_refusals = [v for v in parsed.report.violations if v.code == CODE_BLAST_RADIUS_REFUSAL]
    assert len(blast_radius_refusals) == 1
    assert "writer" in blast_radius_refusals[0].message
    assert "opaque" in blast_radius_refusals[0].message


def test_under_declaring_wiring_at_stage_depth_is_permitted_proving_the_rule_discriminates():
    """The discriminating sibling case to the refusal above: the identical Part construction at
    ``structural_depth="stage"`` (a legal shared-write depth) yields a clean report — proving the
    rule above discriminates on depth rather than always refusing an under-declared wiring.
    """
    registry = PartRegistry(seed_tracer_parts=False)
    registry.register(_opaque_shared_writer_part("stage"))
    doc = {
        "nodes": {
            "writer": {
                "component": "test/opaque-shared-writer@1.0.0",
                "kind": "stage",
                "deps": [],
            }
        }
    }

    parsed = parse_wiring(doc, registry)

    assert parsed.report.ok is True
