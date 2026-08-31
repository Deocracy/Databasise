"""A structural pin on MACH-09's default-off measurement posture
(``.planning/phases/02-falsifier-gate/02-MACH-09-POSTURE.md``), mirroring
``databasise/tests/test_trusted_source_invariant.py``'s AST-scan shape: a scan over source
files with findings reported by file and line, not a bare boolean.

The posture record states that measurement-gated promotion is off by default for the
answer-level and index-side classes (RIG §F3.2), and that this holds today — without any
``measurement_posture`` configuration switch — because no measurement-gated promotion path
exists anywhere in ``databasise/``. This module is what keeps that claim true going forward:

1. **No non-test module imports the ledger.** ``databasise/ledger/ledger.py`` defines the
   append-only ledger; nothing outside ``databasise/tests/`` and ``databasise/ledger/`` itself
   may import it. ``databasise/ledger/`` is exempt for the same reason
   ``databasise/validator/parse.py`` is exempt in the trusted-source pin: it is the definition
   site, not a caller.
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
    and any bare ``import databasise.ledger[...]`` form — the two shapes a caller could use to
    reach ``Ledger``, ``LedgerRecord``, or the ``databasise.ledger`` module itself.
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
    all_findings: list[_Finding] = []
    for path in _scanned_files():
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
