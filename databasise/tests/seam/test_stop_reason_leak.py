"""WIRE-03 (D-05): a consumer-visible ``stop_reason`` or ``degradation_reason`` is one of the closed
node-free codes. It carries no node id, no ``name@version`` and no exception class name; node detail
stays in the debug-only ``cross_process_failure_cause``. The construction legs (REST envelope and
non-debug trace) come first; the gate legs (13-10, D-05, D-23) follow: the test-time value-walk
flags a node id inside a reason, and the engine maps any non-code reason to ``node_failed`` at
response time without ever raising.
"""

from __future__ import annotations

import logging

import pytest

pytest.importorskip("fastapi")

from databasise.parts.registry import default_registry
from databasise.seam import Databasise, QueryObject
from databasise.seam import redact as redact_module
from databasise.seam.redact import assert_no_forbidden_values
from databasise.seam.rest import create_app
from fastapi.testclient import TestClient

_FORBIDDEN = (
    "node '",
    "embedder-query",
    "fact-score",
    "chunk-vector",
    "NodeExecutionError",
    "ClientNotWiredError",
    *default_registry().keys(),
)
_HIPPORAG_SELECTOR = {"capability": ["reads_graph", "reads_kv"]}


def _assert_node_free(reasons: dict[str, str | None]) -> None:
    for field, text in reasons.items():
        assert text, f"{field} is empty on a run that could not complete"
        for fragment in _FORBIDDEN:
            assert fragment not in text, f"{field}={text!r} carries {fragment!r}"


def _query(client: TestClient, body: dict) -> dict:
    response = client.post("/query", json=body)
    assert response.status_code == 200, response.text
    return response.json()


def _reasons(envelope: dict) -> dict[str, str | None]:
    return {"stop_reason": envelope["stop_reason"], "degradation_reason": envelope["degradation_reason"]}


def test_a_naive_query_without_clients_returns_node_free_reasons(synthetic_naive_store):
    store = synthetic_naive_store
    client = TestClient(create_app(store_root=store["store_root"], workspace=store["workspace"], clients=None))

    envelope = _query(client, {"query": {"text": "x"}})

    assert envelope["partial"] is True
    _assert_node_free(_reasons(envelope))


def test_the_non_debug_trace_reasons_are_node_free(synthetic_naive_store):
    store = synthetic_naive_store
    client = TestClient(create_app(store_root=store["store_root"], workspace=store["workspace"], clients=None))
    envelope = _query(client, {"query": {"text": "x"}})

    response = client.post("/trace/resolve", json={"trace_reference": envelope["trace_token"], "debug": False})

    assert response.status_code == 200, response.text
    _assert_node_free(_reasons(response.json()))


def test_a_hipporag_query_on_a_fresh_root_returns_node_free_reasons(store_root):
    client = TestClient(create_app(store_root=store_root, workspace="leak-fresh", clients=None))

    envelope = _query(client, {"query": {"text": "x"}, "selector": _HIPPORAG_SELECTOR})

    _assert_node_free(_reasons(envelope))


# --------------------------------------------------------------------------------------------- #
# the gate legs (13-10, WIRE-03, D-05, D-23)
# --------------------------------------------------------------------------------------------- #

_CLOSED_CODES = [
    "node_failed",
    "placement_refused",
    "budget_halt",
    "cancelled",
    "declared_fallback",
    "fallback_path_taken",
]
_LEAK = "node 'chunk-vector': NodeExecutionError: X"


def _capture(call):
    """The exception ``call()`` raised, or ``None``; the tests assert on it."""
    try:
        call()
    except Exception as exc:  # noqa: BLE001 - asserted on by the caller
        return exc
    return None


def _legacy_record(**reasons) -> dict:
    return {
        "run_id": "00000000-0000-4000-8000-000000000001",
        "wiring_id": "legacy-wiring",
        "wiring_instance_hash": "sha256:legacy",
        "arm_id": "seam",
        "nodes": [{"node_id": "chunk-vector", "instance_hash": "sha256:node"}],
        "partial": True,
        "degraded": True,
        **reasons,
    }


