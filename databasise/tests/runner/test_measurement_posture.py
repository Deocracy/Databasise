"""A structural pin on MACH-09's default-off measurement posture
(``.planning/phases/02-falsifier-gate/02-MACH-09-POSTURE.md``), mirroring
``databasise/tests/test_trusted_source_invariant.py``'s AST-scan shape: a scan over source
files with findings reported by file and line, not a bare boolean.

The posture record states that measurement-gated promotion is off by default for the
answer-level and index-side classes (RIG §F3.2). Before 07-01-PLAN.md this held because no
measurement-gated promotion path existed anywhere in ``databasise/`` at all; as of 07-01-PLAN.md
(MACH-07), the operator-asserted path is real, and the posture instead holds because the two
off-by-default classes' gate-adjudicated verbs (``promote-next``, ``promote-now``) refuse by name
before ever reaching ``Ledger.append()`` — proven at runtime by
``databasise/tests/seam/test_promotion_posture.py``, not merely by this module's own absence
check. This module still pins what a real promotion-gate *implementation* would look like, so
that one appearing anywhere outside tests still forces this record open:

1. **No non-test module imports the ledger, except two deliberately reviewed, named
   exceptions.** ``databasise/ledger/ledger.py`` defines the append-only ledger; nothing outside
   ``databasise/tests/`` and ``databasise/ledger/`` itself may import it, with exactly two named
   exceptions: ``databasise/seam/selectors.py`` (04-03-PLAN.md, D-12/FA-06), whose alias branch
   calls ``Ledger.by_alias`` — a read-only projection — and never ``Ledger.append()``; and
   ``databasise/seam/engine.py`` (07-01-PLAN.md, MACH-07), whose ``Databasise.promote()`` calls
   ``Ledger.append()`` for the ``operator-asserted`` verb only — every gate-adjudicated verb
   refuses before that line is ever reached (``databasise.seam.promotion.
   enforce_gate_verb_posture``). ``databasise/ledger/`` is exempt for the same reason
   ``databasise/validator/parse.py`` is exempt in the trusted-source pin: it is the definition
   site, not a caller. See ``02-MACH-09-POSTURE.md``'s "Read-only exception" and "07-01-PLAN.md:
   the operator-asserted write exception" sections for why these two callers do not mean the
   *gate-adjudicated* promotion path has started to exist.
2. **No promotion-gate implementation is defined outside tests.** No module under the same scan
   defines a function or method named ``promote_next`` or ``promote_now`` — CONTRACT §5's
   gate-adjudicated verbs, which this milestone never implements (they only refuse). ``promote``
   and ``rollback`` are exempted for exactly one file, ``databasise/seam/engine.py``
   (07-01-PLAN.md, 07-02-PLAN.md): both are real operator-asserted entry points (RIG §PR.1/§PR.2),
   never members of §5's ladder — ``promote`` is the entry point every verb (including the
   gate-adjudicated ones) passes through on its way to refusing; ``rollback`` is its own §18
   operation, appending through the identical operator-asserted-only path. ``retire`` needs no
   exemption at all: it was never in this set's named vocabulary, since it was never mistaken for
   a member of §5's ladder in the first place.
3. **``LedgerRecord.promotion_provenance`` can never be defaulted.** No default, no
   ``default_factory`` — an append can never omit its provenance nor acquire one by absence
   (02-CONTEXT.md D-04).

**This test was expected to, and did, fail when Phase 7 built MACH-07's promote path, and again
when 07-02-PLAN.md built rollback** — the posture decision was forced into the open exactly as
this docstring anticipated both times, and
``.planning/phases/02-falsifier-gate/02-MACH-09-POSTURE.md`` was updated in the same change each
time, recording the new narrow exceptions above rather than silently relaxing this test.
"""

from __future__ import annotations

import ast
import dataclasses
from dataclasses import dataclass
from pathlib import Path

from databasise.ledger.ledger import LedgerRecord

# Exemption list — extend deliberately, with a reason, never silently.
_EXEMPT_DIRS = (
    "tests",  # the test suite itself, including this module
    "ledger",  # the ledger's own definition site, not a caller
)

# Per-file exemptions — a single, deliberately reviewed, named caller per entry, never a
# directory-wide carve-out. Extend only alongside a 02-MACH-09-POSTURE.md update naming exactly
# what changed and why it is not the gate-adjudicated promotion path.
_EXEMPT_FILES = (
    # 04-03-PLAN.md (D-12/FA-06): the seam's alias selector reads Ledger.by_alias — a read-only
    # projection, never Ledger.append() — to resolve which wiring an alias names.
    "seam/selectors.py",
    # 07-01-PLAN.md (MACH-07): Databasise.promote() calls Ledger.append() for the
    # operator-asserted verb only — every gate-adjudicated verb refuses (via
    # databasise.seam.promotion.enforce_gate_verb_posture) before that line is ever reached.
    # 07-02-PLAN.md: Databasise.rollback()/retire() append through the identical
    # operator-asserted-only path (RIG §PR.2) — neither is a member of CONTRACT §5's
    # check/preview/run/promote-next/promote-now ladder this guard's own item 2 fences. See
    # _PROMOTION_VERB_EXEMPT_FILES below for the matching promotion-verb-definition exemption.
    "seam/engine.py",
)

