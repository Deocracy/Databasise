"""RUN-01: the MCP tool roster and the live §18.5 coverage record (databasise/evidence/COVERAGE.md)
are cross-checked against each other, and the check is not vacuous.

The roster comes from a real server's ``list_tools()``, and the record's tools come from its own
transports column (``MCP (`<tool>` tool...)``), so neither side is a hand-kept list in this file.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# Same guard as test_tool_growth_invariant.py: importorskip("mcp") can see this repo's own
# databasise/mcp/ package instead of the SDK, so import databasise.mcp directly.
try:
    from databasise.mcp import create_server
except ImportError:
    pytest.skip("the `mcp` extra is not installed", allow_module_level=True)

_COVERAGE_PATH = Path(__file__).resolve().parents[2] / "evidence" / "COVERAGE.md"
_OPERATIONS_HEADER = "| operation | transports | plan |"
_MCP_TOOL_IN_TRANSPORTS = re.compile(r"MCP \(`([a-z_]+)` tool")


def _coverage_markdown() -> str:
    assert _COVERAGE_PATH.is_file(), f"§18.5 coverage record not found; expected at {_COVERAGE_PATH}"
    return _COVERAGE_PATH.read_text(encoding="utf-8")


def _mcp_tools_named_in_coverage(markdown: str) -> set[str]:
    lines = markdown.splitlines()
    start = next((i for i, line in enumerate(lines) if line.strip().startswith(_OPERATIONS_HEADER)), None)
    assert start is not None, f"COVERAGE.md has no §18.5 operations table ({_OPERATIONS_HEADER!r})"

    named: set[str] = set()
    for line in lines[start + 2 :]:
        stripped = line.strip()
        if not stripped.startswith("|"):
            break
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        named.update(_MCP_TOOL_IN_TRANSPORTS.findall(cells[1]))
    assert named, "no MCP tool is named in COVERAGE.md's §18.5 operations table"
    return named


async def _server_tool_names(server) -> set[str]:
    return {tool.name for tool in await server.list_tools()}


async def test_every_served_tool_has_a_coverage_row_and_every_coverage_row_names_a_served_tool(tmp_path):
    served = await _server_tool_names(create_server(store_root=tmp_path, workspace="run01-roster"))
    covered = _mcp_tools_named_in_coverage(_coverage_markdown())

    assert served - covered == set(), f"tools served with no COVERAGE.md row: {sorted(served - covered)}"
    assert covered - served == set(), f"COVERAGE.md rows naming no served tool: {sorted(covered - served)}"


async def test_a_served_tool_with_no_coverage_row_is_detected(tmp_path):
    """Non-vacuity: an extra tool on a temporary server, absent from the record, shows up as
    uncovered."""

    async def unlisted_probe_tool() -> dict:
        return {}

    server = create_server(store_root=tmp_path, workspace="run01-extra")
    server.add_tool(unlisted_probe_tool, name="unlisted_probe_tool")
    served = await _server_tool_names(server)
    covered = _mcp_tools_named_in_coverage(_coverage_markdown())

    assert "unlisted_probe_tool" in served
    assert served - covered == {"unlisted_probe_tool"}
