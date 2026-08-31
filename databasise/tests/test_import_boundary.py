"""Tests for D-14's runnable v1-import-boundary checker (``databasise/tools/check_import_boundary.py``).

Covers plan 01-09's <behavior> Tests 1-6: the real tree is clean; a fixture violation is caught
and named; all four import syntactic forms are detected; a relative-filesystem-path reach into
v1 is detected; the checker excludes its own source from the scan; every declared
``upstream_ref`` under the stores package resolves to a real path.
"""

from __future__ import annotations

from pathlib import Path

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
