"""LRAG-11 (11-03-PLAN.md, D-13): the corpus ports meter v1's own token usage.

The driver captures usage with ``lightrag.utils.TokenTracker`` (one for the LLM, one for
embeddings) and the part builds its ``TokenAccounting`` from the LLM half only. A call count with
zero tokens means the provider sent no usage, which is ``unbudgetable``, never a real zero.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from databasise.clients.builder import build_clients
from databasise.parts.schema import NodeContext
from databasise.parts_core.declared_only import LIGHTRAG_FULL_DELETE_PART
from databasise.parts_core.lightrag import full_delete, full_ingest
from databasise.parts_core.lightrag.full_delete import full_delete_body
from databasise.parts_core.lightrag.full_ingest import full_ingest_body
from databasise.runner import scheduler as _scheduler
from databasise.seam.corpus import IngestDocument
from databasise.seam.engine import Databasise
from databasise.stores.kv import SqliteKVStore
from databasise.tests.fixtures.v1_stub_server import (  # noqa: F401 - fixture
    real_v1,
    requires_v1,
)

# The stub server's per-call chat usage (tests/fixtures/v1_stub_server.py StubModelServer._chat).
_STUB_PROMPT, _STUB_COMPLETION = 11, 7


def _ctx(config: dict[str, Any]) -> NodeContext:
    return NodeContext(node_id="full-ingest", config=config, inputs={}, stores={})


def _usage(call_count: int, prompt: int, completion: int) -> dict[str, Any]:
    llm = {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": prompt + completion,
        "call_count": call_count,
    }
    return {"llm": llm, "embedding": {"prompt_tokens": 5, "completion_tokens": 0, "total_tokens": 5, "call_count": 1}}


@pytest.mark.parametrize(
    ("usage", "expected"),
    [
        (None, ("unbudgetable", 0, 0, 0)),
        ("not-a-dict", ("unbudgetable", 0, 0, 0)),
        (_usage(0, 0, 0), ("none", 0, 0, 0)),
        (_usage(3, 0, 0), ("unbudgetable", 0, 0, 3)),
        (_usage(2, 22, 14), ("v1-subprocess", 22, 14, 2)),
    ],
)
async def test_the_ingest_part_builds_its_accounting_from_the_llm_usage_only(monkeypatch, usage, expected):
    monkeypatch.setattr(
        full_ingest, "run_corpus_op", lambda *a, **k: {"track_id": "t", "enqueued": 1, "usage": usage}
    )

    result = await full_ingest_body(_ctx({"documents": [{"id": "x", "text": "x"}], "track_id": "t"}))

    tokens = result["tokens"]
    assert (tokens.counted_by, tokens.prompt_tokens, tokens.completion_tokens, tokens.call_count) == expected
    assert result["usage"] == usage


@requires_v1
async def test_a_real_ingest_is_metered_unbudgetable_without_usage_and_none_without_a_call(real_v1):  # noqa: F811
    working_dir = str(real_v1.store_root / "ws" / "lightrag-v1")

    def config(doc_id: str, track_id: str) -> dict[str, Any]:
        text = f"UNIQ{doc_id} Corp runs a mill in UNIQ{doc_id} City."
        return {"documents": [{"id": doc_id, "text": text}], "track_id": track_id, "working_dir": working_dir}

    metered = await full_ingest_body(_ctx(config("meterone", "m1")))
    tokens = metered["tokens"]
    assert tokens.counted_by == "v1-subprocess"
    assert tokens.call_count > 0
    assert tokens.prompt_tokens == _STUB_PROMPT * tokens.call_count
    assert tokens.completion_tokens == _STUB_COMPLETION * tokens.call_count
    assert metered["usage"]["embedding"]["call_count"] > 0, "embedding usage is reported beside the LLM figure"

    real_v1.server.omit_usage = True
    unmetered = await full_ingest_body(_ctx(config("metertwo", "m2")))
    assert unmetered["tokens"].counted_by == "unbudgetable"
    assert unmetered["tokens"].call_count > 0

    duplicate = await full_ingest_body(_ctx(config("meterone", "m3")))
    assert duplicate["enqueued"] == 0
    assert duplicate["tokens"].counted_by == "none"
    assert duplicate["tokens"].call_count == 0


def _fake_v1_over_budget(_op: str, payload: dict[str, Any], *, working_dir: Any = None, **_: Any) -> dict[str, Any]:
    """v1 commits the document, then reports more LLM spend than the default 1,000,000 allowance."""
    working_dir = Path(working_dir)
    working_dir.mkdir(parents=True, exist_ok=True)
    doc_id = payload["documents"][0]["id"]
    status = {doc_id: {"status": "processed", "chunks_list": [f"{doc_id}-c"], "track_id": payload["track_id"]}}
    (working_dir / "kv_store_doc_status.json").write_text(json.dumps(status), encoding="utf-8")
    chunks = {f"{doc_id}-c": {"content": "big", "full_doc_id": doc_id}}
    (working_dir / "kv_store_text_chunks.json").write_text(json.dumps(chunks), encoding="utf-8")
    return {"track_id": payload["track_id"], "enqueued": 1, "usage": _usage(3, 1_200_000, 50_000)}


async def test_spend_over_the_allowance_still_syncs_and_commits_a_committed_v1_write(tmp_path, monkeypatch, caplog):
    """11 REVIEW A-WR-02: a budget stop after v1 committed (and billed) used to skip the sync and
    refuse the ingest as RunIncomplete. The spend is logged and the write syncs and commits."""
    monkeypatch.setattr(full_ingest, "run_corpus_op", _fake_v1_over_budget)
    monkeypatch.setattr(
        full_delete, "run_corpus_op", lambda *_a, **_k: {"status": "success", "message": "", "usage": _usage(2, 1_100_000, 0)}
    )
    engine = Databasise(store_root=tmp_path, workspace="over")

    with caplog.at_level("WARNING", logger="databasise.seam.engine"):
        job = await engine.ingest(IngestDocument(document_id="big", text="big"))
        outcome = await engine.delete_document("big")

    assert job.enqueued == 1
    assert outcome.status == "success"
    overruns = [r.getMessage() for r in caplog.records if "over the default allowance" in r.getMessage()]
    assert overruns == [
        "corpus ingest: node full-ingest spent 1250000 tokens, 250000 over the default allowance of 1000000",
        "corpus delete: node full-delete spent 1100000 tokens, 100000 over the default allowance of 1000000",
    ]


async def test_the_synced_chunk_of_an_over_budget_ingest_is_in_the_v2_store(tmp_path, monkeypatch):
    monkeypatch.setattr(full_ingest, "run_corpus_op", _fake_v1_over_budget)
    await Databasise(store_root=tmp_path, workspace="over").ingest(IngestDocument(document_id="big", text="big"))

    kv = SqliteKVStore(namespace="text_chunks", workspace="over", store_root=tmp_path)
    try:
        assert (await kv.get_by_id("big-c"))["full_doc_id"] == "big"
    finally:
        await kv.finalize()


# --------------------------------------------------------------------------------------------- #
# Task 3: the delete half
# --------------------------------------------------------------------------------------------- #


def test_the_delete_wiring_and_part_declare_calls_llm():
    wiring = json.loads((Path(__file__).resolve().parents[3] / "wirings" / "lightrag" / "corpus-delete.json").read_text())
    assert "calls_llm" in wiring["nodes"]["full-delete"]["effects"]
    assert "calls_llm" in LIGHTRAG_FULL_DELETE_PART.effects


async def test_the_delete_part_builds_its_accounting_from_the_llm_usage(monkeypatch):
    result = {"status": "success", "doc_id": "d", "message": "", "status_code": 200, "file_path": None}
    monkeypatch.setattr(full_delete, "run_corpus_op", lambda *a, **k: {**result, "usage": _usage(2, 22, 14)})
    tokens = (await full_delete_body(NodeContext(node_id="full-delete", config={"doc_id": "d"}, inputs={}, stores={})))["tokens"]
    assert (tokens.counted_by, tokens.prompt_tokens, tokens.completion_tokens, tokens.call_count) == ("v1-subprocess", 22, 14, 2)


@requires_v1
async def test_the_scheduler_meters_a_real_delete_with_the_drivers_usage(real_v1, monkeypatch):  # noqa: F811
    engine = Databasise(store_root=real_v1.store_root, workspace="meter", clients=build_clients(real_v1.client_env))
    await engine.ingest(IngestDocument(document_id="deldoc", text="UNIQdel Corp sells lamps in UNIQdel City."))

    traces: list[Any] = []
    original = _scheduler.run_wiring

    async def spy(*args: Any, **kwargs: Any) -> dict[str, Any]:
        scheduled = await original(*args, **kwargs)
        traces.extend(scheduled["nodes"])
        return scheduled

    monkeypatch.setattr(_scheduler, "run_wiring", spy)
    outcome = await engine.delete_document("deldoc")

    assert outcome.status == "success"
    [delete_trace] = [trace for trace in traces if trace.node_id == "full-delete"]
    assert delete_trace.tokens.counted_by in ("v1-subprocess", "none")
