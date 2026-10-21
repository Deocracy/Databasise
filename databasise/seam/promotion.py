"""Pure computation for the operator-asserted promotion path (MACH-07/API-09, 07-01-PLAN.md): the
verb ladder, the measurement-posture refusal, the machine-derived mutation class, and the semver
mint rule. No I/O, no engine import — every function here takes already-resolved data (a resolved
wiring dict, a trace record, a registry) and returns or raises, following ``selectors.py``'s own
module-constant-plus-pure-function shape (``_wiring_effects``/``_match_capability``).

**Trace-id -> single-arm resolution (D-04, 14-08-PLAN.md D-01).** A persisted
``RunRecord.to_dict()`` carries ``arm_id`` — the arm name — since Phase 13 D-03, and a wiring name
``wiring_for_name`` resolves is the arm (a partial record has no completed nodes to match, so it
needs this). A record persisted before that change carries the literal ``"seam"``, and
``wiring_instance_hash`` differs per *query* in an older trace, so the fallback is the one signal
that is query-invariant and unique per arm there: the **dispatched node id set**, each
``RunRecord.nodes`` entry's own ``node_id``, which ``databasise/tests/seam/test_trace_token.py``
already proves is exactly the resolved wiring's own node id set minus its recipe-only nodes (D-04,
11-10). :func:`resolve_single_arm` matches that set against every candidate wiring's own run-shape
node ids (``databasise.wirings.resolve.without_recipe_only_nodes`` over ``all_wirings()``, B-CR-01)
or its full node ids (a trace persisted before 11-10) — never a caller-supplied name (D-11).

**Mutation-class derivation compares component identity, not bare node-id sets (D-10).** The
node-id sets alone cannot express "the same node id now runs a different component" — an arm
patch's own ``replace`` operations can retarget a node's ``component`` without adding or removing
node ids. :func:`derive_mutation_class` therefore takes the two full resolved wiring dicts, not
bare id sets, so it can compare each shared node id's own ``component`` string.
"""

from __future__ import annotations

from typing import Any, Literal, get_args

from databasise.parts.registry import PartRegistry
from databasise.seam.refusals import (
    DisagreeingPromotionTraceIdsError,
    EmptyPromotionTraceIdsError,
    MeasurementPostureRefusalError,
    PartialRunEvidenceError,
    UncalibratedFloorRefusalError,
    UnknownTraceReferenceError,
)
from databasise.seam.selectors import _wiring_effects
from databasise.wirings.resolve import all_wirings, without_recipe_only_nodes, wiring_for_name

# D-08: both values accepted — CONTRACT §7 makes change_origin orthogonal to promotion_provenance,
# and the frozen contract is not re-litigated at the seam. machine_mutation is accepted even
# though no proposer exists in this milestone.
PROVENANCE_OPERATOR_ASSERTED = "operator_asserted"
CHANGE_ORIGINS = frozenset({"human_edit", "machine_mutation"})

# D-07: the three record kinds a ledger row can carry. Rollback/tombstone land in 07-02; declared
# here so every record-kind literal in this module lives in one place.
RECORD_KIND_PROMOTION = "promotion"
RECORD_KIND_ROLLBACK = "rollback"
RECORD_KIND_TOMBSTONE = "tombstone"

# D-09: CONTRACT §5's five-verb ladder plus the operator-asserted path this milestone actually
# builds. A value outside this set is a caller/programming error, not a modeled refusal.
PromotionVerb = Literal[
    "operator-asserted", "check", "preview", "run", "promote-next", "promote-now"
]
# 07-04-PLAN.md (D-09, closing 07-REVIEW.md CR-01): the runtime guard's accepted set, derived from
# PromotionVerb via typing.get_args rather than hand-restated — a seventh literal added above is
# then automatically covered here, never a second hand-maintained list that can drift out of sync.
PROMOTION_VERBS: frozenset[str] = frozenset(get_args(PromotionVerb))
_NOT_BUILT_VERBS: tuple[str, ...] = ("check", "preview", "run")
_GATE_VERBS: tuple[str, ...] = ("promote-next", "promote-now")

