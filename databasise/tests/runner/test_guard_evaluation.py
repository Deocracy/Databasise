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
        "signal": "flag",
    }
    return {**entry, **overrides}


def _parsed(ran: list[str], guards, output=None) -> ParsedWiring:
    """root <- guarded <- downstream, plus an unrelated same-batch sibling of ``guarded``."""
    deps = {"root": (), _GUARDED: ("root",), "sibling": ("root",), "downstream": (_GUARDED,)}

    async def body(ctx: NodeContext):
        ran.append(ctx.node_id)
        return {"flag": False} if output is None else output

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
        {
            "guard_name": "g",
            "evaluating_node": _GUARDED,
            "value_when_not_fired": False,
            "granularity": "per-query",
            "signal": "flag",
        },
        {"name": "g", "evaluating_node": _GUARDED, "value_when_not_fired": False, "signal": "flag"},
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


# --------------------------------------------------------------------------------------------- #
# WIRE-08 (D-19): a guard reads one declared boolean signal of the evaluating node's output
# --------------------------------------------------------------------------------------------- #


def _signal_guard(**overrides) -> dict:
    return _guard(_GUARDED, **overrides)


def _guard_trace(result: dict, node_id: str = _GUARDED):
    return next(trace for trace in result["nodes"] if trace.node_id == node_id)


@pytest.mark.parametrize(("output", "fires"), [({"flag": True}, True), ({"flag": False}, False)])
async def test_a_declared_signal_fires_only_on_its_value(output, fires):
    result, exc = await _run(_parsed([], [_signal_guard()], output=output))

    assert exc is None, repr(exc)
    assert result is not None
    assert _guard_trace(result).guards_fired == (["g"] if fires else [])


async def test_a_plain_dict_output_without_the_signal_does_not_fire():
    result, exc = await _run(_parsed([], [_signal_guard()], output={"x": 1}))

    assert exc is None, repr(exc)
    assert result is not None
    assert "g" not in _guard_trace(result).guards_fired
    assert _guard_trace(result).status == "failed"
    caught = result["node_exceptions"].get(_GUARDED)
    assert type(caught).__name__ == "GuardDeclarationError", repr(caught)
    assert getattr(caught, "node_id", None) == _GUARDED


async def test_a_non_mapping_output_does_not_fire():
    result, exc = await _run(_parsed([], [_signal_guard()], output=True))

    assert exc is None, repr(exc)
    assert result is not None
    assert _guard_trace(result).guards_fired == []
    assert type(result["node_exceptions"].get(_GUARDED)).__name__ == "GuardDeclarationError"


async def test_no_guards_means_none_fired():
    for guards in ([], None):
        result, exc = await _run(_parsed([], guards))

        assert exc is None, repr(exc)
        assert result is not None
        assert _guard_trace(result).guards_fired == [], guards


async def test_fired_guards_keep_declaration_order():
    guards = [_signal_guard(name="second-declared-first"), _signal_guard(name="a-first-by-name")]

    result, exc = await _run(_parsed([], guards, output={"flag": True}))

    assert exc is None, repr(exc)
    assert result is not None
    assert _guard_trace(result).guards_fired == ["second-declared-first", "a-first-by-name"]


async def test_a_four_key_entry_is_refused_by_name():
    ran: list[str] = []
    entry = {key: value for key, value in _signal_guard().items() if key != "signal"}

    _, exc = await _run(_parsed(ran, [entry]))

    _assert_guard_refusal(exc, ran)


async def test_a_bad_granularity_is_still_the_refusal_when_the_signal_is_missing():
    guards = pytest.importorskip("databasise.runner.guards")
    try:
        guards.declare_guard(name="g", evaluating_node="n", value_when_not_fired=True, granularity="sometimes")
    except Exception as exc:  # noqa: BLE001 - asserted on below
        caught = exc
    else:
        caught = None

    assert type(caught).__name__ == "GuardDeclarationError", repr(caught)
    assert "granularity" in str(caught)
