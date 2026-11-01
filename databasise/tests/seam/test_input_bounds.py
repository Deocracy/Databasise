"""Length and bounds refusals (REST probe #2, #3, #4, #6; phase16 NEW-1; phase09 N-4, N-5; fuzz F7):
an oversize value is refused by name at the input boundary, never passed on to crash as ``OSError
ENAMETOOLONG``, sqlite's ``OverflowError`` or a quadratic scan.

(1) document id: must fit a 255-byte file name with its suffix, at most ``MAX_DOCUMENT_ID_CHARS``
    (``InvalidDocumentIdError``, no job recorded);
(2) evidence namespace: at most 128 characters (``InvalidEvidenceNamespaceError``);
(3) page offset: at most ``MAX_PAGE_OFFSET`` on every paged route (``PageBoundsError``);
(4) GET /log limit: 1..1000 refused as ``PageBoundsError`` like the other paged routes;
(5) query text: the document byte cap (``OversizedDocumentError``);
(6) compare: 40,000 selectors are duplicate-checked in well under a second.
"""

from __future__ import annotations

import json
import time

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from databasise.mcp import create_server
from databasise.mcp._sdk import import_sdk
from databasise.seam.compare import comparison_keys
from databasise.seam.corpus import (
    MAX_DOCUMENT_BYTES,
    MAX_DOCUMENT_ID_CHARS,
    MAX_PAGE_OFFSET,
    checked_page,
    generated_on_disk_name,
)
from databasise.seam.engine import Databasise
from databasise.seam.evidence import validate_evidence_namespace
from databasise.seam.refusals import (
    DuplicateComparisonKeyError,
    InvalidDocumentIdError,
    InvalidEvidenceNamespaceError,
    PageBoundsError,
)
from databasise.seam.rest import create_app
from databasise.seam.selectors import Selector
from databasise.tests.seam.test_rest_corpus_endpoints import _make_registry

ToolError = import_sdk("mcp.server.mcpserver.exceptions").ToolError

_HUGE_OFFSET = 2**64


@pytest.fixture
def client(store_root):
    return TestClient(create_app(store_root=store_root, workspace="bounds", registry=_make_registry()))


@pytest.fixture
def operator_client(store_root, tmp_path):
    log = tmp_path / "server.log"
    log.write_text("one\ntwo\n", encoding="utf-8")
    return TestClient(
        create_app(
            store_root=store_root, workspace="bounds-op", registry=_make_registry(), operator=True, log_path=log
        )
    )


def _refused(response, refusal_type: str) -> dict:
    assert response.status_code == 422, response.text
    body = response.json()
    assert body["refusal_type"] == refusal_type, body
    return body


# (1) document id length ------------------------------------------------------------------------- #


def test_document_id_cap_is_what_fits_a_255_byte_file_name_with_its_suffix():
    # NAME_MAX is 255: 251 chars fit with the 4-char default suffix (test_raw_upload_staging pins a
    # 251-char id with ".txt"); with the longest accepted suffix (".properties", 11) only 244 fit.
    assert MAX_DOCUMENT_ID_CHARS == 251
    assert generated_on_disk_name("a" * 251) == "a" * 251 + ".bin"
    assert generated_on_disk_name("a" * 244, ".properties") == "a" * 244 + ".properties"
    with pytest.raises(InvalidDocumentIdError) as exc_info:
        generated_on_disk_name("a" * 252)
    assert "251" in str(exc_info.value)
    with pytest.raises(InvalidDocumentIdError):
        generated_on_disk_name("a" * 245, ".properties")


def test_a_10000_char_upload_id_is_refused_by_name_and_records_no_job(client, monkeypatch):
    recorded: list[tuple] = []
    monkeypatch.setattr(Databasise, "_record_job", lambda self, *args: recorded.append(args))

    response = client.post(
        "/documents/upload", files={"file": ("a.txt", b"hello")}, data={"document_id": "a" * 10_000}
    )

    body = _refused(response, "InvalidDocumentIdError")
    assert len(body["document_id"]) < 300  # bounded echo, never the 10,000-char value
    assert recorded == []


