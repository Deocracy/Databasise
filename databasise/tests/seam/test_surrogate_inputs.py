"""Fuzz F2/F3/F4: a lone surrogate (the JSON escape ``"\\ud800"``, a ``str`` Python accepts but UTF-8
cannot encode) in any caller string is refused at the input boundary as the named 422
``NonEncodableTextError`` -- before it reaches sqlite (trace store, ledger ``by_alias``) or the
run-identity hasher (``CanonicalisationError`` at ``identity/canon.py``), never a 500. The response
builders are already surrogate-safe (fuzz F1/F1b), so a 500 here means the value got through.

Every request is sent as a raw JSON body: ``json.dumps`` keeps the ``\\ud800`` escape so the server
side, not this test, turns it into the lone surrogate."""

from __future__ import annotations

import json

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from databasise.seam.rest import create_app
from databasise.tests.seam.test_rest_corpus_endpoints import _make_registry
from databasise.tests.seam.test_rest_transport import _seed_trace

SURROGATE = "\ud800"


@pytest.fixture
def client(tmp_path):
    app = create_app(store_root=tmp_path, workspace="surrogates", registry=_make_registry())
    return TestClient(app), tmp_path


def _post(client: TestClient, path: str, payload: dict):
    return client.post(path, content=json.dumps(payload), headers={"content-type": "application/json"})


def _assert_named_422(response, refusal_type: str, field: str | None = None):
    assert response.status_code == 422, response.text
    body = response.json()
    assert body["refusal_type"] == refusal_type, body
    if field is not None:
        assert body["field"] == field, body


@pytest.mark.parametrize(
    "selector",
    [{"alias": SURROGATE}, {"capability": SURROGATE}, {"capability": ["x", SURROGATE]}, {"harness": SURROGATE}],
    ids=["alias", "capability", "capability-list", "harness"],
)
def test_a_surrogate_in_any_selector_member_is_refused_before_the_registry_or_ledger(client, selector):
    app, _ = client
    response = _post(app, "/query", {"query": {"text": "q"}, "selector": selector})
    _assert_named_422(response, "NonEncodableTextError", field=next(iter(selector)))


@pytest.mark.parametrize(
    ("query", "field"),
    [
        ({"text": SURROGATE}, "text"),
        ({"text": "q", "predicates": {SURROGATE: 1}}, "predicates"),
        ({"text": "q", "predicates": {"k": [SURROGATE]}}, "predicates"),
        ({"text": "q", "profile_ref": SURROGATE}, "profile_ref"),
        ({"text": "q", "formal_query": SURROGATE}, "formal_query"),
    ],
    ids=["text", "predicate-key", "predicate-value", "profile_ref", "formal_query"],
)
def test_a_surrogate_in_any_query_member_is_refused_before_the_hasher(client, query, field):
    app, _ = client
    _assert_named_422(_post(app, "/query", {"query": query}), "NonEncodableTextError", field=field)
    _assert_named_422(
        _post(app, "/compare", {"query": query, "selectors": [{}]}), "NonEncodableTextError", field=field
    )


def test_a_surrogate_in_a_compare_selector_is_refused(client):
    app, _ = client
    response = _post(app, "/compare", {"query": {"text": "q"}, "selectors": [{"alias": SURROGATE}]})
    _assert_named_422(response, "NonEncodableTextError", field="alias")


def test_a_surrogate_in_ingest_text_is_refused_by_name_not_as_a_schema_error(client):
    app, _ = client
    response = _post(app, "/documents", {"document": {"text": "fine " + SURROGATE}})
    _assert_named_422(response, "NonEncodableTextError", field="text")


def test_a_surrogate_trace_reference_is_refused_before_sqlite(client):
    app, _ = client
    response = _post(app, "/trace/resolve", {"trace_reference": SURROGATE})
    _assert_named_422(response, "NonEncodableTextError", field="trace_reference")


@pytest.mark.parametrize("route", ["/promote", "/rollback", "/retire"])
def test_a_surrogate_promotion_trace_id_or_alias_is_refused_before_sqlite(client, route):
    app, tmp_path = client
    trace = _seed_trace(tmp_path, "naive")
    base = {"alias": "fine", "version": "1.0.0", "trace_ids": [trace], "change_origin": "human_edit"}
    if route == "/promote":
        del base["version"]
    _assert_named_422(
        _post(app, route, {**base, "trace_ids": [trace, SURROGATE]}), "NonEncodableTextError", field="trace_ids"
    )
    _assert_named_422(_post(app, route, {**base, "alias": SURROGATE}), "NonEncodableTextError", field="alias")
    # change_origin is a closed vocabulary: a surrogate is simply not a member and keeps its own refusal.
    _assert_named_422(_post(app, route, {**base, "change_origin": SURROGATE}), "InvalidChangeOriginError")


def test_a_surrogate_evidence_namespace_keeps_its_own_named_refusal(client):
    app, _ = client
    response = _post(app, "/evidence/resolve", {"ref": "r", "namespace": SURROGATE, "kind": "text_chunk"})
    _assert_named_422(response, "InvalidEvidenceNamespaceError")


def test_the_hasher_refusing_a_surrogate_is_the_same_named_refusal_not_a_500():
    """The belt behind the validators: a surrogate that reaches ``canonicalise`` (the run-identity
    hasher) is the typed ``CanonicalisationError`` the engine maps to the named refusal, never a
    raw ``UnicodeEncodeError``."""
    from databasise.identity.canon import CanonicalisationError, canonicalise

    with pytest.raises(CanonicalisationError):
        canonicalise({"config": {"text": SURROGATE}})
    with pytest.raises(CanonicalisationError):
        canonicalise({SURROGATE: 1})
