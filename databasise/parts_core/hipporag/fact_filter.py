"""``hipporag/fact-filter`` (HippoRAG 2 base wiring position ``fact-filter``, PARTS.md ``## §H``) —
DSPyFilter over the top ``linking_top_k`` facts. Ported by search from
``hipporag/HippoRAG.py:462, 1659-1707``.

Takes ``fact-score``'s items, keeps the top ``config["linking_top_k"]`` by score, and asks the LLM
client to drop facts unrelated to the query, returning the surviving subset in input order.
Deliberately lenient JSON parsing on the LLM response (mirrors
``parts_core/lightrag/keywords.py``'s own ``_parse_keywords_payload`` graceful-degradation
precedent): an unparseable or malformed response keeps every top-``linking_top_k`` fact rather than
raising or silently discarding all of them — a filter step failing open, never closed, on this
sub-step's own read.

Emits ``{"items": [...], "guard_fired": bool}`` where ``guard_fired`` is true when zero facts
survive — the ``zero_surviving_facts_dpr_fallback`` guard ``docs/system-model/wirings/
hipporag-base.json`` declares under §19.8, evaluated at this node. In this plan the guard's true
branch has no consumer (this plan's own trimmed wiring has no ``dpr-fallback`` node) — plan 06-07
wires ``dpr-fallback`` to it. Reports token spend through the same ``TokenAccounting`` shape
``keywords.py`` reports.
"""

from __future__ import annotations

import json
import re
from typing import Any

from databasise.parts.schema import NodeContext, Part

_NAME_AT_VERSION = "hipporag/fact-filter@0.1.0"
_DEFAULT_LINKING_TOP_K = 5

_CODE_FENCE_PATTERN = re.compile(r"^\s*```(?:json|JSON)?\s*\n?(.*?)\n?\s*```\s*$", re.DOTALL)

_FACT_FILTER_PROMPT = """---Role---
You are filtering candidate facts retrieved for a query. Keep only the facts genuinely relevant to
answering the query; drop the rest.

---Instructions---
Output MUST be a single JSON object of exactly this shape and nothing else:
{{"keep_ids": ["<fact id>", ...]}}

---Query---
{query}

---Candidate Facts---
{facts}

---Output---
Output:"""


def _parse_keep_ids(text: str) -> list[str] | None:
    """A stdlib-only lenient parser, mirroring ``keywords.py``'s own precedent — returns ``None``
    (never raises) on any unparseable shape, the signal this body's caller treats as "keep every
    candidate" rather than "keep none".
    """
    fence_match = _CODE_FENCE_PATTERN.match(text)
    cleaned = fence_match.group(1) if fence_match else text
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    keep_ids = payload.get("keep_ids")
    if not isinstance(keep_ids, list):
        return None
    return [str(v) for v in keep_ids]


async def _fact_filter_body(ctx: NodeContext) -> dict[str, Any]:
    config = ctx.config or {}
    query = str(config.get("query", ""))
    linking_top_k = int(config.get("linking_top_k", _DEFAULT_LINKING_TOP_K))

    fact_score_output = ctx.inputs["fact-score"]
    candidates = list(fact_score_output.get("items", []))[:linking_top_k]

    if not candidates:
        return {"items": [], "guard_fired": True, "tokens": None}

    facts_text = "\n".join(f"- id={item['id']}: {item!r}" for item in candidates)
    prompt = _FACT_FILTER_PROMPT.format(query=query, facts=facts_text)
    client = ctx.clients["llm"]
    result = await client.chat(
        [{"role": "user", "content": prompt}], response_format={"type": "json_object"}
    )

    keep_ids = _parse_keep_ids(result.text)
    if keep_ids is None:
        # Unparseable response: fail open, keep every top-linking_top_k candidate — never fail
        # closed by discarding all of them on a parse error alone.
        surviving = candidates
    else:
        keep_set = set(keep_ids)
        surviving = [item for item in candidates if str(item["id"]) in keep_set]

    return {
        "items": surviving,
        "guard_fired": len(surviving) == 0,
        "tokens": result.tokens,
        "resolved_model_identity": result.resolved_model_identity,
    }


HIPPORAG_FACT_FILTER_PART = Part(
    name_at_version=_NAME_AT_VERSION,
    kind="ranker-reranker",
    structural_depth="opaque",
    effects=["calls_llm"],
    upstream_ref="hipporag/src/hipporag/HippoRAG.py",
    body=_fact_filter_body,
)
