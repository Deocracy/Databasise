"""D-14's runnable v1-import-boundary check, plus D-14/CONTRACT §7's provenance check.

Two independent checks, both reported through the same ``main()`` exit status:

1. **Import boundary.** No module under ``databasise/`` (this checker's own source excepted —
   its forbidden-reference strings are held as data, see below) references v1's ``lightrag``
   package or the sibling ``v1/`` directory, in any of four syntactic forms (plain import,
   from-import, aliased import, dynamic ``importlib.import_module``/``__import__`` call whose
   argument is a string literal) plus a fifth non-import form: a string literal reaching into the
   sibling ``v1/`` directory by relative filesystem path. Detected by walking the AST
   (``ast.walk``), never by a text scan — a text scan catches the first two import forms and
   misses the aliased and dynamic ones.

2. **Provenance resolution.** Every module under ``databasise/stores/`` that declares a
   class-level ``upstream_ref`` names a path that exists on disk, relative to the repository
   root (the directory containing both ``databasise/`` and ``v1/``). A provenance record naming a
   file that is not there records nothing (D-14, CONTRACT §7).

Self-exclusion matters: this module necessarily holds the strings it forbids as data (in
``_FORBIDDEN_IMPORT_ROOTS`` and ``_FORBIDDEN_PATH_SEGMENT`` below), so a scan counting its own
constants would report a permanent false positive and train a reader to ignore the check.
``scan_tree`` therefore skips this file by resolved path, not by name — a reader can confirm the
exclusion is doing real work by grepping this file directly (see ``tests/test_import_boundary.py``
Test 5).

**Subprocess-entry-point exclusion (03-07-PLAN.md Task 1 deviation; extended by 05-01-PLAN.md
Task 1).** A small, explicitly named set of files under ``databasise/`` are, by design, never
imported by any ``databasise/`` module — they are leaf scripts launched only as a subprocess under
a *different* interpreter (v1's own ``uv``-managed venv), and their entire reason to exist is to
call into v1's ``lightrag`` package from inside that other interpreter
(``databasise/parity/v1_driver_script.py``'s own module docstring explains the split in full).
Scanning them for a forbidden ``import lightrag`` would flag intentional, load-bearing code as a
violation of a rule whose purpose — keep ``databasise/``'s own interpreter from ever importing v1
— they do not violate: nothing under ``databasise/`` imports them either.
``_SUBPROCESS_ENTRY_POINT_EXCLUSIONS`` names these files by resolved path, exactly like the
self-exclusion above, so the exception is auditable rather than a silent gap in the scan.
``v1_corpus_driver_script.py`` (``databasise/foreign/``) joined this list in 05-01-PLAN.md Task 1:
it serves the corpus-side write operations (ingest today; delete/status added by 05-03/05-04),
the write-capable sibling to ``v1_driver_script.py``'s read-only query side.

Import-line-scoped deliberately: only an actual ``import``/``from ... import`` statement or a
dynamic-import call is checked against ``lightrag``/``v1`` — never an arbitrary string anywhere in
the file. A docstring or an ``upstream_ref`` value legitimately names a v1 path in prose (e.g.
``upstream_ref = "v1/lightrag/kg/cozo_impl.py"``), and an unanchored search would flag that
attribution as a violation, inverting the rule into one that punishes the provenance D-14 requires.
"""

from __future__ import annotations

import argparse
import ast
import importlib
import inspect
import sys
from dataclasses import dataclass
from pathlib import Path

# Held as data, not executed — this is exactly what a self-scan would (wrongly) flag; see the
# module docstring's "Self-exclusion matters" note and tests/test_import_boundary.py Test 5.
_FORBIDDEN_IMPORT_ROOTS: tuple[str, ...] = ("lightrag", "v1")
_FORBIDDEN_PATH_SEGMENT = "../v1/"

_STORES_DIR_NAME = "stores"
_STORES_EXCLUDED_MODULES = frozenset({"__init__.py", "base.py"})

# Leaf scripts that intentionally import v1's ``lightrag`` package because they run under v1's own
# interpreter as a subprocess entry point, never as a Python import target of anything under
# ``databasise/`` — see the module docstring's "Subprocess-entry-point exclusion" note. Named here
# by path relative to the scanned root and matched by resolved path (like the self-exclusion), so a
# same-named file elsewhere is still scanned and the exception stays a short, explicit, auditable
# list rather than a silent gap in the scan.
_SUBPROCESS_ENTRY_POINT_EXCLUSIONS = (
    Path("parity") / "v1_driver_script.py",
    Path("foreign") / "v1_corpus_driver_script.py",
)

# A path whose parts (relative to the scanned root) start with "." or equal one of these is not part
# of the package: virtualenvs, build output and installed distributions.
_SKIPPED_DIR_NAMES = frozenset({"site-packages", "build", "dist"})


@dataclass(frozen=True)
class Violation:
    """One import-boundary or provenance defect: the file it was found in, its line number (1 for
    a provenance defect or an unparseable file's missing line), the offending reference, and which
    check (``"import-boundary"`` / ``"provenance"`` / ``"unparseable"``) found it.
    """

    path: str
    line: int
    reference: str
    kind: str


def _is_forbidden_module(name: str) -> bool:
    return any(name == root or name.startswith(f"{root}.") for root in _FORBIDDEN_IMPORT_ROOTS)


