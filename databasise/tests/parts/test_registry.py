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


def test_default_registry_holds_exactly_thirty_three_entries():
    """D-04's six remaining Phase-1 entries (four executable ``parts_core`` reference parts, two
    declaration-only Falsifier-2 wiring placeholders — 03-08-PLAN.md Task 3 retired the third,
    ``lightrag/query-side`` (version ``0.1.0``), once Phase 3 ported its real eighteen positions)
    plus
    03-04-PLAN.md Task 2's seven ported LightRAG parts plus 03-05-PLAN.md's five graph-half parts
    (``keywords``, ``entity-lookup``, ``relation-lookup``, ``entity-hydrate-expand``,
    ``relation-hydrate-expand``) plus 03-06-PLAN.md's three remaining base-wiring components
    (``join-roundrobin``, ``truncator-token-budget``, ``chunk-selector-kg``) plus 05-03-PLAN.md
    Task 1's ``lightrag/full-delete@0.1.0`` (the second, separately-admitted port of the same
    corpus-side engine ``lightrag/full-ingest@0.1.0`` already registers) plus 05-06-PLAN.md's
    ``codebase-memory-mcp@0.1.0`` opaque part — twenty-two entries, the Phase 3/5 count — plus
    06-01-PLAN.md's five ported HippoRAG parts (``fact-score``, ``fact-filter``,
    ``reset-vector-join``, ``ppr``, ``assemble-result``): twenty-seven, the Phase 6 Plan 1 count —
    plus 06-02-PLAN.md's three ported HippoRAG index-side parts (``chunk-embed``, ``openie``,
    ``entity-fact-embed``): thirty, the Phase 6 Plan 2 count — plus 06-05-PLAN.md Task 1's
    two pure edge-transform parts (``fact-edges``, ``passage-edges``): thirty-two — plus
    Task 2's ``hipporag/synonymy-edge-builder@0.1.0``: thirty-three.
    """
    registry = default_registry()
    assert len(registry.keys()) == 33


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


def test_no_declaration_only_entries_remain():
    """05-06-PLAN.md Task 2 gave ``codebase-memory-mcp@0.1.0`` a real body and a real §8
    admission record — the last of D-04's three original Falsifier-2 wiring placeholders is now
    executable. Every entry ``default_registry()`` holds carries a real body."""
    registry = default_registry()
    declaration_only = [
        registry.get(key) for key in registry.keys() if registry.get(key).body is None  # noqa: SIM118 — PartRegistry.keys() is not a dict; `in registry` is not a defined operation
    ]
    assert declaration_only == []


async def test_dispatching_a_declaration_only_part_raises_naming_the_part_not_a_null_result():
    """No production entry is declaration-only anymore (see the test above) — this exercises
    ``dispatch()``'s own refusal directly against a synthetic ``body=None`` Part rather than
    depending on a real registry entry staying unexecuted."""
    from databasise.parts.schema import Part

    declaration_only_part = Part(
        name_at_version="test/declaration-only@1.0.0",
        kind="passthrough",
        structural_depth="stage",
        effects=[],
        upstream_ref="test-fixture",
        body=None,
    )
    ctx = NodeContext(node_id="n1", config=None, inputs={}, stores={})

    with pytest.raises(DeclarationOnlyPartError) as exc_info:
        await dispatch(declaration_only_part, ctx)

    assert declaration_only_part.name_at_version in str(exc_info.value)
