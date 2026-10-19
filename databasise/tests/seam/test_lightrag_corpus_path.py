"""LRAG-02 / LRAG-01 (11-01-PLAN.md, D-01): a document ingested through the seam's LightRAG path is
what the query arms retrieve. LRAG-08 / LRAG-10 (11-05-PLAN.md, D-09, D-10): an upload is indexed
from its own bytes under the caller's id, an unsupported type is refused before any write, and a
re-ingest reports what v1 enqueued.

Real v1 driver, real v1 pipeline, loopback stub model server (``tests/fixtures/v1_stub_server``).
The v1 index lands in ``<store_root>/<workspace>/lightrag-v1`` and the ``lightrag/v1-index-sync``
node mirrors it into the v2 stores the naive arm reads. Skips only when the v1 venv is absent.
"""

from __future__ import annotations

import json
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
from databasise.tests.seam._probes import inbox_files

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


@requires_v1
def test_uat3_an_uploaded_file_resolves_to_the_callers_document_id_and_a_delete_removes_it(real_v1):  # noqa: F811
    """11-UAT item 3: v1 holds a file ingest as ``doc-<md5>``; evidence must show the caller's id."""
    client = _client(real_v1, workspace="lrag-uat3")
    up = _upload(client, "notes.txt", b"UNIQuat Corp weaves baskets.", "caller-doc")
    assert up.status_code == 200, up.text

    evidence = client.post("/query", json={"query": {"text": "UNIQuat baskets"}}).json()["evidence"]
    records = [client.post("/evidence/resolve", json=ref).json() for ref in evidence]
    chunk_records = [r for r in records if "full_doc_id" in r]
    assert chunk_records, records
    assert {r["full_doc_id"] for r in chunk_records} == {"caller-doc"}
    # Outside the sync the reader keeps v1's own id (the parity import is unchanged).
    raw = read_v1_snapshot(real_v1.store_root / "lrag-uat3" / "lightrag-v1").text_chunks
    assert raw and all(rec["full_doc_id"].startswith("doc-") for rec in raw.values()), raw

    deleted = client.delete("/documents/caller-doc")
    assert (deleted.status_code, deleted.json()["status"]) == (200, "success"), deleted.text
    assert client.get("/corpus").json()["documents"] == []
    after = client.post("/query", json={"query": {"text": "UNIQuat baskets"}})
    assert (after.status_code, after.json()["evidence"]) == (200, []), after.text


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


# --------------------------------------------------------------------------------------------- #
# 11-05 (LRAG-10, D-10): a re-ingest v1 drops reports enqueued 0 under the track id v1 recorded.
# --------------------------------------------------------------------------------------------- #


def _statuses(client: TestClient) -> dict[str, str]:
    return {d["document_id"]: d["status"] for d in client.get("/corpus").json()["documents"]}


@requires_v1
def test_redo_a_text_ingest_of_the_same_id_reports_zero_under_v1s_track_id(real_v1):  # noqa: F811
    client = _client(real_v1)
    body = {"document": {"document_id": "redo1", "text": "UNIQredo Corp mends sails."}}
    first = client.post("/documents", json=body)
    second = client.post("/documents", json=body)
    assert (first.status_code, second.status_code) == (200, 200), (first.text, second.text)

    assert (first.json()["enqueued"], second.json()["enqueued"]) == (1, 0)
    # A-CR-02: v1 already holds the id, so it is not called again; the job is the existing row's.
    job_id = second.json()["job_id"]
    assert job_id == first.json()["job_id"]
    rows = client.get(f"/jobs/{job_id}").json()["documents"]
    assert [(r["document_id"], r["status"]) for r in rows] == [("redo1", "processed")], rows
    assert _statuses(client)["redo1"] == "processed"


