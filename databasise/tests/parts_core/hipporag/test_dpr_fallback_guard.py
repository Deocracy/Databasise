"""06-07-PLAN.md: Task 1 (``dpr-fallback``, the thirteenth and final HippoRAG 2 base-wiring
position) and Task 2 (the ``zero_surviving_facts_dpr_fallback`` §19.8 guard, declared on
``fact-filter``, routing ``assemble-result`` between ``ppr`` and ``dpr-fallback``).

Task 1's own ``<verify>`` runs ``pytest -q tests/parts_core/hipporag/test_dpr_fallback_guard.py -x
-k dpr`` — every Task 1 test name below therefore carries ``dpr`` so that filter selects exactly
this task's own tests, mirroring 06-02/06-05's established RED/GREEN-per-task pattern within one
shared file.

Task 2's tests drive both guard branches through a real ``Databasise.query`` call against the
06-01-PLAN.md ``seeded_hipporag_store`` fixture, mirroring ``tests/seam/test_cross_modality_run.py``'s
stub-client/synthetic-store pattern exactly (no network, no imported parity index) — the fixture
already seeds both ``hipporag-facts``/``hipporag-chunks`` vectors and the KV chunk-content records
both branches need.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from databasise.clients.base import ChatResult, EmbeddingResult
from databasise.parts.schema import NodeContext
from databasise.parts_core.hipporag import dpr_fallback as dpr_fallback_module
from databasise.parts_core.hipporag import reset_vector_join as reset_vector_join_module
from databasise.parts_core.hipporag.dpr_fallback import (
    HIPPORAG_DPR_FALLBACK_PART,
    dense_passage_retrieval,
)
from databasise.runner.guards import GuardDeclarationError, declare_guard
from databasise.runner.trace import TokenAccounting
from databasise.seam import Databasise, QueryObject
from databasise.seam.selectors import Selector
from databasise.stores.vector import MultiNamespaceVectorStore
from databasise.wirings.resolve import load_wiring
from parts_core.hipporag.conftest import seeded_hipporag_store  # noqa: F401 — fixture import

_HIPPORAG_CAPABILITY = ["reads_graph", "reads_kv"]
_QUERY_TEXT = "What sat on the mat?"


def _ctx(node_id: str, config=None, inputs=None, stores=None, clients=None) -> NodeContext:
    return NodeContext(
        node_id=node_id,
        config=config or {},
        inputs=inputs or {},
        stores=stores or {},
        clients=clients or {},
    )


class _StubEmbeddingClient:
    def __init__(self, vector: list[float] | None = None) -> None:
        self.vector = vector or [1.0, 0.0, 0.0]
        self.calls: list[list[str]] = []

    async def embed(self, texts, **kwargs) -> EmbeddingResult:
        self.calls.append(list(texts))
        return EmbeddingResult(
            vectors=[self.vector for _ in texts],
            tokens=TokenAccounting(prompt_tokens=len(texts), call_count=1, counted_by="stub-embed"),
            resolved_model_identity="stub-embed-model",
        )


# --------------------------------------------------------------------------------------------- #
# Task 1: dpr-fallback (every test name below carries "dpr" for the -k filter)                    #
# --------------------------------------------------------------------------------------------- #


async def test_dpr_fallback_emits_text_chunk_items_for_every_stored_chunk_sorted_by_descending_score(
    store_root,
):
    # Faiss's own IndexFlatIP-over-L2-normalised-vectors index (stores/vector.py) makes cosine
    # similarity a function of direction only, never magnitude — these three vectors are chosen
    # at genuinely different angles from the query vector so their scores differ.
    vector_store = MultiNamespaceVectorStore(workspace="ws", store_root=store_root)
    chunks_ns = vector_store.select("hipporag-chunks")
    await chunks_ns.upsert(
        ids=["chunk:c1", "chunk:c2", "chunk:c3"],
        embeddings=np.array([[0.6, 0.8, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]),
        metadatas=[{}, {}, {}],
    )
    await vector_store.index_done_callback()

    client = _StubEmbeddingClient(vector=[1.0, 0.0, 0.0])
    ctx = _ctx(
        "dpr-fallback",
        config={"query": "cats on mats"},
        stores={"vector": vector_store},
        clients={"embedding": client},
    )

    result = await HIPPORAG_DPR_FALLBACK_PART.body(ctx)

    assert len(result["items"]) == 3
    assert all(item["kind"] == "text_chunk" for item in result["items"])
    ids = [item["id"] for item in result["items"]]
    assert ids == ["chunk:c2", "chunk:c1", "chunk:c3"]  # descending score, not a top-k truncation
    scores = [item["score"] for item in result["items"]]
    assert scores == sorted(scores, reverse=True)


async def test_dpr_fallback_scores_match_reset_vector_joins_own_passage_weight_scores(store_root):
    """Proves the shared-helper claim two ways: an identity check (reset_vector_join.py imports
    the exact same function object, never a re-implementation) and a behavioral check (dpr-fallback's
    own item scores equal the shared helper's raw scores for the same query/store — the same raw
    scores reset-vector-join's own passage-weight construction min-max normalises)."""
    assert reset_vector_join_module.dense_passage_retrieval is dpr_fallback_module.dense_passage_retrieval

    vector_store = MultiNamespaceVectorStore(workspace="ws", store_root=store_root)
    chunks_ns = vector_store.select("hipporag-chunks")
    await chunks_ns.upsert(
        ids=["chunk:c1", "chunk:c2"],
        embeddings=np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]),
        metadatas=[{}, {}],
    )
    await vector_store.index_done_callback()

    client = _StubEmbeddingClient(vector=[1.0, 0.0, 0.0])
    ctx = _ctx(
        "dpr-fallback",
        config={"query": "q"},
        stores={"vector": vector_store},
        clients={"embedding": client},
    )
    dpr_result = await HIPPORAG_DPR_FALLBACK_PART.body(ctx)
    dpr_scores = {item["id"]: item["score"] for item in dpr_result["items"]}

    raw_items, _ = await dense_passage_retrieval(
        embedding_client=client, chunks_store=chunks_ns, query="q"
    )
    raw_scores = {item["id"]: item["score"] for item in raw_items}

    assert dpr_scores == raw_scores


