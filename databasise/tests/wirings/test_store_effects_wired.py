"""10-12-PLAN.md (STOR-12, D-15, Q5): every store effect in the vocabulary either resolves to a
wired store or is refused at parse time.

``reads_lexical``, ``writes_lexical`` and ``reads_blob`` have no store after D-15, so a node
declaring one (on the node or its resolved part) gets the accumulated violation
``unwired-store-effect``. Through the seam, any non-ok parse report becomes the named refusal
``UnparseableWiringError`` (422) before a store is built, never a later 500.
"""

from __future__ import annotations

from typing import get_args

import numpy as np
import pytest

from databasise.parts.registry import default_registry
from databasise.parts.schema import Effect, Part
from databasise.parts_core import EFFECT_TO_STORE, StoreNotWiredError, UndeclaredEffectError
from databasise.runner import scheduler
from databasise.seam import Databasise, QueryObject
from databasise.seam import engine as engine_module
from databasise.seam.corpus import IngestDocument
from databasise.seam.refusals import UnparseableWiringError
from databasise.seam.selectors import Selector
from databasise.stores.kv import SqliteKVStore
from databasise.stores.vector import FaissVectorStore
from databasise.tests.seam.test_hipporag_write_path import (
    _HIPPORAG_CAPABILITY,
    _StubEmbeddingClient,
    _StubIngestQueryLLMClient,
)
from databasise.validator.errors import CODE_EFFECTS_EXCEED_PART, CODE_UNWIRED_STORE_EFFECT
from databasise.validator.parse import parse_wiring
from databasise.wirings.resolve import load_wiring, resolve_arm

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


# --------------------------------------------------------------------------------------------- #
# Task 2: writes_artifact stays a declaration-only marker; every shipped wiring parses and runs
# --------------------------------------------------------------------------------------------- #

_ARTIFACT_PARTS = (
    "lightrag/full-ingest@0.1.0",
    "lightrag/embedder-index@0.1.0",
    "hipporag/graph-materializer@0.1.0",
)


def test_writes_artifact_is_a_marker_and_the_vocabulary_keeps_17_members():
    assert EFFECT_TO_STORE["writes_artifact"] is None
    assert set(EFFECT_TO_STORE) == set(get_args(Effect))
    assert len(get_args(Effect)) == 17


@pytest.mark.parametrize("name", _ARTIFACT_PARTS)
def test_the_three_artifact_parts_still_declare_writes_artifact(name):
    assert "writes_artifact" in default_registry().get(name).effects


async def _touch_artifact_body(ctx):
    return {"artifact": ctx.stores["artifact"]}


async def test_a_writes_artifact_node_parses_and_its_store_access_is_undeclared_not_unwired():
    registry = default_registry()
    registry.register(
        Part(
            name_at_version="test-fixture/artifact-writer@1.0.0",
            kind="test-fixture",
            structural_depth="stage",
            effects=["writes_artifact"],
            upstream_ref=None,
            body=_touch_artifact_body,
        )
    )
    wiring = {
        "wiring_id": "artifact-fixture",
        "wiring_version": "1",
        "nodes": {
            "art": {
                "component": "test-fixture/artifact-writer@1.0.0",
                "kind": "test-fixture",
                "effects": ["writes_artifact"],
                "deps": [],
            }
        },
        "recipe": {},
        "provides": ["art"],
    }
    parsed = parse_wiring(engine_module._inject_token_allowance(wiring, 1000), registry)
    assert parsed.report.ok

    result = await scheduler.run_wiring(
        parsed,
        registry,
        {},
        determinism_setting=engine_module._DETERMINISM_SETTING,
        concurrency_setting=engine_module._CONCURRENCY_SETTING,
    )

    assert isinstance(result["node_exceptions"]["art"], UndeclaredEffectError)
    assert not any(isinstance(e, StoreNotWiredError) for e in result["node_exceptions"].values())


_SHIPPED_WIRINGS = [
    *[
        (f"lightrag/{arm}", lambda arm=arm: resolve_arm(arm))
        for arm in ("naive", "bypass", "hybrid", "local", "global")
    ],
    ("lightrag/corpus-ingest", lambda: load_wiring("lightrag", variant="corpus-ingest")),
    ("lightrag/corpus-delete", lambda: load_wiring("lightrag", variant="corpus-delete")),
    ("hipporag/base", lambda: load_wiring("hipporag")),
    ("hipporag/corpus-ingest", lambda: load_wiring("hipporag", variant="corpus-ingest")),
]


@pytest.mark.parametrize("name,load", _SHIPPED_WIRINGS, ids=[name for name, _ in _SHIPPED_WIRINGS])
def test_every_shipped_wiring_parses_ok_with_no_unwired_store_effect(name, load):
    parsed = parse_wiring(load(), default_registry())

    assert parsed.report.ok, [v.code for v in parsed.report.violations]
    assert CODE_UNWIRED_STORE_EFFECT not in {v.code for v in parsed.report.violations}


@pytest.fixture
def run_results(monkeypatch):
    results: list[dict] = []
    real = scheduler.run_wiring

    async def spy(*args, **kwargs):
        result = await real(*args, **kwargs)
        results.append(result)
        return result

    monkeypatch.setattr(scheduler, "run_wiring", spy)
    return results


def _store_errors(results: list[dict]) -> list[BaseException]:
    return [
        exc
        for result in results
        for exc in result["node_exceptions"].values()
        if isinstance(exc, StoreNotWiredError | UndeclaredEffectError)
    ]


def _engine(store_root) -> Databasise:
    return Databasise(
        store_root=store_root,
        workspace=_WORKSPACE,
        clients={"embedding": _StubEmbeddingClient(), "llm": _StubIngestQueryLLMClient()},
    )


async def test_the_naive_arm_runs_with_no_store_effect_error(store_root, monkeypatch, run_results):
    # The same synthetic store tests/seam/conftest.py's synthetic_naive_store builds.
    content = "Ed Wood directed several low-budget films."
    vector_store = FaissVectorStore(namespace="chunks", workspace=_WORKSPACE, store_root=store_root)
    await vector_store.upsert(
        ids=["chunk-1"], embeddings=np.array([[1.0, 0.0, 0.0]]), metadatas=[{"content": content}]
    )
    await vector_store.index_done_callback()
    kv_store = SqliteKVStore(namespace="text_chunks", workspace=_WORKSPACE, store_root=store_root)
    await kv_store.upsert({"chunk-1": {"content": content, "file_path": "ed_wood.txt"}})
    await kv_store.index_done_callback()
    await kv_store.finalize()
    monkeypatch.setattr(engine_module, "resolve_selector", lambda selector, **_: resolve_arm("naive"))

    envelope = await _engine(store_root).query(QueryObject(text="What did Ed Wood direct?"))

    assert envelope.evidence
    assert run_results
    assert _store_errors(run_results) == []


async def test_the_hipporag_corpus_ingest_runs_with_no_store_effect_error(store_root, run_results):
    job = await _engine(store_root).ingest(
        IngestDocument(document_id="stor12-doc", text="Ed Wood directed several low-budget films."),
        selector=Selector(capability=_HIPPORAG_CAPABILITY),
    )

    assert job.enqueued == 1
    assert run_results
    assert _store_errors(run_results) == []
