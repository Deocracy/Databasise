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
from databasise.runner.trace import TokenAccounting

_NAME_AT_VERSION = "lightrag/keyword-extractor@0.1.0"
_DEFAULT_LANGUAGE = "English"

_KEYWORDS_EXTRACTION_EXAMPLE = """{
  "high_level_keywords": ["<high_level_keyword>"],
  "low_level_keywords": ["<low_level_keyword>"]
}
"""

# Copied verbatim from v1/lightrag/prompt.py's PROMPTS["keywords_extraction"].
_KEYWORDS_EXTRACTION_PROMPT = """---Role---
You are an expert keyword extractor, specializing in analyzing user queries for a Retrieval-Augmented Generation (RAG) system. Your purpose is to identify both high-level and low-level keywords in the user's query that will be used for effective document retrieval.

---Goal---
Given a user query, your task is to extract two distinct types of keywords:
1. **high_level_keywords**: for overarching concepts or themes, capturing user's core intent, the subject area, or the type of question being asked.
2. **low_level_keywords**: for specific entities or details, identifying the specific entities, proper nouns, technical jargon, product names, or concrete items.

---Instructions & Constraints---
1. **Output Format**: Your output MUST be a valid JSON object and nothing else. Do not include any explanatory text, markdown code fences (like ```json), comments, or any other text before or after the JSON.
2. **Exact JSON Shape**: The JSON object must contain exactly these two keys:
   - `"high_level_keywords"`: an array of strings
   - `"low_level_keywords"`: an array of strings
3. **JSON Boundary**: The first character of your response must be `{{` and the last character must be `}}`.
4. **Source of Truth**: All keywords must be explicitly derived only from the `User Query` in the `---Real Data---` section. Do not infer unsupported facts. Do not invent entities, products, organizations, dates, or technical terms that are not grounded in the query.
5. **Concise & Meaningful**: Keywords should be concise words or meaningful phrases. Prioritize multi-word phrases when they represent a single concept instead of splitting meaningful phrases into isolated words.
6. **Handle Edge Cases**: For queries that are too simple, vague, or nonsensical (e.g., "hello", "ok", "asdfghjkl"), return:
   `{{"high_level_keywords": [], "low_level_keywords": []}}`
7. **No Duplicates**: Do not repeat the same keyword within a list. Keep the lists short and high-signal.
8. **Language**: All extracted keywords MUST be in {language}. Proper nouns (e.g., personal names, place names, organization names) should be kept in their original language.
9. **Output Format Template Safety**: The `---Output Format Template---` section contains an output JSON template only. It is never source text. Do not extract, infer, or copy keywords from the template. Angle-bracket tokens such as `<high_level_keyword>` are placeholders; replace them only with keywords derived from the current `User Query` and never output the placeholders literally.

---Output Format Template---
The following content is an output JSON format template only. It is not source text and must never be used as keyword extraction content.

{examples}

---Real Data---
User Query: {query}

---Output---
Output:"""

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


async def _keywords_body(ctx: NodeContext) -> dict[str, Any]:
    config = ctx.config or {}
    query = str(config.get("query", ""))

    if config.get("pinned"):
        pinned_output = config.get("pinned_output") or {}
        return {
            "high_level_keywords": _normalize_keyword_list(pinned_output.get("high_level_keywords")),
            "low_level_keywords": _normalize_keyword_list(pinned_output.get("low_level_keywords")),
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
        "high_level_keywords": hl_keywords,
        "low_level_keywords": ll_keywords,
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
