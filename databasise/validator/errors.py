"""``Violation``/``ValidationReport`` — the shapes every validator check accumulates into,
never raises. Per wiring-spec-and-validation.md's validator-behaviour-as-contract rule: "The
validator MUST return every violation from a single validation pass at once ... a
one-violation-per-pass validator costs a full repair round trip per defect, and round trips
dominate the cost of validation, not the pass itself."

A ``ValidationReport.cycles`` entry is data, not a defect: cyclic wirings are legal content
(CONTRACT §1), and only the wiring author can know whether a given cycle is intended, so the
validator reports every detected cycle without ever treating its mere presence as a violation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Stable violation codes — a caller matches on ``Violation.code``, never on ``message`` text.
CODE_UNKNOWN_COMPONENT = "unknown-component"
CODE_DANGLING_DEP = "dangling-dep"
CODE_UNKNOWN_EFFECT = "unknown-effect"
CODE_INVALID_NODE_SCHEMA = "invalid-node-schema"
CODE_EMPTY_WIRING = "empty-wiring"
CODE_BLAST_RADIUS_REFUSAL = "blast-radius-refusal"
CODE_EFFECTS_EXCEED_PART = "effects-exceed-part"


@dataclass(frozen=True)
class Violation:
    """One defect: a stable ``code``, an RFC 6901 JSON Pointer into the wiring document (for
    example ``/nodes/extract/effects/1``), and a human-readable ``message``.
    """

    code: str
    pointer: str
    message: str


@dataclass
class ValidationReport:
    """Every violation accumulated from one validation pass, plus every detected cycle reported
    as data. ``ok`` is true exactly when ``violations`` is empty — a report with cycles but no
    violations is still ``ok``, because a cycle by itself is legal wiring content.
    """

    violations: list[Violation] = field(default_factory=list)
    cycles: list[list[str]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.violations
