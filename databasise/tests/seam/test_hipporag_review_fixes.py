"""Phase 12 code-review fixes (12-REVIEW.md): A-CR-01, B-CR-01, B-WR-01..04 regression tests.

Kept in a new file because the tests that cover the neighbouring behaviour are ledger-protected.
No network, no v1 artifacts, no live client.
"""

from __future__ import annotations

import json
import math

import pytest

from databasise.clients.base import ChatResult, EmbeddingResult
from databasise.runner.trace import TokenAccounting
from databasise.seam import Databasise
from databasise.seam.corpus import IngestDocument
from databasise.seam.selectors import Selector
from databasise.stores.graph import CozoGraphStore

_HIPPORAG = Selector(capability=["reads_graph", "reads_kv"])
_D1_ENTITIES = ["x", "a1", "a2", "a3", "a4", "a5"]
_DIMS = 64


class _ClusterEmbeddingClient:
    """The d1 entities share one vector, ``y`` sits at cosine 0.9 from it, every other text is one-hot."""

    def __init__(self) -> None:
        self._slots: dict[str, int] = {}

    async def embed(self, texts, **kwargs):
        vectors = []
        for text in texts:
            key = text.strip().lower()
            if key in _D1_ENTITIES:
                vector = [1.0] + [0.0] * (_DIMS - 1)
            elif key == "y":
                vector = [0.9, math.sqrt(1 - 0.81)] + [0.0] * (_DIMS - 2)
            else:
                slot = 2 + self._slots.setdefault(key, len(self._slots))
                vector = [1.0 if i == slot else 0.0 for i in range(_DIMS)]
            vectors.append(vector)
        return EmbeddingResult(
            vectors=vectors,
            tokens=TokenAccounting(prompt_tokens=len(texts), call_count=1, counted_by="stub-embed"),
            resolved_model_identity="stub-embed-model",
        )


class _TwoDocumentLLMClient:
    async def chat(self, messages, **kwargs):
        content = messages[0]["content"]
        entities, triples = (
            (_D1_ENTITIES, [["x", "rel", a] for a in _D1_ENTITIES[1:]])
            if "DOC-ONE" in content
            else (["y", "z"], [["y", "rel", "z"]])
        )
        if "---Candidate Facts---" in content:
            text = json.dumps({"keep_ids": []})
        elif "---Recognised Entities---" in content:
            text = json.dumps({"triples": triples})
        else:
            text = json.dumps({"entities": entities})
        return ChatResult(
            text=text,
            tokens=TokenAccounting(prompt_tokens=5, completion_tokens=4, call_count=1, counted_by="stub-llm"),
            resolved_model_identity="stub-llm-model",
        )


async def test_reingesting_a_document_keeps_synonymy_edges_other_documents_created(store_root):
    """A-CR-01: y (document 2) has synonymy edges into document 1's entities. Re-ingesting document 1
    unchanged must not delete them, even though y's neighbours' own top-k no longer contain y."""
    workspace = "cross-doc-syn-ws"
    engine = Databasise(
        store_root=store_root,
        workspace=workspace,
        clients={"embedding": _ClusterEmbeddingClient(), "llm": _TwoDocumentLLMClient()},
    )

    async def y_synonymy_pairs() -> set[frozenset[str]]:
        graph_store = CozoGraphStore(namespace="hipporag-graph", workspace=workspace, store_root=store_root)
        try:
            return {
                frozenset((edge["src"], edge["tgt"]))
                for edge in await graph_store.get_node_edges("entity:y")
                if "synonymy" in edge["attrs"].get("edge_types", [])
            }
        finally:
            await graph_store.finalize()

    first = IngestDocument(document_id="doc-1", text="DOC-ONE is about x and its neighbours.")
    await engine.ingest(first, selector=_HIPPORAG)
    await engine.ingest(IngestDocument(document_id="doc-2", text="DOC-TWO is about y."), selector=_HIPPORAG)
    before = await y_synonymy_pairs()
    assert before, "the fixture must give y at least one synonymy edge into document 1"

    await engine.ingest(first, selector=_HIPPORAG)

    assert await y_synonymy_pairs() == before


async def test_a_hipporag_delete_leaves_lightrags_staged_uploads_alone(store_root):
    """B-CR-01: the inbox is LightRAG's; a HippoRAG delete of the same id must not unlink from it."""
    workspace = "inbox-ws"
    engine = Databasise(
        store_root=store_root,
        workspace=workspace,
        clients={"embedding": _ClusterEmbeddingClient(), "llm": _TwoDocumentLLMClient()},
    )
    inbox = store_root / workspace / "corpus-inbox"
    (inbox / "__parsed__").mkdir(parents=True)
    kept = inbox / "report.pdf"
    parsed = inbox / "__parsed__" / "report.pdf"
    kept.write_bytes(b"%PDF kept for retry")
    parsed.write_bytes(b"%PDF parsed")

    outcome = await engine.delete_document("report", selector=_HIPPORAG)

    assert outcome.status == "not_found"
    assert kept.exists() and parsed.exists()


