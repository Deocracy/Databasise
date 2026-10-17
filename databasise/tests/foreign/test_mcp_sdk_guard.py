"""RUN-04: ``mcp_sdk_is_installed()`` must see the real SDK however the interpreter is started, and
must still report False when only a project-internal ``mcp`` shadow is reachable."""

from __future__ import annotations

import importlib.metadata
import subprocess
import sys
from pathlib import Path

import pytest
from databasise.foreign import _mcp_sdk_guard
from databasise.foreign._mcp_sdk_guard import mcp_sdk_is_installed

_PROJECT_DIR = Path(__file__).resolve().parents[2]


def _sdk_distribution_installed() -> bool:
    try:
        importlib.metadata.version("mcp")
    except importlib.metadata.PackageNotFoundError:
        return False
    return True


requires_sdk = pytest.mark.skipif(
    not _sdk_distribution_installed(), reason="mcp distribution not installed"
)


@requires_sdk
def test_sdk_detected_from_inside_the_project_directory():
    # `-c` puts '' on sys.path; with cwd = databasise/ that resolves to the project's own mcp/ package.
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            ("from databasise.foreign._mcp_sdk_guard import mcp_sdk_is_installed; "
             "print(mcp_sdk_is_installed())"),
        ],
        cwd=_PROJECT_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "True"


def test_shadow_only_tree_reports_not_installed(tmp_path, monkeypatch):
    (tmp_path / "mcp").mkdir()
    (tmp_path / "mcp" / "__init__.py").write_text("")
    monkeypatch.setattr(_mcp_sdk_guard, "_PROJECT_ROOT", tmp_path.resolve())
    monkeypatch.setattr(sys, "path", [str(tmp_path)])
    assert mcp_sdk_is_installed() is False


@requires_sdk
def test_real_sdk_is_detected_in_process():
    assert mcp_sdk_is_installed() is True
