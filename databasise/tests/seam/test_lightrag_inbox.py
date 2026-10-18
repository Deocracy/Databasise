"""11-05 Task 2 (LRAG-09, D-09): the raw-upload inbox is per workspace and no inbox file outlives
its job. v1 is faked at ``run_corpus_op`` (the real full-ingest and full-delete bodies run); the
ingest fake moves the staged file into ``__parsed__/`` the way v1 does after a parse (research
Finding 1), so the cleanup is checked on both copies."""

from __future__ import annotations

from pathlib import Path

import pytest

from databasise.foreign import CorpusOpSubprocessError, CorpusOpTimeoutError
from databasise.foreign.v1_corpus_adapter import MissingV1InterpreterError
from databasise.parts_core.lightrag import full_delete, full_ingest
from databasise.seam import engine as engine_module
from databasise.seam.corpus import IngestDocument
from databasise.seam.engine import Databasise
from databasise.seam.refusals import DuplicateDocumentIdError, ForeignEngineRefusalError


def _files(root: Path, workspace: str) -> list[Path]:
    inbox = root / workspace / "corpus-inbox"
    return sorted(p for p in inbox.rglob("*") if p.is_file()) if inbox.exists() else []


def _v1_like_ingest(seen: list[dict]):
    """Records what the driver would receive and moves the staged file to ``__parsed__/``."""

    def _fake(_op, payload, **_kwargs):
        staged = Path(payload["file_paths"][0])
        seen.append({"staged": staged, "existed": staged.is_file(), "input_dir": payload["input_dir"]})
        parsed = Path(payload["input_dir"]) / "__parsed__" / staged.name
        parsed.parent.mkdir(exist_ok=True)
        staged.rename(parsed)
        return {"track_id": payload["track_id"], "enqueued": 1, "usage": None}

    return _fake


def _raising(exc: BaseException):
    def _fake(*_args, **_kwargs):
        raise exc

    return _fake


def _delete(status: str):
    return lambda *_args, **_kwargs: {"status": status, "message": ""}


def _upload(document_id: str = "doc1", name: str = "a.txt", raw: bytes = b"bytes") -> IngestDocument:
    return IngestDocument(raw=raw, document_id=document_id, file_name=name)


async def test_the_same_id_in_two_workspaces_stages_at_two_inbox_paths(tmp_path, monkeypatch):
    seen: list[dict] = []
    monkeypatch.setattr(full_ingest, "run_corpus_op", _v1_like_ingest(seen))

    for workspace in ("wa", "wb"):
        await Databasise(store_root=tmp_path, workspace=workspace).ingest(_upload())

    assert [s["staged"] for s in seen] == [tmp_path / ws / "corpus-inbox" / "doc1.txt" for ws in ("wa", "wb")]
    assert all(s["existed"] for s in seen)
    assert [s["input_dir"] for s in seen] == [str(tmp_path / ws / "corpus-inbox") for ws in ("wa", "wb")]
    assert _files(tmp_path, "wa") == _files(tmp_path, "wb") == []
    assert not (tmp_path / "corpus-inbox-owners").exists()
    assert not (tmp_path / "corpus-inbox").exists()


async def test_a_successful_ingest_leaves_neither_the_staged_nor_the_parsed_copy(tmp_path, monkeypatch):
    seen: list[dict] = []
    monkeypatch.setattr(full_ingest, "run_corpus_op", _v1_like_ingest(seen))
    engine = Databasise(store_root=tmp_path, workspace="ok")

    job = await engine.ingest(_upload(name="Report.PDF"))

    assert job.enqueued == 1
    assert seen[0]["staged"].name == "doc1.pdf"
    assert _files(tmp_path, "ok") == []


