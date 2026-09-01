"""``lightrag/chunk-selector-kg`` (base wiring position `chunk-sel-kg`, one of eighteen positions)
— selects chunk ids related to the truncated entity/relation lists (``budget-entities``,
``budget-relations``), primary method ``config["pick_method"]`` falling back to
``config["fallback_pick_method"]`` when the primary yields nothing, then hydrates the selected
ids' content from the KV store. Ported by search from ``v1/lightrag/operate.py``'s
``_find_related_text_unit_from_entities``/``_find_related_text_units_from_relationships`` (the
shared WEIGHT/VECTOR chunk-selection algorithm) and ``v1/lightrag/utils.py``'s
``pick_by_weighted_polling``/``pick_by_vector_similarity`` (``utils.py:3991-4160``).

**WEIGHT** (v1/lightrag/utils.py:3991-4064, ported by copy): each entity/relation item's own
``source_id`` field (``<SEP>``-joined chunk ids, v1's own ``GRAPH_FIELD_SEP``,
``v1/lightrag/constants.py:49``) is split into candidate chunk ids; a chunk id already claimed by
an earlier-positioned item is dropped from every later item (v1's own earlier-position-wins dedup),
each item's remaining chunks are sorted by global occurrence count descending, and a linear
gradient allocates more chunks to earlier (higher-importance) items than later ones —
``config["related_chunk_number"]`` (default v1's own ``DEFAULT_RELATED_CHUNK_NUMBER = 5``) is the
per-position chunk budget the gradient decreases from.

**VECTOR** (v1/lightrag/utils.py:4071-...): needs a query embedding to rank candidate chunks by
similarity, which this node's own base-wiring deps (``budget-entities``/``budget-relations`` only
— no ``embedder-query`` dependency) do not supply. This body exposes ``config["query_vector"]`` as
the hook a caller MAY set to exercise the real path (this plan's own unit tests do); the
**unpatched base wiring's own committed config carries no such key**, so a real run against it
degrades straight to WEIGHT without this body ever fabricating a vector to query with — an honest,
recorded architectural fact (03-06-SUMMARY.md), not a silently masked gap. Where a vector is
supplied, ranking is delegated to ``ctx.stores["vector"].query(...)``'s own top-k search, filtered
to this node's own candidate chunk-id set: the store this plan wires exposes no by-id vector
lookup (unlike v1's ``chunks_vdb.get_vectors_by_ids``), so a local cosine re-computation over
looked-up vectors is not this store's available surface.

Declares ``reads_kv`` and ``reads_vector`` **unconditionally** — never conditional on
``config["pick_method"]`` — per CONTRACT §19.9's fallback-reachability rule: the declaration
covers a path that COULD be taken, not only one a given config always takes, so a weight-only
config still carries ``reads_vector`` on the registered Part.
"""

from __future__ import annotations

from typing import Any

from databasise.parts.schema import NodeContext, Part

_NAME_AT_VERSION = "lightrag/chunk-selector-kg@0.1.0"
_GRAPH_FIELD_SEP = "<SEP>"  # v1/lightrag/constants.py:49, ported by copy (D-14 import boundary)
_DEFAULT_RELATED_CHUNK_NUMBER = 5  # v1/lightrag/constants.py:58
_DEFAULT_MIN_RELATED_CHUNKS = 1


