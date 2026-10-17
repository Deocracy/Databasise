"""09-07-PLAN.md Task 1 (SEAM-10): ``Selector(capability=[])`` is refused by name on every route
that accepts a selector. It never resolves to the bypass wiring (an empty requested set is a subset
of every wiring's effects), never renders an empty compare key, and no node runs.
"""

from __future__ import annotations

import json

import pytest

pytest.importorskip("fastapi")

from databasise.parts.registry import default_registry
from databasise.seam.compare import render_selector_key
from databasise.seam.refusals import EmptyCapabilitySelectorError, UnsatisfiableSelectorError
from databasise.seam.rest import create_app
from databasise.seam.selectors import Selector, resolve_selector
from databasise.tests.seam._probes import counting_clients, inbox_files, trace_row_count
from databasise.tests.seam.conftest import synthetic_naive_store  # noqa: F401 - fixture
from databasise.tests.seam.test_rest_corpus_endpoints import _make_registry
from fastapi.testclient import TestClient

_EMPTY = {"capability": []}


@pytest.fixture
def query_setup(synthetic_naive_store):  # noqa: F811
    store = synthetic_naive_store
    clients = counting_clients(store["query_vector"])
    app = create_app(store_root=store["store_root"], workspace=store["workspace"], clients=clients)
    return TestClient(app), clients, store["store_root"]


@pytest.fixture
def ingest_client(store_root):
    app = create_app(store_root=store_root, workspace="empty-capability", registry=_make_registry())
    return TestClient(app), store_root


def _assert_refused(response) -> None:
    assert response.status_code == 422, response.text
    assert response.json()["refusal_type"] == "EmptyCapabilitySelectorError"


def _assert_no_client_calls(clients) -> None:
    assert clients["llm"].calls == 0
    assert clients["embedding"].calls == 0


# ---------------------------------------------------------------------------------------------- #
# The pure functions
# ---------------------------------------------------------------------------------------------- #


def test_resolving_an_empty_capability_selector_is_refused_every_time():
    selector = Selector(capability=[])
    for _ in range(2):
        with pytest.raises(EmptyCapabilitySelectorError):
            resolve_selector(selector, registry=default_registry())


def test_an_empty_capability_selector_renders_no_compare_key():
    with pytest.raises(EmptyCapabilitySelectorError):
        render_selector_key(Selector(capability=[]))


def test_a_named_capability_still_resolves_and_blank_ones_stay_unsatisfiable():
    assert resolve_selector(Selector(capability=["reads_vector"]), registry=default_registry())
    for blank in ("", [""]):
        with pytest.raises(UnsatisfiableSelectorError):
            resolve_selector(Selector(capability=blank), registry=default_registry())


# ---------------------------------------------------------------------------------------------- #
# REST
# ---------------------------------------------------------------------------------------------- #


def test_post_query_with_an_empty_capability_is_refused_and_runs_nothing(query_setup):
    client, clients, root = query_setup
    rows_before = trace_row_count(root)

    _assert_refused(client.post("/query", json={"query": {"text": "q"}, "selector": _EMPTY}))

    _assert_no_client_calls(clients)
    assert trace_row_count(root) == rows_before


def test_post_query_stream_with_an_empty_capability_is_refused(query_setup):
    client, clients, root = query_setup
    rows_before = trace_row_count(root)

    _assert_refused(client.post("/query/stream", json={"query": {"text": "q"}, "selector": _EMPTY}))

    _assert_no_client_calls(clients)
    assert trace_row_count(root) == rows_before


@pytest.mark.parametrize("selectors", [[_EMPTY, {}], [{}, _EMPTY]])
def test_post_compare_refuses_an_empty_capability_wherever_it_sits(query_setup, selectors):
    client, clients, root = query_setup
    rows_before = trace_row_count(root)

    _assert_refused(client.post("/compare", json={"query": {"text": "q"}, "selectors": selectors}))

    _assert_no_client_calls(clients)
    assert trace_row_count(root) == rows_before


def test_the_corpus_routes_refuse_an_empty_capability_and_enqueue_nothing(ingest_client):
    client, root = ingest_client

    _assert_refused(client.post("/documents", json={"document": {"text": "hello"}, "selector": _EMPTY}))
    _assert_refused(
        client.post(
            "/documents/upload",
            files={"file": ("a.txt", b"hello", "text/plain")},
            data={"selector": json.dumps(_EMPTY)},
        )
    )
    _assert_refused(client.request("DELETE", "/documents/x", json={"selector": _EMPTY}))

    assert inbox_files(root) == []


# ---------------------------------------------------------------------------------------------- #
# MCP
# ---------------------------------------------------------------------------------------------- #


def _tool_error_detail(exc) -> dict:
    text = str(exc)
    return json.loads(text[text.index("{") :])


def _tool_error_class():
    from databasise.mcp._sdk import import_sdk

    return import_sdk("mcp.server.mcpserver.exceptions").ToolError


async def test_mcp_query_and_compare_refuse_an_empty_capability(synthetic_naive_store):  # noqa: F811
    from databasise.mcp import create_server

    store = synthetic_naive_store
    clients = counting_clients(store["query_vector"])
    server = create_server(store_root=store["store_root"], workspace=store["workspace"], clients=clients)

    for tool, args in (
        ("query", {"query": {"text": "q"}, "selector": _EMPTY}),
        ("compare", {"query": {"text": "q"}, "selectors": [_EMPTY, {}]}),
    ):
        with pytest.raises(_tool_error_class()) as exc_info:
            await server.call_tool(tool, {"args": args})
        assert _tool_error_detail(exc_info.value)["refusal_type"] == "EmptyCapabilitySelectorError"
    _assert_no_client_calls(clients)