@requires_v1
def test_one_id_with_two_suffixes_keeps_one_row_and_a_delete_removes_it_everywhere(real_v1):  # noqa: F811
    """11 REVIEW A-CR-02: ``x.txt`` then ``x.md`` under one id used to leave two v1 rows, and a
    delete removed only one, so the document stayed queryable after a ``success``."""
    client = _client(real_v1, workspace="lrag-suffix")
    first = _upload(client, "x.txt", b"UNIQsuffix Corp grinds flour.", "sfx")
    second = _upload(client, "x.md", b"UNIQsuffix Corp grinds flour, again.", "sfx")
    assert (first.status_code, second.status_code) == (200, 200), (first.text, second.text)
    assert (first.json()["enqueued"], second.json()["enqueued"]) == (1, 0)
    assert second.json()["job_id"] == first.json()["job_id"]
    assert [d["document_id"] for d in client.get("/corpus").json()["documents"]] == ["sfx"]
    assert client.post("/query", json={"query": {"text": "UNIQsuffix flour"}}).json()["evidence"]

    deleted = client.delete("/documents/sfx")
    assert (deleted.status_code, deleted.json()["status"]) == (200, "success"), deleted.text

    assert client.get("/corpus").json()["documents"] == []
    assert read_v1_snapshot(real_v1.store_root / "lrag-suffix" / "lightrag-v1").text_chunks == {}
    after = client.post("/query", json={"query": {"text": "UNIQsuffix flour"}})
    assert (after.status_code, after.json()["evidence"]) == (200, []), after.text


async def test_an_id_v1_already_holds_is_not_sent_to_v1_again(tmp_path, monkeypatch):
    """A-CR-02 without a v1 venv: the status probe finds a row, so the v1 ingest is never called,
    nothing is staged and the job is the existing row's track id."""
    v1_dir = tmp_path / "ws" / "lightrag-v1"
    v1_dir.mkdir(parents=True)
    rows = {"doc-abc": {"status": "processed", "file_path": "held.txt", "track_id": "old-track"}}
    (v1_dir / "kv_store_doc_status.json").write_text(json.dumps(rows), encoding="utf-8")
    probes: list[dict] = []
    ingests: list[dict] = []

    def _status(op, payload, **_kwargs):
        probes.append({"op": op, **payload})
        return {"counts": {"processed": 1}, "documents": [{"document_id": "held", "status": "processed"}], "total": 1}

    monkeypatch.setattr(engine_module, "run_corpus_op", _status)
    monkeypatch.setattr(full_ingest, "run_corpus_op", lambda _op, payload, **_k: ingests.append(payload))
    engine = Databasise(store_root=tmp_path, workspace="ws")

    job = await engine.ingest(IngestDocument(raw=b"new bytes", document_id="held", file_name="held.md"))

    assert (job.job_id, job.enqueued) == ("old-track", 0)
    assert ingests == []
    assert [(p["op"], p["document_id"]) for p in probes] == [("status", "held")]
    assert inbox_files(tmp_path) == []
    assert not engine._write_gate_held()


@requires_v1
def test_the_same_bytes_under_a_new_id_report_zero_and_leave_the_first_processed(real_v1):  # noqa: F811
    client = _client(real_v1)
    data = b"UNIQsame Corp brews tea."
    first = _upload(client, "same.txt", data, "u1")
    second = _upload(client, "same.txt", data, "u2")
    assert (first.status_code, second.status_code) == (200, 200), (first.text, second.text)

    assert (first.json()["enqueued"], second.json()["enqueued"]) == (1, 0)
    assert _statuses(client)["u1"] == "processed"


@requires_v1
def test_u3_uploaded_again_after_its_job_finished_reports_zero(real_v1):  # noqa: F811
    client = _client(real_v1)
    first = _upload(client, "u3.txt", b"UNIQthree Corp sells ink.", "u3")
    assert first.status_code == 200, first.text
    assert _statuses(client)["u3"] == "processed"

    second = _upload(client, "u3.txt", b"UNIQthree Corp sells ink.", "u3")

    assert second.status_code == 200, second.text
    assert second.json()["enqueued"] == 0
    assert _statuses(client)["u3"] == "processed"
