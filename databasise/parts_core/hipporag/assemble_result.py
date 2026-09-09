"""``hipporag/result-assembler`` (HippoRAG 2 base wiring position ``assemble-result``,
PARTS.md ``## §H``) — hydrates each ``ppr`` item's chunk text and assembles the final context.
Ported by search from ``hipporag/HippoRAG.py:501-507``.

Hydrates each ``ppr`` item's chunk text from ``ctx.stores["kv"]`` (this node's own ``reads_kv``
effect), keyed by the item's own ``id`` — the same graph vertex name / chunk id the fixture and
``ppr``'s own readback share. Orders by ``config["order_policy"]``'s declared value
(``"hipporag-doc-score-order"``) — which, at this position, IS ``ppr``'s own emitted order
(descending by PPR score); this node performs no independent re-sort, since re-sorting an already
score-ordered input would silently discard the very ordering ``order_policy`` names.

**Named limitation, per 06-01-PLAN.md's own instruction:** HippoRAG 2's base wiring has no
generator position among its thirteen (PARTS.md ``## §H``) — ``completion`` therefore carries
assembled context (the hydrated chunk texts, joined), never a generated answer. This is a content
difference at the envelope's ``answer`` field, not an envelope-field difference; plan 06-03 records
it against F-14.
"""

from __future__ import annotations

from typing import Any

from databasise.parts.schema import NodeContext, Part

_NAME_AT_VERSION = "hipporag/result-assembler@0.1.0"


async def _assemble_result_body(ctx: NodeContext) -> dict[str, Any]:
    ppr_output = ctx.inputs["ppr"]
    ppr_items = list(ppr_output.get("items", []))

    kv_store = ctx.stores["kv"]
    hydrated_items: list[dict[str, Any]] = []
    contents: list[str] = []
    for item in ppr_items:
        record = await kv_store.get_by_id(str(item["id"]))
        content = str((record or {}).get("content", ""))
        hydrated_items.append({**item, "content": content})
        if content:
            contents.append(content)

    return {"items": hydrated_items, "completion": "\n\n".join(contents)}


HIPPORAG_RESULT_ASSEMBLER_PART = Part(
    name_at_version=_NAME_AT_VERSION,
    kind="assembler",
    structural_depth="opaque",
    effects=["reads_kv"],
    upstream_ref="hipporag/src/hipporag/HippoRAG.py",
    body=_assemble_result_body,
)
