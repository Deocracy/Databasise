"""LightRAG query-side part bodies (§L.1/§L.2) — the seventeen ported nodes plus embedder-index.

``LIGHTRAG_PARTS`` (03-04-PLAN.md Task 2) is the seven parts fitted for the ``naive`` arm's
tracer run; ``databasise/parts/registry.py``'s ``default_registry()`` merges it into the
machine's registry alongside ``PARTS`` and ``DECLARED_ONLY_PARTS``. The remaining eight base-wiring
positions (``keywords``, ``entity-lookup``, ``entity-hydrate-expand``, ``relation-lookup``,
``relation-hydrate-expand``, ``join-roundrobin``, ``truncator-token-budget``,
``chunk-selector-kg``) are plan 03-05/03-06's deliverable — the published unpatched base only
parses clean once every one of the fifteen new components is registered (see
``databasise/wirings/resolve.py``'s own module docstring).
"""

from __future__ import annotations

from databasise.parts.schema import Part
from databasise.parts_core.lightrag.assemble import LIGHTRAG_ASSEMBLER_KG_CONTEXT_PART
from databasise.parts_core.lightrag.chunk_vector import LIGHTRAG_RETRIEVER_CHUNK_TOPK_PART
from databasise.parts_core.lightrag.embedder_index import LIGHTRAG_EMBEDDER_INDEX_PART
from databasise.parts_core.lightrag.embedder_query import LIGHTRAG_EMBEDDER_QUERY_PART
from databasise.parts_core.lightrag.generate import LIGHTRAG_GENERATOR_LLM_PART
from databasise.parts_core.lightrag.heading_backfill import (
    LIGHTRAG_CHUNK_HEADING_BACKFILLER_PART,
)
from databasise.parts_core.lightrag.rerank import LIGHTRAG_RERANKER_CROSS_ENCODER_PART

LIGHTRAG_PARTS: tuple[Part, ...] = (
    LIGHTRAG_EMBEDDER_QUERY_PART,
    LIGHTRAG_RETRIEVER_CHUNK_TOPK_PART,
    LIGHTRAG_CHUNK_HEADING_BACKFILLER_PART,
    LIGHTRAG_RERANKER_CROSS_ENCODER_PART,
    LIGHTRAG_ASSEMBLER_KG_CONTEXT_PART,
    LIGHTRAG_GENERATOR_LLM_PART,
    LIGHTRAG_EMBEDDER_INDEX_PART,
)

__all__ = ["LIGHTRAG_PARTS"]
