"""WIRE-08 (D-19): a misdeclared guard is refused before any node is dispatched, with a
``GuardDeclarationError`` carrying the guarded node's id. A guard entry must be a mapping with exactly
the ``declare_guard`` keys, and its ``evaluating_node`` must be the guarded node itself or one of its
transitive dependencies (the node's output must exist when the guard is evaluated). 13-12 adds the
declared-signal legs.

Every test builds a ``ParsedWiring`` directly (the pattern ``test_scheduler.py`` documents). Exceptions
are captured and asserted on by type name, so the tests fail by assertion on code that predates the fix.
"""

from __future__ import annotations

import pytest

from databasise.parts.registry import PartRegistry
from databasise.parts.schema import NodeContext, Part, WiringNode
from databasise.runner import scheduler
from databasise.validator.errors import ValidationReport
from databasise.validator.parse import ParsedWiring

_GUARDED = "guarded"


def _guard(evaluating_node: str, **overrides) -> dict:
    entry = {
        "name": "g",
        "evaluating_node": evaluating_node,
        "value_when_not_fired": False,
        "granularity": "per-query",
    }
    return {**entry, **overrides}


def _parsed(ran: list[str], guards) -> ParsedWiring:
    """root <- guarded <- downstream, plus an unrelated same-batch sibling of ``guarded``."""
    deps = {"root": (), _GUARDED: ("root",), "sibling": ("root",), "downstream": (_GUARDED,)}

    async def body(ctx: NodeContext):
        ran.append(ctx.node_id)
        return False

    parts = {
        node_id: Part(
            name_at_version=f"test/{node_id}@1.0.0",
            kind="passthrough",
            structural_depth="stage",
            effects=[],
            upstream_ref=None,
            body=body,
        )
        for node_id in deps
    }
    nodes = {
        node_id: WiringNode(
            component=parts[node_id].name_at_version,
            kind="passthrough",
            config={"guards": guards} if node_id == _GUARDED else None,
            deps=list(deps[node_id]),
        )
        for node_id in deps
    }
    return ParsedWiring(
        nodes=nodes,
        parts=parts,
        deps=deps,
        node_order=tuple(sorted(nodes)),
        report=ValidationReport(),
    )


async def _run(parsed: ParsedWiring) -> tuple[dict | None, Exception | None]:
    try:
        result = await scheduler.run_wiring(
            parsed, PartRegistry(), {}, determinism_setting="cache-bypassed", concurrency_setting="sequential"
        )
    except Exception as exc:  # noqa: BLE001 - the test asserts on the captured type
        return None, exc
    return result, None


def _assert_guard_refusal(exc: Exception | None, ran: list[str]) -> None:
    assert type(exc).__name__ == "GuardDeclarationError", repr(exc)
    assert getattr(exc, "node_id", None) == _GUARDED, repr(exc)
    assert ran == [], f"nodes ran before the refusal: {ran}"


@pytest.mark.parametrize("evaluating_node", ["downstream", "sibling", "no-such-node"])
async def test_a_misplaced_evaluating_node_is_refused_before_dispatch(evaluating_node):
    ran: list[str] = []

    _, exc = await _run(_parsed(ran, [_guard(evaluating_node)]))

    _assert_guard_refusal(exc, ran)


@pytest.mark.parametrize("evaluating_node", [_GUARDED, "root"])
async def test_an_evaluating_node_that_is_the_guarded_node_or_an_ancestor_is_accepted(evaluating_node):
    ran: list[str] = []

    result, exc = await _run(_parsed(ran, [_guard(evaluating_node)]))

    assert exc is None, repr(exc)
    assert result is not None and result["partial"] is False
    assert _GUARDED in ran


@pytest.mark.parametrize(
    "entry",
    [
        {"guard_name": "g", "evaluating_node": _GUARDED, "value_when_not_fired": False, "granularity": "per-query"},
        {"name": "g", "evaluating_node": _GUARDED, "value_when_not_fired": False},
        {**_guard(_GUARDED), "extra": 1},
        "g",
    ],
    ids=["renamed-key", "missing-key", "extra-key", "not-a-mapping"],
)
async def test_a_guard_entry_with_wrong_keys_is_refused_by_name(entry):
    ran: list[str] = []

    _, exc = await _run(_parsed(ran, [entry]))

    _assert_guard_refusal(exc, ran)


async def test_an_inadmissible_granularity_is_refused_with_the_guarded_node():
    ran: list[str] = []

    _, exc = await _run(_parsed(ran, [_guard(_GUARDED, granularity="")]))

    _assert_guard_refusal(exc, ran)
