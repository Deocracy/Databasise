"""Subprocess tests of the installed ``databasise-rest`` launcher (08-01, RUN-05..07, D-11).

The names this phase creates (``databasise.launcher`` ...) are imported inside the tests that use
them, never at module top, and processes start with the inherited environment, so the file still
collects on the pre-phase tree (plan 08-10's fail-first check).
"""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

_STUB_LLM_KEY = "stub-llm-key"
_STUB_HOST = "http://127.0.0.1:9/v1"


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _write_stub_env(path: Path, *, omit: tuple[str, ...] = (), extra: str = "") -> Path:
    values = {
        "LLM_BINDING_HOST": _STUB_HOST,
        "LLM_MODEL": "stub-llm",
        "LLM_BINDING_API_KEY": _STUB_LLM_KEY,
        "EMBEDDING_BINDING_HOST": _STUB_HOST,
        "EMBEDDING_MODEL": "stub-embedding",
        "EMBEDDING_BINDING_API_KEY": "stub-embedding-key",
    }
    lines = [f"{key}={value}" for key, value in values.items() if key not in omit]
    path.write_text("\n".join(lines) + "\n" + extra, encoding="utf-8")
    return path


@pytest.fixture
def launch(tmp_path):
    procs: list[subprocess.Popen] = []

    def _launch(script_name: str, *args: str) -> subprocess.Popen:
        n = len(procs)
        with open(tmp_path / f"proc{n}.out", "wb") as out, open(tmp_path / f"proc{n}.err", "wb") as err:
            proc = subprocess.Popen(
                [str(Path(sys.executable).parent / script_name), *args],
                stdin=subprocess.DEVNULL,
                stdout=out,
                stderr=err,
            )
        proc.stderr_path = tmp_path / f"proc{n}.err"  # type: ignore[attr-defined]
        proc.stdout_path = tmp_path / f"proc{n}.out"  # type: ignore[attr-defined]
        procs.append(proc)
        return proc

    yield _launch
    for proc in procs:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(15)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()


def _stderr(proc: subprocess.Popen) -> str:
    return proc.stderr_path.read_text(encoding="utf-8")  # type: ignore[attr-defined]


def _wait_ready(port: int, proc: subprocess.Popen, timeout: float = 60) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            pytest.fail(f"launcher exited {proc.returncode} before serving: {_stderr(proc)}")
        try:
            httpx.get(f"http://127.0.0.1:{port}/openapi.json", timeout=2)
            return
        except httpx.HTTPError:
            time.sleep(0.5)
    pytest.fail("launcher did not become ready in time")


def test_databasise_rest_serves_health_from_the_installed_script(launch, tmp_path):
    root = tmp_path / "store"
    port = _free_port()
    env_file = _write_stub_env(tmp_path / "stub.env")
    proc = launch(
        "databasise-rest",
        "--store-root", str(root),
        "--workspace", "w",
        "--port", str(port),
        "--env-file", str(env_file),
    )  # fmt: skip
    _wait_ready(port, proc)
    assert httpx.get(f"http://127.0.0.1:{port}/health", timeout=90).status_code == 200
    assert (root / ".engine.lock").read_text() == str(proc.pid)


def test_missing_env_keys_stop_startup_naming_every_missing_key(launch, tmp_path):
    env_file = _write_stub_env(tmp_path / "stub.env", omit=("LLM_MODEL", "EMBEDDING_MODEL"))
    proc = launch(
        "databasise-rest",
        "--store-root", str(tmp_path / "store"),
        "--port", str(_free_port()),
        "--env-file", str(env_file),
    )  # fmt: skip
    assert proc.wait(60) == 1
    err = _stderr(proc)
    assert "LLM_MODEL" in err and "EMBEDDING_MODEL" in err
    assert _STUB_LLM_KEY not in err and _STUB_HOST not in err


def test_malformed_routing_body_is_refused_without_echoing_it(launch, tmp_path):
    env_file = _write_stub_env(
        tmp_path / "stub.env", extra="OPENAI_LLM_EXTRA_BODY={provider:{order:[stub-route-marker]}}\n"
    )
    proc = launch(
        "databasise-rest",
        "--store-root", str(tmp_path / "store"),
        "--port", str(_free_port()),
        "--env-file", str(env_file),
    )  # fmt: skip
    assert proc.wait(60) == 1
    err = _stderr(proc)
    assert "OPENAI_LLM_EXTRA_BODY" in err
    for leaked in ("stub-route-marker", _STUB_LLM_KEY, _STUB_HOST):
        assert leaked not in err


def test_engine_argument_defaults_are_the_populated_store_on_loopback():
    from databasise.launcher import serve_rest
    from databasise.parity import import_index

    args = serve_rest.build_parser().parse_args(["--no-clients"])
    assert args.store_root == import_index.DEFAULT_STORE_ROOT
    assert args.store_root.parts[-2:] == ("v1", ".parity_v2_store")
    assert args.workspace == "shared-4fab18fef508b7bc3dda1cc2d8f12e36"
    assert args.host == "127.0.0.1"
    assert args.port == 8000
    assert args.env_file is None
    assert args.workers == 1


def test_env_file_is_required_without_no_clients(launch, tmp_path):
    proc = launch("databasise-rest", "--store-root", str(tmp_path / "store"))
    assert proc.wait(60) == 2
    assert "--env-file" in _stderr(proc)


