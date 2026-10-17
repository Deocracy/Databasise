"""09-06-PLAN.md Task 2 (SEAM-09, D-08): empty or whitespace-only query text, empty or
whitespace-only document text, 0-byte uploads and empty or invalid base64 are refused by name
instead of being run or enqueued. Nothing empty reaches an LLM, a trace row or the corpus inbox.
"""

from __future__ import annotations

import base64
import json

import pytest

pytest.importorskip("fastapi")

from databasise.parts.registry import default_registry
from databasise.seam.corpus import IngestDocument
from databasise.seam.query import QueryObject, check_consumable
from databasise.seam.refusals import EmptyIngestDocumentError, EmptyQueryObjectError
from databasise.seam.rest import create_app
from databasise.tests.seam._probes import counting_clients, inbox_files, trace_row_count
from databasise.tests.seam.conftest import synthetic_naive_store  # noqa: F401 - fixture
from databasise.tests.seam.test_rest_corpus_endpoints import _make_registry
from fastapi.testclient import TestClient

_BLANK_TEXTS = ["", "   ", "\n\t　"]


@pytest.fixture
def query_setup(synthetic_naive_store):  # noqa: F811
    store = synthetic_naive_store
    clients = counting_clients(store["query_vector"])
    app = create_app(store_root=store["store_root"], workspace=store["workspace"], clients=clients)
    return TestClient(app), clients, store["store_root"]


@pytest.fixture
def ingest_client(store_root):
    app = create_app(store_root=store_root, workspace="empty-inputs", registry=_make_registry())
    return TestClient(app), store_root


def _assert_no_client_calls(clients) -> None:
    assert clients["llm"].calls == 0
    assert clients["embedding"].calls == 0


# ---------------------------------------------------------------------------------------------- #
# Queries
# ---------------------------------------------------------------------------------------------- #


@pytest.mark.parametrize("text", _BLANK_TEXTS)
def test_post_query_with_blank_text_is_refused_and_runs_nothing(query_setup, text):
    client, clients, root = query_setup
    rows_before = trace_row_count(root)

    response = client.post("/query", json={"query": {"text": text}})

    assert response.status_code == 422
    assert response.json()["refusal_type"] == "EmptyQueryObjectError"
    _assert_no_client_calls(clients)
    assert trace_row_count(root) == rows_before


def test_a_non_blank_query_still_runs_so_the_counters_are_live(query_setup):
    client, clients, root = query_setup
    rows_before = trace_row_count(root)

    response = client.post("/query", json={"query": {"text": "a"}})

    assert response.status_code == 200
    assert clients["llm"].calls > 0
    assert trace_row_count(root) == rows_before + 1


@pytest.mark.parametrize(
    "query_object",
    [
        QueryObject(text="", embedding=[1.0, 0.0, 0.0]),
        QueryObject(text="   ", predicates={"k": "v"}),
    ],
)
def test_blank_text_is_refused_as_empty_whatever_other_members_are_set(query_object):
    with pytest.raises(EmptyQueryObjectError):
        check_consumable(query_object, default_registry())


def test_a_non_blank_text_beside_an_unconsumable_member_is_still_unconsumable():
    from databasise.seam.refusals import UnconsumableQueryMemberError

    with pytest.raises(UnconsumableQueryMemberError) as exc_info:
        check_consumable(QueryObject(text="hello", embedding=[1.0, 0.0, 0.0]), default_registry())
    assert exc_info.value.member_name == "embedding"


def test_post_query_with_blank_text_and_an_embedding_is_refused_as_empty(query_setup):
    client, clients, root = query_setup
    rows_before = trace_row_count(root)

    response = client.post("/query", json={"query": {"text": "  ", "embedding": [1.0, 0.0, 0.0]}})

    assert response.status_code == 422
    assert response.json()["refusal_type"] == "EmptyQueryObjectError"
    _assert_no_client_calls(clients)
    assert trace_row_count(root) == rows_before


