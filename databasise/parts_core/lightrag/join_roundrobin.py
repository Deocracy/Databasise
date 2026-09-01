"""``lightrag/join-roundrobin`` (base wiring positions `join-entities`/`join-relations`/
`join-chunks`, three of eighteen positions) — one component, three positions, differing only by
config. Ported by search from ``v1/lightrag/operate.py``'s own round-robin merge blocks (entities:
"Round-robin merge entities"; relations: "Round-robin merge relations", both inside
``_get_kg_search`` / the mode-branch block just above them) plus ``_merge_all_chunks``'s own
chunk-union shape for ``join-chunks`` — first from one arm, then the other, deduplicating survivors
against each arriving item rather than deferring dedup to a later node.

Every fan-in in this family interleaves its arms by position with no score read anywhere in the
merge block, and CONTRACT §13.2 ¶4's D6 repair supplies the conformant declaration for exactly this
shape: a positional interleave with no score read declares its emitted score semantics as
``rank_position`` (docs/system-model/PARTS.md §L.2's "The fan-in ordering position", closed at
PARTS-04 D6) — this body stamps ``rank_position`` (the item's 0-based index in the merged,
deduplicated output) on every emitted item, never a read score.

Which of the two input lists is emitted first is read from ``config["arm_precedence"]`` when that
string names one of the node's own dep ids (``join-entities``'s base config,
``"entity-hydrate-expand-emitted-first"``, and ``join-chunks``'s,
``"chunk-sel-kg-emitted-first-then-chunk-vector"``, both name a dep directly); where it does not
(``join-relations``'s base config describes the dedup rule instead of naming an arm — the wiring's
own committed text, not this body's choice), the natural ``ctx.inputs`` order is used, which is
already deps-order (``runner/scheduler.py``'s ``_run_node`` builds ``inputs`` from ``parsed.deps``
in the wiring's own declared order) — the same "local first" order v1's own code hard-codes for
every one of the three merges alike (``operate.py``'s "First from local" / "Then from global"
comments recur at both the entity and relation merge blocks).

``config["arity"]`` — present only on ``join-chunks``'s base/hybrid config (``2``; the local/global
patches replace it with ``1`` for their own degenerate one-arm join; ``join-entities``/
``join-relations`` never declare it) — is checked when present: a supplied input count that
disagrees is a refusal (``ValueError``), never a best-effort merge over whatever arrived, per this
codebase's own house style (a silently short merge here reads downstream as a genuine retrieval
difference, not a decomposition artefact).

CONTRACT §4's fan-in provenance rule, repaired at D9: a fan-in must either pass an item through
unchanged or emit it as authored evidence carrying ``derived_from`` naming what it was computed
from; discarding a contributing item's origin (a dedup collapse, the case ``join-relations``'s own
config names) is authoring, not pass-through. Where a duplicate collapses into a kept item, this
body unions the discarded item's own ``derived_from`` into the survivor's — never drops the second
contributor's origin silently, and never credits the survivor to only whichever arm outer-list
order happened to favour (CONTRACT §4's D9 example is this exact case, named there by name).

Which field the merged output draws from each input dict is a fixed lookup keyed by this node's
own position id, not free-text config: ``entity-hydrate-expand``/``relation-hydrate-expand`` (this
join family's only two upstream producers) both emit ``{entities, relations, missing_seeds}``
(03-05-PLAN.md's own crossover shape — each hydrate-expand node emits both evidence kinds), so
``join-entities`` and ``join-relations`` need to know which of the two same-shaped dicts' keys to
read even though the two positions share every other config field; ``join-chunks``'s two producers
(``chunk-sel-kg``, ``chunk-vector``) both emit ``{items}`` instead. The three field names are the
node's own socket identity, exactly as fixed as the position itself — declaring them via
``config["merge_field"]`` was considered and rejected: the published base wiring (03-04-PLAN.md's
own committed content, read-only here) declares no such key, and inventing one would mean this
plan's own test config no longer matches the wiring it claims to conform to.

Reaches no store and no client; declares no effects — a pure transform over its own inputs.
"""

from __future__ import annotations

from typing import Any

from databasise.parts.schema import NodeContext, Part

_NAME_AT_VERSION = "lightrag/join-roundrobin@0.1.0"

