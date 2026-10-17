"""09-02-PLAN.md Task 3 (SEAM-04, D-03): the HTTP status of a refusal comes from one function,
``rest._status_for``. 404 for the four lookups of a caller-supplied reference that names nothing
(trace reference, job id, evidence reference, generation version); 422 for every other refusal.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from databasise.seam import refusals
from databasise.seam.rest import _status_for, create_app
from databasise.tests.seam.test_rest_corpus_endpoints import _make_registry, _patch_status_and_health
from databasise.tests.seam.test_rest_transport import _REFUSAL_FACTORIES, _seed_trace

_NOT_FOUND = {
    "UnknownTraceReferenceError",
    "UnknownJobError",
    "UnresolvableEvidenceReferenceError",
    "UnknownGenerationVersionError",
}
# ForeignEngineRefusalError is a fault, not a caller refusal; 09-05 gives it its own status.
_MAPPED_ELSEWHERE = {"ForeignEngineRefusalError"}
_CATALOGUE = sorted(
    name
    for name in refusals.__all__
    if name != "SeamRefusalError" and name not in _MAPPED_ELSEWHERE
)


@pytest.fixture
def client(tmp_path):
    app = create_app(store_root=tmp_path, workspace="refusal-status", registry=_make_registry())
    return TestClient(app)


def _assert_refusal(response, status, refusal_type):
    assert response.status_code == status, response.text
    assert response.json()["refusal_type"] == refusal_type


@pytest.mark.parametrize("reference", ["nope", ""])
def test_an_unknown_or_empty_trace_reference_is_a_404(client, reference):
    response = client.post("/trace/resolve", json={"trace_reference": reference})
    _assert_refusal(response, 404, "UnknownTraceReferenceError")


def test_an_unknown_job_id_is_a_404(client, monkeypatch):
    _patch_status_and_health(monkeypatch, documents=[])
    _assert_refusal(client.get("/jobs/job-missing"), 404, "UnknownJobError")


def test_rolling_back_to_a_never_promoted_version_is_a_404(client, tmp_path):
    trace = _seed_trace(tmp_path, "naive")
    response = client.post(
        "/rollback",
        json={
            "alias": "never-promoted",
            "version": "9.9.9",
            "trace_ids": [trace],
            "change_origin": "human_edit",
        },
    )
    _assert_refusal(response, 404, "UnknownGenerationVersionError")


def test_an_unresolvable_evidence_reference_is_a_404(synthetic_naive_store):
    app = create_app(
        store_root=synthetic_naive_store["store_root"], workspace=synthetic_naive_store["workspace"]
    )
    response = TestClient(app).post(
        "/evidence/resolve", json={"ref": "missing", "namespace": "chunks", "kind": "text_chunk"}
    )
    _assert_refusal(response, 404, "UnresolvableEvidenceReferenceError")


def test_a_page_size_above_the_cap_is_still_a_422(client):
    _assert_refusal(client.get("/corpus?limit=101"), 422, "PageSizeExceededError")


def test_a_selector_naming_a_never_promoted_alias_is_a_422_not_a_404(client):
    response = client.post(
        "/query", json={"query": {"text": "q"}, "selector": {"alias": "never-promoted"}}
    )
    _assert_refusal(response, 422, "UnsatisfiableSelectorError")


@pytest.mark.parametrize("name", _CATALOGUE)
def test_status_for_maps_exactly_the_four_lookups_to_404_and_every_other_refusal_to_422(name):
    exc_cls = getattr(refusals, name)
    assert exc_cls in _REFUSAL_FACTORIES, f"{name} has no factory in test_rest_transport"
    expected = 404 if name in _NOT_FOUND else 422
    assert _status_for(_REFUSAL_FACTORIES[exc_cls]()) == expected
