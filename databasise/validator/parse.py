"""One-pass wiring parse: accumulates every violation with a path rather than raising on the
first, per wiring-spec-and-validation.md's validator-behaviour-as-contract rule ("The validator
MUST return every violation from a single validation pass at once ... a one-violation-per-pass
validator costs a full repair round trip per defect, and round trips dominate the cost of
validation, not the pass itself"). ``parse_wiring`` never raises for an ordinary defect: every
violation is accumulated into the returned ``ParsedWiring.report`` (a ``ValidationReport``,
``databasise/validator/errors.py``), which the caller inspects via ``report.ok``.

The checks: every ``component`` resolves in the registry, every entry in ``deps`` names a node
present in ``nodes``, every declared effect is a member of the seventeen (already enforced by
pydantic's ``Literal``-typed ``Effect`` field on ``WiringNode`` itself, so an invalid effect
surfaces as a per-node ``ValidationError`` this function turns into an accumulated violation
rather than a second, separately hand-rolled check), an empty ``nodes`` object, (CR-01) that a
node whose ``component`` resolved never declares an ``effects`` member its resolved ``Part``
itself does not declare (``CODE_EFFECTS_EXCEED_PART``) — a wiring MAY under-declare relative to
its Part, never over-declare — and (MACH-01) that a node never attempts to self-declare one of
the six fields CONTRACT §3 computes (``CODE_SELF_DECLARED_DERIVATION``) rather than every other
unknown node key, which remains ``CODE_INVALID_NODE_SCHEMA``. The effects-exceed-part check is a
consistency/hygiene check, not the containment enforcement itself: the runner
(``runner/scheduler.py``) and the blast-radius rule (``validator/blast_radius.py``) both source
``execution_mode``/store-scoping/the blast-radius predicate from the resolved ``Part``'s own
effects directly, never from the wiring's, so neither is affected by what a wiring declares here
regardless of this check.

Cycle detection (``validator.cycles.strongly_connected_components``) always runs, independent of
whether any other violation was found: a cycle is reported as data under ``report.cycles``, never
treated as a violation by itself, because cyclic wirings are legal content (CONTRACT §1) and only
the wiring author can know whether a given cycle is intended.

The depth/blast-radius pass (``validator.depth.effective_depth`` then
``validator.blast_radius.blast_radius_violations``, D-02's load-time call site) runs only when the
wiring is otherwise structurally sound (no unknown component, dangling dep, invalid node schema,
or empty-``nodes`` violation) — those checks require every node's part to have resolved and every
dep to name a real node, and a wiring that has not cleared that bar has nothing meaningful to say
about depth yet. A cycle does not gate this: with the SCC-condensation depth pass
(``validator/cycles.py``), a cyclic-but-otherwise-well-formed wiring still resolves a defined
depth for every node.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from pydantic import ValidationError

from databasise.parts.registry import PartRegistry, UnknownPartError
from databasise.parts.schema import Part, WiringNode
from databasise.validator.blast_radius import blast_radius_violations
from databasise.validator.cycles import strongly_connected_components
from databasise.validator.depth import effective_depth
from databasise.validator.errors import (
    CODE_DANGLING_DEP,
    CODE_EFFECTS_EXCEED_PART,
    CODE_EMPTY_WIRING,
    CODE_INVALID_NODE_SCHEMA,
    CODE_INVALID_WIRING_DOCUMENT,
    CODE_SELF_DECLARED_DERIVATION,
    CODE_UNKNOWN_COMPONENT,
    CODE_UNKNOWN_EFFECT,
    CODE_UNWIRED_STORE_EFFECT,
    ValidationReport,
    Violation,
    escape_pointer_token,
)

# Phase 10 D-15 (STOR-12): store effects the vocabulary keeps but no store backs.
_UNWIRED_STORE_EFFECTS: frozenset[str] = frozenset({"reads_lexical", "writes_lexical", "reads_blob"})

# CONTRACT §3's derived fields — computed by the validator, never declared by a wiring node. A
# node whose raw document attempts to state one of these under its own name is refused under
# CODE_SELF_DECLARED_DERIVATION rather than the generic CODE_INVALID_NODE_SCHEMA (MACH-01's
# no-self-declaration clause). This is this plan's own enumeration of the properties the
# validator actually computes today (02-03-PLAN.md Flagged Assumption 2) — a later phase adding a
# computed property must extend this set.
_DERIVED_FIELD_NAMES: frozenset[str] = frozenset(
    {
        "effective_depth",
        "execution_mode",
        "structural_depth",
        "depth",
        "artifact_scope",
        "blast_radius",
    }
)


@dataclass(frozen=True)
class ParsedWiring:
    """The load-frozen snapshot the runner reads. CONTRACT §11 forbids mid-run reads of mutable
    decision state, so ``nodes``, ``parts``, ``deps`` and ``node_order`` are immutable views
    (``MappingProxyType``/tuple), never a plain mutable dict or list a later step could quietly
    rewrite underneath the runner.

    ``report`` is the one mutable member: the accumulator ``parse_wiring`` extends with the
    blast-radius violations after it builds the snapshot. It carries every violation and every
    detected cycle from the parse pass that produced this snapshot — see ``validator/errors.py``.
    It defaults to an empty, ``ok`` report so existing call sites that construct a ``ParsedWiring``
    directly (test fixtures) need not thread one through when it is not the thing under test.
    """

    nodes: Mapping[str, WiringNode]
    parts: Mapping[str, Part]
    deps: Mapping[str, tuple[str, ...]]
    node_order: tuple[str, ...]
    report: ValidationReport = field(default_factory=ValidationReport)


# Where each derived field is actually computed, named in the refusal message so a wiring author
# can act on it without reading the validator's source (validator/blast_radius.py's own
# message-clarity property, extended here to the derivation refusal).
_DERIVED_FIELD_COMPUTED_BY: dict[str, str] = {
    "effective_depth": "databasise.validator.depth.effective_depth",
    "execution_mode": "databasise.validator.execution_mode.derive_execution_mode",
    "structural_depth": "the node's resolved Part in the registry, never the wiring itself",
    "depth": "databasise.validator.depth.effective_depth",
    "artifact_scope": "the node's resolved Part in the registry, never the wiring itself",
    "blast_radius": "databasise.validator.blast_radius.blast_radius_violations",
}


def _classify_node_schema_error(err: dict[str, Any]) -> str:
    """A pydantic ``ValidationError`` on a ``WiringNode`` can fail for many reasons. A derived
    field name in ``loc`` (CONTRACT §3's computed properties, MACH-01's no-self-declaration
    clause) is checked first — always classified as ``CODE_SELF_DECLARED_DERIVATION``, since a
    derived name is never ``effects``. Only the ``effects`` field's ``Literal`` rejection is
    specifically the "unknown effect member" defect the seventeen-member vocabulary names —
    everything else is a more general node-schema defect.
    """
    if any(name in _DERIVED_FIELD_NAMES for name in err["loc"]):
        return CODE_SELF_DECLARED_DERIVATION
    if "effects" in err["loc"]:
        return CODE_UNKNOWN_EFFECT
    return CODE_INVALID_NODE_SCHEMA


def parse_wiring(doc: dict[str, Any], registry: PartRegistry) -> ParsedWiring:
    violations: list[Violation] = []
    raw_nodes: dict[str, Any] = {}

    # A wiring is untrusted author input: a non-object document or a non-object `nodes` is
    # reported (WIRE-06), never raised, and the pass continues over an empty node map.
    if not isinstance(doc, dict):
        violations.append(
            Violation(
                code=CODE_INVALID_WIRING_DOCUMENT,
                pointer="",
                message="a wiring document must be a JSON object",
            )
        )
    elif not isinstance(doc.get("nodes", {}), dict):
        violations.append(
            Violation(
                code=CODE_INVALID_WIRING_DOCUMENT,
                pointer="/nodes",
                message="a wiring's `nodes` must be an object mapping node ids to nodes",
            )
        )
    else:
        raw_nodes = doc.get("nodes", {})

    if not violations and not raw_nodes:
        violations.append(
            Violation(
                code=CODE_EMPTY_WIRING,
                pointer="/nodes",
                message="a wiring's `nodes` object must not be empty",
            )
        )

    nodes: dict[str, WiringNode] = {}
    for node_id, raw in raw_nodes.items():
        token = escape_pointer_token(node_id)
        try:
            nodes[node_id] = WiringNode.model_validate(raw)
        except ValidationError as exc:
            for err in exc.errors():
                field_path = "/".join(escape_pointer_token(p) for p in err["loc"])
                pointer = f"/nodes/{token}/{field_path}" if field_path else f"/nodes/{token}"
                code = _classify_node_schema_error(err)
                if code == CODE_SELF_DECLARED_DERIVATION:
                    derived_field = next(
                        name for name in err["loc"] if name in _DERIVED_FIELD_NAMES
                    )
                    message = (
                        f"node {node_id!r} declares {derived_field!r}, a value CONTRACT §3 "
                        f"requires the validator to compute (via {_DERIVED_FIELD_COMPUTED_BY[derived_field]}) "
                        "rather than a wiring author stating it; remove the key and let the "
                        "computation govern"
                    )
                else:
                    message = err["msg"]
                violations.append(
                    Violation(
                        code=code,
                        pointer=pointer,
                        message=message,
                    )
                )

    parts: dict[str, Part] = {}
    for node_id, node in nodes.items():
        token = escape_pointer_token(node_id)
        try:
            part = registry.get(node.component)
        except UnknownPartError:
            # The message carries the wiring's own value only: the registry's part list is not
            # echoed back to a document author (WIRE-06).
            violations.append(
                Violation(
                    code=CODE_UNKNOWN_COMPONENT,
                    pointer=f"/nodes/{token}/component",
                    message=f"node {node_id!r} names component {node.component!r}, which is not registered",
                )
            )
        else:
            parts[node_id] = part
            # CR-01: the runner sources execution_mode/store-scoping/blast-radius from this
            # resolved Part's own effects, never the wiring's self-declared WiringNode.effects
            # (see runner/scheduler.py and validator/blast_radius.py). A wiring MAY declare a
            # narrower effects set than the Part is capable of (to prove it exercises only a
            # subset of what the Part can do), but never a broader one — a broader declaration
            # would be a claim the registry does not back, and is refused here rather than
            # silently accepted.
            extra_effects = set(node.effects) - set(part.effects)
            if extra_effects:
                violations.append(
                    Violation(
                        code=CODE_EFFECTS_EXCEED_PART,
                        pointer=f"/nodes/{token}/effects",
                        message=(
                            f"node {node_id!r} declares effects {sorted(extra_effects)} not "
                            f"declared by its resolved part {part.name_at_version!r} "
                            f"(part effects: {sorted(part.effects)}); a wiring node's effects "
                            "must be a subset of its part's registered effects"
                        ),
                    )
                )
            # D-15: the scheduler scopes from part.effects (CR-01), so the union is checked.
            unwired = (set(node.effects) | set(part.effects)) & _UNWIRED_STORE_EFFECTS
            if unwired:
                violations.append(
                    Violation(
                        code=CODE_UNWIRED_STORE_EFFECT,
                        pointer=f"/nodes/{token}/effects",
                        message=(
                            f"node {node_id!r} declares store effects {sorted(unwired)} that no "
                            "store backs; the machine wires only kv, vector and graph stores"
                        ),
                    )
                )
        for dep_index, dep in enumerate(node.deps):
            if dep not in raw_nodes:
                violations.append(
                    Violation(
                        code=CODE_DANGLING_DEP,
                        pointer=f"/nodes/{token}/deps/{dep_index}",
                        message=f"dependency {dep!r} is not a node in this wiring",
                    )
                )

    deps = {node_id: tuple(node.deps) for node_id, node in nodes.items()}

    # Cycle detection always runs, independent of the violations above — a cycle is data, not a
    # defect (see module docstring).
    deps_as_sets = {node_id: set(dep_tuple) for node_id, dep_tuple in deps.items()}
    sccs = strongly_connected_components(deps_as_sets)
    cycles: list[list[str]] = [sorted(component) for component in sccs if len(component) > 1]
    in_cycle = {node_id for cycle in cycles for node_id in cycle}
    for node_id, dep_set in deps_as_sets.items():
        # a self-loop is a one-member SCC that is still a cycle; inside a larger SCC it is listed once
        if node_id in dep_set and node_id not in in_cycle:
            cycles.append([node_id])
    cycles.sort()  # stable across calls whatever order the SCC pass yields

    report = ValidationReport(violations=violations, cycles=cycles)

    parsed = ParsedWiring(
        nodes=MappingProxyType(dict(nodes)),
        parts=MappingProxyType(dict(parts)),
        deps=MappingProxyType(deps),
        node_order=tuple(sorted(nodes.keys())),
        report=report,
    )

    if report.ok:
        # Every node's part resolved and every dep names a real node — the graph-dependent
        # checks (D-02's load-time blast-radius call site) can now run safely.
        depth_map = effective_depth(parsed)
        report.violations.extend(blast_radius_violations(parsed, depth_map))

    return parsed
