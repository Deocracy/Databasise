"""09 REVIEW CR-01: NaN and +/-infinity are refused by name (``NonFiniteNumberError``) at the
``EvidenceRef.score`` and ``QueryObject.embedding`` boundary, and ``refusal_body`` never carries a
non-finite float, so no refusal can become a 500 on REST or invalid JSON on MCP."""

from __future__ import annotations

import json

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient
from pydantic import ValidationError

from databasise.seam.evidence import EvidenceRef
from databasise.seam.query import QueryObject
from databasise.seam.refusals import (
    EmptyQueryObjectError,
    NonFiniteNumberError,
    refusal_body,
    refusal_from_errors,
)
from databasise.seam.rest import create_app
from databasise.tests.seam.test_rest_corpus_endpoints import _make_registry

_JSON = {"content-type": "application/json"}


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(store_root=tmp_path, workspace="non-finite", registry=_make_registry()))


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_models_refuse_non_finite_floats_by_name(bad):
    with pytest.raises(ValidationError) as score_exc:
        EvidenceRef(ref="x", namespace="chunks", kind="text_chunk", score=bad)
    assert isinstance(refusal_from_errors(score_exc.value.errors()), NonFiniteNumberError)

    with pytest.raises(ValidationError) as embedding_exc:
        QueryObject(text="q", embedding=[0.1, bad])
    assert refusal_from_errors(embedding_exc.value.errors()).field == "embedding"


def test_finite_values_are_untouched():
    assert EvidenceRef(ref="x", namespace="chunks", kind="text_chunk", score=0.5).score == 0.5
    assert QueryObject(embedding=[0.0, -1.5]).embedding == [0.0, -1.5]


def test_rest_evidence_resolve_with_nan_score_is_a_named_422(client):
    response = client.post(
        "/evidence/resolve",
        content=b'{"ref":"x","namespace":"chunks","kind":"text_chunk","score":NaN}',
        headers=_JSON,
    )
    assert response.status_code == 422, response.text
    assert response.json()["refusal_type"] == "NonFiniteNumberError"


def test_rest_query_with_nan_embedding_and_blank_text_is_a_named_422(client):
    response = client.post(
        "/query", content=b'{"query":{"text":"  ","embedding":[NaN]}}', headers=_JSON
    )
    assert response.status_code == 422, response.text
    assert response.json()["refusal_type"] == "NonFiniteNumberError"


def test_refusal_body_replaces_a_non_finite_float_with_null_and_is_strict_json():
    # model_construct skips validation: the body builder must be safe even when a bad value got in.
    query = QueryObject.model_construct(text="  ", embedding=[float("nan"), float("inf"), 1.0])
    body = refusal_body(EmptyQueryObjectError(query))

    assert body["query_object"]["embedding"] == [None, None, 1.0]
    json.dumps(body, allow_nan=False)


async def test_mcp_resolve_with_nan_score_is_bare_strict_json(tmp_path):
    pytest.importorskip("databasise.mcp")
    from databasise.mcp import create_server
    from databasise.mcp._sdk import import_sdk

    ToolError = import_sdk("mcp.server.mcpserver.exceptions").ToolError
    server = create_server(store_root=tmp_path, workspace="non-finite-mcp")
    arguments = {
        "args": {
            "scope": "evidence",
            "evidence_ref": {
                "ref": "x", "namespace": "chunks", "kind": "text_chunk", "score": float("nan"),
            },
        }
    }
    with pytest.raises(ToolError) as exc_info:
        await server.call_tool("resolve", arguments)

    body = json.loads(str(exc_info.value), parse_constant=lambda name: pytest.fail(name))
    assert body["refusal_type"] == "NonFiniteNumberError"