# (2) evidence namespace length ------------------------------------------------------------------ #


def test_a_4096_char_namespace_is_refused_by_name_before_any_store(client):
    body = _refused(
        client.post("/evidence/resolve", json={"ref": "r", "namespace": "a" * 4096, "kind": "text_chunk"}),
        "InvalidEvidenceNamespaceError",
    )
    assert len(body["namespace"]) < 300
    validate_evidence_namespace("a" * 128)
    with pytest.raises(InvalidEvidenceNamespaceError):
        validate_evidence_namespace("a" * 129)


# (3) page offset ceiling ------------------------------------------------------------------------- #


def test_checked_page_refuses_an_offset_above_the_ceiling():
    assert MAX_PAGE_OFFSET == 2**31 - 1
    assert checked_page(10, MAX_PAGE_OFFSET).offset == MAX_PAGE_OFFSET
    with pytest.raises(PageBoundsError):
        checked_page(10, MAX_PAGE_OFFSET + 1)


def test_page_bounds_message_keeps_the_pinned_wording_and_names_the_ceiling():
    # 09-03-PLAN.md:182 pins "non-negative" (test_corpus_status.py); the ceiling is named as well.
    message = str(PageBoundsError(limit=10, offset=MAX_PAGE_OFFSET + 1))
    assert "non-negative" in message
    assert "2**31-1" in message


def test_rest_corpus_refuses_offset_2_pow_64_with_page_bounds_error(client):
    body = _refused(client.get(f"/corpus?offset={_HUGE_OFFSET}"), "PageBoundsError")
    assert body["offset"] == _HUGE_OFFSET


def test_rest_traces_refuses_offset_2_pow_64_with_page_bounds_error(operator_client):
    _refused(operator_client.get(f"/traces?offset={_HUGE_OFFSET}"), "PageBoundsError")


async def test_mcp_status_refuses_offset_2_pow_64_with_page_bounds_error(store_root):
    server = create_server(store_root=store_root, workspace="mcp-bounds", registry=_make_registry())
    with pytest.raises(ToolError) as exc_info:
        await server.call_tool("status", {"args": {"scope": "corpus", "offset": _HUGE_OFFSET}})
    text = str(exc_info.value)
    assert json.loads(text[text.index("{") :])["refusal_type"] == "PageBoundsError"


# (4) GET /log limit ------------------------------------------------------------------------------ #


@pytest.mark.parametrize("limit", [0, 1001, -1])
def test_log_limit_out_of_range_is_page_bounds_error(operator_client, limit):
    body = _refused(operator_client.get("/log", params={"limit": limit}), "PageBoundsError")
    assert body["limit"] == limit
    assert "detail" not in body


def test_log_limit_in_range_still_tails(operator_client):
    assert operator_client.get("/log", params={"limit": 1000}).json()["lines"] == ["one", "two"]


# (5) query text byte cap ------------------------------------------------------------------------- #


def test_oversized_query_text_is_refused_by_name(client):
    body = _refused(
        client.post("/query", json={"query": {"text": "a" * (MAX_DOCUMENT_BYTES + 1)}}), "OversizedDocumentError"
    )
    assert body["limit_bytes"] == MAX_DOCUMENT_BYTES
    assert body["actual_bytes"] == MAX_DOCUMENT_BYTES + 1


# (6) compare duplicate check is linear ----------------------------------------------------------- #


def test_40000_selectors_are_duplicate_checked_in_under_a_second():
    selectors = [Selector(alias=f"a{i}") for i in range(40_000)] + [Selector(alias="a0")]
    started = time.perf_counter()
    with pytest.raises(DuplicateComparisonKeyError) as exc_info:
        comparison_keys(selectors)
    assert time.perf_counter() - started < 1.0
    assert exc_info.value.key == "a0"
