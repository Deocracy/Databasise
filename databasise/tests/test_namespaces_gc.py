"""STOR-15 (Phase 10 D-16): the operator GC CLI removes quarantined namespaces under the store lock."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from databasise.namespaces import NamespaceGCError, derive_namespace, gc_namespace
from databasise.store_lock import store_lock


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


# --- Task 2: gc_namespace reports failures by name; the CLI refuses before removing anything ---


def test_gc_namespace_raises_naming_the_namespace_when_a_subdirectory_is_read_only(tmp_path):
    if os.geteuid() == 0:
        pytest.skip("root ignores directory write permission")
    namespace = _namespace("quarantined")
    sub = tmp_path / namespace / "sub"
    sub.mkdir(parents=True)
    (sub / "file").write_text("x")
    sub.chmod(0o555)
    try:
        with pytest.raises(NamespaceGCError) as excinfo:
            gc_namespace(tmp_path, namespace)
        assert excinfo.value.namespace == namespace
        assert excinfo.value.reason == "PermissionError"
        assert namespace in str(excinfo.value)
    finally:
        sub.chmod(0o755)


def test_gc_namespace_on_a_missing_directory_returns_none(tmp_path):
    assert gc_namespace(tmp_path, _namespace("quarantined")) is None


def test_gc_namespace_refuses_a_symlinked_namespace_and_leaves_the_target_intact(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    (target / "file").write_text("keep")
    root = tmp_path / "store"
    root.mkdir()
    namespace = _namespace("quarantined")
    (root / namespace).symlink_to(target, target_is_directory=True)

    with pytest.raises(NamespaceGCError) as excinfo:
        gc_namespace(root, namespace)

    assert excinfo.value.namespace == namespace
    assert (target / "file").read_text() == "keep"


@pytest.mark.parametrize("token", ["shared-abc", "../x", "a/b", "quarantined-../x"])
def test_cli_refuses_a_token_and_removes_nothing(tmp_path, token):
    root, quarantined, shared = _populated_root(tmp_path)

    result = _run_cli(tmp_path, "--store-root", str(root), token)

    assert result.returncode == 1
    assert len(result.stderr.strip().splitlines()) == 1
    assert token in result.stderr
    assert (root / quarantined / "graph.cozo" / "x").exists()
    assert (root / shared / "x").exists()


def test_cli_validates_every_token_before_removing_any(tmp_path):
    root, quarantined, shared = _populated_root(tmp_path)

    result = _run_cli(tmp_path, "--store-root", str(root), quarantined, shared)

    assert result.returncode == 1
    assert shared in result.stderr
    assert (root / quarantined / "graph.cozo" / "x").exists()


def test_cli_refuses_while_another_process_holds_the_store_lock(tmp_path):
    root, quarantined, _ = _populated_root(tmp_path)

    with store_lock(root):
        result = _run_cli(tmp_path, "--store-root", str(root), quarantined)

    assert result.returncode == 1
    assert "one engine process per store root" in result.stderr
    assert str(os.getpid()) in result.stderr
    assert (root / quarantined / "graph.cozo" / "x").exists()


def test_cli_refuses_a_missing_store_root_without_creating_it(tmp_path):
    missing = tmp_path / "no-such-root"

    result = _run_cli(tmp_path, "--store-root", str(missing), _namespace("quarantined"))

    assert result.returncode == 2
    assert not missing.exists()


def test_cli_reports_a_removal_failure_by_name(tmp_path):
    if os.geteuid() == 0:
        pytest.skip("root ignores directory write permission")
    root, quarantined, _ = _populated_root(tmp_path)
    sub = root / quarantined / "graph.cozo"
    sub.chmod(0o555)
    try:
        result = _run_cli(tmp_path, "--store-root", str(root), quarantined)
    finally:
        sub.chmod(0o755)

    assert result.returncode == 1
    assert f"NamespaceGCError: could not remove namespace {quarantined!r}" in result.stderr
    assert len(result.stderr.strip().splitlines()) == 1
