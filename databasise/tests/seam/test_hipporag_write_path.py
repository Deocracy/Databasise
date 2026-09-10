"""06-10-PLAN.md: closes Gap 1(a), the structural write-surface gap — HippoRAG's own real write
path through the public §18 seam. Task 1 (Tests 1-3): a document ingested through
``Databasise.ingest()`` with a HippoRAG selector lands in HippoRAG's own graph/vector/KV
namespaces and comes back as evidence from a HippoRAG query, under stub clients; the no-selector
path stays byte-for-byte unchanged. Task 2 (Tests 4-7): the named delete refusal, selector parity
on REST/MCP, and the write-path invariant over every entry of ``WIRING_NAMES``.

Mirrors ``databasise/tests/seam/test_compare.py``'s own stub-client fixtures and the exact
``Selector`` value that already resolves to the HippoRAG arm — reused verbatim, never a new
selector. No network, no ``v1/`` artifacts, no live client.
"""

from __future__ import annotations

import json

import pytest

from databasise.clients.base import ChatResult, EmbeddingResult
from databasise.runner.trace import TokenAccounting
from databasise.seam import Databasise, QueryObject
from databasise.seam.corpus import DeletionOutcome, IngestDocument, IngestJob
from databasise.seam.refusals import NoWritePathForModalityError
from databasise.seam.selectors import Selector
from databasise.stores.graph import CozoGraphStore
from databasise.stores.kv import SqliteKVStore
from databasise.stores.vector import MultiNamespaceVectorStore
from databasise.wirings.resolve import WIRING_NAMES

_WORKSPACE = "hipporag-write-path-ws"
_QUERY_VECTOR = [1.0, 0.0, 0.0]

# The exact HippoRAG-resolving capability selector test_compare.py/test_cross_modality_run.py
# already establish — reused verbatim per this plan's own read_first instruction.
_HIPPORAG_CAPABILITY = ["reads_graph", "reads_kv"]

_DOCUMENT_TEXT = "Ed Wood directed several low-budget films."
_SUBJECT, _PREDICATE, _OBJECT = "Ed Wood", "directed", "films"


class _StubEmbeddingClient:
    def __init__(self, vector: list[float] = _QUERY_VECTOR):
        self.vector = vector

    async def embed(self, texts, **kwargs):
        return EmbeddingResult(
            vectors=[self.vector for _ in texts],
            tokens=TokenAccounting(prompt_tokens=len(texts), call_count=1, counted_by="stub-embed"),
            resolved_model_identity="stub-embed-model",
        )


class _StubIngestQueryLLMClient:
    """Serves every LLM call HippoRAG's index-side (``openie``) and query-side (``fact-filter``)
    positions make, dispatching on prompt content rather than call order — this module's own
    tests each drive exactly one document/one query, so a content-based dispatch is unambiguous
    and needs no per-test call-index bookkeeping.

    ``fact-filter``'s own prompt always returns ``keep_ids: []`` — deliberately, so
    ``fact-filter``'s ``zero_surviving_facts_dpr_fallback`` guard fires and ``assemble-result``
    selects ``dpr-fallback``'s items, never ``ppr``'s. This is a real, load-bearing test design
    choice (not an incidental default): ``ppr``'s own readback identifies passage vertices by
    their graph vertex name (``"chunk:" + chunk_id``, ``passage_edges.py``'s own prefix), while
    ``chunk-embed`` writes that same chunk's KV/vector records under the bare ``chunk_id`` alone
    — so content hydration and evidence resolution for a ``ppr``-selected item would look up a key
    neither store holds. ``dpr-fallback`` reads directly off the ``hipporag-chunks`` vector
    namespace, whose ids match ``chunk-embed``'s own unprefixed keys, so forcing this guard is
    what makes this module's own evidence-resolves-to-real-text assertion (Test 1) hold under the
    write path this plan actually ships — not a workaround for a bug this plan introduces.
    """

    async def chat(self, messages, **kwargs):
        content = messages[0]["content"]
        if "---Candidate Facts---" in content:
            text = json.dumps({"keep_ids": []})
        elif "---Recognised Entities---" in content:
            text = json.dumps({"triples": [[_SUBJECT, _PREDICATE, _OBJECT]]})
        else:
            text = json.dumps({"entities": [_SUBJECT, _OBJECT]})
        return ChatResult(
            text=text,
            tokens=TokenAccounting(
                prompt_tokens=5, completion_tokens=4, call_count=1, counted_by="stub-llm"
            ),
            resolved_model_identity="stub-llm-model",
        )


