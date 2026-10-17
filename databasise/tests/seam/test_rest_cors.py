"""RUN-08 (08-08, D-12): the opt-in CORS allow-list on the REST seam.

The names this plan creates (``validate_cors_origin``, ``InvalidCorsOriginError``,
``databasise.launcher.serve_rest``) are imported inside the tests that use them, never at module
top, so the file still collects on the pre-phase tree (plan 08-10's fail-first check).
"""

from __future__ import annotations

from typing import Any

import pytest
from databasise.tests.fixtures.v1_corpus_driver_stub import _run_health, _run_status
from fastapi.testclient import TestClient

_ORIGIN = "http://localhost:5173"
_PREFLIGHT = {
    "Origin": _ORIGIN,
    "Access-Control-Request-Method": "POST",
    "Access-Control-Request-Headers": "content-type",
}


def _patch_health(monkeypatch) -> None:
    """Same seam ``test_rest_corpus_endpoints._patch_status_and_health`` patches: GET /health calls
    ``databasise.seam.engine.run_corpus_op`` (a v1 subprocess) directly."""

    def _fake(op: str, payload: dict[str, Any], *, timeout: float | None = None, **kwargs: Any):
        job = {
            **payload,
            "_stub_documents": [],
            "_stub_counts": {},
            "_stub_working_dir_present": True,
            "_stub_storages_initialized": True,
        }
        if op == "status":
            return _run_status(job)
        if op == "health":
            return _run_health(job)
        raise AssertionError(f"unexpected op {op!r}")

    monkeypatch.setattr("databasise.seam.engine.run_corpus_op", _fake)


def _client(store_root, origins) -> TestClient:
    from databasise.seam.rest import create_app

    return TestClient(create_app(store_root=store_root, workspace="cors", cors_origins=origins))


def test_listed_origin_preflight_returns_200_with_matching_allow_origin(store_root):
    response = _client(store_root, [_ORIGIN]).options("/query", headers=_PREFLIGHT)

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == _ORIGIN
    assert "POST" in response.headers["access-control-allow-methods"]


def test_listed_origin_get_health_carries_the_allow_origin_header(store_root, monkeypatch):
    _patch_health(monkeypatch)

    response = _client(store_root, [_ORIGIN]).get("/health", headers={"Origin": _ORIGIN})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == _ORIGIN


def test_listed_origin_delete_preflight_returns_200(store_root):
    headers = {"Origin": _ORIGIN, "Access-Control-Request-Method": "DELETE"}

    response = _client(store_root, [_ORIGIN]).options("/documents/doc-1", headers=headers)

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == _ORIGIN


def test_unlisted_origin_gets_no_allow_origin_header(store_root, monkeypatch):
    _patch_health(monkeypatch)
    client = _client(store_root, [_ORIGIN])
    evil = "http://evil.example"

    preflight = client.options("/query", headers={**_PREFLIGHT, "Origin": evil})
    get = client.get("/health", headers={"Origin": evil})

    assert "access-control-allow-origin" not in preflight.headers
    assert "access-control-allow-origin" not in get.headers


def test_no_origins_keeps_options_at_405_with_no_cors_headers(store_root):
    from databasise.seam.rest import create_app

    client = TestClient(create_app(store_root=store_root, workspace="cors"))

    response = client.options("/query", headers=_PREFLIGHT)

    assert response.status_code == 405
    assert not [name for name in response.headers if name.startswith("access-control-")]


@pytest.mark.parametrize(
    "origin",
    [
        "http://localhost:5173/",
        "http://localhost:5173/app",
        "*",
        "http://*.example",
        "http://localhost:5173?x=1",
        "localhost:5173",
        "",
    ],
)
def test_invalid_origins_are_refused_by_create_app(store_root, origin):
    from databasise.seam.rest import InvalidCorsOriginError, create_app

    with pytest.raises(InvalidCorsOriginError) as excinfo:
        create_app(store_root=store_root, workspace="cors", cors_origins=[origin])

    assert excinfo.value.origin == origin
    assert repr(origin) in str(excinfo.value)


def test_port_differs_means_a_different_origin(store_root):
    other = {**_PREFLIGHT, "Origin": "http://localhost:5174"}

    response = _client(store_root, [_ORIGIN]).options("/query", headers=other)

    assert "access-control-allow-origin" not in response.headers


def test_duplicate_origins_are_collapsed(store_root):
    response = _client(store_root, [_ORIGIN, _ORIGIN]).options("/query", headers=_PREFLIGHT)

    assert response.status_code == 200
    assert response.headers.get_list("access-control-allow-origin") == [_ORIGIN]
