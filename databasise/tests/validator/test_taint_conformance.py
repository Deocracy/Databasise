"""Spike 005's twelve-case laundering conformance set, ported under the repaired contract
vocabulary (D-03). Every case runs through the real ``parse_wiring`` -> ``effective_depth`` ->
``blast_radius_violations`` path (``databasise/validator/parse.py`` wires the latter two
together at load time) — this file never reimplements the taint or blast-radius rules itself;
only the case-table oracle values below (fixed by the spike, then repaired per D-03) are new.

Source: ``.claude/skills/spike-findings-rag-graph-vector-raw/sources/005-laundering-test/taint.py``
(the twelve-case table, lines 86-195) and its ``README.md`` (the Falsifier 1 record and the
three-scope repair). D-03 names three divergences the port must repair, not carry:

1. ``writes_quarantined`` is not an ``effects[]`` member. Scope is a property of the artifact
   write, carried here as ``artifact_scope`` on the registered ``Part`` (see
   ``test_repair_one_no_fixture_declares_the_fabricated_effect`` below).
2. ``writes_artifact`` is distinguished from the four transient store-write effects, which sit
   outside the blast-radius rule by design (see
   ``test_transient_effects_added_to_case_6_change_nothing`` below).
3. Case 3 is an ordinary expected refusal here — the prototype's harness exempted any case whose
   title started with ``"3."`` from its own failure count (``taint.py`` lines 260-262); this port
   carries no such exemption, and case 3's expected violation set is ``{"ingest"}``, not empty.
"""

from __future__ import annotations

import typing

import pytest
from databasise.parts.registry import UnknownPartError
from databasise.parts.schema import Effect, Part
from databasise.validator.errors import CODE_BLAST_RADIUS_REFUSAL
from databasise.validator.parse import parse_wiring

SPIKE_SOURCE_PATH = (
    ".claude/skills/spike-findings-rag-graph-vector-raw/sources/005-laundering-test/taint.py"
)

# The spike's component registry (taint.py lines 26-45), restated in this project's Part shape.
# Every entry's upstream_ref names this file's provenance per CONTRACT §7/D-14 — this is copied
# prior work, not new authorship.
FIXTURE_COMPONENTS: dict[str, dict[str, object]] = {
    "seed-selector@1.0": {"depth": "stage", "effects": []},
    "expander@1.1": {"depth": "stage", "effects": ["reads_graph"]},
    "ranker@1.0": {"depth": "stage", "effects": []},
    "assembler@2.2": {"depth": "stage", "effects": []},
    "generator@1.0": {"depth": "stage", "effects": ["calls_llm"]},
    "chunker@1.2": {"depth": "stage", "effects": ["writes_artifact"]},
    "extractor@2.0": {"depth": "stage", "effects": ["calls_llm", "writes_artifact"]},
    "embedder@3.0": {"depth": "stage", "effects": ["writes_artifact"]},
    "rerank-cache@1.0": {"depth": "stage", "effects": ["writes_artifact"]},
    "lightrag-ingest@1.5.4": {"depth": "opaque", "effects": ["calls_llm", "writes_artifact"]},
    # D-03 repair 1: the proposed repair, same part, writing an instance-scoped quarantined
    # namespace — declared via artifact_scope, never via a fabricated effect member.
    "lightrag-ingest-quarantined@1.5.4": {
        "depth": "opaque",
        "effects": ["calls_llm", "writes_artifact"],
        "artifact_scope": "quarantined",
    },
    "lightrag-query@1.5.4": {"depth": "opaque", "effects": ["calls_llm"]},
    "cbm-mcp@0.3": {"depth": "opaque", "effects": ["self_storage", "fs"]},
    "hipporag@2.0": {"depth": "evidence", "effects": ["calls_llm"]},
}


def _build_fixture_parts() -> dict[str, Part]:
    parts: dict[str, Part] = {}
    for name_at_version, spec in FIXTURE_COMPONENTS.items():
        part = Part(
            name_at_version=name_at_version,
            kind=str(spec["depth"]),
            structural_depth=spec["depth"],  # type: ignore[arg-type]
            effects=list(spec["effects"]),  # type: ignore[arg-type]
            upstream_ref=SPIKE_SOURCE_PATH,
        )
        if "artifact_scope" in spec:
            part.artifact_scope = spec["artifact_scope"]
        parts[name_at_version] = part
    return parts


class _FixtureRegistry:
    """Duck-types ``PartRegistry.get`` only — ``parse_wiring`` calls nothing else on its
    ``registry`` argument. Scoped to this test module rather than routed through
    ``databasise/parts/registry.py``: that file is plan 01-04's lane in this wave, and a
    single-method lookup shim is all this conformance set needs.
    """

    def __init__(self, parts: dict[str, Part]):
        self._parts = parts

    def get(self, name_at_version: str) -> Part:
        try:
            return self._parts[name_at_version]
        except KeyError:
            raise UnknownPartError(name_at_version, list(self._parts.keys())) from None


REGISTRY = _FixtureRegistry(_build_fixture_parts())


def _n(component: str, *deps: str) -> dict[str, object]:
    spec = FIXTURE_COMPONENTS[component]
    return {
        "component": component,
        "kind": "primitive",
        "effects": list(spec["effects"]),  # type: ignore[arg-type]
        "deps": list(deps),
    }


def _blast_radius_node_ids(doc: dict[str, object]) -> frozenset[str]:
    parsed = parse_wiring(doc, REGISTRY)  # type: ignore[arg-type]
    return frozenset(
        v.pointer.split("/")[2]
        for v in parsed.report.violations
        if v.code == CODE_BLAST_RADIUS_REFUSAL
    )


