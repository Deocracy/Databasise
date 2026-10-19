"""Phase 12 code-review fixes (12-REVIEW.md): A-CR-01, B-CR-01, B-WR-01..04 regression tests.

Kept in a new file because the tests that cover the neighbouring behaviour are ledger-protected.
No network, no v1 artifacts, no live client.
"""

from __future__ import annotations

import json
import math

import pytest

from databasise.clients.base import ChatResult, EmbeddingResult
from databasise.runner.trace import TokenAccounting
from databasise.seam import Databasise
from databasise.seam.corpus import IngestDocument
from databasise.seam.selectors import Selector
from databasise.stores.graph import CozoGraphStore

_HIPPORAG = Selector(capability=["reads_graph", "reads_kv"])
_D1_ENTITIES = ["x", "a1", "a2", "a3", "a4", "a5"]
_DIMS = 64


class _ClusterEmbeddingClient:
    """The d1 entities share one vector, ``y`` sits at cosine 0.9 from it, every other text is one-hot."""

    def __init__(self) -> None:
        self._slots: dict[str, int] = {}

    async def embed(self, texts, **kwargs):
        vectors = []
        for text in texts:
            key = text.strip().lower()
            if key in _D1_ENTITIES:
                vector = [1.0] + [0.0] * (_DIMS - 1)
            elif key == "y":
                vector = [0.9, math.sqrt(1 - 0.81)] + [0.0] * (_DIMS - 2)
            else:
                slot = 2 + self._slots.setdefault(key, len(self._slots))
                vector = [1.0 if i == slot else 0.0 for i in range(_DIMS)]
            vectors.append(vector)
        return EmbeddingResult(
            vectors=vectors,
            tokens=TokenAccounting(prompt_tokens=len(texts), call_count=1, counted_by="stub-embed"),
            resolved_model_identity="stub-embed-model",
        )


class _TwoDocumentLLMClient:
    async def chat(self, messages, **kwargs):
        content = messages[0]["content"]
        entities, triples = (
            (_D1_ENTITIES, [["x", "rel", a] for a in _D1_ENTITIES[1:]])
            if "DOC-ONE" in content
            else (["y", "z"], [["y", "rel", "z"]])
        )
        if "---Candidate Facts---" in content:
            text = json.dumps({"keep_ids": []})
        elif "---Recognised Entities---" in content:
            text = json.dumps({"triples": triples})
        else:
            text = json.dumps({"entities": entities})
        return ChatResult(
            text=text,
            tokens=TokenAccounting(prompt_tokens=5, completion_tokens=4, call_count=1, counted_by="stub-llm"),
            resolved_model_identity="stub-llm-model",
        )


async def test_reingesting_a_document_keeps_synonymy_edges_other_documents_created(store_root):
    """A-CR-01: y (document 2) has synonymy edges into document 1's entities. Re-ingesting document 1
    unchanged must not delete them, even though y's neighbours' own top-k no longer contain y."""
    workspace = "cross-doc-syn-ws"
    engine = Databasise(
        store_root=store_root,
        workspace=workspace,
        clients={"embedding": _ClusterEmbeddingClient(), "llm": _TwoDocumentLLMClient()},
    )

    async def y_synonymy_pairs() -> set[frozenset[str]]:
        graph_store = CozoGraphStore(namespace="hipporag-graph", workspace=workspace, store_root=store_root)
        try:
            return {
                frozenset((edge["src"], edge["tgt"]))
                for edge in await graph_store.get_node_edges("entity:y")
                if "synonymy" in edge["attrs"].get("edge_types", [])
            }
        finally:
            await graph_store.finalize()

    first = IngestDocument(document_id="doc-1", text="DOC-ONE is about x and its neighbours.")
    await engine.ingest(first, selector=_HIPPORAG)
    await engine.ingest(IngestDocument(document_id="doc-2", text="DOC-TWO is about y."), selector=_HIPPORAG)
    before = await y_synonymy_pairs()
    assert before, "the fixture must give y at least one synonymy edge into document 1"

    await engine.ingest(first, selector=_HIPPORAG)

    assert await y_synonymy_pairs() == before
