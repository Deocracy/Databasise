"""15-04-PLAN.md (TOOL-18): the codebase-memory-mcp adapter against fake MCP servers launched over
the real stdio transport. Each fake server is a small script written to ``tmp_path``; the adapter
under test launches it exactly as it launches the real binary. Everything this phase adds is
resolved with ``getattr`` so the file collects (and fails by assertion) on the pre-fix code.
"""

from __future__ import annotations

import os
import stat
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest
from databasise.foreign import codebase_memory_mcp_adapter as adapter
from databasise.foreign._mcp_sdk_guard import mcp_sdk_is_installed

pytestmark = pytest.mark.skipif(not mcp_sdk_is_installed(), reason="the mcp extra is not installed")

# `databasise/mcp/` shadows the SDK's top-level name, so every fake server strips any sys.path
# entry that holds an `mcp` directory outside site-packages before it imports the SDK.
_PREAMBLE = """\
import os, sys
sys.path[:] = [
    p for p in sys.path
    if "site-packages" in p or not os.path.isdir(os.path.join(p or os.getcwd(), "mcp"))
]
"""

_ERROR_SERVER = (
    _PREAMBLE
    + """\
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

server = MCPServer("fake-cbm")

@server.tool(name="search_code")
def search_code() -> str:
    raise ToolError("the tool refused")

server.run()
"""
)

def _write_server(tmp_path: Path, name: str, body: str) -> str:
    path = tmp_path / name
    path.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return str(path)


def _captured(fn):
    try:
        fn()
    except BaseException as caught:  # noqa: BLE001 — the test asserts on the captured type
        return caught
    return None


def test_a_tool_error_reaches_the_caller_as_cbm_tool_call_error(tmp_path):
    binary = _write_server(tmp_path, "error_server.py", _ERROR_SERVER)
    caught = _captured(lambda: adapter.call_tool("search_code", {}, binary=binary, timeout=10))
    assert caught is not None, "call_tool returned instead of raising"
    assert type(caught).__name__ == "CbmToolCallError", repr(caught)


# ---------------------------------------------------------------------------
# Task 2: launch timeout, read-only allowlist, tagged items
# ---------------------------------------------------------------------------

# Never answers `initialize`; exits by itself after 15 s so a pre-fix unbounded handshake ends in
# a transport failure (an assertion), not a hung test run.
_HANG_SERVER = """\
import sys, time
sys.stdin.readline()
time.sleep(15)
"""

# Records that it was launched at all, then serves one read-only tool.
_LOGGING_SERVER_TEMPLATE = (
    _PREAMBLE
    + """\
with open({log!r}, "a") as handle:
    handle.write("launched\\n")

from mcp.server.mcpserver import MCPServer

server = MCPServer("fake-cbm")

@server.tool(name="search_code")
def search_code() -> str:
    return "ok"

server.run()
"""
)

_MUTATING_TOOLS = ("delete_project", "index_repository", "manage_adr", "ingest_traces")


def test_a_server_that_never_answers_initialize_times_out(tmp_path):
    binary = _write_server(tmp_path, "hang_server.py", _HANG_SERVER)
    started = time.monotonic()
    caught = _captured(lambda: adapter.call_tool("search_code", {}, binary=binary, timeout=2))
    elapsed = time.monotonic() - started
    assert type(caught).__name__ == "CbmToolTimeoutError", repr(caught)
    # The SDK waits about 2 s for the child to exit on teardown (15-RESEARCH 5.3, A6), so the
    # bound is timeout + 4, not timeout + 1.
    assert elapsed < 2 + 4, elapsed


def _logging_server(tmp_path: Path) -> tuple[str, Path]:
    log = tmp_path / "launches.log"
    return _write_server(tmp_path, "logging_server.py", _LOGGING_SERVER_TEMPLATE.format(log=str(log))), log


@pytest.mark.parametrize("tool_name", _MUTATING_TOOLS)
def test_a_mutating_tool_is_refused_before_any_launch(tmp_path, tool_name):
    binary, log = _logging_server(tmp_path)
    caught = _captured(lambda: adapter.call_tool(tool_name, {}, binary=binary, timeout=10))
    assert type(caught).__name__ == "CbmToolNotAllowedError", repr(caught)
    assert not log.exists(), "the server was launched"


def test_a_mutating_tool_is_refused_through_the_part_body(tmp_path, monkeypatch):
    import asyncio

    from databasise.parts.schema import NodeContext
    from databasise.parts_core import codebase_memory_mcp as cbm_module

    binary, log = _logging_server(tmp_path)
    # Point the default at the fake: the body passes no binary, and the real one must never run.
    monkeypatch.setattr(adapter, "DEFAULT_CBM_BINARY", binary)
    ctx = NodeContext(
        node_id="cbm", config={"tool": "delete_project", "arguments": {}}, inputs={}, stores={}
    )
    caught = _captured(lambda: asyncio.run(cbm_module.codebase_memory_mcp_body(ctx)))
    assert type(caught).__name__ == "CbmToolNotAllowedError", repr(caught)
    assert not log.exists(), "the server was launched"


def test_a_derived_finding_carries_a_list_derived_from_and_a_tagged_kind():
    item_kind_name = getattr(adapter, "item_kind_name", None)
    assert callable(item_kind_name), "item_kind_name is not defined"

    record = adapter.normalise_to_item_kind({"project": "p"}, "list_projects")
    assert isinstance(record["derived_from"], list), type(record["derived_from"]).__name__
    assert isinstance(record["kind"], dict) and len(record["kind"]) == 1, record["kind"]
    assert item_kind_name(record) == adapter.ITEM_KIND_DERIVED_FINDING

    snippet = adapter.normalise_to_item_kind({"file_path": "a.py", "source": "x"}, "get_code_snippet")
    assert item_kind_name(snippet) == adapter.ITEM_KIND_CODE_SNIPPET
    assert snippet["derived_from"] == []
