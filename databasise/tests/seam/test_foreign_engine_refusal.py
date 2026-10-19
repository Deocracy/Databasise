"""09-05-PLAN.md Task 1 (SEAM-05, D-04): a v1 subprocess failure on a write route is a machine fault,
not a caller refusal. REST returns 502/503 by ``failure_class``, MCP returns the same bare JSON,
neither exposes stderr, a traceback, a server path or an env-var name, and the full cause is logged
server-side exactly once.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from databasise.foreign import CorpusOpSubprocessError, CorpusOpTimeoutError, MissingV1InterpreterError
from databasise.parts_core.lightrag import full_delete, full_ingest
from databasise.seam.engine import Databasise
from databasise.seam.refusals import ForeignEngineRefusalError
from databasise.seam.rest import create_app

# Non-ASCII on purpose (SEAM-05/encoding): the byte length of the body must stay under 1 KB.
_STDERR = (
    "Traceback (most recent call last):\n  File \"/home/chris/v1/run.py\", line 3\n"
    "KeyError: 'LIGHTRAG_API_KEY' é\n"
) * 30
_FORBIDDEN = ("/home/", "Traceback", "LIGHTRAG_API_KEY")


def _boom(exc: BaseException):
    def _raise(*_args, **_kwargs):
        raise exc

    return _raise


@pytest.fixture
def client(tmp_path):
    app = create_app(store_root=tmp_path, workspace="foreign-fault")
    return TestClient(app, raise_server_exceptions=False)


def _assert_clean_fault(response, *, status, operation, failure_class):
    assert response.status_code == status, response.text
    assert response.headers["content-type"].startswith("application/json")
    assert len(response.content) < 1024  # bytes, not characters
    body = response.json()
    assert body["refusal_type"] == "ForeignEngineRefusalError"
    assert body["operation"] == operation
    assert body["failure_class"] == failure_class
    text = response.content.decode("utf-8")
    for forbidden in _FORBIDDEN:
        assert forbidden not in text


def test_stderr_sized_fault_is_clean_on_delete(client, monkeypatch):
    assert len(_STDERR) > 3000 - 200
    monkeypatch.setattr(full_delete, "run_corpus_op", _boom(CorpusOpSubprocessError(1, _STDERR)))
    response = client.delete("/documents/deadbeef")
    _assert_clean_fault(response, status=502, operation="delete", failure_class="CorpusOpSubprocessError")


def test_stderr_sized_fault_is_clean_on_ingest(client, monkeypatch):
    monkeypatch.setattr(full_ingest, "run_corpus_op", _boom(CorpusOpSubprocessError(1, _STDERR)))
    response = client.post("/documents", json={"document": {"text": "x"}})
    _assert_clean_fault(response, status=502, operation="ingest", failure_class="CorpusOpSubprocessError")


@pytest.mark.parametrize(
    ("exc", "status", "failure_class"),
    [
        (CorpusOpTimeoutError("delete", 0.1), 503, "CorpusOpTimeoutError"),
        (MissingV1InterpreterError(Path("/nonexistent/python")), 503, "MissingV1InterpreterError"),
        (CorpusOpSubprocessError(1, ""), 502, "CorpusOpSubprocessError"),
        (RuntimeError("something else /home/x"), 502, "UnclassifiedEngineFailure"),
    ],
)
def test_fault_status_follows_failure_class(client, monkeypatch, exc, status, failure_class):
    monkeypatch.setattr(full_delete, "run_corpus_op", _boom(exc))
    response = client.delete("/documents/deadbeef")
    _assert_clean_fault(response, status=status, operation="delete", failure_class=failure_class)
    assert response.json()["message"]


async def test_mcp_delete_fault_is_bare_clean_json(tmp_path, monkeypatch):
    pytest.importorskip("mcp")
    from databasise.mcp import create_server
    from databasise.mcp._sdk import import_sdk

    tool_error = import_sdk("mcp.server.mcpserver.exceptions").ToolError
    monkeypatch.setattr(full_delete, "run_corpus_op", _boom(CorpusOpSubprocessError(1, _STDERR)))
    server = create_server(store_root=tmp_path, workspace="foreign-fault-mcp")

    with pytest.raises(tool_error) as exc_info:
        await server.call_tool("delete", {"args": {"document_id": "deadbeef"}})

    text = str(exc_info.value)
    assert text.startswith("{") and len(text) < 1024
    body = json.loads(text)
    assert body["refusal_type"] == "ForeignEngineRefusalError"
    for forbidden in _FORBIDDEN:
        assert forbidden not in text


def test_the_full_cause_is_logged_once_server_side(client, monkeypatch, caplog):
    cause = CorpusOpSubprocessError(1, _STDERR)
    monkeypatch.setattr(full_delete, "run_corpus_op", _boom(cause))
    with caplog.at_level(logging.ERROR, logger="databasise.seam.engine"):
        client.delete("/documents/deadbeef")

    records = [r for r in caplog.records if r.name == "databasise.seam.engine" and r.levelno == logging.ERROR]
    assert len(records) == 1
    assert "failure_class=CorpusOpSubprocessError" in records[0].getMessage()
    assert "operation=delete" in records[0].getMessage()
    assert not records[0].exc_info
    assert "detail=" in records[0].getMessage()


async def test_in_process_cause_is_readable_but_private(tmp_path, monkeypatch):
    cause = CorpusOpSubprocessError(1, _STDERR)
    monkeypatch.setattr(full_delete, "run_corpus_op", _boom(cause))
    engine = Databasise(store_root=tmp_path, workspace="foreign-fault-inproc")

    with pytest.raises(ForeignEngineRefusalError) as exc_info:
        await engine.delete_document("deadbeef")

    exc = exc_info.value
    assert exc.cause is cause
    assert "cause" not in vars(exc)
    assert exc.failure_class == "CorpusOpSubprocessError"
    assert "LIGHTRAG_API_KEY" not in str(exc) and "/home/" not in str(exc)

