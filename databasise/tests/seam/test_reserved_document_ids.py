"""11 REVIEW A-WR-03: v1's placeholder source names are refused as caller document ids.

A text row's ``file_path`` is ``unknown_source`` (or ``no-file-path``), so the driver's id stem rule
maps such an id to every text row: a delete of ``unknown_source`` removed an unrelated document.
The seam refuses the id at validation, before any store opens or v1 is called.
"""

from __future__ import annotations

import pytest
from databasise.parts_core.lightrag import full_delete, full_ingest
from databasise.seam import engine as engine_module
from databasise.seam.corpus import IngestDocument, generated_on_disk_name
from databasise.seam.engine import Databasise
from databasise.seam.refusals import InvalidDocumentIdError

_RESERVED = ["unknown_source", "no-file-path"]


@pytest.mark.parametrize("document_id", _RESERVED)
def test_the_token_rule_refuses_v1s_reserved_source_names(document_id):
    with pytest.raises(InvalidDocumentIdError):
        generated_on_disk_name(document_id)
    assert generated_on_disk_name("unknown_source2") == "unknown_source2.bin"


@pytest.mark.parametrize("operation", ["ingest", "delete", "retry"])
@pytest.mark.parametrize("document_id", _RESERVED)
async def test_every_write_refuses_a_reserved_id_before_v1_is_called(tmp_path, monkeypatch, operation, document_id):
    calls: list[str] = []
    for module in (full_ingest, full_delete, engine_module):
        monkeypatch.setattr(module, "run_corpus_op", lambda op, *_a, **_k: calls.append(op))
    engine = Databasise(store_root=tmp_path, workspace="ws")
    write = {
        "ingest": lambda: engine.ingest(IngestDocument(document_id=document_id, text="t")),
        "delete": lambda: engine.delete_document(document_id),
        "retry": lambda: engine.retry_document(document_id),
    }[operation]

    with pytest.raises(InvalidDocumentIdError):
        await write()

    assert calls == []
    assert not (tmp_path / "ws").exists()
