"""LEDG-10 (Phase 14, D-11): capability matching sees the effects a query run exercises.

A ``writes_*`` capability must never resolve to a query wiring whose run never writes (CONTRACT
§19.9, §2 deny-by-default). Matching takes the union of the registered Part effects over
``without_recipe_only_nodes(wiring)``; the node-count tie-break stays on the full wiring.

Self-contained on purpose: it imports only names that exist at 3fd6e4c^ so it can be run there to
show the failing-first state.
"""

from __future__ import annotations

from typing import Any

import pytest

from databasise.parts.registry import default_registry
from databasise.seam.refusals import UnsatisfiableSelectorError
from databasise.seam.selectors import Selector, _wiring_effects, resolve_selector
from databasise.wirings.resolve import all_wirings, without_recipe_only_nodes

_CALLS = {"calls_embedding", "calls_llm"}
_READS = {"reads_kv", "reads_vector"}
_GRAPH_READS = _READS | {"reads_graph"}

# 14-RESEARCH §5.1: the Part effects over the pruned query run, per arm.
_EFFECTS_PER_ARM: dict[str, set[str]] = {
    "naive": _CALLS | _READS | {"calls_rerank"},
    "bypass": {"calls_llm"},
    "hybrid": _CALLS | _GRAPH_READS | {"calls_rerank"},
    "local": _CALLS | _GRAPH_READS | {"calls_rerank"},
    "global": _CALLS | _GRAPH_READS | {"calls_rerank"},
    "hipporag": _CALLS | _GRAPH_READS,
}


def _arm_named(resolved: dict[str, Any]) -> str | None:
    """The all_wirings() name a returned wiring equals (arm records carry no arm_id)."""
    return next((name for name, wiring in all_wirings() if wiring == resolved), None)


def _select(capability: list[str]) -> tuple[str | None, str | None]:
    """(arm name selected, caught exception type name); exactly one is not None."""
    try:
        resolved = resolve_selector(Selector(capability=capability), registry=default_registry())
    except Exception as caught:  # noqa: BLE001 - the refusal type is the assertion
        return None, type(caught).__name__
    return _arm_named(resolved) or "<unknown wiring>", None


@pytest.mark.parametrize(
    "capability",
    [["writes_artifact"], ["writes_graph"], ["writes_vector"], ["writes_kv"]],
    ids=lambda capability: capability[0],
)
def test_write_capabilities_never_select_a_read_only_query_arm(capability):
    arm, caught = _select(capability)
    assert caught == UnsatisfiableSelectorError.__name__, (
        f"{capability} must be refused (no query wiring writes); it selected arm {arm!r}"
        if arm is not None
        else f"{capability} raised {caught}, expected UnsatisfiableSelectorError"
    )


@pytest.mark.parametrize(
    ("capability", "expected_arm"),
    [
        (["reads_vector"], "naive"),
        (["reads_graph"], "hipporag"),
        (["reads_graph", "calls_rerank"], "local"),
        (["calls_llm"], "bypass"),
    ],
    ids=["reads_vector", "reads_graph", "reads_graph+calls_rerank", "calls_llm"],
)
def test_read_capabilities_select_the_same_arms_as_before(capability, expected_arm):
    arm, caught = _select(capability)
    assert (arm, caught) == (expected_arm, None), f"{capability} -> {(arm, caught)}"


def test_the_effect_set_matching_uses_for_every_arm():
    registry = default_registry()
    wirings = all_wirings()
    assert {name for name, _ in wirings} == set(_EFFECTS_PER_ARM), "table must cover every arm"
    for name, resolved in wirings:
        effects = _wiring_effects(without_recipe_only_nodes(resolved), registry)
        assert effects == _EFFECTS_PER_ARM[name], f"{name}: {sorted(effects)}"
