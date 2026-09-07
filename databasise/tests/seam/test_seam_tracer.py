"""04-01-PLAN.md Task 1: the end-to-end "a caller queries the engine and receives a closed
envelope" tracer. Mirrors
``databasise/tests/parity/test_naive_arm_end_to_end.py``'s synthetic-store/stub-client pattern
exactly (no network, no imported parity index, runs on any machine) but drives
``databasise.seam.Databasise.query()`` rather than ``run_arm()`` directly.
"""

from __future__ import annotations

import pydantic
import pytest

from databasise.clients.base import ChatResult, EmbeddingResult
from databasise.runner.trace import NodeTrace, TokenAccounting
from databasise.seam import Databasise, QueryObject, ResponseEnvelope
from databasise.seam.engine import _select_answer

_STUB_COMPLETION = "This is a stub completion for the seam's end-to-end tracer test."


class _StubEmbeddingClient:
    def __init__(self, vector: list[float]):
        self.vector = vector
        self.call_count = 0

    async def embed(self, texts, **kwargs):
        self.call_count += 1
        return EmbeddingResult(
            vectors=[self.vector for _ in texts],
            tokens=TokenAccounting(prompt_tokens=len(texts), call_count=1, counted_by="stub-embed"),
            resolved_model_identity="stub-embed-model",
        )


class _StubLLMClient:
    async def chat(self, messages, **kwargs):
        return ChatResult(
            text=_STUB_COMPLETION,
            tokens=TokenAccounting(prompt_tokens=5, completion_tokens=4, call_count=1, counted_by="stub-llm"),
            resolved_model_identity="stub-llm-model",
        )


async def test_a_caller_queries_the_engine_and_receives_a_closed_envelope(synthetic_naive_store):
    engine = Databasise(
        store_root=synthetic_naive_store["store_root"],
        workspace=synthetic_naive_store["workspace"],
        clients={
            "embedding": _StubEmbeddingClient(vector=synthetic_naive_store["query_vector"]),
            "llm": _StubLLMClient(),
        },
    )

    envelope = await engine.query(QueryObject(text="Which films did Ed Wood direct?"))

    assert isinstance(envelope, ResponseEnvelope)
    # Real value, never shape alone: the stub client's own configured completion text.
    assert envelope.answer == _STUB_COMPLETION
    # The naive arm's provides node ("generate") has structural_depth "stage" and every one of
    # its transitive deps in the naive arm is also "stage" — the effective depth the run actually
    # computed, not an assumed constant.
    assert envelope.depth_label == "stage"
    assert envelope.partial is False
    assert envelope.degraded is False
    assert envelope.stop_reason is None
    assert envelope.degradation_reason is None


def test_response_envelope_rejects_an_unexpected_keyword():
    with pytest.raises(pydantic.ValidationError):
        ResponseEnvelope(
            answer="x",
            depth_label="stage",
            partial=False,
            degraded=False,
            wiring_id="should-not-be-accepted",
        )


# --------------------------------------------------------------------------------------------- #
# WR-01: _select_answer iterates `provides` (the wiring's own declared order), never scheduler
# dispatch order, and refuses when more than one provides position produces a completion.
# --------------------------------------------------------------------------------------------- #


def _node_trace(node_id: str, *, effective_depth: str) -> NodeTrace:
    return NodeTrace(
        node_id=node_id,
        instance_hash=f"sha256:fake-{node_id}",
        depth="stage",
        effective_depth=effective_depth,
        wall_clock_ms=0,
        cache_hit=False,
        guards_fired=[],
        budget_state="completed",
        realised_budget_share=0.0,
        cross_process_failure_cause=None,
        resumable=True,
        tokens=TokenAccounting(),
    )


def test_select_answer_uses_the_answering_provides_nodes_own_effective_depth():
    provides = ["silent-node", "answering-node"]
    provided = {"answering-node": {"completion": "the real answer"}}
    node_by_id = {
        "silent-node": _node_trace("silent-node", effective_depth="deep"),
        "answering-node": _node_trace("answering-node", effective_depth="stage"),
    }

    answer, depth_label = _select_answer(provides, provided, node_by_id)

    assert answer == "the real answer"
    assert depth_label == "stage"


def test_select_answer_refuses_when_more_than_one_provides_node_produces_a_completion():
    """WR-01's own reproduction: two provides positions each producing a completion used to
    silently last-write-win on whichever happened to appear last in scheduler dispatch order —
    now refused explicitly instead."""
    provides = ["node-a", "node-b"]
    provided = {
        "node-a": {"completion": "answer from a"},
        "node-b": {"completion": "answer from b"},
    }
    node_by_id = {
        "node-a": _node_trace("node-a", effective_depth="stage"),
        "node-b": _node_trace("node-b", effective_depth="stage"),
    }

    with pytest.raises(RuntimeError):
        _select_answer(provides, provided, node_by_id)
