"""``databasise.seam.evidence`` — API-05's machine-resolvable evidence references (D-07), 04-02's
Task 1/2 deliverable. Every answer the seam returns carries a list of these; a consumer resolves
one back through the seam (``Databasise.resolve_evidence``) to the same store record it was minted
from, never an inline copy of the record's own content.

**FA-03, the declared ``ChunkRef`` shortfall (04-RESEARCH.md Pitfall 4).** §4 specifies a
``ChunkRef`` as ``(corpus_id, recipe@version, ordinal, content_hash)``. At the point a retrieval
item reaches this module — the raw ``{"id": doc_id, "score": ..., **metadata}`` dict
``databasise/stores/vector.py``'s ``query()`` returns — none of those four members is separately
available: the vector store's own ``upsert`` never plumbed a corpus id, a recipe version, an
ordinal position, or a content hash alongside the caller-supplied ``doc_id``, and the wiring's own
recipe identity is not threaded to this position. **All four ``ChunkRef`` members are therefore
unpopulated in this plan** — this is a named, declared limitation, not an oversight. What genuinely
is available at this position, and what this module's ``EvidenceRef`` carries instead, is flatter:
the store's own record identifier (``ref``), the namespace it lives in, an ``ItemKind`` label
(CONTRACT.md §4's frozen union), the run's own score, and the evidence tier label (``tier``, §4's
T0-T3 ladder — left ``None`` in this plan; no evidence-tier computation exists yet, mirroring
``databasise.runner.trace``'s own ``TIER_PLACEHOLDER`` note that no scored evidence item flows
through a tracer node yet). Closing the ``ChunkRef`` gap requires plumbing recipe identity to the
retrieval position, out of this plan's scope.

**Machine-resolvable, never an inline copy (D-07, T-04-07's mitigation).** ``EvidenceRef`` carries
only the members needed to look the record back up through the same store handle it was minted
from — no instance hash, node position, or wiring identifier. Never populate it with the record's
own content as a convenience alongside the reference: a copy shipped beside its own reference gets
read instead of resolved, and silently diverges from the store's own record the moment the store
changes (the plan's own prohibition).
"""

from __future__ import annotations

from typing import Any

from databasise.seam._base import _StrictModel
from databasise.seam.refusals import SeamRefusalError

# The naive arm's own retrieval position (databasise/parts_core/lightrag/chunk_vector.py) selects
# this namespace off the multi-namespace vector store handle. Exposed here as the default so a
# mint/resolve pair driven from a naive-arm run agrees on it without either side hardcoding a
# second copy of the string.
CHUNKS_NAMESPACE = "chunks"

# CONTRACT.md §4's frozen ItemKind union member for a retrieved text chunk — never a bare ad hoc
# label, since the union is normative contract vocabulary, not a name this module is free to invent.
TEXT_CHUNK_KIND = "text_chunk"


class EvidenceRef(_StrictModel):
    """A machine-resolvable evidence reference (D-07). Carries only the store record identifier,
    the namespace it lives in, its ``ItemKind`` label, the run's own score, and the evidence tier
    label — no instance hash, node position, or wiring identifier (T-04-07's mitigation, proven
    over a real serialized envelope by 04-04's behavioral leak gate)."""

    ref: str
    namespace: str
    kind: str
    score: float | None = None
    tier: str | None = None


class MalformedEvidenceItemError(RuntimeError):
    """Raised when a raw retrieval item reaching :func:`mint_evidence_refs` carries no ``"id"``
    key — a differently-shaped item a future retrieval node could return — named explicitly rather
    than letting a bare ``KeyError`` propagate (house style: this module's own
    ``UnresolvableEvidenceReferenceError`` and ``databasise.stores.vector``'s own
    ``VectorNamespaceNotSelectedError``/``VectorStoreCorruptedError`` follow the identical pattern:
    a named exception carrying the specifics, never a bare ``KeyError``/``ValueError``).

    Not a :class:`~databasise.seam.refusals.SeamRefusalError`: the malformed shape is the wiring's
    own retrieval node output, not the consumer's own input — ``refusals.py``'s own module
    docstring is explicit that a seam refusal names only what the consumer supplied.
    """

    def __init__(self, *, namespace: str, index: int):
        self.namespace = namespace
        self.index = index
        super().__init__(
            f"retrieval item at index {index} in namespace {namespace!r} carries no 'id' key"
        )


class UnresolvableEvidenceReferenceError(SeamRefusalError):
    """Raised when an ``EvidenceRef`` names a record its own namespace's store does not currently
    hold (§4's deref-raising discipline, T-04-08's mitigation). Never returns ``None`` and never an
    empty result — either would be indistinguishable from evidence that was legitimately empty."""

    def __init__(self, ref: EvidenceRef):
        self.ref = ref
        super().__init__(
            f"evidence reference {ref.ref!r} in namespace {ref.namespace!r} does not resolve to "
            "any record the store currently holds"
        )


def mint_evidence_refs(
    items: list[dict[str, Any]], *, namespace: str = CHUNKS_NAMESPACE, kind: str = TEXT_CHUNK_KIND
) -> list[EvidenceRef]:
    """Mint one ``EvidenceRef`` per raw retrieval item, in the exact order ``items`` arrives.
    Envelope assembly must not re-sort (04-02 Task 2) — this function does not either; it is a pure
    element-wise map, order-preserving by construction.

    Raises :class:`MalformedEvidenceItemError` — WR-03, never a bare ``KeyError`` — for an item
    carrying no ``"id"`` key (a differently-shaped item a future retrieval node could return).
    """
    refs: list[EvidenceRef] = []
    for index, item in enumerate(items):
        item_id = item.get("id")
        if item_id is None:
            raise MalformedEvidenceItemError(namespace=namespace, index=index)
        refs.append(EvidenceRef(ref=str(item_id), namespace=namespace, kind=kind, score=item.get("score")))
    return refs


def resolve_evidence_ref(ref: EvidenceRef, vector_store: Any) -> dict[str, Any]:
    """Resolve ``ref`` back through the same store handle it was minted from —
    ``vector_store.select(ref.namespace).get_by_id(ref.ref)``, the same namespace-scoped Faiss
    handle ``databasise/stores/vector.py``'s ``query()`` reads from. Raises
    :class:`UnresolvableEvidenceReferenceError` — never returns ``None`` — for a reference the
    store does not currently hold.
    """
    namespace_store = vector_store.select(ref.namespace)
    record = namespace_store.get_by_id(ref.ref)
    if record is None:
        raise UnresolvableEvidenceReferenceError(ref)
    return record


__all__ = [
    "CHUNKS_NAMESPACE",
    "TEXT_CHUNK_KIND",
    "EvidenceRef",
    "MalformedEvidenceItemError",
    "UnresolvableEvidenceReferenceError",
    "mint_evidence_refs",
    "resolve_evidence_ref",
]
