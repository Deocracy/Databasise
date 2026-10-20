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


class _EmptyDistInfo:
    """An interrupted install's empty ``*.dist-info``: no metadata, so ``version`` is None."""

    metadata = {"Name": "broken"}
    version = None

    def read_text(self, _name):
        return None


@pytest.fixture
def broken_environment(monkeypatch):
    from databasise.identity import env

    monkeypatch.setattr(env, "distributions", lambda: [_EmptyDistInfo()])
    env.environment_hash.cache_clear()
    yield env
    env.environment_hash.cache_clear()  # the real environment's digest is recomputed by the next caller


def test_an_uncollectable_environment_is_an_environment_digest_error(broken_environment):
    """A-WR-03: the TypeError from a None version surfaces as the named error, and is not memoised."""
    with pytest.raises(broken_environment.EnvironmentDigestError):
        broken_environment.environment_hash()
    assert broken_environment.environment_hash.cache_info().currsize == 0


async def test_an_uncollectable_environment_refuses_a_query_as_environment_digest_unavailable(
    store_root, broken_environment
):
    """A-WR-03 (D-22): the query path answers the 503 ForeignEngineRefusalError, never a bare TypeError."""
    wiring = {"nodes": {"a": _node()}, "provides": ["a"]}
    with pytest.raises(ForeignEngineRefusalError) as exc_info:
        await _run_resolved(store_root, PartRegistry(), wiring)
    assert exc_info.value.failure_class == "EnvironmentDigestUnavailable"


@pytest.mark.parametrize(
    ("extra", "code"),
    [
        ({"provides": [["a"]]}, "unknown-provides"),
        ({"provides": "a"}, "invalid-wiring-document"),
        ({"evidence_position": {"node": ["a"]}}, "unknown-evidence-node"),
        ({"evidence_position": "a"}, "invalid-wiring-document"),
    ],
)
def test_a_malformed_top_level_reference_is_reported_not_raised(extra, code):
    """B-WR-01 (WIRE-06): parse_wiring reports these shapes; it raised TypeError or accepted them."""
    from databasise.validator.parse import parse_wiring

    report = parse_wiring({"nodes": {"a": _node()}, **extra}, PartRegistry()).report
    assert code in [violation.code for violation in report.violations]


def _guard(**overrides):
    entry = {
        "name": "g",
        "evaluating_node": "a",
        "value_when_not_fired": False,
        "granularity": "per-query",
        "signal": "s",
    }
    return {**entry, **overrides}


@pytest.mark.parametrize(
    "guards",
    [5, "g", [_guard(evaluating_node=["a"])], [_guard(name=["g"])], [_guard(name=7)]],
    ids=["int", "string", "list-evaluating-node", "list-name", "int-name"],
)
async def test_a_malformed_guard_declaration_is_a_named_422_before_dispatch(store_root, guards):
    """B-WR-02 (WIRE-05, D-07): these shapes raised a bare TypeError (or stored a non-string name)."""
    from databasise.seam.refusals import InvalidGuardDeclarationError

    wiring = {"nodes": {"a": _node(config={"guards": guards})}, "provides": ["a"]}
    with pytest.raises(InvalidGuardDeclarationError) as exc_info:
        await _run_resolved(store_root, PartRegistry(), wiring)
    assert getattr(exc_info.value, "trace_token", None) is None  # pre-dispatch: no run, no trace
