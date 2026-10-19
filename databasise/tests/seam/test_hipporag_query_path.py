"""12-05 (HIPP-12 trace leg, HIPP-05): the HippoRAG query path through the public seam. A query run
dispatches only query-side nodes, and ``fact-filter`` receives the query text. 12-07 adds the HIPP-12
row test (one embed per query). 12-10 adds the HIPP-13 row test (the answer is generated text); 12-11 adds its row test here."""

from __future__ import annotations

import json
import re

from databasise.clients.base import ChatResult
from databasise.runner.trace import TokenAccounting
from databasise.seam import Databasise, QueryObject
from databasise.seam.corpus import IngestDocument
from databasise.seam.selectors import Selector, resolve_selector
from seam.test_hipporag_write_path import (
    _DOCUMENT_TEXT,
    _HIPPORAG_CAPABILITY,
    _OBJECT,
    _PREDICATE,
    _QUERY_VECTOR,
    _SUBJECT,
    _StubEmbeddingClient,
    _StubIngestQueryLLMClient,
)

_INDEX_SIDE_NODES = {
    "chunk-embed",
    "openie",
    "entity-fact-embed",
    "fact-edges",
    "passage-edges",
    "synonymy-edges",
    "graph-augment-persist",
}
_QUERY_SIDE_NODES = {
    "fact-score",
    "fact-filter",
    "reset-vector-join",
    "ppr",
    "dpr-fallback",
    "assemble-result",
    "qa",
}
_QUERY_OPEN = "---Query---\n"
_QUERY_CLOSE = "\n\n---Candidate Facts---"


class _CapturingFactFilterLLMClient(_StubIngestQueryLLMClient):
    """Records every fact-filter prompt; answers like the write-path stub (keep_ids [])."""

    def __init__(self):
        self.fact_filter_prompts: list[str] = []

    async def chat(self, messages, **kwargs):
        content = messages[0]["content"]
        if "---Candidate Facts---" in content:
            self.fact_filter_prompts.append(content)
        return await super().chat(messages, **kwargs)


async def _ingested_engine(store_root, llm) -> tuple[Databasise, Selector]:
    engine = Databasise(
        store_root=store_root,
        workspace="hipporag-query-path-ws",
        clients={"embedding": _StubEmbeddingClient(), "llm": llm},
    )
    selector = Selector(capability=_HIPPORAG_CAPABILITY)
    await engine.ingest(IngestDocument(document_id="query-path-doc", text=_DOCUMENT_TEXT), selector=selector)
    return engine, selector


async def test_a_hipporag_query_trace_names_only_query_side_nodes(store_root):
    engine, selector = await _ingested_engine(store_root, _StubIngestQueryLLMClient())

    envelope = await engine.query(QueryObject(text="What did Ed Wood direct?"), selector)
    trace = await engine.resolve_trace(envelope.trace_token, debug=True)

    node_ids = {node["node_id"] for node in trace["nodes"]}
    assert node_ids & _INDEX_SIDE_NODES == set(), node_ids
    assert node_ids <= _QUERY_SIDE_NODES, node_ids


def _query_section(prompt: str) -> str:
    start = prompt.find(_QUERY_OPEN)
    end = prompt.find(_QUERY_CLOSE)
    if start < 0 or end < 0:
        return f"<markers missing: start={start} end={end}>"
    return prompt[start + len(_QUERY_OPEN) : end]


async def test_fact_filter_prompt_carries_the_query_between_the_markers(store_root):
    llm = _CapturingFactFilterLLMClient()
    engine, selector = await _ingested_engine(store_root, llm)

    captured: dict[str, str] = {}
    for query in ("What did Ed Wood direct?", "Qui a réalisé ce film ?"):
        llm.fact_filter_prompts.clear()
        await engine.query(QueryObject(text=query), selector)
        prompts = list(llm.fact_filter_prompts)
        captured[query] = _query_section(prompts[0]) if prompts else "<no fact-filter prompt>"

    assert captured == {
        "What did Ed Wood direct?": "What did Ed Wood direct?",
        "Qui a réalisé ce film ?": "Qui a réalisé ce film ?",
    }


class _CountingEmbeddingClient(_StubEmbeddingClient):
    """Records the texts of every embed call, returning the write-path query vector."""

    def __init__(self):
        super().__init__()
        self.calls: list[list[str]] = []

    async def embed(self, texts, **kwargs):
        self.calls.append(list(texts))
        return await super().embed(texts, **kwargs)


