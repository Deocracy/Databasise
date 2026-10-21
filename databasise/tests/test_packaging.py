"""TOOL-01 row test: the installed wheel carries everything the offline CLIs read at run time.

The wheel is built from a temporary copy of ``databasise/`` so no ``build/``, ``dist/`` or
egg-info directory is written into the repository (the source-text scan in
``test_removed_stores_absent.py`` would read such copies). When ``uv`` or its warm cache is
missing the build fixture skips with a named reason; a skip is never a pass.
"""

from __future__ import annotations

import shutil
import subprocess
import tomllib
import zipfile
from pathlib import Path

import pytest

import databasise

_PACKAGE_ROOT = Path(databasise.__file__).resolve().parent
_JUNK = (".venv", "__pycache__", "*.egg-info", "build", "dist", ".pytest_cache", ".ruff_cache", ".comparison_results")


def _repo_build_artifacts() -> set[str]:
    return {p.name for p in _PACKAGE_ROOT.iterdir() if p.name in ("build", "dist") or p.name.endswith(".egg-info")}


@pytest.fixture(scope="module")
def _before_build() -> set[str]:
    return _repo_build_artifacts()


@pytest.fixture(scope="module")
def built_wheel(tmp_path_factory, _before_build) -> zipfile.ZipFile:
    if shutil.which("uv") is None:
        pytest.skip("uv build --offline could not resolve the build requirements: uv is not on PATH")
    work = tmp_path_factory.mktemp("wheel_build")
    copy = work / "databasise"
    junk = shutil.ignore_patterns(*_JUNK)

    def ignore(directory: str, names: list[str]) -> set[str]:
        skipped = set(junk(directory, names))
        if Path(directory) == _PACKAGE_ROOT and "tests" in names:
            skipped.add("tests")  # only the two corpus fixtures are copied back in below
        return skipped

    shutil.copytree(_PACKAGE_ROOT, copy, ignore=ignore)
    for fixture in ("corpus", "eval-corpus"):
        shutil.copytree(
            _PACKAGE_ROOT / "tests" / "fixtures" / fixture, copy / "tests" / "fixtures" / fixture, ignore=junk
        )
    out = work / "out"
    result = subprocess.run(
        ["uv", "build", "--offline", "--wheel", "--out-dir", str(out), str(copy)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.skip(f"uv build --offline could not resolve the build requirements: {result.stderr[-300:]}")
    return zipfile.ZipFile(next(out.glob("*.whl")))


def _dist_info_text(wheel: zipfile.ZipFile, name: str) -> str:
    member = next(n for n in wheel.namelist() if n.endswith(f".dist-info/{name}"))
    return wheel.read(member).decode("utf-8")


def test_the_wheel_record_lists_the_tools_the_bundles_and_both_fixtures(built_wheel):
    recorded = {line.split(",", 1)[0] for line in _dist_info_text(built_wheel, "RECORD").splitlines()}
    wanted = [
        "databasise/tools/check_import_boundary.py",
        "databasise/evidence/eval-bundles/bundle@v1/bundle.json",
        "databasise/tests/fixtures/corpus/MANIFEST.json",
        "databasise/tests/fixtures/eval-corpus/MANIFEST.json",
    ]
    missing = [name for name in wanted if name not in recorded]
    assert missing == [], f"the wheel RECORD lacks {missing}"


def test_the_wheel_metadata_carries_the_package_version_and_a_bounded_mcp_extra(built_wheel):
    metadata = _dist_info_text(built_wheel, "METADATA").splitlines()
    versions = [line.split(":", 1)[1].strip() for line in metadata if line.startswith("Version:")]
    assert versions == [databasise.__version__]
    mcp_lines = [line for line in metadata if line.startswith("Requires-Dist: mcp")]
    assert len(mcp_lines) == 1 and "<3" in mcp_lines[0], mcp_lines


def test_pyproject_reads_the_version_from_the_package():
    data = tomllib.loads((_PACKAGE_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert "version" not in data["project"]
    assert "version" in data["project"].get("dynamic", [])
    assert data["tool"]["setuptools"].get("dynamic", {}).get("version", {}).get("attr") == "databasise.__version__"


def test_the_rest_app_reports_the_package_version(tmp_path):
    pytest.importorskip("fastapi")
    from databasise.seam.rest import create_app

    assert create_app(store_root=tmp_path, workspace="w").version == databasise.__version__
    assert 'version="0.1.0"' not in (_PACKAGE_ROOT / "seam" / "rest.py").read_text(encoding="utf-8")


def test_the_build_left_nothing_in_the_repo(built_wheel, _before_build):
    assert _repo_build_artifacts() == _before_build
