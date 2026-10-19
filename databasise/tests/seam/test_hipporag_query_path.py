"""12-05 (HIPP-12 trace leg, HIPP-05): the HippoRAG query path through the public seam. A query run
dispatches only query-side nodes, and ``fact-filter`` receives the query text. 12-07 adds the HIPP-12
row test (one embed per query). Later Phase 12 plans (12-10, 12-11) add their row tests to this module."""

from __future__ import annotations

from databasise.seam import Databasise, QueryObject
from databasise.seam.corpus import IngestDocument
from databasise.seam.selectors import Selector, resolve_selector
from seam.test_hipporag_write_path import (
    _DOCUMENT_TEXT,
    _HIPPORAG_CAPABILITY,
    _QUERY_VECTOR,
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
