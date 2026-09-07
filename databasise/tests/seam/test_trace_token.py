"""04-04-PLAN.md Task 1: a caller exchanges an opaque trace reference for the run's node-by-node
trace. Mirrors ``databasise/tests/parity/test_naive_arm_end_to_end.py``'s synthetic-store/
stub-client pattern (no network, no imported parity index) but drives
``databasise.seam.Databasise.query()``/``resolve_trace()``.
"""

from __future__ import annotations

import pytest

from databasise.clients.base import ChatResult, EmbeddingResult
from databasise.runner.trace import TokenAccounting
from databasise.seam import Databasise, QueryObject
from databasise.seam.trace_store import UnknownTraceReferenceError

_STUB_COMPLETION = "This is a stub completion for the trace-token test."
_QUERY_TEXT = "Which films did Ed Wood direct?"


class _StubEmbeddingClient:
    def __init__(self, vector: list[float]):
        self.vector = vector

    async def embed(self, texts, **kwargs):
        return EmbeddingResult(
            vectors=[self.vector for _ in texts],
            tokens=TokenAccounting(prompt_tokens=len(texts), call_count=1, counted_by="stub-embed"),
            resolved_model_identity="stub-embed-model",
        )


class _StubLLMClient:
    async def chat(self, messages, **kwargs):
        return ChatResult(
            text=_STUB_COMPLETION,
            tokens=TokenAccounting(
                prompt_tokens=5, completion_tokens=4, call_count=1, counted_by="stub-llm"
            ),
            resolved_model_identity="stub-llm-model",
        )


def _make_engine(synthetic_naive_store) -> Databasise:
    return Databasise(
        store_root=synthetic_naive_store["store_root"],
        workspace=synthetic_naive_store["workspace"],
        clients={
            "embedding": _StubEmbeddingClient(vector=synthetic_naive_store["query_vector"]),
            "llm": _StubLLMClient(),
        },
    )


def _forbidden_identities(record: dict) -> set[str]:
    """Built from the resolved run record's own fields at test time — never a literal restated
    here — per this task's own opacity-assertion requirement."""
    forbidden = {
        record["run_id"],
        record["wiring_id"],
        record["wiring_instance_hash"],
        record["arm_id"],
    }
    for node in record["nodes"]:
        forbidden.add(node["node_id"])
        forbidden.add(node["instance_hash"])
    return forbidden


async def test_the_trace_reference_reveals_none_of_the_runs_own_identities(synthetic_naive_store):
    engine = _make_engine(synthetic_naive_store)

    envelope = await engine.query(QueryObject(text=_QUERY_TEXT))
    assert envelope.trace_token

    debug_record = await engine.resolve_trace(envelope.trace_token, debug=True)
    forbidden = _forbidden_identities(debug_record)

    assert envelope.trace_token not in forbidden
    for value in forbidden:
        assert value not in envelope.trace_token, f"{value!r} leaked into the trace reference"
        assert envelope.trace_token not in value, "the trace reference leaked into an identity value"


async def test_exchanging_the_reference_with_debug_returns_the_runs_own_node_entries(
    synthetic_naive_store,
):
    engine = _make_engine(synthetic_naive_store)

    envelope = await engine.query(QueryObject(text=_QUERY_TEXT))
    debug_record = await engine.resolve_trace(envelope.trace_token, debug=True)

    assert debug_record["nodes"]
    node_ids = {node["node_id"] for node in debug_record["nodes"]}
    assert node_ids == {
        "embedder-query",
        "chunk-vector",
        "heading-backfill",
        "rerank",
        "assemble",
        "generate",
        "embedder-index",
    }


async def test_exchanging_the_reference_without_debug_carries_no_node_level_entry(
    synthetic_naive_store,
):
    engine = _make_engine(synthetic_naive_store)

    envelope = await engine.query(QueryObject(text=_QUERY_TEXT))
    non_debug_record = await engine.resolve_trace(envelope.trace_token, debug=False)

    assert "nodes" not in non_debug_record
    assert non_debug_record["partial"] is False


async def test_an_unknown_trace_reference_raises_the_named_refusal(synthetic_naive_store):
    engine = _make_engine(synthetic_naive_store)

    with pytest.raises(UnknownTraceReferenceError):
        await engine.resolve_trace("this-token-was-never-minted", debug=True)


async def test_a_reference_minted_by_one_instance_resolves_through_a_second_instance_same_store_root(
    synthetic_naive_store,
):
    first_engine = _make_engine(synthetic_naive_store)
    envelope = await first_engine.query(QueryObject(text=_QUERY_TEXT))

    second_engine = _make_engine(synthetic_naive_store)
    debug_record = await second_engine.resolve_trace(envelope.trace_token, debug=True)

    assert debug_record["nodes"]


async def test_two_runs_of_the_same_query_mint_two_different_references_each_resolving_to_its_own_record(
    synthetic_naive_store,
):
    engine = _make_engine(synthetic_naive_store)

    envelope_1 = await engine.query(QueryObject(text=_QUERY_TEXT))
    envelope_2 = await engine.query(QueryObject(text=_QUERY_TEXT))

    assert envelope_1.trace_token != envelope_2.trace_token

    record_1 = await engine.resolve_trace(envelope_1.trace_token, debug=True)
    record_2 = await engine.resolve_trace(envelope_2.trace_token, debug=True)
    assert record_1["run_id"] != record_2["run_id"]


async def test_the_trace_database_is_created_beside_the_ledger_database_under_the_store_root(
    synthetic_naive_store,
):
    engine = _make_engine(synthetic_naive_store)
    await engine.query(QueryObject(text=_QUERY_TEXT))

    trace_db = synthetic_naive_store["store_root"] / "trace.db"
    assert trace_db.exists()
