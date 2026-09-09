"""HippoRAG 2 part bodies (PARTS.md ``## §H``) — the tracer's five-node query-side slice, plus
06-02-PLAN.md's three index-side positions, plus 06-05-PLAN.md's four graph-construction positions.

``HIPPORAG_PARTS`` mirrors ``parts_core/lightrag/__init__.py``'s own ``LIGHTRAG_PARTS`` shape:
06-01-PLAN.md ported the five nodes ``fact-score``, ``fact-filter``, ``reset-vector-join``, ``ppr``
and ``assemble-result`` — the tracer's proven query-side chain. 06-02-PLAN.md added the first three
of the seven index-side positions — ``chunk-embed``, ``openie``, ``entity-fact-embed``. 06-05-PLAN.md
adds the remaining four index-side positions — ``fact-edges``, ``passage-edges``, ``synonymy-edges``,
``graph-augment-persist`` — completing the index side. A later plan (06-07) adds the one remaining
query-side position, ``dpr-fallback``.
``databasise/parts/registry.py``'s ``default_registry()`` merges this tuple into the machine's
registry alongside ``PARTS``, ``DECLARED_ONLY_PARTS`` and ``LIGHTRAG_PARTS``.
"""

from __future__ import annotations

from databasise.parts.schema import Part
from databasise.parts_core.hipporag.assemble_result import HIPPORAG_RESULT_ASSEMBLER_PART
from databasise.parts_core.hipporag.chunk_embed import HIPPORAG_CHUNKER_EMBEDDER_PART
from databasise.parts_core.hipporag.entity_fact_embed import HIPPORAG_ENTITY_FACT_EMBEDDER_PART
from databasise.parts_core.hipporag.fact_edges import HIPPORAG_FACT_EDGE_BUILDER_PART
from databasise.parts_core.hipporag.fact_filter import HIPPORAG_FACT_FILTER_PART
from databasise.parts_core.hipporag.fact_score import HIPPORAG_FACT_SCORER_PART
from databasise.parts_core.hipporag.openie import HIPPORAG_OPENIE_EXTRACTOR_PART
from databasise.parts_core.hipporag.passage_edges import HIPPORAG_PASSAGE_EDGE_BUILDER_PART
from databasise.parts_core.hipporag.ppr import HIPPORAG_PPR_RETRIEVER_PART
from databasise.parts_core.hipporag.reset_vector_join import HIPPORAG_RESET_VECTOR_JOIN_PART

HIPPORAG_PARTS: tuple[Part, ...] = (
    HIPPORAG_FACT_SCORER_PART,
    HIPPORAG_FACT_FILTER_PART,
    HIPPORAG_RESET_VECTOR_JOIN_PART,
    HIPPORAG_PPR_RETRIEVER_PART,
    HIPPORAG_RESULT_ASSEMBLER_PART,
    HIPPORAG_CHUNKER_EMBEDDER_PART,
    HIPPORAG_OPENIE_EXTRACTOR_PART,
    HIPPORAG_ENTITY_FACT_EMBEDDER_PART,
    HIPPORAG_FACT_EDGE_BUILDER_PART,
    HIPPORAG_PASSAGE_EDGE_BUILDER_PART,
)

__all__ = ["HIPPORAG_PARTS"]
