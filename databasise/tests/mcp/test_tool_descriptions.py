"""TOOL-19 (15-07-PLAN.md): every MCP tool publishes a non-empty, plan-free description, the
published input schemas name no plan, and the package text states the real tool count.

See ``test_dual_transport_parity.py``'s module docstring for why this directory carries no
``__init__.py`` and why the SDK is not skipped with ``pytest.importorskip("mcp")``.
"""

from __future__ import annotations

import json
import re

import pytest

try:
    import databasise.mcp  # noqa: F401
except ImportError:
    pytest.skip("the `mcp` extra is not installed", allow_module_level=True)
from databasise.mcp import create_server
from databasise.mcp.tools import TOOL_NAMES

_PLAN_PATTERN = re.compile(r"PLAN\.md|Phase \d|_refusal_mapped|\b\d\d-\d\d\b")
_MODALITY_PATTERN = re.compile(r"lightrag|hipporag|naive|bypass|hybrid|codebase-memory", re.IGNORECASE)


async def _listed_tools(tmp_path):
    server = create_server(store_root=tmp_path, workspace="descriptions")
    return await server.list_tools()


async def test_every_tool_publishes_a_non_empty_description(tmp_path):
    tools = await _listed_tools(tmp_path)
    assert {tool.name for tool in tools} == set(TOOL_NAMES)
    empty = sorted(tool.name for tool in tools if not (tool.description or "").strip())
    assert empty == [], f"tools publishing an empty description: {empty}"


async def test_no_description_names_a_plan_or_a_phase(tmp_path):
    tools = await _listed_tools(tmp_path)
    offending = {
        tool.name: _PLAN_PATTERN.findall(tool.description or "")
        for tool in tools
        if _PLAN_PATTERN.search(tool.description or "")
    }
    assert offending == {}, f"descriptions naming a plan or phase: {offending}"


async def test_no_published_input_schema_names_a_plan(tmp_path):
    tools = await _listed_tools(tmp_path)
    offending = {
        tool.name: _PLAN_PATTERN.findall(json.dumps(tool.input_schema))
        for tool in tools
        if _PLAN_PATTERN.search(json.dumps(tool.input_schema))
    }
    assert offending == {}, f"input schemas naming a plan or phase: {offending}"


async def test_no_description_names_an_arm_or_a_part(tmp_path):
    tools = await _listed_tools(tmp_path)
    offending = {
        tool.name: _MODALITY_PATTERN.findall(tool.description or "")
        for tool in tools
        if _MODALITY_PATTERN.search(tool.description or "")
    }
    assert offending == {}, f"descriptions naming an arm, wiring or part: {offending}"
