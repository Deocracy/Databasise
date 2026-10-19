"""12-10 (HIPP-13, D-19): the ``hipporag/qa-reader`` node — upstream HippoRAG 2 ``rag_qa`` ported as
the 14th node: its prompt shape, the no-context ``fail_response`` answer (no LLM call), and the
"Answer:" parse."""

from __future__ import annotations

from databasise.clients.base import ChatResult
from databasise.parts.schema import NodeContext
from databasise.parts_core.hipporag.qa import HIPPORAG_QA_READER_PART
from databasise.parts_core.lightrag.prompts import PROMPTS
from databasise.runner.trace import TokenAccounting


class _RecordingLLM:
    def __init__(self, text: str) -> None:
        self.text = text
        self.calls: list[list[dict]] = []

    async def chat(self, messages, **kwargs) -> ChatResult:
        self.calls.append(list(messages))
        return ChatResult(
            text=self.text,
            tokens=TokenAccounting(prompt_tokens=3, completion_tokens=2, call_count=1, counted_by="stub-llm"),
            resolved_model_identity="stub-llm-model",
        )


def _ctx(contents: list[str], llm: _RecordingLLM, query: str = "Who directed it?") -> NodeContext:
    items = [{"id": f"c{i}", "score": 1.0, "content": content} for i, content in enumerate(contents)]
    return NodeContext(
        node_id="qa",
        config={"query": query},
        inputs={"assemble-result": {"items": items}},
        stores={},
        clients={"llm": llm},
    )


async def test_no_passage_content_answers_fail_response_without_an_llm_call():
    llm = _RecordingLLM("should never be used")

    out = await HIPPORAG_QA_READER_PART.body(_ctx(["", ""], llm))
    empty_items = await HIPPORAG_QA_READER_PART.body(_ctx([], llm))

    assert out["completion"] is PROMPTS["fail_response"]
    assert empty_items["completion"] is PROMPTS["fail_response"]
    assert llm.calls == []


async def test_the_messages_are_system_one_shot_pair_then_the_passages_and_question():
    llm = _RecordingLLM("Thought: x. Answer: forty-two.")

    out = await HIPPORAG_QA_READER_PART.body(_ctx(["first passage", "second passage"], llm, query="Why?"))

    assert len(llm.calls) == 1
    messages = llm.calls[0]
    assert [m["role"] for m in messages] == ["system", "user", "assistant", "user"]
    assert messages[3]["content"] == (
        "Wikipedia Title: first passage\n\nWikipedia Title: second passage\n\nQuestion: Why?\nThought: "
    )
    assert out["completion"] == "forty-two."
    for message in messages:
        assert "---Candidate Facts---" not in message["content"]
        assert "---Recognised Entities---" not in message["content"]


async def test_a_response_without_the_answer_marker_is_returned_whole():
    llm = _RecordingLLM("just some text, no marker")

    out = await HIPPORAG_QA_READER_PART.body(_ctx(["a passage"], llm))

    assert out["completion"] == "just some text, no marker"


def test_the_part_declares_a_generator_with_calls_llm():
    part = HIPPORAG_QA_READER_PART
    assert (part.name_at_version, part.kind, part.structural_depth, list(part.effects)) == (
        "hipporag/qa-reader@0.1.0",
        "generator",
        "opaque",
        ["calls_llm"],
    )
