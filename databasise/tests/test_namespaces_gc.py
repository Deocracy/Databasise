"""STOR-15 (Phase 10 D-16): the operator GC CLI removes quarantined namespaces under the store lock."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from databasise.namespaces import derive_namespace


def _namespace(scope: str, corpus_id: str = "corpus-a") -> str:
    return derive_namespace(
        sa1_instance_hash="instance-1",
        sa2_chunker="chunker@1",
        sa2_extraction="extraction@1",
        sa2_embedding="embedding@1",
        corpus_id=corpus_id,
        space_id=None,
        scope=scope,
    )


def _run_cli(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "databasise.launcher.gc_namespaces", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def _populated_root(tmp_path: Path) -> tuple[Path, str, str]:
    root = tmp_path / "store"
    quarantined = _namespace("quarantined")
    shared = _namespace("shared")
    (root / quarantined / "graph.cozo").mkdir(parents=True)
    (root / quarantined / "graph.cozo" / "x").write_text("q")
    (root / shared).mkdir(parents=True)
    (root / shared / "x").write_text("s")
    return root, quarantined, shared


def test_cli_removes_a_quarantined_namespace_and_leaves_a_shared_sibling(tmp_path):
    root, quarantined, shared = _populated_root(tmp_path)

    result = _run_cli(tmp_path, "--store-root", str(root), quarantined)

    assert result.returncode == 0, result.stderr
    assert f"removed {quarantined}" in result.stdout
    assert not (root / quarantined).exists()
    assert (root / shared / "x").read_text() == "s"


def test_cli_reports_a_missing_namespace_as_absent(tmp_path):
    root, _, _ = _populated_root(tmp_path)
    missing = _namespace("quarantined", corpus_id="corpus-missing")

    result = _run_cli(tmp_path, "--store-root", str(root), missing)

    assert result.returncode == 0, result.stderr
    assert f"absent {missing}" in result.stdout


def test_cli_removes_two_tokens_in_one_call(tmp_path):
    root, first, _ = _populated_root(tmp_path)
    second = _namespace("quarantined", corpus_id="corpus-b")
    (root / second).mkdir()

    result = _run_cli(tmp_path, "--store-root", str(root), first, second)

    assert result.returncode == 0, result.stderr
    assert not (root / first).exists()
    assert not (root / second).exists()
