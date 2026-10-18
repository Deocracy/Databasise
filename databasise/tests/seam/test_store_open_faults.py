"""Phase 10 review WR-08: a corrupt ``kv.sqlite3`` or ``graph.cozo`` raised while the engine opens its
stores is a ``ForeignEngineRefusalError(failure_class="StoreCorrupted")`` (HTTP 502), the same as a
corrupt vector index, on every route that opens stores. No raw sqlite or pycozo error reaches a caller."""

from __future__ import annotations

import pytest

from databasise.seam import Databasise, QueryObject
from databasise.seam.corpus import IngestDocument
from databasise.seam.refusals import ForeignEngineRefusalError
from databasise.stores.graph import _ClientRegistry

_WS = "open-faults"


def _corrupt_kv(store_root):
    path = store_root / _WS / "text_chunks" / "kv.sqlite3"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"this is not a sqlite database" * 20)


def _corrupt_graph(store_root):
    path = store_root / _WS / "chunk_entity_relation" / "graph.cozo"
    path.parent.mkdir(parents=True)
    path.write_text("not a database")


@pytest.mark.parametrize("corrupt", [_corrupt_kv, _corrupt_graph], ids=["kv", "graph"])
@pytest.mark.parametrize("route", ["query", "ingest", "delete"])
async def test_a_corrupt_store_at_open_is_a_store_corrupted_fault(store_root, corrupt, route):
    corrupt(store_root)
    engine = Databasise(store_root=store_root, workspace=_WS)

    with pytest.raises(ForeignEngineRefusalError) as exc_info:
        if route == "query":
            await engine.query(QueryObject(text="anything"))
        elif route == "ingest":
            await engine.ingest(IngestDocument(document_id="d1", text="some text"))
        else:
            await engine.delete_document("deadbeef")

    assert exc_info.value.failure_class == "StoreCorrupted"
    assert str(store_root) not in str(exc_info.value)
    # nothing opened before the failure is left held (the registry is process-wide, so scope to this root)
    assert [key for key in _ClientRegistry._entries if key.startswith(str(store_root))] == []
