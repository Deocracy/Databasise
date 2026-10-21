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

_HANG_SERVER = """\
import sys, time
sys.stdin.readline()
time.sleep(60)
"""


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
