"""04-02-PLAN.md Tasks 1 & 2: an answer's evidence reference resolves through the seam back to the
same store record it was minted from (D-07), an unresolvable reference raises by exception type
rather than returning ``None``/empty, a zero-item retrieval yields an empty evidence list without
refusing the query, and evidence ordering/the top-k boundary are pinned by tests naming the
expected ids explicitly (never re-derived from the same sort the code under test performs).
"""

from __future__ import annotations

import inspect

import numpy as np
import pydantic
import pytest
from databasise.clients.base import ChatResult, EmbeddingResult
from databasise.runner.trace import TokenAccounting
from databasise.seam import Databasise, QueryObject
from databasise.seam import evidence as evidence_module
from databasise.seam._base import _StrictModel
from databasise.seam.evidence import (
    CHUNKS_NAMESPACE,
    EvidenceRef,
    MalformedEvidenceItemError,
    UnresolvableEvidenceReferenceError,
    mint_evidence_refs,
)
from databasise.stores.vector import FaissVectorStore
from databasise.tests.seam.conftest import _CONTENT

_STUB_COMPLETION = "This is a stub completion for the evidence-reference tests."


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
            tokens=TokenAccounting(prompt_tokens=5, completion_tokens=4, call_count=1, counted_by="stub-llm"),
            resolved_model_identity="stub-llm-model",
        )


def _engine_for(store: dict, *, vector: list[float]) -> Databasise:
    return Databasise(
        store_root=store["store_root"],
        workspace=store["workspace"],
        clients={"embedding": _StubEmbeddingClient(vector=vector), "llm": _StubLLMClient()},
    )


# --------------------------------------------------------------------------------------------- #
# Task 1: mint -> resolve round trip, unresolvable refusal, empty-evidence, module docstring.
# --------------------------------------------------------------------------------------------- #


async def test_a_minted_evidence_reference_resolves_through_the_seam_to_the_same_record(
    synthetic_naive_store,
):
    engine = _engine_for(synthetic_naive_store, vector=synthetic_naive_store["query_vector"])

    envelope = await engine.query(QueryObject(text="Which films did Ed Wood direct?"))

    assert len(envelope.evidence) == 1
    ref = envelope.evidence[0]
    assert ref.ref == "chunk-1"
    assert ref.namespace == CHUNKS_NAMESPACE

    resolved = await engine.resolve_evidence(ref)
    # Real values the test's own fixture wrote into the synthetic store — never shape alone.
    assert resolved["id"] == "chunk-1"
    assert resolved["content"] == _CONTENT


async def test_dereferencing_an_unknown_evidence_reference_raises_the_named_refusal(
    synthetic_naive_store,
):
    engine = _engine_for(synthetic_naive_store, vector=synthetic_naive_store["query_vector"])
    unknown_ref = EvidenceRef(ref="no-such-chunk", namespace=CHUNKS_NAMESPACE, kind="text_chunk")

    with pytest.raises(UnresolvableEvidenceReferenceError):
        await engine.resolve_evidence(unknown_ref)


async def test_zero_item_retrieval_yields_an_empty_but_present_evidence_list(store_root):
    # No vector upsert at all: FaissVectorStore.query() on a never-flushed namespace returns [].
    engine = Databasise(
        store_root=store_root,
        workspace="seam-test-empty-retrieval",
        clients={"embedding": _StubEmbeddingClient(vector=[1.0, 0.0, 0.0]), "llm": _StubLLMClient()},
    )

    envelope = await engine.query(QueryObject(text="anything"))

    assert envelope.evidence == []
    assert isinstance(envelope.answer, str) and len(envelope.answer) > 0
    assert envelope.answer == _STUB_COMPLETION


def test_mint_evidence_refs_raises_the_named_refusal_for_an_item_missing_its_id_key():
    """WR-03: a retrieval item missing an "id" key used to let a bare `KeyError` propagate — now a
    named exception carrying the malformed item's namespace/index, house style."""
    items = [{"id": "chunk-1", "score": 0.9}, {"score": 0.4}]

    with pytest.raises(MalformedEvidenceItemError) as exc_info:
        mint_evidence_refs(items, namespace=CHUNKS_NAMESPACE)

    assert exc_info.value.namespace == CHUNKS_NAMESPACE
    assert exc_info.value.index == 1