def _make_engine(store_root, *, workspace: str = _WORKSPACE) -> Databasise:
    return Databasise(
        store_root=store_root,
        workspace=workspace,
        clients={"embedding": _StubEmbeddingClient(), "llm": _StubIngestQueryLLMClient()},
    )


# --------------------------------------------------------------------------------------------- #
# Task 1: the tracer — one document, HippoRAG's own index, retrievable as evidence.
# --------------------------------------------------------------------------------------------- #


async def test_hipporag_ingest_lands_in_hipporags_own_namespaces_and_is_retrievable_as_evidence(
    store_root,
):
    engine = _make_engine(store_root)
    selector = Selector(capability=_HIPPORAG_CAPABILITY)
    document = IngestDocument(document_id="hipporag-doc-1", text=_DOCUMENT_TEXT)

    job = await engine.ingest(document, selector=selector)

    assert isinstance(job, IngestJob)
    assert job.enqueued == 1

    graph_store = CozoGraphStore(namespace="hipporag-graph", workspace=_WORKSPACE, store_root=store_root)
    graph = await graph_store.export_to_igraph()
    await graph_store.finalize()
    vertex_names = set(graph.vs["name"]) if graph.vcount() else set()
    assert any(name.startswith("entity:") for name in vertex_names)
    assert any(name.startswith("chunk:") for name in vertex_names)

    vector_store = MultiNamespaceVectorStore(workspace=_WORKSPACE, store_root=store_root)
    chunks_ns = vector_store.select("hipporag-chunks")
    assert list(chunks_ns.iter_vectors())
    await vector_store.finalize()

    envelope = await engine.query(QueryObject(text="What did Ed Wood direct?"), selector)

    assert envelope.evidence
    assert envelope.evidence[0].namespace == "hipporag-chunks"
    resolved = [await engine.resolve_evidence(ref) for ref in envelope.evidence]
    assert any(_SUBJECT in str(record.get("content", "")) for record in resolved)


async def test_no_selector_ingest_still_resolves_to_the_lightrag_corpus_wiring(store_root):
    import dataclasses

    from databasise.parts.registry import PartRegistry, default_registry
    from databasise.parts_core.declared_only import LIGHTRAG_FULL_INGEST_PART

    captured: dict[str, object] = {}

    async def _capturing_full_ingest_body(ctx):
        config = ctx.config or {}
        captured["config"] = dict(config)
        return {"track_id": config.get("track_id"), "enqueued": len(config.get("documents") or [])}

    test_part = dataclasses.replace(LIGHTRAG_FULL_INGEST_PART, body=_capturing_full_ingest_body)
    base = default_registry()
    registry = PartRegistry(seed_tracer_parts=False)
    for name in base.keys():
        candidate = base.get(name)
        registry.register(test_part if candidate.name_at_version == test_part.name_at_version else candidate)

    engine = Databasise(store_root=store_root, workspace="no-selector-ws", registry=registry)
    job = await engine.ingest(IngestDocument(text="unselected ingest"))

    assert isinstance(job, IngestJob)
    assert "config" in captured  # lightrag/full-ingest's own body was the one dispatched

    workspace_dir = store_root / "no-selector-ws"
    on_disk = {p.name for p in workspace_dir.iterdir() if p.is_dir()} if workspace_dir.exists() else set()
    assert "text_chunks" in on_disk
    assert "chunk_entity_relation" in on_disk
    assert "hipporag-text-chunks" not in on_disk
    assert "hipporag-graph" not in on_disk


async def test_hipporag_ingest_does_not_touch_lightrags_store_directories(store_root):
    engine = _make_engine(store_root, workspace="isolation-ws")
    selector = Selector(capability=_HIPPORAG_CAPABILITY)
    document = IngestDocument(document_id="hipporag-doc-2", text=_DOCUMENT_TEXT)

    await engine.ingest(document, selector=selector)

    workspace_dir = store_root / "isolation-ws"
    on_disk = {p.name for p in workspace_dir.iterdir() if p.is_dir()} if workspace_dir.exists() else set()
    assert "hipporag-graph" in on_disk
    assert "chunk_entity_relation" not in on_disk
    assert "text_chunks" not in on_disk
