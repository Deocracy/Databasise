"""16-07 (CONN-10): POST /chunks, the operator chunk browser.

The route pages the chunk references of the fitted modality a selector resolves to, and each reference
opens through POST /evidence/resolve. New API is reached over HTTP, so before the change each row fails
by a plain ``AssertionError`` (the route is a 404), never by an import error (16-RESEARCH Pitfall 1).
"""

from __future__ import annotations

import inspect

import pytest

pytest.importorskip("fastapi")

from databasise.seam.rest import create_app
from databasise.tests.seam.test_hipporag_write_path import (
    _DOCUMENT_TEXT,
    _HIPPORAG_CAPABILITY,
    _StubEmbeddingClient,
    _StubIngestQueryLLMClient,
)
from fastapi.testclient import TestClient

_TEXT_KEYS = {"text", "content"}


def _operator_app(store_root, *, clients=None):
    assert "operator" in inspect.signature(create_app).parameters, "create_app has no operator flag (CONN-01)"
    return create_app(store_root=store_root, workspace="ws", clients=clients, operator=True)


def test_chunks_page_lists_the_selected_modalitys_refs(tmp_path):
    root = tmp_path / "store"
    root.mkdir()
    clients = {"embedding": _StubEmbeddingClient(), "llm": _StubIngestQueryLLMClient()}
    client = TestClient(_operator_app(root, clients=clients))

    ingested = client.post(
        "/documents",
        json={
            "document": {"document_id": "chunks-doc", "text": _DOCUMENT_TEXT},
            "selector": {"capability": _HIPPORAG_CAPABILITY},
        },
    )
    assert ingested.status_code == 200, (ingested.status_code, ingested.text)

    response = client.post(
        "/chunks", json={"selector": {"capability": ["reads_graph"]}, "limit": 50, "offset": 0}
    )
    assert response.status_code == 200, (response.status_code, response.text)
    page = response.json()
    refs = page.get("refs")
    assert isinstance(refs, list) and page.get("total", 0) >= 1, page
    assert page.get("next_offset") is None, page
    for ref in refs:
        assert ref.get("namespace") == "hipporag-chunks", ref
        assert ref.get("kind") == "text_chunk", ref
        assert not (set(ref) & _TEXT_KEYS), ref
        resolved = client.post("/evidence/resolve", json=ref)
        assert resolved.status_code == 200, (resolved.status_code, resolved.text)

    # LightRAG's `chunks` namespace was never populated on this root: an empty page, and the read
    # creates nothing.
    empty = client.post("/chunks", json={"selector": None})
    assert empty.status_code == 200, (empty.status_code, empty.text)
    assert empty.json() == {"refs": [], "total": 0, "next_offset": None}
    assert not (root / "ws" / "chunks").exists()
