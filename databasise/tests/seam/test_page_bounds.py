"""09-03-PLAN.md Task 2 (SEAM-08, D-07): page limits and offsets are bounded on every path.
``limit`` outside 1..100 and a negative ``offset`` are refused by name (``PageSizeExceededError``
for the upper cap, ``PageBoundsError`` for the lower bounds), never clamped, and no refused input
reaches the v1 driver (``databasise.seam.engine.run_corpus_op``)."""

from __future__ import annotations

import json
from typing import Any

import pydantic
import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

import databasise.seam.engine as engine_module
from databasise.mcp import create_server
from databasise.mcp._sdk import import_sdk
from databasise.seam.corpus import MAX_PAGE_SIZE, Page, checked_page
from databasise.seam.engine import Databasise
from databasise.seam.refusals import PageBoundsError, PageSizeExceededError
from databasise.seam.rest import create_app
from databasise.tests.seam.test_rest_corpus_endpoints import _make_registry, _patch_status_and_health

ToolError = import_sdk("mcp.server.mcpserver.exceptions").ToolError


@pytest.fixture
def driver_calls(monkeypatch):
    """Patches the status driver and records every ``run_corpus_op`` call."""
    _patch_status_and_health(monkeypatch)
    delegate = engine_module.run_corpus_op
    calls: list[tuple] = []

    def _recording(op, payload, **kwargs):
        calls.append((op, payload))
        return delegate(op, payload, **kwargs)

    monkeypatch.setattr(engine_module, "run_corpus_op", _recording)
    return calls


@pytest.fixture
def client(store_root):
    return TestClient(create_app(store_root=store_root, workspace="page-bounds", registry=_make_registry()))


def _tool_error_detail(exc: ToolError) -> dict[str, Any]:
    text = str(exc)
    return json.loads(text[text.index("{") :])


@pytest.mark.parametrize(
    "path",
    [
        "/corpus?limit=0",
        "/corpus?limit=-1",
        "/corpus?limit=-5",
        "/corpus?offset=-1",
        "/jobs/job-abc?limit=0",
        "/jobs/job-abc?offset=-1",
    ],
)
def test_rest_refuses_an_out_of_range_page_with_page_bounds_error(client, driver_calls, path):
    response = client.get(path)

    assert response.status_code == 422, response.text
    body = response.json()
    assert body["refusal_type"] == "PageBoundsError"
    assert "detail" not in body
    assert driver_calls == []


@pytest.mark.parametrize(
    "args",
    [
        {"scope": "corpus", "limit": 0},
        {"scope": "corpus", "limit": -1},
        {"scope": "corpus", "offset": -1},
        {"scope": "job", "job_id": "job-abc", "limit": 0},
    ],
)
async def test_mcp_status_refuses_an_out_of_range_page_with_page_bounds_error(store_root, driver_calls, args):
    server = create_server(store_root=store_root, workspace="mcp-page-bounds", registry=_make_registry())

    with pytest.raises(ToolError) as exc_info:
        await server.call_tool("status", {"args": args})

    assert _tool_error_detail(exc_info.value)["refusal_type"] == "PageBoundsError"
    assert driver_calls == []


def test_page_with_limit_zero_raises_a_validation_error_naming_the_refusal():
    with pytest.raises(pydantic.ValidationError) as exc_info:
        Page(limit=0)

    assert "PageBoundsError" in str(exc_info.value)
    assert "PageBoundsError" in (Page.__doc__ or "")


def test_checked_page_raises_the_refusal_itself():
    with pytest.raises(PageBoundsError):
        checked_page(0, 0)
    with pytest.raises(PageSizeExceededError):
        checked_page(MAX_PAGE_SIZE + 1, 0)


@pytest.mark.parametrize("limit", [1, 100])
def test_limit_boundaries_are_accepted(limit):
    assert checked_page(limit, 0).limit == limit


@pytest.mark.parametrize("limit", [0, 101])
def test_limit_boundaries_are_refused(limit):
    with pytest.raises((PageBoundsError, PageSizeExceededError)):
        checked_page(limit, 0)


def test_offset_zero_is_accepted_and_minus_one_refused():
    assert checked_page(50, 0).offset == 0
    with pytest.raises(PageBoundsError):
        checked_page(50, -1)


def test_limit_zero_with_offset_minus_one_is_one_body_carrying_both(client, driver_calls):
    response = client.get("/corpus?limit=0&offset=-1")

    assert response.status_code == 422
    body = response.json()
    assert body["refusal_type"] == "PageBoundsError"
    assert body["limit"] == 0
    assert body["offset"] == -1


def test_no_limit_or_offset_uses_the_defaults(client, driver_calls):
    response = client.get("/corpus")

    assert response.status_code == 200, response.text
    assert driver_calls[0][1]["limit"] == 50
    assert driver_calls[0][1]["offset"] == 0


def test_the_upper_cap_is_checked_before_the_lower_bounds(client, driver_calls):
    response = client.get("/corpus?limit=101&offset=-1")

    assert response.status_code == 422
    assert response.json()["refusal_type"] == "PageSizeExceededError"
    assert driver_calls == []


def _fake_status(documents: list[dict[str, Any]], total: int):
    def _fake(op, payload, **kwargs):
        return {"documents": documents, "counts": {"processed": total}, "total": total}

    return _fake


def _doc(n: int) -> dict[str, Any]:
    return {"document_id": f"d{n}", "status": "processed", "updated_at": "2026-01-01T00:00:00Z"}


@pytest.mark.parametrize(
    ("documents", "total", "offset", "expected"),
    [
        ([], 5, 0, None),
        ([_doc(0), _doc(1)], 5, 0, 2),
        ([_doc(0), _doc(1), _doc(2)], 3, 0, None),
    ],
    ids=["zero-rows-below-total", "two-of-five", "last-page"],
)
async def test_next_offset_is_offset_plus_rows_or_none(
    monkeypatch, store_root, documents, total, offset, expected
):
    monkeypatch.setattr(engine_module, "run_corpus_op", _fake_status(documents, total))
    engine = Databasise(store_root=store_root, workspace="next-offset", registry=_make_registry())

    corpus = await engine.corpus_status(Page(limit=10, offset=offset))
    job = await engine.get_job_status("job-abc", Page(limit=10, offset=offset))

    assert corpus.next_offset == expected
    assert job.next_offset == expected
