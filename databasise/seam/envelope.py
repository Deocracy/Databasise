"""§18.2's closed response envelope (D-04, D-05).

**Checkpoint decision (04-CHECKPOINT-ANSWERS.md, `declare-upfront`).** The complete §18.2 field set
is declared here in wave 1, not grown incrementally. Fields whose element type belongs to a later
plan in this phase (the evidence-reference list's own shape, the token-accounting breakdown, the
seam-event list, the trace reference) are declared now with their final names and container types
and land empty/``None`` in this plan — 04-02 and 04-04 fill them. Every later plan in this phase
binds an element type into a field that already exists here; none may widen this envelope. See
04-01-SUMMARY.md's ``decisions_recorded_here`` section for the derivation.

**04-02: the evidence and token-accounting element types are now bound to their real models**
(``databasise.seam.evidence.EvidenceRef``, ``databasise.seam.tokens.TokenBreakdownEntry``) —
04-01's own placeholder classes of the same shape are retired in favour of them; no field on
``ResponseEnvelope`` itself was added, renamed, or removed. See those two modules for the field
shapes and FA-03's declared ``ChunkRef`` shortfall.

**04-04: ``SeamEvent.outcome`` is now a closed ``Literal`` (D-09/MACH-11).** The correlation rule
that populates ``seam_events`` — a ``mutates_store`` participant reached outside its wiring's own
``deps`` graph — lives in ``databasise.seam.engine`` (see that module's docstring for the rule's
exact statement and its FA-08 provenance: defined by this plan, not by CONTRACT, and narrower than
the general case, since no registered ``parts_core`` part exercises it today). An outcome string
outside the declared vocabulary is refused at construction rather than passed through — the same
closed-set discipline every other field in this module already carries.

**Nested strictness (Pitfall 7).** Pydantic v2 does not cascade ``frozen=True, extra="forbid"``
through nested model fields — each nested model must set its own ``model_config``, or inherit from
a shared strict base. Every model in this module, top-level and nested alike, inherits
``_StrictModel`` (``databasise.seam._base`` — see that module's own docstring for why the base
lives in its own leaf module rather than here, once ``evidence.py``/``tokens.py`` need to inherit
it too), so an unexpected key is rejected at every nesting depth, not only the outermost. The
structural guard alone would miss an internal id smuggled inside a nested value (D-05) — the
behavioral leak gate over a real serialized envelope is 04-04's job; this module only carries the
structural half.

**`resolved_model_identity` is excluded (FA-02, resolved by the checkpoint answer).** No
requirement in this phase asks for it, and including it would make "which model answered" visible
to a consumer without that having been decided under §18.3's invariance rule.

**07-01-PLAN.md: `PromotionResult`, §18.2's closed set for `Databasise.promote()`.** Exactly
`alias`, `version`, `record_kind`, `provenance`, `generation_ordinal` — never a wiring name, arm
name, node id, or instance hash. Placed beside `ResponseEnvelope`/`SeamEvent` because it is the
same closed-response-model discipline over `_StrictModel`, not because a promotion is a query.
"""

from __future__ import annotations

from typing import Literal

from databasise.seam._base import _StrictModel
from databasise.seam.evidence import EvidenceRef
from databasise.seam.tokens import TokenBreakdownEntry

# The closed outcome vocabulary for a MACH-11 seam event (04-04, Claude's Discretion per
# 04-CONTEXT.md — CONTRACT names no outcome vocabulary for this event). "completed": the
# out-of-deps mutation's own node finished dispatch normally. "halted": the node's own
# budget_state is "halted" (CONTRACT §9's budget-halt path) — the mutation is still real and still
# reported, never silently dropped because the run stopped early. "failed": reserved for a node
# whose dispatch itself raised before completing; no registered part reaches this branch today
# (FA-08 — nothing in parts_core exercises the out-of-deps case at all yet), but the vocabulary is
# declared now rather than widened later once one does.
SeamEventOutcome = Literal["completed", "halted", "failed"]


class SeamEvent(_StrictModel):
    """D-09/MACH-11's seam-level event: a ``mutates_store`` call outside a wiring's ``deps`` graph,
    carrying the component's ``name@version``, its spend, and its outcome — drawn from a closed
    vocabulary declared on this model, refusing construction with anything else. 04-04 wires the
    detection (``databasise.seam.engine``) and populates this list from a real run.
    """

    component: str
    spend: TokenBreakdownEntry | None = None
    outcome: SeamEventOutcome


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
    token_accounting: list[TokenBreakdownEntry] = []
    seam_events: list[SeamEvent] = []


class PromotionResult(_StrictModel):
    """07-01-PLAN.md's §18.2 closed set for ``Databasise.promote()``: exactly ``alias``,
    ``version``, ``record_kind``, ``provenance``, ``generation_ordinal`` — never a wiring name, arm
    name, node id, or instance hash.
    """

    alias: str
    version: str
    record_kind: str
    provenance: str
    generation_ordinal: int


__all__ = [
    "EvidenceRef",
    "PromotionResult",
    "ResponseEnvelope",
    "SeamEvent",
    "SeamEventOutcome",
    "TokenBreakdownEntry",
]
