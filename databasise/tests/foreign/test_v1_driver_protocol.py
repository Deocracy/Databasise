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
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest

from databasise.foreign import CorpusOpSubprocessError, CorpusOpTimeoutError, run_corpus_op, v1_corpus_adapter
from databasise.foreign.v1_corpus_adapter import DEFAULT_V1_DRIVER_SCRIPT, DEFAULT_V1_INTERPRETER
from databasise.parts.schema import NodeContext
from databasise.parts_core.lightrag.full_ingest import full_ingest_body
from databasise.tests.fixtures.v1_stub_server import real_v1, requires_v1, write_env_overlay  # noqa: F401

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


# --------------------------------------------------------------------------------------------- #
# Task 3: delete by our id, configuration refusal (exit 3), facade-free health, no entity ops
# --------------------------------------------------------------------------------------------- #

_STUB_DRIVER = Path(__file__).resolve().parents[1] / "fixtures" / "v1_corpus_driver_stub.py"


def _raw_driver(job: dict[str, Any], env_path: Path) -> subprocess.CompletedProcess[str]:
    """The driver run the way ``run_corpus_op`` runs it, keeping stdout on a non-zero exit."""
    env = dict(os.environ)
    env.update(v1_corpus_adapter._load_env_file(env_path))
    return subprocess.run(
        [str(DEFAULT_V1_INTERPRETER), str(DEFAULT_V1_DRIVER_SCRIPT)],
        input=json.dumps(job),
        capture_output=True,
        text=True,
        cwd=str(DEFAULT_V1_INTERPRETER.parents[2]),
        env=env,
        timeout=_OP_TIMEOUT,
    )


def _overlay_values(real_v1) -> list[str]:  # noqa: F811
    values = [line.partition("=")[2] for line in real_v1.env_path.read_text(encoding="utf-8").splitlines()]
    return [value for value in values if len(value) >= 5]


@requires_v1
def test_a_file_ingested_document_is_deleted_by_our_document_id(real_v1, tmp_path):  # noqa: F811
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "filedoc.txt").write_text("UNIQfile Corp paints walls in UNIQfile City.", encoding="utf-8")
    working_dir = _wd(real_v1)
    _ingest(
        working_dir,
        {
            "documents": [{"id": "filedoc", "text": ""}],
            "file_paths": [str(inbox / "filedoc.txt")],
            "docs_format": "pending_parse",
            "input_dir": str(inbox),
            "track_id": "tf",
        },
    )
    assert any(v1_id.startswith("doc-") for v1_id in _doc_status(working_dir))

    deleted = run_corpus_op("delete", {"doc_id": "filedoc"}, timeout=_OP_TIMEOUT, working_dir=working_dir)

    assert deleted["status"] == "success"
    assert deleted["usage"]["llm"]["call_count"] >= 0
    assert _doc_status(working_dir) == {}


@requires_v1
@pytest.mark.parametrize("op", ["status", "ingest", "delete"])
def test_missing_configuration_exits_3_naming_keys_only(real_v1, tmp_path, op):  # noqa: F811
    blanked = write_env_overlay(tmp_path / "blank.env", real_v1.server.url, blank=("EMBEDDING_DIM", "LLM_MODEL"))
    job = {"op": op, "working_dir": str(_wd(real_v1)), "documents": [], "doc_id": "x", "track_id": None}

    with pytest.raises(CorpusOpSubprocessError) as raised:
        run_corpus_op(op, {k: v for k, v in job.items() if k != "op"}, timeout=_OP_TIMEOUT, env_path=blanked)
    assert raised.value.returncode == 3

    proc = _raw_driver(job, blanked)
    assert proc.returncode == 3
    expected = ["EMBEDDING_DIM"] if op == "status" else ["EMBEDDING_DIM", "LLM_MODEL"]
    assert json.loads(proc.stdout) == {"error": "v1_not_configured", "missing_keys": expected, "unsupported_keys": []}
    assert not any(value in proc.stdout for value in _overlay_values(real_v1))
    assert not _wd(real_v1).exists(), "a refused op must not create the working dir"


@requires_v1
def test_an_unsupported_backend_is_refused_by_key_name_before_v1_runs(real_v1, tmp_path):  # noqa: F811
    overlay = tmp_path / "nano.env"
    overlay.write_text(real_v1.env_path.read_text(encoding="utf-8") + "LIGHTRAG_VECTOR_STORAGE=NanoVectorDBStorage\n")
    for op in ("status", "ingest", "delete"):
        proc = _raw_driver({"op": op, "working_dir": str(_wd(real_v1)), "documents": [], "doc_id": "x"}, overlay)
        assert proc.returncode == 3, op
        assert json.loads(proc.stdout) == {
            "error": "v1_not_configured",
            "missing_keys": [],
            "unsupported_keys": ["LIGHTRAG_VECTOR_STORAGE"],
        }
        assert "NanoVectorDBStorage" not in proc.stdout

    health = run_corpus_op("health", {}, timeout=_OP_TIMEOUT, env_path=overlay, working_dir=_wd(real_v1))
    assert health == {"configured": False, "missing_keys": [], "unsupported_keys": ["LIGHTRAG_VECTOR_STORAGE"]}


