"""12-06-PLAN.md Task 2 (D-12, HIPP-16): ``hipporag/document-remover`` removes exactly what one
document alone contributed. Drives ``Databasise.ingest`` / ``delete_document`` with a HippoRAG
selector under text-keyed stub clients, then inspects the committed stores through fresh handles.

Corpus: d1 "Ed Wood directed films with Bela Lugosi." gives (Ed Wood, directed, films) and
(Bela Lugosi, starred_in, films); d2 "Ed Wood directed films." gives (Ed Wood, directed, films) and
(Edward Wood, directed, pictures). The embedding stub gives "Ed Wood" and "Edward Wood" one vector and
"films" and "pictures" one vector, so d2's ingest adds two synonymy-only edges.
"""

from __future__ import annotations

import contextlib
import json

from databasise.clients.base import ChatResult, EmbeddingResult
from databasise.parts.registry import default_registry
from databasise.parts_core.hipporag import HIPPORAG_CORPUS_PARTS, HIPPORAG_PARTS
from databasise.parts_core.hipporag.openie import _fact_id
from databasise.runner.trace import TokenAccounting
from databasise.seam import Databasise
from databasise.seam.corpus import IngestDocument
from databasise.seam.selectors import Selector
from databasise.stores.graph import CozoGraphStore
from databasise.stores.kv import SqliteKVStore
from databasise.stores.vector import MultiNamespaceVectorStore
from seam.test_hipporag_write_path import _HIPPORAG_CAPABILITY

_WORKSPACE = "document-remover-ws"
_D1 = "Ed Wood directed films with Bela Lugosi."
_D2 = "Ed Wood directed films."
_TRIPLES = {
    _D1: [["Ed Wood", "directed", "films"], ["Bela Lugosi", "starred_in", "films"]],
    _D2: [["Ed Wood", "directed", "films"], ["Edward Wood", "directed", "pictures"]],
}
_ALIASES = {"Edward Wood": "Ed Wood", "pictures": "films"}
_ED, _FILMS, _BELA = "entity:ed wood", "entity:films", "entity:bela lugosi"
_EDWARD, _PICTURES = "entity:edward wood", "entity:pictures"
_SHARED_FACT = _fact_id("Ed Wood", "directed", "films")
_BELA_FACT = _fact_id("Bela Lugosi", "starred_in", "films")


class _TextKeyedLLM:
    """NER and triple answers chosen by which passage text the prompt carries."""

    async def chat(self, messages, **kwargs):
        content = messages[0]["content"]
        passage = next(text for text in sorted(_TRIPLES, key=len, reverse=True) if text in content)
        triples = _TRIPLES[passage]
        if "---Recognised Entities---" in content:
            payload = {"triples": triples}
        else:
            payload = {"entities": sorted({t[0] for t in triples} | {t[2] for t in triples})}
        return ChatResult(
            text=json.dumps(payload),
            tokens=TokenAccounting(prompt_tokens=5, completion_tokens=4, call_count=1, counted_by="stub-llm"),
            resolved_model_identity="stub-llm-model",
        )


class _TextKeyedEmbedding:
    """One one-hot vector per distinct text; an alias shares its target's vector."""

    def __init__(self) -> None:
        self._index: dict[str, int] = {}

    def _vector(self, text: str) -> list[float]:
        key = _ALIASES.get(text, text)
        position = self._index.setdefault(key, len(self._index))
        vector = [0.0] * 64
        vector[position] = 1.0
        return vector

    async def embed(self, texts, **kwargs):
        return EmbeddingResult(
            vectors=[self._vector(text) for text in texts],
            tokens=TokenAccounting(prompt_tokens=len(texts), call_count=1, counted_by="stub-embed"),
            resolved_model_identity="stub-embed-model",
        )


def _engine(store_root) -> Databasise:
    return Databasise(
        store_root=store_root,
        workspace=_WORKSPACE,
        clients={"embedding": _TextKeyedEmbedding(), "llm": _TextKeyedLLM()},
    )


_SELECTOR = Selector(capability=_HIPPORAG_CAPABILITY)


async def _ingest(engine: Databasise, document_id: str, text: str) -> None:
    await engine.ingest(IngestDocument(document_id=document_id, text=text), selector=_SELECTOR)


@contextlib.asynccontextmanager
async def _committed(store_root):
    vectors = MultiNamespaceVectorStore(workspace=_WORKSPACE, store_root=store_root)
    kv = SqliteKVStore(namespace="hipporag-text-chunks", workspace=_WORKSPACE, store_root=store_root)
    graph = CozoGraphStore(namespace="hipporag-graph", workspace=_WORKSPACE, store_root=store_root)
    try:
        yield vectors, kv, graph
    finally:
        await vectors.finalize()
        await kv.finalize()
        await graph.finalize()


async def _manifest_chunk_ids(store_root, document_id: str) -> list[str]:
    async with _committed(store_root) as (_, kv, _):
        manifest = await kv.get_by_id(f"doc:{document_id}")
    return list((manifest or {}).get("chunk_ids", []))


def _ids(vectors, namespace: str) -> set[str]:
    return {doc_id for doc_id, _ in vectors.select(namespace).iter_vectors()}


async def test_the_ingest_manifest_records_the_documents_chunks_facts_and_entities(store_root):
    engine = _engine(store_root)
    await _ingest(engine, "d1", _D1)

    async with _committed(store_root) as (vectors, kv, _):
        manifest = await kv.get_by_id("doc:d1")
        chunk_ids = _ids(vectors, "hipporag-chunks")

    assert manifest is not None
    assert set(manifest["chunk_ids"]) == chunk_ids and chunk_ids
    assert manifest["fact_ids"] == sorted([_SHARED_FACT, _BELA_FACT])
    assert manifest["entities"] == sorted([_ED, _FILMS, _BELA])
    assert manifest["ingested_at"]


