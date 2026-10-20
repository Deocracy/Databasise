"""WIRE-12 (D-17): a run that records ``concurrency_setting: sequential`` runs one node body at a
time. This file holds the concurrency leg; later plans add the identity and trace_token legs.
"""

from __future__ import annotations

import asyncio

import pytest
from databasise.clients.base import ChatResult, EmbeddingResult
from databasise.parts.registry import PartRegistry, default_registry
from databasise.parts.schema import NodeContext, Part, WiringNode
from databasise.runner import scheduler
from databasise.runner.trace import TokenAccounting
from databasise.seam import Databasise, QueryObject
from databasise.seam.selectors import Selector
from databasise.tests.seam._probes import trace_row_count
from databasise.validator.errors import ValidationReport
from databasise.validator.parse import ParsedWiring


async def test_a_sequential_run_never_has_two_node_bodies_in_flight():
    in_flight = {"current": 0, "peak": 0}

    async def body(ctx: NodeContext):
        in_flight["current"] += 1
        in_flight["peak"] = max(in_flight["peak"], in_flight["current"])
        await asyncio.sleep(0.02)
        in_flight["current"] -= 1
        return {}

    part = Part(
        name_at_version="test/counter@1.0.0",
        kind="passthrough",
        structural_depth="stage",
        effects=[],
        upstream_ref=None,
        body=body,
    )
    nodes = {n: WiringNode(component="test/counter@1.0.0", kind="passthrough", deps=[]) for n in ("one", "two")}
    parsed = ParsedWiring(
        nodes=nodes,
        parts={n: part for n in nodes},
        deps={n: () for n in nodes},
        node_order=("one", "two"),
        report=ValidationReport(),
    )

    result = await scheduler.run_wiring(
        parsed, PartRegistry(), {}, determinism_setting="cache-bypassed", concurrency_setting="sequential"
    )

    assert len(result["nodes"]) == 2
    assert in_flight["peak"] == 1


# --------------------------------------------------------------------------------------------- #
# WIRE-12 (D-04): a post-dispatch query refusal leaves a resolvable trace
# --------------------------------------------------------------------------------------------- #


class _UnbudgetableEmbeddingClient:
    async def embed(self, texts, **kwargs):
        return EmbeddingResult(
            vectors=[[1.0, 0.0, 0.0] for _ in texts],
            tokens=TokenAccounting(counted_by="unbudgetable"),
            resolved_model_identity="opaque-engine",
        )


class _PlainLLMClient:
    async def chat(self, messages, **kwargs):
        return ChatResult(
            text="stub completion",
            tokens=TokenAccounting(prompt_tokens=5, completion_tokens=4, call_count=1, counted_by="stub-llm"),
            resolved_model_identity="stub-llm-model",
        )


def _clients() -> dict[str, object]:
    return {"embedding": _UnbudgetableEmbeddingClient(), "llm": _PlainLLMClient()}


async def _outcome(awaitable):
    """``(result, exception)`` of awaiting ``awaitable``; never raises."""
    try:
        return await awaitable, None
    except Exception as exc:  # noqa: BLE001 - the assertions name what was caught
        return None, exc


def _rows(store_root) -> int:
    return trace_row_count(store_root) if (store_root / "trace.db").exists() else 0


async def test_an_unbudgetable_refusal_leaves_a_resolvable_trace(synthetic_naive_store):
    store = synthetic_naive_store
    engine = Databasise(store_root=store["store_root"], workspace=store["workspace"], clients=_clients())
    rows_before = _rows(store["store_root"])

    _result, caught = await _outcome(engine.query(QueryObject(text="anything")))

    assert type(caught).__name__ == "UnbudgetableParticipantError", caught
    token = getattr(caught, "trace_token", None)
    assert isinstance(token, str), f"the refusal carries no trace_token: {vars(caught)}"
    record = await engine.resolve_trace(token, debug=True)
    assert record["nodes"], "the resolved run carries no node traces"
    assert _rows(store["store_root"]) == rows_before + 1