# A narrower, promotion-verb-specific exemption: this file defines `promote` and `rollback` (both
# real operator-asserted entry points, RIG §PR.1/§PR.2), but no gate-adjudicated verb
# (`promote_next`/`promote_now`) is defined anywhere in it — those names are only ever string
# values of the `verb` parameter, checked and refused, never function definitions.
# `retire` is deliberately absent from `_PROMOTION_VERB_NAMES` below: it was never part of
# CONTRACT §5's gate-adjudicated ladder this set fences (that ladder is
# check/preview/run/promote-next/promote-now), so defining it needs no exemption at all.
_PROMOTION_VERB_EXEMPT_FILES = ("seam/engine.py",)

_PROMOTION_VERB_NAMES = frozenset({"promote", "promote_next", "promote_now", "rollback"})
_PROMOTION_VERB_EXEMPT_DETAILS = frozenset({"def promote(...)", "def rollback(...)"})


@dataclass(frozen=True)
class _Finding:
    path: str
    line: int
    detail: str


def _package_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _scanned_files() -> list[Path]:
    root = _package_root()
    files: list[Path] = []
    for path in root.rglob("*.py"):
        relative = path.relative_to(root)
        if relative.parts and relative.parts[0] in _EXEMPT_DIRS:
            continue
        files.append(path)
    return files


def _ledger_import_findings(path: Path) -> list[_Finding]:
    """Flag any import whose dotted module path is ``databasise.ledger`` or a submodule of it,
    any bare ``import databasise.ledger[...]`` form, and any ``from databasise import ledger``
    form (or a dotted path into it via an imported alias name, e.g. ``from databasise import
    ledger as l``) — the shapes a caller could use to reach ``Ledger``, ``LedgerRecord``, or the
    ``databasise.ledger`` module itself (WR-03).
    """
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))

    findings: list[_Finding] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "databasise.ledger" or module.startswith("databasise.ledger."):
                findings.append(
                    _Finding(str(path), node.lineno, f"from {module} import ...")
                )
                continue
            # `from databasise import ledger` reaches the ledger via the imported alias name
            # rather than the dotted module path — check the combined "module.alias" against
            # the same "databasise.ledger"/"databasise.ledger." predicate.
            for alias in node.names:
                combined = f"{module}.{alias.name}" if module else alias.name
                if combined == "databasise.ledger" or combined.startswith(
                    "databasise.ledger."
                ):
                    findings.append(
                        _Finding(
                            str(path), node.lineno, f"from {module} import {alias.name}"
                        )
                    )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "databasise.ledger" or alias.name.startswith(
                    "databasise.ledger."
                ):
                    findings.append(_Finding(str(path), node.lineno, f"import {alias.name}"))
    return findings


def _promotion_verb_findings(path: Path) -> list[_Finding]:
    """AST walk over ``FunctionDef``/``AsyncFunctionDef`` names — not a text grep, so a name
    inside a docstring or comment does not trip this.
    """
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))

    findings: list[_Finding] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in (
            _PROMOTION_VERB_NAMES
        ):
            findings.append(_Finding(str(path), node.lineno, f"def {node.name}(...)"))
    return findings


def test_no_non_test_module_imports_the_ledger():
    root = _package_root()
    all_findings: list[_Finding] = []
    for path in _scanned_files():
        if path.relative_to(root).as_posix() in _EXEMPT_FILES:
            continue
        all_findings.extend(_ledger_import_findings(path))

    assert all_findings == [], (
        "a non-test, non-ledger module imports the ledger — this means the measurement-gated "
        "promotion path has started to exist. Update "
        ".planning/phases/02-falsifier-gate/02-MACH-09-POSTURE.md in the same change rather "
        f"than relaxing this test: {all_findings}"
    )


def test_no_promotion_verb_is_defined_outside_tests():
    root = _package_root()
    all_findings: list[_Finding] = []
    for path in _scanned_files():
        relative = path.relative_to(root).as_posix()
        for finding in _promotion_verb_findings(path):
            # `promote`/`rollback` on the one named exempt file are both real operator-asserted
            # entry points (07-01-PLAN.md/07-02-PLAN.md); a gate-adjudicated verb name
            # (promote_next/promote_now), or either defined anywhere else, still fails this test.
            if (
                relative in _PROMOTION_VERB_EXEMPT_FILES
                and finding.detail in _PROMOTION_VERB_EXEMPT_DETAILS
            ):
                continue
            all_findings.append(finding)

    assert all_findings == [], (
        "a gate-adjudicated promotion verb (promote_next/promote_now), or `promote`/`rollback` "
        "outside their one named exemption, is defined outside the test suite — this means the "
        "gate-adjudicated promotion path has started to exist. Update "
        ".planning/phases/02-falsifier-gate/02-MACH-09-POSTURE.md in the same change rather than "
        f"relaxing this test: {all_findings}"
    )


def test_promotion_provenance_has_no_default():
    field = next(
        f for f in dataclasses.fields(LedgerRecord) if f.name == "promotion_provenance"
    )
    assert field.default is dataclasses.MISSING, (
        "LedgerRecord.promotion_provenance carries a default value — a ledger append could "
        "then omit its provenance and acquire one by absence, which is exactly what "
        "02-CONTEXT.md D-04's human-in-the-loop posture forbids."
    )
    assert field.default_factory is dataclasses.MISSING, (
        "LedgerRecord.promotion_provenance carries a default_factory — same failure as a bare "
        "default: an append could omit its provenance and acquire one by absence."
    )
