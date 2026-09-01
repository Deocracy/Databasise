"""LightRAG query-side part bodies (§L.1/§L.2) — all eighteen positions over fifteen registered
components.

``LIGHTRAG_PARTS`` started as the seven parts 03-04-PLAN.md fitted for the ``naive`` arm's tracer
run; ``databasise/parts/registry.py``'s ``default_registry()`` merges it into the machine's
registry alongside ``PARTS`` and ``DECLARED_ONLY_PARTS``. 03-05-PLAN.md added all five graph-half
positions: Task 2's ``keywords``/``entity-lookup``/``relation-lookup`` and Task 3's
``entity-hydrate-expand``/``relation-hydrate-expand``. 03-06-PLAN.md closes the set: Task 1's
``join-roundrobin`` (serving ``join-entities``/``join-relations``/``join-chunks``, three
positions), Task 2's ``truncator-token-budget`` (serving ``budget-entities``/``budget-relations``,
two positions) and ``chunk-selector-kg`` (``chunk-sel-kg``, one position) — fifteen registered
components over eighteen published base-wiring positions, the published unpatched base now parsing
clean (see ``databasise/wirings/resolve.py``'s own module docstring).
"""

from __future__ import annotations

from databasise.parts.schema import Part
from databasise.parts_core.lightrag.assemble import LIGHTRAG_ASSEMBLER_KG_CONTEXT_PART
from databasise.parts_core.lightrag.chunk_sel_kg import LIGHTRAG_CHUNK_SELECTOR_KG_PART
from databasise.parts_core.lightrag.chunk_vector import LIGHTRAG_RETRIEVER_CHUNK_TOPK_PART
from databasise.parts_core.lightrag.embedder_index import LIGHTRAG_EMBEDDER_INDEX_PART
from databasise.parts_core.lightrag.embedder_query import LIGHTRAG_EMBEDDER_QUERY_PART
from databasise.parts_core.lightrag.entity_hydrate_expand import (
    LIGHTRAG_ENTITY_HYDRATE_EXPAND_PART,
)
from databasise.parts_core.lightrag.entity_lookup import LIGHTRAG_ENTITY_LOOKUP_PART
from databasise.parts_core.lightrag.generate import LIGHTRAG_GENERATOR_LLM_PART
from databasise.parts_core.lightrag.heading_backfill import (
    LIGHTRAG_CHUNK_HEADING_BACKFILLER_PART,
)
from databasise.parts_core.lightrag.join_roundrobin import LIGHTRAG_JOIN_ROUNDROBIN_PART
from databasise.parts_core.lightrag.keywords import LIGHTRAG_KEYWORD_EXTRACTOR_PART
from databasise.parts_core.lightrag.relation_hydrate_expand import (
    LIGHTRAG_RELATION_HYDRATE_EXPAND_PART,
)
from databasise.parts_core.lightrag.relation_lookup import LIGHTRAG_RELATION_LOOKUP_PART
from databasise.parts_core.lightrag.rerank import LIGHTRAG_RERANKER_CROSS_ENCODER_PART
from databasise.parts_core.lightrag.truncator_token_budget import (
    LIGHTRAG_TRUNCATOR_TOKEN_BUDGET_PART,
)

LIGHTRAG_PARTS: tuple[Part, ...] = (
    LIGHTRAG_EMBEDDER_QUERY_PART,
    LIGHTRAG_RETRIEVER_CHUNK_TOPK_PART,
    LIGHTRAG_CHUNK_HEADING_BACKFILLER_PART,
    LIGHTRAG_RERANKER_CROSS_ENCODER_PART,
    LIGHTRAG_ASSEMBLER_KG_CONTEXT_PART,
    LIGHTRAG_GENERATOR_LLM_PART,
    LIGHTRAG_EMBEDDER_INDEX_PART,
    LIGHTRAG_KEYWORD_EXTRACTOR_PART,
    LIGHTRAG_ENTITY_LOOKUP_PART,
    LIGHTRAG_RELATION_LOOKUP_PART,
    LIGHTRAG_ENTITY_HYDRATE_EXPAND_PART,
    LIGHTRAG_RELATION_HYDRATE_EXPAND_PART,
    LIGHTRAG_JOIN_ROUNDROBIN_PART,
    LIGHTRAG_TRUNCATOR_TOKEN_BUDGET_PART,
    LIGHTRAG_CHUNK_SELECTOR_KG_PART,
)

__all__ = ["LIGHTRAG_PARTS"]
