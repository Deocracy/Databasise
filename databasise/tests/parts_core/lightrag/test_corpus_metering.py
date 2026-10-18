"""LRAG-11 (11-03-PLAN.md, D-13): the corpus ports meter v1's own token usage.

The driver captures usage with ``lightrag.utils.TokenTracker`` (one for the LLM, one for
embeddings) and the part builds its ``TokenAccounting`` from the LLM half only. A call count with
zero tokens means the provider sent no usage, which is ``unbudgetable``, never a real zero.
"""

from __future__ import annotations

from typing import Any

import pytest

from databasise.parts.schema import NodeContext
from databasise.parts_core.lightrag import full_ingest
from databasise.parts_core.lightrag.full_ingest import full_ingest_body
from databasise.tests.fixtures.v1_stub_server import real_v1, requires_v1  # noqa: F401 - fixture

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
