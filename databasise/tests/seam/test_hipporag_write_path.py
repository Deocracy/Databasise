"""06-10-PLAN.md: closes Gap 1(a), the structural write-surface gap — HippoRAG's own real write
path through the public §18 seam. Task 1 (Tests 1-3): a document ingested through
``Databasise.ingest()`` with a HippoRAG selector lands in HippoRAG's own graph/vector/KV
namespaces and comes back as evidence from a HippoRAG query, under stub clients; the no-selector
path stays byte-for-byte unchanged. Task 2 (Tests 4-7): the HippoRAG delete (HIPP-16), selector parity
on REST/MCP, and the write-path invariant over every entry of ``WIRING_NAMES``.

Mirrors ``databasise/tests/seam/test_compare.py``'s own stub-client fixtures and the exact
``Selector`` value that already resolves to the HippoRAG arm — reused verbatim, never a new
selector. No network, no ``v1/`` artifacts, no live client.
"""

from __future__ import annotations

import json
import re

import pytest

from databasise.clients.base import ChatResult, EmbeddingResult
from databasise.runner.trace import TokenAccounting
from databasise.seam import Databasise, QueryObject
from databasise.seam.corpus import DeletionOutcome, IngestDocument, IngestJob
from databasise.seam.refusals import NoRawUploadPathForModalityError, NoWritePathForModalityError
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


class _StubKeepAllFactsLLMClient:
    """Like ``_StubIngestQueryLLMClient`` but ``fact-filter`` keeps every candidate fact, so the
    query takes ``ppr``'s branch (no ``zero_surviving_facts_dpr_fallback`` guard)."""

    async def chat(self, messages, **kwargs):
        content = messages[0]["content"]
        if "---Candidate Facts---" in content:
            text = json.dumps({"keep_ids": re.findall(r"id=([^:\s]+):", content)})
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


async def test_a_ppr_branch_query_hydrates_content_and_every_ref_resolves(store_root):
    """HIPP-01 (D-01): with ``fact-filter`` keeping every fact the query takes ``ppr``'s branch;
    ``ppr`` must emit the bare chunk id so ``assemble-result`` hydrates real text and every
    evidence ref resolves."""
    engine = Databasise(
        store_root=store_root,
        workspace="ppr-branch-ws",
        clients={"embedding": _StubEmbeddingClient(), "llm": _StubKeepAllFactsLLMClient()},
    )
    selector = Selector(capability=_HIPPORAG_CAPABILITY)
    await engine.ingest(IngestDocument(document_id="hipporag-ppr-doc", text=_DOCUMENT_TEXT), selector=selector)

    envelope = await engine.query(QueryObject(text="What did Ed Wood direct?"), selector)

    trace = await engine.resolve_trace(envelope.trace_token, debug=True)
    fact_filter_guards = [n["guards_fired"] for n in trace["nodes"] if n["node_id"] == "fact-filter"]
    assert fact_filter_guards == [[]]
    assert envelope.evidence

    failures: list[Exception] = []
    resolved: list[dict] = []
    for ref in envelope.evidence:
        try:
            resolved.append(await engine.resolve_evidence(ref))
        except Exception as exc:  # noqa: BLE001 - the assertion below reports what was caught
            failures.append(exc)
    assert failures == []
    assert resolved
    assert all(_SUBJECT in str(record.get("content", "")) for record in resolved)
    assert envelope.answer.strip()
    assert "[no-context]" not in envelope.answer


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


