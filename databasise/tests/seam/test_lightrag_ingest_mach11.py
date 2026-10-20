"""LRAG-03 / LRAG-02 (11-01-PLAN.md Task 2): LightRAG ingest and delete both report MACH-11 seam
events, and both come from the machine-observed touches of ``lightrag/v1-index-sync``, never from a
self-report by the v1 port (v1's subprocess changes v1's own dir, not the v2 stores).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import databasise.parts_core.lightrag.full_delete as full_delete_module
from databasise.clients.builder import build_clients
from databasise.seam.corpus import IngestDocument
from databasise.seam.engine import Databasise
from databasise.tests.fixtures.v1_stub_server import real_v1, requires_v1  # noqa: F401 - fixture

_SYNC = "mutates_store"


@requires_v1
async def test_a_lightrag_ingest_and_delete_each_report_one_event_from_the_sync(real_v1):  # noqa: F811
    engine = Databasise(
        store_root=real_v1.store_root, workspace="lrag-mach11", clients=build_clients(real_v1.client_env)
    )

    job = await engine.ingest(IngestDocument(document_id="mach11doc", text="UNIQmach Corp is in UNIQmach City."))

    assert [event.component for event in job.seam_events] == [_SYNC]
    assert job.seam_events[0].spend.counted_by == "none"

    outcome = await engine.delete_document("mach11doc")

    assert outcome.status == "success"
    assert [event.component for event in outcome.seam_events] == [_SYNC]
    assert outcome.seam_events[0].spend.counted_by == "none"


async def test_full_delete_reports_no_store_touch_of_its_own(monkeypatch):
    monkeypatch.setattr(
        full_delete_module, "run_corpus_op", lambda *a, **k: {"status": "success", "doc_id": "d", "message": "ok"}
    )

    def _no_touch(key: str) -> None:
        raise AssertionError(f"full-delete self-reported a {key!r} touch it never made")

    ctx = SimpleNamespace(config={"doc_id": "d", "working_dir": "/unused"}, record_store_touch=_no_touch)
    result: dict[str, Any] = await full_delete_module.full_delete_body(ctx)

    assert result["status"] == "success"
