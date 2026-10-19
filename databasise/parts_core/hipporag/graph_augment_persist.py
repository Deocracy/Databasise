"""``hipporag/graph-materializer`` (HippoRAG 2 base wiring position ``graph-augment-persist``,
PARTS.md ``## §H``) — the whole-graph materialisation position: the last of HippoRAG's seven
index-side positions, and the one that turns ``fact-edges``/``passage-edges``/``synonymy-edges``'s
three separate edge streams into the single persisted, weighted graph ``ppr`` reads back via
``CozoGraphStore.export_to_igraph``. Ported by search from ``hipporag/HippoRAG.py:334-335``,
``:1146-1230`` (``save_igraph`` at ``:1225-1230``). No ``§13.4`` row names a whole-graph
materialisation step; this node is typed ``extractor`` by nearest signature only, without that
row's own query/LLM call signature.

``## §H`` declares no effects for this row; ``writes_graph`` and ``writes_artifact`` are added
here — ADDITIVE EFFECTS DISCREPANCY, recorded per this plan's own instruction, the same case as
``chunk-embed``/``entity-fact-embed`` — because this node's own described behaviour is a
whole-graph store write producing a persisted index, and ``CapabilityScopedStores.require`` hands
a body no store handle for an undeclared effect.

``artifact_scope`` is set on the ``Part`` itself, never on the wiring node —
``parts_core/lightrag/embedder_index.py``'s own established convention (``WiringNode``'s schema,
``databasise/parts/schema.py``, ``extra="forbid"``, declares no ``artifact_scope`` field at all —
adding it to a registered wiring node raises ``WiringRefusedError`` at parse time; the illustrative
``docs/system-model/wirings/hipporag-base.json`` copy is not wire-schema-constrained the way the
registered wiring is). The value is ``quarantined``: ``## §H``'s own Artifact scopes clause states
the whole index side (``chunk-embed`` through ``graph-augment-persist``) is undecomposed relative
to any prior port on this record, so its effective depth is ``opaque`` under CONTRACT.md §3's taint
rule, and its output MUST NOT go to ``shared`` (CONTRACT.md §3: "An opaque node MAY write
``quarantined`` and MUST NOT write ``shared``"). A ``shared`` write here would make an index that
has earned nothing eligible for reuse by another arm.

**The collapse and the cross-ingest merge (D-04).** Distinct vertex refs across all three edge
streams are each persisted once via ``upsert_node``. Edges are grouped by canonical endpoint pair
(mirroring ``fact_edges.py``'s own ``_canonical_pair`` convention). For each pair the stored edge is
read (``get_edge``) and merged with this run's contribution, then written back through
``upsert_edge``: ``cooccurrence_by_chunk`` is the stored map overwritten per chunk key by the run's
``fact-cooccurrence`` counts (a fact edge without ``by_chunk`` contributes its weight under key
``""``), so re-ingesting the same chunk ids raises nothing; ``synonymy_weight`` is the max of stored
and incoming; ``passage_weight`` is 1.0 once a ``passage-entity`` edge was seen and never a count;
``edge_types`` is stored types then new ones; ``weight = sum(cooccurrence_by_chunk) +
synonymy_weight + passage_weight`` is the single attribute ``export_to_igraph`` reads (``## §H``'s
"single ``weight`` edge attribute collapsing all three edge types into one weighted view" clause).
The map and the types are persisted on the edge, not exported. An edge of any other type raises
``ValueError``. Stores written before Phase 12 carry no per-chunk map and are rebuild-required. The
``passage-edges`` ``vertices`` stream is upserted too, so a chunk with no edge still gets a vertex
(HIPP-06, D-02).

``ctx.stores["graph"]`` is a single, already-namespaced ``CozoGraphStore`` per run — never a
``.select()`` handle — the same architecture 06-01-PLAN.md's own key-decision already established
for ``reset-vector-join``/``ppr``.

**No commit here (10-04, D-07, D-09).** The body only stages its writes in the store's pending
buffer. The engine commits the graph together with the kv and vector stores once the whole run
succeeded, and drops all of them when any node fails, so a part never calls a lifecycle method.
"""