async def test_raw_upload_against_a_hipporag_selector_refuses_by_name_rather_than_losing_content(
    store_root,
):
    """06-REVIEW.md CR-01: before the fix, a raw-bytes ``IngestDocument`` against a
    HippoRAG-resolving selector always stamped ``text=""`` for the target node
    (``hipporag/chunker-embedder`` reads only ``document["text"]``, never ``file_paths``), so it
    silently chunked/embedded/wrote nothing while still reporting a normal-looking
    ``IngestJob(enqueued=1)``. This test fails without the fix (no exception was raised, and a
    ``hipporag-graph`` directory was never created either way, making the prior silent-success
    path indistinguishable from a real ingest without inspecting the returned evidence)."""
    engine = _make_engine(store_root, workspace="raw-upload-refusal-ws")
    selector = Selector(capability=_HIPPORAG_CAPABILITY)
    document = IngestDocument(document_id="hipporag-raw-doc", raw=b"raw pdf bytes")

    with pytest.raises(NoRawUploadPathForModalityError) as exc_info:
        await engine.ingest(document, selector=selector)

    assert exc_info.value.operation == "ingest"
    message = str(exc_info.value)
    assert "hipporag" not in message.lower()
    assert "lightrag" not in message.lower()

    workspace_dir = store_root / "raw-upload-refusal-ws"
    on_disk = {p.name for p in workspace_dir.iterdir() if p.is_dir()} if workspace_dir.exists() else set()
    assert "hipporag-graph" not in on_disk
    assert not (store_root / "corpus-inbox").exists()


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


# --------------------------------------------------------------------------------------------- #
# Task 2: the named delete refusal, selector parity on REST/MCP, and the write-path invariant.
# --------------------------------------------------------------------------------------------- #


async def test_a_hipporag_delete_removes_the_document_and_a_second_delete_is_not_found(store_root):
    """HIPP-16 (delete half, D-12): a HippoRAG-selected delete is a real corpus op. It removes the
    document's chunk vectors, chunk KV rows, ``doc:<id>`` manifest and chunk vertices, and a query
    afterwards returns no evidence from it; a second delete reports ``not_found``."""
    workspace = "hipporag-delete-ws"
    engine = _make_engine(store_root, workspace=workspace)
    selector = Selector(capability=_HIPPORAG_CAPABILITY)
    await engine.ingest(IngestDocument(document_id="hipporag-del-doc", text=_DOCUMENT_TEXT), selector=selector)

    vector_store = MultiNamespaceVectorStore(workspace=workspace, store_root=store_root)
    chunk_ids = [doc_id for doc_id, _ in vector_store.select("hipporag-chunks").iter_vectors()]
    await vector_store.finalize()
    assert chunk_ids

    raised: Exception | None = None
    outcome = None
    try:
        outcome = await engine.delete_document("hipporag-del-doc", selector=selector)
    except Exception as exc:  # noqa: BLE001 - asserted on below
        raised = exc
    assert raised is None, repr(raised)
    assert isinstance(outcome, DeletionOutcome)
    assert outcome.status == "success"

    vector_store = MultiNamespaceVectorStore(workspace=workspace, store_root=store_root)
    kv_store = SqliteKVStore(namespace="hipporag-text-chunks", workspace=workspace, store_root=store_root)
    graph_store = CozoGraphStore(namespace="hipporag-graph", workspace=workspace, store_root=store_root)
    try:
        for namespace in ("hipporag-chunks", "hipporag-facts", "hipporag-entities"):
            assert [doc_id for doc_id, _ in vector_store.select(namespace).iter_vectors()] == [], namespace
        for chunk_id in chunk_ids:
            assert await kv_store.get_by_id(chunk_id) is None
        assert await kv_store.get_by_id("doc:hipporag-del-doc") is None
        names = await graph_store.get_all_labels()
        assert not any(name.startswith("chunk:") for name in names), names
    finally:
        await vector_store.finalize()
        await kv_store.finalize()
        await graph_store.finalize()

    query_evidence = None
    query_error: Exception | None = None
    try:
        query_evidence = (await engine.query(QueryObject(text="What did Ed Wood direct?"), selector)).evidence
    except Exception as exc:  # noqa: BLE001 - a refusal on an emptied index is also "no evidence"
        query_error = exc
    assert not query_evidence, (query_evidence, repr(query_error))

    second = await engine.delete_document("hipporag-del-doc", selector=selector)
    assert second.status == "not_found"


