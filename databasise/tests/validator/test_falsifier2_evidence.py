"""Falsifier 2 evidence: MACH-01's named wirings compute effective_depth/execution_mode
correctly against the real ``default_registry()``, through the same functions the runner calls
(``databasise.validator.depth.effective_depth``, never the superseded tracer-era
``derive_execution_mode`` also in that module — see ``databasise.validator.execution_mode``'s
canonical, four-value version), and the rendered evidence document is stable under re-render.
Covers .planning/phases/02-falsifier-gate/02-CONTEXT.md D-03 and REQUIREMENTS.md MACH-01.
"""

from __future__ import annotations

from databasise.evidence.falsifier2 import EVIDENCE_PATH, evaluate_wiring, render_markdown

_W1_EXECUTION_MODES = {
    "retrieve": "in-process",
    "refine": "long-lived-service",
    "query-side": "in-process",
    "generate": "in-process",
    "assemble": "in-process",
}


def test_w1_parses_clean_against_the_real_registry():
    evidence = evaluate_wiring("w1-lightrag-query-side")
    assert evidence.violations == ()


def test_w1_every_node_computes_effective_depth_stage():
    evidence = evaluate_wiring("w1-lightrag-query-side")
    computed = {row.node_id: row.effective_depth for row in evidence.rows}
    assert computed == {node_id: "stage" for node_id in _W1_EXECUTION_MODES}


def test_w1_execution_modes_match_the_kind_and_effects_derivation():
    """``refine`` is a ``fixpoint`` node and computes ``long-lived-service``; every other W1 node
    computes ``in-process`` — none declares net/fs/self_storage/mutates_store nor is opaque.
    """
    evidence = evaluate_wiring("w1-lightrag-query-side")
    computed = {row.node_id: row.execution_mode for row in evidence.rows}
    assert computed == _W1_EXECUTION_MODES


def test_render_markdown_is_idempotent():
    assert render_markdown() == render_markdown()


def test_committed_evidence_document_matches_a_fresh_render():
    """The drift gate: the committed FALSIFIER-2-EVIDENCE.md must equal what ``render_markdown()``
    produces right now, so the document is generated output whose only author is this module —
    never hand-edited into a verdict a re-run would not reproduce.
    """
    committed = EVIDENCE_PATH.read_text(encoding="utf-8")
    assert committed == render_markdown()
