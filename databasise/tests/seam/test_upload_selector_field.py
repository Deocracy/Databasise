"""09-02-PLAN.md Task 1 (SEAM-13, SEAM-02 upload half): the multipart ``selector`` form field means
the same thing the JSON routes' ``selector`` member means -- omitted, empty, whitespace-only or the
JSON literal ``null`` is "no selector" (the default); valid JSON that breaks a selector rule returns
that rule's own refusal; only unparseable JSON or a non-refusal schema error is
``MalformedSelectorPayloadError``.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

import databasise.seam.engine as engine_module
from databasise.seam.rest import create_app
from databasise.tests.seam.test_rest_corpus_endpoints import _make_registry

_HASH_A = "sha256:" + "a" * 64


@pytest.fixture
def seen_selectors(monkeypatch):
    """Records the selector every ``resolve_selector`` call receives, delegating to the original."""
    seen: list[object] = []
    original = engine_module.resolve_selector

    def _recording(selector, *args, **kwargs):
        seen.append(selector)
        return original(selector, *args, **kwargs)

    monkeypatch.setattr(engine_module, "resolve_selector", _recording)
    return seen


@pytest.fixture
def client(tmp_path):
    app = create_app(store_root=tmp_path, workspace="upload-selector", registry=_make_registry())
    return TestClient(app)


def _upload(client, **data):
    return client.post(
        "/documents/upload",
        files={"file": ("doc.txt", b"hello world", "text/plain")},
        data=data,
    )


@pytest.mark.parametrize(
    "form",
    [{}, {"selector": "null"}, {"selector": ""}, {"selector": "   "}, {"selector": "  null  "}],
    ids=["omitted", "null", "empty", "whitespace", "padded-null"],
)
def test_a_default_selector_field_ingests_with_no_selector(client, seen_selectors, form):
    response = _upload(client, **form)

    assert response.status_code == 200, response.text
    assert response.json()["enqueued"] == 1
    assert seen_selectors and all(selector is None for selector in seen_selectors)


def test_a_hash_shaped_alias_returns_the_forbidden_selector_refusal(client):
    response = _upload(client, selector='{"alias":"%s"}' % _HASH_A)

    assert response.status_code == 422
    body = response.json()
    assert body["refusal_type"] == "ForbiddenSelectorInputError"
    assert body["member_name"] == "alias"


@pytest.mark.parametrize(
    "selector",
    ['{"alias":', '{"alias": 5}', "NULL"],
    ids=["unparseable", "wrong-type", "not-the-json-literal"],
)
def test_unparseable_or_schema_broken_selector_keeps_the_malformed_payload_refusal(client, selector):
    response = _upload(client, selector=selector)

    assert response.status_code == 422
    assert response.json()["refusal_type"] == "MalformedSelectorPayloadError"
