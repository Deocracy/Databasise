"""LRAG-02 / LRAG-01 (11-01-PLAN.md, D-01): a document ingested through the seam's LightRAG path is
what the query arms retrieve. LRAG-08 / LRAG-10 (11-05-PLAN.md, D-09, D-10): an upload is indexed
from its own bytes under the caller's id, an unsupported type is refused before any write, and a
re-ingest reports what v1 enqueued.

Real v1 driver, real v1 pipeline, loopback stub model server (``tests/fixtures/v1_stub_server``).
The v1 index lands in ``<store_root>/<workspace>/lightrag-v1`` and the ``lightrag/v1-index-sync``
node mirrors it into the v2 stores the naive arm reads. Skips only when the v1 venv is absent.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import databasise.seam.engine as engine_module
from databasise.clients.builder import build_clients
from databasise.parity.import_index import import_v1_index, read_v1_snapshot
from databasise.parts_core.lightrag import full_ingest
from databasise.seam.corpus import IngestDocument
from databasise.seam.engine import Databasise
from databasise.seam.query import QueryObject
from databasise.seam.rest import create_app
from databasise.stores.graph import CozoGraphStore
from databasise.stores.kv import SqliteKVStore
from databasise.stores.vector import FaissVectorStore
from databasise.tests.fixtures.v1_stub_server import real_v1, requires_v1  # noqa: F401 - fixture
from databasise.tests.parts_core.lightrag.test_v1_index_sync import mixed_v1_dir  # noqa: F401 - fixture

_WS = "lrag-path"
_TEXT = "UNIQalpha Corp builds bridges in UNIQalpha City."
_OPERATOR_CORPUS = Path(__file__).resolve().parents[3] / "v1" / ".corpus_working_dir"


def _listing(root: Path) -> dict[str, int]:
    if not root.exists():
        return {}
    return {str(p.relative_to(root)): p.stat().st_mtime_ns for p in root.rglob("*")}


def _engine(real_v1) -> Databasise:  # noqa: F811
    return Databasise(store_root=real_v1.store_root, workspace=_WS, clients=build_clients(real_v1.client_env))


@requires_v1
async def test_an_ingested_document_is_what_the_naive_arm_retrieves_and_resolves(real_v1):  # noqa: F811
    operator_before = _listing(_OPERATOR_CORPUS)
    engine = _engine(real_v1)

    job = await engine.ingest(IngestDocument(document_id="lragdoc1", text=_TEXT))

    assert job.enqueued == 1
    assert (real_v1.store_root / _WS / "lightrag-v1" / "kv_store_doc_status.json").is_file()
    assert _listing(_OPERATOR_CORPUS) == operator_before

    envelope = await engine.query(QueryObject(text="UNIQalpha bridges"))
    assert envelope.evidence, "the naive arm returned no evidence for an ingested document"
    record = await engine.resolve_evidence(envelope.evidence[0])
    assert record["full_doc_id"] == "lragdoc1"
    assert "UNIQalpha" in record["content"]


@requires_v1
def test_a_deleted_document_leaves_the_query_stores_and_its_ref_is_refused(real_v1):  # noqa: F811
    client = TestClient(
        create_app(store_root=real_v1.store_root, workspace=_WS, clients=build_clients(real_v1.client_env))
    )
    assert client.post("/documents", json={"document": {"document_id": "lragdoc1", "text": _TEXT}}).status_code == 200
    before = client.post("/query", json={"query": {"text": "UNIQalpha bridges"}}).json()["evidence"]
    assert before

    deleted = client.delete("/documents/lragdoc1")
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["status"] == "success"

    after = client.post("/query", json={"query": {"text": "UNIQalpha bridges"}})
    assert after.status_code == 200, after.text
    assert {ref["ref"] for ref in after.json()["evidence"]}.isdisjoint({ref["ref"] for ref in before})
    resolved = client.post("/evidence/resolve", json=before[0])
    # A lookup refusal: SEAM-04 maps UnresolvableEvidenceReferenceError to 404.
    assert (resolved.status_code, resolved.json()["refusal_type"]) == (404, "UnresolvableEvidenceReferenceError")


async def _seeded_rows(store_root: Path) -> tuple[set[str], set[str], set[str]]:
    kv = SqliteKVStore(namespace="text_chunks", workspace=_WS, store_root=store_root)
    chunks = FaissVectorStore(namespace="chunks", workspace=_WS, store_root=store_root)
    graph = CozoGraphStore(namespace="chunk_entity_relation", workspace=_WS, store_root=store_root)
    try:
        return (
            {cid for cid in ("c1", "c2", "c3") if await kv.get_by_id(cid) is not None},
            {cid for cid in ("c1", "c2", "c3") if chunks.get_by_id(cid) is not None},
            {nid for nid in ("A", "B", "C", "R") if await graph.has_node(nid)},
        )
    finally:
        for store in (kv, chunks, graph):
            await store.finalize()


@requires_v1
async def test_parity_imported_rows_survive_seam_writes_in_the_same_workspace(real_v1, mixed_v1_dir):  # noqa: F811
    await import_v1_index(mixed_v1_dir, real_v1.store_root, workspace=_WS)
    seeded = await _seeded_rows(real_v1.store_root)
    assert seeded == ({"c1", "c2", "c3"}, {"c1", "c2", "c3"}, {"A", "B", "C", "R"})
    engine = _engine(real_v1)

    await engine.ingest(IngestDocument(document_id="lragdoc1", text=_TEXT))
    assert (await engine.delete_document("lragdoc1")).status == "success"

    assert await _seeded_rows(real_v1.store_root) == seeded
    assert read_v1_snapshot(real_v1.store_root / _WS / "lightrag-v1").text_chunks == {}


# --------------------------------------------------------------------------------------------- #
# 11-05 (LRAG-08, D-09): uploads index their own bytes; an unsupported type writes nothing.
# --------------------------------------------------------------------------------------------- #

_UP_WS = "lrag-upload"


def _client(real_v1, workspace: str = _UP_WS) -> TestClient:  # noqa: F811
    return TestClient(
        create_app(store_root=real_v1.store_root, workspace=workspace, clients=build_clients(real_v1.client_env))
    )


def _upload(client: TestClient, name: str, data: bytes, document_id: str | None = None):
    form = {"document_id": document_id} if document_id is not None else {}
    return client.post("/documents/upload", files={"file": (name, data, "text/plain")}, data=form)


@requires_v1
def test_two_uploads_are_indexed_from_their_own_bytes_under_the_callers_ids(real_v1):  # noqa: F811
    client = _client(real_v1)
    a = _upload(client, "aaa.txt", b"UNIQaaa Corp makes rope.", "up-a")
    b = _upload(client, "bbb.txt", b"UNIQbbb Corp makes nets.", "up-b")
    assert (a.status_code, b.status_code) == (200, 200), (a.text, b.text)
    assert a.json()["enqueued"] == b.json()["enqueued"] == 1

    corpus = client.get("/corpus").json()
    assert {d["document_id"]: d["status"] for d in corpus["documents"]} == {"up-a": "processed", "up-b": "processed"}
    for job in (a, b):
        rows = client.get(f"/jobs/{job.json()['job_id']}").json()["documents"]
        assert rows and not [r for r in rows if r["document_id"].startswith("dup-")], rows

    evidence = client.post("/query", json={"query": {"text": "UNIQaaa rope"}}).json()["evidence"]
    contents = [client.post("/evidence/resolve", json=ref).json()["content"] for ref in evidence]
    assert any("UNIQaaa" in content for content in contents), contents


@pytest.mark.parametrize(("name", "suffix"), [("notes.xyz", ".xyz"), ("README", "")])
def test_an_unsupported_upload_type_is_refused_before_anything_is_written(tmp_path, monkeypatch, name, suffix):
    calls: list[tuple] = []
    monkeypatch.setattr(full_ingest, "run_corpus_op", lambda *a, **k: calls.append(a))
    monkeypatch.setattr(engine_module, "run_corpus_op", lambda *a, **k: calls.append(a))
    client = TestClient(create_app(store_root=tmp_path, workspace=_UP_WS))

    response = _upload(client, name, b"x")

    assert response.status_code == 422, response.text
    assert (response.json()["refusal_type"], response.json()["suffix"]) == ("UnsupportedUploadTypeError", suffix)
    assert not (tmp_path / _UP_WS).exists()
    assert not (tmp_path / "corpus-inbox").exists()
    assert calls == []
