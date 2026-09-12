"""Pure computation for the operator-asserted promotion path (MACH-07/API-09, 07-01-PLAN.md): the
verb ladder, the measurement-posture refusal, the machine-derived mutation class, and the semver
mint rule. No I/O, no engine import — every function here takes already-resolved data (a resolved
wiring dict, a trace record, a registry) and returns or raises, following ``selectors.py``'s own
module-constant-plus-pure-function shape (``_wiring_effects``/``_match_capability``).

**Trace-id -> single-arm resolution (D-04).** A persisted ``RunRecord.to_dict()`` carries
``wiring_id``/``arm_id`` fields, but neither distinguishes one LightRAG arm from another in
practice: every LightRAG arm's own resolved ``wiring_id`` is the shared ``"lightrag-base"`` string
(no arm patch touches it), and ``arm_id`` is always the literal ``"seam"``
(``databasise/seam/engine.py::_execute``). ``wiring_instance_hash`` does differ per arm, but it is
computed over the *fully injected* resolved wiring (query text and token allowance stamped onto
every node's config by ``_inject_query``/``_inject_token_allowance``), so it differs per *query
too* — the same arm run against two different queries never has the same instance hash. The one
signal that is both query-invariant and unique per arm is the **dispatched node id set**: each
``RunRecord.nodes`` entry's own ``node_id``, which ``databasise/tests/seam/test_trace_token.py``
already proves is exactly the resolved wiring's own node id set. :func:`resolve_single_arm` matches
that set against every candidate wiring's own resolved node ids
(``databasise.wirings.resolve.all_wirings()``) — never a caller-supplied name (D-11).

**Mutation-class derivation compares component identity, not bare node-id sets (D-10).** The
node-id sets alone cannot express "the same node id now runs a different component" — an arm
patch's own ``replace`` operations can retarget a node's ``component`` without adding or removing
node ids. :func:`derive_mutation_class` therefore takes the two full resolved wiring dicts, not
bare id sets, so it can compare each shared node id's own ``component`` string.
"""

from __future__ import annotations

from typing import Any, Literal

from databasise.parts.registry import PartRegistry
from databasise.seam.refusals import (
    DisagreeingPromotionTraceIdsError,
    EmptyPromotionTraceIdsError,
    MeasurementPostureRefusalError,
    UncalibratedFloorRefusalError,
)
from databasise.seam.selectors import _wiring_effects
from databasise.wirings.resolve import all_wirings

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
    unlike ``wiring_instance_hash``."""
    return frozenset(node["node_id"] for node in resolved_trace_record.get("nodes", []))


def _arm_name_for_node_ids(node_ids: frozenset[str]) -> str:
    """The one candidate in :func:`~databasise.wirings.resolve.all_wirings` whose own resolved
    node id set equals ``node_ids``. Raises ``AssertionError`` — an internal invariant, never a
    consumer-reachable refusal — if no candidate matches, which should be unreachable for a trace
    persisted against the same wirings on disk.
    """
    for name, resolved in all_wirings():
        if frozenset(resolved.get("nodes", {}).keys()) == node_ids:
            return name
    raise AssertionError(
        "trace record's own dispatched node id set "
        f"{sorted(node_ids)!r} does not match any currently registered wiring's own resolved "
        "node id set"
    )


def resolved_wiring_for_arm(arm_name: str) -> dict[str, Any]:
    """The resolved wiring dict for ``arm_name`` from the same candidate pool
    :func:`resolve_single_arm` matches against — unlike
    ``databasise.wirings.resolve.resolve_arm``, this also resolves a non-LightRAG wiring name
    (e.g. ``"hipporag"``), since :func:`all_wirings` is the candidate pool ``resolve_single_arm``
    actually derives an arm name from.
    """
    for name, resolved in all_wirings():
        if name == arm_name:
            return resolved
    raise AssertionError(
        f"arm name {arm_name!r} was derived from resolve_single_arm's own scan of all_wirings() "
        "but does not appear there on a second pass — should be unreachable"
    )


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
        _arm_name_for_node_ids(_dispatched_node_ids(record)) for record in resolved_trace_records
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
    """
    if _MEASUREMENT_POSTURE[mutation_class]:
        raise UncalibratedFloorRefusalError(verb=verb, mutation_class=mutation_class)
    raise MeasurementPostureRefusalError(verb=verb, mutation_class=mutation_class)


__all__ = [
    "PromotionVerb",
    "MutationClass",
    "PROVENANCE_OPERATOR_ASSERTED",
    "CHANGE_ORIGINS",
    "RECORD_KIND_PROMOTION",
    "RECORD_KIND_ROLLBACK",
    "RECORD_KIND_TOMBSTONE",
    "resolve_single_arm",
    "resolved_wiring_for_arm",
    "declared_surface",
    "mint_version",
    "derive_mutation_class",
    "enforce_gate_verb_posture",
]
