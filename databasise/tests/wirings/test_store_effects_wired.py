"""10-12-PLAN.md (STOR-12, D-15, Q5): every store effect in the vocabulary either resolves to a
wired store or is refused at parse time.

``reads_lexical``, ``writes_lexical`` and ``reads_blob`` have no store after D-15, so a node
declaring one (on the node or its resolved part) gets the accumulated violation
``unwired-store-effect``. Through the seam, any non-ok parse report becomes the named refusal
``UnparseableWiringError`` (422) before a store is built, never a later 500.
"""

from __future__ import annotations

import pytest

from databasise.parts.registry import default_registry
from databasise.parts.schema import Part
from databasise.seam import Databasise, QueryObject
from databasise.seam import engine as engine_module
from databasise.seam.corpus import IngestDocument
from databasise.seam.refusals import UnparseableWiringError
from databasise.validator.errors import CODE_EFFECTS_EXCEED_PART, CODE_UNWIRED_STORE_EFFECT
from databasise.validator.parse import parse_wiring

_WORKSPACE = "stor12-ws"
_UNWIRED = ["reads_lexical", "writes_lexical", "reads_blob"]


async def _touch_lexical_body(ctx):
    return {"hits": ctx.stores["lexical"]}


def _fixture_part(effect: str) -> Part:
    return Part(
        name_at_version=f"test-fixture/{effect}@1.0.0",
        kind="test-fixture",
        structural_depth="stage",
        effects=[effect],
        upstream_ref=None,
        body=_touch_lexical_body,
    )


def _registry():
    registry = default_registry()
    for effect in _UNWIRED:
        registry.register(_fixture_part(effect))
    return registry


def _wiring(effect: str, node_effects: list[str] | None = None, **extra) -> dict:
    return {
        "wiring_id": "unwired-fixture",
        "wiring_version": "1",
        "nodes": {
            "lex": {
                "component": f"test-fixture/{effect}@1.0.0",
                "kind": "test-fixture",
                "effects": node_effects if node_effects is not None else [effect],
                "deps": [],
            }
        },
        "recipe": {},
        "provides": ["lex"],
        **extra,
    }


@pytest.fixture
def build_calls(monkeypatch):
    calls: list[tuple] = []
    real = engine_module._build_stores

    def spy(*args, **kwargs):
        calls.append(args)
        return real(*args, **kwargs)

    monkeypatch.setattr(engine_module, "_build_stores", spy)
    return calls


# --------------------------------------------------------------------------------------------- #
# Task 1: the parse check and the seam refusal
# --------------------------------------------------------------------------------------------- #


@pytest.mark.parametrize("effect", _UNWIRED)
def test_a_node_declaring_a_store_less_store_effect_is_refused_at_parse(effect):
    parsed = parse_wiring(_wiring(effect), _registry())

    assert not parsed.report.ok
    hits = [v for v in parsed.report.violations if v.code == CODE_UNWIRED_STORE_EFFECT]
    assert len(hits) == 1
    assert hits[0].pointer == "/nodes/lex/effects"
    assert effect in hits[0].message


def test_the_part_effect_alone_triggers_the_check_when_the_node_declares_narrower():
    parsed = parse_wiring(_wiring("reads_blob", node_effects=[]), _registry())

    assert CODE_UNWIRED_STORE_EFFECT in {v.code for v in parsed.report.violations}


def test_unwired_store_effect_accumulates_with_effects_exceed_part():
    parsed = parse_wiring(_wiring("reads_lexical", node_effects=["reads_lexical", "reads_kv"]), _registry())

    codes = [v.code for v in parsed.report.violations]
    assert CODE_UNWIRED_STORE_EFFECT in codes
    assert CODE_EFFECTS_EXCEED_PART in codes


async def test_query_is_refused_before_any_store_is_built(store_root, monkeypatch, build_calls):
    monkeypatch.setattr(engine_module, "resolve_selector", lambda selector, **_: _wiring("reads_lexical"))
    engine = Databasise(store_root=store_root, workspace=_WORKSPACE, registry=_registry())

    with pytest.raises(UnparseableWiringError) as exc_info:
        await engine.query(QueryObject(text="what is indexed?"))

    assert exc_info.value.violations == ["unwired-store-effect"]
    assert build_calls == []


async def test_ingest_is_refused_before_any_store_is_built(store_root, monkeypatch, build_calls):
    monkeypatch.setattr(
        engine_module,
        "_corpus_wiring",
        lambda query_wiring, operation: _wiring("writes_lexical", consumes_documents=["lex"]),
    )
    engine = Databasise(store_root=store_root, workspace=_WORKSPACE, registry=_registry())

    with pytest.raises(UnparseableWiringError) as exc_info:
        await engine.ingest(IngestDocument(document_id="doc-1", text="some text"))

    assert exc_info.value.violations == ["unwired-store-effect"]
    assert build_calls == []


async def test_delete_document_is_refused_before_any_store_is_built(store_root, monkeypatch, build_calls):
    monkeypatch.setattr(
        engine_module, "_corpus_wiring", lambda query_wiring, operation: _wiring("writes_lexical")
    )
    engine = Databasise(store_root=store_root, workspace=_WORKSPACE, registry=_registry())

    with pytest.raises(UnparseableWiringError) as exc_info:
        await engine.delete_document("doc-1")

    assert exc_info.value.violations == ["unwired-store-effect"]
    assert build_calls == []


def test_rest_query_answers_422_with_codes_only(store_root, monkeypatch):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from databasise.seam.rest import create_app

    monkeypatch.setattr(engine_module, "resolve_selector", lambda selector, **_: _wiring("reads_lexical"))
    client = TestClient(create_app(store_root=store_root, workspace=_WORKSPACE, registry=_registry()))

    response = client.post("/query", json={"query": {"text": "what is indexed?"}})

    assert response.status_code == 422
    body = response.json()
    assert body["refusal_type"] == "UnparseableWiringError"
    assert body["violations"] == ["unwired-store-effect"]
    assert "lex" not in response.text


def test_unparseable_wiring_maps_to_422():
    pytest.importorskip("fastapi")
    from databasise.seam.rest import _status_for

    assert _status_for(UnparseableWiringError(violations=["x"])) == 422