# D-10: RIG §CM.1's index-extraction moment. embedder-index is PARTS §L.1's one LightRAG
# index-recipe node; full-ingest is LightRAG's corpus-ingest.json position; the remaining seven
# are exactly the node ids in databasise/wirings/hipporag/corpus-ingest.json (confirmed against
# that file, not merely asserted).
_INDEX_RECIPE_NODE_IDS: frozenset[str] = frozenset(
    {
        "embedder-index",
        "full-ingest",
        "chunk-embed",
        "openie",
        "entity-fact-embed",
        "fact-edges",
        "passage-edges",
        "synonymy-edges",
        "graph-augment-persist",
    }
)

# D-10: RIG §CM.1's query-generation moment — the prompt-bearing nodes whose registered Part
# declares calls_llm and which are not in the index recipe. openie also declares calls_llm but is
# index-side and is classed there first (the index-recipe check runs before this one).
_ANSWER_LEVEL_NODE_IDS: frozenset[str] = frozenset({"generate", "keywords", "fact-filter"})

# D-10: the closed set derive_mutation_class can return. A Literal, not a bare frozenset, so a
# test can introspect it (typing.get_args) and assert _MEASUREMENT_POSTURE's own key set covers
# every class this function can produce — a later fourth class landing in the Literal without a
# matching posture entry is then a KeyError at the one _MEASUREMENT_POSTURE read site, not a
# silent fall-through.
MutationClass = Literal["index-side", "answer-level", "retrieval-side"]

# D-11: RIG §F3.2's default posture, verbatim — retrieval-side ON, answer-level and index-side
# OFF. Read at exactly one call site, inside this module (enforce_gate_verb_posture below), never
# passed in, never overridden, never reached through an environment variable, a config file, or a
# Databasise constructor argument. Flipping a class is a source edit, and
# 06-GATE-AMENDMENT.md/07-GATE-AMENDMENT.md bind that edit to running the A/A calibration first —
# a runtime flag here would make that record's residual-risk framing false.
_MEASUREMENT_POSTURE: dict[str, bool] = {
    "retrieval-side": True,
    "answer-level": False,
    "index-side": False,
}


def _dispatched_node_ids(resolved_trace_record: dict[str, Any]) -> frozenset[str]:
    """The node id set a persisted ``RunRecord.to_dict()`` actually dispatched — query-invariant,
    unlike ``wiring_instance_hash``. Only completed nodes count (D-13): a failed, cancelled or
    not-scheduled node never ran to completion. A node with no ``status`` (a record persisted
    before Phase 13) reads as completed."""
    return frozenset(
        node["node_id"]
        for node in resolved_trace_record.get("nodes", [])
        if node.get("status", "completed") == "completed"
    )


# B-WR-03: nodes a wiring gained after traces were already persisted. A HippoRAG query trace from
# before Phase 12 dispatched every base node but ``qa`` (D-19), and no pruning existed (D-16).
_NODES_ADDED_AFTER_LEGACY_TRACES: dict[str, frozenset[str]] = {"hipporag": frozenset({"qa"})}


def _arm_name_for_node_ids(node_ids: frozenset[str], *, trace_reference: str | None = None) -> str:
    """The one candidate in :func:`~databasise.wirings.resolve.all_wirings` whose own resolved
    node id set equals ``node_ids``. A trace that matches no candidate (for example one persisted
    against wirings that have since changed shape) raises
    :class:`~databasise.seam.refusals.UnknownTraceReferenceError`, a named 404 refusal, never an
    ``AssertionError`` the consumer sees as a 500.
    """
    for name, resolved in all_wirings():
        # B-CR-01: a query trace omits recipe-only nodes (D-04), so compare the run shape. The full
        # set still matches a trace persisted before 11-10; no full set equals another arm's run set.
        run_ids = frozenset(without_recipe_only_nodes(resolved).get("nodes", {}).keys())
        full_ids = frozenset(resolved.get("nodes", {}).keys())
        legacy_ids = full_ids - _NODES_ADDED_AFTER_LEGACY_TRACES.get(name, frozenset())
        if node_ids in (run_ids, full_ids, legacy_ids):
            return name
    raise UnknownTraceReferenceError(trace_reference or f"<run with nodes {sorted(node_ids)!r}>")


