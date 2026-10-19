"""``hipporag/document-remover`` — the HippoRAG corpus-delete position (Phase 12 D-12, HIPP-16).
Ported by search from upstream ``HippoRAG.delete`` (``hipporag/src/hipporag/HippoRAG.py:595-690``),
which retracts a document's chunks, then the facts and entities no remaining chunk supports.

The remover works from the per-document manifest ``doc:<document_id>`` -> ``{chunk_ids, fact_ids,
entities, ingested_at}`` that ``chunk-embed`` and ``entity-fact-embed`` write into
``hipporag-text-chunks`` in the same commit as the data (D-12). A document with no manifest (never
ingested, already deleted, or ingested before Phase 12) is ``not_found`` and nothing is staged.

What one removal stages, and what it deliberately keeps:

- the document's chunk vectors, chunk KV rows and chunk vertices (``delete_node`` hides every
  incident edge from ``get_edge``/``get_node_edges``/export, so no explicit edge delete is needed);
- each manifest fact's ``chunk_ids`` minus the removed chunks, in the KV record and the fact vector
  metadata; a fact left with no chunk is deleted from both. A fact another document still supports
  keeps that document's chunk ids;
- the removed chunk ids from ``cooccurrence_by_chunk`` on every edge of a surviving manifest entity,
  with ``weight`` recomputed as ``sum(cooccurrence_by_chunk) + synonymy_weight + passage_weight``
  (``graph_augment_persist``'s rule); an edge left with no co-occurrence, no synonymy and no
  passage weight is deleted, so a synonymy-only edge is never touched;
- each manifest entity left with no edge to a surviving chunk vertex (an orphan), with its vertex
  and its entity vector. It is returned in ``removed_entities`` so a re-ingest in the same run can
  treat it as new (D-12 re-ingest orphan fix).

This body only stages writes; it never calls a lifecycle method. The engine commits all stores
together, or drops them all (Phase 10 D-07). Document ids come from ``config["doc_id"]`` (the delete
path) or from ``config["documents"]`` (the ingest path); none is a no-op.
"""

from __future__ import annotations

from typing import Any

from databasise.parts.schema import NodeContext, Part
from databasise.parts_core.hipporag.entity_fact_embed import CHUNK_VERTEX_PREFIX

_NAME_AT_VERSION = "hipporag/document-remover@0.1.0"
_CHUNKS_NAMESPACE = "hipporag-chunks"
_FACTS_NAMESPACE = "hipporag-facts"
_ENTITIES_NAMESPACE = "hipporag-entities"
_FACT_TYPE = "fact-cooccurrence"


def _document_ids(config: dict[str, Any]) -> list[str]:
    if config.get("doc_id"):
        return [str(config["doc_id"])]
    return [str(d["document_id"]) for d in config.get("documents") or [] if d.get("document_id")]


def _other_end(edge: dict[str, Any], vertex: str) -> str:
    return edge["tgt"] if edge["src"] == vertex else edge["src"]


