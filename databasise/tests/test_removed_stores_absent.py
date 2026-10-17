"""Phase 10 D-15: the unwired lexical store, the blob store and the artifact registry are removed.

STOR-13 (blob digest validation) and STOR-14 (lexical AND query) are met by removal (TOOL-17's
"removed" branch): neither store exists, so no digest path or lexical query can misbehave. These
tests fail if any module comes back or anything imports one again. The 17-member Effect
vocabulary is unchanged, so CONTRACT §2 is not amended.
"""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path
from typing import get_args

import databasise
from databasise.parts.schema import Effect

_ROOT = Path(databasise.__file__).resolve().parent
_REMOVED = ("databasise.stores.blob", "databasise.stores.lexical", "databasise.registry_artifact")
_SELF = Path(__file__).resolve()


def _scanned_sources() -> list[Path]:
    out = []
    for path in _ROOT.rglob("*.py"):
        rel = path.relative_to(_ROOT)
        parts = rel.parts
        if parts[0] in (".venv", "evidence") or "__pycache__" in parts:
            continue
        if parts[:2] == ("tests", "fixtures") or any(p.endswith(".egg-info") for p in parts):
            continue
        if path.resolve() == _SELF:
            continue
        out.append(path)
    return out


def _module_of(path: Path) -> str:
    rel = path.relative_to(_ROOT).with_suffix("")
    names = ["databasise", *rel.parts]
    if names[-1] == "__init__":
        names.pop()
    return ".".join(names)


def _is_removed(name: str) -> bool:
    return any(name == r or name.startswith(r + ".") for r in _REMOVED)


def _imported_names(path: Path) -> list[str]:
    """Every absolute module name an import in ``path`` resolves to, relative forms included."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    module = _module_of(path)
    package = module if path.name == "__init__.py" else module.rpartition(".")[0]
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base_parts = package.split(".")
                base_parts = base_parts[: len(base_parts) - (node.level - 1)]
                base = ".".join(base_parts + ([node.module] if node.module else []))
            else:
                base = node.module or ""
            names.append(base)
            # `from databasise.stores import blob` names the module through the alias.
            names.extend(f"{base}.{alias.name}" for alias in node.names)
    return names


def test_removed_store_modules_do_not_exist():
    assert not (_ROOT / "stores" / "blob.py").exists()
    assert not (_ROOT / "stores" / "lexical.py").exists()
    assert not (_ROOT / "registry_artifact").exists()


def test_no_module_imports_a_removed_store():
    offenders = [
        f"{path.relative_to(_ROOT)}: {name}"
        for path in _scanned_sources()
        for name in _imported_names(path)
        if _is_removed(name)
    ]
    assert offenders == []


_FORBIDDEN_TEXT = (
    *_REMOVED,
    "ArtifactRegistry",
    "FilesystemBlobStore",
    "SqliteLexicalStore",
)


def test_no_source_names_a_removed_store():
    offenders = [
        f"{path.relative_to(_ROOT)}: {needle}"
        for path in _scanned_sources()
        for needle in _FORBIDDEN_TEXT
        if needle in path.read_text(encoding="utf-8")
    ]
    assert offenders == []


def test_pyproject_does_not_package_the_artifact_registry():
    pyproject = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert "databasise.registry_artifact" not in pyproject["tool"]["setuptools"]["packages"]


def test_effect_vocabulary_keeps_all_17_members():
    effects = get_args(Effect)
    assert len(effects) == 17
    assert {"reads_lexical", "writes_lexical", "reads_blob", "writes_artifact"} <= set(effects)
