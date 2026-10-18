"""LRAG-17 proofs (D-16, "match v1"): the KG arms answer from v1 ``kg_query``'s context and prompt.

v1 references: ``operate.py`` kg_query (system prompt ``rag_response`` filled with the context,
the query as the user message), ``_apply_token_truncation`` (entity and relation rows),
``_build_context_str`` (``kg_query_context`` and the chunk budget), ``utils.py``
``generate_reference_list_from_chunks`` (reference ids by frequency then first appearance).

The arm tests drive one real-driver ingest through the hermetic loopback harness and skip only
when ``v1/.venv/bin/python`` is absent; the part tests run everywhere.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from databasise.clients.base import ChatResult
from databasise.clients.builder import build_clients
from databasise.parity.run_comparison import _inject_pinned_keywords
from databasise.parts.schema import NodeContext
from databasise.parts_core.lightrag.assemble import (
    LIGHTRAG_ASSEMBLER_KG_CONTEXT_PART,
    UnknownOrderPolicyError,
)
from databasise.parts_core.lightrag.generate import (
    LIGHTRAG_GENERATOR_LLM_PART,
    UnknownPromptTemplateError,
)
from databasise.parts_core.lightrag.prompts import PROMPTS
from databasise.parts_core.lightrag.truncator_token_budget import (
    LIGHTRAG_TRUNCATOR_TOKEN_BUDGET_PART,
)
from databasise.runner.trace import TokenAccounting
from databasise.seam.corpus import IngestDocument
from databasise.seam.engine import Databasise
from databasise.seam.query import QueryObject
from databasise.tests.fixtures.v1_stub_server import (  # noqa: F401 - fixture
    real_v1,
    requires_v1,
)
from databasise.wirings.resolve import resolve_arm

_TEXT = "UNIQalpha Corp builds bridges in UNIQalpha City."
_QUERY = "What does UNIQalpha Corp build in UNIQalpha City?"
_ENTITY_DESCRIPTION = "UNIQalpha Corp is an organization."
_RELATION_DESCRIPTION = "UNIQalpha Corp is in UNIQalpha City."
_KG_HEADERS = (
    "Knowledge Graph Data (Entity):",
    "Knowledge Graph Data (Relationship):",
    "Document Chunks (Each entry has a reference_id",
    "Reference Document List (Each entry starts with",
)


def _ctx(
    node_id: str,
    config: dict[str, Any] | None = None,
    inputs: dict[str, Any] | None = None,
    clients: dict[str, Any] | None = None,
) -> NodeContext:
    return NodeContext(node_id=node_id, config=config, inputs=inputs or {}, stores={}, clients=clients or {})


def _opening(template: str) -> str:
    """The template's fixed text before its first placeholder."""
    return template.split("{", 1)[0]


class _RecordingLLM:
    """Records every message list; forwards to ``inner`` when given, else answers ``"answer"``."""

    def __init__(self, inner: Any = None) -> None:
        self.inner = inner
        self.calls: list[list[dict[str, str]]] = []

    async def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> ChatResult:
        self.calls.append(list(messages))
        if self.inner is not None:
            return await self.inner.chat(messages, **kwargs)
        return ChatResult(
            text="answer",
            tokens=TokenAccounting(prompt_tokens=3, completion_tokens=2, call_count=1, counted_by="rec"),
            resolved_model_identity="rec-model",
        )


# --------------------------------------------------------------------------------------------- #
# The arms over one real-driver ingest
# --------------------------------------------------------------------------------------------- #


async def _ingested_engine(real_v1: Any, workspace: str) -> tuple[Databasise, _RecordingLLM]:  # noqa: F811
    clients = build_clients(real_v1.client_env)
    recorder = _RecordingLLM(clients["llm"])
    clients["llm"] = recorder
    engine = Databasise(store_root=real_v1.store_root, workspace=workspace, clients=clients)
    job = await engine.ingest(IngestDocument(document_id="kgdoc1", text=_TEXT))
    assert job.enqueued == 1
    return engine, recorder