def test_module_docstring_names_each_chunkref_member_as_unpopulated():
    doc = evidence_module.__doc__ or ""
    for member in ("corpus_id", "recipe@version", "ordinal", "content_hash"):
        assert member in doc, f"module docstring does not name ChunkRef member {member!r}"
    assert "unpopulated" in doc


def test_evidence_ref_inherits_the_envelope_modules_strict_base():
    assert issubclass(EvidenceRef, _StrictModel)
    with pytest.raises(pydantic.ValidationError):
        EvidenceRef(ref="x", namespace="chunks", kind="text_chunk", not_a_real_field="leak")


def test_engine_exposes_an_async_resolve_evidence_method():
    assert inspect.iscoroutinefunction(Databasise.resolve_evidence)


# --------------------------------------------------------------------------------------------- #
# Task 2: ordering and the top-k boundary, pinned against an explicit expected id list.
# --------------------------------------------------------------------------------------------- #

# (id, x) pairs — the doc vector is [x, 1.0], the query vector is [1.0, 0.0], so cosine similarity
# is x / sqrt(x**2 + 1): strictly increasing in x for x > 0, giving a fully controlled score order
# with no dependence on the actual numeric score value. c08a/c08b share the same x (hence a
# bit-identical vector and a bit-identical score) to exercise the store's own id tiebreak.
_ORDERED_IDS_AND_X: list[tuple[str, float]] = [
    ("c01", 100.0),
    ("c02", 90.0),
    ("c03", 80.0),
    ("c04", 72.0),
    ("c05", 65.0),
    ("c06", 59.0),
    ("c07", 54.0),
    ("c08a", 50.0),
    ("c08b", 50.0),
    ("c09", 46.0),
    ("c10", 42.0),  # rank 11 — one place beyond the default top_k=10, must be absent
    ("c11", 38.0),  # rank 12 — further beyond
]
_EXPECTED_TOP_10_IDS = ["c01", "c02", "c03", "c04", "c05", "c06", "c07", "c08a", "c08b", "c09"]


@pytest.fixture
async def many_chunks_store(store_root):
    workspace = "seam-test-many-chunks"
    query_vector = [1.0, 0.0]
    vector_store = FaissVectorStore(namespace=CHUNKS_NAMESPACE, workspace=workspace, store_root=store_root)
    ids = [item_id for item_id, _ in _ORDERED_IDS_AND_X]
    vectors = np.array([[x, 1.0] for _, x in _ORDERED_IDS_AND_X], dtype="float32")
    metadatas = [{"content": f"content for {item_id}"} for item_id in ids]
    await vector_store.upsert(ids=ids, embeddings=vectors, metadatas=metadatas)
    await vector_store.index_done_callback()
    return {"store_root": store_root, "workspace": workspace, "query_vector": query_vector}


async def test_evidence_reference_list_matches_the_expected_top_k_id_sequence(many_chunks_store):
    engine = _engine_for(many_chunks_store, vector=many_chunks_store["query_vector"])

    envelope = await engine.query(QueryObject(text="anything"))

    assert [ref.ref for ref in envelope.evidence] == _EXPECTED_TOP_10_IDS


async def test_the_record_at_rank_top_k_plus_one_is_absent(many_chunks_store):
    engine = _engine_for(many_chunks_store, vector=many_chunks_store["query_vector"])

    envelope = await engine.query(QueryObject(text="anything"))

    ids = [ref.ref for ref in envelope.evidence]
    assert "c10" not in ids
    assert "c11" not in ids
    assert len(ids) == 10


async def test_equal_scoring_records_appear_in_the_stores_own_id_tiebreak_order(many_chunks_store):
    engine = _engine_for(many_chunks_store, vector=many_chunks_store["query_vector"])

    envelope = await engine.query(QueryObject(text="anything"))

    ids = [ref.ref for ref in envelope.evidence]
    assert ids.index("c08a") < ids.index("c08b")
    assert ids[ids.index("c08a") : ids.index("c08a") + 2] == ["c08a", "c08b"]


async def test_running_the_same_query_twice_yields_identical_evidence_order(many_chunks_store):
    engine = _engine_for(many_chunks_store, vector=many_chunks_store["query_vector"])

    first = await engine.query(QueryObject(text="anything"))
    second = await engine.query(QueryObject(text="anything"))

    ids_1 = [ref.ref for ref in first.evidence]
    ids_2 = [ref.ref for ref in second.evidence]
    assert ids_1 == ids_2 == _EXPECTED_TOP_10_IDS
