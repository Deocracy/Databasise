"""LRAG-01 (11-02-PLAN.md Task 1, D-01): every LightRAG corpus op an app makes carries that app's
own per-workspace v1 working dir, ``<store_root>/<workspace>/lightrag-v1``, and two apps on two
store roots never list each other's documents.

A recording fake replaces ``run_corpus_op`` in the engine (status, counts, jobs, health) and in the
full-ingest and full-delete bodies. It keeps one document table per working dir it is handed, so a
call that reached the wrong dir would show up both in the recorded calls and in ``GET /corpus``.
The adapter case checks the job ``run_corpus_op`` builds: no ``working_dir`` key unless one is
passed, so nothing falls back to the operator corpus.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("fastapi")

import databasise.parts_core.lightrag.full_delete as full_delete_module
import databasise.parts_core.lightrag.full_ingest as full_ingest_module
import databasise.seam.engine as engine_module
from databasise.foreign.v1_corpus_adapter import run_corpus_op
from databasise.seam.rest import create_app
from fastapi.testclient import TestClient

_WS = "iso"
_OPERATOR_CORPUS = Path(__file__).resolve().parents[3] / "v1" / ".corpus_working_dir"


class _RecordingCorpus:
    """Per-working-dir document tables plus every ``(op, working_dir)`` the fake was called with."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []
        self.docs: dict[str, list[dict[str, Any]]] = {}

    def __call__(self, op: str, payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        wd = kwargs.get("working_dir")
        wd = None if wd is None else str(wd)
        self.calls.append((op, wd))
        table = self.docs.setdefault(str(wd), [])
        if op == "ingest":
            for doc in payload.get("documents") or []:
                table.append(
                    {"document_id": doc["id"], "status": "processed", "updated_at": "t", "_track_id": payload["track_id"]}
                )
            return {"track_id": payload["track_id"], "enqueued": len(payload.get("documents") or []), "usage": None}
        if op == "delete":
            before = len(table)
            table[:] = [d for d in table if d["document_id"] != payload["doc_id"]]
            status = "success" if len(table) < before else "not_found"
            code = 200 if status == "success" else 404
            return {"status": status, "doc_id": payload["doc_id"], "message": "", "status_code": code, "file_path": None}
        if op == "status":
            rows = [d for d in table if not payload.get("track_id") or d["_track_id"] == payload["track_id"]]
            page = rows[payload["offset"] : payload["offset"] + payload["limit"]]
            return {
                "counts": {"processed": len(rows)} if rows else {},
                "documents": [{k: v for k, v in d.items() if k != "_track_id"} for d in page],
                "total": len(rows),
            }
        if op == "health":
            return {"working_dir_present": True, "storages_initialized": True}
        raise AssertionError(f"unexpected op {op!r}")


@pytest.fixture
def corpus(monkeypatch) -> _RecordingCorpus:
    fake = _RecordingCorpus()
    for module in (engine_module, full_ingest_module, full_delete_module):
        monkeypatch.setattr(module, "run_corpus_op", fake)
    return fake


@pytest.fixture
def two_apps(tmp_path: Path, corpus: _RecordingCorpus):
    root_a, root_b = tmp_path / "root-a", tmp_path / "root-b"
    apps = {}
    for name, root in (("a", root_a), ("b", root_b)):
        root.mkdir()
        apps[name] = (TestClient(create_app(store_root=root, workspace=_WS)), str(root / _WS / "lightrag-v1"))
    return apps


def _calls_since(corpus: _RecordingCorpus, start: int) -> list[tuple[str, str | None]]:
    return corpus.calls[start:]


def test_every_corpus_op_on_each_app_carries_its_own_per_workspace_v1_dir(two_apps, corpus):
    (client_a, wd_a), (client_b, wd_b) = two_apps["a"], two_apps["b"]
    assert wd_a.endswith("/root-a/iso/lightrag-v1") and wd_b.endswith("/root-b/iso/lightrag-v1")

    start = len(corpus.calls)
    posted = client_a.post("/documents", json={"document": {"text": "isolation doc", "document_id": "iso1"}})
    assert posted.status_code == 200, posted.text
    job_id = posted.json()["job_id"]
    for path in ("/corpus", "/corpus/counts", f"/jobs/{job_id}", "/health"):
        assert client_a.get(path).status_code == 200, path
    calls_a = _calls_since(corpus, start)

    start = len(corpus.calls)
    for path in ("/corpus", "/corpus/counts", "/health"):
        assert client_b.get(path).status_code == 200, path
    assert client_b.get(f"/jobs/{job_id}").status_code == 404  # A's job is not B's
    assert client_b.delete("/documents/iso1").json()["status"] == "not_found"
    calls_b = _calls_since(corpus, start)

    assert {op for op, _ in calls_a} == {"ingest", "status", "health"}
    assert {op for op, _ in calls_b} == {"status", "health", "delete"}
    assert {wd for _, wd in calls_a} == {wd_a}
    assert {wd for _, wd in calls_b} == {wd_b}
    assert str(_OPERATOR_CORPUS) not in {wd for _, wd in corpus.calls}


def test_app_b_does_not_list_the_document_app_a_ingested(two_apps, corpus):
    (client_a, _), (client_b, _) = two_apps["a"], two_apps["b"]
    assert client_a.post("/documents", json={"document": {"text": "isolation doc", "document_id": "iso1"}}).status_code == 200

    listed_b = client_b.get("/corpus").json()
    assert (listed_b["total"], listed_b["documents"]) == (0, [])
    assert client_b.get("/corpus/counts").json()["total"] == 0

    listed_a = client_a.get("/corpus").json()
    assert [doc["document_id"] for doc in listed_a["documents"]] == ["iso1"]
    assert client_a.get("/corpus/counts").json()["total"] == 1


def test_a_delete_through_app_a_reaches_only_app_a_dir(two_apps, corpus):
    client_a, wd_a = two_apps["a"]
    client_a.post("/documents", json={"document": {"text": "isolation doc", "document_id": "iso1"}})

    start = len(corpus.calls)
    assert client_a.delete("/documents/iso1").json()["status"] == "success"
    assert _calls_since(corpus, start) == [("delete", wd_a)]
    assert client_a.get("/corpus").json()["total"] == 0


def _echo_script(tmp_path: Path) -> Path:
    script = tmp_path / "echo_driver.py"
    script.write_text("import sys\nsys.stdout.write(sys.stdin.read())\n", encoding="utf-8")
    return script


def test_run_corpus_op_sends_working_dir_only_when_passed(tmp_path: Path):
    empty_env = tmp_path / "empty.env"
    empty_env.write_text("", encoding="utf-8")
    common = {"timeout": 30.0, "interpreter": Path(sys.executable), "driver_script": _echo_script(tmp_path), "env_path": empty_env}

    without = run_corpus_op("status", {"track_id": None}, **common)
    assert without == {"op": "status", "track_id": None}

    with_dir = run_corpus_op("status", {"track_id": None}, working_dir=tmp_path / "wd", **common)
    assert with_dir["working_dir"] == str(tmp_path / "wd")
