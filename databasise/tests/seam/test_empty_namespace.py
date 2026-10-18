"""11-10 Task 1 (LRAG-16, D-15): a query on a never-populated vector namespace is a named
``EmptyNamespaceError`` (422, public field ``store_kind`` only) raised before any node runs, so no
model call is made and no trace is written. A populated namespace with no match, or one emptied by a
delete, keeps the plain envelope. Reading a namespace creates no directory.
"""

from __future__ import annotations

import numpy as np
import pytest
from databasise.parts_core.lightrag import chunk_vector, entity_lookup, relation_lookup
from databasise.seam import engine as engine_module
from databasise.seam.engine import Databasise
from databasise.seam.query import QueryObject
from databasise.seam.refusals import EmptyNamespaceError
from databasise.stores.vector import FaissVectorStore, MultiNamespaceVectorStore
from databasise.tests.seam._probes import counting_clients, trace_row_count
from databasise.wirings.resolve import resolve_arm

_WS = "ws"
_VECTOR = [1.0, 0.0, 0.0]
_LIGHTRAG_NAMESPACES = ("chunks", "entities", "relationships")


def _assert_no_namespace_dirs(store_root) -> None:
    for namespace in _LIGHTRAG_NAMESPACES:
        assert not (store_root / _WS / namespace).exists(), namespace


def _assert_no_calls(clients) -> None:
    assert clients["llm"].calls == 0
    assert clients["embedding"].calls == 0


async def test_a_hybrid_query_on_a_fresh_root_is_refused_before_any_model_call(store_root):
    clients = counting_clients(_VECTOR)
    engine = Databasise(store_root=store_root, workspace=_WS, clients=clients)

    with pytest.raises(EmptyNamespaceError) as caught:
        await engine._execute_resolved(QueryObject(text="q"), resolve_arm("hybrid"))

    assert caught.value.store_kind == "vector"
    _assert_no_calls(clients)
    assert trace_row_count(store_root) == 0
    _assert_no_namespace_dirs(store_root)


async def test_a_default_naive_query_on_a_fresh_root_is_refused_before_any_model_call(store_root):
    clients = counting_clients(_VECTOR)
    engine = Databasise(store_root=store_root, workspace=_WS, clients=clients)

    with pytest.raises(EmptyNamespaceError) as caught:
        await engine.query(QueryObject(text="q"))

    assert caught.value.store_kind == "vector"
    _assert_no_calls(clients)
    assert trace_row_count(store_root) == 0
    _assert_no_namespace_dirs(store_root)


def test_rest_query_on_a_fresh_root_is_a_422_naming_only_the_store_kind(store_root):
    pytest.importorskip("fastapi")
    from databasise.seam.rest import create_app
    from fastapi.testclient import TestClient

    clients = counting_clients(_VECTOR)
    client = TestClient(create_app(store_root=store_root, workspace=_WS, clients=clients))
    response = client.post("/query", json={"query": {"text": "q"}})

    assert response.status_code == 422, response.text
    body = response.json()
    assert body["refusal_type"] == "EmptyNamespaceError"
    assert set(body) == {"refusal_type", "message", "store_kind"}
    assert body["store_kind"] == "vector"
    for namespace in _LIGHTRAG_NAMESPACES:
        assert namespace not in body["message"]
    assert str(store_root) not in body["message"]
    _assert_no_calls(clients)


def test_a_populated_namespace_with_no_match_returns_the_plain_envelope(synthetic_naive_store):
    pytest.importorskip("fastapi")
    from databasise.seam.rest import create_app
    from fastapi.testclient import TestClient

    app = create_app(
        store_root=synthetic_naive_store["store_root"],
        workspace=synthetic_naive_store["workspace"],
        clients=counting_clients(synthetic_naive_store["query_vector"]),
    )
    response = TestClient(app).post("/query", json={"query": {"text": "zzz unrelated"}})

    assert response.status_code == 200, response.text
    assert "refusal_type" not in response.json()


async def test_a_namespace_emptied_by_a_delete_returns_the_plain_no_match_path(store_root):
    store = FaissVectorStore("chunks", _WS, store_root)
    await store.upsert(["c1"], np.array([_VECTOR]), [{"content": "alpha"}])
    await store.index_done_callback()
    await store.delete_by_ids(["c1"])
    await store.index_done_callback()
    assert (store_root / _WS / "chunks" / "vector.faiss").is_file()

    engine = Databasise(store_root=store_root, workspace=_WS, clients=counting_clients(_VECTOR))
    envelope = await engine.query(QueryObject(text="q"))

    assert envelope.evidence == []


async def test_select_and_read_create_no_directory_and_the_first_write_does(store_root):
    handle = MultiNamespaceVectorStore(workspace=_WS, store_root=store_root)
    child = handle.select("never-written")

    assert await child.query(_VECTOR, top_k=3) == []
    assert not (store_root / _WS / "never-written").exists()

    await child.upsert(["a"], np.array([_VECTOR]), [{"content": "alpha"}])
    await handle.index_done_callback()
    assert (store_root / _WS / "never-written" / "vector.faiss").is_file()


def test_the_engine_retrieval_namespace_table_matches_the_part_modules():
    expected = {
        chunk_vector._NAME_AT_VERSION.split("@")[0]: chunk_vector._CHUNKS_NAMESPACE,
        entity_lookup._NAME_AT_VERSION.split("@")[0]: entity_lookup._ENTITIES_NAMESPACE,
        relation_lookup._NAME_AT_VERSION.split("@")[0]: relation_lookup._RELATIONSHIPS_NAMESPACE,
    }
    assert engine_module._RETRIEVAL_NAMESPACES == expected
