"""09-01-PLAN.md Task 1 (SEAM-02, D-01): every refusal raised inside a pydantic validator on a JSON
REST route reaches the client as the one top-level refusal body -- ``{refusal_type, message,
<public attributes>}`` with no FastAPI ``detail`` wrapper. A schema error with no refusal anywhere
keeps FastAPI's own ``{detail: [...]}`` shape (the only other documented 4xx shape).
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from databasise.seam.rest import create_app

_HASH_A = "sha256:" + "a" * 64
_HASH_B = "b" * 64
_MAX_DOCUMENT_BYTES = 26_214_400


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(store_root=tmp_path, workspace="refusal-body-shape"))


def _assert_refusal(response, refusal_type):
    assert response.status_code == 422
    body = response.json()
    assert "detail" not in body
    assert body["refusal_type"] == refusal_type
    assert isinstance(body["message"], str) and body["message"]
    return body


def test_query_with_a_hash_shaped_alias_returns_the_forbidden_selector_refusal(client):
    response = client.post("/query", json={"query": {"text": "q"}, "selector": {"alias": _HASH_A}})
    body = _assert_refusal(response, "ForbiddenSelectorInputError")
    assert body["member_name"] == "alias"
    assert body["value"] == _HASH_A


def test_compare_with_a_hash_shaped_selector_at_index_one_returns_the_refusal(client):
    response = client.post(
        "/compare",
        json={"query": {"text": "q"}, "selectors": [{"alias": "ok"}, {"alias": _HASH_A}]},
    )
    _assert_refusal(response, "ForbiddenSelectorInputError")


def test_documents_with_a_hash_shaped_selector_returns_the_refusal(client):
    response = client.post(
        "/documents", json={"document": {"text": "hello"}, "selector": {"alias": _HASH_A}}
    )
    _assert_refusal(response, "ForbiddenSelectorInputError")


def test_delete_document_with_a_hash_shaped_selector_body_returns_the_refusal(client):
    response = client.request("DELETE", "/documents/doc-1", json={"selector": {"alias": _HASH_A}})
    _assert_refusal(response, "ForbiddenSelectorInputError")


def test_query_with_two_selector_members_returns_the_multi_member_refusal(client):
    response = client.post(
        "/query",
        json={"query": {"text": "q"}, "selector": {"alias": "a", "capability": ["x"]}},
    )
    body = _assert_refusal(response, "MultiMemberSelectorError")
    assert body["set_members"] == ["alias", "capability"]


def test_an_empty_ingest_document_returns_the_ambiguous_payload_refusal_with_no_members(client):
    response = client.post("/documents", json={"document": {}})
    body = _assert_refusal(response, "AmbiguousIngestPayloadError")
    assert body["set_members"] == []


def test_an_ingest_document_with_text_and_raw_returns_both_members(client):
    response = client.post("/documents", json={"document": {"text": "t", "raw": "r"}})
    body = _assert_refusal(response, "AmbiguousIngestPayloadError")
    assert body["set_members"] == ["text", "raw"]


def test_an_oversized_text_is_refused_by_byte_count_without_echoing_the_input(client):
    response = client.post(
        "/documents", json={"document": {"text": "a" * (_MAX_DOCUMENT_BYTES + 1)}}
    )
    body = _assert_refusal(response, "OversizedDocumentError")
    assert body["actual_bytes"] == _MAX_DOCUMENT_BYTES + 1
    assert body["limit_bytes"] == _MAX_DOCUMENT_BYTES
    assert len(response.content) < 4096


def test_a_schema_error_with_no_refusal_keeps_fastapis_detail_shape(client):
    response = client.post("/query", json={"query": {"text": 5}})
    assert response.status_code == 422
    body = response.json()
    assert isinstance(body["detail"], list)
    assert "refusal_type" not in body


def test_a_refusal_wins_over_a_schema_error_in_the_same_request(client):
    response = client.post(
        "/query", json={"query": {"text": 5}, "selector": {"alias": _HASH_A}}
    )
    _assert_refusal(response, "ForbiddenSelectorInputError")


def test_compare_reports_the_first_refusal_in_pydantic_error_order(client):
    response = client.post(
        "/compare",
        json={
            "query": {"text": "q"},
            "selectors": [{"alias": _HASH_A}, {"alias": _HASH_B}],
        },
    )
    body = _assert_refusal(response, "ForbiddenSelectorInputError")
    assert body["value"] == _HASH_A


def test_the_same_refused_request_returns_byte_identical_bodies(client):
    payload = {"query": {"text": "q"}, "selector": {"alias": "a", "harness": "h"}}
    first = client.post("/query", json=payload)
    second = client.post("/query", json=payload)
    assert first.status_code == second.status_code == 422
    assert first.content == second.content