@requires_v1
def test_health_reports_configuration_and_creates_no_working_dir(real_v1, tmp_path):  # noqa: F811
    working_dir = _wd(real_v1)

    assert run_corpus_op("health", {}, timeout=_OP_TIMEOUT, working_dir=working_dir) == {
        "configured": True,
        "missing_keys": [],
        "unsupported_keys": [],
    }
    blanked = write_env_overlay(tmp_path / "blank.env", real_v1.server.url, blank=("EMBEDDING_DIM", "LLM_MODEL"))
    assert run_corpus_op("health", {}, timeout=_OP_TIMEOUT, env_path=blanked, working_dir=working_dir) == {
        "configured": False,
        "missing_keys": ["EMBEDDING_DIM", "LLM_MODEL"],
        "unsupported_keys": [],
    }
    assert not working_dir.exists(), "health built the v1 facade (it created the working dir)"


@requires_v1
@pytest.mark.parametrize("op", ["entities", "entity_info"])
def test_the_entity_ops_are_refused_as_unknown(real_v1, op):  # noqa: F811
    with pytest.raises(CorpusOpSubprocessError) as raised:
        run_corpus_op(op, {"doc_id": "x", "entity_names": []}, timeout=_OP_TIMEOUT, working_dir=_wd(real_v1))
    assert raised.value.returncode == 1
    assert "UnknownOpError" in raised.value.stderr


@requires_v1
def test_status_filters_by_our_document_id_with_the_stem_rule(real_v1, tmp_path):  # noqa: F811
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "stemdoc.txt").write_text("UNIQstem Corp grows tea in UNIQstem City.", encoding="utf-8")
    working_dir = _wd(real_v1)
    _ingest(
        working_dir,
        {
            "documents": [{"id": "stemdoc", "text": ""}],
            "file_paths": [str(inbox / "stemdoc.txt")],
            "docs_format": "pending_parse",
            "input_dir": str(inbox),
            "track_id": "tstem",
        },
    )
    _ingest(working_dir, {"documents": [{"id": "tdoc", "text": "UNIQtdoc Corp fixes bikes."}], "track_id": "ttxt"})

    def status(**extra: Any) -> dict[str, Any]:
        page = {"track_id": None, "limit": 10, "offset": 0, **extra}
        return run_corpus_op("status", page, timeout=_OP_TIMEOUT, working_dir=working_dir)

    by_file = status(document_id="stemdoc")
    assert [doc["document_id"] for doc in by_file["documents"]] == ["stemdoc"]
    assert by_file["total"] == 1
    assert by_file["counts"] == {"processed": 2}, "counts are whole-corpus, never filtered"
    assert [doc["document_id"] for doc in status(document_id="tdoc")["documents"]] == ["tdoc"]
    assert sorted(doc["document_id"] for doc in status()["documents"]) == ["stemdoc", "tdoc"]
    assert [doc["document_id"] for doc in status(track_id="tstem")["documents"]] == ["stemdoc"]


@requires_v1
@pytest.mark.parametrize("page", [{"limit": -1, "offset": 0}, {"limit": 0, "offset": 0}, {"limit": 5, "offset": -1}])
def test_status_refuses_a_bad_page_by_name(real_v1, page):  # noqa: F811
    with pytest.raises(CorpusOpSubprocessError) as raised:
        run_corpus_op("status", {"track_id": None, **page}, timeout=_OP_TIMEOUT, working_dir=_wd(real_v1))
    assert raised.value.returncode == 1
    assert "InvalidPageRequestError" in raised.value.stderr


@requires_v1
def test_a_torn_doc_status_file_exits_4_and_a_missing_dir_is_an_empty_corpus(real_v1):  # noqa: F811
    working_dir = _wd(real_v1)
    page = {"track_id": None, "limit": 10, "offset": 0}
    assert run_corpus_op("status", page, timeout=_OP_TIMEOUT, working_dir=working_dir) == {
        "counts": {},
        "documents": [],
        "total": 0,
    }
    assert not working_dir.exists(), "a status read must create nothing"

    working_dir.mkdir(parents=True)
    (working_dir / "kv_store_doc_status.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(CorpusOpSubprocessError) as raised:
        run_corpus_op("status", page, timeout=_OP_TIMEOUT, working_dir=working_dir)
    assert raised.value.returncode == 4
    proc = _raw_driver({"op": "status", "working_dir": str(working_dir), **page}, real_v1.env_path)
    assert (proc.returncode, json.loads(proc.stdout)) == (4, {"error": "doc_status_unreadable"})


def test_the_stub_driver_carries_no_entity_ops():
    text = _STUB_DRIVER.read_text(encoding="utf-8")
    assert "entity_info" not in text
    assert '"entities"' not in text
