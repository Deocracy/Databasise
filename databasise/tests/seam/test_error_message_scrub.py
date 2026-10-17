"""09 REVIEW WR-03: v1's free-text ``error_message`` never reaches a caller with an absolute path or a
traceback, and is length-capped. One helper (``scrub_error_message``) behind ``DocumentStatusEntry``,
so REST and MCP get the same text."""

from __future__ import annotations

import json

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from databasise.seam import engine as engine_module
from databasise.seam.corpus import (
    MAX_ERROR_MESSAGE_CHARS,
    DeletionOutcome,
    DocumentStatusEntry,
    scrub_error_message,
)
from databasise.seam.rest import create_app
from databasise.tests.seam.test_rest_corpus_endpoints import _make_registry

_RAW = "Failed parsing /home/chris/store/corpus-inbox/a.bin: bad header"
_TRACEBACK = 'Parse error\nTraceback (most recent call last):\n  File "/home/chris/v1/x.py", line 3\nKeyError'


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, None),
        (_RAW, "Failed parsing a.bin: bad header"),
        ("cannot open C:\\Users\\chris\\doc.pdf now", "cannot open doc.pdf now"),
        ("a/b stays, but (/etc/) goes", "a/b stays, but (etc) goes"),
        ("root / is bare", "root <path> is bare"),
        (_TRACEBACK, "Parse error"),
        ("Traceback (most recent call last):\n  File \"/x/y.py\"", None),
        ("", None),
        # 09 REVIEW iteration 2 WR-02: the forms the first heuristic let through.
        ("Failed parsing ~/store/a.bin", "Failed parsing a.bin"),
        ("x ~chris/s/a.bin y", "x a.bin y"),
        ("err '/home/chris/my docs/a b.bin' ok", "err 'a b.bin' ok"),
        ('err "C:\\Users\\me\\my docs\\a b.pdf" ok', 'err "a b.pdf" ok'),
        ("\\\\server\\share\\a.bin bad", "a.bin bad"),
        ("see ./store/corpus-inbox/a.bin", "see a.bin"),
        ("../../etc/passwd", "passwd"),
        ("GET http://host:8000/path/to failed", "GET <url> failed"),
        ("fetched https://h/x?k=1 and file:///home/u/a.bin", "fetched <url> and <url>"),
        ("read s3://bucket/key failed", "read <url> failed"),
    ],
)
def test_scrub_error_message(raw, expected):
    assert scrub_error_message(raw) == expected


def test_deletion_outcome_message_is_scrubbed_on_construction():
    outcome = DeletionOutcome(
        document_id="d", status="fail", message="Error while deleting: [Errno 2] '/srv/db/my store/x.json'"
    )
    assert outcome.message == "Error while deleting: [Errno 2] 'x.json'"
    assert DeletionOutcome(document_id="d", status="success", message="").message == ""


def test_rest_delete_returns_the_scrubbed_message(tmp_path, monkeypatch):
    registry = _make_registry(delete_status="fail")
    real = engine_module._node_result_or_refuse

    def _with_path(scheduled, node_id, operation):
        return {**real(scheduled, node_id, operation), "message": "boom at /home/chris/store/a.json"}

    monkeypatch.setattr(engine_module, "_node_result_or_refuse", _with_path)
    client = TestClient(create_app(store_root=tmp_path, workspace="scrub-del", registry=registry))

    response = client.delete("/documents/doc-1")

    assert response.status_code == 200, response.text
    assert response.json()["message"] == "boom at a.json"


def test_scrub_caps_length():
    assert len(scrub_error_message("x" * 5000)) == MAX_ERROR_MESSAGE_CHARS


def test_the_model_scrubs_on_construction():
    entry = DocumentStatusEntry(document_id="d", status="failed", updated_at="t", error_message=_RAW)
    assert "/home/" not in entry.error_message


def _fake_run_corpus_op(*_args, **_kwargs):
    return {
        "documents": [
            {"document_id": "d", "status": "failed", "updated_at": "t", "error_message": _RAW},
        ],
        "total": 1,
        "counts": {"failed": 1},
    }


def test_rest_status_routes_return_the_scrubbed_message(tmp_path, monkeypatch):
    monkeypatch.setattr(engine_module, "run_corpus_op", _fake_run_corpus_op)
    client = TestClient(create_app(store_root=tmp_path, workspace="scrub", registry=_make_registry()))

    for route in ("/corpus", "/jobs/j"):
        response = client.get(route)
        assert response.status_code == 200, response.text
        assert "/home/" not in response.text
        assert response.json()["documents"][0]["error_message"] == "Failed parsing a.bin: bad header"


async def test_mcp_status_returns_the_scrubbed_message(tmp_path, monkeypatch):
    pytest.importorskip("databasise.mcp")
    from databasise.mcp import create_server

    monkeypatch.setattr(engine_module, "run_corpus_op", _fake_run_corpus_op)
    server = create_server(store_root=tmp_path, workspace="scrub-mcp")

    result = await server.call_tool("status", {"args": {"scope": "corpus"}})

    assert "/home/" not in json.dumps(result, default=str)
    assert "Failed parsing a.bin: bad header" in json.dumps(result, default=str)