async def test_deleting_one_document_keeps_what_another_still_contributes(store_root):
    engine = _engine(store_root)
    await _ingest(engine, "d1", _D1)
    await _ingest(engine, "d2", _D2)
    d1_chunks = await _manifest_chunk_ids(store_root, "d1")
    d2_chunks = await _manifest_chunk_ids(store_root, "d2")
    async with _committed(store_root) as (_, _, graph):
        before = await graph.get_edge(_ED, _FILMS)
    assert before["weight"] == 2.0
    assert sorted(before["cooccurrence_by_chunk"]) == sorted(d1_chunks + d2_chunks)

    outcome = await engine.delete_document("d1", selector=_SELECTOR)

    assert outcome.status == "success"
    async with _committed(store_root) as (vectors, kv, graph):
        # the shared fact keeps d2's chunk only, in KV and in the fact vector's metadata
        assert (await kv.get_by_id(f"fact:{_SHARED_FACT}"))["chunk_ids"] == d2_chunks
        assert vectors.select("hipporag-facts").get_by_id(_SHARED_FACT)["chunk_ids"] == d2_chunks
        # the fact only d1 supported is gone from both
        assert await kv.get_by_id(f"fact:{_BELA_FACT}") is None
        assert vectors.select("hipporag-facts").get_by_id(_BELA_FACT) is None
        # d1's chunks and manifest are gone, d2's remain
        assert _ids(vectors, "hipporag-chunks") == set(d2_chunks)
        assert await kv.get_by_id("doc:d1") is None
        assert await kv.get_by_id("doc:d2") is not None
        # the orphaned entity is gone with its vector; the shared ones survive
        names = set(await graph.get_all_labels())
        assert _BELA not in names and {_ED, _FILMS} <= names
        assert _BELA not in _ids(vectors, "hipporag-entities")
        assert {_ED, _FILMS} <= _ids(vectors, "hipporag-entities")
        # the shared pair edge drops from its two-chunk weight to the one-chunk weight
        after = await graph.get_edge(_ED, _FILMS)
        assert after["weight"] == 1.0
        assert sorted(after["cooccurrence_by_chunk"]) == d2_chunks
        assert not any(name == f"chunk:{c}" for c in d1_chunks for name in names)


async def test_a_synonymy_only_edge_is_untouched_by_deleting_another_document(store_root):
    engine = _engine(store_root)
    await _ingest(engine, "d1", _D1)
    await _ingest(engine, "d2", _D2)
    async with _committed(store_root) as (_, _, graph):
        before = {
            pair: await graph.get_edge(*pair) for pair in ((_ED, _EDWARD), (_FILMS, _PICTURES))
        }
    assert all(edge is not None and edge["edge_types"] == ["synonymy"] for edge in before.values())

    await engine.delete_document("d1", selector=_SELECTOR)

    async with _committed(store_root) as (_, _, graph):
        for pair, edge in before.items():
            assert await graph.get_edge(*pair) == edge


async def test_deleting_the_last_document_removes_every_fact_entity_and_vertex(store_root):
    engine = _engine(store_root)
    await _ingest(engine, "d1", _D1)
    await _ingest(engine, "d2", _D2)
    await engine.delete_document("d1", selector=_SELECTOR)

    outcome = await engine.delete_document("d2", selector=_SELECTOR)

    assert outcome.status == "success"
    async with _committed(store_root) as (vectors, kv, graph):
        for namespace in ("hipporag-chunks", "hipporag-facts", "hipporag-entities"):
            assert _ids(vectors, namespace) == set(), namespace
        assert await graph.get_all_labels() == []
        for key in (f"fact:{_SHARED_FACT}", f"fact:{_BELA_FACT}", "doc:d1", "doc:d2"):
            assert await kv.get_by_id(key) is None, key


async def test_deleting_an_id_never_ingested_is_not_found_and_changes_nothing(store_root):
    engine = _engine(store_root)
    await _ingest(engine, "d1", _D1)
    async with _committed(store_root) as (vectors, kv, graph):
        before = (
            {ns: _ids(vectors, ns) for ns in ("hipporag-chunks", "hipporag-facts", "hipporag-entities")},
            await graph.get_all_labels(),
            await kv.get_by_id("doc:d1"),
        )

    outcome = await engine.delete_document("never-ingested", selector=_SELECTOR)

    assert outcome.status == "not_found"
    async with _committed(store_root) as (vectors, kv, graph):
        after = (
            {ns: _ids(vectors, ns) for ns in ("hipporag-chunks", "hipporag-facts", "hipporag-entities")},
            await graph.get_all_labels(),
            await kv.get_by_id("doc:d1"),
        )
    assert after == before


def test_the_remover_part_is_registered_in_the_corpus_tuple_and_not_among_the_base_positions():
    name = "hipporag/document-remover@0.1.0"
    part = default_registry().get(name)

    assert part.kind == "extractor"
    assert part.structural_depth == "opaque"
    assert set(part.effects) == {"writes_kv", "writes_vector", "writes_graph"}
    assert [p.name_at_version for p in HIPPORAG_CORPUS_PARTS] == [name]
    assert name not in {p.name_at_version for p in HIPPORAG_PARTS}
