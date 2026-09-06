"""04-03-PLAN.md: the §18.4 selectors — the capability branch (Task 1), the alias branch
(Task 2), the harness branch and the default selector's opaque exclusion, plus the §18.5
falsifier check (Task 3).
"""

from __future__ import annotations

from unittest.mock import patch

import pydantic
import pytest

from databasise.clients.base import ChatResult
from databasise.parts.registry import default_registry
from databasise.runner.trace import TokenAccounting
from databasise.seam import selectors
from databasise.seam.engine import Databasise
from databasise.seam.query import QueryObject
from databasise.seam.refusals import UnsatisfiableSelectorError
from databasise.seam.selectors import Selector
from databasise.validator.parse import ParsedWiring, parse_wiring
from databasise.wirings.resolve import resolve_arm

_ARM_NAMES: tuple[str, ...] = ("naive", "bypass", "hybrid", "local", "global")
_ALL_NODE_IDS: set[str] = set().union(
    *(set(resolve_arm(name).get("nodes", {}).keys()) for name in _ARM_NAMES)
)


class _StubLLMClient:
    def __init__(self, text: str):
        self.text = text

    async def chat(self, messages, **kwargs):
        return ChatResult(
            text=self.text,
            tokens=TokenAccounting(prompt_tokens=1, completion_tokens=1, call_count=1, counted_by="stub-llm"),
            resolved_model_identity="stub-llm-model",
        )


# --------------------------------------------------------------------------------------------- #
# Task 1: the capability selector
# --------------------------------------------------------------------------------------------- #

_BYPASS_COMPLETION = "This is the bypass arm's own stub completion for the capability selector test."


async def test_a_capability_selector_resolves_to_a_wiring_and_returns_a_real_envelope(tmp_path):
    engine = Databasise(
        store_root=tmp_path,
        workspace="capability-test",
        clients={"llm": _StubLLMClient(_BYPASS_COMPLETION)},
    )

    envelope = await engine.query(
        QueryObject(text="does not matter, bypass ignores context"),
        Selector(capability=["calls_llm"]),
    )

    # Real value, never shape alone: the stub client's own configured completion text, proving
    # the capability selector actually reached (and ran) the bypass arm, the smallest of the
    # arms whose registered parts declare calls_llm.
    assert envelope.answer == _BYPASS_COMPLETION


def test_an_unsatisfiable_capability_selector_raises_and_never_falls_through_to_the_default():
    registry = default_registry()

    with patch.object(selectors, "_resolve_default") as spy_default:
        with pytest.raises(UnsatisfiableSelectorError) as exc_info:
            selectors.resolve_selector(Selector(capability=["fs"]), registry=registry)

    spy_default.assert_not_called()
    assert exc_info.value.selector_kind == "capability"


def test_the_unsatisfiable_capability_refusal_discloses_no_candidate_wiring_or_node_id():
    registry = default_registry()
    all_wiring_ids = {resolve_arm(name).get("wiring_id", name) for name in _ARM_NAMES}

    with pytest.raises(UnsatisfiableSelectorError) as exc_info:
        selectors.resolve_selector(Selector(capability=["fs"]), registry=registry)

    message = str(exc_info.value)
    for node_id in _ALL_NODE_IDS:
        assert node_id not in message
    for wiring_id in all_wiring_ids:
        assert wiring_id not in message


@pytest.mark.parametrize(
    "kwargs",
    [
        {"alias": "a" * 64},
        {"alias": "sha256:" + "b" * 64},
        {"harness": "c" * 64},
        {"capability": ["d" * 64]},
    ],
)
def test_an_instance_hash_shaped_selector_value_raises_validation_error(kwargs):
    with pytest.raises(pydantic.ValidationError):
        Selector(**kwargs)


def test_selectors_reads_provides_and_harnesses_off_the_raw_resolved_dict_never_parsed_wiring():
    resolved = resolve_arm("bypass")
    registry = default_registry()
    parsed = parse_wiring(resolved, registry)

    # The raw dict carries these fields...
    assert "provides" in resolved
    assert "harnesses" in resolved
    # ...but ParsedWiring never does — a future refactor toward the validator's own snapshot
    # would fail loudly here rather than silently losing these fields (Pitfall 1).
    assert not hasattr(parsed, "provides")
    assert not hasattr(parsed, "harnesses")
    assert set(ParsedWiring.__dataclass_fields__) == {"nodes", "parts", "deps", "node_order", "report"}
