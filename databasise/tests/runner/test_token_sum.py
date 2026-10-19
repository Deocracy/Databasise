"""HIPP-19 (12-02, D-07): token accountings that carry different ``counted_by`` labels are never
reported under one label. The shared helper is ``runner.trace.sum_token_accountings``; the HippoRAG
openie and entity-fact-embed bodies both route through it.

Symbols new in Phase 12 are reached with ``getattr`` or an in-body import so this module collects
against pre-fix code and the row test fails by AssertionError.
"""

from __future__ import annotations

import json
from typing import Any

from databasise.clients.base import ChatResult, EmbeddingResult
from databasise.parts.schema import NodeContext
from databasise.parts_core.hipporag.entity_fact_embed import HIPPORAG_ENTITY_FACT_EMBEDDER_PART
from databasise.parts_core.hipporag.openie import HIPPORAG_OPENIE_EXTRACTOR_PART
from databasise.runner import trace
from databasise.runner.trace import TokenAccounting
from databasise.stores.kv import SqliteKVStore
from databasise.stores.vector import MultiNamespaceVectorStore


def _ctx(node_id: str, **kwargs: Any) -> NodeContext:
    return NodeContext(
        node_id=node_id,
        config=kwargs.get("config"),
        inputs=kwargs.get("inputs") or {},
        stores=kwargs.get("stores") or {},
        clients=kwargs.get("clients") or {},
    )


class _MixedLabelLLM:
    """NER call reports ``tiktoken``, triple call reports ``provider``."""

    def __init__(self) -> None:
        self.calls = 0

    async def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> ChatResult:
        is_triple_call = self.calls % 2
        self.calls += 1
        text = json.dumps({"triples": [["cat", "sat_on", "mat"]]} if is_triple_call else {"entities": ["cat"]})
        label = "provider" if is_triple_call else "tiktoken"
        return ChatResult(
            text=text,
            tokens=TokenAccounting(
                prompt_tokens=5, completion_tokens=3, call_count=1, counted_by=label
            ),
            resolved_model_identity="stub-llm",
        )


class _MixedLabelEmbedder:
    """First embed call reports ``tiktoken``, second ``provider``; one model identity."""

    def __init__(self) -> None:
        self.calls = 0

    async def embed(self, texts: list[str], **kwargs: Any) -> EmbeddingResult:
        label = "provider" if self.calls else "tiktoken"
        self.calls += 1
        return EmbeddingResult(
            vectors=[[1.0, 0.0, 0.0] for _ in texts],
            tokens=TokenAccounting(prompt_tokens=len(texts), call_count=1, counted_by=label),
            resolved_model_identity="stub-embed",
        )


async def test_mixed_counters_never_share_one_label(tmp_path):
    helper = getattr(trace, "sum_token_accountings", None)

    openie_result = await HIPPORAG_OPENIE_EXTRACTOR_PART.body(
        _ctx(
            "openie",
            inputs={"chunk-embed": {"chunks": [{"chunk_id": "c1", "text": "The cat sat on the mat."}]}},
            clients={"llm": _MixedLabelLLM()},
        )
    )
    openie_tokens = openie_result["tokens"]

    embed_result = await HIPPORAG_ENTITY_FACT_EMBEDDER_PART.body(
        _ctx(
            "entity-fact-embed",
            inputs={"openie": openie_result},
            stores={
                "vector": MultiNamespaceVectorStore(workspace="ws", store_root=tmp_path),
                "kv": SqliteKVStore(namespace="hipporag-text-chunks", workspace="ws", store_root=tmp_path),
            },
            clients={"embedding": _MixedLabelEmbedder()},
        )
    )
    embed_tokens = embed_result["tokens"]

    assert openie_tokens.counted_by == "unbudgetable"
    assert (openie_tokens.prompt_tokens, openie_tokens.completion_tokens, openie_tokens.call_count) == (
        10,
        6,
        2,
    )
    assert embed_tokens.counted_by == "unbudgetable"
    assert embed_tokens.call_count == 2
    assert helper is not None, "runner.trace.sum_token_accountings does not exist"


def test_sum_token_accountings_label_rules():
    from databasise.runner.trace import UNBUDGETABLE_SENTINEL, sum_token_accountings

    def acc(label: str, prompt: int = 1) -> TokenAccounting:
        return TokenAccounting(prompt_tokens=prompt, call_count=1, counted_by=label)

    assert sum_token_accountings([]) == TokenAccounting()
    assert sum_token_accountings([acc("stub"), acc("stub")]).counted_by == "stub"
    assert sum_token_accountings([acc("stub"), acc("stub", 4)]).prompt_tokens == 5
    # a counted_by "none" no-call zero does not make a label mixed
    assert sum_token_accountings([acc("stub"), TokenAccounting()]).counted_by == "stub"
    assert sum_token_accountings([TokenAccounting(), TokenAccounting()]).counted_by == "none"
    assert sum_token_accountings([acc("stub"), acc(UNBUDGETABLE_SENTINEL)]).counted_by == UNBUDGETABLE_SENTINEL
    # exact-string comparison: different case is a different counter
    mixed = sum_token_accountings([acc("Tiktoken"), acc("tiktoken")])
    assert mixed.counted_by == UNBUDGETABLE_SENTINEL
    assert mixed.call_count == 2