# Case id -> (wiring nodes, expected violation node-id set). D-03-repaired against taint.py's
# own case table (lines 86-195); see the module docstring for what changed and why.
CASES: list[tuple[str, dict[str, object], frozenset[str]]] = [
    (
        "1_decomposed_ingest_opaque_query_core",
        {
            "chunk": _n("chunker@1.2"),
            "extract": _n("extractor@2.0", "chunk"),
            "qcore": _n("lightrag-query@1.5.4"),
            "asm": _n("assembler@2.2", "qcore"),
        },
        frozenset(),
    ),
    (
        "2_index_side_laundering",
        {
            "ocore": _n("lightrag-query@1.5.4"),
            "extract": _n("extractor@2.0", "ocore"),
        },
        frozenset({"extract"}),
    ),
    (
        "3_real_lightrag_middle_state",
        {
            "ingest": _n("lightrag-ingest@1.5.4"),
            "seed": _n("seed-selector@1.0", "ingest"),
            "expand": _n("expander@1.1", "seed"),
            "rank": _n("ranker@1.0", "expand"),
            "asm": _n("assembler@2.2", "rank"),
            "gen": _n("generator@1.0", "asm"),
        },
        frozenset({"ingest"}),  # D-03 repair 3: an ordinary refusal, not exempted
    ),
    (
        "3b_ingest_run_alone",
        {"ingest": _n("lightrag-ingest@1.5.4")},
        frozenset({"ingest"}),
    ),
    (
        "3c_query_run_alone_no_runtime_dep_on_ingest",
        {
            "seed": _n("seed-selector@1.0"),
            "expand": _n("expander@1.1", "seed"),
            "rank": _n("ranker@1.0", "expand"),
            "asm": _n("assembler@2.2", "rank"),
            "gen": _n("generator@1.0", "asm"),
        },
        frozenset(),
    ),
    (
        "3d_quarantined_repair",
        {"ingest": _n("lightrag-ingest-quarantined@1.5.4")},
        frozenset(),
    ),
    (
        "4_fully_decomposed",
        {
            "chunk": _n("chunker@1.2"),
            "extract": _n("extractor@2.0", "chunk"),
            "embed": _n("embedder@3.0", "chunk"),
            "seed": _n("seed-selector@1.0", "embed"),
            "asm": _n("assembler@2.2", "seed"),
        },
        frozenset(),
    ),
    (
        "5_fully_opaque_self_storage",
        {"cbm": _n("cbm-mcp@0.3")},
        frozenset(),
    ),
    (
        "6_opaque_direct_shared_write",
        {"ingest": _n("lightrag-ingest@1.5.4")},
        frozenset({"ingest"}),
    ),
    (
        "7_non_adjacent_fan_in",
        {
            "ocore": _n("lightrag-query@1.5.4"),
            "rank": _n("ranker@1.0"),
            "cache": _n("rerank-cache@1.0", "rank", "ocore"),
        },
        frozenset({"cache"}),
    ),
    (
        "8_parallel_lanes",
        {
            "chunk": _n("chunker@1.2"),
            "embed": _n("embedder@3.0", "chunk"),
            "qcore": _n("lightrag-query@1.5.4"),
            "asm": _n("assembler@2.2", "qcore"),
        },
        frozenset(),
    ),
    (
        "9_evidence_depth_shared_write",
        {
            "hippo": _n("hipporag@2.0"),
            "extract": _n("extractor@2.0", "hippo"),
        },
        frozenset({"extract"}),
    ),
]


def test_case_table_has_exactly_twelve_entries():
    """Meta-test: the ported table carries all twelve spike-005 cases, no more, no fewer."""
    assert len(CASES) == 12


@pytest.mark.parametrize("case_id,wiring_nodes,expected", CASES, ids=[c[0] for c in CASES])
def test_case(case_id: str, wiring_nodes: dict[str, object], expected: frozenset[str]) -> None:
    """One parametrized test over all twelve cases: the computed violation set must equal the
    expected set exactly — not a superset, not a subset.
    """
    doc = {"nodes": wiring_nodes}
    got = _blast_radius_node_ids(doc)
    assert got == expected, case_id


def test_transient_effects_added_to_case_6_change_nothing():
    """D-03 repair 2: adding each of writes_kv/writes_vector/writes_graph/writes_lexical to case
    6's opaque node leaves the violation set at {"ingest"} — no additional violation appears for
    the transient writes themselves, because they sit outside the blast-radius rule by design.
    """
    base_effects = list(FIXTURE_COMPONENTS["lightrag-ingest@1.5.4"]["effects"])  # type: ignore[arg-type]
    for transient_effect in ("writes_kv", "writes_vector", "writes_graph", "writes_lexical"):
        doc = {
            "nodes": {
                "ingest": {
                    "component": "lightrag-ingest@1.5.4",
                    "kind": "primitive",
                    "effects": [*base_effects, transient_effect],
                    "deps": [],
                }
            }
        }
        got = _blast_radius_node_ids(doc)
        assert got == frozenset({"ingest"}), transient_effect


def test_repair_one_no_fixture_declares_the_fabricated_effect():
    """D-03 repair 1: ``writes_quarantined`` is not one of the seventeen frozen ``effects[]``
    members. Every fixture part's declared effects is a subset of that vocabulary, checked by
    value rather than by a text search of this module.
    """
    allowed = set(typing.get_args(Effect))
    for name_at_version, spec in FIXTURE_COMPONENTS.items():
        declared = set(spec["effects"])  # type: ignore[arg-type]
        assert declared <= allowed, name_at_version
        assert "writes_quarantined" not in declared, name_at_version