def _long_text(n_sentences: int = 55) -> str:
    """About 2600 characters of distinct sentences: three chunks at the default 1200/100."""
    return " ".join(f"Sentence number {i} says something unique about topic {i * 7}." for i in range(n_sentences))


async def _committed_chunk_ids(store_root, workspace: str, document_id: str) -> list[str]:
    vector_store = MultiNamespaceVectorStore(workspace=workspace, store_root=store_root)
    try:
        chunks = vector_store.select("hipporag-chunks")
        return sorted(
            doc_id
            for doc_id, _ in chunks.iter_vectors()
            if (chunks.get_by_id(doc_id) or {}).get("document_id") == document_id
        )
    finally:
        await vector_store.finalize()


async def test_reingest_leaves_no_stale_chunk_and_delete_removes_everything(store_root):
    """HIPP-16 (D-12): re-ingesting a document id with shorter text replaces the document inside one
    run. No chunk vector, KV record, vertex or edge from the old chunks remains, a following delete
    leaves nothing and a query returns no evidence."""
    workspace = "reingest-ws"
    engine = _make_engine(store_root, workspace=workspace)
    selector = Selector(capability=_HIPPORAG_CAPABILITY)

    await engine.ingest(IngestDocument(document_id="reingest-doc", text=_long_text()), selector=selector)
    old_ids = await _committed_chunk_ids(store_root, workspace, "reingest-doc")
    assert len(old_ids) == 3

    await engine.ingest(IngestDocument(document_id="reingest-doc", text=_DOCUMENT_TEXT), selector=selector)

    new_ids = await _committed_chunk_ids(store_root, workspace, "reingest-doc")
    assert len(new_ids) == 1, new_ids
    stale = [chunk_id for chunk_id in old_ids if chunk_id not in new_ids]
    kv_store = SqliteKVStore(namespace="hipporag-text-chunks", workspace=workspace, store_root=store_root)
    graph_store = CozoGraphStore(namespace="hipporag-graph", workspace=workspace, store_root=store_root)
    try:
        for chunk_id in stale:
            assert await kv_store.get_by_id(chunk_id) is None, chunk_id
        labels = set(await graph_store.get_all_labels())
        assert not {f"chunk:{chunk_id}" for chunk_id in stale} & labels
        for label in labels:
            for edge in await graph_store.get_node_edges(label):
                assert not {edge["src"], edge["tgt"]} & {f"chunk:{chunk_id}" for chunk_id in stale}
    finally:
        await kv_store.finalize()
        await graph_store.finalize()

    raised: Exception | None = None
    outcome = None
    try:
        outcome = await engine.delete_document("reingest-doc", selector=selector)
    except Exception as exc:  # noqa: BLE001 - asserted on below
        raised = exc
    assert raised is None, repr(raised)
    assert outcome is not None and outcome.status == "success"

    vector_store = MultiNamespaceVectorStore(workspace=workspace, store_root=store_root)
    kv_store = SqliteKVStore(namespace="hipporag-text-chunks", workspace=workspace, store_root=store_root)
    graph_store = CozoGraphStore(namespace="hipporag-graph", workspace=workspace, store_root=store_root)
    try:
        assert [d for d, _ in vector_store.select("hipporag-chunks").iter_vectors()] == []
        for chunk_id in old_ids + new_ids:
            assert await kv_store.get_by_id(chunk_id) is None
        assert await kv_store.get_by_id("doc:reingest-doc") is None
        assert not any(n.startswith("chunk:") for n in await graph_store.get_all_labels())
    finally:
        await vector_store.finalize()
        await kv_store.finalize()
        await graph_store.finalize()

    evidence = None
    try:
        evidence = (await engine.query(QueryObject(text="What did Ed Wood direct?"), selector)).evidence
    except Exception:  # noqa: BLE001 - a refusal on an emptied index is also "no evidence"
        pass
    assert not evidence


