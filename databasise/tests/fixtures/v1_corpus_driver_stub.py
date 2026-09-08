"""A standard-library-only stand-in for ``databasise/foreign/v1_corpus_driver_script.py``, used by
``databasise/tests/parts_core/lightrag/test_full_ingest.py`` (05-01-PLAN.md Task 1) via
``run_corpus_op``'s ``driver_script=``/``interpreter=`` override points, so the test suite never
needs a real v1 venv or a real LLM call to prove the ingest wiring end to end.

Honours the same stdin/stdout JSON protocol the real driver does: for ``op == "ingest"`` echoes
back ``{"track_id": <job's track_id>, "enqueued": len(documents), "usage": None}``. For
``op == "delete"`` (05-03-PLAN.md Task 1) echoes a configurable status (``_stub_status``,
defaulting to ``"success"``) back as ``{"status": ..., "doc_id": ..., "message": ..., "status_code":
..., "file_path": None}``. Both ``ingest`` and ``delete`` optionally sleep first
(``_stub_sleep_seconds`` on the job) so a timeout can be provoked deliberately. For
``op == "entities"`` echoes a configurable entity map (``_stub_entities``, defaulting to ``{}``)
and a configurable chunk-id list (``_stub_chunk_ids``, defaulting to ``None``) back as
``{"chunk_ids": ..., "entities": ...}``. For ``op == "entity_info"`` echoes a configurable
name-keyed map (``_stub_entity_info``, defaulting to ``{}``) back as ``{"entities": ...}``.

For ``op == "status"`` (05-04-PLAN.md Task 1), the job carries a caller-configured
``_stub_documents`` (a list of ``{"document_id", "status", "updated_at", "error_message",
"_track_id"}`` dicts — ``_track_id`` is stub-only bookkeeping, stripped before the page is
returned) and ``_stub_counts``. Filters by the job's own ``track_id`` when given (matching each
document's ``_track_id``), slices the result by ``offset``/``limit`` exactly as the real driver
does, and returns ``{"counts": ..., "documents": ..., "total": <the unsliced, filtered count>}`` —
letting a test build an arbitrarily large ``_stub_documents`` list to exercise pagination across
several pages without a real v1 venv. For ``op == "health"`` echoes configurable
``_stub_working_dir_present``/``_stub_storages_initialized`` booleans (both defaulting to
``True``) back as ``{"working_dir_present": ..., "storages_initialized": ...}``.

Any other ``op`` exits 1 with a traceback on stderr. Imports nothing from ``lightrag`` and nothing
from ``databasise`` — a genuine leaf, run under whatever interpreter the test process itself uses
(no special venv required).
"""

from __future__ import annotations

import json
import sys
import time
import traceback

_STATUS_CODES = {"success": 200, "not_found": 404, "not_allowed": 403, "fail": 500}


def _run_ingest(job: dict) -> dict:
    sleep_seconds = job.get("_stub_sleep_seconds")
    if sleep_seconds:
        time.sleep(float(sleep_seconds))
    documents = job.get("documents") or []
    return {"track_id": job.get("track_id"), "enqueued": len(documents), "usage": None}


def _run_delete(job: dict) -> dict:
    sleep_seconds = job.get("_stub_sleep_seconds")
    if sleep_seconds:
        time.sleep(float(sleep_seconds))
    status = job.get("_stub_status", "success")
    return {
        "status": status,
        "doc_id": job.get("doc_id"),
        "message": f"stub delete status={status}",
        "status_code": _STATUS_CODES.get(status, 500),
        "file_path": None,
    }


def _run_entities(job: dict) -> dict:
    return {
        "chunk_ids": job.get("_stub_chunk_ids"),
        "entities": job.get("_stub_entities") or {},
    }


def _run_entity_info(job: dict) -> dict:
    return {"entities": job.get("_stub_entity_info") or {}}


def _run_status(job: dict) -> dict:
    track_id = job.get("track_id")
    limit = int(job.get("limit", 50))
    offset = int(job.get("offset", 0))
    documents = list(job.get("_stub_documents") or [])
    if track_id:
        documents = [doc for doc in documents if doc.get("_track_id") == track_id]

    total = len(documents)
    page = documents[offset : offset + limit]
    page = [{k: v for k, v in doc.items() if k != "_track_id"} for doc in page]

    return {"counts": job.get("_stub_counts") or {}, "documents": page, "total": total}


def _run_health(job: dict) -> dict:
    return {
        "working_dir_present": job.get("_stub_working_dir_present", True),
        "storages_initialized": job.get("_stub_storages_initialized", True),
    }


def main() -> int:
    try:
        job = json.loads(sys.stdin.read())
        op = job["op"]
        if op == "ingest":
            result = _run_ingest(job)
        elif op == "delete":
            result = _run_delete(job)
        elif op == "entities":
            result = _run_entities(job)
        elif op == "entity_info":
            result = _run_entity_info(job)
        elif op == "status":
            result = _run_status(job)
        elif op == "health":
            result = _run_health(job)
        else:
            raise ValueError(f"unknown op {op!r}")
    except Exception:
        traceback.print_exc()
        return 1
    sys.stdout.write(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
