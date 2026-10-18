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

**VECTOR** (v1/lightrag/utils.py:4071-4191): ranks each side's candidate chunks by similarity to
the query embedding, read from ``ctx.inputs["embedder-query"]["vector"]`` (11-04: base.json now
lists ``embedder-query`` in this node's deps; ``config["query_vector"]`` still overrides it for
tests). One ``score_all(vector)`` over this position's ``chunks`` namespace is filtered to the
candidate ids (the store's equivalent of v1's ``get_vectors_by_ids`` plus cosine) and takes the
top ``int(related_chunk_number * len(items) / 2)``. As in v1, a side whose vector pick yields
nothing (no vector, a count of zero, or a candidate with no stored vector) falls back to WEIGHT.
The WEIGHT branch never selects a vector namespace.

**Two sides** (v1 operate.py:4737-4790): entity chunks are selected first; relation candidates
then drop every chunk id the entity side selected; the two lists are merged round-robin
(entity, relation, entity, ...). ``pick_method_used`` is the method both sides used, or
``"MIXED"`` when they differ; ``pick_method_used_by_side`` names each side's method.

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
# This position's own vector namespace (v1's own per-kind naming, matching
# databasise/parity/import_index.py's _VECTOR_KINDS) — selected only by the VECTOR pick-method
# branch below; the WEIGHT fallback branch never selects or touches a vector namespace at all.
_CHUNKS_NAMESPACE = "chunks"


def _entities_with_chunks(
    items: list[dict[str, Any]], exclude: set[str] | None = None
) -> list[dict[str, Any]]:
    """v1's own Steps 1-3: split each item's ``source_id`` on the field separator, drop a chunk id
    already claimed by an earlier item (earlier-position-wins dedup), then sort each item's own
    remaining chunks by global occurrence count, descending. ``exclude`` (relation side only) is
    v1's entity-chunk dedup (operate.py:5592-5626): those ids are skipped before counting, and a
    relation left with no chunks is dropped. The entity side keeps emptied items, as v1 does.
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
            if exclude is not None and chunk_id in exclude:
                continue
            occurrence[chunk_id] = occurrence.get(chunk_id, 0) + 1
            if occurrence[chunk_id] == 1:
                deduped.append(chunk_id)
        entry["chunks"] = deduped
    if exclude is not None:
        with_chunks = [entry for entry in with_chunks if entry["chunks"]]

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


async def _hydrate(ctx: NodeContext, selected_ids: list[str]) -> list[dict[str, Any]]:
    kv_store = ctx.stores["kv"]
    items: list[dict[str, Any]] = []
    for chunk_id in dict.fromkeys(selected_ids):
        record = await kv_store.get_by_id(chunk_id)
        if record is not None and "content" in record:
            item = dict(record)
            item["id"] = chunk_id
            item["chunk_id"] = chunk_id
            item["source_type"] = "kg"
            items.append(item)
    return items


async def _chunk_sel_kg_body(ctx: NodeContext) -> dict[str, Any]:
    config = ctx.config or {}
    entities = list(ctx.inputs.get("budget-entities", {}).get("items", []))
    relations = list(ctx.inputs.get("budget-relations", {}).get("items", []))
    max_related_chunks = int(config.get("related_chunk_number", _DEFAULT_RELATED_CHUNK_NUMBER))
    pick_method = str(config.get("pick_method", "WEIGHT"))
    query_vector = config.get("query_vector")
    if query_vector is None:
        query_vector = (ctx.inputs.get("embedder-query") or {}).get("vector")
    scored: list[dict[str, Any]] | None = None  # one score_all per query, shared by both sides

    async def select_side(with_chunks: list[dict[str, Any]]) -> tuple[list[str], str | None]:
        """v1's per-side pick (operate.py:5349-5392, 5641-5684): VECTOR when configured and a
        query vector exists, else (or when it yields nothing) WEIGHT. Only WEIGHT is implemented
        as the fallback; every shipped config's fallback_pick_method is "WEIGHT"."""
        nonlocal scored
        if not with_chunks:
            return [], None
        if pick_method == "VECTOR" and query_vector is not None:
            num_of_chunks = int(max_related_chunks * len(with_chunks) / 2)
            candidates = {cid for entry in with_chunks for cid in entry["sorted_chunks"]}
            if num_of_chunks > 0 and candidates:
                if scored is None:
                    store = ctx.stores["vector"].select(_CHUNKS_NAMESPACE)
                    scored = await store.score_all(query_vector)
                picked = [r["id"] for r in scored if r["id"] in candidates]
                # v1 utils.py:4143-4152: a candidate with no stored vector voids the vector pick.
                if len(picked) == len(candidates):
                    return picked[:num_of_chunks], "VECTOR"
        return _pick_by_weighted_polling(with_chunks, max_related_chunks), "WEIGHT"

    entity_ids, entity_method = await select_side(_entities_with_chunks(entities))
    entity_items = await _hydrate(ctx, entity_ids)
    entity_chunk_ids = {item["chunk_id"] for item in entity_items}
    relation_ids, relation_method = await select_side(
        _entities_with_chunks(relations, exclude=entity_chunk_ids)
    )
    relation_items = await _hydrate(ctx, relation_ids)

    items: list[dict[str, Any]] = []
    for i in range(max(len(entity_items), len(relation_items))):
        items.extend(side[i] for side in (entity_items, relation_items) if i < len(side))

    methods = {m for m in (entity_method, relation_method) if m is not None}
    used_method = methods.pop() if len(methods) == 1 else ("MIXED" if methods else "WEIGHT")
    return {
        "items": items,
        "pick_method_used": used_method,
        "pick_method_used_by_side": {"entity": entity_method, "relation": relation_method},
    }


LIGHTRAG_CHUNK_SELECTOR_KG_PART = Part(
    name_at_version=_NAME_AT_VERSION,
    kind="retriever",
    structural_depth="stage",
    effects=["reads_kv", "reads_vector"],
    upstream_ref="v1/lightrag/operate.py",
    body=_chunk_sel_kg_body,
)
