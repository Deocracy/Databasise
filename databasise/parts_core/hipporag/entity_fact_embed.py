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

SECOND ADDITIVE EFFECTS DISCREPANCY (06-07-PLAN.md, closing the gap 06-05-SUMMARY.md's own "Next
Phase Readiness" section named and disposed to this plan): ``writes_kv`` is added here too.
``reset_vector_join.py`` (06-01, already committed) reads each surviving fact's own chunk
association from a KV ``fact:<id>`` -> ``{chunk_ids}`` record; before this plan, no code in this
repository wrote that record — only ``tests/parts_core/hipporag/conftest.py``'s
``seeded_hipporag_store`` fixture hand-seeded it for ``reset-vector-join``'s own isolated tests.
06-05-SUMMARY.md's disposition named ``reset-vector-join``'s KV-read interface as the more
load-bearing of the two (already committed, already declaring ``reads_kv``) and this node as the
one needing the additive write — this node already computes ``chunk_ids`` per fact for its own
fact-vector metadata, so writing the same data to the KV store under the ``fact:<id>`` key costs
one more store call, not a new computation.

Vertex-ref identity space: ``ENTITY_VERTEX_PREFIX``/``CHUNK_VERTEX_PREFIX`` below are the node
identity space ``export_to_igraph``, ``reset-vector-join`` and ``ppr`` all share — defined once
here and imported (never re-spelled) by 06-05's graph-construction nodes. Entity-prefixed and
chunk-prefixed refs resolve to disjoint vertex indices, which is what makes
``reset-vector-join``'s sum disjoint-support and order-insensitive per ``## §H``'s
``arm_precedence`` declaration.

Fact provenance accumulates across ingests (Phase 12 D-06, HIPP-09): the ``fact:<id>`` KV record and
the fact vector metadata both hold the stored chunk ids followed by this run's new ones.

Document manifests (Phase 12 D-12, HIPP-16): ``chunk-embed`` writes ``doc:<document_id>`` into the
chunk KV; this node maps each finding's chunk to its document through ``openie``'s ``chunks``
passthrough and fills that manifest's ``fact_ids`` and ``entities`` (vertex-prefixed refs), which
``hipporag/document-remover`` deletes by. A document with no manifest is skipped.

Re-ingest (D-12): in ``corpus-ingest.json`` this node also depends on ``document-remover``. An entity
the remover deleted and this run re-adds counts as new (``new_entities``), so its synonymy edges are
rebuilt; the committed vector store still holds the deleted entity until the commit, so
``get_by_id`` alone would call it old.

Each surviving fact's own entity refs (its subject/object, vertex-prefixed) are carried in that
fact's vector metadata — the same ``entities`` field ``reset-vector-join`` already reads off each
scored fact item (``databasise/parts_core/hipporag/reset_vector_join.py``) to accumulate phrase
weight onto the right graph vertices.
"""

from __future__ import annotations

from typing import Any

from databasise.parts.schema import NodeContext, Part
from databasise.runner.trace import sum_token_accountings

_NAME_AT_VERSION = "hipporag/entity-fact-embedder@0.1.0"
_ENTITIES_NAMESPACE = "hipporag-entities"
_FACTS_NAMESPACE = "hipporag-facts"

ENTITY_VERTEX_PREFIX = "entity:"
CHUNK_VERTEX_PREFIX = "chunk:"


async def _entity_fact_embed_body(ctx: NodeContext) -> dict[str, Any]:
    openie_output = ctx.inputs["openie"]
    findings = list(openie_output.get("findings", []))
    if not findings:
        return {"entities": [], "facts": [], "new_entities": []}

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

    # D-06 (HIPP-09): a fact seen in an earlier ingest keeps that ingest's chunk ids. The KV record
    # is the source of truth: stored ids first, then this run's new ids, so the union is stable.
    kv_store = ctx.stores["kv"]
    for fid, record in fact_records.items():
        stored = await kv_store.get_by_id(f"fact:{fid}")
        stored_ids = list((stored or {}).get("chunk_ids", []))
        record["chunk_ids"] = stored_ids + [c for c in record["chunk_ids"] if c not in stored_ids]

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
    # WR-02 (06-REVIEW.md): two embed() calls, one resolved_model_identity reported — a silent
    # last-wins/first-wins pick would hide a genuine per-call identity divergence (a
    # routing/fallback client, a test double simulating drift). reset_vector_join.py's own
    # arity-mismatch precedent (raise ValueError naming the disagreement, never a best-effort
    # merge) is mirrored here rather than silently discarding one call's identity.
    if entity_embed_result.resolved_model_identity != fact_embed_result.resolved_model_identity:
        raise ValueError(
            f"{ctx.node_id!r} embedded entities under model identity "
            f"{entity_embed_result.resolved_model_identity!r} but facts under "
            f"{fact_embed_result.resolved_model_identity!r} — a per-call identity divergence is a "
            "refusal, never a silently-dropped report"
        )

    entity_store = ctx.stores["vector"].select(_ENTITIES_NAMESPACE)
    removed = set(ctx.inputs.get("document-remover", {}).get("removed_entities", []))
    new_entities = [ref for ref in entity_refs if entity_store.get_by_id(ref) is None or ref in removed]
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

    # 06-07-PLAN.md: the additive fact:<id> -> {chunk_ids} KV write reset-vector-join.py already
    # reads — see this module's own docstring for the full disposition.
    await kv_store.upsert(
        {f"fact:{fid}": {"chunk_ids": fact_records[fid]["chunk_ids"]} for fid in fact_ids}
    )

    # D-12 (HIPP-16): fill the fact_ids and entities of each document's manifest, which chunk-embed
    # wrote in this same run. A document with no manifest is skipped, never invented here.
    document_by_chunk = {
        str(chunk["chunk_id"]): str(chunk["document_id"])
        for chunk in openie_output.get("chunks", [])
        if chunk.get("document_id") is not None
    }
    facts_by_document: dict[str, set[str]] = {}
    entities_by_document: dict[str, set[str]] = {}
    for finding in findings:
        document_id = document_by_chunk.get(str(finding.get("chunk_id")))
        if document_id is None:
            continue
        facts_by_document.setdefault(document_id, set()).add(str(finding["fact_id"]))
        entities_by_document.setdefault(document_id, set()).update(
            f"{ENTITY_VERTEX_PREFIX}{str(raw).strip().lower()}"
            for raw in (finding["subject"], finding["object"])
            if str(raw).strip()
        )
    for document_id in sorted(facts_by_document):
        manifest = await kv_store.get_by_id(f"doc:{document_id}")
        if manifest is not None:
            await kv_store.upsert(
                {
                    f"doc:{document_id}": {
                        **manifest,
                        "fact_ids": sorted(facts_by_document[document_id]),
                        "entities": sorted(entities_by_document[document_id]),
                    }
                }
            )

    return {
        "entities": [
            {"ref": ref, "surface_form": text}
            for ref, text in zip(entity_refs, entity_texts, strict=True)
        ],
        "facts": [{"fact_id": fid, **fact_records[fid]} for fid in fact_ids],
        "new_entities": new_entities,
        "tokens": sum_token_accountings([entity_embed_result.tokens, fact_embed_result.tokens]),
        "resolved_model_identity": entity_embed_result.resolved_model_identity,
    }


HIPPORAG_ENTITY_FACT_EMBEDDER_PART = Part(
    name_at_version=_NAME_AT_VERSION,
    kind="embedder",
    structural_depth="opaque",
    effects=["calls_embedding", "writes_vector", "writes_kv"],
    upstream_ref="hipporag/src/hipporag/HippoRAG.py",
    body=_entity_fact_embed_body,
)