def _arm_name_for_record(record: dict[str, Any], trace_reference: str | None) -> str:
    """One record's arm: ``record["arm_id"]`` when ``wiring_for_name`` resolves it (Phase 13 D-03),
    else the node-set match for a record persisted before it. A *partial* record the node-set match
    cannot identify refuses as :class:`~databasise.seam.refusals.PartialRunEvidenceError` (D-01),
    not as a false unknown trace; a non-partial one keeps its 404.
    """
    arm_id = record.get("arm_id")
    if isinstance(arm_id, str) and wiring_for_name(arm_id) is not None:
        return arm_id
    try:
        return _arm_name_for_node_ids(_dispatched_node_ids(record), trace_reference=trace_reference)
    except UnknownTraceReferenceError:
        if record.get("partial"):
            raise PartialRunEvidenceError(trace_ids=[trace_reference] if trace_reference else []) from None
        raise


def refuse_partial_evidence(resolved_trace_records: list[dict[str, Any]], trace_ids: list[str]) -> None:
    """The one partial-evidence rule (14-08-PLAN.md, D-03): raises
    :class:`~databasise.seam.refusals.PartialRunEvidenceError` naming exactly the trace ids whose
    record has a truthy ``partial``. Keyed on ``partial`` and never ``degraded`` — a degraded run
    that is not partial took a declared fallback and completed (Phase 13 D-21, CONTRACT §19.8). A
    seeded record carries no ``partial`` key and reads as complete. Phase 16's CONN-09 preview calls
    this same function.
    """
    partial_ids = [
        trace_id
        for trace_id, record in zip(trace_ids, resolved_trace_records)
        if record.get("partial")
    ]
    if partial_ids:
        raise PartialRunEvidenceError(trace_ids=partial_ids)


def resolve_single_arm(
    resolved_trace_records: list[dict[str, Any]],
    *,
    alias: str,
    trace_ids: list[str],
) -> str:
    """The one arm name every resolved trace record agrees on (D-04). Raises
    :class:`~databasise.seam.refusals.EmptyPromotionTraceIdsError` for an empty
    ``resolved_trace_records`` list and
    :class:`~databasise.seam.refusals.DisagreeingPromotionTraceIdsError` when the records name
    more than one distinct arm — never "take the first" or "take the last": a promote call whose
    trace ids belong to two different wirings is a caller mistake, not a target to guess at.
    """
    if not resolved_trace_records:
        raise EmptyPromotionTraceIdsError(alias=alias)

    arm_names = {
        _arm_name_for_record(record, trace_ids[i] if i < len(trace_ids) else None)
        for i, record in enumerate(resolved_trace_records)
    }
    if len(arm_names) > 1:
        raise DisagreeingPromotionTraceIdsError(trace_ids=list(trace_ids))
    return next(iter(arm_names))


def declared_surface(
    resolved: dict[str, Any], registry: PartRegistry
) -> tuple[frozenset[str], tuple[str, ...]]:
    """CONTRACT §0's "declared socket / capability / effects surface" for the MAJOR/MINOR
    comparison (D-06): the union of every node's registered Part's own declared effects
    (``selectors._wiring_effects``, reused rather than re-derived — it already applies CR-01), plus
    the wiring's own ``provides`` list.
    """
    return frozenset(_wiring_effects(resolved, registry)), tuple(resolved.get("provides") or [])