def test_post_query_stream_with_blank_text_is_refused(query_setup):
    client, clients, root = query_setup
    rows_before = trace_row_count(root)

    response = client.post("/query/stream", json={"query": {"text": "   "}})

    assert response.status_code == 422
    assert response.json()["refusal_type"] == "EmptyQueryObjectError"
    _assert_no_client_calls(clients)
    assert trace_row_count(root) == rows_before


def _tool_error_detail(exc) -> dict:
    text = str(exc)
    return json.loads(text[text.index("{") :])


def _tool_error_class():
    from databasise.mcp._sdk import import_sdk

    return import_sdk("mcp.server.mcpserver.exceptions").ToolError


async def test_mcp_query_and_compare_with_blank_text_are_refused(synthetic_naive_store):  # noqa: F811
    from databasise.mcp import create_server

    store = synthetic_naive_store
    clients = counting_clients(store["query_vector"])
    server = create_server(store_root=store["store_root"], workspace=store["workspace"], clients=clients)

    for tool, args in (
        ("query", {"query": {"text": "   "}}),
        ("compare", {"query": {"text": ""}, "selectors": [{}]}),
    ):
        with pytest.raises(_tool_error_class()) as exc_info:
            await server.call_tool(tool, {"args": args})
        assert _tool_error_detail(exc_info.value)["refusal_type"] == "EmptyQueryObjectError"
    _assert_no_client_calls(clients)


# ---------------------------------------------------------------------------------------------- #
# Ingest
# ---------------------------------------------------------------------------------------------- #

_SELECTORS = [None, {"capability": ["reads_graph", "reads_kv"]}]


@pytest.mark.parametrize("selector", _SELECTORS)
@pytest.mark.parametrize("text", _BLANK_TEXTS)
def test_post_documents_with_blank_text_is_refused_by_name(ingest_client, text, selector):
    client, root = ingest_client

    response = client.post("/documents", json={"document": {"text": text}, "selector": selector})

    assert response.status_code == 422
    body = response.json()
    assert body["refusal_type"] == "EmptyIngestDocumentError"
    assert body["member"] == "text"
    assert inbox_files(root) == []


def test_a_zero_byte_upload_is_refused_by_name_and_writes_nothing(ingest_client):
    client, root = ingest_client

    response = client.post("/documents/upload", files={"file": ("a.txt", b"", "text/plain")})

    assert response.status_code == 422
    body = response.json()
    assert body["refusal_type"] == "EmptyIngestDocumentError"
    assert body["member"] == "raw"
    assert inbox_files(root) == []


def test_a_one_character_text_is_accepted(ingest_client):
    client, _ = ingest_client

    response = client.post("/documents", json={"document": {"text": "a"}})

    assert response.status_code == 200


def test_the_empty_document_rule_is_a_pure_validator():
    for kwargs, member in (({"text": "  "}, "text"), ({"raw": b""}, "raw")):
        with pytest.raises(Exception) as exc_info:
            IngestDocument(**kwargs)
        original = exc_info.value
        refusal = original.errors()[0]["ctx"]["error"] if hasattr(original, "errors") else original
        assert isinstance(refusal, EmptyIngestDocumentError)
        assert refusal.member == member


async def test_mcp_ingest_refuses_empty_and_invalid_base64_and_accepts_valid(store_root):
    from databasise.mcp import create_server

    server = create_server(store_root=store_root, workspace="empty-inputs-mcp", registry=_make_registry())
    tool_error = _tool_error_class()

    cases = {
        "": "EmptyIngestDocumentError",
        "!!!!": "MalformedBase64PayloadError",
        "YW*Jj": "MalformedBase64PayloadError",
        "YW!Jj": "MalformedBase64PayloadError",
    }
    for raw_base64, refusal_type in cases.items():
        with pytest.raises(tool_error) as exc_info:
            await server.call_tool("ingest", {"args": {"raw_base64": raw_base64}})
        assert _tool_error_detail(exc_info.value)["refusal_type"] == refusal_type, raw_base64
    assert inbox_files(store_root) == []

    ok = await server.call_tool("ingest", {"args": {"raw_base64": "YWJj"}})
    assert "enqueued" in "".join(getattr(item, "text", "") or "" for item in ok.content)
    assert base64.b64decode("YWJj") == b"abc"
