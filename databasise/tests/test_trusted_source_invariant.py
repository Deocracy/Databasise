"""A structural pin on CR-01's trusted-source rule (01-10-PLAN.md Task 3, DEC-D): no enforcement
path in ``databasise/runner/scheduler.py`` or ``databasise/validator/blast_radius.py`` reads a
wiring node's ``effects`` or ``kind`` attribute — every containment, placement, capability-scoping
and blast-radius decision must be sourced from the registry's own resolved ``Part``, never from
the wiring's untrusted, self-declared fields (``validator/cycles.py``'s own "a hostile or merely
large wiring could declare..." framing).

``databasise/validator/parse.py`` is deliberately exempt and NOT scanned by this module:
``parse_wiring``'s ``CODE_EFFECTS_EXCEED_PART`` check is the one legitimate site that compares a
wiring node's declared ``effects`` against its resolved Part's — a validation-layer consistency
check, never the enforcement itself (see that module's own docstring).

**DEC-D (recorded here in summary; full rationale in 01-10-PLAN.md's
``<decisions_recorded_here>``).** ``01-REVIEW-FIX.md``'s CR-01 fix pass deliberately narrowed the
new consistency check in ``parse_wiring`` to ``effects`` only, not ``kind``. That narrowing is
accepted here, not extended: ``execution_mode`` — the only consumer of a ``kind`` value in any
enforcement path — is derived from ``part.kind`` at ``runner/scheduler.py``'s
``derive_execution_mode(part.effects, part.kind)`` call site, and an exhaustive attribute scan of
the package outside ``databasise/tests/`` finds ZERO reads of a wiring node's ``kind`` anywhere. A
strict ``kind``-consistency check would close no bypass (the property is already unconditional
without it) and would break the deliberate, documented, pre-existing convention that
``WiringNode.kind`` is an unconstrained ``str`` decoupled from a Part's own structural kind
(``tests/validator/test_taint_conformance.py``'s 12-case table sets ``WiringNode.kind="primitive"``
uniformly against fixture Parts of kind ``stage``/``opaque``/``evidence``, and
``tests/test_phase_success_criteria.py``'s module docstring documents the decoupling explicitly).

This test is what keeps DEC-D's second clause ("no enforcement path reads the wiring node's
``kind`` either") true going forward, rather than leaving it as prose a later change could
silently invalidate — which is exactly how the ``resumable`` residual (closed by the
orchestrator's own ``973592e`` fix, per ``01-REVIEW-FIX.md``) survived the first CR-01 fix pass
until a later manual inspection caught it. Both attribute names are asserted, not only ``kind``: a
reintroduced ``effects`` read is the same bypass class CR-01 already closed once.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

_FLAGGED_ATTRS = frozenset({"effects", "kind"})
_WIRING_MAPPING_ATTR = "nodes"  # parsed.nodes[node_id] — the wiring's own untrusted node mapping

_SCANNED_MODULES = ("runner/scheduler.py", "validator/blast_radius.py")


@dataclass(frozen=True)
class _Finding:
    path: str
    line: int
    detail: str


def _is_wiring_node_subscript(node: ast.expr) -> bool:
    """``True`` iff ``node`` is exactly the ``parsed.nodes[node_id]`` shape: a ``Subscript`` whose
    ``.value`` is an ``Attribute`` ending in ``.nodes`` (the wiring's own node mapping, as opposed
    to ``parsed.parts[node_id]``, the registry's resolved-Part mapping, which this check does not
    flag — reading a Part's own ``effects``/``kind`` is the entire point of CR-01's fix).
    """
    return (
        isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Attribute)
        and node.value.attr == _WIRING_MAPPING_ATTR
    )


def _wiring_node_bound_names(tree: ast.Module) -> set[str]:
    """Every local name bound anywhere in the module by a plain assignment whose right-hand side
    is exactly a ``parsed.nodes[node_id]`` subscript (e.g. ``node = parsed.nodes[node_id]``) — an
    attribute read off one of these names is a read off the untrusted wiring node itself, not the
    registry's resolved Part.
    """
    bound: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and _is_wiring_node_subscript(node.value)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        ):
            bound.add(node.targets[0].id)
    return bound


def _flagged_attribute_reads(path: Path) -> list[_Finding]:
    """Walk ``path``'s AST for an ``effects``/``kind`` attribute read on a binding derived from
    the wiring's own node mapping — either directly chained (``parsed.nodes[node_id].effects``)
    or via a locally bound name (``node = parsed.nodes[node_id]`` ... ``node.effects``). Purely
    AST-based: a docstring or comment describing the rule in prose (both modules under scan carry
    exactly that prose) produces no ``ast.Attribute`` node at all and therefore cannot trip this.
    """
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    wiring_bound_names = _wiring_node_bound_names(tree)

    findings: list[_Finding] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Attribute) and node.attr in _FLAGGED_ATTRS):
            continue

        if _is_wiring_node_subscript(node.value):
            findings.append(
                _Finding(str(path), node.lineno, f"parsed.nodes[...].{node.attr} (direct chain)")
            )
        elif isinstance(node.value, ast.Name) and node.value.id in wiring_bound_names:
            findings.append(
                _Finding(
                    str(path),
                    node.lineno,
                    f"{node.value.id}.{node.attr} (bound from parsed.nodes[...])",
                )
            )
    return findings


def _package_root() -> Path:
    return Path(__file__).resolve().parent.parent


def test_no_scanned_module_reads_a_wiring_nodes_effects_or_kind():
    package_root = _package_root()
    all_findings: list[_Finding] = []
    for relative_path in _SCANNED_MODULES:
        all_findings.extend(_flagged_attribute_reads(package_root / relative_path))

    assert all_findings == [], (
        "found a wiring-node effects/kind read outside validator/parse.py's own consistency "
        f"check: {all_findings}"
    )


def test_the_check_does_not_trip_on_prose_describing_the_rule():
    """Non-vacuous guard: both scanned modules carry exactly the prose this rule must NOT trip
    on (``runner/scheduler.py``'s CR-01 docstring paragraph, ``validator/blast_radius.py``'s
    module docstring) — confirmed here by grepping the raw source text for that prose while the
    AST-based test above still passes clean, proving the check discriminates real attribute
    access from documentation describing it.
    """
    package_root = _package_root()
    scheduler_source = (package_root / "runner/scheduler.py").read_text(encoding="utf-8")
    blast_radius_source = (package_root / "validator/blast_radius.py").read_text(encoding="utf-8")

    assert "parsed.nodes[node_id].effects" in scheduler_source
    assert "parsed.nodes[node_id].effects" in blast_radius_source
    # The AST check above already ran clean over these same two files in the other test in this
    # module — this test exists to name explicitly which prose was present while it did.
