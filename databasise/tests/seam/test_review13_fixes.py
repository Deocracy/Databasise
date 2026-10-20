"""Phase 13 code-review fixes (13-REVIEW.md): regression tests for the Warning findings.

Kept in a new file because the tests that cover the neighbouring behaviour are ledger-protected.
No network, no v1 artifacts, no live client.
"""

from __future__ import annotations

import pytest

from databasise.parts.registry import PartRegistry
from databasise.parts.schema import Part
from databasise.seam import Databasise, QueryObject
from databasise.seam.refusals import ForeignEngineRefusalError, MutableStoreComparisonExcludedError, refusal_body

_PASSTHROUGH = "core/passthrough@1.0.0"


def _node(component: str = _PASSTHROUGH, **extra):
    return {"component": component, "kind": "passthrough", "deps": [], **extra}


def _registry_with_body(name: str, body) -> PartRegistry:
    registry = PartRegistry()  # the tracer passthrough plus the injected part
    registry.register(
        Part(name_at_version=name, kind="passthrough", structural_depth="stage", effects=[], upstream_ref=None, body=body)
    )
    return registry


async def _run_resolved(store_root, registry: PartRegistry, wiring: dict):
    engine = Databasise(store_root=store_root, workspace="review13-ws", registry=registry)
    return await engine._execute_resolved(QueryObject(text="q"), wiring)


def test_the_mutable_store_refusal_names_the_capability_not_the_part():
    """A-WR-01 (D-15, §18.3): the public body carries ``mutates_store``; the part name stays private."""
    part = "codebase-memory-mcp/indexer@1.2.3"
    body = refusal_body(MutableStoreComparisonExcludedError(component=part))
    assert body["component"] == "mutates_store"
    assert "codebase-memory-mcp" not in repr(body)


@pytest.mark.parametrize("items", [None, ["chunk-1"], {"id": "chunk-1"}, "chunk-1"])
async def test_a_malformed_items_value_is_malformed_driver_output_with_a_trace(store_root, items):
    """A-WR-02 (D-09, D-04): ``items`` that is not a list of mappings is a named fault, not a bare
    TypeError or AttributeError, and the persisted run's trace_token rides on the refusal."""

    async def body(ctx):
        return {"items": items}

    registry = _registry_with_body("review13/items@1.0.0", body)
    wiring = {
        "nodes": {"retrieve": _node("review13/items@1.0.0")},
        "evidence_position": {"node": "retrieve", "namespace": "chunks"},
    }
    with pytest.raises(ForeignEngineRefusalError) as exc_info:
        await _run_resolved(store_root, registry, wiring)
    assert exc_info.value.failure_class == "MalformedDriverOutput"
    assert exc_info.value.trace_token