def mint_version(
    prior_version: str | None,
    prior_surface: tuple[frozenset[str], tuple[str, ...]] | None,
    new_surface: tuple[frozenset[str], tuple[str, ...]],
) -> str:
    """D-06's semver mint rule. ``"1.0.0"`` when ``prior_version is None`` (a first promotion);
    otherwise a MAJOR bump when ``new_surface`` differs from ``prior_surface``, else a MINOR bump.
    **PATCH is never minted** — no branch of this function returns a version whose patch component
    is non-zero; no measured bug-fix distinction exists without a gate. Derived from the alias's
    prior *active* generation's own declared surface, never from a row count — a
    rollback-then-repromote sequence must mint a number reflecting an actual capability change,
    not how many times a mutation has ever been promoted.
    """
    if prior_version is None:
        return "1.0.0"
    major_str, minor_str, _patch_str = prior_version.split(".")
    major, minor = int(major_str), int(minor_str)
    if new_surface != prior_surface:
        return f"{major + 1}.0.0"
    return f"{major}.{minor + 1}.0"


def derive_mutation_class(
    new_resolved: dict[str, Any], prior_resolved: dict[str, Any] | None
) -> MutationClass:
    """D-10's machine derivation: the caller may not state a class. ``differing`` is the symmetric
    difference of the two resolved wirings' own node-id sets, unioned with the node ids present in
    both whose own ``component`` identity differs. If ``differing`` intersects
    :data:`_INDEX_RECIPE_NODE_IDS`, returns ``"index-side"``; elif it intersects
    :data:`_ANSWER_LEVEL_NODE_IDS`, returns ``"answer-level"``; else ``"retrieval-side"``. A first
    promotion (``prior_resolved is None``) is classed by the wiring's own node set alone under the
    identical rule — D-10's own stated behaviour, not a special case.
    """
    new_nodes = new_resolved.get("nodes", {})
    prior_nodes = (prior_resolved or {}).get("nodes", {})
    new_ids = set(new_nodes)
    prior_ids = set(prior_nodes)

    differing = new_ids ^ prior_ids
    for node_id in new_ids & prior_ids:
        if new_nodes[node_id].get("component") != prior_nodes[node_id].get("component"):
            differing.add(node_id)

    if differing & _INDEX_RECIPE_NODE_IDS:
        return "index-side"
    if differing & _ANSWER_LEVEL_NODE_IDS:
        return "answer-level"
    return "retrieval-side"


def enforce_gate_verb_posture(verb: str, mutation_class: MutationClass) -> None:
    """D-09/D-11: the one call site that reads :data:`_MEASUREMENT_POSTURE`. Always raises —
    called only for a verb in :data:`_GATE_VERBS`, which never appends a row in this milestone.
    ``True`` (retrieval-side, on by default) raises
    :class:`~databasise.seam.refusals.UncalibratedFloorRefusalError` (no calibrated A/A floor
    exists, RIG §AA.2); ``False`` (answer-level/index-side, off by default) raises
    :class:`~databasise.seam.refusals.MeasurementPostureRefusalError` (RIG §F3.2).

    15-16 (TOOL-12): ``Databasise.promote`` no longer calls this. A gate verb with no floor is
    ``GateNotCalibratedError``; with a valid floor the engine raises ``GateVerbNotBuiltError`` for a
    retrieval-side change and ``MeasurementPostureRefusalError`` for the other classes, so this
    function's retrieval-side branch is unreachable from ``promote``. Kept for its pinned signature.
    """
    if _MEASUREMENT_POSTURE[mutation_class]:
        raise UncalibratedFloorRefusalError(verb=verb, mutation_class=mutation_class)
    raise MeasurementPostureRefusalError(verb=verb, mutation_class=mutation_class)


__all__ = [
    "PromotionVerb",
    "PROMOTION_VERBS",
    "MutationClass",
    "PROVENANCE_OPERATOR_ASSERTED",
    "CHANGE_ORIGINS",
    "RECORD_KIND_PROMOTION",
    "RECORD_KIND_ROLLBACK",
    "RECORD_KIND_TOMBSTONE",
    "refuse_partial_evidence",
    "resolve_single_arm",
    "declared_surface",
    "mint_version",
    "derive_mutation_class",
    "enforce_gate_verb_posture",
]
