"""16-REVIEW-A WR-03: a bad ``--log-file`` is a one-line ``databasise:`` refusal before the store lock."""

from __future__ import annotations

import os

import pytest

from databasise.launcher import serve_rest


def _bad_paths(tmp_path):
    locked = tmp_path / "locked"
    locked.mkdir()
    locked.chmod(0o500)
    return {
        "missing parent": str(tmp_path / "missing-dir" / "server.log"),
        "directory": str(tmp_path),
        "empty string": "",
        "unwritable": str(locked / "server.log"),
    }


@pytest.mark.parametrize("case", ["missing parent", "directory", "empty string", "unwritable"])
def test_bad_log_file_is_refused_before_the_store_lock(tmp_path, monkeypatch, capsys, case):
    if case == "unwritable" and os.geteuid() == 0:
        pytest.skip("root can write a 0500 directory")

    def _never(_args):
        raise AssertionError("open_engine ran: the store lock was taken before --log-file was checked")

    monkeypatch.setattr(serve_rest, "open_engine", _never)
    argv = ["--store-root", str(tmp_path / "store"), "--no-clients", "--log-file", _bad_paths(tmp_path)[case]]
    assert serve_rest.main(argv) == 1
    err = capsys.readouterr().err
    assert err.startswith("databasise: --log-file ")
    assert err.count("\n") == 1 and "Traceback" not in err
    assert not (tmp_path / "store" / ".engine.lock").exists()