@requires_v1
async def test_the_hybrid_arm_sends_v1s_rag_response_over_a_kg_context_as_the_system_message(real_v1):  # noqa: F811
    engine, recorder = await _ingested_engine(real_v1, "lrag17-hybrid")
    resolved = _inject_pinned_keywords(
        resolve_arm("hybrid"), hl_keywords=["bridge building"], ll_keywords=["UNIQalpha Corp", "UNIQalpha City"]
    )

    await engine._execute_resolved(QueryObject(text=_QUERY), resolved)

    assert len(recorder.calls) == 1  # keywords are pinned, so the one call is generate's
    (system, user) = recorder.calls[0]
    assert system["role"] == "system"
    assert user == {"role": "user", "content": _QUERY}
    text = system["content"]
    assert text.startswith(_opening(PROMPTS["rag_response"]))
    for header in _KG_HEADERS:
        assert header in text, header
    assert _ENTITY_DESCRIPTION in text
    assert _RELATION_DESCRIPTION in text
    assert "UNIQalpha Corp builds bridges" in text  # the chunk
    assert "Multiple Paragraphs" in text


@requires_v1
async def test_the_naive_arm_uses_naive_rag_response_and_bypass_sends_the_bare_query(real_v1):  # noqa: F811
    engine, recorder = await _ingested_engine(real_v1, "lrag17-naive")

    await engine._execute_resolved(QueryObject(text=_QUERY), resolve_arm("naive"))
    (system, user) = recorder.calls[-1]
    assert system["role"] == "system"
    assert system["content"].startswith(_opening(PROMPTS["naive_rag_response"]))
    assert "Document Chunks (Each entry has a reference_id" in system["content"]
    assert "Knowledge Graph Data" not in system["content"]
    assert user == {"role": "user", "content": _QUERY}

    await engine._execute_resolved(QueryObject(text=_QUERY), resolve_arm("bypass"))
    assert recorder.calls[-1] == [{"role": "user", "content": _QUERY}]


# --------------------------------------------------------------------------------------------- #
# assemble
# --------------------------------------------------------------------------------------------- #


_ENTITY_ROWS = [{"entity": "E1", "type": "Organization", "description": "E1 is a firm."}]
_RELATION_ROWS = [{"entity1": "E1", "entity2": "E2", "description": "E1 is near E2."}]
_CHUNKS = [
    {"id": "c1", "content": "chunk one", "file_path": "b.txt"},
    {"id": "c2", "content": "chunk two", "file_path": "a.txt"},
    {"id": "c3", "content": "chunk three", "file_path": "a.txt"},
]


def _kg_inputs(chunks: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "rerank": {"items": list(_CHUNKS if chunks is None else chunks)},
        "budget-entities": {"items": [], "entities_context": _ENTITY_ROWS},
        "budget-relations": {"items": [], "relations_context": _RELATION_ROWS},
    }


async def test_kg_template_fills_kg_query_context_with_v1s_rows_and_reference_list():
    ctx = _ctx("assemble", config={"order_policy": "kg-template"}, inputs=_kg_inputs())
    result = await LIGHTRAG_ASSEMBLER_KG_CONTEXT_PART.body(ctx)

    # a.txt appears twice, so it is reference 1 (frequency first, then first appearance).
    chunk_rows = [
        {"reference_id": "2", "content": "chunk one"},
        {"reference_id": "1", "content": "chunk two"},
        {"reference_id": "1", "content": "chunk three"},
    ]
    expected = PROMPTS["kg_query_context"].format(
        entities_str=json.dumps(_ENTITY_ROWS[0], ensure_ascii=False),
        relations_str=json.dumps(_RELATION_ROWS[0], ensure_ascii=False),
        text_chunks_str="\n".join(json.dumps(r, ensure_ascii=False) for r in chunk_rows),
        reference_list_str="[1] a.txt\n[2] b.txt",
    )
    assert result["context"] == expected
    assert result["order_policy"] == "kg-template"
    assert result["template_kind"] == "kg_query_context"
    assert result["chunk_count"] == 3


async def test_naive_template_fills_naive_query_context_with_chunks_and_references_only():
    inputs = {"rerank": {"items": list(_CHUNKS)}}
    ctx = _ctx("assemble", config={"order_policy": "naive-template"}, inputs=inputs)
    result = await LIGHTRAG_ASSEMBLER_KG_CONTEXT_PART.body(ctx)

    assert result["template_kind"] == "naive_query_context"
    assert result["context"].startswith(_opening(PROMPTS["naive_query_context"]))
    assert "Knowledge Graph Data" not in result["context"]
    assert "[1] a.txt\n[2] b.txt" in result["context"]


