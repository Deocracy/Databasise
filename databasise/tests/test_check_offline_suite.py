"""Tests for RUN-12's dual-invocation gate (``databasise/tools/check_offline_suite.py``) and the
offline guard in ``conftest.py``.

The gate tests exercise the pure parsing functions only; none of them starts a pytest subprocess.
"""

from __future__ import annotations

import socket

import pytest
from databasise.tools import check_offline_suite as gate

_NOT_INSTALLED_SKIP = (
    "SKIPPED [1] tests/x.py:138: binary not found ... or the 'mcp' extra is not installed "
    "(found=False)"
)
_REAL_DELETE_SKIP = (
    "SKIPPED [1] tests/seam/test_delete_document.py:256: set DATABASISE_RUN_REAL_DELETE=1 ..."
)


def test_parse_skip_lines_keeps_only_skipped_lines():
    output = f"noise\n{_NOT_INSTALLED_SKIP}\n  SKIPPED not at line start\n{_REAL_DELETE_SKIP}\n"
    assert gate.parse_skip_lines(output) == [_NOT_INSTALLED_SKIP, _REAL_DELETE_SKIP]


def test_a_not_installed_skip_is_contradictory_when_mcp_is_installed():
    assert gate.contradictory_skips([_NOT_INSTALLED_SKIP], mcp_installed=True) == [
        _NOT_INSTALLED_SKIP
    ]


def test_a_not_installed_skip_is_not_contradictory_when_mcp_is_missing():
    assert gate.contradictory_skips([_NOT_INSTALLED_SKIP], mcp_installed=False) == []


def test_an_environment_true_skip_is_never_contradictory():
    assert gate.contradictory_skips([_REAL_DELETE_SKIP], mcp_installed=True) == []


def test_summary_line_returns_the_final_pytest_summary():
    output = "....\nSKIPPED [1] a: b\n1207 passed, 1 skipped, 4 deselected in 190.12s (0:03:10)\n"
    assert gate.summary_line(output) == "1207 passed, 1 skipped, 4 deselected in 190.12s (0:03:10)"


def test_has_deselected_is_true_only_when_the_summary_says_deselected():
    assert gate.has_deselected("1207 passed, 4 deselected in 1s")
    assert not gate.has_deselected("1211 passed in 1s")


def test_the_offline_guard_refuses_a_non_loopback_connect():
    # 192.0.2.1 is TEST-NET-1 (never routed); the guard raises before any packet is sent.
    # conftest is not importable as a package here, so the error is matched by class name.
    with pytest.raises(RuntimeError, match="non-loopback") as excinfo:
        socket.create_connection(("192.0.2.1", 9), timeout=0.2)
    assert type(excinfo.value).__name__ == "NonLoopbackConnectionError"
    assert excinfo.value.address == ("192.0.2.1", 9)


def test_the_offline_guard_allows_loopback():
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        with socket.create_connection(server.getsockname(), timeout=2):
            pass
