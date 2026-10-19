"""12-05 Task 1 (HIPP-12, D-16): a query run keeps only the ancestors of ``provides``, and capability
matching sees the effects a query run of the candidate can have (its pruned copy), not the effects of
the index-side nodes the query never dispatches."""

from __future__ import annotations

import copy

import pytest

from databasise.parts.registry import default_registry
from databasise.seam.refusals import UnsatisfiableSelectorError
from databasise.seam.selectors import Selector, resolve_selector
from databasise.wirings.resolve import (
    load_wiring,
    resolve_arm,
    without_recipe_only_nodes,
    wiring_family,
)

_LIGHTRAG_ARMS = ("naive", "bypass", "hybrid", "local", "global")
_HIPPORAG_QUERY_NODES = {
    "fact-score",
    "fact-filter",
    "reset-vector-join",
    "ppr",
    "dpr-fallback",
    "assemble-result",
}


def _recipe_only_rule(resolved: dict) -> set[str]:
    """The node set the pre-D-16 rule kept: every node except undepended recipe nodes."""
    nodes = resolved["nodes"]
    recipe_ids = set((resolved.get("recipe") or {}).values())
    dropped = {
        node_id
        for node_id in recipe_ids & set(nodes)
        if not any(node_id in (node.get("deps") or []) for node in nodes.values())
    }
    return set(nodes) - dropped


def test_hipporag_pruning_keeps_exactly_the_query_side_nodes():
    resolved = load_wiring("hipporag")
    before = copy.deepcopy(resolved)

    pruned = without_recipe_only_nodes(resolved)

    assert set(pruned["nodes"]) == _HIPPORAG_QUERY_NODES
    assert resolved == before  # the full wiring is left untouched


@pytest.mark.parametrize("arm", _LIGHTRAG_ARMS)
def test_every_lightrag_arm_prunes_to_the_node_set_the_recipe_only_rule_gave(arm):
    resolved = resolve_arm(arm)

    assert set(without_recipe_only_nodes(resolved)["nodes"]) == _recipe_only_rule(resolved)


def test_empty_provides_falls_back_to_the_recipe_only_rule():
    resolved = {
        "nodes": {
            "a": {"deps": []},
            "b": {"deps": ["a"]},
            "idx": {"deps": []},
        },
        "recipe": {"embedding": "idx"},
        "provides": [],
    }

    assert set(without_recipe_only_nodes(resolved)["nodes"]) == {"a", "b"}


def test_provides_naming_no_node_falls_back_to_the_recipe_only_rule():
    resolved = {
        "nodes": {"a": {"deps": []}, "idx": {"deps": []}},
        "recipe": {"embedding": "idx"},
        "provides": ["ghost"],
    }

    assert set(without_recipe_only_nodes(resolved)["nodes"]) == {"a"}


def _resolve_family(capability: list[str]) -> str | UnsatisfiableSelectorError:
    try:
        resolved = resolve_selector(Selector(capability=capability), registry=default_registry())
    except UnsatisfiableSelectorError as exc:
        return exc
    return wiring_family(resolved)


def test_a_write_effect_selector_no_longer_resolves_to_the_hipporag_wiring():
    outcome = _resolve_family(["writes_graph"])

    assert outcome != "hipporag", outcome


def test_writes_artifact_is_unsatisfiable():
    outcome = _resolve_family(["writes_artifact"])

    assert isinstance(outcome, UnsatisfiableSelectorError), outcome


def test_the_read_selector_the_seam_uses_still_resolves_to_hipporag():
    assert _resolve_family(["reads_graph", "reads_kv"]) == "hipporag"