async def test_an_unknown_order_policy_is_refused_by_name():
    ctx = _ctx("assemble", config={"order_policy": "bogus"}, inputs=_kg_inputs())
    with pytest.raises(UnknownOrderPolicyError, match="bogus"):
        await LIGHTRAG_ASSEMBLER_KG_CONTEXT_PART.body(ctx)
    assert issubclass(UnknownOrderPolicyError, ValueError)


async def test_no_entities_relations_or_chunks_gives_an_empty_context_and_v1s_fail_response():
    inputs = {
        "rerank": {"items": []},
        "budget-entities": {"items": [], "entities_context": []},
        "budget-relations": {"items": [], "relations_context": []},
    }
    assembled = await LIGHTRAG_ASSEMBLER_KG_CONTEXT_PART.body(
        _ctx("assemble", config={"order_policy": "kg-template"}, inputs=inputs)
    )
    assert assembled["context"] == ""

    client = _RecordingLLM()
    result = await LIGHTRAG_GENERATOR_LLM_PART.body(
        _ctx("generate", config={"query": "q"}, inputs={"assemble": assembled}, clients={"llm": client})
    )
    assert result["completion"] == PROMPTS["fail_response"]
    assert result["tokens"] == TokenAccounting(counted_by="none")
    assert client.calls == []


# --------------------------------------------------------------------------------------------- #
# generate
# --------------------------------------------------------------------------------------------- #


async def test_generate_sends_the_filled_template_as_system_and_the_query_as_user():
    client = _RecordingLLM()
    result = await LIGHTRAG_GENERATOR_LLM_PART.body(
        _ctx(
            "generate",
            config={"query": "q?", "priority_class": "query"},
            inputs={"assemble": {"context": "CTX"}},
            clients={"llm": client},
        )
    )
    system = PROMPTS["rag_response"].format(
        response_type="Multiple Paragraphs", user_prompt="n/a", context_data="CTX"
    )
    assert client.calls == [[{"role": "system", "content": system}, {"role": "user", "content": "q?"}]]
    assert result["priority_class"] == "query"
    assert result["completion"] == "answer"


async def test_generate_naive_template_and_unknown_template():
    client = _RecordingLLM()
    await LIGHTRAG_GENERATOR_LLM_PART.body(
        _ctx(
            "generate",
            config={"query": "q", "prompt_template": "naive"},
            inputs={"assemble": {"context": "CTX"}},
            clients={"llm": client},
        )
    )
    assert client.calls[0][0]["content"] == PROMPTS["naive_rag_response"].format(
        response_type="Multiple Paragraphs", user_prompt="n/a", content_data="CTX"
    )

    with pytest.raises(UnknownPromptTemplateError, match="bogus"):
        await LIGHTRAG_GENERATOR_LLM_PART.body(
            _ctx("generate", config={"query": "q", "prompt_template": "bogus"}, clients={"llm": client})
        )


async def test_generate_bypass_template_sends_one_user_message_and_echoes_priority_class():
    client = _RecordingLLM()
    result = await LIGHTRAG_GENERATOR_LLM_PART.body(
        _ctx(
            "generate",
            config={"query": "direct", "prompt_template": "none - direct LLM call, no context", "priority_class": "summary"},
            clients={"llm": client},
        )
    )
    assert client.calls == [[{"role": "user", "content": "direct"}]]
    assert result["priority_class"] == "summary"


# --------------------------------------------------------------------------------------------- #
# budget-entities / budget-relations: v1's row projection and costing
# --------------------------------------------------------------------------------------------- #


def _cost(row: dict[str, Any]) -> int:
    return len(json.dumps(row, ensure_ascii=False)) // 4


async def test_budget_entities_costs_and_emits_v1s_entity_rows():
    items = [
        {"entity_name": f"E{i}", "entity_type": "Org", "description": "d" * 30, "source_id": "c1<SEP>c2",
         "derived_from": ["x"], "rank": i}
        for i in range(3)
    ]
    rows = [{"entity": f"E{i}", "type": "Org", "description": "d" * 30} for i in range(3)]
    allowance = _cost(rows[0]) * 2
    result = await LIGHTRAG_TRUNCATOR_TOKEN_BUDGET_PART.body(
        _ctx("budget-entities", config={"max_token_allowance": allowance}, inputs={"join-entities": {"items": items}})
    )
    assert result["entities_context"] == rows[:2]
    assert result["items"] == items[:2]
    assert result["consumed"] == _cost(rows[0]) + _cost(rows[1])


