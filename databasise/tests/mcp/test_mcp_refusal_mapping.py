"""09-04-PLAN.md (SEAM-03, D-02): every refusal REST returns reaches an MCP client as
``CallToolResult(isError=True)`` whose single text content is the bare refusal JSON — including
refusals the SDK wraps (argument validation, models built in a tool body, the engine).

No ``__init__.py`` in this directory (same reason as ``test_dual_transport_parity.py``'s docstring);
the SDK is only ever reached through ``databasise.mcp._sdk.import_sdk``.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

try:
    import databasise.mcp  # noqa: F401 - import-for-availability-check only
except ImportError:
    pytest.skip("the `mcp` extra is not installed", allow_module_level=True)

from databasise.mcp import create_server
from databasise.mcp._sdk import import_sdk
from databasise.seam import refusals
from databasise.seam.refusals import SeamRefusalError, refusal_body
from databasise.tests.seam.test_rest_transport import _REFUSAL_FACTORIES

ToolError = import_sdk("mcp.server.mcpserver.exceptions").ToolError
mcp = import_sdk("mcp")

_FACTORY_CLASSES = [
    getattr(refusals, name)
    for name in refusals.__all__
    if getattr(refusals, name) in _REFUSAL_FACTORIES
]


def _server(tmp_path, workspace: str = "mcp-refusal-mapping"):
    return create_server(store_root=tmp_path, workspace=workspace)


async def _wire_call(server, tool: str, arguments: dict[str, Any]):
    async with mcp.Client(server) as client:
        return await client.call_tool(tool, arguments)


async def _raised(server, tool: str, arguments: dict[str, Any]) -> ToolError:
    with pytest.raises(ToolError) as exc_info:
        await server.call_tool(tool, arguments)
    return exc_info.value


def _bare_json(exc: BaseException) -> dict[str, Any]:
    text = str(exc)
    assert text.startswith("{"), text
    return json.loads(text)


async def test_ingest_empty_args_is_bare_json_with_is_error_over_the_wire(tmp_path):
    result = await _wire_call(_server(tmp_path), "ingest", {"args": {}})

    assert result.is_error is True
    assert len(result.content) == 1
    text = result.content[0].text
    assert text.startswith("{")
    body = json.loads(text)
    assert body["refusal_type"] == "AmbiguousIngestPayloadError"
    assert body["set_members"] == []


async def test_in_process_call_tool_raises_a_tool_error_whose_text_is_the_refusal_body(tmp_path):
    exc = await _raised(_server(tmp_path), "ingest", {"args": {}})

    expected = refusals.AmbiguousIngestPayloadError(set_members=[])
    assert str(exc) == json.dumps(refusal_body(expected))
    assert json.loads(str(exc)) == refusal_body(expected)


async def test_a_refusal_raised_during_argument_validation_is_found(tmp_path):
    alias = "sha256:" + "a" * 64
    exc = await _raised(
        _server(tmp_path),
        "query",
        {"args": {"query": {"text": "hello"}, "selector": {"alias": alias}}},
    )

    assert _bare_json(exc)["refusal_type"] == "ForbiddenSelectorInputError"


@pytest.mark.parametrize("exc_cls", _FACTORY_CLASSES, ids=lambda cls: cls.__name__)
async def test_every_catalogued_refusal_reaches_mcp_as_bare_json(tmp_path, exc_cls):
    server = _server(tmp_path)

    async def probe(name: str) -> dict[str, Any]:
        raise _REFUSAL_FACTORIES[next(c for c in _REFUSAL_FACTORIES if c.__name__ == name)]()

    server.add_tool(probe, name="refusal_probe")

    exc = await _raised(server, "refusal_probe", {"name": exc_cls.__name__})

    assert _bare_json(exc)["refusal_type"] == exc_cls.__name__
    assert issubclass(exc_cls, SeamRefusalError)


async def test_a_schema_error_carrying_no_refusal_keeps_the_sdk_text(tmp_path):
    exc = await _raised(_server(tmp_path), "ingest", {"args": {"text": 5}})

    assert str(exc).startswith("Error executing tool ingest: ")
    assert not str(exc).startswith("{")
