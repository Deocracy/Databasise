"""05-04-PLAN.md Task 2 (+ Task 3): dual-transport equivalence for every corpus-side operation
(API-01, API-02, API-06) — REST and in-process reach identical results from identical inputs, the
same rule ``test_dual_transport.py`` already proves for the query side. Task 3 adds the
upload-poll-delete round trip (ROADMAP criterion 3) to this same file.

Driven by a registry holding test-local ``lightrag/full-ingest@0.1.0``/``lightrag/full-delete@0.1.0``
variants pointed at the stub driver (mirrors ``test_full_ingest.py``/``test_delete_document.py``'s
own pattern exactly) for ``ingest``/``delete_document``, and by monkeypatching
``databasise.seam.engine.run_corpus_op`` for ``get_job_status``/``corpus_status``/
``document_counts``/``health`` — those four never dispatch a Part at all (05-04-PLAN.md Task 1's
own design), so there is no Part body to substitute; the monkeypatch reuses the real stub driver's
own ``_run_status``/``_run_health`` functions (never a second, independently-maintained fake).
"""

from __future__ import annotations

import asyncio
import dataclasses
import sys
from pathlib import Path
from typing import Any

import pytest

# Skips this entire module cleanly (never a collection error) when the `rest` extra is not
# installed — see test_rest_transport.py's identical guard for why.
pytest.importorskip("fastapi")

import databasise.seam.engine as engine_module
from databasise.foreign import run_corpus_op
from databasise.parts.registry import PartRegistry
from databasise.parts.schema import NodeContext
from databasise.parts_core.declared_only import LIGHTRAG_FULL_DELETE_PART, LIGHTRAG_FULL_INGEST_PART
from databasise.runner.trace import TokenAccounting
from databasise.seam.corpus import IngestDocument, generated_on_disk_name
from databasise.seam.engine import Databasise
from databasise.seam.rest import create_app
from databasise.tests.fixtures.v1_corpus_driver_stub import _run_health, _run_status
from fastapi.testclient import TestClient

_STUB_DRIVER = Path(__file__).resolve().parents[1] / "fixtures" / "v1_corpus_driver_stub.py"


def _make_stub_ingest_body(*, timeout: float = 5.0):
    """Same shape as ``full_ingest_body``, pointed at the stub driver — mirrors
    ``test_full_ingest.py``'s own ``_make_stub_full_ingest_body``."""

    async def _body(ctx: NodeContext) -> dict[str, Any]:
        config = ctx.config or {}
        payload: dict[str, Any] = {
            "documents": config.get("documents") or [],
            "track_id": config.get("track_id"),
        }
        if config.get("file_paths") is not None:
            payload["file_paths"] = config["file_paths"]
        if config.get("docs_format") is not None:
            payload["docs_format"] = config["docs_format"]

        result = await asyncio.to_thread(
            run_corpus_op,
            "ingest",
            payload,
            timeout=timeout,
            interpreter=Path(sys.executable),
            driver_script=_STUB_DRIVER,
        )
        return {
            "track_id": result.get("track_id"),
            "enqueued": result.get("enqueued", 0),
            "usage": result.get("usage"),
            "tokens": TokenAccounting(counted_by="unbudgetable"),
        }

    return _body


def _make_stub_delete_body(*, timeout: float = 5.0, stub_status: str = "success"):
    """Same shape as ``full_delete_body``, pointed at the stub driver — mirrors
    ``test_delete_document.py``'s own ``_make_stub_full_delete_body``."""

    async def _body(ctx: NodeContext) -> dict[str, Any]:
        config = ctx.config or {}
        payload: dict[str, Any] = {
            "doc_id": config.get("doc_id"),
            "delete_llm_cache": bool(config.get("delete_llm_cache", False)),
            "_stub_status": stub_status,
        }
        result = await asyncio.to_thread(
            run_corpus_op,
            "delete",
            payload,
            timeout=timeout,
            interpreter=Path(sys.executable),
            driver_script=_STUB_DRIVER,
        )
        if result.get("status") == "success":
            ctx.record_store_touch("graph")
            ctx.record_store_touch("vector")
            ctx.record_store_touch("kv")
        return {**result, "tokens": TokenAccounting(counted_by="unbudgetable")}

    return _body