class _TextKeyedEmbeddingClient:
    """'films' and 'movies' embed identically; every other text gets its own one-hot vector."""

    def __init__(self) -> None:
        self._index: dict[str, int] = {}

    async def embed(self, texts, **kwargs):
        vectors = []
        for text in texts:
            key = "films" if text.strip().lower() in ("films", "movies") else text
            slot = self._index.setdefault(key, len(self._index))
            vectors.append([1.0 if i == slot else 0.0 for i in range(64)])
        return EmbeddingResult(
            vectors=vectors,
            tokens=TokenAccounting(prompt_tokens=len(texts), call_count=1, counted_by="stub-embed"),
            resolved_model_identity="stub-embed-model",
        )


class _SynonymLLMClient:
    """NER finds Ed Wood, films and movies; the triples tie Ed Wood to both synonyms."""

    async def chat(self, messages, **kwargs):
        content = messages[0]["content"]
        if "---Candidate Facts---" in content:
            text = json.dumps({"keep_ids": []})
        elif "---Recognised Entities---" in content:
            text = json.dumps({"triples": [["Ed Wood", "directed", "films"], ["Ed Wood", "made", "movies"]]})
        else:
            text = json.dumps({"entities": ["Ed Wood", "films", "movies"]})
        return ChatResult(
            text=text,
            tokens=TokenAccounting(prompt_tokens=5, completion_tokens=4, call_count=1, counted_by="stub-llm"),
            resolved_model_identity="stub-llm-model",
        )


async def test_reingesting_a_document_keeps_its_synonymy_edges(store_root):
    """D-12 / D-05: the remover deletes the document's orphaned entities and the re-ingest adds them
    back in the same run. They must count as new, or synonymy-edges never matches them again."""
    workspace = "syn-ws"
    engine = Databasise(
        store_root=store_root,
        workspace=workspace,
        clients={"embedding": _TextKeyedEmbeddingClient(), "llm": _SynonymLLMClient()},
    )
    selector = Selector(capability=_HIPPORAG_CAPABILITY)

    async def synonymy_edge_types() -> list[str]:
        graph_store = CozoGraphStore(namespace="hipporag-graph", workspace=workspace, store_root=store_root)
        try:
            return [
                t
                for edge in await graph_store.get_node_edges("entity:films")
                if {edge["src"], edge["tgt"]} == {"entity:films", "entity:movies"}
                for t in edge["attrs"].get("edge_types", [])
            ]
        finally:
            await graph_store.finalize()

    document = IngestDocument(document_id="syn-doc", text=_DOCUMENT_TEXT)
    await engine.ingest(document, selector=selector)
    assert "synonymy" in await synonymy_edge_types()

    await engine.ingest(document, selector=selector)
    assert "synonymy" in await synonymy_edge_types()


async def test_an_old_ref_never_resolves_to_the_new_text_after_reingest(store_root):
    """HIPP-17 (D-03): an EvidenceRef minted before a re-ingest with changed text resolves to the
    original text or is refused as unresolvable, never to the new text."""
    text_a = "Ed Wood directed several low-budget films."
    text_b = "Ed Wood also wrote pulp novels for a living."
    engine = _make_engine(store_root, workspace="ref-ws")
    selector = Selector(capability=_HIPPORAG_CAPABILITY)

    await engine.ingest(IngestDocument(document_id="ref-doc", text=text_a), selector=selector)
    kept = (await engine.query(QueryObject(text="What did Ed Wood direct?"), selector)).evidence
    assert kept

    await engine.ingest(IngestDocument(document_id="ref-doc", text=text_b), selector=selector)

    outcomes: list[tuple[str, str]] = []
    for ref in kept:
        try:
            record = await engine.resolve_evidence(ref)
            outcomes.append(("resolved", str(record.get("content", ""))))
        except Exception as exc:  # noqa: BLE001 - the type name is asserted below
            outcomes.append((type(exc).__name__, ""))
    for kind, content in outcomes:
        assert (kind, content) == ("resolved", text_a) or kind == "UnresolvableEvidenceReferenceError", outcomes


