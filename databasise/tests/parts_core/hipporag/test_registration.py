"""06-01-PLAN.md Task 3 (extended by 06-02-PLAN.md, then 06-05-PLAN.md): every ``HIPPORAG_PARTS``
member's declared shape is pinned — table-driven against a hand-written mapping, so a future
accidental change to any part's own ``kind``/``effects``/``structural_depth`` fails here rather
than silently drifting. Also proves none of the parts needs subprocess containment
(``derive_execution_mode`` — the 01-03 hardened version the runner actually uses,
``databasise.validator.execution_mode``, never the tracer-era duplicate in
``databasise.validator.depth``) and that the parsed HippoRAG wiring resolves every node to
``opaque`` effective depth. 06-02-PLAN.md added ``hipporag/chunker-embedder@0.1.0``,
``hipporag/openie-extractor@0.1.0`` and ``hipporag/entity-fact-embedder@0.1.0`` to the pinned
mapping (five members -> eight). 06-05-PLAN.md Task 1 adds ``hipporag/fact-edge-builder@0.1.0``
and ``hipporag/passage-edge-builder@0.1.0`` (eight -> ten); Task 2 adds
``hipporag/synonymy-edge-builder@0.1.0`` (ten -> eleven); Task 3 adds
``hipporag/graph-materializer@0.1.0``, completing HippoRAG's seven-position index side
(eleven -> twelve).
"""

from __future__ import annotations

from databasise.parts.registry import default_registry
from databasise.parts_core.hipporag import HIPPORAG_PARTS
from databasise.validator.depth import effective_depth
from databasise.validator.execution_mode import derive_execution_mode
from databasise.validator.parse import parse_wiring
from databasise.wirings.resolve import load_wiring

_EXPECTED_SHAPE: dict[str, dict[str, object]] = {
    "hipporag/fact-scorer@0.1.0": {
        "kind": "retriever",
        "effects": ["reads_vector", "calls_embedding"],
        "structural_depth": "opaque",
    },
    "hipporag/fact-filter@0.1.0": {
        "kind": "ranker-reranker",
        "effects": ["calls_llm"],
        "structural_depth": "opaque",
    },
    "hipporag/reset-vector-join@0.1.0": {
        "kind": "join",
        "effects": ["reads_vector", "calls_embedding", "reads_kv"],
        "structural_depth": "opaque",
    },
    "hipporag/ppr-retriever@0.1.0": {
        "kind": "retriever",
        "effects": ["reads_graph"],
        "structural_depth": "opaque",
    },
    "hipporag/result-assembler@0.1.0": {
        "kind": "assembler",
        "effects": ["reads_kv"],
        "structural_depth": "opaque",
    },
    "hipporag/chunker-embedder@0.1.0": {
        "kind": "embedder",
        "effects": ["calls_embedding", "writes_vector", "writes_kv"],
        "structural_depth": "opaque",
    },
    "hipporag/openie-extractor@0.1.0": {
        "kind": "extractor",
        "effects": ["calls_llm"],
        "structural_depth": "opaque",
    },
    "hipporag/entity-fact-embedder@0.1.0": {
        "kind": "embedder",
        "effects": ["calls_embedding", "writes_vector"],
        "structural_depth": "opaque",
    },
    "hipporag/fact-edge-builder@0.1.0": {
        "kind": "extractor",
        "effects": [],
        "structural_depth": "opaque",
    },
    "hipporag/passage-edge-builder@0.1.0": {
        "kind": "extractor",
        "effects": [],
        "structural_depth": "opaque",
    },
    "hipporag/synonymy-edge-builder@0.1.0": {
        "kind": "extractor",
        "effects": ["reads_vector"],
        "structural_depth": "opaque",
    },
    "hipporag/graph-materializer@0.1.0": {
        "kind": "extractor",
        "effects": ["writes_graph", "writes_artifact"],
        "structural_depth": "opaque",
    },
}


def test_hipporag_parts_has_exactly_twelve_members_matching_the_pinned_names():
    assert {part.name_at_version for part in HIPPORAG_PARTS} == set(_EXPECTED_SHAPE)
    assert len(HIPPORAG_PARTS) == 12


def test_every_part_matches_its_pinned_kind_effects_and_structural_depth():
    for part in HIPPORAG_PARTS:
        expected = _EXPECTED_SHAPE[part.name_at_version]
        assert part.kind == expected["kind"], part.name_at_version
        assert part.effects == expected["effects"], part.name_at_version
        assert part.structural_depth == expected["structural_depth"], part.name_at_version


def test_none_of_the_twelve_parts_requires_containment_beyond_in_process():
    for part in HIPPORAG_PARTS:
        mode = derive_execution_mode(part.effects, part.kind)
        assert mode == "in-process", (part.name_at_version, mode)


def test_default_registry_registers_all_twelve_hipporag_names():
    registry = default_registry()
    for name in _EXPECTED_SHAPE:
        assert name in registry.keys()


def test_effective_depth_over_the_parsed_hipporag_wiring_is_opaque_at_every_node():
    registry = default_registry()
    resolved = load_wiring("hipporag")
    parsed = parse_wiring(resolved, registry)
    assert parsed.report.ok, [v.code for v in parsed.report.violations]

    depths = effective_depth(parsed)
    assert set(depths.values()) == {"opaque"}
    assert set(depths.keys()) == set(resolved["nodes"].keys())