def _write_kv(store_root, workspace, rows):
    import sqlite3

    directory = store_root / workspace / "hipporag-text-chunks"
    directory.mkdir(parents=True)
    conn = sqlite3.connect(directory / "kv.sqlite3")
    conn.execute("CREATE TABLE kv (id TEXT PRIMARY KEY, value TEXT NOT NULL)")
    conn.executemany("INSERT INTO kv VALUES (?, ?)", rows)
    conn.commit()
    conn.close()
    return directory


@pytest.mark.parametrize("bad_value", ["{not json", "[1, 2]", "3"])
async def test_a_bad_manifest_row_is_a_typed_refusal_not_a_bare_exception(store_root, bad_value):
    """B-WR-01: an undecodable or non-dict ``doc:`` row used to escape as JSONDecodeError/AttributeError."""
    from databasise.seam.refusals import ForeignEngineRefusalError

    _write_kv(store_root, "bad-manifest-ws", [("doc:good", json.dumps({"ingested_at": "t"})), ("doc:bad", bad_value)])
    engine = Databasise(
        store_root=store_root,
        workspace="bad-manifest-ws",
        clients={"embedding": _ClusterEmbeddingClient(), "llm": _TwoDocumentLLMClient()},
    )

    with pytest.raises(ForeignEngineRefusalError) as raised:
        await engine.corpus_status(selector=_HIPPORAG)

    assert raised.value.failure_class == "MalformedDriverOutput"


def test_list_kv_prefix_refuses_a_wal_with_frames_and_no_shm(store_root):
    """B-WR-02: an immutable open ignores the WAL, so the listing would omit committed documents."""
    import sqlite3

    from databasise.stores.probes import list_kv_prefix

    directory = _write_kv(store_root, "wal-ws", [("doc:a", "{}")])
    (directory / "kv.sqlite3-wal").write_bytes(b"committed frames")

    with pytest.raises(sqlite3.OperationalError, match="shm"):
        list_kv_prefix(directory, "doc:", limit=10, offset=0)
    assert not (directory / "kv.sqlite3-shm").exists()


