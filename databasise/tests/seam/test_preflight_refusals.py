"""WIRE-05 (D-07): every refusal raised before dispatch reaches a consumer as a named refusal, never a
500. A cyclic wiring is refused by ``_refuse_unparseable`` (the cycle code joins the violation codes)
on the query, ingest, delete and retry paths; the runner's pre-flight errors are translated to named
seam refusals.

Recorded exception to the requirement text (D-07, D-25): the public violation entry carries its
``code`` only; each violation's pointer and message stay private and are logged server-side.

New names are read with ``getattr`` and exceptions are captured, so every test collects and fails by
assertion on code that predates the fix.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from databasise.parts.registry import PartRegistry
from databasise.parts.schema import NodeContext, Part, WiringNode
from databasise.runner import scheduler
from databasise.seam import Databasise
from databasise.seam.corpus import IngestDocument
from databasise.seam.rest import create_app
from databasise.validator.errors import ValidationReport
from databasise.validator.parse import ParsedWiring
from fastapi.testclient import TestClient

_PASSTHROUGH = "parts-core/passthrough@1.0.0"
_QUERY_BODY = {"query": {"text": "x"}}


def _node(*deps: str, component: str = _PASSTHROUGH, config: dict | None = None) -> dict:
    node = {"component": component, "kind": "passthrough", "deps": list(deps)}
    if config is not None:
        node["config"] = config
    return node


def _cyclic_wiring(wiring_id: str = "lightrag-cyclic", *, unknown_component: bool = False) -> dict:
    nodes = {"cyc-a": _node("cyc-b"), "cyc-b": _node("cyc-a")}
    if unknown_component:  # a dependency of the provides node, so the run-wiring prune keeps it
        nodes["ghost"] = _node(component="nowhere/missing@1.0.0")
        nodes["cyc-a"]["deps"].append("ghost")
    return {
        "wiring_id": wiring_id,
        "nodes": nodes,
        "provides": ["cyc-a"],
        "consumes_documents": ["cyc-a"],
        "consumes_query": [],
    }


def _client(store_root, workspace: str = "preflight") -> TestClient:
    app = create_app(store_root=store_root, workspace=workspace, clients=None)
    return TestClient(app, raise_server_exceptions=False)


def _trace_rows(client: TestClient) -> int:
    engine = client.app.state.engine
    return engine._trace_store._conn.execute("SELECT COUNT(*) FROM traces").fetchone()[0]


def _json(response) -> dict:
    try:
        return response.json()
    except ValueError:  # a 500 has a plain-text body; the status assertion then reports the fault
        return {}


def _inject_query_wiring(monkeypatch, wiring_factory) -> None:
    monkeypatch.setattr(
        "databasise.seam.engine.resolve_selector",
        lambda selector, registry, store_root: wiring_factory(),
    )


def test_a_cyclic_query_wiring_is_refused_by_name_over_rest(store_root, monkeypatch):
    _inject_query_wiring(monkeypatch, _cyclic_wiring)
    client = _client(store_root)
    rows_before = _trace_rows(client)

    response = client.post("/query", json=_QUERY_BODY)

    assert response.status_code == 422, response.text
    body = _json(response)
    assert body.get("refusal_type") == "UnparseableWiringError", body
    assert "cyclic-wiring" in body.get("violations", []), body
    assert _trace_rows(client) == rows_before


def test_a_cycle_and_an_unknown_component_are_one_refusal(store_root, monkeypatch):
    _inject_query_wiring(monkeypatch, lambda: _cyclic_wiring(unknown_component=True))
    client = _client(store_root)

    response = client.post("/query", json=_QUERY_BODY)

    assert response.status_code == 422, response.text
    body = _json(response)
    assert body.get("refusal_type") == "UnparseableWiringError", body
    assert sorted(body.get("violations", [])) == ["cyclic-wiring", "unknown-component"], body


def test_the_refusal_body_carries_codes_only(store_root, monkeypatch):
    _inject_query_wiring(monkeypatch, lambda: _cyclic_wiring(unknown_component=True))
    client = _client(store_root)

    response = client.post("/query", json=_QUERY_BODY)

    body = _json(response)
    assert body.get("refusal_type") == "UnparseableWiringError", body
    assert all(isinstance(entry, str) for entry in body.get("violations", [])), body
    text = response.text
    for private in ("cyc-a", "cyc-b", "ghost", "/nodes/", "nowhere/missing", "pointer"):
        assert private not in text, f"{private!r} leaked into {text}"


def test_a_refused_cyclic_request_repeats_the_same_refusal(store_root, monkeypatch):
    _inject_query_wiring(monkeypatch, _cyclic_wiring)
    client = _client(store_root)
    rows_before = _trace_rows(client)

    first = client.post("/query", json=_QUERY_BODY)
    second = client.post("/query", json=_QUERY_BODY)

    assert (first.status_code, _json(first).get("refusal_type")) == (422, "UnparseableWiringError")
    assert (second.status_code, _json(second).get("refusal_type")) == (422, "UnparseableWiringError")
    assert _trace_rows(client) == rows_before


async def _no_v1(*args, **kwargs):
    raise AssertionError("a refused cyclic wiring must not reach v1")


async def _operation_outcome(engine: Databasise, operation: str) -> Exception | None:
    try:
        if operation == "ingest":
            await engine.ingest(IngestDocument(document_id="cyc-doc", text="hello"))
        elif operation == "delete":
            await engine.delete_document("cyc-doc")
        else:
            await engine.retry_document("cyc-doc")
    except Exception as exc:  # noqa: BLE001 - the test asserts on the captured type
        return exc
    return None


@pytest.mark.parametrize("operation", ["ingest", "delete", "retry"])
async def test_ingest_delete_and_retry_refuse_a_cyclic_corpus_wiring(operation, store_root, monkeypatch):
    # hipporag family for ingest and delete (no v1 gate), lightrag for retry (the only family it supports)
    family = "lightrag" if operation == "retry" else "hipporag"
    monkeypatch.setattr(
        "databasise.seam.engine._corpus_wiring", lambda query_wiring, op: _cyclic_wiring(f"{family}-cyclic")
    )
    monkeypatch.setattr("databasise.seam.engine._corpus_op_or_refuse", _no_v1)
    engine = Databasise(store_root=store_root, workspace="preflight-corpus", clients=None)

    outcome = await _operation_outcome(engine, operation)

    assert type(outcome).__name__ == "UnparseableWiringError", repr(outcome)
    assert "cyclic-wiring" in getattr(outcome, "violations", []), repr(outcome)
    inbox = store_root / "preflight-corpus" / "corpus-inbox"
    assert not inbox.exists() or not list(inbox.iterdir())


# ---- runner pre-flight: settings are true ints (D-07) ----------------------------------------------

def _single_node_wiring(ran: list[str], config: dict | None) -> ParsedWiring:
    async def body(ctx: NodeContext):
        ran.append(ctx.node_id)
        return {}

    part = Part(
        name_at_version="test/only@1.0.0",
        kind="passthrough",
        structural_depth="stage",
        effects=[],
        upstream_ref=None,
        body=body,
    )
    node = WiringNode(component=part.name_at_version, kind="passthrough", config=config, deps=[])
    return ParsedWiring(
        nodes={"only": node},
        parts={"only": part},
        deps={"only": ()},
        node_order=("only",),
        report=ValidationReport(),
    )


async def _run_single(config: dict | None) -> tuple[dict | None, Exception | None, list[str]]:
    ran: list[str] = []
    try:
        result = await scheduler.run_wiring(
            _single_node_wiring(ran, config),
            PartRegistry(),
            {},
            determinism_setting="cache-bypassed",
            concurrency_setting="sequential",
        )
    except Exception as exc:  # noqa: BLE001 - the test asserts on the captured type
        return None, exc, ran
    return result, None, ran


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("max_concurrency", True, "InvalidMaxConcurrencyError"),
        ("max_concurrency", 2.7, "InvalidMaxConcurrencyError"),
        ("max_concurrency", "100", "InvalidMaxConcurrencyError"),
        ("token_allowance", 0.9, "InvalidTokenAllowanceError"),
        ("token_allowance", "100", "InvalidTokenAllowanceError"),
        ("token_allowance", False, "InvalidTokenAllowanceError"),
    ],
)
async def test_a_non_int_setting_is_refused_before_dispatch(field, value, error):
    _, exc, ran = await _run_single({field: value})

    assert type(exc).__name__ == error, repr(exc)
    assert ran == [], "a node ran although its setting was refused"


@pytest.mark.parametrize(
    ("config", "refused"),
    [
        ({"max_concurrency": 1}, None),
        ({"max_concurrency": 0}, "InvalidMaxConcurrencyError"),
        ({"token_allowance": 0}, None),
        ({"token_allowance": -1}, "InvalidTokenAllowanceError"),
        (None, None),
    ],
    ids=["concurrency-1", "concurrency-0", "allowance-0", "allowance-minus-1", "no-config"],
)
async def test_boundary_settings(config, refused):
    result, exc, ran = await _run_single(config)

    if refused is None:
        assert exc is None, repr(exc)
        assert ran == ["only"]
        assert result is not None and result["partial"] is False
    else:
        assert type(exc).__name__ == refused, repr(exc)
        assert ran == []