from __future__ import annotations

from typing import Any

from databasise.parts.schema import ArtifactScope, NodeContext, Part

_NAME_AT_VERSION = "hipporag/graph-materializer@0.1.0"
_ARTIFACT_SCOPE: ArtifactScope = "quarantined"
_EDGE_STREAM_NODE_IDS = ("fact-edges", "passage-edges", "synonymy-edges")
_FACT_TYPE = "fact-cooccurrence"
_SYNONYMY_TYPE = "synonymy"
_PASSAGE_TYPE = "passage-entity"


def _canonical_pair(a: str, b: str) -> tuple[str, str]:
    return tuple(sorted((a, b)))  # type: ignore[return-value]


async def _graph_augment_persist_body(ctx: NodeContext) -> dict[str, Any]:
    all_edges: list[dict[str, Any]] = []
    for node_id in _EDGE_STREAM_NODE_IDS:
        stream = ctx.inputs.get(node_id, {})
        all_edges.extend(stream.get("edges", []))

    vertex_refs: set[str] = set(ctx.inputs.get("passage-edges", {}).get("vertices", []))
    incoming: dict[tuple[str, str], dict[str, Any]] = {}
    for edge in all_edges:
        src, tgt = str(edge["src"]), str(edge["tgt"])
        vertex_refs.add(src)
        vertex_refs.add(tgt)
        edge_type = str(edge.get("edge_type", "unknown"))
        slot = incoming.setdefault(
            _canonical_pair(src, tgt),
            {"by_chunk": {}, "synonymy": 0.0, "passage": 0.0, "types": []},
        )
        if edge_type == _FACT_TYPE:
            by_chunk = edge.get("by_chunk") or {"": float(edge.get("weight", 1.0))}
            for chunk_id, count in by_chunk.items():
                slot["by_chunk"][chunk_id] = slot["by_chunk"].get(chunk_id, 0.0) + float(count)
        elif edge_type == _SYNONYMY_TYPE:
            slot["synonymy"] = max(slot["synonymy"], float(edge.get("weight", 1.0)))
        elif edge_type == _PASSAGE_TYPE:
            slot["passage"] = 1.0
        else:
            raise ValueError(f"graph-augment-persist: unknown edge type {edge_type!r}")
        if edge_type not in slot["types"]:
            slot["types"].append(edge_type)

    graph_store = ctx.stores["graph"]
    for vertex_ref in sorted(vertex_refs):
        await graph_store.upsert_node(vertex_ref, {})
    for (src, tgt), slot in incoming.items():
        stored = await graph_store.get_edge(src, tgt) or {}
        by_chunk = {**stored.get("cooccurrence_by_chunk", {}), **slot["by_chunk"]}
        synonymy_weight = max(float(stored.get("synonymy_weight", 0.0)), slot["synonymy"])
        passage_weight = max(float(stored.get("passage_weight", 0.0)), slot["passage"])
        edge_types = list(dict.fromkeys([*stored.get("edge_types", []), *slot["types"]]))
        await graph_store.upsert_edge(
            src,
            tgt,
            {
                "weight": sum(by_chunk.values()) + synonymy_weight + passage_weight,
                "edge_types": edge_types,
                "cooccurrence_by_chunk": by_chunk,
                "synonymy_weight": synonymy_weight,
                "passage_weight": passage_weight,
            },
        )

    return {
        "artifact": {"node_count": len(vertex_refs), "edge_count": len(incoming)},
        "artifact_scope": _ARTIFACT_SCOPE,
    }


HIPPORAG_GRAPH_MATERIALIZER_PART = Part(
    name_at_version=_NAME_AT_VERSION,
    kind="extractor",
    structural_depth="opaque",
    effects=["writes_graph", "writes_artifact"],
    upstream_ref="hipporag/src/hipporag/HippoRAG.py",
    body=_graph_augment_persist_body,
    artifact_scope=_ARTIFACT_SCOPE,
)
