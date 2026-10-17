"""09 REVIEW CR-01/WR-04: a raw upload is staged in the inbox only right before the v1 run, by
exclusive create under ``generated_on_disk_name(document_id)``. A second upload with the same
document id is refused while its staged file exists (it never overwrites a file v1 may still be
parsing). ``delete_document`` releases the staged file, so delete then re-upload always works. The
staged file is removed only for a failure before v1 starts; after the run begins (timeout, malformed
output) it stays, because v1 may hold its path."""

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


def _delete(status):
    return lambda *_args, **_kwargs: {"status": status, "message": ""}


def _doc(raw: bytes) -> IngestDocument:
    return IngestDocument(raw=raw, document_id="doc-1")


async def test_a_second_upload_with_the_same_id_is_refused_and_keeps_the_first_bytes(tmp_path, monkeypatch):
    monkeypatch.setattr(full_ingest, "run_corpus_op", _ok)
    engine = Databasise(store_root=tmp_path, workspace="staging-dup")

    await engine.ingest(_doc(b"first"))
    with pytest.raises(DuplicateDocumentIdError) as exc_info:
        await engine.ingest(_doc(b"second"))

    assert exc_info.value.document_id == "doc-1"
    [staged] = inbox_files(tmp_path)
    assert staged.read_bytes() == b"first"


async def test_upload_delete_then_reupload_of_the_same_id_is_accepted(tmp_path, monkeypatch):
    monkeypatch.setattr(full_ingest, "run_corpus_op", _ok)
    monkeypatch.setattr(full_delete, "run_corpus_op", _delete("success"))
    engine = Databasise(store_root=tmp_path, workspace="staging-cycle")

    await engine.ingest(_doc(b"first"))
    outcome = await engine.delete_document("doc-1")
    assert outcome.status == "success"
    assert inbox_files(tmp_path) == []

    job = await engine.ingest(_doc(b"second"))
    assert job.enqueued == 1
    [staged] = inbox_files(tmp_path)
    assert staged.read_bytes() == b"second"


async def test_an_orphan_without_an_owner_record_is_removed_only_when_v1_deleted_successfully(
    tmp_path, monkeypatch
):
    # Accepted limit (09 REVIEW WR-02): a file without a record is released only on v1 success, so a
    # crash orphan (which v1 never saw, hence not_found) needs manual removal.
    engine = Databasise(store_root=tmp_path, workspace="staging-orphan")
    orphan = tmp_path / "corpus-inbox" / generated_on_disk_name("doc-1")
    orphan.parent.mkdir(parents=True)
    orphan.write_bytes(b"left by a crashed upload")

    monkeypatch.setattr(full_delete, "run_corpus_op", _delete("not_found"))
    assert (await engine.delete_document("doc-1")).status == "not_found"
    assert orphan.exists()

    monkeypatch.setattr(full_delete, "run_corpus_op", _delete("success"))
    assert (await engine.delete_document("doc-1")).status == "success"
    assert not orphan.exists()


async def test_another_workspaces_delete_leaves_the_staged_file_and_owner_record(tmp_path, monkeypatch):
    monkeypatch.setattr(full_ingest, "run_corpus_op", _ok)
    monkeypatch.setattr(full_delete, "run_corpus_op", _delete("success"))
    w1 = Databasise(store_root=tmp_path, workspace="ws-one")
    w2 = Databasise(store_root=tmp_path, workspace="ws-two")
    owner = tmp_path / "corpus-inbox-owners" / generated_on_disk_name("doc-1")

    await w1.ingest(_doc(b"w1 bytes"))
    [staged] = inbox_files(tmp_path)
    assert owner.read_text() == "ws-one"

    await w2.delete_document("doc-1")
    assert staged.read_bytes() == b"w1 bytes" and owner.exists()
    with pytest.raises(DuplicateDocumentIdError):
        await w2.ingest(_doc(b"w2 bytes"))

    await w1.delete_document("doc-1")
    assert inbox_files(tmp_path) == [] and not owner.exists()
    await w2.ingest(_doc(b"w2 bytes"))
    [staged] = inbox_files(tmp_path)
    assert staged.read_bytes() == b"w2 bytes" and owner.read_text() == "ws-two"


