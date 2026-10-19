"""12-05 (HIPP-12 trace leg, HIPP-05): the HippoRAG query path through the public seam. A query run
dispatches only query-side nodes, and ``fact-filter`` receives the query text. Later Phase 12 plans
(12-07, 12-10, 12-11) add their row tests to this module."""

from __future__ import annotations

from databasise.seam import Databasise, QueryObject
from databasise.seam.corpus import IngestDocument
from databasise.seam.selectors import Selector
from seam.test_hipporag_write_path import (
    _DOCUMENT_TEXT,
    _HIPPORAG_CAPABILITY,
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
