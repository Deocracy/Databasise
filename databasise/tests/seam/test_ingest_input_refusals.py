"""09-03-PLAN.md Task 1 (SEAM-07, D-06, D-12): a malformed caller document id is refused by name
(``InvalidDocumentIdError``) on every ingest and delete entry point before any file is written or
any wiring runs; an oversized upload is a 422; only a blank ``document_id`` FORM field on
``/documents/upload`` means "absent" (the server mints an id)."""

from __future__ import annotations

import json
import re

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

import databasise.parts_core.lightrag.full_delete as full_delete_module
from databasise.mcp import create_server
from databasise.mcp._sdk import import_sdk
from databasise.seam.corpus import MAX_DOCUMENT_BYTES, generated_on_disk_name
from databasise.seam.refusals import InvalidDocumentIdError
from databasise.seam.rest import create_app
from databasise.tests.seam.test_rest_corpus_endpoints import _make_registry

ToolError = import_sdk("mcp.server.mcpserver.exceptions").ToolError

_BAD_IDS = ["../x", "a.b", "a\n"]
_HEX32 = re.compile(r"[0-9a-f]{32}")


@pytest.fixture
def client(store_root):
    app = create_app(store_root=store_root, workspace="ingest-input-refusals", registry=_make_registry())
    return TestClient(app)


def _inbox_files(store_root):
    # 11-05 (D-09): the legacy flat inbox and every per-workspace inbox tree.
    inboxes = [store_root / "corpus-inbox", *store_root.glob("*/corpus-inbox")]
    return sorted(p for inbox in inboxes for p in inbox.rglob("*") if p.is_file())


def _upload(client, **data):
    return client.post(
        "/documents/upload",
        files={"file": ("doc.txt", b"hello world", "text/plain")},
        data=data,
    )


def _tool_error_detail(exc: ToolError) -> dict:
    text = str(exc)
    return json.loads(text[text.index("{") :])


@pytest.mark.parametrize("bad", ["", "../x", "a.b", "a\n"])
def test_generated_on_disk_name_refuses_a_malformed_id_by_name(bad):
    with pytest.raises(InvalidDocumentIdError) as exc_info:
        generated_on_disk_name(bad)
    assert exc_info.value.document_id == bad


def test_generated_on_disk_name_accepts_a_token():
    assert generated_on_disk_name("a_kiss-for_corliss") == "a_kiss-for_corliss.bin"


def test_an_oversized_upload_is_a_422_oversized_document_error(client, store_root):
    response = client.post(
        "/documents/upload",
        files={"file": ("big.bin", b"x" * (MAX_DOCUMENT_BYTES + 1), "application/octet-stream")},
    )

    assert response.status_code == 422
    assert response.json()["refusal_type"] == "OversizedDocumentError"
    assert _inbox_files(store_root) == []


@pytest.mark.parametrize("bad", _BAD_IDS)
def test_post_documents_refuses_a_malformed_id_and_writes_nothing(client, store_root, bad):
    response = client.post("/documents", json={"document": {"text": "x", "document_id": bad}})

    assert response.status_code == 422, response.text
    assert response.json()["refusal_type"] == "InvalidDocumentIdError"
    assert _inbox_files(store_root) == []


@pytest.mark.parametrize("bad", _BAD_IDS)
def test_upload_refuses_a_malformed_id_and_writes_nothing(client, store_root, bad):
    response = _upload(client, document_id=bad)

    assert response.status_code == 422, response.text
    assert response.json()["refusal_type"] == "InvalidDocumentIdError"
    assert _inbox_files(store_root) == []


def test_a_blank_upload_form_field_is_absent_and_gets_a_minted_id(store_root):
    # 11-05 (D-09): each staged name is seen while its ingest node runs; none outlives its job.
    names: list[str] = []
    registry = _make_registry(on_ingest=lambda ctx: names.extend(p.name for p in _inbox_files(store_root)))
    client = TestClient(create_app(store_root=store_root, workspace="ingest-input-refusals", registry=registry))
    omitted = _upload(client)
    blank = _upload(client, document_id="")

    assert omitted.status_code == 200, omitted.text
    assert blank.status_code == 200, blank.text
    assert blank.json()["enqueued"] == omitted.json()["enqueued"] == 1
    assert len(names) == 2
    assert all(_HEX32.fullmatch(name.removesuffix(".txt")) for name in names), names
    assert _inbox_files(store_root) == []


def test_a_whitespace_upload_form_field_is_a_caller_id_and_refused(client, store_root):
    response = _upload(client, document_id="   ")

    assert response.status_code == 422
    assert response.json()["refusal_type"] == "InvalidDocumentIdError"
    assert _inbox_files(store_root) == []


def test_post_documents_refuses_a_caller_supplied_empty_id(client, store_root):
    response = client.post("/documents", json={"document": {"text": "x", "document_id": ""}})

    assert response.status_code == 422
    assert response.json()["refusal_type"] == "InvalidDocumentIdError"
    assert _inbox_files(store_root) == []


async def test_mcp_ingest_refuses_a_caller_supplied_empty_id(store_root):
    server = create_server(store_root=store_root, workspace="mcp-empty-id", registry=_make_registry())

    with pytest.raises(ToolError) as exc_info:
        await server.call_tool("ingest", {"args": {"text": "x", "document_id": ""}})

    assert _tool_error_detail(exc_info.value)["refusal_type"] == "InvalidDocumentIdError"
    assert _inbox_files(store_root) == []


async def test_mcp_ingest_refuses_a_path_like_id(store_root):
    server = create_server(store_root=store_root, workspace="mcp-bad-id", registry=_make_registry())

    with pytest.raises(ToolError) as exc_info:
        await server.call_tool("ingest", {"args": {"text": "x", "document_id": "../evil"}})

    assert _tool_error_detail(exc_info.value)["refusal_type"] == "InvalidDocumentIdError"
    assert _inbox_files(store_root) == []


@pytest.mark.parametrize("path", ["/documents/a.b", "/documents/a%0A"])
def test_delete_refuses_a_malformed_id_before_the_v1_delete_call(client, monkeypatch, path):
    calls: list[tuple] = []
    monkeypatch.setattr(full_delete_module, "run_corpus_op", lambda *a, **k: calls.append((a, k)))

    response = client.delete(path)

    assert response.status_code == 422, response.text
    assert response.json()["refusal_type"] == "InvalidDocumentIdError"
    assert calls == []


def test_a_refused_ingest_repeated_returns_the_same_body_and_leaves_the_inbox_empty(client, store_root):
    first = client.post("/documents", json={"document": {"text": "x", "document_id": "../x"}})
    second = client.post("/documents", json={"document": {"text": "x", "document_id": "../x"}})

    assert first.status_code == second.status_code == 422
    assert first.json() == second.json()
    assert _inbox_files(store_root) == []


@pytest.mark.parametrize("good", ["round-trip-doc", "a_kiss_for_corliss"])
def test_a_well_formed_id_still_ingests(client, good):
    response = client.post("/documents", json={"document": {"text": "x", "document_id": good}})

    assert response.status_code == 200, response.text