async def test_budget_relations_costs_and_emits_v1s_relation_rows():
    items = [
        {"src_id": "A", "tgt_id": "B", "description": "A knows B.", "weight": 1.0, "source_id": "c1"},
        {"src_tgt": ["C", "D"], "description": "C knows D.", "rank": 2},
    ]
    result = await LIGHTRAG_TRUNCATOR_TOKEN_BUDGET_PART.body(
        _ctx("budget-relations", inputs={"join-relations": {"items": items}})
    )
    assert result["relations_context"] == [
        {"entity1": "A", "entity2": "B", "description": "A knows B."},
        {"entity1": "C", "entity2": "D", "description": "C knows D."},
    ]
    assert result["allowance"] == 8000
    assert result["consumed"] == sum(_cost(r) for r in result["relations_context"])


# --------------------------------------------------------------------------------------------- #
# The context cap: chunk_top_k, v1's available-token formula, and the engine-set max_total_tokens
# --------------------------------------------------------------------------------------------- #


async def test_an_oversized_chunk_set_is_cut_so_the_system_prompt_fits_max_total_tokens():
    chunks = [{"id": f"c{i}", "content": chr(97 + i) * 2000, "file_path": f"{i}.txt"} for i in range(10)]
    ctx = _ctx("assemble", config={"order_policy": "kg-template", "max_total_tokens": 2000, "query": "q"},
               inputs=_kg_inputs(chunks))
    result = await LIGHTRAG_ASSEMBLER_KG_CONTEXT_PART.body(ctx)

    system = PROMPTS["rag_response"].format(
        response_type="Multiple Paragraphs", user_prompt="n/a", context_data=result["context"]
    )
    assert len(system) // 4 <= 2000
    assert 0 < result["chunk_count"] < 10
    assert "a" * 2000 in result["context"]  # whole chunks are dropped from the end


async def test_assemble_keeps_at_most_chunk_top_k_chunks():
    chunks = [{"id": f"c{i}", "content": f"chunk {i}"} for i in range(30)]
    default = await LIGHTRAG_ASSEMBLER_KG_CONTEXT_PART.body(
        _ctx("assemble", config={"order_policy": "naive-template"}, inputs={"rerank": {"items": chunks}})
    )
    capped = await LIGHTRAG_ASSEMBLER_KG_CONTEXT_PART.body(
        _ctx("assemble", config={"order_policy": "naive-template", "chunk_top_k": 5}, inputs={"rerank": {"items": chunks}})
    )
    assert default["chunk_count"] == 20
    assert capped["chunk_count"] == 5


class _StopAtParse(Exception):
    pass


async def _parsed_assemble_config(monkeypatch: pytest.MonkeyPatch, store_root: Any, resolved: dict[str, Any]) -> dict:
    from databasise.seam import engine as engine_module

    captured: dict[str, Any] = {}

    def _spy(run_resolved: dict[str, Any], registry: Any) -> None:
        captured["resolved"] = run_resolved
        raise _StopAtParse

    monkeypatch.setattr(engine_module, "parse_wiring", _spy)
    engine = Databasise(store_root=store_root, workspace="lrag17-cap", clients={})
    with pytest.raises(_StopAtParse):
        await engine._execute_resolved(QueryObject(text="q"), resolved)
    return captured["resolved"]["nodes"]["assemble"]["config"]


async def test_the_engine_sets_max_total_tokens_on_assemble_and_keeps_a_wiring_value(monkeypatch, store_root):
    config = await _parsed_assemble_config(monkeypatch, store_root, resolve_arm("hybrid"))
    assert config["max_total_tokens"] == 30000

    own = resolve_arm("hybrid")
    own["nodes"]["assemble"]["config"]["max_total_tokens"] = 1234
    config = await _parsed_assemble_config(monkeypatch, store_root, own)
    assert config["max_total_tokens"] == 1234
