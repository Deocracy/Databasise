"""``lightrag/assembler-kg-context`` — builds the answer context the way v1 does (D-16, LRAG-17).

``order_policy`` picks the v1 template: ``kg-template`` fills ``PROMPTS["kg_query_context"]`` with
the entity rows, relation rows, chunks and reference list (``operate.py`` ``_build_context_str``);
``naive-template`` fills ``PROMPTS["naive_query_context"]`` with chunks and references only
(``naive_query``). Any other value is refused by name. Entity and relation rows are the
``entities_context`` / ``relations_context`` that ``budget-entities`` / ``budget-relations`` emit
(both inputs optional, so the naive arm and the fixture wirings run without them). Chunks are JSON
lines ``{"reference_id", "content"[, "content_headings"]}`` whose reference ids come from
``utils.py`` ``generate_reference_list_from_chunks``: file paths numbered by frequency, then first
appearance. With no entity, relation or chunk the context is empty, so ``generate`` answers with
v1's ``fail_response`` and makes no call.

Chunks are capped at ``config["chunk_top_k"]`` (v1 default 20), then cut from the end, whole chunks
only, to v1's available budget: ``max_total_tokens`` (the engine always sets it, v1 default 30000)
minus the system template, the KG sections, the query and a 200-token buffer (``_build_context_str``).

``items`` is that truncated chunk list as ``{id, score}`` in context order, the evidence a KG arm
returns (``evidence_position`` points at this node).

No store or client access (no declared effects) — a pure transform over its inputs.
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

from databasise.parts.schema import NodeContext, Part
from databasise.parts_core.lightrag.prompts import PROMPTS

_NAME_AT_VERSION = "lightrag/assembler-kg-context@0.1.0"
_DEFAULT_ORDER_POLICY = "naive-template"
_TEMPLATE_BY_ORDER_POLICY = {"kg-template": "kg_query_context", "naive-template": "naive_query_context"}
# The system template each policy's context is sent in, for the token budget (generate.py).
_SYSTEM_TEMPLATE_BY_ORDER_POLICY = {
    "kg-template": ("rag_response", "context_data"),
    "naive-template": ("naive_rag_response", "content_data"),
}
_DEFAULT_MAX_TOTAL_TOKENS = 30000  # v1 constants.py DEFAULT_MAX_TOTAL_TOKENS
_DEFAULT_CHUNK_TOP_K = 20  # v1 constants.py DEFAULT_CHUNK_TOP_K
_BUFFER_TOKENS = 200  # v1: reserved for the reference list and a safety margin
_CHARS_PER_TOKEN = 4


def _tokens(text: str) -> int:
    # shortcut: len // 4 stands in for v1's tokenizer (no offline encoding); upgrade when an offline-safe tokenizer ships (D-16)
    return len(text) // _CHARS_PER_TOKEN


class UnknownOrderPolicyError(ValueError):
    """``config["order_policy"]`` names no v1 context template."""

    def __init__(self, order_policy: Any) -> None:
        self.order_policy = order_policy
        super().__init__(
            f"unknown assemble order_policy {order_policy!r}; expected one of "
            f"{sorted(_TEMPLATE_BY_ORDER_POLICY)}"
        )


def _json_lines(rows: list[dict[str, Any]]) -> str:
    return "\n".join(json.dumps(row, ensure_ascii=False) for row in rows)


def _chunk_rows_and_references(chunks: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str]:
    """v1 ``generate_reference_list_from_chunks`` plus ``_build_context_str``'s chunk rows."""
    counts = Counter(
        path for chunk in chunks if (path := chunk.get("file_path")) and path != "unknown_source"
    )
    # Counter keeps first-appearance order and sorted() is stable: frequency, then first seen.
    paths = sorted(counts, key=lambda path: -counts[path])
    reference_id = {path: str(i + 1) for i, path in enumerate(paths)}
    rows = []
    for chunk in chunks:
        row = {"reference_id": reference_id.get(chunk.get("file_path"), ""), "content": str(chunk.get("content", ""))}
        if chunk.get("content_headings"):
            row["content_headings"] = chunk["content_headings"]
        rows.append(row)
    return rows, "\n".join(f"[{reference_id[path]}] {path}" for path in paths)


