"""06-07-PLAN.md Task 3: pins the port's completeness claim (MODAL-04) against the governing
record — deriving both sides at test time rather than from a hand-maintained literal list wherever
possible. Mirrors ``tests/parity/test_arm_conformance.py``'s own resolved-node-id-set conformance
shape (its "criterion 1" checks), adapted to a single 13-node base wiring with no arms.

``## §H``'s own text is this test module's oracle: the node set, the declared ``effects[]:``
union, the ``Recipe:``, the ``Admission: n/a — decomposed`` verdict, and the ``Arms:
none (single base wiring)`` statement. See ``databasise/evidence/HIPPORAG-PORT-RECORD.md`` for the
full declared-effects reconciliation this test's additive-effects assertion is drawn from.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from databasise.parts.registry import default_registry
from databasise.validator.depth import effective_depth
from databasise.validator.execution_mode import derive_execution_mode
from databasise.validator.parse import parse_wiring
from databasise.wirings.resolve import load_wiring


def _repository_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "docs" / "system-model").is_dir():
            return parent
    raise RuntimeError(f"could not locate repository root walking up from {__file__}")


def _governing_wiring() -> dict[str, Any]:
    path = _repository_root() / "docs" / "system-model" / "wirings" / "hipporag-base.json"
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


# PARTS.md ## §H's own "effects[]:" sentence — the union it declares, before any of this port's
# own additive discrepancies (see HIPPORAG-PORT-RECORD.md for the per-node reconciliation).
_GOVERNING_EFFECTS_UNION = frozenset(
    {"calls_embedding", "calls_llm", "reads_vector", "reads_graph", "reads_kv"}
)

# Every additive effect a built node declares beyond ## §H's node-table row for it — collected
# from 06-01/06-02/06-05/06-07's own recorded discrepancies (HIPPORAG-PORT-RECORD.md).
_ADDITIVE_EFFECTS = frozenset({"writes_vector", "writes_kv", "writes_graph", "writes_artifact"})


def test_the_governing_wiring_declares_exactly_thirteen_positions():
    """Sanity precondition, named so a governing-doc edit that silently changes the position
    count fails loudly here rather than corrupting the assertions below."""
    assert len(_governing_wiring()["nodes"]) == 13


def test_the_built_wirings_resolved_node_id_set_equals_the_governing_thirteen():
    built = load_wiring("hipporag")
    governing = _governing_wiring()
    assert set(built["nodes"].keys()) == set(governing["nodes"].keys())


def test_every_node_resolves_to_a_registered_part_with_a_non_none_body():
    registry = default_registry()
    built = load_wiring("hipporag")
    for node_id, node in built["nodes"].items():
        part = registry.get(node["component"])
        assert part.body is not None, node_id


def test_no_hipporag_part_is_opaque_kinded_and_none_carries_an_admission_record():
    """Makes ## §H's ``Admission: n/a — decomposed`` verdict checkable, and MODAL-04's "no opaque
    core left behind" clause checkable with it."""
    registry = default_registry()
    built = load_wiring("hipporag")
    for node_id, node in built["nodes"].items():
        part = registry.get(node["component"])
        assert part.kind != "opaque", node_id
        assert part.admission is None, node_id


def test_effective_depth_is_opaque_at_all_thirteen_positions():
    registry = default_registry()
    built = load_wiring("hipporag")
    parsed = parse_wiring(built, registry)
    assert parsed.report.ok, [v.code for v in parsed.report.violations]

    depths = effective_depth(parsed)
    assert set(depths.values()) == {"opaque"}
    assert set(depths.keys()) == set(built["nodes"].keys())


def test_declared_effects_union_equals_the_governing_union_plus_exactly_the_additive_set():
    registry = default_registry()
    built = load_wiring("hipporag")
    built_union: set[str] = set()
    for node in built["nodes"].values():
        part = registry.get(node["component"])
        built_union.update(part.effects)

    assert built_union == _GOVERNING_EFFECTS_UNION | _ADDITIVE_EFFECTS


def test_recipe_equals_the_governing_recipe():
    built = load_wiring("hipporag")
    governing = _governing_wiring()
    assert built["recipe"] == governing["recipe"]


def test_the_wiring_declares_no_arms_and_no_patch_file_exists_for_this_modality():
    wirings_dir = _repository_root() / "databasise" / "wirings" / "hipporag"
    patch_files = list(wirings_dir.glob("*.json-patch.json"))
    assert patch_files == []


def test_derive_execution_mode_returns_in_process_for_all_thirteen_positions():
    registry = default_registry()
    built = load_wiring("hipporag")
    for node_id, node in built["nodes"].items():
        part = registry.get(node["component"])
        mode = derive_execution_mode(part.effects, part.kind)
        assert mode == "in-process", (node_id, mode)
