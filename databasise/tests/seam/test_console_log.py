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


def test_log_file_flag_passes_a_file_log_config_only_when_given(tmp_path, monkeypatch):
    assert callable(getattr(serve_rest, "log_config_for", None))
    import uvicorn

    seen: list[dict] = []
    monkeypatch.setattr(uvicorn, "run", lambda *a, **kw: seen.append(kw))
    log = tmp_path / "server.log"
    base = ["--no-clients", "--store-root", str(tmp_path / "store"), "--operator"]
    assert serve_rest.main([*base, "--log-file", str(log)]) == 0
    config = seen[0]["log_config"]
    assert config["handlers"]["file"]["filename"] == str(log)
    assert "file" in config["loggers"]["uvicorn"]["handlers"]
    assert "file" in config["loggers"]["uvicorn.access"]["handlers"]
    assert "file" in config["root"]["handlers"]
    assert config["disable_existing_loggers"] is False
    assert serve_rest.main(base) == 0
    assert "log_config" not in seen[1]


def test_log_config_captures_engine_lines_and_tracebacks(tmp_path):
    assert callable(getattr(serve_rest, "log_config_for", None))
    log = tmp_path / "server.log"
    code = (
        "import logging, logging.config, sys\n"
        "import databasise.seam.engine\n"  # the engine logger exists before dictConfig runs
        "from databasise.launcher.serve_rest import log_config_for\n"
        "logging.config.dictConfig(log_config_for(sys.argv[1]))\n"
        "logging.getLogger('databasise.seam.engine').warning('engine line marker')\n"
        "try:\n"
        "    raise ValueError('boom marker')\n"
        "except ValueError:\n"
        "    logging.getLogger('uvicorn.error').exception('Exception in ASGI application')\n"
        "logging.shutdown()\n"
    )
    done = subprocess.run(
        [sys.executable, "-c", code, str(log)],
        env={"PYTHONPATH": str(_REPO_ROOT), "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    text = log.read_text(encoding="utf-8")
    assert "engine line marker" in text
    assert "Traceback" in text and "boom marker" in text


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def test_a_real_operator_launch_writes_lines_that_get_log_returns(tmp_path):
    assert callable(getattr(serve_rest, "log_config_for", None))
    log = tmp_path / "server.log"
    port = _free_port()
    err = tmp_path / "launch.err"
    with open(err, "wb") as err_file:
        proc = subprocess.Popen(
            [
                str(Path(sys.executable).parent / "databasise-rest"),
                "--operator", "--log-file", str(log),
                "--no-clients", "--store-root", str(tmp_path / "store"),
                "--workspace", "w", "--port", str(port),
            ],  # fmt: skip
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=err_file,
        )
    try:
        deadline = time.monotonic() + 60
        while True:
            assert proc.poll() is None, f"launcher exited {proc.returncode}: {err.read_text()}"
            assert time.monotonic() < deadline, "launcher did not become ready in time"
            try:
                httpx.get(f"http://127.0.0.1:{port}/openapi.json", timeout=2)
                break
            except httpx.HTTPError:
                time.sleep(0.5)
        assert httpx.get(f"http://127.0.0.1:{port}/info", timeout=10).status_code == 200
        got = httpx.get(f"http://127.0.0.1:{port}/log", params={"limit": 50}, timeout=10)
        assert got.status_code == 200
        assert any("GET /info" in line for line in got.json()["lines"])
    finally:
        proc.terminate()
        try:
            proc.wait(15)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