def test_list_kv_prefix_survives_the_wal_vanishing_between_the_checks(store_root, monkeypatch):
    """B-IN-07: the last writer closing removes the WAL between ``exists`` and ``stat``; that is healthy."""
    from pathlib import Path

    from databasise.stores.probes import list_kv_prefix

    directory = _write_kv(store_root, "vanishing-wal-ws", [("doc:a", "{}")])
    wal = directory / "kv.sqlite3-wal"
    wal.write_bytes(b"frames")
    real_stat = Path.stat

    def stat_that_loses_the_wal(self, *args, **kwargs):
        if self.name == "kv.sqlite3-wal":
            self.unlink()
            raise FileNotFoundError(self.name)
        return real_stat(self, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", stat_that_loses_the_wal)

    assert list_kv_prefix(directory, "doc:", limit=10, offset=0) == ([("doc:a", {})], 1)


def test_list_kv_prefix_still_lists_a_checkpointed_store(store_root):
    from databasise.stores.probes import list_kv_prefix

    directory = _write_kv(store_root, "plain-ws", [("doc:a", "{}"), ("other", "{}")])

    assert list_kv_prefix(directory, "doc:", limit=10, offset=0) == ([("doc:a", {})], 1)


def test_a_pre_phase_12_hipporag_trace_still_matches_its_wiring_and_an_unknown_shape_is_a_named_refusal():
    """B-WR-03: the old 13-node HippoRAG run shape (no ``qa``) matches; a shape matching no wiring
    is a 404 refusal, not an AssertionError."""
    from databasise.seam.promotion import _arm_name_for_node_ids
    from databasise.seam.refusals import UnknownTraceReferenceError
    from databasise.wirings.resolve import load_wiring

    full = frozenset(load_wiring("hipporag")["nodes"])
    assert "qa" in full

    assert _arm_name_for_node_ids(full - {"qa"}) == "hipporag"
    assert _arm_name_for_node_ids(full) == "hipporag"
    with pytest.raises(UnknownTraceReferenceError):
        _arm_name_for_node_ids(frozenset({"not-a-node"}), trace_reference="trace-123")


async def _hipporag_envelope(store_root, llm, n_documents, workspace):
    from seam.test_hipporag_write_path import _DOCUMENT_TEXT, _HIPPORAG_CAPABILITY, _StubEmbeddingClient

    from databasise.seam import QueryObject

    engine = Databasise(
        store_root=store_root,
        workspace=workspace,
        clients={"embedding": _StubEmbeddingClient(), "llm": llm},
    )
    selector = Selector(capability=_HIPPORAG_CAPABILITY)
    for index in range(n_documents):
        await engine.ingest(
            IngestDocument(document_id=f"stand-in-{index}", text=f"{_DOCUMENT_TEXT} Variant {index}."),
            selector=selector,
        )
    envelope = await engine.query(QueryObject(text="What did Ed Wood direct?"), selector)
    trace = await engine.resolve_trace(envelope.trace_token, debug=True)
    node = next(n for n in trace["nodes"] if n["node_id"] == "assemble-result")
    return envelope, node


async def test_an_empty_ppr_query_reads_degraded_with_the_node_free_reason(store_root, tmp_path, monkeypatch):
    """A-WR-05 (D-21): answering from dpr-fallback because PPR reached nothing is a declared
    degradation path: the node reports the guard, the run reads degraded, and the reason codes name
    no node or guard. A query answered by PPR itself reads clean."""
    from seam.test_hipporag_query_path import _KeepAllFactsLLMClient

    from databasise.parts_core.hipporag.ppr import HIPPORAG_PPR_RETRIEVER_PART

    normal, normal_node = await _hipporag_envelope(tmp_path / "ppr", _KeepAllFactsLLMClient(), 3, "ppr-ws")

    real_ppr = HIPPORAG_PPR_RETRIEVER_PART.body

    async def ppr_reaching_nothing(ctx):  # every PPR score 0: the degenerate reset vector of A-WR-02
        output = await real_ppr(ctx)
        return {**output, "items": [{**item, "score": 0.0} for item in output["items"]]}

    monkeypatch.setattr(HIPPORAG_PPR_RETRIEVER_PART, "body", ppr_reaching_nothing)
    stand_in, stand_in_node = await _hipporag_envelope(store_root, _KeepAllFactsLLMClient(), 3, "stand-in-ws")

    assert stand_in.evidence, "the dense stand-in must still answer"
    assert stand_in_node["guards_fired"] == ["empty_ppr_dpr_stand_in"]
    assert (stand_in.degraded, stand_in.stop_reason, stand_in.degradation_reason) == (
        True,
        "declared_fallback",
        "fallback_path_taken",
    )
    assert normal_node["guards_fired"] == []
    assert (normal.degraded, normal.stop_reason, normal.degradation_reason) == (False, None, None)


# --- B-WR-04: strict replacements for lax assertions in the protected write-path/query-path tests ---
# The protected tests wrap the post-delete query in ``except Exception`` (write_path.py:310-316, 394-399)
# and assert only ``<= 5`` / ``> 0`` in the top_k test (query_path.py:230-240); these pin what they claim.


async def _query_after_delete(store_root, workspace):
    from seam.test_hipporag_write_path import (
        _DOCUMENT_TEXT,
        _HIPPORAG_CAPABILITY,
        _StubEmbeddingClient,
        _StubIngestQueryLLMClient,
    )

    from databasise.seam import QueryObject

    engine = Databasise(
        store_root=store_root,
        workspace=workspace,
        clients={"embedding": _StubEmbeddingClient(), "llm": _StubIngestQueryLLMClient()},
    )
    selector = Selector(capability=_HIPPORAG_CAPABILITY)
    await engine.ingest(IngestDocument(document_id="gone-doc", text=_DOCUMENT_TEXT), selector=selector)
    assert (await engine.delete_document("gone-doc", selector=selector)).status == "success"
    return await engine.query(QueryObject(text="What did Ed Wood direct?"), selector)


async def test_a_query_after_the_only_document_is_deleted_returns_no_evidence_or_names_the_empty_namespace(
    store_root,
):
    from databasise.seam.refusals import EmptyNamespaceError

    try:
        envelope = await _query_after_delete(store_root, "post-delete-ws")
    except EmptyNamespaceError:
        return  # the named refusal on an emptied index; any other exception is a failure
    assert list(envelope.evidence) == []


async def test_both_branches_return_between_one_and_top_k_refs_and_take_the_branch_they_name(store_root, tmp_path):
    from seam.test_hipporag_query_path import _KeepAllFactsLLMClient, _refs_over_twenty_documents
    from seam.test_hipporag_write_path import (
        _HIPPORAG_CAPABILITY,
        _StubEmbeddingClient,
        _StubIngestQueryLLMClient,
    )

    from databasise.seam import QueryObject

    async def guards_fired_by_fact_filter(root, llm):
        engine = Databasise(
            store_root=root,
            workspace="hipporag-top-k-ws",  # the workspace _refs_over_twenty_documents already filled
            clients={"embedding": _StubEmbeddingClient(), "llm": llm},
        )
        selector = Selector(capability=_HIPPORAG_CAPABILITY)
        envelope = await engine.query(QueryObject(text="What did Ed Wood direct?"), selector)
        trace = await engine.resolve_trace(envelope.trace_token, debug=True)
        node = next(n for n in trace["nodes"] if n["node_id"] == "fact-filter")
        return list(node.get("guards_fired") or [])

    dpr_refs = await _refs_over_twenty_documents(store_root, _StubIngestQueryLLMClient())
    ppr_refs = await _refs_over_twenty_documents(tmp_path / "ppr-root", _KeepAllFactsLLMClient())

    assert 0 < len(dpr_refs) <= 5
    assert 0 < len(ppr_refs) <= 5
    assert all(ref.score > 0 for ref in ppr_refs)
    assert await guards_fired_by_fact_filter(store_root, _StubIngestQueryLLMClient()) != []
    assert await guards_fired_by_fact_filter(tmp_path / "ppr-root", _KeepAllFactsLLMClient()) == []
