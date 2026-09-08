"""A standard-library-only stand-in for ``databasise/foreign/v1_corpus_driver_script.py``, used by
``databasise/tests/parts_core/lightrag/test_full_ingest.py`` (05-01-PLAN.md Task 1) via
``run_corpus_op``'s ``driver_script=``/``interpreter=`` override points, so the test suite never
needs a real v1 venv or a real LLM call to prove the ingest wiring end to end.

Honours the same stdin/stdout JSON protocol the real driver does: for ``op == "ingest"`` echoes
back ``{"track_id": <job's track_id>, "enqueued": len(documents), "usage": None}``, optionally
sleeping first (``_stub_sleep_seconds`` on the job) so a timeout can be provoked deliberately. For
``op == "delete"`` (05-03-PLAN.md Task 1) echoes a configurable status
(``_stub_status``, defaulting to ``"success"``) back as ``{"status": ..., "doc_id": ..., "message":
..., "status_code": ..., "file_path": None}``. For ``op == "entities"`` echoes a configurable entity
map (``_stub_entities``, defaulting to ``{}``) back as ``{"entities": ...}``. Any other ``op`` exits
1 with a traceback on stderr. Imports nothing from ``lightrag`` and nothing from ``databasise`` — a
genuine leaf, run under whatever interpreter the test process itself uses (no special venv
required).
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
    status = job.get("_stub_status", "success")
    return {
        "status": status,
        "doc_id": job.get("doc_id"),
        "message": f"stub delete status={status}",
        "status_code": _STATUS_CODES.get(status, 500),
        "file_path": None,
    }


def _run_entities(job: dict) -> dict:
    return {"entities": job.get("_stub_entities") or {}}


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
        else:
            raise ValueError(f"unknown op {op!r}")
    except Exception:
        traceback.print_exc()
        return 1
    sys.stdout.write(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