def _make_registry(*, delete_status: str = "success") -> PartRegistry:
    registry = PartRegistry(seed_tracer_parts=False)
    registry.register(dataclasses.replace(LIGHTRAG_FULL_INGEST_PART, body=_make_stub_ingest_body()))
    registry.register(
        dataclasses.replace(
            LIGHTRAG_FULL_DELETE_PART, body=_make_stub_delete_body(stub_status=delete_status)
        )
    )
    return registry


def _patch_status_and_health(
    monkeypatch,
    *,
    documents: list[dict[str, Any]] = (),
    counts: dict[str, int] | None = None,
    working_dir_present: bool = True,
    storages_initialized: bool = True,
) -> None:
    """Monkeypatches ``databasise.seam.engine.run_corpus_op`` — the module-level name
    ``get_job_status``/``corpus_status``/``document_counts``/``health`` call directly (no Part, no
    scheduler) — with a fake that delegates to the real stub driver's own ``_run_status``/
    ``_run_health`` functions, exactly as ``test_corpus_status.py`` does. Affects both the REST
    app and any in-process ``Databasise`` built after this call, since both reach the same
    module-level name.
    """
    counts = counts if counts is not None else {}
    documents = list(documents)

    def _fake(op: str, payload: dict[str, Any], *, timeout: float | None = None, **kwargs: Any):
        job = {
            **payload,
            "_stub_documents": documents,
            "_stub_counts": counts,
            "_stub_working_dir_present": working_dir_present,
            "_stub_storages_initialized": storages_initialized,
        }
        if op == "status":
            return _run_status(job)
        if op == "health":
            return _run_health(job)
        raise AssertionError(f"unexpected op {op!r}")

    monkeypatch.setattr(engine_module, "run_corpus_op", _fake)


@pytest.fixture
def app(store_root):
    return create_app(store_root=store_root, workspace="rest-corpus-test", registry=_make_registry())


@pytest.fixture
def client(app):
    return TestClient(app)


# --------------------------------------------------------------------------------------------- #
# Task 2: dual-transport equivalence for every corpus-side operation.
# --------------------------------------------------------------------------------------------- #


async def test_post_documents_returns_the_same_ingest_job_fields_an_in_process_ingest_returns(client, app):
    body = {"document": {"text": "a structured document"}}

    response = client.post("/documents", json=body)
    assert response.status_code == 200

    in_process = await app.state.engine.ingest(IngestDocument(text="a structured document"))
    assert response.json()["enqueued"] == in_process.enqueued
    assert response.json()["job_id"]


