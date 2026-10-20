"""14-08-PLAN.md Task 1 (LEDG-02, D-03): a trace from a partial run is never promotion evidence.

``promote`` refuses every trace whose record has ``partial`` true, naming only the offending trace
ids, and writes nothing (no row, no ``ledger.db``). The rule is keyed on ``partial``, never
``degraded``: a completed run and a degraded-but-complete record still promote. The file imports only
names that exist at the phase base and copies its own stubs, so it collects and fails by assertion
there.
"""

from __future__ import annotations

import pytest

from databasise.clients.base import ChatResult, EmbeddingResult
from databasise.runner.trace import TokenAccounting
from databasise.seam.engine import Databasise
from databasise.seam.query import QueryObject
from databasise.seam.selectors import Selector
from databasise.seam.trace_store import TraceStore
from databasise.wirings.resolve import all_wirings

pytest.importorskip("fastapi")
from databasise.seam.rest import create_app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

_BYPASS = Selector(capability=["calls_llm"])


class _StubEmbeddingClient:
    def __init__(self, vector):
        self.vector = vector

    async def embed(self, texts, **kwargs):
        return EmbeddingResult(
            vectors=[self.vector for _ in texts],
            tokens=TokenAccounting(prompt_tokens=len(texts), call_count=1, counted_by="stub-embed"),
            resolved_model_identity="stub-embed-model",
        )


class _StubLLMClient:
    async def chat(self, messages, **kwargs):
        return ChatResult(
            text="a stub completion",
            tokens=TokenAccounting(prompt_tokens=5, completion_tokens=4, call_count=1, counted_by="stub-llm"),
            resolved_model_identity="stub-llm-model",
        )


async def _capture(awaitable):
    try:
        return await awaitable
    except Exception as caught:  # noqa: BLE001 - the assertion is on the captured type
        return caught


def _node_ids(arm_name: str) -> list[str]:
    resolved = next(resolved for name, resolved in all_wirings() if name == arm_name)
    return sorted(resolved.get("nodes", {}).keys())


def _persist(store_root, arm_name: str, **extra) -> str:
    record = {
        "run_id": f"fake-run-{arm_name}",
        "wiring_id": f"lightrag-{arm_name}",
        "wiring_instance_hash": f"sha256:{'0' * 63}{len(_node_ids(arm_name)) % 10}",
        "arm_id": "seam",
        "nodes": [{"node_id": node_id} for node_id in _node_ids(arm_name)],
    }
    record.update(extra)
    return TraceStore(store_root).persist(record)


def _no_ledger(store_root) -> bool:
    return not any((store_root / name).exists() for name in ("ledger.db", "ledger.db-wal", "ledger.db-shm"))


async def test_a_failed_bypass_run_is_refused_twice_with_no_row(synthetic_naive_store):
    root, workspace = synthetic_naive_store["store_root"], synthetic_naive_store["workspace"]
    engine = Databasise(store_root=root, workspace=workspace, clients=None)
    envelope = await engine.query(QueryObject(text="q"), _BYPASS)
    assert envelope.partial is True and envelope.trace_token

    for attempt in range(2):
        caught = await _capture(engine.promote("alias-x", [envelope.trace_token], "human_edit"))
        assert type(caught).__name__ == "PartialRunEvidenceError", (
            f"attempt {attempt}: promote on a failed run's trace gave {type(caught).__name__}: {caught}"
        )
        assert caught.trace_ids == [envelope.trace_token]
    assert _no_ledger(root), "a refused promote created ledger.db"

    client = TestClient(create_app(store_root=root, workspace=workspace, clients=None), raise_server_exceptions=False)
    response = client.post(
        "/promote", json={"alias": "alias-x", "trace_ids": [envelope.trace_token], "change_origin": "human_edit"}
    )
    assert response.status_code == 422, response.text
    assert response.json()["refusal_type"] == "PartialRunEvidenceError", response.text
    assert _no_ledger(root), "a refused REST promote created ledger.db"


async def test_an_old_format_partial_record_is_refused(tmp_path):
    token = _persist(tmp_path, "bypass", partial=True)
    engine = Databasise(store_root=tmp_path, workspace="partial-test")

    caught = await _capture(engine.promote("alias-old", [token], "human_edit"))

    assert type(caught).__name__ == "PartialRunEvidenceError", (
        f"an old-format partial record gave {type(caught).__name__}: {caught}"
    )
    assert caught.trace_ids == [token]
    assert _no_ledger(tmp_path), "a refused promote created ledger.db"


async def test_only_the_partial_trace_is_named(tmp_path):
    partial = _persist(tmp_path, "bypass", partial=True)
    complete = _persist(tmp_path, "bypass")
    engine = Databasise(store_root=tmp_path, workspace="partial-test")

    caught = await _capture(engine.promote("alias-mixed", [complete, partial], "human_edit"))

    assert type(caught).__name__ == "PartialRunEvidenceError", f"{type(caught).__name__}: {caught}"
    assert caught.trace_ids == [partial]
    assert complete not in str(caught)
    assert _no_ledger(tmp_path), "a refused promote created ledger.db"


async def test_a_completed_bypass_run_still_promotes(synthetic_naive_store):
    root, workspace = synthetic_naive_store["store_root"], synthetic_naive_store["workspace"]
    clients = {"embedding": _StubEmbeddingClient(synthetic_naive_store["query_vector"]), "llm": _StubLLMClient()}
    engine = Databasise(store_root=root, workspace=workspace, clients=clients)
    envelope = await engine.query(QueryObject(text="q"), _BYPASS)
    assert envelope.partial is False

    result = await _capture(engine.promote("alias-ok", [envelope.trace_token], "human_edit"))

    assert getattr(result, "version", None) == "1.0.0", f"{type(result).__name__}: {result}"


async def test_a_degraded_run_that_is_not_partial_still_promotes(tmp_path):
    token = _persist(tmp_path, "bypass", partial=False, degraded=True)
    engine = Databasise(store_root=tmp_path, workspace="partial-test")

    result = await _capture(engine.promote("alias-degraded", [token], "human_edit"))

    assert getattr(result, "version", None) == "1.0.0", f"{type(result).__name__}: {result}"
