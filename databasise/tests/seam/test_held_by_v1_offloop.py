"""Sweep finding v1-track-id-offloop (A-CR-02 follow-up): ``_held_by_v1`` reads v1's whole
``kv_store_doc_status.json`` to recover the held row's track id. That parse runs under the D-07
write gate, so it must leave the event loop thread or every concurrent query stalls with it."""

from __future__ import annotations

import threading

import databasise.seam.engine as engine_module
from databasise.seam.engine import Databasise


async def test_held_by_v1_reads_the_track_id_off_the_loop_thread(store_root, monkeypatch):
    engine = Databasise(store_root=store_root, workspace="held-by-v1-offloop")
    status_path = engine._v1_working_dir() / engine_module._V1_DOC_STATUS_FILE
    status_path.parent.mkdir(parents=True)
    status_path.write_text("{}", encoding="utf-8")

    async def held(*args, **kwargs):
        return {"total": 1}

    threads: list[threading.Thread] = []

    def record_thread(path, document_id):
        threads.append(threading.current_thread())
        return "track-from-file"

    monkeypatch.setattr(engine_module, "_corpus_op_or_refuse", held)
    monkeypatch.setattr(engine_module, "_v1_row_track_id", record_thread)

    job = await engine._held_by_v1("doc1", "fallback-track")

    assert (job.job_id, job.enqueued) == ("track-from-file", 0)
    assert len(threads) == 1
    assert threads[0] is not threading.current_thread(), "track id parsed on the loop thread"
