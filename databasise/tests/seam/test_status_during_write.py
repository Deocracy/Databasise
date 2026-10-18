"""LRAG-05 driver clause and research Q2 (11-03-PLAN.md Task 4): status reads answer while an
ingest subprocess holds the v1 working dir.

The driver's ``status`` op reads ``kv_store_doc_status.json`` directly, so it never opens v1's
Cozo/RocksDB store that a running ingest holds. Real driver, loopback stub model server.
"""

from __future__ import annotations

import asyncio

import databasise.seam.engine as engine_module
from databasise.clients.builder import build_clients
from databasise.seam.corpus import IngestDocument
from databasise.seam.engine import Databasise
from databasise.tests.fixtures.v1_stub_server import (  # noqa: F401 - fixture
    real_v1,
    requires_v1,
)


@requires_v1
async def test_corpus_status_and_counts_answer_while_an_ingest_holds_the_working_dir(real_v1):  # noqa: F811
    engine = Databasise(store_root=real_v1.store_root, workspace="busy", clients=build_clients(real_v1.client_env))
    real_v1.server.delay_for["UNIQbusy"] = 8.0

    ingest = asyncio.create_task(
        engine.ingest(IngestDocument(document_id="busydoc", text="UNIQbusy Corp weaves rugs in UNIQbusy City."))
    )
    for _ in range(600):  # until the delayed chat request arrives (the ingest is mid-pipeline)
        if any("UNIQbusy" in call for call in real_v1.server.chat_calls):
            break
        await asyncio.sleep(0.1)
    else:
        raise AssertionError("the ingest never reached its delayed model call")

    status = await engine.corpus_status()
    counts = await engine.document_counts()

    assert [(doc.document_id, doc.status) for doc in status.documents] == [("busydoc", "processing")]
    assert counts.by_status == {"processing": 1}

    real_v1.server.delay_for.clear()
    job = await ingest
    assert job.enqueued == 1
    assert (await engine.document_counts()).by_status == {"processed": 1}


async def test_document_counts_asks_for_a_valid_one_row_page(store_root, monkeypatch):
    # The driver refuses limit < 1 (11-03 Task 4); counts read only the whole-corpus counts.
    sent: list[dict] = []

    def fake(op, payload, **kwargs):
        sent.append(payload)
        return {"counts": {"processed": 3}, "documents": [], "total": 3}

    monkeypatch.setattr(engine_module, "run_corpus_op", fake)
    counts = await Databasise(store_root=store_root, workspace="counts").document_counts()

    assert sent == [{"track_id": None, "limit": 1, "offset": 0}]
    assert (counts.by_status, counts.total) == ({"processed": 3}, 3)
