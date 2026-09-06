"""§18.2's closed response envelope (D-04, D-05).

**Checkpoint decision (04-CHECKPOINT-ANSWERS.md, `declare-upfront`).** The complete §18.2 field set
is declared here in wave 1, not grown incrementally. Fields whose element type belongs to a later
plan in this phase (the evidence-reference list's own shape, the token-accounting breakdown, the
seam-event list, the trace reference) are declared now with their final names and container types
and land empty/``None`` in this plan — 04-02 and 04-04 fill them. Every later plan in this phase
binds an element type into a field that already exists here; none may widen this envelope. See
04-01-SUMMARY.md's ``decisions_recorded_here`` section for the derivation.

**Nested strictness (Pitfall 7).** Pydantic v2 does not cascade ``frozen=True, extra="forbid"``
through nested model fields — each nested model must set its own ``model_config``, or inherit from
a shared strict base. Every model in this module, top-level and nested alike, inherits
``_StrictModel`` below, so an unexpected key is rejected at every nesting depth, not only the
outermost. The structural guard alone would miss an internal id smuggled inside a nested value
(D-05) — the behavioral leak gate over a real serialized envelope is 04-04's job; this module only
carries the structural half.

**`resolved_model_identity` is excluded (FA-02, resolved by the checkpoint answer).** No
requirement in this phase asks for it, and including it would make "which model answered" visible
to a consumer without that having been decided under §18.3's invariance rule.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class _StrictModel(BaseModel):
    """The shared strict base every model in this module inherits (Pitfall 7) — frozen and
    extra-forbidding, so an unexpected key is rejected at every nesting depth."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class EvidenceRef(_StrictModel):
    """§18.2's evidence reference: a machine-resolvable, deref-raising ref (§4's ``ScoredItem``),
    never an inline copy of evidence content. The element type — what ``ref``/``kind`` actually
    carry for a real run — is 04-02's deliverable; this plan declares the shape and leaves the
    envelope's ``evidence`` list empty.
    """

    ref: str
    kind: str
    tier: str | None = None
    score: float | None = None


class TokenAccountingEntry(_StrictModel):
    """One breakdown entry in §18.2's ``counted_by``-tagged token accounting (D-08, Pitfall 5) —
    never a single summed scalar, since per-node ``counted_by`` values legitimately disagree
    within one run. 04-02 populates this list from a real run; this plan declares the shape and
    leaves the envelope's ``token_accounting`` list empty.
    """

    counted_by: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_read_tokens: int = 0
    call_count: int = 0


class SeamEvent(_StrictModel):
    """D-09/MACH-11's seam-level event: a ``mutates_store`` call outside a wiring's ``deps`` graph,
    carrying the component's ``name@version``, its spend, and its outcome. 04-04 wires the
    detection and populates this list from a real run; this plan declares the shape and leaves the
    envelope's ``seam_events`` list empty.
    """

    component: str
    spend: TokenAccountingEntry | None = None
    outcome: str


class ResponseEnvelope(_StrictModel):
    """The §18.2 closed response envelope. A consumer MUST NOT receive a field naming a wiring, a
    node id, an instance hash, or any other internal identity (D-05) — see
    ``databasise/tests/seam/test_envelope_schema.py`` for the structural proof, derived from
    ``databasise.runner.trace.RunRecord``/``NodeTrace``'s own identity field names rather than a
    hand-maintained literal list.
    """

    answer: str
    evidence: list[EvidenceRef] = []
    trace_token: str | None = None
    depth_label: str
    partial: bool
    degraded: bool
    stop_reason: str | None = None
    degradation_reason: str | None = None
    token_accounting: list[TokenAccountingEntry] = []
    seam_events: list[SeamEvent] = []


__all__ = ["ResponseEnvelope", "EvidenceRef", "TokenAccountingEntry", "SeamEvent"]
