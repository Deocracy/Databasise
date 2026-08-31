"""Cycle-safe depth: Tarjan SCC condensation (Tests 1-6, ``strongly_connected_components`` and
``effective_depth`` directly), and ``parse_wiring``'s one-pass violation accumulation plus
cycle-as-data reporting (Tests 7-9). Covers plan 01-03 Task 1's <behavior> in full.

Also covers CR-01's ``parse_wiring`` consistency check: a wiring node's declared ``effects`` must
be a subset of its resolved Part's own declared ``effects`` (``CODE_EFFECTS_EXCEED_PART``) — see
``databasise/runner/scheduler.py``'s and ``databasise/validator/blast_radius.py``'s own CR-01
notes for the containment/blast-radius enforcement this check is a document-validation-layer
complement to.
"""

from __future__ import annotations

from types import MappingProxyType

from databasise.parts.registry import PartRegistry
from databasise.parts.schema import Part, WiringNode
from databasise.validator.cycles import strongly_connected_components
from databasise.validator.depth import effective_depth
from databasise.validator.errors import CODE_EFFECTS_EXCEED_PART, CODE_EMPTY_WIRING
from databasise.validator.parse import ParsedWiring, parse_wiring


def _make_parsed(depths: dict[str, str], deps: dict[str, list[str]]) -> ParsedWiring:
    """Hand-build a minimal ``ParsedWiring`` directly from a node-id -> structural-depth map plus
    a node-id -> deps-list map, bypassing ``parse_wiring``/the registry — these tests are about
    ``effective_depth``'s own reduction, not about parsing.
    """
    nodes: dict[str, WiringNode] = {}
    parts: dict[str, Part] = {}
    for node_id, depth in depths.items():
        node_deps = deps.get(node_id, [])
        nodes[node_id] = WiringNode(component=f"{node_id}@1.0", kind="stage", deps=node_deps)
        parts[node_id] = Part(
            name_at_version=f"{node_id}@1.0",
            kind="stage",
            structural_depth=depth,
            effects=[],
            upstream_ref=None,
        )
    deps_map = {node_id: tuple(deps.get(node_id, [])) for node_id in depths}
    return ParsedWiring(
        nodes=MappingProxyType(nodes),
        parts=MappingProxyType(parts),
        deps=MappingProxyType(deps_map),
        node_order=tuple(sorted(depths)),
    )


def test_linear_chain_taints_downstream_from_an_opaque_root():
    """Test 1: a -> b -> c, a is opaque, b/c are stage: all three compute opaque."""
    parsed = _make_parsed(
        depths={"a": "opaque", "b": "stage", "c": "stage"},
        deps={"b": ["a"], "c": ["b"]},
    )
    depths = effective_depth(parsed)
    assert depths == {"a": "opaque", "b": "opaque", "c": "opaque"}


def test_parallel_lanes_do_not_taint_each_other():
    """Test 2: two lanes with no dep edge between them — an opaque node in lane 2 leaves lane 1's
    stage node untouched.
    """
    parsed = _make_parsed(
        depths={"lane1": "stage", "lane2_root": "opaque", "lane2_leaf": "stage"},
        deps={"lane2_leaf": ["lane2_root"]},
    )
    depths = effective_depth(parsed)
    assert depths["lane1"] == "stage"
    assert depths["lane2_leaf"] == "opaque"


def test_non_adjacent_fan_in_taints():
    """Test 3: a node depending on both a stage sibling and an opaque sibling computes opaque."""
    parsed = _make_parsed(
        depths={"stage_sib": "stage", "opaque_sib": "opaque", "fan_in": "stage"},
        deps={"fan_in": ["stage_sib", "opaque_sib"]},
    )
    depths = effective_depth(parsed)
    assert depths["fan_in"] == "opaque"


def test_three_node_cycle_resolves_one_shared_depth_and_is_one_scc():
    """Test 4: a -> b -> c -> a, one member evidence and the rest stage: all three compute
    evidence, and ``strongly_connected_components`` groups exactly those three into one component.
    """
    deps = {"a": {"b"}, "b": {"c"}, "c": {"a"}}
    sccs = strongly_connected_components(deps)
    assert sccs == [{"a", "b", "c"}]

    parsed = _make_parsed(
        depths={"a": "evidence", "b": "stage", "c": "stage"},
        deps={"a": ["b"], "b": ["c"], "c": ["a"]},
    )
    depths = effective_depth(parsed)
    assert depths == {"a": "evidence", "b": "evidence", "c": "evidence"}


