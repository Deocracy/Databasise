"""11-08 Task 2 (LRAG-07, D-08): the ``retry`` MCP tool reaches ``Databasise.retry_document``, the
same engine method ``POST /documents/{document_id}/retry`` reaches.

v1 is faked at ``run_corpus_op``: the status op reports the document's status and the ingest op
records its payload. No ``__init__.py`` in this directory (see ``test_dual_transport_parity.py``).
"""

from __future__ import annotations

import json
from typing import Any

import pytest

try:
    import databasise.mcp  # noqa: F401 - import-for-availability-check only
except ImportError:
    pytest.skip("the `mcp` extra is not installed", allow_module_level=True)

import databasise.seam.engine as engine_module
from databasise.mcp import create_server
from databasise.mcp._sdk import import_sdk
from databasise.parts_core.lightrag import full_ingest

ToolError = import_sdk("mcp.server.mcpserver.exceptions").ToolError
mcp = import_sdk("mcp")


@pytest.fixture
def fake_v1(monkeypatch) -> dict[str, Any]:
    state: dict[str, Any] = {"status": "processing", "ingests": []}

    def status(op, payload, **_kwargs):
        assert op == "status" and payload["document_id"] == "slow1"
        row = {"document_id": "slow1", "status": state["status"], "updated_at": "t", "error_message": None}
        return {"counts": {state["status"]: 1}, "documents": [row], "total": 1}

    def ingest(op, payload, **_kwargs):
        assert op == "ingest"
        state["ingests"].append(payload)
        return {"track_id": "original-track", "enqueued": 1, "usage": None}

    monkeypatch.setattr(engine_module, "run_corpus_op", status)
    monkeypatch.setattr(full_ingest, "run_corpus_op", ingest)
    return state


async def test_the_retry_tool_reprocesses_only_the_named_interrupted_document(tmp_path, fake_v1):
    server = create_server(store_root=tmp_path, workspace="retry-tool")
    assert "retry" in [tool.name for tool in await server.list_tools()]

    async with mcp.Client(server) as client:
        result = await client.call_tool("retry", {"args": {"document_id": "slow1"}})

    assert result.is_error is False, result.content
    job = json.loads(result.content[0].text)
    assert (job["job_id"], job["enqueued"]) == ("original-track", 1)
    [payload] = fake_v1["ingests"]
    assert payload["retry_doc_ids"] == ["slow1"]
    assert payload["documents"] == []


async def test_retrying_a_processed_document_is_a_named_refusal(tmp_path, fake_v1):
    fake_v1["status"] = "processed"
    server = create_server(store_root=tmp_path, workspace="retry-tool")

    with pytest.raises(ToolError) as raised:
        await server.call_tool("retry", {"args": {"document_id": "slow1"}})

    body = json.loads(str(raised.value))
    assert (body["refusal_type"], body["document_id"], body["status"]) == (
        "DocumentNotInterruptedError",
        "slow1",
        "processed",
    )
    assert fake_v1["ingests"] == []
