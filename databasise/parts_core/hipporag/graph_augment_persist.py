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

**The collapse.** Distinct vertex refs across all three edge streams are each persisted once via
``upsert_node``. Edges are grouped by canonical endpoint pair (mirroring ``fact_edges.py``'s own
``_canonical_pair`` convention) and their weights summed into the single ``weight`` attribute
``export_to_igraph`` reads — ``## §H``'s "single ``weight`` edge attribute collapsing all three
edge types into one weighted view" clause. The contributing edge types are recorded on the edge's
own ``edge_types`` attrs list, so the collapse is auditable rather than lossy.

``ctx.stores["graph"]`` is a single, already-namespaced ``CozoGraphStore`` per run — never a
``.select()`` handle — the same architecture 06-01-PLAN.md's own key-decision already established
for ``reset-vector-join``/``ppr``.
"""

from __future__ import annotations

from typing import Any

from databasise.parts.schema import ArtifactScope, NodeContext, Part

_NAME_AT_VERSION = "hipporag/graph-materializer@0.1.0"
_ARTIFACT_SCOPE: ArtifactScope = "quarantined"
_EDGE_STREAM_NODE_IDS = ("fact-edges", "passage-edges", "synonymy-edges")


def _canonical_pair(a: str, b: str) -> tuple[str, str]:
    return tuple(sorted((a, b)))  # type: ignore[return-value]


async def _graph_augment_persist_body(ctx: NodeContext) -> dict[str, Any]:
    return {"artifact": {"node_count": 0, "edge_count": 0}, "artifact_scope": _ARTIFACT_SCOPE}


HIPPORAG_GRAPH_MATERIALIZER_PART = Part(
    name_at_version=_NAME_AT_VERSION,
    kind="extractor",
    structural_depth="opaque",
    effects=["writes_graph", "writes_artifact"],
    upstream_ref="hipporag/src/hipporag/HippoRAG.py",
    body=_graph_augment_persist_body,
    artifact_scope=_ARTIFACT_SCOPE,
)
