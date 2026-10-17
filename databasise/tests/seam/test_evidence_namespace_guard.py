"""09-06-PLAN.md Task 1 (SEAM-01, D-05): a path-like or malformed evidence namespace is refused as
``InvalidEvidenceNamespaceError`` before any store is opened or any directory is created.

``FaissVectorStore.__init__`` joins ``store_root / workspace / namespace`` and calls ``mkdir`` on it,
so an unchecked ``../../escape_probe`` used to create a directory outside ``store_root``. These tests
build everything under ``tmp_path`` and compare a recursive listing of it before and after.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

pytest.importorskip("fastapi")

from databasise.seam import engine as engine_module
from databasise.seam.evidence import validate_evidence_namespace
from databasise.seam.refusals import InvalidEvidenceNamespaceError
from databasise.seam.rest import create_app
from databasise.tests.seam.conftest import synthetic_naive_store  # noqa: F401 - fixture
from fastapi.testclient import TestClient

_VALID_NAMESPACES = [
    "chunks",
    "entities",
    "relationships",
    "hipporag-chunks",
    "hipporag-entities",
    "hipporag-facts",
]


def _malformed_namespaces(tmp_path) -> list[str]:
    return ["../../escape_probe", "../other-ws/chunks", str(tmp_path / "abs_target"), "chunks\n", "chunks/", ""]


def _body(namespace: str, ref: str = "chunk-1") -> dict[str, Any]:
    return {"ref": ref, "namespace": namespace, "kind": "text_chunk"}


def _listing(tmp_path) -> list[str]:
    return sorted(str(path) for path in tmp_path.rglob("*"))


class _ConstructionSpy:
    """Wraps the real ``MultiNamespaceVectorStore`` and counts constructions."""

    def __init__(self, real):
        self.real = real
        self.count = 0

    def __call__(self, *args, **kwargs):
        self.count += 1
        return self.real(*args, **kwargs)


@pytest.fixture
def spy(monkeypatch):
    spy = _ConstructionSpy(engine_module.MultiNamespaceVectorStore)
    monkeypatch.setattr(engine_module, "MultiNamespaceVectorStore", spy)
    return spy


@pytest.fixture
def client(synthetic_naive_store):  # noqa: F811
    store = synthetic_naive_store
    return TestClient(create_app(store_root=store["store_root"], workspace=store["workspace"]))


def test_malformed_namespaces_are_refused_by_name_with_the_callers_namespace(client, tmp_path, spy):
    for namespace in _malformed_namespaces(tmp_path):
        response = client.post("/evidence/resolve", json=_body(namespace))
        assert response.status_code == 422, namespace
        body = response.json()
        assert body["refusal_type"] == "InvalidEvidenceNamespaceError"
        assert body["namespace"] == namespace
    assert spy.count == 0


def test_no_directory_is_created_inside_or_outside_store_root(client, tmp_path, spy):
    before = _listing(tmp_path)

    for namespace in [*_malformed_namespaces(tmp_path), "zzz"]:
        client.post("/evidence/resolve", json=_body(namespace))

    assert _listing(tmp_path) == before
    assert not (tmp_path / "escape_probe").exists()
    assert not (tmp_path / "abs_target").exists()
    assert spy.count == 0


def test_a_well_formed_unknown_namespace_is_404_and_builds_no_vector_store(client, tmp_path, spy):
    before = _listing(tmp_path)

    response = client.post("/evidence/resolve", json=_body("zzz"))

    assert response.status_code == 404
    assert response.json()["refusal_type"] == "UnresolvableEvidenceReferenceError"
    assert _listing(tmp_path) == before
    assert spy.count == 0


def test_a_valid_ref_still_resolves_and_builds_exactly_one_vector_store(client, spy):
    response = client.post("/evidence/resolve", json=_body("chunks"))

    assert response.status_code == 200
    assert response.json()["id"] == "chunk-1"
    assert response.json()["content"]
    assert spy.count == 1


def test_resolve_evidence_never_opens_the_kv_or_graph_store(synthetic_naive_store, monkeypatch):  # noqa: F811
    def _fail(*args, **kwargs):  # pragma: no cover - only runs on regression
        raise AssertionError("resolve_evidence must not call _build_stores")

    monkeypatch.setattr(engine_module, "_build_stores", _fail)
    store = synthetic_naive_store
    client = TestClient(create_app(store_root=store["store_root"], workspace=store["workspace"]))

    assert client.post("/evidence/resolve", json=_body("chunks")).status_code == 200
    assert client.post("/evidence/resolve", json=_body("zzz")).status_code == 404
    assert client.post("/evidence/resolve", json=_body("../x")).status_code == 422


def test_trailing_newline_and_slash_are_refused_while_the_bare_token_resolves(client):
    assert client.post("/evidence/resolve", json=_body("chunks")).status_code == 200
    assert client.post("/evidence/resolve", json=_body("chunks\n")).status_code == 422
    assert client.post("/evidence/resolve", json=_body("chunks/")).status_code == 422


def test_an_empty_namespace_is_refused_by_name_before_any_store(client, spy):
    response = client.post("/evidence/resolve", json=_body(""))

    assert response.status_code == 422
    assert response.json()["refusal_type"] == "InvalidEvidenceNamespaceError"
    assert spy.count == 0


def test_the_same_refused_request_twice_returns_identical_bodies_and_changes_nothing(client, tmp_path):
    before = _listing(tmp_path)

    first = client.post("/evidence/resolve", json=_body("../../escape_probe"))
    second = client.post("/evidence/resolve", json=_body("../../escape_probe"))

    assert first.status_code == second.status_code == 422
    assert first.json() == second.json()
    assert _listing(tmp_path) == before


@pytest.mark.parametrize("namespace", _VALID_NAMESPACES)
def test_validate_evidence_namespace_accepts_every_existing_namespace_name(namespace):
    validate_evidence_namespace(namespace)


@pytest.mark.parametrize("namespace", ["", "a/b", "..", "a b", "a\n", "a_b", "/abs"])
def test_validate_evidence_namespace_refuses_non_tokens(namespace):
    with pytest.raises(InvalidEvidenceNamespaceError) as exc_info:
        validate_evidence_namespace(namespace)
    assert exc_info.value.namespace == namespace


async def test_mcp_resolve_refuses_the_same_malformed_namespaces(synthetic_naive_store, tmp_path, spy):  # noqa: F811
    from databasise.mcp import create_server
    from databasise.mcp._sdk import import_sdk

    tool_error = import_sdk("mcp.server.mcpserver.exceptions").ToolError
    store = synthetic_naive_store
    server = create_server(store_root=store["store_root"], workspace=store["workspace"])
    before = _listing(tmp_path)

    for namespace in _malformed_namespaces(tmp_path):
        with pytest.raises(tool_error) as exc_info:
            await server.call_tool(
                "resolve", {"args": {"scope": "evidence", "evidence_ref": _body(namespace)}}
            )
        text = str(exc_info.value)
        detail = json.loads(text[text.index("{") :])
        assert detail["refusal_type"] == "InvalidEvidenceNamespaceError"

    assert _listing(tmp_path) == before
    assert spy.count == 0
