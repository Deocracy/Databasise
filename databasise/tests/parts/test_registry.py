"""Tests for D-13's explicit part registry (parts/registry.py) and D-04's three
declaration-only Falsifier-2 wiring entries (parts_core/declared_only.py).
"""

from __future__ import annotations

import pytest
from databasise.parts.registry import (
    DeclarationOnlyPartError,
    DuplicatePartError,
    UnknownPartError,
    default_registry,
    dispatch,
)
from databasise.parts.schema import NodeContext


def test_default_registry_holds_exactly_fourteen_entries():
    """D-04's seven Phase-1 entries (four executable ``parts_core`` reference parts, three
    declaration-only Falsifier-2 wiring placeholders) plus 03-04-PLAN.md Task 2's seven ported
    LightRAG parts — this count grows again once plan 03-05/03-06 ports the remaining eight
    base-wiring positions, per design, not a regression.
    """
    registry = default_registry()
    assert len(registry.keys()) == 14


def test_get_on_an_unknown_key_raises_with_the_requested_key_quoted_in_the_message():
    registry = default_registry()
    with pytest.raises(UnknownPartError) as exc_info:
        registry.get("nonexistent/part@9.9.9")
    assert "'nonexistent/part@9.9.9'" in str(exc_info.value)


def test_register_refuses_a_duplicate_key_rather_than_overwriting_it():
    registry = default_registry()
    existing_key = registry.keys()[0]
    existing_part = registry.get(existing_key)
    with pytest.raises(DuplicatePartError):
        registry.register(existing_part)


def test_the_three_declaration_only_entries_have_no_body_and_a_non_empty_upstream_ref():
    registry = default_registry()
    declaration_only = [
        registry.get(key) for key in registry.keys() if registry.get(key).body is None  # noqa: SIM118 — PartRegistry.keys() is not a dict; `in registry` is not a defined operation
    ]
    assert len(declaration_only) == 3
    assert all(part.upstream_ref for part in declaration_only)


async def test_dispatching_a_declaration_only_part_raises_naming_the_part_not_a_null_result():
    registry = default_registry()
    declaration_only_part = next(
        registry.get(key) for key in registry.keys() if registry.get(key).body is None  # noqa: SIM118 — PartRegistry.keys() is not a dict; `in registry` is not a defined operation
    )
    ctx = NodeContext(node_id="n1", config=None, inputs={}, stores={})

    with pytest.raises(DeclarationOnlyPartError) as exc_info:
        await dispatch(declaration_only_part, ctx)

    assert declaration_only_part.name_at_version in str(exc_info.value)