def test_downstream_node_inherits_the_cycles_depth_in_dependency_order():
    """Test 5: a cycle {a, b} at depth opaque, and a downstream stage node depending on the
    cycle, computes the downstream node's depth as the cycle's depth — proving the condensation
    DAG is traversed in dependency order, not just node-id order.
    """
    parsed = _make_parsed(
        depths={"a": "opaque", "b": "stage", "downstream": "stage"},
        deps={"a": ["b"], "b": ["a"], "downstream": ["a"]},
    )
    depths = effective_depth(parsed)
    assert depths["a"] == "opaque"
    assert depths["b"] == "opaque"
    assert depths["downstream"] == "opaque"


def test_self_loop_is_a_one_member_scc_and_does_not_recurse_infinitely():
    """Test 6: a -> a is a valid one-member SCC computed without recursion."""
    sccs = strongly_connected_components({"a": {"a"}})
    assert sccs == [{"a"}]


def test_parse_wiring_accumulates_three_independent_defects_in_one_pass():
    """Test 7: a document with three independent defects (unknown component, dangling dep,
    unknown effect) returns all three in one ``ValidationReport``, each with a distinct pointer,
    and raises nothing.
    """
    doc = {
        "nodes": {
            "unknown_component": {"component": "does-not-exist@1.0", "kind": "stage", "deps": []},
            "dangling_dep": {
                "component": "core/passthrough@1.0.0",
                "kind": "stage",
                "deps": ["missing"],
            },
            "unknown_effect": {
                "component": "core/passthrough@1.0.0",
                "kind": "stage",
                "effects": ["not-a-real-effect"],
                "deps": [],
            },
        }
    }
    parsed = parse_wiring(doc, PartRegistry())  # must not raise
    assert len(parsed.report.violations) == 3
    pointers = {v.pointer for v in parsed.report.violations}
    assert len(pointers) == 3


def test_empty_wiring_is_one_violation_and_a_single_clean_node_yields_one_depth():
    """Test 8: an empty ``nodes`` object produces exactly one violation pointing at ``/nodes``; a
    single-node wiring with an empty ``deps`` list validates clean and yields a depth map of
    length one.
    """
    empty_parsed = parse_wiring({"nodes": {}}, PartRegistry())
    assert len(empty_parsed.report.violations) == 1
    assert empty_parsed.report.violations[0].pointer == "/nodes"
    assert empty_parsed.report.violations[0].code == CODE_EMPTY_WIRING

    single_doc = {
        "nodes": {"solo": {"component": "core/passthrough@1.0.0", "kind": "stage", "deps": []}}
    }
    single_parsed = parse_wiring(single_doc, PartRegistry())
    assert single_parsed.report.ok
    depths = effective_depth(single_parsed)
    assert len(depths) == 1


def test_wiring_node_declaring_an_effect_its_part_does_not_is_refused():
    """CR-01: a wiring node claiming ``writes_kv`` while its resolved Part (``core/passthrough``,
    declared ``effects=[]``) does not declare it at all is refused by name
    (``CODE_EFFECTS_EXCEED_PART``), naming the offending node and both effect sets — a wiring's
    own declaration must never claim more than its registered Part actually backs.
    """
    doc = {
        "nodes": {
            "over-declared": {
                "component": "core/passthrough@1.0.0",
                "kind": "stage",
                "effects": ["writes_kv"],
                "deps": [],
            }
        }
    }
    parsed = parse_wiring(doc, PartRegistry())
    assert not parsed.report.ok
    violations = [v for v in parsed.report.violations if v.code == CODE_EFFECTS_EXCEED_PART]
    assert len(violations) == 1
    assert violations[0].pointer == "/nodes/over-declared/effects"
    assert "over-declared" in violations[0].message
    assert "writes_kv" in violations[0].message


def test_wiring_node_declaring_a_narrower_effects_set_than_its_part_is_permitted():
    """CR-01: a wiring MAY declare fewer effects than its Part is capable of (to prove it
    exercises only a subset of what the Part can do) — only a BROADER declaration is refused.
    ``core/kv-writer@1.0.0`` declares ``effects=["writes_kv"]``; a wiring node for it declaring no
    effects at all validates clean.
    """
    doc = {
        "nodes": {
            "under-declared": {"component": "core/kv-writer@1.0.0", "kind": "stage", "deps": []}
        }
    }
    parsed = parse_wiring(doc, PartRegistry())
    assert parsed.report.ok


def test_unintended_cycle_is_reported_as_data_not_raised():
    """Test 9: a cycle is reported under ``report.cycles`` as node-id data, the report stays
    ``ok`` (a cycle alone is not a violation), and no exception escapes the validator.
    """
    doc = {
        "nodes": {
            "x": {"component": "core/passthrough@1.0.0", "kind": "stage", "deps": ["y"]},
            "y": {"component": "core/passthrough@1.0.0", "kind": "stage", "deps": ["x"]},
        }
    }
    parsed = parse_wiring(doc, PartRegistry())  # must not raise
    assert parsed.report.ok
    assert len(parsed.report.cycles) == 1
    assert sorted(parsed.report.cycles[0]) == ["x", "y"]
