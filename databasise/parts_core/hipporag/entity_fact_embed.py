"""``hipporag/entity-fact-embedder`` (HippoRAG 2 base wiring position ``entity-fact-embed``,
PARTS.md ``## §H``) — embeds ``openie``'s findings into two isolated Vector namespaces: entities
and facts (declared capability ``§14.2 namespaces``). Ported by search from
``hipporag/HippoRAG.py:317,320``.

The two namespaces are separate because their query-side readers need different shapes over the
same underlying findings: ``fact-score`` scores against facts exhaustively (§14.2 ``score_all``)
while ``synonymy-edges`` runs a self-KNN over entities (§14.2 Vector self-KNN) — a single shared
namespace would make one of the two read the other's own records.

PARTS.md ``## §H`` declares this node's effects as ``calls_embedding`` alone.

ADDITIVE EFFECTS DISCREPANCY (06-02-PLAN.md Task 3, recorded per this plan's own SUMMARY.md, the
same case as this plan's own ``chunk-embed`` and 06-01's ``fact-score``): ``writes_vector`` is
added here in addition to the declared ``calls_embedding`` — this node writes two vector
namespaces, and ``CapabilityScopedStores.require`` hands a body no store handle for an undeclared
effect.

Vertex-ref identity space: ``ENTITY_VERTEX_PREFIX``/``CHUNK_VERTEX_PREFIX`` below are the node
identity space ``export_to_igraph``, ``reset-vector-join`` and ``ppr`` all share — defined once
here and imported (never re-spelled) by 06-05's graph-construction nodes. Entity-prefixed and
chunk-prefixed refs resolve to disjoint vertex indices, which is what makes
``reset-vector-join``'s sum disjoint-support and order-insensitive per ``## §H``'s
``arm_precedence`` declaration.

Each surviving fact's own entity refs (its subject/object, vertex-prefixed) are carried in that
fact's vector metadata — the same ``entities`` field ``reset-vector-join`` already reads off each
scored fact item (``databasise/parts_core/hipporag/reset_vector_join.py``) to accumulate phrase
weight onto the right graph vertices.
"""

from __future__ import annotations

from typing import Any

from databasise.parts.schema import NodeContext, Part
from databasise.runner.trace import TokenAccounting

_NAME_AT_VERSION = "hipporag/entity-fact-embedder@0.1.0"
_ENTITIES_NAMESPACE = "hipporag-entities"
_FACTS_NAMESPACE = "hipporag-facts"

ENTITY_VERTEX_PREFIX = "entity:"
CHUNK_VERTEX_PREFIX = "chunk:"


def _sum_token_accountings(accountings: list[TokenAccounting]) -> TokenAccounting:
    if not accountings:
        return TokenAccounting()
    unbudgetable = any(acc.counted_by == "unbudgetable" for acc in accountings)
    counted_by = "unbudgetable" if unbudgetable else accountings[0].counted_by
    return TokenAccounting(
        prompt_tokens=sum(acc.prompt_tokens for acc in accountings),
        completion_tokens=sum(acc.completion_tokens for acc in accountings),
        cached_read_tokens=sum(acc.cached_read_tokens for acc in accountings),
        call_count=sum(acc.call_count for acc in accountings),
        counted_by=counted_by,
    )


async def _entity_fact_embed_body(ctx: NodeContext) -> dict[str, Any]:
    openie_output = ctx.inputs["openie"]
    findings = list(openie_output.get("findings", []))
    if not findings:
        return {"entities": [], "facts": []}

    # Deduplicate entities by normalised (stripped, lower-cased) surface form, preserving the
    # first-seen display text for the vector's own metadata.
    entity_by_key: dict[str, str] = {}
    for finding in findings:
        for raw in (finding["subject"], finding["object"]):
            key = str(raw).strip().lower()
            if key and key not in entity_by_key:
                entity_by_key[key] = str(raw).strip()

    # Deduplicate facts by fact_id, aggregating every chunk_id that independently produced the
    # same triple — the divisor reset-vector-join's own phrase-weight scaling needs.
    fact_records: dict[str, dict[str, Any]] = {}
    for finding in findings:
        fact_id = str(finding["fact_id"])
        record = fact_records.get(fact_id)
        if record is None:
            record = {
                "subject": finding["subject"],
                "predicate": finding["predicate"],
                "object": finding["object"],
                "chunk_ids": [],
            }
            fact_records[fact_id] = record
        chunk_id = finding.get("chunk_id")
        if chunk_id is not None and chunk_id not in record["chunk_ids"]:
            record["chunk_ids"].append(chunk_id)

    entity_keys = sorted(entity_by_key)
    entity_texts = [entity_by_key[key] for key in entity_keys]
    entity_refs = [f"{ENTITY_VERTEX_PREFIX}{key}" for key in entity_keys]

    fact_ids = sorted(fact_records)
    fact_texts = [
        f"{fact_records[fid]['subject']} {fact_records[fid]['predicate']} {fact_records[fid]['object']}"
        for fid in fact_ids
    ]

    embedding_client = ctx.clients["embedding"]
    entity_embed_result = await embedding_client.embed(entity_texts)
    fact_embed_result = await embedding_client.embed(fact_texts)

    entity_store = ctx.stores["vector"].select(_ENTITIES_NAMESPACE)
    await entity_store.upsert(
        ids=entity_refs,
        embeddings=entity_embed_result.vectors,
        metadatas=[{"surface_form": text} for text in entity_texts],
    )

    fact_store = ctx.stores["vector"].select(_FACTS_NAMESPACE)
    await fact_store.upsert(
        ids=fact_ids,
        embeddings=fact_embed_result.vectors,
        metadatas=[
            {
                "subject": fact_records[fid]["subject"],
                "predicate": fact_records[fid]["predicate"],
                "object": fact_records[fid]["object"],
                "chunk_ids": fact_records[fid]["chunk_ids"],
                "entities": [
                    f"{ENTITY_VERTEX_PREFIX}{str(fact_records[fid]['subject']).strip().lower()}",
                    f"{ENTITY_VERTEX_PREFIX}{str(fact_records[fid]['object']).strip().lower()}",
                ],
            }
            for fid in fact_ids
        ],
    )

    return {
        "entities": [
            {"ref": ref, "surface_form": text}
            for ref, text in zip(entity_refs, entity_texts, strict=True)
        ],
        "facts": [{"fact_id": fid, **fact_records[fid]} for fid in fact_ids],
        "tokens": _sum_token_accountings([entity_embed_result.tokens, fact_embed_result.tokens]),
        "resolved_model_identity": entity_embed_result.resolved_model_identity,
    }


HIPPORAG_ENTITY_FACT_EMBEDDER_PART = Part(
    name_at_version=_NAME_AT_VERSION,
    kind="embedder",
    structural_depth="opaque",
    effects=["calls_embedding", "writes_vector"],
    upstream_ref="hipporag/src/hipporag/HippoRAG.py",
    body=_entity_fact_embed_body,
)