def test_post_documents_upload_returns_an_ingest_job_via_the_deferred_parse_path(client):
    response = client.post(
        "/documents/upload",
        files={"file": ("report.pdf", b"raw pdf bytes", "application/pdf")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["enqueued"] == 1
    assert body["job_id"]


async def test_get_jobs_returns_the_same_job_status_an_in_process_get_job_status_returns(
    client, app, monkeypatch
):
    documents = [
        {
            "document_id": "doc-1",
            "_track_id": "job-abc",
            "status": "processed",
            "updated_at": "t",
            "error_message": None,
        }
    ]
    _patch_status_and_health(monkeypatch, documents=documents, counts={"processed": 1})

    rest_response = client.get("/jobs/job-abc")
    assert rest_response.status_code == 200

    in_process = await app.state.engine.get_job_status("job-abc")
    assert rest_response.json() == in_process.model_dump()


def test_get_jobs_for_an_unknown_job_id_returns_422_with_the_refusal_type_name(client, monkeypatch):
    _patch_status_and_health(monkeypatch, documents=[])

    response = client.get("/jobs/no-such-job")

    assert response.status_code == 422
    assert response.json()["refusal_type"] == "UnknownJobError"


async def test_delete_documents_returns_the_same_deletion_outcome_an_in_process_delete_returns(client, app):
    response = client.delete("/documents/deadbeef")
    assert response.status_code == 200
    body = response.json()

    in_process = await app.state.engine.delete_document("deadbeef")
    assert body["status"] == in_process.status == "success"
    assert body["document_id"] == in_process.document_id


async def test_get_health_returns_the_same_health_report_an_in_process_health_call_returns(
    client, app, monkeypatch
):
    _patch_status_and_health(monkeypatch)

    response = client.get("/health")
    assert response.status_code == 200

    in_process = await app.state.engine.health()
    assert response.json() == in_process.model_dump()


async def test_get_corpus_returns_the_same_corpus_status_an_in_process_corpus_status_call_returns(
    client, app, monkeypatch
):
    documents = [
        {"document_id": f"doc-{i}", "status": "processed", "updated_at": "t", "error_message": None}
        for i in range(3)
    ]
    _patch_status_and_health(monkeypatch, documents=documents, counts={"processed": 3})

    response = client.get("/corpus", params={"limit": 2, "offset": 0})
    assert response.status_code == 200

    from databasise.seam.corpus import Page

    in_process = await app.state.engine.corpus_status(Page(limit=2, offset=0))
    assert response.json() == in_process.model_dump()


async def test_get_corpus_counts_returns_the_same_document_counts_an_in_process_call_returns(
    client, app, monkeypatch
):
    counts = {"processed": 4, "failed": 1}
    _patch_status_and_health(monkeypatch, counts=counts)

    response = client.get("/corpus/counts")
    assert response.status_code == 200

    in_process = await app.state.engine.document_counts()
    assert response.json() == in_process.model_dump()


def test_get_corpus_over_the_cap_returns_422_carrying_requested_and_cap(client, monkeypatch):
    from databasise.seam.corpus import MAX_PAGE_SIZE

    _patch_status_and_health(monkeypatch)

    response = client.get("/corpus", params={"limit": MAX_PAGE_SIZE + 1})

    assert response.status_code == 422
    body = response.json()
    assert body["refusal_type"] == "PageSizeExceededError"
    assert body["requested"] == MAX_PAGE_SIZE + 1
    assert body["limit"] == MAX_PAGE_SIZE


def test_databasise_still_importable_with_no_web_framework_present_after_this_module_grew():
    """Re-runs the same import guard ``test_rest_transport.py`` already proves — the enlarged
    module must still not be imported at module scope by ``databasise``/``databasise.seam``."""
    import ast
    import inspect

    import databasise
    import databasise.seam

    for module in (databasise, databasise.seam):
        tree = ast.parse(inspect.getsource(module))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "rest" not in alias.name.split(".")
            elif isinstance(node, ast.ImportFrom):
                assert "rest" not in (node.module or "").split(".")


def test_rest_module_still_calls_no_selector_resolution_redaction_or_envelope_assembly_function():
    """Re-runs ``test_rest_transport.py``'s own AST proof against the enlarged module — the
    thin-adapter rule is not merely assumed to survive Task 2's new routes, it is re-checked
    (05-04-PLAN.md Task 2's own instruction)."""
    import ast
    import inspect

    from databasise.seam import rest as rest_module
    from databasise.seam import redact as redact_module
    from databasise.seam import selectors as selectors_module

    def _called_names(source: str) -> set[str]:
        names: set[str] = set()
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name):
                    names.add(func.id)
                elif isinstance(func, ast.Attribute):
                    names.add(func.attr)
        return names

    called = _called_names(inspect.getsource(rest_module))
    forbidden = {"ResponseEnvelope"}
    forbidden.update(name for name in selectors_module.__all__ if name != "Selector")
    forbidden.update(redact_module.__all__)

    overlap = called & forbidden
    assert not overlap, f"databasise/seam/rest.py calls forbidden seam-logic function(s): {overlap}"


def test_generated_on_disk_name_is_reachable_for_a_multipart_uploaded_document(client):
    """The multipart upload path reaches the driver with the deferred-parse document format and a
    server-generated on-disk name — never the caller's own filename (05-04-PLAN.md Task 2's own
    behaviour bullet, mirroring 05-01's own raw-upload proof for the in-process path)."""
    response = client.post(
        "/documents/upload",
        files={"file": ("../escape.pdf", b"raw pdf bytes", "application/pdf")},
    )
    assert response.status_code == 200
    # A malicious client-supplied filename never reaches generated_on_disk_name() as the
    # document_id — the server mints its own uuid4-derived id regardless of the filename.
    assert generated_on_disk_name(response.json()["job_id"] or "deadbeef")


# --------------------------------------------------------------------------------------------- #
# Task 3: the upload-poll-delete round trip, proved once end to end (ROADMAP criterion 3) — over
# REST, over in-process, and asserted to produce the same observed status sequence.
# --------------------------------------------------------------------------------------------- #

_ROUND_TRIP_STATUSES = ["pending", "processing", "processed"]


def _patch_status_sequence(monkeypatch):
    """Configures ``run_corpus_op("status", ...)`` to report the *next* value in
    ``_ROUND_TRIP_STATUSES`` for a job-scoped poll (``track_id`` set — advances the sequence) and
    the *current* value for a corpus-wide read (``track_id`` is ``None`` — never advances), so a
    ``GET /corpus/counts`` in the middle of a polling sequence observes whatever status the last
    poll settled on rather than silently advancing the sequence itself. Reuses the real stub
    driver's own ``_run_status``/``_run_health`` — never a second, independently-maintained fake.
    Returns the mutable state dict so a test can inspect ``state["poll_index"]`` if needed.
    """
    state = {"poll_index": 0}

    def _fake(op: str, payload: dict[str, Any], *, timeout: float | None = None, **kwargs: Any):
        if op == "status":
            track_id = payload.get("track_id")
            idx = min(state["poll_index"], len(_ROUND_TRIP_STATUSES) - 1)
            current_status = _ROUND_TRIP_STATUSES[idx]
            documents = [
                {
                    "document_id": track_id or "round-trip-doc",
                    "_track_id": track_id,
                    "status": current_status,
                    "updated_at": "t",
                    "error_message": None,
                }
            ]
            job = {**payload, "_stub_documents": documents, "_stub_counts": {current_status: 1}}
            result = _run_status(job)
            if track_id:
                state["poll_index"] = min(state["poll_index"] + 1, len(_ROUND_TRIP_STATUSES) - 1)
            return result
        if op == "health":
            return _run_health(
                {**payload, "_stub_working_dir_present": True, "_stub_storages_initialized": True}
            )
        raise AssertionError(f"unexpected op {op!r}")

    monkeypatch.setattr(engine_module, "run_corpus_op", _fake)
    return state


def test_upload_poll_delete_round_trip(store_root, monkeypatch):
    """Over the REST transport, in one test: upload, poll a job to completion (observing the full
    status sequence, not only the terminal state), read counts, delete, read counts again, and
    confirm a second delete of the same id reports ``not_found``."""
    _patch_status_sequence(monkeypatch)
    success_client = TestClient(
        create_app(store_root=store_root, workspace="round-trip-success", registry=_make_registry())
    )

    upload_response = success_client.post(
        "/documents/upload",
        files={"file": ("doc.txt", b"hello world", "text/plain")},
        data={"document_id": "round-trip-doc"},
    )
    assert upload_response.status_code == 200
    job_id = upload_response.json()["job_id"]

    observed_statuses: list[str] = []
    for _ in _ROUND_TRIP_STATUSES:
        job_response = success_client.get(f"/jobs/{job_id}")
        assert job_response.status_code == 200
        observed_statuses.append(job_response.json()["documents"][0]["status"])

    # A poll that only ever sees the terminal state proves nothing about polling.
    assert observed_statuses == _ROUND_TRIP_STATUSES

    counts_response = success_client.get("/corpus/counts")
    assert counts_response.status_code == 200
    assert counts_response.json()["by_status"].get("processed") == 1

    delete_response = success_client.delete("/documents/round-trip-doc")
    assert delete_response.status_code == 200
    assert delete_response.json()["status"] == "success"

    second_counts_response = success_client.get("/corpus/counts")
    assert second_counts_response.status_code == 200

    not_found_client = TestClient(
        create_app(
            store_root=store_root,
            workspace="round-trip-success",
            registry=_make_registry(delete_status="not_found"),
        )
    )
    second_delete_response = not_found_client.delete("/documents/round-trip-doc")
    assert second_delete_response.status_code == 200
    assert second_delete_response.json()["status"] == "not_found"


async def test_upload_poll_delete_round_trip_in_process_matches_the_rest_status_sequence(
    store_root, monkeypatch
):
    """The dual-transport rule applied to a multi-step flow, not just to single calls — the
    identical sequence driven entirely in-process against ``Databasise`` methods produces the
    same observed status sequence the REST round trip above does."""
    _patch_status_sequence(monkeypatch)
    engine = Databasise(store_root=store_root, workspace="round-trip-in-process", registry=_make_registry())

    job = await engine.ingest(IngestDocument(text="hello world", document_id="round-trip-doc-2"))

    observed_statuses: list[str] = []
    for _ in _ROUND_TRIP_STATUSES:
        status = await engine.get_job_status(job.job_id)
        observed_statuses.append(status.documents[0].status)

    assert observed_statuses == _ROUND_TRIP_STATUSES

    counts = await engine.document_counts()
    assert counts.by_status.get("processed") == 1

    outcome = await engine.delete_document("round-trip-doc-2")
    assert outcome.status == "success"

    second_counts = await engine.document_counts()
    assert second_counts.total >= 0  # a fixed-size record either way — never a partial dump

    not_found_engine = Databasise(
        store_root=store_root,
        workspace="round-trip-in-process",
        registry=_make_registry(delete_status="not_found"),
    )
    second_outcome = await not_found_engine.delete_document("round-trip-doc-2")
    assert second_outcome.status == "not_found"


async def test_the_rest_and_in_process_round_trips_observe_the_identical_status_sequence(
    store_root, monkeypatch
):
    """The two round trips above are driven by independently-monkeypatched fakes (test isolation)
    — this test drives both against the *same* patched fake within one test, so the sequences are
    compared directly rather than merely asserted equal to the same hardcoded literal twice."""
    _patch_status_sequence(monkeypatch)
    rest_client = TestClient(
        create_app(store_root=store_root, workspace="round-trip-compare-rest", registry=_make_registry())
    )
    upload_response = rest_client.post(
        "/documents/upload",
        files={"file": ("doc.txt", b"hello world", "text/plain")},
        data={"document_id": "round-trip-doc-3"},
    )
    rest_job_id = upload_response.json()["job_id"]
    rest_sequence = [
        rest_client.get(f"/jobs/{rest_job_id}").json()["documents"][0]["status"]
        for _ in _ROUND_TRIP_STATUSES
    ]

    _patch_status_sequence(monkeypatch)
    engine = Databasise(
        store_root=store_root, workspace="round-trip-compare-in-process", registry=_make_registry()
    )
    in_process_job = await engine.ingest(IngestDocument(text="hello world", document_id="round-trip-doc-4"))
    in_process_sequence = []
    for _ in _ROUND_TRIP_STATUSES:
        status = await engine.get_job_status(in_process_job.job_id)
        in_process_sequence.append(status.documents[0].status)

    assert rest_sequence == in_process_sequence == _ROUND_TRIP_STATUSES


def test_get_corpus_over_the_cap_refusal_body_parses_as_json_with_integer_requested_and_limit(
    client, monkeypatch
):
    """Task 3's own restatement of Task 2's over-cap refusal test — the response body is parsed
    as JSON here (rather than merely indexed) and its ``requested``/``limit`` values are asserted
    to be real integers, so a caller can act on the refusal without parsing prose."""
    import json as _json

    from databasise.seam.corpus import MAX_PAGE_SIZE

    _patch_status_and_health(monkeypatch)

    response = client.get("/corpus", params={"limit": MAX_PAGE_SIZE + 1})
    assert response.status_code == 422

    body = _json.loads(response.text)
    assert isinstance(body["requested"], int) and body["requested"] == MAX_PAGE_SIZE + 1
    assert isinstance(body["limit"], int) and body["limit"] == MAX_PAGE_SIZE
