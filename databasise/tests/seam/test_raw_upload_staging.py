"""09 REVIEW WR-04: a raw upload is staged in the inbox only right before the v1 run, by exclusive
create. A second upload with the same document id is refused (it never overwrites a file v1 may
still be parsing), and a request that fails before or during the run leaves no staged file."""

from __future__ import annotations

import pytest

from databasise.foreign import CorpusOpSubprocessError
from databasise.parts_core.lightrag import full_ingest
from databasise.seam import engine as engine_module
from databasise.seam.corpus import IngestDocument
from databasise.seam.engine import Databasise
from databasise.seam.refusals import DuplicateDocumentIdError, ForeignEngineRefusalError
from databasise.tests.seam._probes import inbox_files


def _ok(*_args, **_kwargs):
    return {"track_id": "t", "enqueued": 1, "usage": None}


def _fail(*_args, **_kwargs):
    raise CorpusOpSubprocessError(1, "boom")


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


async def test_a_failure_before_the_run_leaves_no_staged_file(tmp_path, monkeypatch):
    def _boom(*_args, **_kwargs):
        raise RuntimeError("store build failed")

    monkeypatch.setattr(engine_module, "_build_stores", _boom)
    engine = Databasise(store_root=tmp_path, workspace="staging-prerun")

    with pytest.raises(RuntimeError):
        await engine.ingest(_doc(b"bytes"))

    assert inbox_files(tmp_path) == []


async def test_a_faulted_run_removes_its_staged_file_so_a_retry_can_reuse_the_id(tmp_path, monkeypatch):
    monkeypatch.setattr(full_ingest, "run_corpus_op", _fail)
    engine = Databasise(store_root=tmp_path, workspace="staging-fault")

    with pytest.raises(ForeignEngineRefusalError):
        await engine.ingest(_doc(b"bytes"))
    assert inbox_files(tmp_path) == []

    monkeypatch.setattr(full_ingest, "run_corpus_op", _ok)
    job = await engine.ingest(_doc(b"bytes"))
    assert job.enqueued == 1
    assert len(inbox_files(tmp_path)) == 1
