"""09 REVIEW WR-01 / WR-02 (D-04): ``ForeignEngineRefusalError`` is the one fault type on every
corpus route. Undecodable driver bytes and ``OSError`` from the adapter are faults on the read
routes (not bare 500s), and malformed driver output on ingest and delete is a 502."""

from __future__ import annotations

from typing import Any

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from databasise.seam import engine as engine_module
from databasise.seam.rest import create_app
from databasise.tests.seam.test_rest_corpus_endpoints import _make_registry

_READ_ROUTES = ["/corpus", "/corpus/counts", "/jobs/x"]
_LEAK = "/home/chris/secret-path"


def _boom(exc: BaseException):
    def _raise(*_args: Any, **_kwargs: Any):
        raise exc

    return _raise


@pytest.fixture
def client(tmp_path):
    app = create_app(store_root=tmp_path, workspace="fault-breadth", registry=_make_registry())
    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize("route", _READ_ROUTES)
@pytest.mark.parametrize(
    ("exc", "status", "failure_class"),
    [
        (UnicodeDecodeError("utf-8", b"\xff", 0, 1, f"bad {_LEAK}"), 502, "MalformedDriverOutput"),
        (PermissionError(13, f"Permission denied: {_LEAK}"), 503, "DriverUnavailable"),
        (FileNotFoundError(2, f"No such file: {_LEAK}"), 503, "DriverUnavailable"),
    ],
)
def test_undecodable_output_and_oserror_are_structured_faults_on_read_routes(
    client, monkeypatch, route, exc, status, failure_class
):
    monkeypatch.setattr(engine_module, "run_corpus_op", _boom(exc))
    response = client.get(route)

    assert response.status_code == status, response.text
    body = response.json()
    assert body["refusal_type"] == "ForeignEngineRefusalError"
    assert body["failure_class"] == failure_class
    assert _LEAK not in response.text