@pytest.mark.parametrize("status", ["not_allowed", "fail"])
async def test_a_delete_v1_refused_or_failed_leaves_the_staged_file_and_owner_record(
    tmp_path, monkeypatch, status
):
    monkeypatch.setattr(full_ingest, "run_corpus_op", _ok)
    monkeypatch.setattr(full_delete, "run_corpus_op", _delete(status))
    engine = Databasise(store_root=tmp_path, workspace="staging-busy")
    owner = tmp_path / "corpus-inbox-owners" / generated_on_disk_name("doc-1")

    await engine.ingest(_doc(b"bytes"))
    assert (await engine.delete_document("doc-1")).status == status

    [staged] = inbox_files(tmp_path)
    assert staged.read_bytes() == b"bytes" and owner.read_text() == "staging-busy"


@pytest.mark.parametrize("record", [b"\xff\xfe", b"", b"  \n"], ids=["not-utf8", "empty", "blank"])
async def test_an_unreadable_or_empty_owner_record_counts_as_no_record(tmp_path, monkeypatch, record):
    monkeypatch.setattr(full_ingest, "run_corpus_op", _ok)
    monkeypatch.setattr(full_delete, "run_corpus_op", _delete("success"))
    engine = Databasise(store_root=tmp_path, workspace="staging-bad-record")
    owner = tmp_path / "corpus-inbox-owners" / generated_on_disk_name("doc-1")

    await engine.ingest(_doc(b"bytes"))
    owner.write_bytes(record)

    assert (await engine.delete_document("doc-1")).status == "success"
    assert inbox_files(tmp_path) == [] and not owner.exists()


async def test_the_owner_record_is_written_atomically(tmp_path, monkeypatch):
    monkeypatch.setattr(full_ingest, "run_corpus_op", _ok)
    engine = Databasise(store_root=tmp_path, workspace="staging-atomic")

    await engine.ingest(_doc(b"bytes"))

    assert [p.name for p in (tmp_path / "corpus-inbox-owners").iterdir()] == [generated_on_disk_name("doc-1")]


async def test_a_failed_owner_record_write_removes_the_staged_file(tmp_path, monkeypatch):
    monkeypatch.setattr(full_ingest, "run_corpus_op", _ok)
    (tmp_path / "corpus-inbox-owners").write_text("a file where the directory should be")
    engine = Databasise(store_root=tmp_path, workspace="staging-owner-fail")

    with pytest.raises(OSError):
        await engine.ingest(_doc(b"bytes"))

    assert inbox_files(tmp_path) == []


async def test_a_failure_removing_the_staged_file_does_not_fail_a_delete(tmp_path, monkeypatch):
    monkeypatch.setattr(full_delete, "run_corpus_op", _delete("success"))
    engine = Databasise(store_root=tmp_path, workspace="staging-rm-error")
    orphan = tmp_path / "corpus-inbox" / generated_on_disk_name("doc-1")
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


async def test_a_fault_after_the_run_started_logs_the_staged_path_once(tmp_path, monkeypatch, caplog):
    def _raise(*_args, **_kwargs):
        raise CorpusOpTimeoutError("ingest", 1.0)

    monkeypatch.setattr(full_ingest, "run_corpus_op", _raise)
    engine = Databasise(store_root=tmp_path, workspace="staging-log")

    with caplog.at_level("WARNING", logger=engine_module.logger.name), pytest.raises(ForeignEngineRefusalError):
        await engine.ingest(_doc(b"bytes"))

    [staged] = inbox_files(tmp_path)
    logged = [r for r in caplog.records if "staged upload left in place" in r.getMessage()]
    assert len(logged) == 1 and str(staged) in logged[0].getMessage()


async def test_a_document_id_that_fits_as_a_file_name_also_fits_its_owner_record_temp_file(tmp_path, monkeypatch):
    # 251 chars + ".bin" is NAME_MAX; the owner record's temp name must not add the id again.
    monkeypatch.setattr(full_ingest, "run_corpus_op", _ok)
    engine = Databasise(store_root=tmp_path, workspace="staging-long-id")

    await engine.ingest(IngestDocument(raw=b"x", document_id="d" * 251))

    [staged] = inbox_files(tmp_path)
    assert staged.name == generated_on_disk_name("d" * 251)
