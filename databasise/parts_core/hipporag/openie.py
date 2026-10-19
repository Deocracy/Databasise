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
tolerant, code-fence-stripping JSON parsing, but strict about failure (Phase 12 D-08, HIPP-10): a
chunk whose NER or triple call raises, or whose response is not a JSON object with the expected
list, is a failed chunk. Every chunk is still attempted, then the whole ingest is refused with
``ExtractionFailedError`` carrying the failed-chunk count and one closed reason code per failed
chunk (v1 likewise fails the document on its first chunk error). A valid response with zero
triples is not a failure. Chunks run with bounded concurrency: the scheduler's
``config.max_concurrency`` semaphore, held across one chunk's NER-then-triples pair.

The input chunk records pass through unchanged as the ``chunks`` output key so ``passage-edges``
can give every chunk a vertex, including a chunk OpenIE found no triple in (HIPP-06, D-02).

Token accounting: this node makes up to two ``chat`` calls per input chunk, so its own emitted
``tokens`` is the sum of every call's own ``TokenAccounting`` (never a bare zero for a node that
made calls), computed by the shared ``runner.trace.sum_token_accountings``. If any individual call
reports the ``unbudgetable`` sentinel (§8/§9 — the client exposed no usage for that call), or the
calls report different ``counted_by`` labels, the summed total reports ``unbudgetable`` rather than
treating the unexposed call as a real zero or two counters as one (HIPP-19, D-07).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
from typing import Any

from databasise.parts.schema import NodeContext, Part
from databasise.runner.trace import TokenAccounting, sum_token_accountings

_NAME_AT_VERSION = "hipporag/openie-extractor@0.1.0"

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


class ExtractionFailedError(RuntimeError):
    """One or more chunks failed extraction (D-08). ``failure_reasons`` holds one closed code per
    failed chunk (``unparseable_response`` or ``llm_call_failed:<exception class name>``), never
    provider text, so the message and attributes are safe to surface through a refusal."""

    def __init__(self, *, failed_chunks: int, failure_reasons: list[str]) -> None:
        self.failed_chunks = failed_chunks
        self.failure_reasons = failure_reasons
        super().__init__(f"OpenIE extraction failed for {failed_chunks} chunk(s)")


def _parse_entities(text: str) -> list[str] | None:
    """``None`` when the response is not a JSON object with an ``entities`` list."""
    payload = _lenient_json(text)
    if not isinstance(payload, dict):
        return None
    raw = payload.get("entities")
    if not isinstance(raw, list):
        return None
    if not all(isinstance(v, str) for v in raw):  # A-WR-03: a bad item is a refusal, not a thinner graph
        return None
    return [v.strip() for v in raw if v.strip()]


def _parse_triples(text: str) -> list[tuple[str, str, str]] | None:
    """``None`` when the response is not a JSON object with a ``triples`` list, or when any item is
    not a list of three non-empty strings. ``[]`` is the only valid zero-triple response."""
    payload = _lenient_json(text)
    if not isinstance(payload, dict):
        return None
    raw = payload.get("triples")
    if not isinstance(raw, list):
        return None
    triples: list[tuple[str, str, str]] = []
    for item in raw:
        if not (
            isinstance(item, (list, tuple))
            and len(item) == 3
            and all(isinstance(v, str) and v.strip() for v in item)
        ):
            return None
        triples.append((item[0].strip(), item[1].strip(), item[2].strip()))
    return triples


def _fact_id(subject: str, predicate: str, obj: str) -> str:
    """A SHA-256 over the canonicalised (lower-cased, pipe-joined) triple, so the same triple
    surfacing from two different chunks resolves to one fact id."""
    canonical = "|".join(v.strip().lower() for v in (subject, predicate, obj))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def _extract_chunk(
    client: Any, chunk: dict[str, Any], semaphore: asyncio.Semaphore
) -> tuple[list[dict[str, Any]], list[TokenAccounting], str | None, str | None]:
    """NER then triples for one chunk. Returns (findings, call accountings, resolved model identity,
    failure reason); a failure reason means the chunk failed and its findings are discarded."""
    chunk_id = chunk["chunk_id"]
    text = str(chunk.get("text", ""))
    accountings: list[TokenAccounting] = []
    identity: str | None = None
    async with semaphore:
        try:
            ner_result = await client.chat(
                [{"role": "user", "content": _NER_PROMPT.format(text=text)}],
                response_format={"type": "json_object"},
            )
            accountings.append(ner_result.tokens)
            identity = ner_result.resolved_model_identity
            entities = _parse_entities(ner_result.text)
            if entities is None:
                return [], accountings, identity, "unparseable_response"

            triple_result = await client.chat(
                [
                    {
                        "role": "user",
                        "content": _TRIPLE_PROMPT.format(entities=json.dumps(entities), text=text),
                    }
                ],
                response_format={"type": "json_object"},
            )
            accountings.append(triple_result.tokens)
            identity = triple_result.resolved_model_identity
            triples = _parse_triples(triple_result.text)
        except Exception as exc:  # noqa: BLE001 - recorded as a closed code; BaseException still propagates
            return [], accountings, identity, f"llm_call_failed:{type(exc).__name__}"
    if triples is None:
        return [], accountings, identity, "unparseable_response"
    findings = [
        {
            "subject": subject,
            "predicate": predicate,
            "object": obj,
            "chunk_id": chunk_id,
            "fact_id": _fact_id(subject, predicate, obj),
        }
        for subject, predicate, obj in triples
    ]
    return findings, accountings, identity, None


async def _openie_body(ctx: NodeContext) -> dict[str, Any]:
    chunk_embed_output = ctx.inputs["chunk-embed"]
    chunks = list(chunk_embed_output.get("chunks", []))
    if not chunks:
        return {"findings": [], "chunks": []}

    client = ctx.clients["llm"]
    # The scheduler validates max_concurrency and hands the body its per-node semaphore; a
    # hand-built context carries none, so build one from the same config key.
    semaphore = getattr(ctx, "_semaphore", None) or asyncio.Semaphore(
        int((ctx.config or {}).get("max_concurrency", 1))
    )
    results = await asyncio.gather(*(_extract_chunk(client, chunk, semaphore) for chunk in chunks))

    reasons = [reason for _, _, _, reason in results if reason is not None]
    if reasons:
        raise ExtractionFailedError(failed_chunks=len(reasons), failure_reasons=reasons)

    findings = [finding for chunk_findings, _, _, _ in results for finding in chunk_findings]
    call_accountings = [acc for _, accountings, _, _ in results for acc in accountings]
    resolved_model_identity = next(
        (identity for _, _, identity, _ in reversed(results) if identity is not None), None
    )
    return {
        "findings": findings,
        "chunks": chunks,
        "tokens": sum_token_accountings(call_accountings),
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
