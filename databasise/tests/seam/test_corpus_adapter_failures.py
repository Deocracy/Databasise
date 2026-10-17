"""09-05-PLAN.md Task 2 (SEAM-06, D-04): a v1 adapter failure on GET /corpus, GET /corpus/counts and
GET /jobs/{id} is the same structured ForeignEngineRefusalError fault the write routes return (502
or 503, JSON body), never a text/plain 500 and never a 4xx caller refusal. OpenAPI declares it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from databasise.foreign import CorpusOpSubprocessError, CorpusOpTimeoutError, MissingV1InterpreterError
from databasise.seam import engine as engine_module
from databasise.seam.rest import create_app
from databasise.tests.seam.test_rest_corpus_endpoints import _make_registry, _patch_status_and_health

_STDERR = "Traceback (most recent call last):\n  File \"/home/x/run.py\"\nKeyError: 'LIGHTRAG_API_KEY'"

_FAULTS = [
    (MissingV1InterpreterError(Path("/nonexistent/python")), 503, "MissingV1InterpreterError"),
    (CorpusOpSubprocessError(1, _STDERR), 502, "CorpusOpSubprocessError"),
    (CorpusOpTimeoutError("status", 0.1), 503, "CorpusOpTimeoutError"),
    (json.JSONDecodeError("Expecting value", "", 0), 502, "MalformedDriverOutput"),
]
_READ_ROUTES = ["/corpus", "/corpus/counts", "/jobs/x"]


def _boom(exc: BaseException):
    def _raise(*_args: Any, **_kwargs: Any):
        raise exc

    return _raise


@pytest.fixture
def client(tmp_path):
    app = create_app(store_root=tmp_path, workspace="adapter-failures", registry=_make_registry())
    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize("route", _READ_ROUTES)
@pytest.mark.parametrize(("exc", "status", "failure_class"), _FAULTS)
def test_a_read_route_reports_an_adapter_failure_as_a_structured_fault(
    client, monkeypatch, route, exc, status, failure_class
):
    monkeypatch.setattr(engine_module, "run_corpus_op", _boom(exc))
    response = client.get(route)

    assert response.status_code == status, response.text
    assert response.headers["content-type"].startswith("application/json")
    body = response.json()
    assert body["refusal_type"] == "ForeignEngineRefusalError"
    assert body["failure_class"] == failure_class
    for forbidden in ("/home/", "Traceback", "LIGHTRAG_API_KEY"):
        assert forbidden not in response.text


@pytest.mark.parametrize(("exc", "status", "failure_class"), _FAULTS)
def test_health_stays_a_200_degraded_report(client, monkeypatch, exc, status, failure_class):
    monkeypatch.setattr(engine_module, "run_corpus_op", _boom(exc))
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"


async def test_mcp_corpus_status_fault_is_bare_json_without_stderr(tmp_path, monkeypatch):
    pytest.importorskip("mcp")
    from databasise.mcp import create_server
    from databasise.mcp._sdk import import_sdk

    tool_error = import_sdk("mcp.server.mcpserver.exceptions").ToolError
    monkeypatch.setattr(engine_module, "run_corpus_op", _boom(CorpusOpSubprocessError(1, _STDERR)))
    server = create_server(store_root=tmp_path, workspace="adapter-failures-mcp")

    with pytest.raises(tool_error) as exc_info:
        await server.call_tool("status", {"args": {"scope": "corpus"}})

    text = str(exc_info.value)
    assert text.startswith("{")
    assert json.loads(text)["refusal_type"] == "ForeignEngineRefusalError"
    assert "Traceback" not in text and "/home/" not in text


@pytest.mark.parametrize("route", ["/corpus", "/jobs/x"])
def test_a_well_formed_result_of_the_wrong_shape_is_malformed_driver_output(client, monkeypatch, route):
    monkeypatch.setattr(
        engine_module,
        "run_corpus_op",
        lambda *a, **k: {"documents": [{"bogus": 1}], "total": 1, "counts": {}},
    )
    response = client.get(route)

    assert response.status_code == 502, response.text
    assert response.json()["failure_class"] == "MalformedDriverOutput"


def test_a_zero_total_job_is_still_a_404_not_a_parse_fault(client, monkeypatch):
    _patch_status_and_health(monkeypatch, documents=[])
    response = client.get("/jobs/x")

    assert response.status_code == 404
    assert response.json()["refusal_type"] == "UnknownJobError"


def test_an_empty_driver_result_is_empty_not_a_fault(client, monkeypatch):
    monkeypatch.setattr(engine_module, "run_corpus_op", lambda *a, **k: {})

    job = client.get("/jobs/x")
    assert (job.status_code, job.json()["refusal_type"]) == (404, "UnknownJobError")
    corpus = client.get("/corpus")
    assert corpus.status_code == 200
    assert corpus.json()["total"] == 0 and corpus.json()["documents"] == []
    counts = client.get("/corpus/counts")
    assert counts.status_code == 200 and counts.json()["total"] == 0


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/corpus"),
        ("get", "/corpus/counts"),
        ("get", "/jobs/{job_id}"),
        ("post", "/documents"),
        ("post", "/documents/upload"),
        ("delete", "/documents/{document_id}"),
    ],
)
def test_openapi_declares_the_machine_fault_responses(client, method, path):
    responses = client.app.openapi()["paths"][path][method]["responses"]

    assert "502" in responses and "503" in responses
