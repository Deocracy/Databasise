"""HippoRAG 2 query-side part bodies (PARTS.md ``## §H``) — the tracer's five-node slice.

``HIPPORAG_PARTS`` mirrors ``parts_core/lightrag/__init__.py``'s own ``LIGHTRAG_PARTS`` shape:
06-01-PLAN.md ports the five nodes ``fact-score``, ``fact-filter``, ``reset-vector-join``, ``ppr``
and ``assemble-result`` — the tracer's proven query-side chain. Later plans in this phase (06-02,
06-05, 06-07) add the remaining eight positions (``chunk-embed``, ``openie``, ``entity-fact-embed``,
``fact-edges``, ``passage-edges``, ``synonymy-edges``, ``graph-augment-persist``, ``dpr-fallback``).
``databasise/parts/registry.py``'s ``default_registry()`` merges this tuple into the machine's
registry alongside ``PARTS``, ``DECLARED_ONLY_PARTS`` and ``LIGHTRAG_PARTS``.
"""

from __future__ import annotations

from databasise.parts.schema import Part
from databasise.parts_core.hipporag.assemble_result import HIPPORAG_RESULT_ASSEMBLER_PART
from databasise.parts_core.hipporag.fact_filter import HIPPORAG_FACT_FILTER_PART
from databasise.parts_core.hipporag.fact_score import HIPPORAG_FACT_SCORER_PART
from databasise.parts_core.hipporag.ppr import HIPPORAG_PPR_RETRIEVER_PART
from databasise.parts_core.hipporag.reset_vector_join import HIPPORAG_RESET_VECTOR_JOIN_PART

HIPPORAG_PARTS: tuple[Part, ...] = (
    HIPPORAG_FACT_SCORER_PART,
    HIPPORAG_FACT_FILTER_PART,
    HIPPORAG_RESET_VECTOR_JOIN_PART,
    HIPPORAG_PPR_RETRIEVER_PART,
    HIPPORAG_RESULT_ASSEMBLER_PART,
)

__all__ = ["HIPPORAG_PARTS"]
