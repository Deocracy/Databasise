"""13-02 (WIRE-16, D-10): the four advanced query members are refused for this contract version, and
no part declaration path can make them consumable."""

from __future__ import annotations

import typing

import pytest

from databasise.parts.registry import PartRegistry, default_registry
from databasise.parts.schema import Effect, Part
from databasise.seam import query as query_module
from databasise.seam.query import QueryObject, check_consumable

_ADVANCED_MEMBERS = [
    ("embedding", [1.0, 0.0, 0.0]),
    ("predicates", {"field": "value"}),
    ("profile_ref", "profile:abc"),
    ("formal_query", "SELECT * FROM x"),
]


def _part(name: str, effects: list) -> Part:
    return Part(name_at_version=name, kind="stage", structural_depth="stage", effects=effects, upstream_ref=None)


def _try_register(registry: PartRegistry, part: Part):
    try:
        registry.register(part)
    except Exception as exc:  # noqa: BLE001 - captured to assert on its type
        return exc
    return None


def test_an_effect_outside_the_literal_is_refused():
    registry = PartRegistry(seed_tracer_parts=False)
    error = _try_register(registry, _part("probe/space@0.1.0", ["reads_space"]))
    assert error is not None, "registration accepted an effect outside the Effect literal"
    assert isinstance(error, ValueError) and type(error) is not ValueError
    assert "probe/space@0.1.0" not in registry.keys()


@pytest.mark.parametrize("effect", typing.get_args(Effect))
def test_each_frozen_effect_registers(effect):
    registry = PartRegistry(seed_tracer_parts=False)
    assert _try_register(registry, _part("probe/ok@0.1.0", [effect])) is None
    assert registry.keys() == ["probe/ok@0.1.0"]


def test_no_effects_registers():
    registry = PartRegistry(seed_tracer_parts=False)
    assert _try_register(registry, _part("probe/none@0.1.0", [])) is None


def test_a_corrected_registration_succeeds_after_a_refusal():
    registry = PartRegistry(seed_tracer_parts=False)
    assert _try_register(registry, _part("probe/space@0.1.0", ["reads_space"])) is not None
    assert _try_register(registry, _part("probe/space@0.1.0", ["reads_kv"])) is None
    assert registry.keys() == ["probe/space@0.1.0"]


@pytest.mark.parametrize("member_name,value", _ADVANCED_MEMBERS)
def test_each_advanced_member_is_refused(member_name, value):
    try:
        check_consumable(QueryObject(**{member_name: value}), default_registry())
    except Exception as exc:  # noqa: BLE001
        assert type(exc).__name__ == "UnconsumableQueryMemberError"
        assert exc.member_name == member_name
    else:
        raise AssertionError(f"{member_name} was consumable")


def test_query_docstring_states_the_members_are_refused_for_this_contract_version():
    doc = query_module.__doc__ or ""
    assert "frozen" in doc
    assert "A later phase that registers" not in doc
    assert "by absence, not by permanent exclusion" not in doc
