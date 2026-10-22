"""16-11 (CONN-14, D-18, D-19): GET /log tails the launcher's log file, only under ``--operator`` and
``--log-file``; each line is redacted at read time.

New API is reached through ``getattr``/help text so that, before the change, each node fails by a plain
``AssertionError`` rather than a ``TypeError`` or a launch timeout (16-RESEARCH Pitfall 1).
"""

from __future__ import annotations

import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

pytest.importorskip("fastapi")

from databasise.launcher import serve_rest
from databasise.launcher.serve_rest import build_app, build_parser
from fastapi.testclient import TestClient

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _args(root: Path, *extra: str):
    return build_parser().parse_args(
        ["--no-clients", "--store-root", str(root), "--workspace", "ws", *extra]
    )


def _client(root: Path, *extra: str) -> TestClient:
    return TestClient(build_app(_args(root, *extra), None), base_url="http://127.0.0.1")


def test_log_tails_the_launcher_log_and_is_404_without_both_flags(tmp_path):
    assert "--log-file" in build_parser().format_help()
    log = tmp_path / "server.log"
    lines = [f"line {i:04d}" for i in range(1200)]
    lines[-1] += " https://provider.example/v1?key=sk-test-abc"
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")

    both = _client(tmp_path / "both", "--operator", "--log-file", str(log))
    got = both.get("/log", params={"limit": 10})
    assert got.status_code == 200
    tail = got.json()["lines"]
    assert [line[:9] for line in tail] == [f"line {i:04d}" for i in range(1190, 1200)]
    assert "<url>" in tail[-1]
    assert "https://" not in tail[-1] and "sk-test-abc" not in tail[-1]
    assert both.get("/log", params={"limit": 0}).status_code == 422
    assert both.get("/log", params={"limit": 1001}).status_code == 422
    assert len(both.get("/log").json()["lines"]) == 100

    assert _client(tmp_path / "no-file", "--operator").get("/log").status_code == 404
    assert _client(tmp_path / "no-operator", "--log-file", str(log)).get("/log").status_code == 404