async def test_an_ingest_refused_before_v1_started_leaves_no_file(tmp_path, monkeypatch):
    monkeypatch.setattr(
        full_ingest, "run_corpus_op", _raising(MissingV1InterpreterError(tmp_path / "missing-python"))
    )
    engine = Databasise(store_root=tmp_path, workspace="refused")

    with pytest.raises(ForeignEngineRefusalError) as exc_info:
        await engine.ingest(_upload())

    assert exc_info.value.failure_class == "MissingV1InterpreterError"
    assert _files(tmp_path, "refused") == []


@pytest.mark.parametrize(
    "fault",
    [
        pytest.param(CorpusOpTimeoutError("ingest", 1.0), id="timeout"),
        pytest.param(CorpusOpSubprocessError(1, "boom"), id="subprocess-failure"),
    ],
)
async def test_a_driver_fault_keeps_the_file_logs_it_once_and_a_later_delete_removes_it(
    tmp_path, monkeypatch, caplog, fault
):
    monkeypatch.setattr(full_ingest, "run_corpus_op", _raising(fault))
    engine = Databasise(store_root=tmp_path, workspace="fault")

    with caplog.at_level("WARNING", logger=engine_module.logger.name), pytest.raises(ForeignEngineRefusalError):
        await engine.ingest(_upload())

    [staged] = _files(tmp_path, "fault")
    assert staged == tmp_path / "fault" / "corpus-inbox" / "doc1.txt"
    logged = [r for r in caplog.records if "staged upload left in place" in r.getMessage()]
    assert len(logged) == 1 and str(staged) in logged[0].getMessage()

    # The kept file still guards the id against a concurrent re-upload.
    with pytest.raises(DuplicateDocumentIdError):
        await engine.ingest(_upload(raw=b"second"))
    assert staged.read_bytes() == b"bytes"

    monkeypatch.setattr(full_delete, "run_corpus_op", _delete("success"))
    assert (await engine.delete_document("doc1")).status == "success"
    assert _files(tmp_path, "fault") == []


@pytest.mark.parametrize("status", ["success", "not_found"])
async def test_delete_removes_every_inbox_file_for_the_id_and_only_that_id(tmp_path, monkeypatch, status):
    inbox = tmp_path / "del" / "corpus-inbox"
    (inbox / "__parsed__").mkdir(parents=True)
    for rel in ("doc1.txt", "__parsed__/doc1.pdf", "doc10.txt", "__parsed__/doc1-b.md"):
        (inbox / rel).write_bytes(b"x")
    monkeypatch.setattr(full_delete, "run_corpus_op", _delete(status))

    assert (await Databasise(store_root=tmp_path, workspace="del").delete_document("doc1")).status == status

    assert [p.relative_to(inbox).as_posix() for p in _files(tmp_path, "del")] == [
        "__parsed__/doc1-b.md",
        "doc10.txt",
    ]


@pytest.mark.parametrize("status", ["not_allowed", "fail"])
async def test_a_delete_v1_refused_or_failed_leaves_the_inbox_file(tmp_path, monkeypatch, status):
    monkeypatch.setattr(full_ingest, "run_corpus_op", _raising(CorpusOpTimeoutError("ingest", 1.0)))
    engine = Databasise(store_root=tmp_path, workspace="busy")
    with pytest.raises(ForeignEngineRefusalError):
        await engine.ingest(_upload())

    monkeypatch.setattr(full_delete, "run_corpus_op", _delete(status))
    assert (await engine.delete_document("doc1")).status == status

    assert len(_files(tmp_path, "busy")) == 1


async def test_another_workspaces_delete_leaves_this_workspaces_file(tmp_path, monkeypatch):
    monkeypatch.setattr(full_ingest, "run_corpus_op", _raising(CorpusOpTimeoutError("ingest", 1.0)))
    monkeypatch.setattr(full_delete, "run_corpus_op", _delete("success"))
    with pytest.raises(ForeignEngineRefusalError):
        await Databasise(store_root=tmp_path, workspace="w1").ingest(_upload())

    await Databasise(store_root=tmp_path, workspace="w2").delete_document("doc1")

    assert len(_files(tmp_path, "w1")) == 1
