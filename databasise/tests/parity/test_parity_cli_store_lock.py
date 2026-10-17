"""D-03 (RUN-07): the six parity entry points refuse while a launcher holds the default store root.

Each ``main()`` must take ``store_lock(import_index.DEFAULT_STORE_ROOT)`` before any work starts,
so a parity run can no longer open graph.cozo under a running launcher and fail later inside
RocksDB with no PID. The lock is held in-process here (flock refuses a second open of the lock
file even within one process). Every work function is replaced with one that raises, so a main
that skips the lock fails the test instead of touching a store, index or endpoint.
"""

from __future__ import annotations

import importlib
import os

import pytest
from databasise.parity import import_index
from databasise.store_lock import store_lock

_NOT_STARTED = "work started while the store root was held"
_LOCKED_IN_TASK_2 = pytest.mark.xfail(strict=True, reason="locked in Task 2")

# (module, argv, work functions that must never be reached)
_ENTRY_POINTS = [
    pytest.param("import_index", [], ["import_v1_index", "verify_import"], id="import_index"),
    pytest.param("build_hipporag_index", [], ["build_index"], id="build_hipporag_index"),
    pytest.param("run_arm", ["--arm", "naive", "--query", "q"], ["run_arm"], id="run_arm"),
    pytest.param("run_comparison", ["--arm", "naive"], ["_run_cli"], id="run_comparison", marks=_LOCKED_IN_TASK_2),
    pytest.param("run_cross_modality", [], ["run_cross_modality"], id="run_cross_modality", marks=_LOCKED_IN_TASK_2),
    pytest.param("storage_audit", ["--arm", "naive"], ["run_audit"], id="storage_audit", marks=_LOCKED_IN_TASK_2),
]


@pytest.mark.parametrize(("module_name", "argv", "work_functions"), _ENTRY_POINTS)
def test_parity_cli_refuses_while_the_store_root_is_held(
    module_name, argv, work_functions, tmp_path, monkeypatch, capsys
):
    module = importlib.import_module(f"databasise.parity.{module_name}")
    root = tmp_path / "store"
    monkeypatch.setattr(import_index, "DEFAULT_STORE_ROOT", root)

    def _boom(*_args, **_kwargs):
        raise AssertionError(_NOT_STARTED)

    for name in work_functions:
        monkeypatch.setattr(module, name, _boom)

    with store_lock(root):
        returncode = module.main(argv)

    assert returncode == 1
    err = capsys.readouterr().err
    assert str(root) in err
    assert str(os.getpid()) in err