class _Remover:
    """One run's removal state: the stores, and the committed fact vectors read at most once."""

    def __init__(self, ctx: NodeContext) -> None:
        self.kv = ctx.stores["kv"]
        self.graph = ctx.stores["graph"]
        self.vectors = ctx.stores["vector"]
        self._fact_vectors: dict[str, Any] | None = None

    def _committed_fact_vector(self, fact_id: str) -> Any | None:
        if self._fact_vectors is None:
            self._fact_vectors = dict(self.vectors.select(_FACTS_NAMESPACE).iter_vectors())
        return self._fact_vectors.get(fact_id)

    async def _reduce_fact(self, fact_id: str, removed: set[str]) -> None:
        facts = self.vectors.select(_FACTS_NAMESPACE)
        stored = await self.kv.get_by_id(f"fact:{fact_id}")
        remaining = [c for c in (stored or {}).get("chunk_ids", []) if c not in removed]
        if not remaining:
            await self.kv.delete([f"fact:{fact_id}"])
            await facts.delete_by_ids([fact_id])
            return
        await self.kv.upsert({f"fact:{fact_id}": {**stored, "chunk_ids": remaining}})
        metadata = facts.get_by_id(fact_id)
        vector = self._committed_fact_vector(fact_id)
        if metadata is not None and vector is not None:
            metadata.pop("id", None)  # reserved key (STOR-16); the id is passed separately
            await facts.upsert([fact_id], [vector], [{**metadata, "chunk_ids": remaining}])

    async def _reduce_cooccurrence(self, entity: str, removed: set[str], seen: set[tuple[str, str]]) -> None:
        for edge in await self.graph.get_node_edges(entity):
            pair = (edge["src"], edge["tgt"])
            attrs = edge["attrs"]
            by_chunk = attrs.get("cooccurrence_by_chunk")
            if pair in seen or not by_chunk or removed.isdisjoint(by_chunk):
                continue
            seen.add(pair)
            by_chunk = {c: n for c, n in by_chunk.items() if c not in removed}
            synonymy = float(attrs.get("synonymy_weight", 0.0))
            passage = float(attrs.get("passage_weight", 0.0))
            if not by_chunk and synonymy == 0.0 and passage == 0.0:
                await self.graph.delete_edge(edge["src"], edge["tgt"])
                continue
            types = [t for t in attrs.get("edge_types", []) if by_chunk or t != _FACT_TYPE]
            await self.graph.upsert_edge(
                edge["src"],
                edge["tgt"],
                {
                    **attrs,
                    "weight": sum(by_chunk.values()) + synonymy + passage,
                    "edge_types": types,
                    "cooccurrence_by_chunk": by_chunk,
                },
            )

    async def remove(self, document_id: str) -> tuple[bool, list[str]]:
        manifest = await self.kv.get_by_id(f"doc:{document_id}")
        if manifest is None:
            return False, []
        chunk_ids = [str(c) for c in manifest.get("chunk_ids", [])]
        removed = set(chunk_ids)

        if chunk_ids:
            await self.vectors.select(_CHUNKS_NAMESPACE).delete_by_ids(chunk_ids)
            await self.kv.delete(chunk_ids)
        for chunk_id in chunk_ids:
            await self.graph.delete_node(f"{CHUNK_VERTEX_PREFIX}{chunk_id}")

        for fact_id in manifest.get("fact_ids", []):
            await self._reduce_fact(str(fact_id), removed)

        entities = [str(e) for e in manifest.get("entities", [])]
        orphans: list[str] = []
        for entity in entities:
            neighbours = [_other_end(e, entity) for e in await self.graph.get_node_edges(entity)]
            if not any(n.startswith(CHUNK_VERTEX_PREFIX) for n in neighbours):
                orphans.append(entity)
        for entity in orphans:
            await self.graph.delete_node(entity)
        if orphans:
            await self.vectors.select(_ENTITIES_NAMESPACE).delete_by_ids(orphans)

        seen: set[tuple[str, str]] = set()
        for entity in entities:
            if entity not in orphans:
                await self._reduce_cooccurrence(entity, removed, seen)

        await self.kv.delete([f"doc:{document_id}"])
        return True, orphans


async def _document_remover_body(ctx: NodeContext) -> dict[str, Any]:
    remover = _Remover(ctx)
    found = False
    removed_entities: set[str] = set()
    for document_id in _document_ids(ctx.config or {}):
        document_found, orphans = await remover.remove(document_id)
        found = found or document_found
        removed_entities.update(orphans)
    return {
        "status": "success" if found else "not_found",
        "message": "",
        "removed_entities": sorted(removed_entities),
    }


HIPPORAG_DOCUMENT_REMOVER_PART = Part(
    name_at_version=_NAME_AT_VERSION,
    kind="extractor",
    structural_depth="opaque",
    effects=["writes_kv", "writes_vector", "writes_graph"],
    upstream_ref="hipporag/src/hipporag/HippoRAG.py",
    body=_document_remover_body,
)