def _dynamic_import_target(node: ast.Call, import_module_names: frozenset[str] = frozenset()) -> str | None:
    """Return the string-literal first argument of an ``importlib.import_module(...)``,
    ``__import__(...)`` or ``import_module(...)`` call (the last when the file bound the name with
    ``from importlib import import_module [as x]``; ``import_module_names`` holds those local names),
    or ``None`` if ``node`` is none of those calls or its first argument is not a string literal (a
    dynamically-computed argument cannot be checked statically, and is out of this checker's scope).
    """
    func = node.func
    is_import_module = (
        isinstance(func, ast.Attribute)
        and func.attr == "import_module"
        and isinstance(func.value, ast.Name)
        and func.value.id == "importlib"
    )
    is_dunder_import = isinstance(func, ast.Name) and func.id in ({"__import__"} | import_module_names)
    if not (is_import_module or is_dunder_import):
        return None
    if not node.args:
        return None
    first = node.args[0]
    if isinstance(first, ast.Constant) and isinstance(first.value, str):
        return first.value
    return None


def scan_file(path: Path) -> list[Violation]:
    """Walk ``path``'s AST, reporting every forbidden import (plain, from, aliased, dynamic) and
    every string literal reaching into the sibling ``v1/`` directory by relative filesystem path.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (SyntaxError, UnicodeDecodeError, ValueError) as exc:
        return [Violation(str(path), getattr(exc, "lineno", None) or 1, f"{type(exc).__name__}: {exc}", "unparseable")]
    violations: list[Violation] = []
    import_module_names = frozenset(
        alias.asname or alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "importlib"
        for alias in node.names
        if alias.name == "import_module"
    )

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _is_forbidden_module(alias.name):
                    violations.append(Violation(str(path), node.lineno, alias.name, "import-boundary"))
        elif isinstance(node, ast.ImportFrom):
            if node.module and _is_forbidden_module(node.module):
                violations.append(Violation(str(path), node.lineno, node.module, "import-boundary"))
        elif isinstance(node, ast.Call):
            target = _dynamic_import_target(node, import_module_names)
            if target is not None and _is_forbidden_module(target):
                violations.append(Violation(str(path), node.lineno, target, "import-boundary"))
        elif (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and _FORBIDDEN_PATH_SEGMENT in node.value
        ):
            violations.append(Violation(str(path), node.lineno, node.value, "import-boundary"))

    return violations


def scan_tree(package_root: Path) -> list[Violation]:
    """Scan every ``.py`` file under ``package_root``, excluding this checker's own source file and
    the two subprocess entry points (compared by resolved path, not by name — see the module
    docstring) and any path with a hidden, ``site-packages``, ``build`` or ``dist`` part relative to
    ``package_root`` (never the absolute parts: a temp directory can sit under a hidden ancestor).
    """
    self_path = Path(__file__).resolve()
    excluded = {(package_root / rel).resolve() for rel in _SUBPROCESS_ENTRY_POINT_EXCLUSIONS}
    violations: list[Violation] = []
    for path in sorted(package_root.rglob("*.py")):
        parts = path.relative_to(package_root).parts
        if any(part.startswith(".") or part in _SKIPPED_DIR_NAMES for part in parts):
            continue
        resolved = path.resolve()
        if resolved == self_path or resolved in excluded:
            continue
        violations.extend(scan_file(path))
    return violations


def check_upstream_refs(package_root: Path, repo_root: Path) -> list[Violation]:
    """For every class defined in a ``databasise/stores/*.py`` module (excluding ``__init__.py``
    and the shared ``base.py`` lifecycle ABC) that declares a non-empty class-level
    ``upstream_ref``, assert the referenced path exists under ``repo_root``. A module declaring no
    ``upstream_ref`` at all (a new primitive with no v1 analog, e.g. a store module written fresh for v2)
    contributes no violation — this check only holds *declared* provenance to account, per its own
    docstring.
    """
    stores_dir = package_root / _STORES_DIR_NAME
    violations: list[Violation] = []
    for path in sorted(stores_dir.glob("*.py")):
        if path.name in _STORES_EXCLUDED_MODULES:
            continue
        module_name = f"databasise.{_STORES_DIR_NAME}.{path.stem}"
        module = importlib.import_module(module_name)
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if obj.__module__ != module_name:
                continue
            ref = getattr(obj, "upstream_ref", None)
            if not ref:
                continue
            target = repo_root / ref
            if not target.exists():
                violations.append(
                    Violation(str(path), 1, f"{obj.__qualname__}.upstream_ref={ref!r}", "provenance")
                )
    return violations


def _package_root() -> Path:
    return Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    """Run both checks over the real ``databasise/`` tree. Prints nothing and returns 0 when
    clean; otherwise prints one line per violation (file, line, reference) and returns 1. From an
    installed wheel there is no ``v1/`` beside the package: the provenance check is skipped, one
    stderr line says so, and the exit code follows the import-boundary result alone.
    """
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args(argv)
    package_root = _package_root()
    repo_root = package_root.parent

    violations = scan_tree(package_root)
    if (repo_root / "v1").is_dir():
        violations.extend(check_upstream_refs(package_root, repo_root))
    else:
        print("provenance not checked: no v1/ directory beside the package (installed wheel)", file=sys.stderr)

    if not violations:
        return 0

    for v in violations:
        print(f"{v.path}:{v.line}: [{v.kind}] {v.reference}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