def test_workers_above_one_is_refused_naming_the_store_lock(launch, tmp_path):
    root = tmp_path / "fresh-store"
    proc = launch("databasise-rest", "--store-root", str(root), "--no-clients", "--workers", "2")
    assert proc.wait(60) == 2
    assert "store lock" in _stderr(proc)
    assert not (root / ".engine.lock").exists()


def test_both_console_scripts_are_installed_entry_points():
    from importlib.metadata import entry_points

    scripts = {ep.name: ep.value for ep in entry_points(group="console_scripts")}
    assert scripts["databasise-rest"] == "databasise.launcher.serve_rest:main"
    assert scripts["databasise-mcp"] == "databasise.launcher.serve_mcp:main"


@pytest.mark.parametrize("module", ["databasise.launcher.serve_rest", "databasise.launcher.serve_mcp"])
def test_python_m_modules_print_help(module):
    result = subprocess.run(
        [sys.executable, "-m", module, "--help"], capture_output=True, text=True, timeout=120, check=False
    )
    assert result.returncode == 0, result.stderr
    assert "--store-root" in result.stdout


async def test_databasise_mcp_stdio_lists_the_in_process_tool_set(tmp_path):
    from databasise.foreign._mcp_sdk_guard import import_real_mcp
    from databasise.mcp import TOOL_NAMES, create_server

    mcp = import_real_mcp("mcp")
    stdio = import_real_mcp("mcp.client.stdio")
    params = mcp.StdioServerParameters(
        command=str(Path(sys.executable).parent / "databasise-mcp"),
        args=["--transport", "stdio", "--store-root", str(tmp_path / "root_a"), "--workspace", "w", "--no-clients"],
    )
    async with stdio.stdio_client(params) as (read, write), mcp.ClientSession(read, write) as session:
        await session.initialize()
        over_stdio = sorted(tool.name for tool in (await session.list_tools()).tools)
    in_process = sorted(
        tool.name for tool in await create_server(store_root=tmp_path / "root_b", workspace="w").list_tools()
    )
    assert over_stdio == in_process == sorted(TOOL_NAMES)


@pytest.mark.parametrize("transport", ["stdio", "sse", "streamable-http"])
def test_databasise_mcp_passes_each_transport_to_the_server_run_method(transport, tmp_path, monkeypatch):
    from databasise.launcher import serve_mcp
    from databasise.mcp import create_server

    calls: list[tuple] = []
    server_cls = type(create_server(store_root=tmp_path / "probe", workspace="w"))
    monkeypatch.setattr(server_cls, "run", lambda self, name, **kwargs: calls.append((name, kwargs)))
    argv = [
        "--transport", transport,
        "--store-root", str(tmp_path / "root"),
        "--workspace", "w",
        "--no-clients",
        "--port", "8123",
    ]  # fmt: skip
    assert serve_mcp.main(argv) == 0
    expected = {} if transport == "stdio" else {"host": "127.0.0.1", "port": 8123}
    assert calls == [(transport, expected)]


def test_example_mcp_config_invokes_databasise_mcp_over_stdio():
    example = Path(__file__).resolve().parents[2] / "examples" / "mcp-client.stdio.json"
    entry = json.loads(example.read_text(encoding="utf-8"))["mcpServers"]["databasise"]
    args = entry["args"]
    assert entry["command"].endswith("databasise-mcp")
    assert args[args.index("--transport") + 1] == "stdio"
    for flag in ("--store-root", "--env-file"):
        assert args[args.index(flag) + 1].startswith("/")


def test_second_launcher_on_a_held_store_root_exits_with_the_store_lock_error(launch, tmp_path):
    root = tmp_path / "store"
    port_a = _free_port()
    env_file = _write_stub_env(tmp_path / "stub.env")
    first = launch(
        "databasise-rest",
        "--store-root", str(root),
        "--workspace", "w",
        "--port", str(port_a),
        "--env-file", str(env_file),
    )  # fmt: skip
    _wait_ready(port_a, first)
    second_rest = launch(
        "databasise-rest", "--store-root", str(root), "--workspace", "w", "--port", str(_free_port()), "--no-clients"
    )
    second_mcp = launch(
        "databasise-mcp", "--transport", "stdio", "--store-root", str(root), "--workspace", "w", "--no-clients"
    )
    for refused in (second_rest, second_mcp):
        assert refused.wait(30) not in (0, None)
        err = _stderr(refused)
        assert str(root) in err and str(first.pid) in err
        assert "one engine process per store root" in err
    assert second_mcp.stdout_path.read_bytes() == b""  # type: ignore[attr-defined]
    assert httpx.get(f"http://127.0.0.1:{port_a}/health", timeout=90).status_code == 200


def test_a_released_store_root_can_be_launched_again(launch, tmp_path):
    root = tmp_path / "store"
    env_file = _write_stub_env(tmp_path / "stub.env")
    port_first = _free_port()
    first = launch(
        "databasise-rest", "--store-root", str(root), "--workspace", "w",
        "--port", str(port_first), "--env-file", str(env_file),
    )  # fmt: skip
    _wait_ready(port_first, first)
    first.terminate()
    first.wait(30)
    port = _free_port()
    again = launch(
        "databasise-rest", "--store-root", str(root), "--workspace", "w",
        "--port", str(port), "--env-file", str(env_file),
    )  # fmt: skip
    _wait_ready(port, again)
    assert httpx.get(f"http://127.0.0.1:{port}/health", timeout=90).status_code == 200
