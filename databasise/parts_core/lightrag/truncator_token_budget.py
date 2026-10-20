"""``lightrag/truncator-token-budget`` (base wiring positions `budget-entities`/`budget-relations`,
two of eighteen positions) — truncates a joined entity or relation list to a token allowance,
first-come over the joined list, removing from the tail and never re-sorting. Ported by search from
``v1/lightrag/operate.py``'s ``_apply_token_truncation``, which calls ``utils.py``'s
``truncate_list_by_token_size`` (``utils.py:2596-2610``): walk the list in order, accumulate a
token cost per item, and stop at the first item whose accumulated cost would exceed the allowance —
returning everything before it, never a partial item. An allowance smaller than the first item's
own cost therefore returns an empty list on the very first accumulation check, before any item is
kept — this body reports that as a consumed count of zero, matching v1's own all-or-nothing
per-item behaviour rather than crediting a partial spend for an item that was never actually kept.

One body serves both ``budget-entities`` and ``budget-relations``; the differing default token
allowance (v1's own ``DEFAULT_MAX_ENTITY_TOKENS``/``DEFAULT_MAX_RELATION_TOKENS``,
``v1/lightrag/constants.py:54-55``) is selected by the node's own position id and is always
overridable via ``config["max_token_allowance"]`` — CONTRACT §19.4's rule that a numeric threshold
or cap is config, not a knob.

D-16 (LRAG-17): each item is first projected to v1's row — ``{entity, type, description}`` at
``budget-entities``, ``{entity1, entity2, description}`` at ``budget-relations`` (``operate.py``
``_apply_token_truncation``) — and the row's ``json.dumps`` is what is costed, at four chars per
token (no tokenizer dependency; see ``_token_cost``). The kept rows are emitted as
``entities_context`` / ``relations_context`` for ``assemble``, beside the kept original ``items``
that ``chunk-sel-kg`` reads.

Declares no effects (a non-effectful cut, no budget spent at this node): reaches no store and no
client. Truncating from the tail without re-sorting matters specifically because a re-sort
here would change ranking, and ranking is exactly what the retrieval-level parity comparison
measures — truncation must be a pure cut, never a re-rank in disguise.
"""

from __future__ import annotations

import json
from typing import Any

from databasise.parts.schema import NodeContext, Part

_NAME_AT_VERSION = "lightrag/truncator-token-budget@0.1.0"

_CHARS_PER_TOKEN = 4

# v1's own defaults (v1/lightrag/constants.py:54-55), selected by this node's own position id.
_DEFAULT_ALLOWANCE_BY_NODE_ID: dict[str, int] = {
    "budget-entities": 6000,
    "budget-relations": 8000,
}
_FALLBACK_DEFAULT_ALLOWANCE = 6000


def _entity_row(item: dict[str, Any]) -> dict[str, Any]:
    """v1 ``_apply_token_truncation``'s entity row, ``file_path``/``created_at`` already removed."""
    return {
        "entity": item.get("entity_name"),
        "type": item.get("entity_type", "UNKNOWN"),
        "description": item.get("description", "UNKNOWN"),
    }


def _relation_row(item: dict[str, Any]) -> dict[str, Any]:
    if "src_tgt" in item:
        entity1, entity2 = item["src_tgt"]
    else:
        entity1, entity2 = item.get("src_id"), item.get("tgt_id")
    return {"entity1": entity1, "entity2": entity2, "description": item.get("description", "UNKNOWN")}


def _token_cost(row: dict[str, Any]) -> int:
    # shortcut: len // 4 stands in for v1's tokenizer (no offline encoding); upgrade when an offline-safe tokenizer ships (D-16)
    return len(json.dumps(row, ensure_ascii=False, default=str)) // _CHARS_PER_TOKEN


async def _truncator_token_budget_body(ctx: NodeContext) -> dict[str, Any]:
    config = ctx.config or {}
    (upstream,) = ctx.inputs.values()  # a single dep in every arm: join-entities or join-relations
    items = list(upstream.get("items", []))

    default_allowance = _DEFAULT_ALLOWANCE_BY_NODE_ID.get(ctx.node_id, _FALLBACK_DEFAULT_ALLOWANCE)
    allowance = int(config.get("max_token_allowance", default_allowance))
    is_relations = ctx.node_id == "budget-relations"
    project = _relation_row if is_relations else _entity_row

    kept: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    consumed = 0
    running = 0
    for item in items:
        row = project(item)
        running += _token_cost(row)
        if running > allowance:
            break
        kept.append(item)
        rows.append(row)
        consumed = running

    context_key = "relations_context" if is_relations else "entities_context"
    return {"items": kept, context_key: rows, "consumed": consumed, "allowance": allowance}


LIGHTRAG_TRUNCATOR_TOKEN_BUDGET_PART = Part(
    name_at_version=_NAME_AT_VERSION,
    kind="grader-filter",
    structural_depth="stage",
    effects=[],
    upstream_ref="v1/lightrag/operate.py",
    body=_truncator_token_budget_body,
)
