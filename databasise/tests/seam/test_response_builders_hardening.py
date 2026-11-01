"""Phase 09 hardening (fuzz F1/F1b/F5/F6, REST probe #1, phase09 N-2): no caller-derived content
can make ``seam.rest``'s two response builders raise. (a) A refusal whose echoed attribute holds a
lone surrogate still returns the documented 422 refusal body. (b) A schema error with no refusal
returns FastAPI's ``{detail: [...]}`` 422 even when the body carries NaN literals, lone surrogates
(in a value or in an object key that lands in ``loc``) or 2000-level nesting -- the error items
carry ``type``/``loc``/``msg`` only, never an ``input`` echo. (c) Every refusal that echoes a
caller value bounds that echo through one shared helper, in the attribute and in the message.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from databasise.seam.refusals import (
    DuplicateDocumentIdError,
    EmptyQueryObjectError,
    ForbiddenSelectorInputError,
    InvalidDocumentIdError,
    InvalidPromotionAliasError,
    UnsatisfiableSelectorError,
    refusal_body,
)
from databasise.seam.rest import create_app

_JSON = {"content-type": "application/json"}


@pytest.fixture
def client(tmp_path):
    app = create_app(store_root=tmp_path, workspace="response-builders-hardening")
    return TestClient(app, raise_server_exceptions=False)


def test_a_refusal_echoing_a_lone_surrogate_still_returns_the_refusal_body(client):
    response = client.post(
        "/documents", content=b'{"document": {"text": "hello", "document_id": "\\ud800"}}', headers=_JSON
    )
    assert response.status_code == 422, response.text
    body = response.json()
    assert body["refusal_type"] == "InvalidDocumentIdError"
    assert "detail" not in body
    assert body["document_id"] == "\\ud800"
    body["document_id"].encode("utf-8")


@pytest.mark.parametrize(
    "payload",
    [
        b'{"query": {"text": NaN}}',
        b'{"query": {"text": Infinity}}',
        b'{"query": {"text": ["\\ud800"]}}',
        b'{"query": {"\\ud800": 1}}',
        b'{"query": {"text": ' + b"[" * 2000 + b"]" * 2000 + b"}}",
    ],
    ids=["nan", "infinity", "surrogate-value", "surrogate-key", "deep-nesting"],
)
def test_a_schema_error_with_hostile_content_returns_a_bounded_422_detail(client, payload):
    response = client.post("/query", content=payload, headers=_JSON)
    assert response.status_code == 422, response.text
    body = response.json()
    assert "refusal_type" not in body
    assert isinstance(body["detail"], list) and body["detail"]
    for item in body["detail"]:
        assert set(item) <= {"type", "loc", "msg"}
        assert "input" not in item
    assert len(response.content) < 4096


def test_a_schema_error_detail_never_echoes_the_input(client):
    response = client.post("/query", json={"query": {"text": ["x" * 100_000 + "SENTINEL-ECHO"]}})
    assert response.status_code == 422
    assert "SENTINEL-ECHO" not in response.text
    assert len(response.content) < 4096


_LONG = "a" * 5000


@pytest.mark.parametrize(
    ("refusal", "attribute"),
    [
        (lambda: EmptyQueryObjectError({"text": _LONG}), "query_object"),
        (lambda: InvalidDocumentIdError(document_id=_LONG + "."), "document_id"),
        (lambda: ForbiddenSelectorInputError(member_name="alias", value=_LONG), "value"),
        (lambda: UnsatisfiableSelectorError(selector_kind="alias", requested=_LONG), "requested"),
        (lambda: UnsatisfiableSelectorError(selector_kind="capability", requested=[_LONG] * 500), "requested"),
        (lambda: InvalidPromotionAliasError(alias=_LONG), "alias"),
        (lambda: DuplicateDocumentIdError(document_id=_LONG), "document_id"),
    ],
    ids=[
        "EmptyQueryObjectError",
        "InvalidDocumentIdError",
        "ForbiddenSelectorInputError",
        "UnsatisfiableSelectorError-alias",
        "UnsatisfiableSelectorError-capability",
        "InvalidPromotionAliasError",
        "DuplicateDocumentIdError",
    ],
)
def test_echoed_caller_values_are_bounded_in_attribute_and_message(refusal, attribute):
    exc = refusal()
    body = refusal_body(exc)
    assert len(repr(body[attribute])) < 1000, len(repr(body[attribute]))
    assert len(body["message"]) < 1000, len(body["message"])
    assert "a" * 201 not in body["message"]


def test_a_short_echo_is_returned_unchanged():
    body = refusal_body(InvalidDocumentIdError(document_id="a.b"))
    assert body["document_id"] == "a.b"
    assert "'a.b'" in body["message"]


def test_an_overlong_document_id_refusal_is_bounded_over_rest(client):
    response = client.post("/documents", json={"document": {"text": "hello", "document_id": _LONG + "."}})
    assert response.status_code == 422, response.text
    body = response.json()
    assert body["refusal_type"] == "InvalidDocumentIdError"
    assert len(body["document_id"]) < 300
    assert len(response.content) < 2048