async def test_dpr_fallback_runs_unconditionally_reading_no_guard_state(store_root, tmp_path):
    """The wiring dispatches dpr-fallback unconditionally regardless of the guard's outcome —
    nothing in this node's own body reads a guard at all. Asserted structurally (the body's own
    source references no 'guard' identifier) and behaviorally (it runs and emits real items when
    invoked directly, with no guard-shaped input anywhere in its config/inputs)."""
    import inspect

    source = inspect.getsource(dpr_fallback_module._dpr_fallback_body)
    assert "guard" not in source.lower()

    vector_store = MultiNamespaceVectorStore(workspace="ws", store_root=store_root)
    chunks_ns = vector_store.select("hipporag-chunks")
    await chunks_ns.upsert(
        ids=["chunk:c1"], embeddings=np.array([[1.0, 0.0, 0.0]]), metadatas=[{}]
    )
    await vector_store.index_done_callback()

    ctx = _ctx(
        "dpr-fallback",
        config={"query": "q"},
        inputs={},  # no fact-filter/guard-shaped input reaches this body at all
        stores={"vector": vector_store},
        clients={"embedding": _StubEmbeddingClient()},
    )
    result = await HIPPORAG_DPR_FALLBACK_PART.body(ctx)
    assert len(result["items"]) == 1


async def test_dpr_fallback_with_empty_chunk_namespace_emits_empty_items_never_raises(store_root):
    vector_store = MultiNamespaceVectorStore(workspace="ws", store_root=store_root)
    ctx = _ctx(
        "dpr-fallback",
        config={"query": "q"},
        stores={"vector": vector_store},
        clients={"embedding": _StubEmbeddingClient()},
    )

    result = await HIPPORAG_DPR_FALLBACK_PART.body(ctx)

    assert result["items"] == []


def test_dpr_fallback_declares_exactly_hash_h_s_two_effects_and_calls_no_top_k():
    import inspect

    assert HIPPORAG_DPR_FALLBACK_PART.effects == ["calls_embedding", "reads_vector"]
    assert "top_k" not in inspect.getsource(dpr_fallback_module)


# --------------------------------------------------------------------------------------------- #
# Task 2: the §19.8 guard on fact-filter, routing assemble-result                                 #
# --------------------------------------------------------------------------------------------- #


class _KeepIdsLLMClient:
    """A stub LLM client whose ``keep_ids`` response is fixed at construction — ``[]`` forces the
    zero-surviving-facts branch, ``["f1", "f2"]`` the normal branch."""

    def __init__(self, keep_ids: list[str]) -> None:
        self._keep_ids = keep_ids

    async def chat(self, messages, **kwargs) -> ChatResult:
        return ChatResult(
            text=json.dumps({"keep_ids": self._keep_ids}),
            tokens=TokenAccounting(
                prompt_tokens=5, completion_tokens=4, call_count=1, counted_by="stub-llm"
            ),
            resolved_model_identity="stub-llm-model",
        )


