"""Falsifier 2 evidence: MACH-01's named wirings compute effective_depth/execution_mode
correctly against the real ``default_registry()``, through the same functions the runner calls
(``databasise.validator.depth.effective_depth``, never the superseded tracer-era
``derive_execution_mode`` also in that module — see ``databasise.validator.execution_mode``'s
canonical, four-value version), the CONTRACT §19.10 boundary enumeration covers all three
candidate classes for every wiring, and the rendered evidence document is stable under re-render.
Covers .planning/phases/02-falsifier-gate/02-CONTEXT.md D-03 and REQUIREMENTS.md MACH-01.

03-08-PLAN.md Task 3: W1 and W3 were rewritten to resolve against the real, registered LightRAG
ports (the ``local`` arm's own fifteen-node set) rather than the single declaration-only stub
they used to carry — see ``databasise/evidence/wirings/w1-lightrag-query-side.json`` and
``w3-lightrag-half-decomposed.json``. The per-node tables grew (one row became fifteen); the
recorded Falsifier 2 verdict itself did not move (asserted by
``test_committed_evidence_document_matches_a_fresh_render`` below, and independently by this
plan's own ``<verify>`` script against the committed document's text).
"""

from __future__ import annotations

from databasise.evidence.falsifier2 import (
    EVIDENCE_PATH,
    NAMED_WIRINGS,
    enumerate_boundaries,
    evaluate_wiring,
    load_wiring,
    render_markdown,
)
from databasise.parts.registry import PartRegistry, default_registry
from databasise.parts.schema import Part
from databasise.validator.depth import effective_depth
from databasise.validator.errors import CODE_EMPTY_WIRING
from databasise.validator.parse import parse_wiring

# The real local arm's fifteen node ids (databasise/wirings/lightrag/, resolved via
# databasise/wirings/resolve.py) — W1 and W3 both embed this same node set (see module
# docstring); W3 additionally prepends the opaque "ingest" node upstream of "keywords".
_LOCAL_ARM_NODE_IDS = frozenset(
    {
        "keywords",
        "embedder-query",
        "entity-lookup",
        "entity-hydrate-expand",
        "join-entities",
        "join-relations",
        "budget-entities",
        "budget-relations",
        "chunk-sel-kg",
        "join-chunks",
        "heading-backfill",
        "rerank",
        "assemble",
        "generate",
        "embedder-index",
    }
)
_W1_NODE_IDS = _LOCAL_ARM_NODE_IDS
_W3_NODE_IDS = _LOCAL_ARM_NODE_IDS | {"ingest"}
_W2_EXECUTION_MODES = {"cbm": "subprocess", "normalise": "in-process", "answer": "in-process"}


def test_w1_parses_clean_against_the_real_registry():
    evidence = evaluate_wiring("w1-lightrag-query-side")
    assert evidence.violations == ()


def test_w1_holds_exactly_the_real_local_arms_fifteen_nodes():
    evidence = evaluate_wiring("w1-lightrag-query-side")
    assert {row.node_id for row in evidence.rows} == _W1_NODE_IDS


def test_w1_every_node_computes_effective_depth_stage_except_the_opaque_embedder_index():
    """Every ``local``-arm node is genuinely ``stage`` except ``embedder-index``, whose own
    registered Part declares ``structural_depth="opaque"`` (§L.2: tainted by the undecomposed
    ingest core it feeds) independent of any taint propagation from an upstream node — W1 carries
    no opaque node at all, so this is ``embedder-index``'s own declared depth, not inherited.
    """
    evidence = evaluate_wiring("w1-lightrag-query-side")
    computed = {row.node_id: row.effective_depth for row in evidence.rows}
    expected = {node_id: "stage" for node_id in _W1_NODE_IDS}
    expected["embedder-index"] = "opaque"
    assert computed == expected


def test_w1_execution_modes_are_all_in_process():
    """Every W1 node, including the structurally-opaque ``embedder-index``, computes
    ``in-process``: ``derive_execution_mode`` is driven by a node's own ``kind``/effects (opaque
    *kind*, or a declared net/fs/self_storage effect), not by its ``structural_depth`` — none of
    the real LightRAG parts is ``kind="opaque"`` or declares one of those effects.
    """
    evidence = evaluate_wiring("w1-lightrag-query-side")
    computed = {row.node_id: row.execution_mode for row in evidence.rows}
    assert computed == {node_id: "in-process" for node_id in _W1_NODE_IDS}


def test_w2_taint_rule_overrides_stage_nodes_downstream_of_the_opaque_cbm():
    """``cbm`` is opaque (structural_depth `opaque`, execution_mode `subprocess`); `normalise`
    and `answer` each declare `structural_depth` `stage` on their own part but compute
    `effective_depth` `opaque` — the taint rule — while still computing `execution_mode`
    `in-process` (execution_mode is derived from a node's own effects/kind, not its depth).
    """
    evidence = evaluate_wiring("w2-codebase-memory-mcp")
    assert evidence.violations == ()
    depths = {row.node_id: row.effective_depth for row in evidence.rows}
    assert depths == {"cbm": "opaque", "normalise": "opaque", "answer": "opaque"}
    modes = {row.node_id: row.execution_mode for row in evidence.rows}
    assert modes == _W2_EXECUTION_MODES


