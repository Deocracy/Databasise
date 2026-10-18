"""The ``@0.2.0`` corpus driver protocol against real v1 (11-03-PLAN.md, D-06).

Real driver, real v1 pipeline, loopback stub model server (``tests/fixtures/v1_stub_server``).
Every case skips only when ``v1/.venv/bin/python`` is absent.

- file ingest through ``INPUT_DIR`` indexes the file's own bytes (LRAG-08 driver half, D-09);
- a re-ingested id reports ``enqueued: 0`` under the caller's track id (LRAG-10, D-10);
- an interrupted document is left alone by an unrelated ingest and processed by
  ``retry_doc_ids`` (LRAG-07 driver half, D-08).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from databasise.foreign import CorpusOpTimeoutError, run_corpus_op
from databasise.parts.schema import NodeContext
from databasise.parts_core.lightrag.full_ingest import full_ingest_body
from databasise.tests.fixtures.v1_stub_server import real_v1, requires_v1  # noqa: F401 - fixture

_OP_TIMEOUT = 120.0


def _wd(real_v1) -> Path:  # noqa: F811
    return real_v1.store_root / "ws" / "lightrag-v1"


def _doc_status(working_dir: Path) -> dict[str, Any]:
    return json.loads((working_dir / "kv_store_doc_status.json").read_text(encoding="utf-8"))


def _ingest(working_dir: Path, payload: dict[str, Any], *, timeout: float = _OP_TIMEOUT) -> dict[str, Any]:
    return run_corpus_op("ingest", payload, timeout=timeout, working_dir=working_dir)


def _ctx(config: dict[str, Any]) -> NodeContext:
    return NodeContext(node_id="full-ingest", config=config, inputs={}, stores={})


@requires_v1
async def test_a_file_ingest_indexes_the_files_own_bytes_through_input_dir(real_v1):  # noqa: F811
    inbox = real_v1.store_root / "ws" / "corpus-inbox"
    inbox.mkdir(parents=True)
    source = inbox / "aaa.txt"
    source.write_text("UNIQaaa Corp builds ships in UNIQaaa City.", encoding="utf-8")
    working_dir = _wd(real_v1)

    result = await full_ingest_body(
        _ctx(
            {
                "documents": [{"id": "aaa", "text": ""}],
                "file_paths": [str(source)],
                "docs_format": "pending_parse",
                "input_dir": str(inbox),
                "track_id": "t1",
                "working_dir": str(working_dir),
            }
        )
    )

    assert result["enqueued"] == 1
    assert result["track_id"] == "t1"
    chunks = json.loads((working_dir / "kv_store_text_chunks.json").read_text(encoding="utf-8"))
    assert any("UNIQaaa" in chunk.get("content", "") for chunk in chunks.values()), (
        "the chunk text did not come from the staged file's bytes"
    )
    [(v1_id, row)] = _doc_status(working_dir).items()
    assert v1_id.startswith("doc-"), "a file ingest must go through v1's file path, not ids="
    assert Path(row["file_path"]).stem == "aaa"
    assert row["status"] == "processed"


@requires_v1
def test_re_ingesting_an_id_reports_zero_enqueued_under_the_callers_track_id(real_v1):  # noqa: F811
    working_dir = _wd(real_v1)
    doc = {"id": "dupdoc", "text": "UNIQdup Corp sells maps in UNIQdup City."}

    first = _ingest(working_dir, {"documents": [doc], "track_id": "d1"})
    second = _ingest(working_dir, {"documents": [doc], "track_id": "d2"})

    assert first["enqueued"] == 1
    assert second["enqueued"] == 0
    assert second["track_id"] == "d2"


@requires_v1
def test_an_interrupted_document_is_left_alone_until_retry_doc_ids_names_it(real_v1):  # noqa: F811
    working_dir = _wd(real_v1)
    real_v1.server.delay_for["UNIQslow"] = 60.0
    slow = {"id": "slowdoc", "text": "UNIQslow Corp makes clocks in UNIQslow City."}

    with pytest.raises(CorpusOpTimeoutError):
        _ingest(working_dir, {"documents": [slow], "track_id": "ts"}, timeout=10.0)
    assert any("UNIQslow" in call for call in real_v1.server.chat_calls), "the slow call never started"
    assert _doc_status(working_dir)["slowdoc"]["status"] == "processing"

    slow_calls_before = sum("UNIQslow" in call for call in real_v1.server.chat_calls)
    other = _ingest(
        working_dir,
        {"documents": [{"id": "otherdoc", "text": "UNIQother Corp bakes bread in UNIQother City."}], "track_id": "to"},
    )
    assert other["enqueued"] == 1
    assert _doc_status(working_dir)["slowdoc"]["status"] == "processing"
    assert sum("UNIQslow" in call for call in real_v1.server.chat_calls) == slow_calls_before, (
        "an unrelated ingest reprocessed the interrupted document"
    )

    real_v1.server.delay_for.clear()
    retried = _ingest(working_dir, {"documents": [], "track_id": "tr", "retry_doc_ids": ["slowdoc"]})

    assert retried["enqueued"] == 1
    assert retried["track_id"] == "ts", "a retry reports the document's own track id (research A9)"
    assert _doc_status(working_dir)["slowdoc"]["status"] == "processed"
