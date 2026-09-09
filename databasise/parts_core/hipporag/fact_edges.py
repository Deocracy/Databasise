"""``hipporag/fact-edge-builder`` (HippoRAG 2 base wiring position ``fact-edges``, PARTS.md
``## §H``) — a pure entity-to-entity co-occurrence edge transform. Ported by search from
``hipporag/HippoRAG.py:327``, ``:867-913``.

``## §H`` types this row ``extractor`` by nearest signature only, with declared effects the empty
list: this node reaches no store and no client of its own — the graph write happens once,
downstream, at ``graph-augment-persist``. This body genuinely makes zero store/client calls, so no
additive-effects discrepancy is recorded here (unlike ``chunk-embed``/``entity-fact-embed``, whose
own store writes forced an additive declaration).

Reads ``ctx.inputs["openie"]["findings"]`` directly (this node's sole dep, per the governing
wiring), never ``entity-fact-embed``'s already-deduped fact records — the per-triple view is what
lets the symmetric co-occurrence *count* be counted at all; a deduped fact record has already
collapsed that count away.

Weight is the symmetric co-occurrence count: the number of triples (findings) in which the same
unordered entity pair appears. Endpoint pairs are canonicalised by sorted vertex ref — the same
order-insensitive-pair convention ``databasise/parts_core/lightrag/join_roundrobin.py``'s own
``_relation_key`` already establishes, rather than inventing a second one — so ``A-B`` and ``B-A``
collapse to one edge, never two.

Entity vertex refs use ``ENTITY_VERTEX_PREFIX`` imported from ``entity_fact_embed.py`` (the
identity space ``export_to_igraph``/``reset-vector-join``/``ppr`` all share) — this module defines
no prefix literal of its own.
"""

from __future__ import annotations

from typing import Any

from databasise.parts.schema import NodeContext, Part
from databasise.parts_core.hipporag.entity_fact_embed import ENTITY_VERTEX_PREFIX

_NAME_AT_VERSION = "hipporag/fact-edge-builder@0.1.0"
_EDGE_TYPE = "fact-cooccurrence"


def _entity_ref(raw: Any) -> str:
    return f"{ENTITY_VERTEX_PREFIX}{str(raw).strip().lower()}"


def _canonical_pair(a: str, b: str) -> tuple[str, str]:
    return tuple(sorted((a, b)))  # type: ignore[return-value]


async def _fact_edges_body(ctx: NodeContext) -> dict[str, Any]:
    return {"edges": []}


HIPPORAG_FACT_EDGE_BUILDER_PART = Part(
    name_at_version=_NAME_AT_VERSION,
    kind="extractor",
    structural_depth="opaque",
    effects=[],
    upstream_ref="hipporag/src/hipporag/HippoRAG.py",
    body=_fact_edges_body,
)