def _cost_row(item: dict[str, Any], is_kg: bool) -> dict[str, Any]:
    """B-WR-03: the dict v1 costs per chunk, not the whole pipeline item. KG arms cost the merged
    chunk ``{content, file_path, chunk_id}`` (operate.py:4795-4829); naive costs
    ``_get_vector_context``'s dict (operate.py:4302-4308)."""
    content, file_path = item.get("content"), item.get("file_path", "unknown_source")
    chunk_id = item.get("chunk_id") or item.get("id")
    if is_kg:
        return {"content": content, "file_path": file_path, "chunk_id": chunk_id}
    return {
        "content": content,
        "created_at": item.get("created_at"),
        "file_path": file_path,
        "source_type": "vector",
        "chunk_id": chunk_id,
    }


def _budget_rows(output: dict[str, Any] | None, key: str) -> list[dict[str, Any]]:
    return list((output or {}).get(key) or [])


async def _assemble_body(ctx: NodeContext) -> dict[str, Any]:
    config = ctx.config or {}
    order_policy = config.get("order_policy", _DEFAULT_ORDER_POLICY)
    template_kind = _TEMPLATE_BY_ORDER_POLICY.get(order_policy)
    if template_kind is None:
        raise UnknownOrderPolicyError(order_policy)

    is_kg = order_policy == "kg-template"
    entities = _budget_rows(ctx.inputs.get("budget-entities"), "entities_context") if is_kg else []
    relations = _budget_rows(ctx.inputs.get("budget-relations"), "relations_context") if is_kg else []

    chunk_top_k = int(config.get("chunk_top_k", _DEFAULT_CHUNK_TOP_K))
    candidates = list(ctx.inputs["rerank"]["items"])[:chunk_top_k]

    # v1 _build_context_str / naive_query: available = max_total_tokens - (sys_prompt_tokens +
    # kg_context_tokens + query_tokens + 200); naive subtracts no context-template overhead.
    max_total_tokens = int(config.get("max_total_tokens", _DEFAULT_MAX_TOTAL_TOKENS))
    prompt_key, placeholder = _SYSTEM_TEMPLATE_BY_ORDER_POLICY[order_policy]
    sys_prompt = PROMPTS[prompt_key].format(
        response_type="Multiple Paragraphs", user_prompt="n/a", **{placeholder: ""}
    )
    kg_overhead = (
        PROMPTS["kg_query_context"].format(
            entities_str=_json_lines(entities),
            relations_str=_json_lines(relations),
            text_chunks_str="",
            reference_list_str="",
        )
        if is_kg
        else ""
    )
    available = max_total_tokens - (
        _tokens(sys_prompt) + _tokens(kg_overhead) + _tokens(str(config.get("query", ""))) + _BUFFER_TOKENS
    )
    chunks: list[dict[str, Any]] = []
    running = 0
    for item in candidates:  # v1 truncate_list_by_token_size: stop at the first chunk that overflows
        running += _tokens(json.dumps(_cost_row(item, is_kg), ensure_ascii=False, default=str))
        if running > available:
            break
        chunks.append(item)

    context = ""
    if entities or relations or chunks:
        chunk_rows, reference_list_str = _chunk_rows_and_references(chunks)
        sections = {"text_chunks_str": _json_lines(chunk_rows), "reference_list_str": reference_list_str}
        if is_kg:
            sections.update(entities_str=_json_lines(entities), relations_str=_json_lines(relations))
        context = PROMPTS[template_kind].format(**sections)

    return {
        "context": context,
        "order_policy": order_policy,
        "template_kind": template_kind,
        "chunk_count": len(chunks),
        # v1's truncated_chunks reference list: what the KG arms return as evidence (WIRE-02, D-02).
        "items": [{"id": c.get("chunk_id") or c.get("id"), "score": c.get("score")} for c in chunks],
    }


LIGHTRAG_ASSEMBLER_KG_CONTEXT_PART = Part(
    name_at_version=_NAME_AT_VERSION,
    kind="assembler",
    structural_depth="stage",
    effects=[],
    upstream_ref="v1/lightrag/operate.py",
    body=_assemble_body,
)
