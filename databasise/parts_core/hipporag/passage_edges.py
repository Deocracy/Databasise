"""``hipporag/passage-edge-builder`` (HippoRAG 2 base wiring position ``passage-edges``,
PARTS.md ``## §H``) — a pure passage-to-entity unit-weight edge transform. Ported by search from
``hipporag/HippoRAG.py:328``, ``:915-957``.

``## §H`` types this row ``extractor`` by nearest signature only, with declared effects the empty
list — the same "reaches no store, no client, the graph write happens once downstream at
``graph-augment-persist``" disposition ``fact_edges.py``'s own module docstring states, and for the
same reason: this node genuinely makes zero store/client calls.

Reads ``ctx.inputs["openie"]["findings"]`` directly (this node's sole dep). For each finding,
emits one edge per (chunk, entity) pair the finding connects — chunk-subject and chunk-object —
deduplicated so the same (chunk, entity) pair arriving from two different triples in the same
chunk collapses to one edge, at unit weight (never a co-occurrence count; that is ``fact-edges``'
own semantics, not this node's).

Uses ``CHUNK_VERTEX_PREFIX`` on the chunk endpoint and ``ENTITY_VERTEX_PREFIX`` on the entity
endpoint, both imported from ``entity_fact_embed.py`` — this module defines no prefix literal of
its own.
"""

from __future__ import annotations

from typing import Any

from databasise.parts.schema import NodeContext, Part
from databasise.parts_core.hipporag.entity_fact_embed import (
    CHUNK_VERTEX_PREFIX,
    ENTITY_VERTEX_PREFIX,
)

_NAME_AT_VERSION = "hipporag/passage-edge-builder@0.1.0"
_EDGE_TYPE = "passage-entity"
_WEIGHT = 1.0


def _entity_ref(raw: Any) -> str:
    return f"{ENTITY_VERTEX_PREFIX}{str(raw).strip().lower()}"


def _chunk_ref(chunk_id: Any) -> str:
    return f"{CHUNK_VERTEX_PREFIX}{chunk_id}"


async def _passage_edges_body(ctx: NodeContext) -> dict[str, Any]:
    openie_output = ctx.inputs["openie"]
    findings = list(openie_output.get("findings", []))

    seen: set[tuple[str, str]] = set()
    edges: list[dict[str, Any]] = []
    for finding in findings:
        chunk_id = finding.get("chunk_id")
        if chunk_id is None:
            continue
        chunk_ref = _chunk_ref(chunk_id)
        for raw_entity in (finding["subject"], finding["object"]):
            entity_ref = _entity_ref(raw_entity)
            pair = (chunk_ref, entity_ref)
            if pair in seen:
                continue
            seen.add(pair)
            edges.append(
                {"src": chunk_ref, "tgt": entity_ref, "weight": _WEIGHT, "edge_type": _EDGE_TYPE}
            )

    return {"edges": sorted(edges, key=lambda e: (e["src"], e["tgt"]))}


HIPPORAG_PASSAGE_EDGE_BUILDER_PART = Part(
    name_at_version=_NAME_AT_VERSION,
    kind="extractor",
    structural_depth="opaque",
    effects=[],
    upstream_ref="hipporag/src/hipporag/HippoRAG.py",
    body=_passage_edges_body,
)