async def test_identical_text_in_two_documents_gets_two_chunk_ids(store_root):
    """HIPP-17: the chunk id hashes the document id too, so a document-scoped delete never removes
    the other document's chunk."""
    workspace = "twin-ws"
    engine = _make_engine(store_root, workspace=workspace)
    selector = Selector(capability=_HIPPORAG_CAPABILITY)
    await engine.ingest(IngestDocument(document_id="twin-a", text=_DOCUMENT_TEXT), selector=selector)
    await engine.ingest(IngestDocument(document_id="twin-b", text=_DOCUMENT_TEXT), selector=selector)

    ids_a = await _committed_chunk_ids(store_root, workspace, "twin-a")
    ids_b = await _committed_chunk_ids(store_root, workspace, "twin-b")
    assert len(ids_a) == len(ids_b) == 1
    assert ids_a != ids_b


async def test_no_selector_delete_still_reaches_the_lightrag_delete_wiring(store_root):
    from seam.test_delete_document import _make_stub_full_delete_body, _registry_with

    import dataclasses

    from databasise.parts_core.declared_only import LIGHTRAG_FULL_DELETE_PART

    test_part = dataclasses.replace(
        LIGHTRAG_FULL_DELETE_PART, body=_make_stub_full_delete_body(timeout=5.0, stub_status="success")
    )
    registry = _registry_with(test_part)
    engine = Databasise(store_root=store_root, workspace="no-selector-delete-ws", registry=registry)

    outcome = await engine.delete_document("some-doc")

    assert isinstance(outcome, DeletionOutcome)
    assert outcome.status == "success"


async def test_write_path_invariant_holds_over_every_wiring_name():
    """The invariant Task 1's assumption-delta checkpoint accepted: for every entry of
    ``WIRING_NAMES``, either its own ``corpus-<operation>.json`` exists (and loads through
    ``_corpus_wiring`` without raising) or the operation raises ``NoWritePathForModalityError`` —
    never a silent fallback to another modality's file. Iterates ``WIRING_NAMES`` itself, never a
    hand-written modality list, so a modality added later fails this test instead of passing by
    omission."""
    from pathlib import Path

    from databasise.seam.engine import _corpus_wiring

    wirings_root = Path(__file__).resolve().parents[2] / "wirings"

    for name in WIRING_NAMES:
        fake_query_wiring = {"wiring_id": f"{name}-base"}
        for operation in ("ingest", "delete"):
            wiring_path = wirings_root / name / f"corpus-{operation}.json"
            if wiring_path.is_file():
                resolved = _corpus_wiring(fake_query_wiring, operation)
                assert resolved.get("nodes")
            else:
                with pytest.raises(NoWritePathForModalityError):
                    _corpus_wiring(fake_query_wiring, operation)


async def test_hipporag_ingest_parity_across_rest_mcp_and_in_process_transports(store_root):
    pytest.importorskip("fastapi")
    try:
        import databasise.mcp  # noqa: F401 - import-for-availability-check only
    except ImportError:
        pytest.skip("the `mcp` extra is not installed")

    from fastapi.testclient import TestClient

    from databasise.mcp import create_server
    from databasise.seam.rest import create_app

    clients = {"embedding": _StubEmbeddingClient(), "llm": _StubIngestQueryLLMClient()}
    selector_payload = {"capability": _HIPPORAG_CAPABILITY}

    rest_app = create_app(store_root=store_root, workspace="parity-rest-ws", clients=clients)
    rest_client = TestClient(rest_app)
    rest_response = rest_client.post(
        "/documents",
        json={
            "document": {"document_id": "hipporag-doc-rest", "text": _DOCUMENT_TEXT},
            "selector": selector_payload,
        },
    )
    assert rest_response.status_code == 200
    rest_job = rest_response.json()
    assert rest_job["enqueued"] == 1
    assert rest_job["job_id"]

    mcp_server = create_server(store_root=store_root, workspace="parity-mcp-ws", clients=clients)
    mcp_result = await mcp_server.call_tool(
        "ingest",
        {
            "args": {
                "document_id": "hipporag-doc-mcp",
                "text": _DOCUMENT_TEXT,
                "selector": selector_payload,
            }
        },
    )
    mcp_job = _tool_json(mcp_result)
    assert mcp_job["enqueued"] == 1
    assert mcp_job["job_id"]

    in_process_engine = _make_engine(store_root, workspace="parity-in-process-ws")
    in_process_job = await in_process_engine.ingest(
        IngestDocument(document_id="hipporag-doc-in-process", text=_DOCUMENT_TEXT),
        selector=Selector(capability=_HIPPORAG_CAPABILITY),
    )
    assert set(rest_job.keys()) == set(in_process_job.model_dump().keys()) == set(mcp_job.keys())

    # A HippoRAG delete is a real corpus op over both transports (HIPP-16, D-12).
    rest_delete_response = rest_client.request(
        "DELETE", "/documents/hipporag-doc-rest", json={"selector": selector_payload}
    )
    assert rest_delete_response.status_code == 200
    assert rest_delete_response.json()["status"] == "success"

    mcp_delete_result = await mcp_server.call_tool(
        "delete", {"args": {"document_id": "hipporag-doc-mcp", "selector": selector_payload}}
    )
    assert _tool_json(mcp_delete_result)["status"] == "success"


