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
rather than a second, separately hand-rolled check), an empty ``nodes`` object, and (CR-01) that a
node whose ``component`` resolved never declares an ``effects`` member its resolved ``Part``
itself does not declare (``CODE_EFFECTS_EXCEED_PART``) — a wiring MAY under-declare relative to
its Part, never over-declare. This is a consistency/hygiene check, not the containment
enforcement itself: the runner (``runner/scheduler.py``) and the blast-radius rule
(``validator/blast_radius.py``) both source ``execution_mode``/store-scoping/the blast-radius
predicate from the resolved ``Part``'s own effects directly, never from the wiring's, so neither
is affected by what a wiring declares here regardless of this check.

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
    CODE_UNKNOWN_COMPONENT,
    CODE_UNKNOWN_EFFECT,
    ValidationReport,
    Violation,
)


class WiringValidationError(ValueError):
    """Retained for import stability; ``parse_wiring`` no longer raises this. Every violation now
    accumulates into the returned ``ParsedWiring.report`` instead — see the module docstring.
    """

    def __init__(self, violations: list[dict[str, str]]):
        self.violations = violations
        super().__init__(f"{len(violations)} wiring violation(s): {violations}")


@dataclass(frozen=True)
class ParsedWiring:
    """The load-frozen snapshot the runner reads. CONTRACT §11 forbids mid-run reads of mutable
    decision state, so every collection here is a read-only view (``MappingProxyType``/tuple),
    never a plain mutable dict or list a later step could quietly rewrite underneath the runner.

    ``report`` carries every violation and every detected cycle from the parse pass that produced
    this snapshot — see ``validator/errors.py``. It defaults to an empty, ``ok`` report so
    existing call sites that construct a ``ParsedWiring`` directly (test fixtures) need not
    thread one through when it is not the thing under test.
    """

    nodes: Mapping[str, WiringNode]
    parts: Mapping[str, Part]
    deps: Mapping[str, tuple[str, ...]]
    node_order: tuple[str, ...]
    report: ValidationReport = field(default_factory=ValidationReport)


def _classify_node_schema_error(err: dict[str, Any]) -> str:
    """A pydantic ``ValidationError`` on a ``WiringNode`` can fail for many reasons; only the
    ``effects`` field's ``Literal`` rejection is specifically the "unknown effect member" defect
    the seventeen-member vocabulary names — everything else is a more general node-schema defect.
    """
    if "effects" in err["loc"]:
        return CODE_UNKNOWN_EFFECT
    return CODE_INVALID_NODE_SCHEMA


def parse_wiring(doc: dict[str, Any], registry: PartRegistry) -> ParsedWiring:
    violations: list[Violation] = []
    raw_nodes: dict[str, Any] = doc.get("nodes", {})

    if not raw_nodes:
        violations.append(
            Violation(
                code=CODE_EMPTY_WIRING,
                pointer="/nodes",
                message="a wiring's `nodes` object must not be empty",
            )
        )

    nodes: dict[str, WiringNode] = {}
    for node_id, raw in raw_nodes.items():
        try:
            nodes[node_id] = WiringNode.model_validate(raw)
        except ValidationError as exc:
            for err in exc.errors():
                field_path = "/".join(str(p) for p in err["loc"])
                pointer = f"/nodes/{node_id}/{field_path}" if field_path else f"/nodes/{node_id}"
                violations.append(
                    Violation(
                        code=_classify_node_schema_error(err),
                        pointer=pointer,
                        message=err["msg"],
                    )
                )

    parts: dict[str, Part] = {}
    for node_id, node in nodes.items():
        try:
            part = registry.get(node.component)
        except UnknownPartError as exc:
            violations.append(
                Violation(
                    code=CODE_UNKNOWN_COMPONENT,
                    pointer=f"/nodes/{node_id}/component",
                    message=str(exc),
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
                        pointer=f"/nodes/{node_id}/effects",
                        message=(
                            f"node {node_id!r} declares effects {sorted(extra_effects)} not "
                            f"declared by its resolved part {part.name_at_version!r} "
                            f"(part effects: {sorted(part.effects)}); a wiring node's effects "
                            "must be a subset of its part's registered effects"
                        ),
                    )
                )
        for dep_index, dep in enumerate(node.deps):
            if dep not in raw_nodes:
                violations.append(
                    Violation(
                        code=CODE_DANGLING_DEP,
                        pointer=f"/nodes/{node_id}/deps/{dep_index}",
                        message=f"dependency {dep!r} is not a node in this wiring",
                    )
                )

    deps = {node_id: tuple(node.deps) for node_id, node in nodes.items()}

    # Cycle detection always runs, independent of the violations above — a cycle is data, not a
    # defect (see module docstring).
    deps_as_sets = {node_id: set(dep_tuple) for node_id, dep_tuple in deps.items()}
    sccs = strongly_connected_components(deps_as_sets)
    cycles: list[list[str]] = [sorted(component) for component in sccs if len(component) > 1]
    for node_id, dep_set in deps_as_sets.items():
        if node_id in dep_set:  # a self-loop is a one-member SCC that is still a cycle
            cycles.append([node_id])

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