def _entities_with_chunks(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """v1's own Steps 1-3: split each item's ``source_id`` on the field separator, drop a chunk id
    already claimed by an earlier item (earlier-position-wins dedup), then sort each item's own
    remaining chunks by global occurrence count, descending.
    """
    with_chunks: list[dict[str, Any]] = []
    for item in items:
        source_id = item.get("source_id")
        if not source_id:
            continue
        chunk_ids = [c for c in str(source_id).split(_GRAPH_FIELD_SEP) if c]
        if chunk_ids:
            with_chunks.append({"chunks": chunk_ids})

    occurrence: dict[str, int] = {}
    for entry in with_chunks:
        deduped: list[str] = []
        for chunk_id in entry["chunks"]:
            occurrence[chunk_id] = occurrence.get(chunk_id, 0) + 1
            if occurrence[chunk_id] == 1:
                deduped.append(chunk_id)
        entry["chunks"] = deduped

    for entry in with_chunks:
        entry["sorted_chunks"] = sorted(
            entry["chunks"], key=lambda cid: occurrence.get(cid, 0), reverse=True
        )
    return with_chunks


def _pick_by_weighted_polling(
    entities_with_chunks: list[dict[str, Any]],
    max_related_chunks: int,
    min_related_chunks: int = _DEFAULT_MIN_RELATED_CHUNKS,
) -> list[str]:
    """Ported by copy from v1's ``pick_by_weighted_polling`` (``v1/lightrag/utils.py:3991-4064``):
    linear-gradient weighted polling, allocating more chunks to earlier (higher-importance)
    entities/relations, then scanning for any leftover quota.
    """
    if not entities_with_chunks:
        return []
    n = len(entities_with_chunks)
    if n == 1:
        return entities_with_chunks[0]["sorted_chunks"][:max_related_chunks]

    expected_counts = []
    for i in range(n):
        ratio = i / (n - 1)
        expected = max_related_chunks - ratio * (max_related_chunks - min_related_chunks)
        expected_counts.append(int(round(expected)))

    selected: list[str] = []
    used_counts: list[int] = []
    total_remaining = 0
    for i, entry in enumerate(entities_with_chunks):
        chunks = entry["sorted_chunks"]
        actual = min(expected_counts[i], len(chunks))
        selected.extend(chunks[:actual])
        used_counts.append(actual)
        remaining = expected_counts[i] - actual
        if remaining > 0:
            total_remaining += remaining

    for _ in range(total_remaining):
        allocated = False
        for i, entry in enumerate(entities_with_chunks):
            chunks = entry["sorted_chunks"]
            if used_counts[i] < len(chunks):
                selected.append(chunks[used_counts[i]])
                used_counts[i] += 1
                allocated = True
                break
        if not allocated:
            break
    return selected


async def _pick_by_vector_similarity(
    ctx: NodeContext,
    all_chunk_ids: list[str],
    query_vector: Any,
    num_of_chunks: int,
) -> list[str]:
    """Query ``ctx.stores["vector"]`` with the caller-supplied ``config["query_vector"]``, keeping
    only ids already present in this node's own candidate set — the store's own top-k neighbours
    may include ids outside that set, which this node's own inputs never licensed it to select
    from. Adapted from v1's own ``pick_by_vector_similarity`` to this store's ``query(vector,
    top_k)`` surface (no by-id vector lookup here — see module docstring).
    """
    if not all_chunk_ids or num_of_chunks <= 0:
        return []
    store = ctx.stores["vector"]
    candidates = set(all_chunk_ids)
    results = await store.query(query_vector, top_k=max(num_of_chunks, len(all_chunk_ids)))
    picked = [r["id"] for r in results if r["id"] in candidates]
    return picked[:num_of_chunks]


async def _chunk_sel_kg_body(ctx: NodeContext) -> dict[str, Any]:
    config = ctx.config or {}
    entities = list(ctx.inputs.get("budget-entities", {}).get("items", []))
    relations = list(ctx.inputs.get("budget-relations", {}).get("items", []))
    entities_with_chunks = _entities_with_chunks(entities + relations)

    max_related_chunks = int(config.get("related_chunk_number", _DEFAULT_RELATED_CHUNK_NUMBER))
    pick_method = str(config.get("pick_method", "WEIGHT"))
    fallback_pick_method = str(config.get("fallback_pick_method", "WEIGHT"))

    selected_ids: list[str] = []
    used_method = pick_method

    if pick_method == "VECTOR":
        query_vector = config.get("query_vector")
        if query_vector is not None:
            all_chunk_ids = sorted({cid for entry in entities_with_chunks for cid in entry["chunks"]})
            num_of_chunks = int(max_related_chunks * len(entities_with_chunks) / 2) or max_related_chunks
            selected_ids = await _pick_by_vector_similarity(
                ctx, all_chunk_ids, query_vector, num_of_chunks
            )
        if not selected_ids:
            used_method = fallback_pick_method

    if used_method != "VECTOR":
        # Only WEIGHT is implemented as a real fallback target in this tracer — every published
        # base-wiring config's own fallback_pick_method is "WEIGHT" (see base.json).
        selected_ids = _pick_by_weighted_polling(entities_with_chunks, max_related_chunks)
        used_method = "WEIGHT"

    unique_ids = list(dict.fromkeys(selected_ids))
    kv_store = ctx.stores["kv"]
    items: list[dict[str, Any]] = []
    for chunk_id in unique_ids:
        record = await kv_store.get_by_id(chunk_id)
        if record is not None and "content" in record:
            item = dict(record)
            item["id"] = chunk_id
            item["chunk_id"] = chunk_id
            item["source_type"] = "kg"
            items.append(item)

    return {"items": items, "pick_method_used": used_method}


LIGHTRAG_CHUNK_SELECTOR_KG_PART = Part(
    name_at_version=_NAME_AT_VERSION,
    kind="retriever",
    structural_depth="stage",
    effects=["reads_kv", "reads_vector"],
    upstream_ref="v1/lightrag/operate.py",
    body=_chunk_sel_kg_body,
)
