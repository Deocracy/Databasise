"""``lightrag/keyword-extractor`` (base wiring position 1 of 18) — the query-side keyword
extraction call. Ported by search from ``v1/lightrag/operate.py``'s ``get_keywords_from_query`` /
``extract_keywords_only``, which format ``PROMPTS["keywords_extraction"]`` (``v1/lightrag/prompt.py``)
with the query text and call ``global_config["role_llm_funcs"]["keyword"]``, then parse a
``{"high_level_keywords": [...], "low_level_keywords": [...]}`` JSON payload out of the response.

The prompt text below is copied verbatim (never imported — D-14's import boundary) from
``v1/lightrag/prompt.py``'s ``PROMPTS["keywords_extraction"]``/``PROMPTS["keywords_extraction_examples"]``:
this node must send v1's own prompt, or a parity comparison against the ``local``/``global``/
``hybrid`` arms measures prompt drift instead of the decomposition itself.

D-12's pinned-replay mechanism (this node is the phase's one genuinely stochastic query-side
node): ``config["pinned"] = True`` plus ``config["pinned_output"] = {"high_level_keywords": [...],
"low_level_keywords": [...]}`` returns that recorded output verbatim and makes zero LLM calls — an
explicit config key, not inferred from the mere presence of a value, so a replay is visible in the
wiring's own ``config_hash``. The pinned path's ``TokenAccounting`` is the all-zero default with
``counted_by="pinned-replay"``, distinguishable in the run record from a live call's populated,
non-zero accounting — never looking alike (see this module's own docstring on why that matters:
an unmetered *real* call would be a refusal, but a pinned replay's zero spend is correct).
"""

from __future__ import annotations

import json
import re
from typing import Any

from databasise.parts.schema import NodeContext, Part
from databasise.parts_core.lightrag.prompts import PROMPTS
from databasise.runner.trace import TokenAccounting

_NAME_AT_VERSION = "lightrag/keyword-extractor@0.1.0"
_DEFAULT_LANGUAGE = "English"

# v1 fills {examples} with "\n".join(PROMPTS["keywords_extraction_examples"]) (operate.py:4175).
_KEYWORDS_EXTRACTION_EXAMPLE = "\n".join(PROMPTS["keywords_extraction_examples"])

# v1's PROMPTS["keywords_extraction"], kept with the other duplicated prompts (D-16 drift test).
_KEYWORDS_EXTRACTION_PROMPT = PROMPTS["keywords_extraction"]

_CODE_FENCE_PATTERN = re.compile(r"^\s*```(?:json|JSON)?\s*\n?(.*?)\n?\s*```\s*$", re.DOTALL)


def _normalize_keyword_list(raw_values: Any) -> list[str]:
    if not isinstance(raw_values, list):
        return []
    return [v.strip() for v in raw_values if isinstance(v, str) and v.strip()]


def _parse_keywords_payload(text: str) -> tuple[list[str], list[str]]:
    """A stdlib-only, deliberately lenient version of v1's own ``_parse_keywords_payload``
    (``json_repair`` is not one of ``databasise/pyproject.toml``'s approved runtime deps — this
    codebase's own reference parts never take on a new dependency purely for tolerant parsing).
    Strips a surrounding markdown code fence, then ``json.loads``; a response this codebase's own
    stub/real clients cannot parse degrades to two empty lists rather than raising, mirroring v1's
    own graceful degradation on an unparseable keyword-extraction response.
    """
    fence_match = _CODE_FENCE_PATTERN.match(text)
    cleaned = fence_match.group(1) if fence_match else text
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        return [], []
    if not isinstance(payload, dict):
        return [], []
    return (
        _normalize_keyword_list(payload.get("high_level_keywords")),
        _normalize_keyword_list(payload.get("low_level_keywords")),
    )


def _keyword_fields(query: str, hl_keywords: list[str], ll_keywords: list[str]) -> dict[str, Any]:
    """v1 kg_query's post-extraction step (operate.py:3850-3862): both lists empty and a query under
    50 characters forces ``ll = [query]``; then each list is ", "-joined into the string v1 embeds
    for the entity (ll) and relation (hl) vector searches. v1 returns ``fail_response`` for a long
    query with no keywords; here both lists stay empty and the downstream lookups skip the store.
    """
    if not hl_keywords and not ll_keywords and len(query) < 50:
        ll_keywords = [query]
    return {
        "high_level_keywords": hl_keywords,
        "low_level_keywords": ll_keywords,
        "hl_keywords_str": ", ".join(hl_keywords),
        "ll_keywords_str": ", ".join(ll_keywords),
    }


async def _keywords_body(ctx: NodeContext) -> dict[str, Any]:
    config = ctx.config or {}
    query = str(config.get("query", ""))

    if config.get("pinned"):
        pinned_output = config.get("pinned_output") or {}
        return {
            **_keyword_fields(
                query,
                _normalize_keyword_list(pinned_output.get("high_level_keywords")),
                _normalize_keyword_list(pinned_output.get("low_level_keywords")),
            ),
            # CR-01: embedder-query's own _query_text reads this node's "query" key when
            # `keywords` is one of its deps (hybrid/local/global) — never emitted before this
            # fix, so embedder-query silently embedded "" for those three arms. Emit the raw
            # query text here so it survives both the pinned-replay and live-call branches.
            "query": query,
            "tokens": TokenAccounting(counted_by="pinned-replay"),
        }

    language = str(config.get("language", _DEFAULT_LANGUAGE))
    prompt = _KEYWORDS_EXTRACTION_PROMPT.format(
        query=query, examples=_KEYWORDS_EXTRACTION_EXAMPLE, language=language
    )
    client = ctx.clients["llm"]
    result = await client.chat(
        [{"role": "user", "content": prompt}], response_format={"type": "json_object"}
    )
    hl_keywords, ll_keywords = _parse_keywords_payload(result.text)
    return {
        **_keyword_fields(query, hl_keywords, ll_keywords),
        "query": query,  # CR-01: same reasoning as the pinned-replay branch above.
        "tokens": result.tokens,
        "resolved_model_identity": result.resolved_model_identity,
    }


LIGHTRAG_KEYWORD_EXTRACTOR_PART = Part(
    name_at_version=_NAME_AT_VERSION,
    kind="rewriter",
    structural_depth="stage",
    effects=["calls_llm"],
    upstream_ref="v1/lightrag/operate.py",
    body=_keywords_body,
)