def _tool_json(result) -> dict:
    """Mirrors ``databasise/tests/mcp/test_dual_transport_parity.py``'s own helper: every tool
    returns a plain dict, rendered by the SDK as one JSON text content block."""
    text = "".join(getattr(item, "text", "") or "" for item in result.content)
    return json.loads(text)


async def test_hipporag_documents_appear_in_jobs_corpus_counts_and_health(store_root, monkeypatch):
    """HIPP-15 (D-13): the job id a HippoRAG ingest returns answers ``processed``; ``/corpus`` and
    ``/corpus/counts`` with a HippoRAG selector list and count the document from its manifest; and
    ``/health`` reports HippoRAG's own stores. The faked v1 corpus is empty, so a listing that still
    came from v1 would show zero documents."""
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    import databasise.seam.engine as engine_module
    from databasise.seam.rest import create_app

    def _fake(op, payload, *, timeout=None, **kwargs):
        if op == "status":
            return {"total": 0, "documents": [], "counts": {}}
        return {"configured": True, "missing_keys": [], "unsupported_keys": []}

    monkeypatch.setattr(engine_module, "run_corpus_op", _fake)

    clients = {"embedding": _StubEmbeddingClient(), "llm": _StubIngestQueryLLMClient()}
    client = TestClient(create_app(store_root=store_root, workspace="corpus-surface-ws", clients=clients))
    selector_json = json.dumps({"capability": _HIPPORAG_CAPABILITY})

    ingest = client.post(
        "/documents",
        json={
            "document": {"document_id": "corpus-doc", "text": _DOCUMENT_TEXT},
            "selector": {"capability": _HIPPORAG_CAPABILITY},
        },
    )
    assert ingest.status_code == 200
    job_id = ingest.json()["job_id"]

    job = client.get(f"/jobs/{job_id}")
    assert job.status_code == 200
    assert [(d["document_id"], d["status"]) for d in job.json()["documents"]] == [("corpus-doc", "processed")]

    corpus = client.get("/corpus", params={"selector": selector_json})
    assert corpus.status_code == 200
    body = corpus.json()
    assert body["total"] == 1, body
    assert [(d["document_id"], d["status"]) for d in body["documents"]] == [("corpus-doc", "processed")]
    assert body["next_offset"] is None

    counts = client.get("/corpus/counts", params={"selector": selector_json})
    assert counts.status_code == 200
    assert counts.json() == {"by_status": {"processed": 1}, "total": 1}

    health = client.get("/health")
    assert health.status_code == 200
    stores = health.json()["stores"]
    assert stores["kv:hipporag-text-chunks"] == "ok"
    assert stores["graph:hipporag-graph"] == "ok"
    assert stores["vector:hipporag-chunks"] == "ok"
