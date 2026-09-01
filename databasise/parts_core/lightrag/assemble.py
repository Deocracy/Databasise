"""``lightrag/assembler-kg-context`` (naive arm position 5 of 7) — joins the ordered chunk items
into one context string, applying the arm's own ``order_policy`` and the chunk-token budget. §L.1
absorbs the chunk-token budget into this node rather than a separate one — ported by search from
``v1/lightrag/operate.py``'s ``naive_query``, which computes ``available_chunk_tokens`` (total
minus system-prompt/query/buffer overhead) and passes it to ``process_chunks_unified`` as
``chunk_token_limit``.

No store or client access (no declared effects) — this node is a pure transform over its inputs.
``config["max_total_tokens"]`` (character-budgeted here as a documented four-chars-per-token
heuristic, since this tracer has no tokenizer dependency of its own) truncates whole chunks only,
never a chunk's own text mid-string, mirroring ``process_chunks_unified``'s own whole-chunk
truncation.
"""

from __future__ import annotations

from typing import Any

from databasise.parts.schema import NodeContext, Part

_NAME_AT_VERSION = "lightrag/assembler-kg-context@0.1.0"
_DEFAULT_ORDER_POLICY = "naive-template"
# Deliberately coarse: no tokenizer dependency in this tracer, so a token budget is converted to
# a character budget at this fixed ratio. Wide enough headroom that it never truncates mid-chunk
# for this plan's snapshot-sized corpus; a real tokenizer-backed budget is out of this plan's scope.
_CHARS_PER_TOKEN = 4


async def _assemble_body(ctx: NodeContext) -> dict[str, Any]:
    config = ctx.config or {}
    items = list(ctx.inputs["rerank"]["items"])
    order_policy = config.get("order_policy", _DEFAULT_ORDER_POLICY)

    max_total_tokens = config.get("max_total_tokens")
    char_budget = int(max_total_tokens) * _CHARS_PER_TOKEN if max_total_tokens else None

    parts: list[str] = []
    total_chars = 0
    for item in items:
        content = str(item.get("content", ""))
        if char_budget is not None and parts and total_chars + len(content) > char_budget:
            break
        parts.append(content)
        total_chars += len(content)

    context = "\n\n".join(parts)
    return {"context": context, "order_policy": order_policy, "chunk_count": len(parts)}


LIGHTRAG_ASSEMBLER_KG_CONTEXT_PART = Part(
    name_at_version=_NAME_AT_VERSION,
    kind="assembler",
    structural_depth="stage",
    effects=[],
    upstream_ref="v1/lightrag/operate.py",
    body=_assemble_body,
)
