"""12-09-PLAN.md Task 2 (D-13, HIPP-15): the selector on the corpus read routes. A HippoRAG selector
lists and counts HippoRAG's documents over REST and MCP; a malformed selector is a 422; no selector
is the unchanged v1 path; and the read creates nothing on a fresh root (LRAG-13)."""

from __future__ import annotations

import json

import pytest

from databasise.seam.corpus import IngestDocument
from seam.test_hipporag_write_path import (
    _DOCUMENT_TEXT,
    _HIPPORAG_CAPABILITY,
    _StubEmbeddingClient,
    _StubIngestQueryLLMClient,
)

pytest.importorskip("fastapi")

_V1_CORPUS = {
    "total": 1,
    "documents": [{"document_id": "v1-doc", "status": "processed", "updated_at": "2026-01-01T00:00:00+00:00"}],
    "counts": {"processed": 1},
}
_SELECTOR = {"capability": _HIPPORAG_CAPABILITY}


@pytest.fixture
def v1_corpus(monkeypatch):
    import databasise.seam.engine as engine_module

    def _fake(op, payload, *, timeout=None, **kwargs):
        return dict(_V1_CORPUS)

    monkeypatch.setattr(engine_module, "run_corpus_op", _fake)


def _clients():
    return {"embedding": _StubEmbeddingClient(), "llm": _StubIngestQueryLLMClient()}


def _app(store_root, workspace="surface-ws"):
    from fastapi.testclient import TestClient

    from databasise.seam.rest import create_app

    return TestClient(create_app(store_root=store_root, workspace=workspace, clients=_clients()))


def test_a_malformed_selector_is_a_422_refusal_never_a_500(v1_corpus, store_root):
    client = _app(store_root)

    for path in ("/corpus", "/corpus/counts"):
        response = client.get(path, params={"selector": "not-json"})
        assert response.status_code == 422, (path, response.text)
        assert response.json()["refusal_type"]


def test_no_selector_and_a_null_selector_answer_from_v1_unchanged(v1_corpus, store_root):
    client = _app(store_root)

    plain = client.get("/corpus")
    assert plain.status_code == 200
    assert plain.json()["documents"][0]["document_id"] == "v1-doc"
    for blank in ("", "null"):
        assert client.get("/corpus", params={"selector": blank}).content == plain.content
    plain_counts = client.get("/corpus/counts")
    assert plain_counts.json() == {"by_status": {"processed": 1}, "total": 1}
    assert client.get("/corpus/counts", params={"selector": "null"}).content == plain_counts.content


def test_a_hipporag_listing_on_a_fresh_root_is_empty_and_creates_nothing(v1_corpus, store_root):
    client = _app(store_root)  # building the engine makes its own trace and job registries
    selector = json.dumps(_SELECTOR)
    before = sorted(p.relative_to(store_root) for p in store_root.rglob("*"))

    corpus = client.get("/corpus", params={"selector": selector})
    counts = client.get("/corpus/counts", params={"selector": selector})

    assert corpus.json() == {"documents": [], "counts": {}, "total": 0, "next_offset": None}
    assert counts.json() == {"by_status": {}, "total": 0}
    assert sorted(p.relative_to(store_root) for p in store_root.rglob("*")) == before
    assert not (store_root / "surface-ws").exists()


def test_pages_are_bounded_and_next_offset_is_null_on_the_last_page(v1_corpus, store_root):
    from databasise.seam import Databasise
    from databasise.seam.selectors import Selector

    import asyncio

    engine = Databasise(store_root=store_root, workspace="surface-ws", clients=_clients())
    selector = Selector(capability=_HIPPORAG_CAPABILITY)

    async def _ingest():
        for name in ("a", "ab"):
            await engine.ingest(IngestDocument(document_id=name, text=_DOCUMENT_TEXT), selector=selector)

    asyncio.run(_ingest())
    client = _app(store_root)
    params = {"selector": json.dumps(_SELECTOR)}

    first = client.get("/corpus", params={**params, "limit": 1}).json()
    last = client.get("/corpus", params={**params, "limit": 1, "offset": 1}).json()

    assert [d["document_id"] for d in first["documents"]] == ["a"] and first["next_offset"] == 1
    assert [d["document_id"] for d in last["documents"]] == ["ab"] and last["next_offset"] is None
    assert last["total"] == 2
    assert client.get("/corpus", params={**params, "limit": 0}).status_code == 422
    assert client.get("/corpus", params={**params, "offset": -1}).status_code == 422


async def test_mcp_status_corpus_and_counts_take_the_selector(v1_corpus, store_root):
    try:
        from databasise.mcp import create_server
    except ImportError:
        pytest.skip("the `mcp` extra is not installed")

    from databasise.seam import Databasise
    from databasise.seam.selectors import Selector

    engine = Databasise(store_root=store_root, workspace="surface-mcp-ws", clients=_clients())
    await engine.ingest(
        IngestDocument(document_id="mcp-doc", text=_DOCUMENT_TEXT), selector=Selector(capability=_HIPPORAG_CAPABILITY)
    )
    server = create_server(store_root=store_root, workspace="surface-mcp-ws", clients=_clients())

    def _json(result):
        return json.loads("".join(getattr(item, "text", "") or "" for item in result.content))

    corpus = _json(await server.call_tool("status", {"args": {"scope": "corpus", "selector": _SELECTOR}}))
    counts = _json(await server.call_tool("status", {"args": {"scope": "counts", "selector": _SELECTOR}}))
    plain = _json(await server.call_tool("status", {"args": {"scope": "corpus"}}))

    assert [d["document_id"] for d in corpus["documents"]] == ["mcp-doc"]
    assert counts == {"by_status": {"processed": 1}, "total": 1}
    assert plain["documents"][0]["document_id"] == "v1-doc"
