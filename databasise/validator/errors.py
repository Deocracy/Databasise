"""``Violation``/``ValidationReport`` — the shapes every validator check accumulates into,
never raises. Per wiring-spec-and-validation.md's validator-behaviour-as-contract rule: "The
validator MUST return every violation from a single validation pass at once ... a
one-violation-per-pass validator costs a full repair round trip per defect, and round trips
dominate the cost of validation, not the pass itself."

A ``ValidationReport.cycles`` entry is data, not a defect: cyclic wirings are legal content
(CONTRACT §1), and only the wiring author can know whether a given cycle is intended, so the
validator reports every detected cycle without ever treating its mere presence as a violation.

``CODE_SELF_DECLARED_DERIVATION`` is a wiring node's attempt to state a value CONTRACT §3
requires the validator to compute — ``effective_depth``, ``execution_mode``, ``structural_depth``,
``depth``, ``artifact_scope`` or ``blast_radius`` — rather than letting the machine derive it. It
is distinguished by code from ``CODE_INVALID_NODE_SCHEMA`` (any other unknown node key), so a
typo and an attempted self-declaration are never conflated.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Stable violation codes — a caller matches on ``Violation.code``, never on ``message`` text.
CODE_UNKNOWN_COMPONENT = "unknown-component"
CODE_DANGLING_DEP = "dangling-dep"
CODE_UNKNOWN_EFFECT = "unknown-effect"
CODE_INVALID_NODE_SCHEMA = "invalid-node-schema"
CODE_EMPTY_WIRING = "empty-wiring"
CODE_INVALID_WIRING_DOCUMENT = "invalid-wiring-document"
"""The wiring document is not a JSON object, or its ``nodes`` value is present but not an object
(WIRE-06): reported instead of raised so a malformed author document is a refusal, not a 500."""
CODE_KIND_MISMATCH = "kind-mismatch"
"""A wiring node's ``kind`` differs from the ``kind`` of the registered part its ``component``
names (WIRE-06): the registry's kind governs placement and depth, so a disagreeing wiring is refused."""
CODE_CYCLIC_WIRING = "cyclic-wiring"
"""A wiring's dependency graph holds a cycle where the engine refuses one before dispatch (D-07);
``parse_wiring`` itself still reports a cycle as data under ``ValidationReport.cycles``, not as this code."""
CODE_BLAST_RADIUS_REFUSAL = "blast-radius-refusal"
CODE_EFFECTS_EXCEED_PART = "effects-exceed-part"
CODE_SELF_DECLARED_DERIVATION = "self-declared-derivation"
"""A wiring node attempted to state a value CONTRACT §3 requires the validator to compute
(``effective_depth``, ``execution_mode``, ``structural_depth``, ``depth``, ``artifact_scope``,
``blast_radius``) rather than letting the machine derive it from wiring + registry. MACH-01's
no-self-declaration clause: the computation governs regardless of what a wiring author writes, so
an attempt to write one of these keys is refused rather than silently ignored."""
CODE_UNWIRED_STORE_EFFECT = "unwired-store-effect"
"""A node (or its resolved part) declares a store effect that is in the frozen 17-member Effect
vocabulary but has no store behind it after Phase 10 D-15 (``reads_lexical``, ``writes_lexical``,
``reads_blob``). Refused at parse time so no wiring parses and then fails inside a node when it
reaches for a store the machine never builds (STOR-12)."""


def escape_pointer_token(token: object) -> str:
    """One RFC 6901 reference token: ``~`` becomes ``~0`` first, then ``/`` becomes ``~1``, so a
    node id containing either character still addresses exactly one location."""
    return str(token).replace("~", "~0").replace("/", "~1")


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
