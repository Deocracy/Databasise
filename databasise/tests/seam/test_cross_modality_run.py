"""06-01-PLAN.md Task 2: HippoRAG 2's five-node query-side chain answers one real query end to end
through the §18 seam, over its own isolated stores, reached by a caller-supplied capability
selector — the phase's architectural de-risking tracer. Mirrors
``databasise/tests/seam/test_trace_token.py``'s synthetic-store/stub-client pattern: no network,
no imported parity index.

Cross-package fixture import (documented in ``tests/parts_core/hipporag/conftest.py``'s own
module docstring): ``databasise/tests/`` carries no top-level ``__init__.py``, so pytest's default
import mode inserts ``tests/`` onto ``sys.path`` and every immediate subpackage
(``parts_core``, ``seam``, ...) is importable as a top-level module from any other test under
``tests/``.
"""

from __future__ import annotations

import json

import pytest

from databasise.clients.base import ChatResult, EmbeddingResult
from databasise.parts.registry import default_registry
from databasise.runner.trace import TokenAccounting
from databasise.seam import Databasise, QueryObject
from databasise.seam.selectors import Selector, resolve_selector
from parts_core.hipporag.conftest import seeded_hipporag_store  # noqa: F401 — fixture import

_QUERY_TEXT = "What sat on the mat?"

# A capability set only HippoRAG's own 5-node wiring satisfies at the smallest resolved size —
# every LightRAG arm satisfying it (hybrid/local/global, via entity-hydrate-expand/chunk-sel-kg)
# resolves far more nodes, so the "smallest resolved wiring wins" tie-break
# (databasise/seam/selectors.py) picks HippoRAG's wiring deterministically.
_HIPPORAG_CAPABILITY = ["reads_graph", "reads_kv"]


class _StubEmbeddingClient:
    def __init__(self, vector: list[float]):
        self.vector = vector

    async def embed(self, texts, **kwargs):
        return EmbeddingResult(
            vectors=[self.vector for _ in texts],
            tokens=TokenAccounting(prompt_tokens=len(texts), call_count=1, counted_by="stub-embed"),
            resolved_model_identity="stub-embed-model",
        )


class _StubLLMClient:
    """Confirms every candidate fact-filter hands it as relevant — the tracer's own happy path,
    not fact-filter's own filtering logic (untested here; 06-01-PLAN.md Task 3 does not carry a
    dedicated fact-filter unit test, only the end-to-end shape)."""

    async def chat(self, messages, **kwargs):
        return ChatResult(
            text=json.dumps({"keep_ids": ["f1", "f2"]}),
            tokens=TokenAccounting(
                prompt_tokens=5, completion_tokens=4, call_count=1, counted_by="stub-llm"
            ),
            resolved_model_identity="stub-llm-model",
        )


def _make_engine(seeded_hipporag_store) -> Databasise:
    return Databasise(
        store_root=seeded_hipporag_store["store_root"],
        workspace=seeded_hipporag_store["workspace"],
        clients={
            "embedding": _StubEmbeddingClient(vector=seeded_hipporag_store["query_vector"]),
            "llm": _StubLLMClient(),
        },
    )


async def test_hipporag_query_returns_evidence_from_its_own_chunks_namespace(seeded_hipporag_store):
    engine = _make_engine(seeded_hipporag_store)

    envelope = await engine.query(
        QueryObject(text=_QUERY_TEXT), Selector(capability=_HIPPORAG_CAPABILITY)
    )

    assert envelope.evidence
    assert envelope.evidence[0].namespace == "hipporag-chunks"
    for ref in envelope.evidence:
        assert ref.namespace == "hipporag-chunks"
    assert envelope.degraded is False
    assert envelope.partial is False
    # HippoRAG's base wiring has no generator position (06-01-PLAN.md's own named limitation) —
    # the answer carries assembled context from the fixture's own chunk content.
    assert "cat" in envelope.answer.lower() or "mat" in envelope.answer.lower()


async def test_hipporag_query_does_not_touch_lightrags_store_directories(
    seeded_hipporag_store, tmp_path
):
    """RIG §RUN.1/§RUN.2: HippoRAG's resolved graph/KV directories are disjoint from LightRAG's on
    the same store_root/workspace — proven here by asserting the HippoRAG-scoped directories exist
    and the LightRAG-scoped ones (chunk_entity_relation / text_chunks) do not appear."""
    engine = _make_engine(seeded_hipporag_store)
    await engine.query(QueryObject(text=_QUERY_TEXT), Selector(capability=_HIPPORAG_CAPABILITY))

    workspace_dir = seeded_hipporag_store["store_root"] / seeded_hipporag_store["workspace"]
    on_disk = {p.name for p in workspace_dir.iterdir() if p.is_dir()}
    assert "hipporag-graph" in on_disk
    assert "hipporag-text-chunks" in on_disk
    assert "chunk_entity_relation" not in on_disk
    assert "text_chunks" not in on_disk


def test_capability_selector_for_rerank_still_resolves_a_lightrag_arm():
    registry = default_registry()
    resolved = resolve_selector(Selector(capability=["calls_rerank"]), registry=registry)
    assert resolved.get("wiring_id") == "lightrag-base"


def test_default_selector_still_resolves_naive(tmp_path):
    registry = default_registry()
    resolved = resolve_selector(None, registry=registry, store_root=tmp_path)
    assert resolved.get("wiring_id") == "lightrag-base"
    assert "generate" in resolved.get("nodes", {})