def test_w3_taint_rule_overrides_stage_nodes_downstream_of_the_opaque_ingest():
    """``ingest`` writes a `quarantined`-scope artifact at `opaque` depth, which the blast-radius
    rule permits (only a `shared`-scope write requires `stage`); every real query-side node
    downstream of ``ingest`` — the entire chain, transitively, from ``keywords`` through
    ``generate`` — taints to `opaque` despite each part's own `stage` structural_depth.
    ``embedder-index`` is the one exception: its own registered Part already declares
    `structural_depth="opaque"` independent of any taint (see W1's identical case), so it shows no
    divergence even though its computed depth is also `opaque`.
    """
    evidence = evaluate_wiring("w3-lightrag-half-decomposed")
    assert evidence.violations == ()
    depths = {row.node_id: row.effective_depth for row in evidence.rows}
    assert depths == {node_id: "opaque" for node_id in _W3_NODE_IDS}
    modes = {row.node_id: row.execution_mode for row in evidence.rows}
    expected_modes = {node_id: "in-process" for node_id in _W3_NODE_IDS}
    expected_modes["ingest"] = "subprocess"
    assert modes == expected_modes
    ingest_row = next(row for row in evidence.rows if row.node_id == "ingest")
    assert ingest_row.blast_radius == "permitted"


def test_distinct_execution_mode_set_across_all_three_wirings_is_exactly_two_values():
    """`confined-unit` is unreachable from these registered parts: the only parts declaring
    `fs`/`self_storage` are also `kind="opaque"` and take the subprocess branch first in
    `derive_execution_mode`. `long-lived-service` (previously produced by W1's now-retired
    ``refine`` fixpoint fixture node) is likewise no longer reachable — none of the real,
    registered LightRAG parts is `kind="fixpoint"`. Assert the exact set, not a count — an absence
    is expected here, not a wrong-import signal (02-RESEARCH.md).
    """
    modes = set()
    for stem in NAMED_WIRINGS:
        evidence = evaluate_wiring(stem)
        modes.update(row.execution_mode for row in evidence.rows)
    assert modes == {"in-process", "subprocess"}


def test_divergence_list_names_the_taint_overridden_nodes_and_is_empty_for_w1():
    w1 = evaluate_wiring("w1-lightrag-query-side")
    assert [r.node_id for r in w1.rows if r.effective_depth != r.structural_depth] == []

    w2 = evaluate_wiring("w2-codebase-memory-mcp")
    w2_diverged = {r.node_id for r in w2.rows if r.effective_depth != r.structural_depth}
    assert w2_diverged == {"normalise", "answer"}

    w3 = evaluate_wiring("w3-lightrag-half-decomposed")
    w3_diverged = {r.node_id for r in w3.rows if r.effective_depth != r.structural_depth}
    # Every real query-side node tainted to opaque, except "ingest" (already opaque on its own
    # declared structural_depth) and "embedder-index" (also already opaque on its own — see the
    # taint-rule test above for why).
    assert w3_diverged == (_W3_NODE_IDS - {"ingest", "embedder-index"})


def test_enumerate_boundaries_covers_all_three_classes_for_every_wiring():
    for stem in NAMED_WIRINGS:
        doc = load_wiring(stem)
        parsed = parse_wiring(doc, default_registry())
        evidence = evaluate_wiring(stem)
        boundaries = enumerate_boundaries(evidence, parsed)
        classes = {row.boundary_class for row in boundaries}
        assert classes == {"effects-change", "value-crossing", "knob"}, stem


def test_empty_wiring_reports_exactly_one_violation_and_no_depth_map():
    parsed = parse_wiring({"nodes": {}}, default_registry())
    assert len(parsed.report.violations) == 1
    assert parsed.report.violations[0].code == CODE_EMPTY_WIRING
    assert parsed.node_order == ()


def test_two_node_cycle_through_an_opaque_part_shares_one_opaque_depth_and_stays_ok():
    """A cycle is data, not a violation (CONTRACT §1): two mutually-reachable nodes, one
    resolving to an opaque part, resolve to one shared `opaque` effective depth, are recorded
    under `report.cycles`, and leave `report.ok` true.
    """
    registry = PartRegistry(seed_tracer_parts=False)
    registry.register(
        Part(
            name_at_version="test/opaque-cycle-member@1.0.0",
            kind="opaque",
            structural_depth="opaque",
            effects=[],
            upstream_ref=None,
        )
    )
    registry.register(
        Part(
            name_at_version="test/stage-cycle-member@1.0.0",
            kind="passthrough",
            structural_depth="stage",
            effects=[],
            upstream_ref=None,
        )
    )
    doc = {
        "nodes": {
            "a": {"component": "test/opaque-cycle-member@1.0.0", "kind": "opaque", "deps": ["b"]},
            "b": {"component": "test/stage-cycle-member@1.0.0", "kind": "passthrough", "deps": ["a"]},
        }
    }
    parsed = parse_wiring(doc, registry)
    assert parsed.report.ok
    assert sorted(parsed.report.cycles[0]) == ["a", "b"]
    depths = effective_depth(parsed)
    assert depths == {"a": "opaque", "b": "opaque"}


def test_render_markdown_is_idempotent():
    assert render_markdown() == render_markdown()


def test_committed_evidence_document_matches_a_fresh_render():
    """The drift gate: the committed FALSIFIER-2-EVIDENCE.md must equal what ``render_markdown()``
    produces right now, so the document is generated output whose only author is this module —
    never hand-edited into a verdict a re-run would not reproduce.
    """
    committed = EVIDENCE_PATH.read_text(encoding="utf-8")
    assert committed == render_markdown()