# This component serves exactly these three published base-wiring positions
# (databasise/wirings/lightrag/base.json) — the field each position's merged output draws from
# each same-shaped input dict, fixed by the position's own identity (see module docstring).
_MERGE_FIELD_BY_NODE_ID: dict[str, str] = {
    "join-entities": "entities",
    "join-relations": "relations",
    "join-chunks": "items",
}


def _merge_field(node_id: str) -> str:
    try:
        return _MERGE_FIELD_BY_NODE_ID[node_id]
    except KeyError:
        raise ValueError(
            f"lightrag/join-roundrobin has no known merge field for node id {node_id!r}; "
            f"this component only serves {sorted(_MERGE_FIELD_BY_NODE_ID)}"
        ) from None


def _ordered_input_names(config: dict[str, Any], input_names: list[str]) -> list[str]:
    """``config["arm_precedence"]`` names the first-emitted input where it mentions one of the
    node's own dep ids by name; otherwise ``input_names``' own order governs (already deps-order —
    see module docstring).
    """
    precedence_text = str(config.get("arm_precedence", ""))
    mentioned = [name for name in input_names if name in precedence_text]
    mentioned.sort(key=precedence_text.index)
    remainder = [name for name in input_names if name not in mentioned]
    return mentioned + remainder


def _relation_key(item: dict[str, Any]) -> tuple[str, str]:
    """v1's own dual-shape dedup key (``operate.py``'s round-robin relation merge): a hydrated
    relation's endpoints live under ``src_tgt`` (entity-hydrate-expand's edge-expansion shape) or
    ``src_id``/``tgt_id`` (relation-hydrate-expand's own hydrated-seed shape) — either way, order
    the pair so ``A-B`` and ``B-A`` collapse to the same key (the "order-insensitive" rule
    ``join-relations``'s own base config names).
    """
    pair = item.get("src_tgt")
    if pair is None:
        pair = (item.get("src_id"), item.get("tgt_id"))
    return tuple(sorted(pair))


def _item_key(field: str, item: dict[str, Any]) -> Any:
    if field == "entities":
        return item.get("entity_name")
    if field == "relations":
        return _relation_key(item)
    return None  # join-chunks: no dedup — v1's own chunk union never collapses by id at this node


async def _join_roundrobin_body(ctx: NodeContext) -> dict[str, Any]:
    config = ctx.config or {}
    input_names = list(ctx.inputs.keys())

    arity = config.get("arity")
    if arity is not None and int(arity) != len(input_names):
        raise ValueError(
            f"{ctx.node_id!r} declares arity {arity} but received {len(input_names)} input(s) "
            f"({sorted(input_names)}) — a supplied input count disagreeing with a declared arity "
            "is a refusal, never a best-effort merge over whatever arrived"
        )

    field = _merge_field(ctx.node_id)
    ordered_names = _ordered_input_names(config, input_names)
    lists = [list(ctx.inputs[name].get(field, [])) for name in ordered_names]

    merged: list[dict[str, Any]] = []
    index_by_key: dict[Any, int] = {}
    max_len = max((len(lst) for lst in lists), default=0)
    for position in range(max_len):
        for lst in lists:
            if position >= len(lst):
                continue
            item = dict(lst[position])
            key = _item_key(field, item)
            if key is not None and key in index_by_key:
                # Dedup collapse: CONTRACT §4 D9 — the discarded contributor's own origin is
                # unioned into the survivor's derived_from, never silently dropped.
                survivor = merged[index_by_key[key]]
                survivor_from = list(survivor.get("derived_from") or [])
                discarded_from = list(item.get("derived_from") or [])
                survivor["derived_from"] = survivor_from + [
                    origin for origin in discarded_from if origin not in survivor_from
                ]
                continue
            if key is not None:
                index_by_key[key] = len(merged)
            merged.append(item)

    for rank_position, item in enumerate(merged):
        item["rank_position"] = rank_position

    return {"items": merged}


LIGHTRAG_JOIN_ROUNDROBIN_PART = Part(
    name_at_version=_NAME_AT_VERSION,
    kind="join",
    structural_depth="stage",
    effects=[],
    upstream_ref="v1/lightrag/operate.py",
    body=_join_roundrobin_body,
)
