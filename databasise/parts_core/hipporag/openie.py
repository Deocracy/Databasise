"""``hipporag/openie-extractor`` (HippoRAG 2 base wiring position ``openie``, PARTS.md ``## §H``)
— the two-call NER-then-triple-extraction index-side position. Ported by search from
``hipporag/HippoRAG.py:299``: one fused two-call operation with no external branch — the two LLM
calls (named-entity recognition, then triple extraction over those entities) are internals of this
one node position, never two positions. That fusion is exactly what ``## §H`` records; splitting it
into two nodes would change the node count this phase's MODAL-04 requirement pins.

Both prompts are carried inside this component as module-level constants, ``_NER_PROMPT`` and
``_TRIPLE_PROMPT`` — exactly the disposition ``PARTS.md ## §P``'s HippoRAG row states for the
OpenIE extraction prompts ("carried inside the component"). They are this plan's own prompt text
(HippoRAG 2's paper, ``reference/hipporag2-2502.14802.pdf``, describes the NER-then-triples shape;
the exact upstream DSPy signatures are not reproduced verbatim here — see ``upstream_ref``).

Mirrors ``parts_core/lightrag/keywords.py``'s own ``ctx.clients["llm"].chat(...)`` call shape and
tolerant, code-fence-stripping JSON parsing: a chunk whose triple-extraction response is malformed
degrades to zero findings for that chunk alone, never an aborted run for its sibling chunks — the
same graceful-degradation precedent ``keywords.py``/``fact_filter.py`` already establish.

Token accounting: this node makes up to two ``chat`` calls per input chunk, so its own emitted
``tokens`` is the sum of every call's own ``TokenAccounting`` (never a bare zero for a node that
made calls). If any individual call reports the ``unbudgetable`` sentinel (§8/§9 — the client
exposed no usage for that call), the summed total also reports ``unbudgetable`` rather than
silently treating the unexposed call as a real zero.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from databasise.parts.schema import NodeContext, Part
from databasise.runner.trace import TokenAccounting

_NAME_AT_VERSION = "hipporag/openie-extractor@0.1.0"
_UNBUDGETABLE_SENTINEL = "unbudgetable"

_CODE_FENCE_PATTERN = re.compile(r"^\s*```(?:json|JSON)?\s*\n?(.*?)\n?\s*```\s*$", re.DOTALL)

_NER_PROMPT = """---Role---
You are extracting named entities mentioned in a passage of text.

---Instructions---
Output MUST be a single JSON object of exactly this shape and nothing else:
{{"entities": ["<entity name>", ...]}}

---Passage---
{text}

---Output---
Output:"""

_TRIPLE_PROMPT = """---Role---
You are extracting (subject, predicate, object) triples from a passage of text, using the named
entities already recognised in that passage as anchors for each triple's subject and object.

---Instructions---
Output MUST be a single JSON object of exactly this shape and nothing else:
{{"triples": [["<subject>", "<predicate>", "<object>"], ...]}}

---Recognised Entities---
{entities}

---Passage---
{text}

---Output---
Output:"""


def _lenient_json(text: str) -> Any:
    """Strip a surrounding markdown code fence, then ``json.loads``; any unparseable shape
    returns ``None`` rather than raising, mirroring ``keywords.py``'s own graceful degradation."""
    fence_match = _CODE_FENCE_PATTERN.match(text)
    cleaned = fence_match.group(1) if fence_match else text
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


def _parse_entities(text: str) -> list[str]:
    payload = _lenient_json(text)
    if not isinstance(payload, dict):
        return []
    raw = payload.get("entities")
    if not isinstance(raw, list):
        return []
    return [v.strip() for v in raw if isinstance(v, str) and v.strip()]


def _parse_triples(text: str) -> list[tuple[str, str, str]]:
    payload = _lenient_json(text)
    if not isinstance(payload, dict):
        return []
    raw = payload.get("triples")
    if not isinstance(raw, list):
        return []
    triples: list[tuple[str, str, str]] = []
    for item in raw:
        if (
            isinstance(item, (list, tuple))
            and len(item) == 3
            and all(isinstance(v, str) and v.strip() for v in item)
        ):
            triples.append((item[0].strip(), item[1].strip(), item[2].strip()))
    return triples


def _fact_id(subject: str, predicate: str, obj: str) -> str:
    """A SHA-256 over the canonicalised (lower-cased, pipe-joined) triple, so the same triple
    surfacing from two different chunks resolves to one fact id."""
    canonical = "|".join(v.strip().lower() for v in (subject, predicate, obj))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _sum_token_accountings(accountings: list[TokenAccounting]) -> TokenAccounting:
    if not accountings:
        return TokenAccounting()
    if any(acc.counted_by == _UNBUDGETABLE_SENTINEL for acc in accountings):
        counted_by = _UNBUDGETABLE_SENTINEL
    else:
        counted_by = accountings[0].counted_by
    return TokenAccounting(
        prompt_tokens=sum(acc.prompt_tokens for acc in accountings),
        completion_tokens=sum(acc.completion_tokens for acc in accountings),
        cached_read_tokens=sum(acc.cached_read_tokens for acc in accountings),
        call_count=sum(acc.call_count for acc in accountings),
        counted_by=counted_by,
    )


async def _openie_body(ctx: NodeContext) -> dict[str, Any]:
    chunk_embed_output = ctx.inputs["chunk-embed"]
    chunks = list(chunk_embed_output.get("chunks", []))
    if not chunks:
        return {"findings": []}

    client = ctx.clients["llm"]
    findings: list[dict[str, Any]] = []
    call_accountings: list[TokenAccounting] = []
    resolved_model_identity: str | None = None

    for chunk in chunks:
        chunk_id = chunk["chunk_id"]
        text = str(chunk.get("text", ""))

        ner_result = await client.chat(
            [{"role": "user", "content": _NER_PROMPT.format(text=text)}],
            response_format={"type": "json_object"},
        )
        call_accountings.append(ner_result.tokens)
        resolved_model_identity = ner_result.resolved_model_identity
        entities = _parse_entities(ner_result.text)

        triple_result = await client.chat(
            [
                {
                    "role": "user",
                    "content": _TRIPLE_PROMPT.format(entities=json.dumps(entities), text=text),
                }
            ],
            response_format={"type": "json_object"},
        )
        call_accountings.append(triple_result.tokens)
        resolved_model_identity = triple_result.resolved_model_identity

        for subject, predicate, obj in _parse_triples(triple_result.text):
            findings.append(
                {
                    "subject": subject,
                    "predicate": predicate,
                    "object": obj,
                    "chunk_id": chunk_id,
                    "fact_id": _fact_id(subject, predicate, obj),
                }
            )

    return {
        "findings": findings,
        "tokens": _sum_token_accountings(call_accountings),
        "resolved_model_identity": resolved_model_identity,
    }


HIPPORAG_OPENIE_EXTRACTOR_PART = Part(
    name_at_version=_NAME_AT_VERSION,
    kind="extractor",
    structural_depth="opaque",
    effects=["calls_llm"],
    upstream_ref="hipporag/src/hipporag/HippoRAG.py",
    body=_openie_body,
)
