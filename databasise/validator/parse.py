"""One-pass wiring parse: accumulates every violation with a path rather than raising on the
first, per wiring-spec-and-validation.md's validator-behaviour-as-contract rule ("The validator
MUST return every violation from a single validation pass at once ... a one-violation-per-pass
validator costs a full repair round trip per defect, and round trips dominate the cost of
validation, not the pass itself").

For the tracer the checks are: every ``component`` resolves in the registry, every entry in
``deps`` names a node present in ``nodes``, and every declared effect is a member of the
seventeen — the last already enforced by pydantic's ``Literal``-typed ``Effect`` field on
``WiringNode`` itself, so an invalid effect surfaces as a per-node ``ValidationError`` this
function turns into an accumulated violation rather than a second, separately hand-rolled check.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from pydantic import ValidationError

from databasise.parts.registry import PartRegistry, UnknownPartError
from databasise.parts.schema import Part, WiringNode


class WiringValidationError(ValueError):
    """Every violation accumulated in one pass, each carrying a JSON-Pointer-style path."""

    def __init__(self, violations: list[dict[str, str]]):
        self.violations = violations
        super().__init__(f"{len(violations)} wiring violation(s): {violations}")


@dataclass(frozen=True)
class ParsedWiring:
    """The load-frozen snapshot the runner reads. CONTRACT §11 forbids mid-run reads of mutable
    decision state, so every collection here is a read-only view (``MappingProxyType``/tuple),
    never a plain mutable dict or list a later step could quietly rewrite underneath the runner.
    """

    nodes: Mapping[str, WiringNode]
    parts: Mapping[str, Part]
    deps: Mapping[str, tuple[str, ...]]
    node_order: tuple[str, ...]


def parse_wiring(doc: dict[str, Any], registry: PartRegistry) -> ParsedWiring:
    violations: list[dict[str, str]] = []
    raw_nodes: dict[str, Any] = doc.get("nodes", {})

    nodes: dict[str, WiringNode] = {}
    for node_id, raw in raw_nodes.items():
        try:
            nodes[node_id] = WiringNode.model_validate(raw)
        except ValidationError as exc:
            for err in exc.errors():
                field_path = "/".join(str(p) for p in err["loc"])
                path = f"/nodes/{node_id}/{field_path}" if field_path else f"/nodes/{node_id}"
                violations.append({"path": path, "message": err["msg"]})

    parts: dict[str, Part] = {}
    for node_id, node in nodes.items():
        try:
            parts[node_id] = registry.get(node.component)
        except UnknownPartError as exc:
            violations.append({"path": f"/nodes/{node_id}/component", "message": str(exc)})
        for dep in node.deps:
            if dep not in raw_nodes:
                violations.append(
                    {
                        "path": f"/nodes/{node_id}/deps",
                        "message": f"dependency {dep!r} is not a node in this wiring",
                    }
                )

    if violations:
        raise WiringValidationError(violations)

    deps = {node_id: tuple(node.deps) for node_id, node in nodes.items()}
    return ParsedWiring(
        nodes=MappingProxyType(dict(nodes)),
        parts=MappingProxyType(dict(parts)),
        deps=MappingProxyType(deps),
        node_order=tuple(sorted(nodes.keys())),
    )