async def test_a_query_runs_only_query_side_nodes_and_embeds_once(store_root):
    """HIPP-12: one query embeds its text once (fact-score; reset-vector-join and dpr-fallback reuse
    the vector), dispatches no index-side node, and no write selector resolves to HippoRAG."""
    embedding = _CountingEmbeddingClient()
    engine = Databasise(
        store_root=store_root,
        workspace="hipporag-query-path-ws",
        clients={"embedding": embedding, "llm": _StubIngestQueryLLMClient()},
    )
    selector = Selector(capability=_HIPPORAG_CAPABILITY)
    await engine.ingest(IngestDocument(document_id="query-path-doc", text=_DOCUMENT_TEXT), selector=selector)
    embedding.calls.clear()

    envelope = await engine.query(QueryObject(text="What did Ed Wood direct?"), selector)
    trace = await engine.resolve_trace(envelope.trace_token, debug=True)
    node_ids = {node["node_id"] for node in trace["nodes"]}

    write_outcome: object
    try:
        resolved = resolve_selector(
            Selector(capability=["writes_graph"]), registry=engine.registry, store_root=store_root
        )
        write_outcome = str(resolved.get("wiring_id", ""))
    except Exception as exc:  # noqa: BLE001 — the refusal is the expected outcome
        write_outcome = type(exc).__name__

    assert {
        "index_nodes_dispatched": sorted(node_ids & _INDEX_SIDE_NODES),
        "write_selector_resolves_to_hipporag": str(write_outcome).startswith("hipporag"),
        "embed_calls": embedding.calls,
    } == {
        "index_nodes_dispatched": [],
        "write_selector_resolves_to_hipporag": False,
        "embed_calls": [["What did Ed Wood direct?"]],
    }
    assert node_ids == _QUERY_SIDE_NODES, node_ids


_QA_REPLY = "Thought: The passage names the films. Answer: low-budget films"


class _StubQaAwareLLMClient:
    """Answers a call whose first message is a system message (the qa node) with a fixed reply;
    every other call like the write-path stub (the guard fires, keep_ids [])."""

    def __init__(self):
        self.qa_calls: list[list[dict]] = []

    async def chat(self, messages, **kwargs):
        content = messages[0]["content"]
        if messages[0]["role"] == "system":
            self.qa_calls.append(list(messages))
            text = _QA_REPLY
        elif "---Candidate Facts---" in content:
            text = json.dumps({"keep_ids": []})
        elif "---Recognised Entities---" in content:
            text = json.dumps({"triples": [[_SUBJECT, _PREDICATE, _OBJECT]]})
        else:
            text = json.dumps({"entities": [_SUBJECT, _OBJECT]})
        return ChatResult(
            text=text,
            tokens=TokenAccounting(prompt_tokens=5, completion_tokens=4, call_count=1, counted_by="stub-llm"),
            resolved_model_identity="stub-llm-model",
        )


async def test_the_answer_is_generated_text_not_the_joined_evidence(store_root):
    """HIPP-13 (D-19): the envelope answer is what the qa node generates from the hydrated passages,
    not the evidence contents joined by blank lines."""
    llm = _StubQaAwareLLMClient()
    engine, selector = await _ingested_engine(store_root, llm)

    envelope = await engine.query(QueryObject(text="What did Ed Wood direct?"), selector)

    resolved = [await engine.resolve_evidence(ref) for ref in envelope.evidence]
    joined = "\n\n".join(str(record.get("content", "")) for record in resolved)
    assert envelope.evidence
    assert envelope.answer != joined
    assert envelope.answer == "low-budget films"
    assert len(llm.qa_calls) == 1


class _KeepAllFactsLLMClient(_StubIngestQueryLLMClient):
    """Like the write-path stub, but fact-filter keeps every candidate fact (the PPR branch)."""

    async def chat(self, messages, **kwargs):
        content = messages[0]["content"]
        if "---Candidate Facts---" not in content:
            return await super().chat(messages, **kwargs)
        return ChatResult(
            text=json.dumps({"keep_ids": re.findall(r"id=([^:\s]+):", content)}),
            tokens=TokenAccounting(prompt_tokens=5, completion_tokens=4, call_count=1, counted_by="stub-llm"),
            resolved_model_identity="stub-llm-model",
        )


async def _refs_over_twenty_documents(store_root, llm) -> list:
    engine = Databasise(
        store_root=store_root,
        workspace="hipporag-top-k-ws",
        clients={"embedding": _StubEmbeddingClient(), "llm": llm},
    )
    selector = Selector(capability=_HIPPORAG_CAPABILITY)
    for index in range(20):
        text = f"{_DOCUMENT_TEXT} Variant {index}."
        await engine.ingest(IngestDocument(document_id=f"top-k-doc-{index}", text=text), selector=selector)
    envelope = await engine.query(QueryObject(text="What did Ed Wood direct?"), selector)
    return list(envelope.evidence)


async def test_a_query_returns_at_most_top_k_items_on_both_branches(store_root, tmp_path):
    """HIPP-11 (D-20): over twenty documents each branch returns at most top_k (5) evidence refs, and
    every PPR ref scores above zero."""
    dpr_refs = await _refs_over_twenty_documents(store_root, _StubIngestQueryLLMClient())
    ppr_refs = await _refs_over_twenty_documents(tmp_path / "ppr-root", _KeepAllFactsLLMClient())

    assert {
        "dpr_within_top_k": len(dpr_refs) <= 5,
        "ppr_within_top_k": len(ppr_refs) <= 5,
        "ppr_scores_positive": all(ref.score > 0 for ref in ppr_refs),
    } == {"dpr_within_top_k": True, "ppr_within_top_k": True, "ppr_scores_positive": True}
