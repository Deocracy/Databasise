"""LEDG-14 (14-10-PLAN.md, D-15): registry, schema, resolve, ledger, selector and alias-test
docstrings state current facts. Each banned phrase below was true once and is false now; the
test scans whitespace-normalised source text, so a re-wrapped line cannot hide one.

Standard library only, and every scanned file is located from this file's own path, so the test
also runs when this file alone is copied into a checkout of an older commit.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

_PKG = Path(__file__).resolve().parent.parent


def _norm(text: str) -> str:
    return " ".join(text.split())


def _source(relpath: str) -> str:
    return _norm((_PKG / relpath).read_text(encoding="utf-8"))


def _tree(relpath: str) -> ast.Module:
    return ast.parse((_PKG / relpath).read_text(encoding="utf-8"))


def _docstring(relpath: str, name: str | None = None) -> str:
    """The docstring of the module (``name`` None) or of the class or function ``name``."""
    tree = _tree(relpath)
    if name is None:
        return _norm(ast.get_docstring(tree) or "")
    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return _norm(ast.get_docstring(node) or "")
    raise AssertionError(f"{relpath} defines no {name}")


_STALE_IN_SOURCE = {
    "parts/registry.py": [
        "D-04's seven Phase-1 entries",
        "two remaining declaration-only",
        "wiring placeholders",
        "fifteen ported LightRAG parts",
        "five ported HippoRAG parts",
        "four executable",
        "awaits its Phase 3 port",
        "a later runner plan",
    ],
    "parts/schema.py": ["starts being consumed"],
    "wirings/resolve.py": [
        "needs all fifteen new components",
        "only the ``naive`` and ``bypass`` arms resolve",
        "does not necessarily",
    ],
    "ledger/ledger.py": [
        "Scope fence (Phase 1 only stands the table",
        "The registry is empty until Phase 7",
        "zero rows in every environment",
        "would stall the",
        "is this method's only caller",
        "are this method's only callers",
        "nothing in the live Phase 1 runner path calls",
    ],
    "tests/seam/test_alias_registry.py": ["promote path does not exist yet"],
}


@pytest.mark.parametrize("relpath", sorted(_STALE_IN_SOURCE))
def test_no_stale_phrase_remains(relpath: str) -> None:
    source = _source(relpath)
    found = [phrase for phrase in _STALE_IN_SOURCE[relpath] if phrase in source]
    assert not found, f"{relpath} still states stale text: {found}"


def test_no_stale_phrase_remains_in_resolve_alias_docstring() -> None:
    doc = _docstring("seam/selectors.py", "_resolve_alias")
    found = [p for p in ("Phase 7's promote path must append", "An empty registry") if p in doc]
    assert not found, f"_resolve_alias docstring still states stale text: {found}"


_COUNT = re.compile(
    r"\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|eighteen|\d+)\s+"
    r"(executable|ported|declaration-only|reference|parts?)\b",
    re.IGNORECASE,
)


@pytest.mark.parametrize("name", ["PartRegistry", "default_registry"])
def test_the_registry_points_at_keys_and_states_no_count(name: str) -> None:
    doc = _docstring("parts/registry.py", name)
    assert "keys()" in doc, f"{name} docstring does not point at keys(): {doc!r}"
    counted = [m.group(0) for m in _COUNT.finditer(doc)]
    assert not counted, f"{name} docstring states a part count: {counted}"


def test_the_resolve_module_docstring_names_its_functions() -> None:
    doc = _docstring("wirings/resolve.py")
    missing = [n for n in ("all_wirings", "load_wiring", "wiring_for_name") if n not in doc]
    assert not missing, f"wirings/resolve.py module docstring omits {missing}"


def test_the_selectors_docstring_keeps_all_wirings() -> None:
    assert "all_wirings()" in _docstring("seam/selectors.py")
