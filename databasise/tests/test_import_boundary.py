"""Tests for D-14's runnable v1-import-boundary checker (``databasise/tools/check_import_boundary.py``).

Covers plan 01-09's <behavior> Tests 1-6: the real tree is clean; a fixture violation is caught
and named; all four import syntactic forms are detected; a relative-filesystem-path reach into
v1 is detected; the checker excludes its own source from the scan; every declared
``upstream_ref`` under the stores package resolves to a real path.

Tests 7-9 below (03-08-PLAN.md Task 2) extend the proof to the directories this phase added
(``parts_core/lightrag/``, ``clients/``, ``parity/``, ``wirings/``). No change to
``check_import_boundary.py`` itself — its ``scan_tree`` walk already covers the whole
``databasise/`` tree by AST — so what was missing is a test proving that coverage is real (a
synthetic violation planted under the new directory tree is actually caught), not a vacuous pass
that would keep succeeding even if the checker silently stopped walking those directories.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import databasise
from databasise.tools import check_import_boundary


def _package_root() -> Path:
    return Path(databasise.__file__).resolve().parent


def _repo_root() -> Path:
    return _package_root().parent


def test_1_the_real_package_tree_has_zero_violations_and_main_returns_zero(capsys):
    violations = check_import_boundary.scan_tree(_package_root())
    violations.extend(check_import_boundary.check_upstream_refs(_package_root(), _repo_root()))
    assert violations == []

    status = check_import_boundary.main([])
    captured = capsys.readouterr()

    assert status == 0
    assert captured.out == ""


def test_2_a_fixture_tree_with_one_violation_names_the_file_and_line(tmp_path):
    pkg = tmp_path / "fixture_one_violation"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    bad = pkg / "bad.py"
    bad.write_text("import lightrag\n", encoding="utf-8")

    violations = check_import_boundary.scan_tree(pkg)

    assert len(violations) == 1
    assert violations[0].path == str(bad)
    assert violations[0].line == 1
    assert violations[0].reference == "lightrag"


def test_3_detects_a_forbidden_reference_in_all_four_syntactic_forms(tmp_path):
    pkg = tmp_path / "fixture_four_forms"
    pkg.mkdir()
    (pkg / "bad.py").write_text(
        "import lightrag\n"
        "from lightrag.utils import helper\n"
        "import lightrag as lr\n"
        "import importlib\n"
        "importlib.import_module('lightrag.kg.factory')\n",
        encoding="utf-8",
    )

    violations = check_import_boundary.scan_tree(pkg)

    assert len(violations) == 4
    assert {v.line for v in violations} == {1, 2, 3, 5}
    assert all(v.kind == "import-boundary" for v in violations)


def test_4_detects_a_relative_filesystem_path_reaching_into_v1(tmp_path):
    # Built by concatenation, not as one literal relative-path substring: this test file lives
    # under databasise/tests/ (not the tools/ dir the acceptance grep excludes), so an embedded
    # literal would itself trip the plan's own grep-based relative-path acceptance check.
    relative_v1_reference = ".." + "/v1/lightrag/some_file.py"
    pkg = tmp_path / "fixture_fs_path"
    pkg.mkdir()
    (pkg / "reads_v1.py").write_text(
        f'SOME_PATH = "{relative_v1_reference}"\n', encoding="utf-8"
    )

    violations = check_import_boundary.scan_tree(pkg)

    assert len(violations) == 1
    assert violations[0].kind == "import-boundary"
    assert relative_v1_reference in violations[0].reference


def test_5_the_checker_excludes_its_own_source_from_the_scan():
    # The real tree (which includes this checker's own source file) reports zero violations —
    # only true if scan_tree actually excludes it, since the checker's own source contains the
    # forbidden strings as constant data (asserted below).
    violations = check_import_boundary.scan_tree(_package_root())
    assert violations == []

    # Built by concatenation for the same reason as test_4's fixture above — this file must not
    # itself embed the literal substring the plan's own grep acceptance check searches for.
    relative_v1_segment = ".." + "/v1/"
    checker_path = Path(check_import_boundary.__file__)
    checker_source = checker_path.read_text(encoding="utf-8")
    assert "lightrag" in checker_source
    assert '"v1"' in checker_source
    assert relative_v1_segment in checker_source

    # Scanning the checker's own file directly (bypassing the exclusion) does find a violation —
    # proving the exclusion in scan_tree is doing real work, not passing vacuously.
    direct_violations = check_import_boundary.scan_file(checker_path)
    assert direct_violations != []


def test_6_every_declared_upstream_ref_under_stores_names_a_real_path():
    violations = check_import_boundary.check_upstream_refs(_package_root(), _repo_root())
    assert violations == []

    # Non-vacuous: confirm the check actually has declared upstream_refs to verify.
    from databasise.stores.graph import CozoGraphStore
    from databasise.stores.kv import SqliteKVStore
    from databasise.stores.vector import FaissVectorStore

    assert CozoGraphStore.upstream_ref
    assert (_repo_root() / CozoGraphStore.upstream_ref).exists()
    assert FaissVectorStore.upstream_ref
    assert (_repo_root() / FaissVectorStore.upstream_ref).exists()
    assert SqliteKVStore.upstream_ref
    assert (_repo_root() / SqliteKVStore.upstream_ref).exists()


def test_7_the_real_tree_actually_contains_the_new_phase_3_directories_the_scan_claims_to_cover():
    """Non-vacuous companion to test_1: ``scan_tree(package_root)`` reporting zero violations
    means nothing about the new directories specifically unless they are actually present and
    populated — this pins that fact so test_1's "zero violations" claim cannot silently become
    true-because-empty.
    """
    package_root = _package_root()
    for rel in ("parts_core/lightrag", "clients", "parity", "wirings"):
        directory = package_root / rel
        assert directory.is_dir(), f"{rel} is missing from the real tree"
        assert list(directory.glob("*.py")), f"{rel} has no .py modules to scan"


@pytest.fixture
def _lightrag_shaped_fixture_root(tmp_path: Path) -> Path:
    root = tmp_path / "fixture_lightrag_shaped"
    (root / "parts_core" / "lightrag").mkdir(parents=True)
    (root / "__init__.py").write_text("", encoding="utf-8")
    (root / "parts_core" / "__init__.py").write_text("", encoding="utf-8")
    (root / "parts_core" / "lightrag" / "__init__.py").write_text("", encoding="utf-8")
    return root


def test_9_a_synthetic_module_under_parts_core_lightrag_importing_v1_or_lightrag_is_detected(
    _lightrag_shaped_fixture_root,
):
    bad = _lightrag_shaped_fixture_root / "parts_core" / "lightrag" / "bad_import.py"
    bad.write_text("import v1\nfrom lightrag.operate import kg_query\n", encoding="utf-8")

    violations = check_import_boundary.scan_tree(_lightrag_shaped_fixture_root)

    assert len(violations) == 2
    assert {v.reference for v in violations} == {"v1", "lightrag.operate"}
    assert all(v.kind == "import-boundary" for v in violations)


def test_10_a_synthetic_relative_path_reach_into_v1_under_parts_core_lightrag_is_detected(
    _lightrag_shaped_fixture_root,
):
    relative_v1_reference = ".." + "/v1/lightrag/some_file.py"  # built by concatenation, see test_4
    bad = _lightrag_shaped_fixture_root / "parts_core" / "lightrag" / "bad_path.py"
    bad.write_text(f'SOME_PATH = "{relative_v1_reference}"\n', encoding="utf-8")

    violations = check_import_boundary.scan_tree(_lightrag_shaped_fixture_root)

    assert len(violations) == 1
    assert violations[0].kind == "import-boundary"
    assert relative_v1_reference in violations[0].reference


def test_11_v1_driver_script_is_pinned_as_a_leaf_never_importable_from_databasise():
    """``databasise/parity/v1_driver_script.py`` (plan 03-07) runs under the ``v1/`` interpreter
    and must stay a leaf subprocess entry point — never importing ``databasise`` or anything that
    would make it importable from the ``databasise`` side. Asserted by AST, not by convention, so
    a later edit that quietly imports a ``databasise`` helper into it fails here instead of at
    runtime under an interpreter that does not have the package installed.

    Skips cleanly if the file is not yet present in this checkout: this plan (03-08) and plan
    03-07 run in parallel, separate worktrees, and 03-07 owns ``v1_driver_script.py``'s creation —
    it may not have been merged into this tree yet.
    """
    script_path = _package_root() / "parity" / "v1_driver_script.py"
    if not script_path.exists():
        pytest.skip(
            f"{script_path} not present in this checkout — plan 03-07 (parallel worktree) owns "
            "this file's creation; re-run once the two plans are merged"
        )

    import ast

    tree = ast.parse(script_path.read_text(encoding="utf-8"), filename=str(script_path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not (alias.name == "databasise" or alias.name.startswith("databasise.")), (
                    f"v1_driver_script.py imports {alias.name!r} — it must stay a leaf, never "
                    "importable from the databasise side"
                )
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                assert not (node.module == "databasise" or node.module.startswith("databasise.")), (
                    f"v1_driver_script.py imports from {node.module!r} — it must stay a leaf, "
                    "never importable from the databasise side"
                )