def _make_engine(seeded_hipporag_store, *, keep_ids: list[str]) -> Databasise:
    return Databasise(
        store_root=seeded_hipporag_store["store_root"],
        workspace=seeded_hipporag_store["workspace"],
        clients={
            "embedding": _StubEmbeddingClient(vector=seeded_hipporag_store["query_vector"]),
            "llm": _KeepIdsLLMClient(keep_ids),
        },
    )


async def test_facts_survive_assemble_result_uses_ppr_and_guard_does_not_fire(seeded_hipporag_store):
    engine = _make_engine(seeded_hipporag_store, keep_ids=["f1", "f2"])

    envelope = await engine.query(
        QueryObject(text=_QUERY_TEXT), Selector(capability=_HIPPORAG_CAPABILITY)
    )
    record = await engine.resolve_trace(envelope.trace_token)
    fact_filter_trace = next(n for n in record["nodes"] if n["node_id"] == "fact-filter")

    assert fact_filter_trace["guards_fired"] == []
    assert envelope.evidence
    assert envelope.evidence[0].namespace == "hipporag-chunks"


async def test_zero_facts_survive_assemble_result_uses_dpr_fallback_and_guard_fires(
    seeded_hipporag_store,
):
    engine = _make_engine(seeded_hipporag_store, keep_ids=[])

    envelope = await engine.query(
        QueryObject(text=_QUERY_TEXT), Selector(capability=_HIPPORAG_CAPABILITY)
    )
    record = await engine.resolve_trace(envelope.trace_token)
    fact_filter_trace = next(n for n in record["nodes"] if n["node_id"] == "fact-filter")

    assert fact_filter_trace["guards_fired"] == ["zero_surviving_facts_dpr_fallback"]
    # dpr-fallback's items are still resolved against the seeded hipporag-chunks namespace, so
    # the envelope's own evidence is real, not empty, even though the guard fired.
    assert envelope.evidence
    assert envelope.evidence[0].namespace == "hipporag-chunks"


async def test_guard_fired_run_reports_degraded_false_and_partial_false_on_the_envelope(
    seeded_hipporag_store,
):
    engine = _make_engine(seeded_hipporag_store, keep_ids=[])

    envelope = await engine.query(
        QueryObject(text=_QUERY_TEXT), Selector(capability=_HIPPORAG_CAPABILITY)
    )

    assert envelope.degraded is False
    assert envelope.partial is False


async def test_guard_name_appears_nowhere_in_the_serialised_envelope(seeded_hipporag_store):
    engine = _make_engine(seeded_hipporag_store, keep_ids=[])

    envelope = await engine.query(
        QueryObject(text=_QUERY_TEXT), Selector(capability=_HIPPORAG_CAPABILITY)
    )

    serialised = envelope.model_dump_json()
    assert "zero_surviving_facts_dpr_fallback" not in serialised
    assert "guard" not in serialised.lower()


def test_fact_filter_node_declares_the_guard_at_config_guards_with_per_query_granularity():
    resolved = load_wiring("hipporag")
    guards = resolved["nodes"]["fact-filter"]["config"]["guards"]
    assert len(guards) == 1
    guard = guards[0]
    assert guard["name"] == "zero_surviving_facts_dpr_fallback"
    assert guard["evaluating_node"] == "fact-filter"
    assert guard["granularity"] == "per-query"


def test_guard_declaration_missing_granularity_raises_guarddeclarationerror():
    """Mirrors runner/guards.py's own established test precedent
    (tests/runner/test_run_record.py's ``test_11_...``) — an inadmissible granularity value (this
    module's own convention for 'missing') is refused by name at wire time, never silently
    defaulted, per CONTRACT §19.8's mandatory-granularity rule."""
    with pytest.raises(GuardDeclarationError):
        declare_guard(
            name="zero_surviving_facts_dpr_fallback",
            evaluating_node="fact-filter",
            value_when_not_fired=False,
            granularity="",
        )


def test_assemble_result_body_source_never_reads_the_run_record():
    import inspect

    from databasise.parts_core.hipporag import assemble_result as assemble_result_module

    source = inspect.getsource(assemble_result_module._assemble_result_body)
    assert "resolve_trace" not in source
    assert "trace_store" not in source
    assert "RunRecord" not in source
