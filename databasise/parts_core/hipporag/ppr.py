"""``hipporag/ppr-retriever`` (HippoRAG 2 base wiring position ``ppr``, PARTS.md ``## §H``) —
whole-graph personalized PageRank via the native igraph/prpack implementation. Ported by search
from ``hipporag/HippoRAG.py:1709-1748``, readback at ``:1745-1747``.

Calls ``ctx.stores["graph"].export_to_igraph()`` — §14.2's Graph bulk-export sub-capability
(``databasise/stores/graph.py``). **Deviation from 06-01-PLAN.md's literal action prose (Rule 1 —
bug, recorded per SUMMARY.md):** the plan's own prose names
``ctx.stores["graph"].select("hipporag-graph").export_to_igraph()``, but ``CozoGraphStore`` is not
a multi-namespace handle — only the vector store is (``MultiNamespaceVectorStore``). The plan's own
``store_namespaces`` seam-coupling task item settles this explicitly: "The vector key stays
MultiNamespaceVectorStore: vector isolation is already a side effect of each part selecting its own
namespace by name" — implying kv/graph are each a single store already scoped to the resolved
wiring's own ``store_namespaces`` declaration by ``Databasise._build_stores``, with no further
per-node ``.select()`` call. ``ctx.stores["graph"]`` is therefore already the
``hipporag-graph``-namespaced store; adding a ``.select()`` call would raise
``AttributeError`` against the real ``CozoGraphStore`` class. This is the architecturally
consistent reading, not a new decision.

Aligns the reset vector (``reset-vector-join``'s ``reset_vector``/``vertex_names`` pair) to the
exported graph's own vertex order — a dense array of length ``graph.vcount()``, default ``0.0``
for any graph vertex the join did not touch, positioned by ``graph.vs["name"]``. Every NaN and
every negative entry in that aligned array is replaced with ``0`` before the call (HippoRAG's own
guard against a malformed reset vector poisoning the whole-graph walk). Damping defaults to
``0.5`` — HippoRAG's own default, deliberately not igraph's own ``0.85`` default.

Reads back only the passage-node vertex partition — this plan's own fixture convention, vertex
names carrying the ``"chunk:"`` prefix (documented here as this plan's own naming convention; the
conftest fixture under ``tests/parts_core/hipporag/`` seeds graph nodes matching it) — sorted
descending by score, emitted as ``text_chunk``-kind scored items.
"""

from __future__ import annotations

import math
from typing import Any

from databasise.parts.schema import NodeContext, Part

_NAME_AT_VERSION = "hipporag/ppr-retriever@0.1.0"
_DEFAULT_DAMPING = 0.5
_PASSAGE_VERTEX_PREFIX = "chunk:"


async def _ppr_body(ctx: NodeContext) -> dict[str, Any]:
    config = ctx.config or {}
    damping = float(config.get("damping", _DEFAULT_DAMPING))

    graph_store = ctx.stores["graph"]
    graph = await graph_store.export_to_igraph()

    join_output = ctx.inputs["reset-vector-join"]
    join_vertex_names: list[str] = list(join_output.get("vertex_names", []))
    join_reset_vector: list[float] = list(join_output.get("reset_vector", []))
    join_weight_by_name = dict(zip(join_vertex_names, join_reset_vector, strict=True))

    graph_vertex_names: list[str] = list(graph.vs["name"])
    reset: list[float] = []
    for vertex_name in graph_vertex_names:
        value = join_weight_by_name.get(vertex_name, 0.0)
        if isinstance(value, float) and math.isnan(value):
            value = 0.0
        if value < 0:
            value = 0.0
        reset.append(float(value))

    scores: list[float]
    if graph.vcount() == 0 or sum(reset) == 0:
        # No vertices, or every reset entry zeroed out (a degenerate input this plan's own
        # <flagged_assumptions> names as unresolved — MODAL-04's unclassified edge behaviour):
        # igraph's own personalized_pagerank raises on an all-zero reset vector rather than
        # returning a defined result, so this branch returns an all-zero score vector instead of
        # letting that exception propagate as an opaque node-dispatch failure.
        scores = [0.0] * graph.vcount()
    else:
        scores = graph.personalized_pagerank(
            vertices=range(graph.vcount()),
            damping=damping,
            directed=False,
            weights="weight",
            reset=reset,
            implementation="prpack",
        )

    items = [
        {"id": name, "score": float(score), "kind": "text_chunk"}
        for name, score in zip(graph_vertex_names, scores, strict=True)
        if name.startswith(_PASSAGE_VERTEX_PREFIX)
    ]
    items.sort(key=lambda item: (-item["score"], item["id"]))

    return {"items": items}


HIPPORAG_PPR_RETRIEVER_PART = Part(
    name_at_version=_NAME_AT_VERSION,
    kind="retriever",
    structural_depth="opaque",
    effects=["reads_graph"],
    upstream_ref="hipporag/src/hipporag/HippoRAG.py",
    body=_ppr_body,
)