async def test_the_trace_token_reaches_the_rest_body(synthetic_naive_store):
    pytest.importorskip("fastapi")
    from databasise.seam.rest import create_app
    from fastapi.testclient import TestClient

    store = synthetic_naive_store
    client = TestClient(
        create_app(store_root=store["store_root"], workspace=store["workspace"], clients=_clients())
    )

    response = client.post("/query", json={"query": {"text": "anything"}})

    assert response.status_code == 422, response.text
    token = response.json().get("trace_token")
    assert isinstance(token, str), response.text
    resolved = client.post("/trace/resolve", json={"trace_reference": token, "debug": False})
    assert resolved.status_code == 200, resolved.text


async def test_a_pre_dispatch_refusal_carries_no_trace_token(store_root):
    engine = Databasise(store_root=store_root, workspace="no-token", clients=_clients())

    _result, caught = await _outcome(engine.query(QueryObject(text="x"), Selector(capability=["reads_vector"])))

    assert caught is not None, "an empty namespace must be refused"
    assert not hasattr(caught, "trace_token"), vars(caught)


# --------------------------------------------------------------------------------------------- #
# WIRE-12 (D-04): two answering provides nodes are a named refusal that still carries its trace
# --------------------------------------------------------------------------------------------- #


def _answering_registry() -> PartRegistry:
    """The default registry plus ``test/answer``, a passthrough part that returns a completion."""
    registry = default_registry()

    async def body(ctx: NodeContext):
        return {"completion": f"answer from {ctx.node_id}"}

    registry.register(
        Part(
            name_at_version="test/answer@1.0.0",
            kind="passthrough",
            structural_depth="stage",
            effects=[],
            upstream_ref=None,
            body=body,
        )
    )
    return registry


def _two_answers_wiring() -> dict:
    node = {"component": "test/answer@1.0.0", "kind": "passthrough", "deps": []}
    return {
        "nodes": {"first-answer": dict(node), "second-answer": dict(node)},
        "provides": ["first-answer", "second-answer"],
    }


async def test_two_answering_provides_nodes_are_refused_with_a_trace(tmp_path, monkeypatch):
    pytest.importorskip("fastapi")
    from databasise.seam import engine as engine_module
    from databasise.seam.rest import create_app
    from fastapi.testclient import TestClient

    monkeypatch.setattr(engine_module, "resolve_selector", lambda *a, **kw: _two_answers_wiring())
    engine = Databasise(store_root=tmp_path, workspace="two-answers", clients={}, registry=_answering_registry())

    _result, caught = await _outcome(engine.query(QueryObject(text="x")))

    assert type(caught).__name__ == "AmbiguousAnswerPositionError", repr(caught)
    token = getattr(caught, "trace_token", None)
    assert isinstance(token, str), vars(caught)
    assert (await engine.resolve_trace(token, debug=True))["nodes"]
    response = TestClient(
        create_app(store_root=tmp_path, workspace="two-answers", clients={}, registry=_answering_registry())
    ).post("/query", json={"query": {"text": "x"}})
    assert response.status_code == 422, response.text
    assert "first-answer" not in response.text and "second-answer" not in response.text


async def test_a_malformed_evidence_refusal_carries_a_trace_token(tmp_path):
    wiring = {
        "nodes": {"p": {"component": "parts-core/passthrough@1.0.0", "kind": "passthrough", "deps": []}},
        "provides": ["p"],
        "evidence_position": {"node": "p", "namespace": "chunks"},
    }
    engine = Databasise(store_root=tmp_path, workspace="malformed", clients={})

    _result, caught = await _outcome(engine._execute_resolved(QueryObject(text="x"), wiring))

    assert type(caught).__name__ == "ForeignEngineRefusalError", repr(caught)
    token = getattr(caught, "trace_token", None)
    assert isinstance(token, str), vars(caught)
    assert (await engine.resolve_trace(token, debug=True))["nodes"]
