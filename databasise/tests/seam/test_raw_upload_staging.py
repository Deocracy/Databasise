"""09 REVIEW CR-01/WR-04, as changed by 11-05 (D-09): a raw upload is staged in its workspace's
inbox only right before the v1 run, by exclusive create under
``generated_on_disk_name(document_id, suffix)``. A second upload with the same id is refused while
the first one's file exists (it never overwrites a file v1 may still be parsing). The file is
removed after a committed run and after a failure before v1 starts; after a v1 fault (timeout,
subprocess failure, malformed output) it stays until a delete removes it. The per-workspace
lifecycle proofs live in ``test_lightrag_inbox.py``."""

from __future__ import annotations

import pytest

from databasise.foreign import CorpusOpSubprocessError, CorpusOpTimeoutError
from databasise.parts_core.lightrag import full_delete, full_ingest
from databasise.seam import engine as engine_module
from databasise.seam.corpus import IngestDocument, generated_on_disk_name
from databasise.seam.engine import Databasise
from databasise.seam.refusals import DuplicateDocumentIdError, ForeignEngineRefusalError
from databasise.tests.seam._probes import inbox_files


def _ok(*_args, **_kwargs):
    return {"track_id": "t", "enqueued": 1, "usage": None}


def _timeout(*_args, **_kwargs):
    raise CorpusOpTimeoutError("ingest", 1.0)


def _delete(status):
    return lambda *_args, **_kwargs: {"status": status, "message": ""}


def _doc(raw: bytes) -> IngestDocument:
    return IngestDocument(raw=raw, document_id="doc-1", file_name="doc.txt")


async def test_a_second_upload_while_the_first_is_staged_is_refused_and_keeps_the_first_bytes(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(full_ingest, "run_corpus_op", _timeout)
    engine = Databasise(store_root=tmp_path, workspace="staging-dup")

    with pytest.raises(ForeignEngineRefusalError):
        await engine.ingest(_doc(b"first"))
    monkeypatch.setattr(full_ingest, "run_corpus_op", _ok)
    with pytest.raises(DuplicateDocumentIdError) as exc_info:
        await engine.ingest(_doc(b"second"))

    assert exc_info.value.document_id == "doc-1"
    [staged] = inbox_files(tmp_path)
    assert staged == tmp_path / "staging-dup" / "corpus-inbox" / "doc-1.txt"
    assert staged.read_bytes() == b"first"


async def test_a_reupload_after_a_committed_run_is_staged_again(tmp_path, monkeypatch):
    staged_bytes: list[bytes] = []

    def _record(_op, payload, **_kwargs):
        staged_bytes.append(open(payload["file_paths"][0], "rb").read())  # noqa: SIM115 - test probe
        return _ok()

    monkeypatch.setattr(full_ingest, "run_corpus_op", _record)
    engine = Databasise(store_root=tmp_path, workspace="staging-again")

    await engine.ingest(_doc(b"first"))
    assert inbox_files(tmp_path) == []
    job = await engine.ingest(_doc(b"second"))

    assert job.enqueued == 1
    assert staged_bytes == [b"first", b"second"]
    assert inbox_files(tmp_path) == []


async def test_upload_fault_delete_then_reupload_of_the_same_id_is_accepted(tmp_path, monkeypatch):
    monkeypatch.setattr(full_ingest, "run_corpus_op", _timeout)
    monkeypatch.setattr(full_delete, "run_corpus_op", _delete("success"))
    engine = Databasise(store_root=tmp_path, workspace="staging-cycle")

    with pytest.raises(ForeignEngineRefusalError):
        await engine.ingest(_doc(b"first"))
    assert (await engine.delete_document("doc-1")).status == "success"
    assert inbox_files(tmp_path) == []

    monkeypatch.setattr(full_ingest, "run_corpus_op", _ok)
    assert (await engine.ingest(_doc(b"second"))).enqueued == 1


async def test_a_failure_removing_the_staged_file_does_not_fail_a_delete(tmp_path, monkeypatch):
    monkeypatch.setattr(full_delete, "run_corpus_op", _delete("success"))
    engine = Databasise(store_root=tmp_path, workspace="staging-rm-error")
    orphan = tmp_path / "staging-rm-error" / "corpus-inbox" / generated_on_disk_name("doc-1", ".txt")
    orphan.parent.mkdir(parents=True)
    orphan.write_bytes(b"x")

    def _denied(self, missing_ok=False):
        raise PermissionError("denied")

    monkeypatch.setattr(type(orphan), "unlink", _denied)

    outcome = await engine.delete_document("doc-1")

    assert outcome.status == "success"


async def test_a_failure_before_the_run_leaves_no_staged_file(tmp_path, monkeypatch):
    def _boom(*_args, **_kwargs):
        raise RuntimeError("store build failed")

    monkeypatch.setattr(engine_module, "_build_stores", _boom)
    engine = Databasise(store_root=tmp_path, workspace="staging-prerun")

    with pytest.raises(RuntimeError):
        await engine.ingest(_doc(b"bytes"))

    assert inbox_files(tmp_path) == []


@pytest.mark.parametrize(
    "fault",
    [
        pytest.param(CorpusOpTimeoutError("ingest", 1.0), id="timeout"),
        pytest.param(CorpusOpSubprocessError(1, "boom"), id="subprocess-failure"),
    ],
)
async def test_a_driver_fault_after_the_run_started_leaves_the_staged_file(tmp_path, monkeypatch, fault):
    def _raise(*_args, **_kwargs):
        raise fault

    monkeypatch.setattr(full_ingest, "run_corpus_op", _raise)
    engine = Databasise(store_root=tmp_path, workspace="staging-fault")

    with pytest.raises(ForeignEngineRefusalError):
        await engine.ingest(_doc(b"bytes"))

    [staged] = inbox_files(tmp_path)
    assert staged.read_bytes() == b"bytes"


async def test_malformed_driver_output_leaves_the_staged_file(tmp_path, monkeypatch):
    monkeypatch.setattr(
        full_ingest, "run_corpus_op", lambda *_a, **_k: {"track_id": "t", "enqueued": "many", "usage": None}
    )
    engine = Databasise(store_root=tmp_path, workspace="staging-malformed")

    with pytest.raises(ForeignEngineRefusalError) as exc_info:
        await engine.ingest(_doc(b"bytes"))

    assert exc_info.value.failure_class == "MalformedDriverOutput"
    assert len(inbox_files(tmp_path)) == 1


async def test_a_document_id_that_fits_as_a_file_name_is_staged(tmp_path, monkeypatch):
    # 251 chars + ".txt" is NAME_MAX.
    seen: list[str] = []
    monkeypatch.setattr(full_ingest, "run_corpus_op", lambda _op, payload, **_k: seen.append(payload["file_paths"][0]) or _ok())
    engine = Databasise(store_root=tmp_path, workspace="staging-long-id")

    await engine.ingest(IngestDocument(raw=b"x", document_id="d" * 251, file_name="a.txt"))

    assert [s.rsplit("/", 1)[-1] for s in seen] == [generated_on_disk_name("d" * 251, ".txt")]
