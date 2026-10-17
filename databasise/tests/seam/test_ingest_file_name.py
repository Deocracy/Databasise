"""09-09-PLAN.md Task 1 (SEAM-15, D-11): ``file_name`` and ``content_type`` are discarded at ingest,
and the DTO, the REST schema and the MCP schema all say so ("not stored")."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("fastapi")

import databasise.seam.corpus as corpus_module
from databasise.mcp import create_server
from databasise.seam.rest import create_app
from databasise.tests.seam._probes import inbox_files
from databasise.tests.seam.test_rest_corpus_endpoints import _make_registry
from fastapi.testclient import TestClient

_FIELDS = ("file_name", "content_type")


def _resolve(schema: dict[str, Any], defs: dict[str, Any]) -> dict[str, Any]:
    ref = schema.get("$ref")
    return defs[ref.rsplit("/", 1)[-1]] if ref else schema


def test_openapi_ingest_document_fields_say_not_stored(store_root):
    app = create_app(store_root=store_root, workspace="file-name-openapi", registry=_make_registry())
    properties = app.openapi()["components"]["schemas"]["IngestDocument"]["properties"]
    for field in _FIELDS:
        assert "not stored" in properties[field]["description"], field


async def test_mcp_ingest_tool_schema_fields_say_not_stored(tmp_path):
    server = create_server(store_root=tmp_path, workspace="file-name-mcp", registry=_make_registry())
    tool = next(t for t in await server.list_tools() if t.name == "ingest")
    schema = tool.input_schema
    defs = schema.get("$defs", {})
    args = _resolve(schema["properties"]["args"], defs) if "args" in schema.get("properties", {}) else schema
    for field in _FIELDS:
        assert "not stored" in args["properties"][field]["description"], field


def test_corpus_module_no_longer_claims_citation_carry_through():
    # whitespace collapsed: the stale sentence wraps across a source line break
    source = " ".join(Path(corpus_module.__file__).read_text(encoding="utf-8").split())
    assert "carried into the job payload for citation" not in source
    assert "built only from the server-minted" not in source


def test_empty_file_name_and_content_type_are_accepted(store_root):
    client = TestClient(create_app(store_root=store_root, workspace="file-name-empty", registry=_make_registry()))
    response = client.post("/documents", json={"document": {"text": "x", "file_name": "", "content_type": ""}})
    assert response.status_code == 200


def test_non_ascii_upload_filename_is_never_stored(store_root, tmp_path):
    client = TestClient(create_app(store_root=store_root, workspace="file-name-utf8", registry=_make_registry()))
    response = client.post(
        "/documents/upload",
        files={"file": ("résumé.pdf", b"raw pdf bytes", "application/pdf")},
    )
    assert response.status_code == 200
    written = inbox_files(store_root)
    assert len(written) == 1
    assert re.fullmatch(r"[0-9a-f]{32}\.bin", written[0].name)
    assert not [p for p in tmp_path.rglob("*") if p.name == "résumé.pdf"]
