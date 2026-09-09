"""``hipporag/reset-vector-join`` (HippoRAG 2 base wiring position ``reset-vector-join``,
PARTS.md ``## §H``) — builds the two dense weight arrays ``ppr``'s personalized PageRank reset
vector is seeded from. Ported by search from ``hipporag/HippoRAG.py:1577-1578`` (building the two
arrays), ``:1591-1608`` (phrase/passage weight construction) and ``:1621-1638`` (summing them);
the dense array itself never crosses this node's own port, per §13.1's part-local-projection
cross-reference — only the already-summed ``reset_vector``/``vertex_names`` pair does.

**Phrase weights.** For each surviving fact ``fact-filter`` emits, this node reads that fact's own
chunk-association record from the KV store (``reads_kv`` — the ``{fact_id: chunk_ids}`` mapping
this plan's own conftest fixture seeds under ``hipporag-text-chunks``, a 06-01-PLAN.md design
decision for exercising the declared ``reads_kv`` effect meaningfully) and divides the fact's own
score by its own chunk count, adding the result onto every entity vertex the fact names.

**Passage weights.** This node performs its own dense passage retrieval — embeds
``ctx.config["query"]`` (``calls_embedding``) and reads §14.2's exhaustive ``score_all``
sub-capability over the ``hipporag-chunks`` vector namespace (``reads_vector``) — min-max
normalises the resulting scores, and multiplies by ``config["passage_node_weight"]``.

**The sum.** Disjoint-support and order-insensitive: entity-prefixed and chunk-prefixed vertex
refs resolve to disjoint indices in the same dense vertex-index space ``CozoGraphStore
.export_to_igraph`` produces (both sides are keyed by the graph's own vertex-name strings — this
node never renames them). ``config["arity"]`` — the two branches this node itself computes
(phrase, passage), not a count of upstream node deps — is checked exactly as
``join_roundrobin.py``'s own ``config["arity"]`` check-and-refuse rule: a computed branch count
disagreeing with a declared arity raises ``ValueError`` rather than merging what arrived. This
body does NOT copy ``join_roundrobin.py``'s round-robin interleave — the merge semantics here are
a vector sum, not a positional interleave.

**Verified finding, recorded per 06-01-PLAN.md's own instruction:** ``join_roundrobin.py`` already
runs today as a plain ``Part`` with ``kind="join"`` because ``runner/scheduler.py``'s ``_run_node``
calls ``dispatch(part, ctx)`` uniformly and branches on ``kind`` only inside
``derive_execution_mode``; no new scheduler dispatch is built by this plan for this node either.
"""

from __future__ import annotations

from typing import Any

from databasise.parts.schema import NodeContext, Part

_NAME_AT_VERSION = "hipporag/reset-vector-join@0.1.0"
_CHUNKS_NAMESPACE = "hipporag-chunks"
_DEFAULT_PASSAGE_NODE_WEIGHT = 1.0
_DEFAULT_ARITY = 2


def _min_max_normalise(scores: list[float]) -> list[float]:
    if not scores:
        return []
    lo, hi = min(scores), max(scores)
    span = hi - lo
    if span == 0:
        return [0.0 for _ in scores]
    return [(s - lo) / span for s in scores]


async def _reset_vector_join_body(ctx: NodeContext) -> dict[str, Any]:
    config = ctx.config or {}
    query = str(config.get("query", ""))
    arity = config.get("arity", _DEFAULT_ARITY)
    passage_node_weight = float(config.get("passage_node_weight", _DEFAULT_PASSAGE_NODE_WEIGHT))

    fact_filter_output = ctx.inputs["fact-filter"]
    surviving_facts = list(fact_filter_output.get("items", []))

    kv_store = ctx.stores["kv"]
    phrase_weights: dict[str, float] = {}
    for fact in surviving_facts:
        fact_id = str(fact["id"])
        score = float(fact.get("score", 0.0))
        association = await kv_store.get_by_id(f"fact:{fact_id}")
        chunk_ids = (association or {}).get("chunk_ids") or []
        chunk_count = max(len(chunk_ids), 1)
        weight = score / chunk_count
        entities = fact.get("entities") or []
        for vertex_name in entities:
            phrase_weights[vertex_name] = phrase_weights.get(vertex_name, 0.0) + weight

    embedding_client = ctx.clients["embedding"]
    embed_result = await embedding_client.embed([query])
    vector = embed_result.vectors[0]

    chunks_store = ctx.stores["vector"].select(_CHUNKS_NAMESPACE)
    passage_items = await chunks_store.score_all(vector)
    passage_ids = [item["id"] for item in passage_items]
    normalised = _min_max_normalise([item["score"] for item in passage_items])
    passage_weights: dict[str, float] = {
        doc_id: score * passage_node_weight for doc_id, score in zip(passage_ids, normalised, strict=True)
    }

    branches = [phrase_weights, passage_weights]
    if arity is not None and int(arity) != len(branches):
        raise ValueError(
            f"{ctx.node_id!r} declares arity {arity} but computed {len(branches)} branch(es) "
            "(phrase weights, passage weights) — a computed branch count disagreeing with a "
            "declared arity is a refusal, never a best-effort merge"
        )

    reset_vector_map: dict[str, float] = {}
    for branch in branches:
        for vertex_name, weight in branch.items():
            reset_vector_map[vertex_name] = reset_vector_map.get(vertex_name, 0.0) + weight

    vertex_names = sorted(reset_vector_map.keys())
    reset_vector = [reset_vector_map[name] for name in vertex_names]

    return {
        "reset_vector": reset_vector,
        "vertex_names": vertex_names,
        "tokens": embed_result.tokens,
    }


HIPPORAG_RESET_VECTOR_JOIN_PART = Part(
    name_at_version=_NAME_AT_VERSION,
    kind="join",
    structural_depth="opaque",
    effects=["reads_vector", "calls_embedding", "reads_kv"],
    upstream_ref="hipporag/src/hipporag/HippoRAG.py",
    body=_reset_vector_join_body,
)
