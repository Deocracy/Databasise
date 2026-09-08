"""Tests for D-13's explicit part registry (parts/registry.py) and D-04's two remaining
declaration-only Falsifier-2 wiring entries (parts_core/declared_only.py) — 03-08-PLAN.md Task 3
retired the third, ``lightrag/query-side`` (version ``0.1.0``).
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


def test_default_registry_holds_exactly_twenty_one_entries():
    """D-04's six remaining Phase-1 entries (four executable ``parts_core`` reference parts, two
    declaration-only Falsifier-2 wiring placeholders — 03-08-PLAN.md Task 3 retired the third,
    ``lightrag/query-side`` (version ``0.1.0``), once Phase 3 ported its real eighteen positions)
    plus
    03-04-PLAN.md Task 2's seven ported LightRAG parts plus 03-05-PLAN.md's five graph-half parts
    (``keywords``, ``entity-lookup``, ``relation-lookup``, ``entity-hydrate-expand``,
    ``relation-hydrate-expand``) plus 03-06-PLAN.md's three remaining base-wiring components
    (``join-roundrobin``, ``truncator-token-budget``, ``chunk-selector-kg``) — this is by design
    the final count: all eighteen §L.1 positions resolve against a registered part, and the stub
    they superseded is gone.
    """
    registry = default_registry()
    assert len(registry.keys()) == 21


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


def test_the_one_remaining_declaration_only_entry_has_no_body_and_a_non_empty_upstream_ref():
    """05-01-PLAN.md Task 1 gave ``lightrag/full-ingest@0.1.0`` a real body and a real §8
    admission record — ``codebase-memory-mcp@0.1.0`` is now the only remaining declaration-only
    entry, until plan 05-06 admits it too."""
    registry = default_registry()
    declaration_only = [
        registry.get(key) for key in registry.keys() if registry.get(key).body is None  # noqa: SIM118 — PartRegistry.keys() is not a dict; `in registry` is not a defined operation
    ]
    assert len(declaration_only) == 1
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
