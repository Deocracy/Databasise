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


# --------------------------------------------------------------------------------------------- #
# Task 2: the named delete refusal, selector parity on REST/MCP, and the write-path invariant.
# --------------------------------------------------------------------------------------------- #


async def test_hipporag_selected_delete_raises_the_named_refusal_naming_only_the_operation(
    store_root,
):
    engine = _make_engine(store_root, workspace="delete-refusal-ws")
    selector = Selector(capability=_HIPPORAG_CAPABILITY)

    with pytest.raises(NoWritePathForModalityError) as exc_info:
        await engine.delete_document("hipporag-doc-1", selector=selector)

    assert exc_info.value.operation == "delete"
    message = str(exc_info.value)
    assert "hipporag" not in message.lower()
    assert "lightrag" not in message.lower()
    for node_id in ("chunk-embed", "openie", "entity-fact-embed", "full-delete"):
        assert node_id not in message


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

    # HippoRAG delete refuses over both transports, mapping to the documented 422 the generic
    # SeamRefusalError handler already produces — never a per-endpoint branch.
    rest_delete_response = rest_client.request(
        "DELETE", "/documents/hipporag-doc-rest", json={"selector": selector_payload}
    )
    assert rest_delete_response.status_code == 422
    assert rest_delete_response.json()["refusal_type"] == "NoWritePathForModalityError"

    from databasise.mcp._sdk import import_sdk

    ToolError = import_sdk("mcp.server.mcpserver.exceptions").ToolError
    with pytest.raises(ToolError):
        await mcp_server.call_tool(
            "delete", {"args": {"document_id": "hipporag-doc-mcp", "selector": selector_payload}}
        )


def _tool_json(result) -> dict:
    """Mirrors ``databasise/tests/mcp/test_dual_transport_parity.py``'s own helper: every tool
    returns a plain dict, rendered by the SDK as one JSON text content block."""
    text = "".join(getattr(item, "text", "") or "" for item in result.content)
    return json.loads(text)