def test_the_value_walk_flags_a_node_id_inside_a_reason():
    caught = _capture(lambda: assert_no_forbidden_values({"stop_reason": _LEAK}, {"chunk-vector"}))
    bare = _capture(lambda: assert_no_forbidden_values({"degradation_reason": "chunk-vector"}, {"chunk-vector"}))

    assert isinstance(caught, AssertionError), caught
    assert isinstance(bare, AssertionError), bare


def test_an_answer_containing_a_node_word_is_not_flagged():
    caught = _capture(lambda: assert_no_forbidden_values({"answer": "generate the qa"}, {"generate", "qa"}))
    other = _capture(lambda: assert_no_forbidden_values({"note": "the qa pass"}, {"generate", "qa"}))

    assert caught is None, caught
    assert other is None, other  # equality only on every key but the two reason keys


async def test_a_leaky_scheduler_reason_is_served_as_node_failed(synthetic_naive_store, monkeypatch):
    from databasise.seam import engine as engine_module

    original = engine_module._scheduler.run_wiring

    async def leaky(*args, **kwargs):
        result = await original(*args, **kwargs)
        return {**result, "stop_reason": _LEAK, "degradation_reason": _LEAK}

    monkeypatch.setattr(engine_module._scheduler, "run_wiring", leaky)
    store = synthetic_naive_store
    engine = Databasise(store_root=store["store_root"], workspace=store["workspace"], clients=None)

    try:
        envelope, caught = await engine.query(QueryObject(text="x")), None
    except Exception as exc:  # noqa: BLE001 - asserted on below
        envelope, caught = None, exc

    assert caught is None, repr(caught)
    assert (envelope.stop_reason, envelope.degradation_reason) == ("node_failed", "node_failed")


async def test_a_legacy_stored_reason_resolves_as_node_failed(store_root):
    engine = Databasise(store_root=store_root, workspace="legacy", clients=None)
    token = engine._trace_store.persist(_legacy_record(stop_reason=_LEAK, degradation_reason=_LEAK))

    public = await engine.resolve_trace(token, debug=False)
    full = await engine.resolve_trace(token, debug=True)

    assert (public["stop_reason"], public["degradation_reason"]) == ("node_failed", "node_failed")
    assert (full["stop_reason"], full["degradation_reason"]) == (_LEAK, _LEAK)


def _node_free_reason():
    func = getattr(redact_module, "node_free_reason", None)
    assert func is not None, "seam.redact has no node_free_reason"
    return func


@pytest.mark.parametrize("code", _CLOSED_CODES)
def test_closed_codes_pass_unchanged(code):
    assert _node_free_reason()(code, {"chunk-vector"}) == code


def test_an_appended_code_is_mapped():
    assert _node_free_reason()("node_failed: x", {"chunk-vector"}) == "node_failed"


def test_clean_run_reasons_stay_none():
    assert _node_free_reason()(None, {"chunk-vector"}) is None


def test_a_non_string_reason_is_mapped_and_never_raises():
    func = _node_free_reason()

    assert func(7, {"chunk-vector"}) == "node_failed"
    assert func({"x": 1}, set()) == "node_failed"


def test_the_quoted_and_bare_forms_of_a_node_id_are_both_logged_as_forbidden(caplog):
    func = _node_free_reason()
    with caplog.at_level(logging.ERROR):
        func("node 'chunk-vector': boom", {"chunk-vector"})
        func("failed in chunk-vector", {"chunk-vector"})

    errors = [record for record in caplog.records if record.levelno >= logging.ERROR]
    assert len(errors) == 2, [record.getMessage() for record in caplog.records]
    for record in errors:
        assert "chunk-vector" not in record.getMessage()
