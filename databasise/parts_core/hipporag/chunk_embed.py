"""``hipporag/chunker-embedder`` (HippoRAG 2 base wiring position ``chunk-embed``, PARTS.md
``## §H``) — the fused chunk-store-and-embed index-side position. Ported by search from
``hipporag/HippoRAG.py:282`` (``EmbeddingStore.insert_strings``), which fuses chunk storage and
embedding into one call with no external cut point (``§19.4`` — no knob at that boundary). This is
why the governing wiring's own ``recipe`` field names ``chunk-embed`` for both the ``chunker`` and
``embedding`` roles (``docs/system-model/wirings/hipporag-base.json``): chunking and embedding are
deliberately one node, not two, because upstream itself never exposes a seam between them.

PARTS.md ``## §H`` declares this node's effects as ``calls_embedding`` alone.

ADDITIVE EFFECTS DISCREPANCY (06-02-PLAN.md Task 1, recorded per this plan's own SUMMARY.md):
``writes_vector`` and ``writes_kv`` are added here in addition to the declared ``calls_embedding``
— ``CapabilityScopedStores.require`` hands a body no store handle for an undeclared effect, and
this node's own ``## §H`` description ("fused chunk-store + embed") is itself a store write, so a
store-writing body needs both write effects declared or it cannot reach ``ctx.stores`` at all.
Mirrors 06-01's own additive-declaration precedent for ``fact-score``'s ``calls_embedding`` and
``entity-fact-embed``'s ``writes_vector`` — recorded, never silently resolved either direction.

Unconfigured-run precedent: mirrors ``parts_core/lightrag/embedder_index.py``'s own rule — no
``config["documents"]`` (or an empty list) makes zero client calls and returns ``{"chunks": []}``,
so a query-time run of the base wiring (which never sets this key) costs nothing at this position.

Chunking: a deterministic, dependency-free sliding-window character chunker (``chunk_size``/
``chunk_overlap`` config keys, defaulting to 1200/100 characters below) — HippoRAG's own chunker
is not exercised here (it lives inside the opaque, quarantined index-side chain this node
represents; see PARTS.md ``## §H``'s Artifact scopes clause), only a stand-in with the same
input/output shape. Each ``chunk_id`` is a SHA-256 of the document id and the chunk's own ordinal
(never the chunk text), so re-dispatching the same document reproduces identical ids.
"""

from __future__ import annotations

import hashlib
from typing import Any

from databasise.parts.schema import NodeContext, Part

_NAME_AT_VERSION = "hipporag/chunker-embedder@0.1.0"
_CHUNKS_NAMESPACE = "hipporag-chunks"
_DEFAULT_CHUNK_SIZE = 1200
_DEFAULT_CHUNK_OVERLAP = 100


def _split_into_chunks(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """A deterministic, dependency-free sliding-window character chunker. Never advances past the
    end of ``text`` and never emits an empty trailing piece. ``chunk_overlap`` is clamped so the
    per-iteration step is always at least 1 character — a misconfigured overlap (``>= chunk_size``)
    can never produce an infinite loop.
    """
    if not text:
        return []
    if chunk_size <= 0 or len(text) <= chunk_size:
        return [text]

    step = max(chunk_size - max(chunk_overlap, 0), 1)
    pieces: list[str] = []
    start = 0
    while start < len(text):
        pieces.append(text[start : start + chunk_size])
        if start + chunk_size >= len(text):
            break
        start += step
    return pieces


async def _chunk_embed_body(ctx: NodeContext) -> dict[str, Any]:
    config = ctx.config or {}
    documents = config.get("documents") or []
    if not documents:
        return {"chunks": []}

    chunk_size = int(config.get("chunk_size", _DEFAULT_CHUNK_SIZE))
    chunk_overlap = int(config.get("chunk_overlap", _DEFAULT_CHUNK_OVERLAP))

    chunk_records: list[dict[str, Any]] = []
    for document in documents:
        document_id = str(document["document_id"])
        text = str(document.get("text", ""))
        for ordinal, piece in enumerate(_split_into_chunks(text, chunk_size, chunk_overlap)):
            chunk_id = hashlib.sha256(f"{document_id}:{ordinal}".encode("utf-8")).hexdigest()
            chunk_records.append(
                {
                    "chunk_id": chunk_id,
                    "document_id": document_id,
                    "ordinal": ordinal,
                    "text": piece,
                }
            )

    if not chunk_records:
        return {"chunks": []}

    embedding_client = ctx.clients["embedding"]
    embed_result = await embedding_client.embed([record["text"] for record in chunk_records])

    vector_store = ctx.stores["vector"].select(_CHUNKS_NAMESPACE)
    await vector_store.upsert(
        ids=[record["chunk_id"] for record in chunk_records],
        embeddings=embed_result.vectors,
        metadatas=[
            {
                "document_id": record["document_id"],
                "ordinal": record["ordinal"],
                # 06-10-PLAN.md (Rule 2 deviation): the chunk's own text, mirroring LightRAG's own
                # real vector-metadata convention (databasise/parity/import_index.py imports v1's
                # own "content"-carrying Faiss meta json verbatim). Without this, a real chunk
                # ingested through this node can never resolve to its own text via
                # databasise.seam.evidence.resolve_evidence_ref, which reads the vector store's
                # own metadata directly, never the sibling KV record this node also writes.
                "content": record["text"],
            }
            for record in chunk_records
        ],
    )

    kv_store = ctx.stores["kv"]
    await kv_store.upsert(
        {record["chunk_id"]: {"content": record["text"]} for record in chunk_records}
    )

    return {
        "chunks": chunk_records,
        "tokens": embed_result.tokens,
        "resolved_model_identity": embed_result.resolved_model_identity,
    }


HIPPORAG_CHUNKER_EMBEDDER_PART = Part(
    name_at_version=_NAME_AT_VERSION,
    kind="embedder",
    structural_depth="opaque",
    effects=["calls_embedding", "writes_vector", "writes_kv"],
    upstream_ref="hipporag/src/hipporag/HippoRAG.py",
    body=_chunk_embed_body,
)
