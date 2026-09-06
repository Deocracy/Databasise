"""A structural pin on MACH-09's default-off measurement posture
(``.planning/phases/02-falsifier-gate/02-MACH-09-POSTURE.md``), mirroring
``databasise/tests/test_trusted_source_invariant.py``'s AST-scan shape: a scan over source
files with findings reported by file and line, not a bare boolean.

The posture record states that measurement-gated promotion is off by default for the
answer-level and index-side classes (RIG §F3.2), and that this holds today — without any
``measurement_posture`` configuration switch — because no measurement-gated promotion path
exists anywhere in ``databasise/``. This module is what keeps that claim true going forward:

1. **No non-test module imports the ledger, except one deliberately reviewed, read-only
   caller.** ``databasise/ledger/ledger.py`` defines the append-only ledger; nothing outside
   ``databasise/tests/`` and ``databasise/ledger/`` itself may import it, with exactly one named
   exception: ``databasise/seam/selectors.py`` (04-03-PLAN.md, D-12/FA-06), whose alias branch
   calls ``Ledger.by_alias`` — a read-only projection — to resolve which wiring an alias names.
   It never calls ``Ledger.append()``. ``databasise/ledger/`` is exempt for the same reason
   ``databasise/validator/parse.py`` is exempt in the trusted-source pin: it is the definition
   site, not a caller. See ``02-MACH-09-POSTURE.md``'s "Read-only exception" section for why this
   one caller does not mean the promotion path has started to exist.
2. **No promotion verb is defined outside tests.** No module under the same scan defines a
   function or method named ``promote``, ``promote_next``, ``promote_now``, or ``rollback``.
3. **``LedgerRecord.promotion_provenance`` can never be defaulted.** No default, no
   ``default_factory`` — an append can never omit its provenance nor acquire one by absence
   (02-CONTEXT.md D-04).

**This test is expected to fail when Phase 7 builds MACH-07's promote/rollback path.** That
failure is the posture decision being forced into the open: a new ledger caller or a new
promotion verb means the promotion path has started to exist, and
``.planning/phases/02-falsifier-gate/02-MACH-09-POSTURE.md`` must be updated in the same
change rather than this test relaxed without updating the record it pins.
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

# Per-file exemptions — a single, deliberately reviewed, read-only non-test caller, never a
# directory-wide carve-out. Extend only alongside a 02-MACH-09-POSTURE.md update naming exactly
# what changed and why it is not the promotion path.
_EXEMPT_FILES = (
    # 04-03-PLAN.md (D-12/FA-06): the seam's alias selector reads Ledger.by_alias — a read-only
    # projection, never Ledger.append() — to resolve which wiring an alias names. No promotion
    # verb is defined here (test_no_promotion_verb_is_defined_outside_tests still scans this
    # file), so this exemption narrows only the import-site check, not the promotion-verb one.
    "seam/selectors.py",
)

_PROMOTION_VERB_NAMES = frozenset({"promote", "promote_next", "promote_now", "rollback"})


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
    all_findings: list[_Finding] = []
    for path in _scanned_files():
        all_findings.extend(_promotion_verb_findings(path))

    assert all_findings == [], (
        "a promotion verb (promote/promote_next/promote_now/rollback) is defined outside the "
        "test suite — this means the measurement-gated promotion path has started to exist. "
        "Update .planning/phases/02-falsifier-gate/02-MACH-09-POSTURE.md in the same change "
        f"rather than relaxing this test: {all_findings}"
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
