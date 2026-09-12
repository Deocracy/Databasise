# Phase 5: Opaque-Side Admission - Pattern Map

**Mapped:** 2026-09-08
**Files analyzed:** 12 (new/modified, from RESEARCH.md's Recommended Project Structure + Test Map)
**Analogs found:** 10 / 12

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `databasise/parity/v1_ingest_driver_script.py` (NEW; name per A5, sibling of `v1_driver_script.py`) | utility (subprocess entry point, v1-side) | request-response (JSON over stdin/stdout) | `databasise/parity/v1_driver_script.py` | exact |
| `databasise/parts_core/lightrag/full_ingest.py` (NEW; replaces `body=None` stub) | service (opaque Part body) | request-response wrapping subprocess launch | `databasise/parity/v1_arm.py` (`run_v1_arm`) | exact |
| `databasise/parts_core/lightrag/full_delete.py` (NEW; separate port per §19.6) | service (opaque Part body, `mutates_store`) | request-response wrapping subprocess launch | `databasise/parity/v1_arm.py` (`run_v1_arm`) + `v1/lightrag/lightrag.py:adelete_by_doc_id` | role-match (launch shape exact; deletion algorithm to preserve, not reimplement) |
| `databasise/parts_core/declared_only.py` (MODIFY: `LIGHTRAG_FULL_INGEST_PART.body` gets a real callable; `CODEBASE_MEMORY_MCP_PART` stays declared-only but effects/verdicts extended) | config (Part registry declarations) | — | itself (existing file, in-place edit) | exact |
| `databasise/seam/engine.py` (MODIFY: add `ingest()`, `get_job_status()`, `delete_document()`, `health()`, `corpus_status()`, `document_counts()`) | service (seam methods on `Databasise`) | CRUD / request-response | `databasise/seam/engine.py` itself — `resolve_evidence`/`resolve_trace` (thin store-lifecycle methods) | exact |
| `databasise/seam/rest.py` (MODIFY: add `POST /documents`, `GET /documents/{id}/status`, `DELETE /documents/{id}`, `GET /health`, `GET /corpus`) | route (REST endpoints) | request-response | `databasise/seam/rest.py` itself — `post_query`/`post_resolve_evidence`/`post_resolve_trace` | exact |
| `databasise/mcp/__init__.py`, `databasise/mcp/server.py`, `databasise/mcp/tools.py` (NEW package) | route (MCP transport, thin adapter) | request-response | `databasise/seam/rest.py` (whole file — "thin adapter, provably" pattern) | role-match (same adapter shape, different protocol library) |
| `databasise/tools/check_import_boundary.py` (MODIFY: add new driver script filename to `_SUBPROCESS_ENTRY_POINT_EXCLUSIONS`) | config/utility (AST-scan exclusion list) | — | itself (existing file, one-line addition) | exact |
| `databasise/tests/parts_core/lightrag/test_full_ingest.py` (NEW) | test | integration | `databasise/tests/seam/test_mach11_event.py` (fixture-Part + real scheduler run pattern) | role-match |
| `databasise/tests/parts_core/lightrag/test_full_ingest_compat.py` (NEW) | test | unit (boundary-value pinning) | `databasise/tests/test_import_boundary.py` (not read this session, but named directly by RESEARCH.md as the precedent for compat-style AST/declared-value checks) | role-match |
| `databasise/tests/parts_core/test_codebase_memory_mcp_admission.py` (NEW) | test | unit (declared-metadata assertions) | `databasise/parts_core/declared_only.py` (the fixture-under-test) + `databasise/tests/seam/test_mach11_event.py` (assertion style over declared effects) | partial-match |
| `databasise/tests/mcp/test_tool_growth_invariant.py`, `databasise/tests/mcp/test_dual_transport_parity.py` (NEW) | test | request-response (parity across transports) | `databasise/tests/seam/test_rest_transport.py` (named in `rest.py`'s own docstring as the AST-based thin-adapter proof — not read this session, but the closest existing parity/shape-proof test) | role-match |

## Pattern Assignments

### `databasise/parity/v1_ingest_driver_script.py` (utility, request-response subprocess entry point)

**Analog:** `databasise/parity/v1_driver_script.py` (read in full this session)

**Module docstring / boundary framing** (lines 1-15):
```python
"""Subprocess entry point ... Lives under ``databasise/parity/`` ... but is executed
**by v1's own interpreter** (``v1/.venv/bin/python``), never by the interpreter running
``databasise/``'s own code ... v1's ``lightrag`` package is neither installed in nor importable
from `databasise/`'s environment, and ``databasise/tools/check_import_boundary.py`` forbids that
import anywhere under ``databasise/`` regardless (D-14).

This module is therefore a **leaf**: it imports only v1's own packages (``lightrag``) and the
standard library. Nothing under ``databasise/`` ever imports it with a Python ``import``..."""
```

**Protocol pattern** (lines 17-31): read one JSON object from stdin (a job dict), build v1's `LightRAG` facade from it, run the operation, write one JSON object to stdout. The ingest driver's job dict must carry whatever `ainsert()`/`apipeline_process_enqueue_documents()` needs (document text/path, `working_dir`) instead of the query-side's `{"mode", "query", "hl_keywords", "ll_keywords", "working_dir"}`; the delete driver's job dict carries `{"doc_id", "working_dir"}` and calls `adelete_by_doc_id()`.

**Error handling pattern** (module docstring, final paragraph):
```
A malformed job, a v1-side query failure, or any other exception prints a traceback to stderr and
exits 1 — the caller (``v1_arm.py``) treats any non-zero exit as a refusal carrying that stderr,
never as an empty success.
```
Copy this exactly: `try/except Exception: traceback.print_exc(file=sys.stderr); sys.exit(1)` around the whole `main()` body, nothing partial written to stdout on failure.

**Imports pattern** (lines 39-46):
```python
from __future__ import annotations
import asyncio
import json
import os
import sys
import traceback
from functools import partial
from typing import Any
from lightrag import LightRAG
from lightrag.base import QueryParam
from lightrag.llm.openai import openai_complete_if_cache, openai_embed
from lightrag.utils import EmbeddingFunc
```
The ingest driver swaps `QueryParam`-only imports for whatever `pipeline.py`'s ingest entry points need (`apipeline_process_enqueue_documents`, `adelete_by_doc_id`); the LLM-client injection imports stay identical (needed for condition-3 network-namespace-by-construction, per Open Question 3's recommendation).

---

### `databasise/parts_core/lightrag/full_ingest.py` and `full_delete.py` (service, opaque Part body)

**Analog:** `databasise/parity/v1_arm.py`'s `run_v1_arm` (read this session, lines ~100-175)

**Launch pattern** (lines 122-134, timeout-parameterized subprocess call):
```python
env = dict(os.environ)
env.update(_load_env_file(env_path or DEFAULT_V1_ENV_PARITY))
env.setdefault("ENABLE_LLM_CACHE", "false")

job = {
    "mode": mode,
    "query": query,
    ...
    "working_dir": str(working_dir or DEFAULT_V1_WORKING_DIR),
}

start = time.monotonic()
proc = subprocess.run(
    [str(interpreter), str(driver_script)],
    input=json.dumps(job),
    capture_output=True,
    text=True,
    cwd=str(_REPO_ROOT / "v1"),
    env=env,
    timeout=timeout,
)
```
`full_ingest.py`'s `Part.body` callable builds the same job-dict shape (document payload instead of query) and calls this exact subprocess-run shape, `timeout` sourced from the node's budget allowance (§8 condition 4's wall-clock ceiling). `full_delete.py`'s body is identical except the job dict carries `{"doc_id", "working_dir"}` and `mode="delete"`.

**Error propagation:**
```python
if proc.returncode != 0:
    raise V1ArmSubprocessError(proc.returncode, proc.stderr)
payload = json.loads(proc.stdout)
```
Reuse this shape — non-zero exit is a hard refusal, never a partial/empty success, mirroring `databasise/seam/refusals.py`'s house style (raise a named exception carrying the offending value).

**Async-boundary note:** `run_v1_arm` is itself blocking (`subprocess.run`); its own docstring says "a caller on an event loop should run this via `asyncio.to_thread`" — the new `Part.body` (an async callable per `NodeContext`) must do the same: `await asyncio.to_thread(run_v1_arm_like_call, ...)`.

**Condition-3 (network denial) pattern:** inject the machine's own `OpenAICompatibleClient` base_url into the subprocess env exactly as the existing `_extra_body`/`OPENAI_LLM_EXTRA_BODY`-style env injection does in `v1_driver_script.py`/`v1_arm.py` — do not let the subprocess make independent outbound calls.

---

### `databasise/seam/engine.py` — new `Databasise` methods (service, CRUD/request-response)

**Analog:** `databasise/seam/engine.py` itself, `resolve_evidence`/`resolve_trace` (lines 464-489, read this session)

**Thin store-lifecycle pattern** (lines 464-472):
```python
async def resolve_evidence(self, ref: EvidenceRef) -> dict[str, Any]:
    stores = _build_stores(self.store_root, self.workspace)
    try:
        return resolve_evidence_ref(ref, stores["vector"])
    finally:
        for store in stores.values():
            await store.finalize()
```
`corpus_status()`/`document_counts()`/`health()` follow this exact open-try/finally-finalize shape against whatever store(s) they read (doc-status KV, artifact registry) — bounded/paginated per Anti-Pattern "never a full dump".

**Raise-not-None pattern** (`resolve_trace`, lines 477-489):
```python
record = self._trace_store.resolve(trace_reference)
if debug:
    return record
return {key: value for key, value in record.items() if key in _NON_DEBUG_TRACE_FIELDS}
```
`get_job_status()` mirrors this: raise a named "unknown job" exception rather than return `None`, exactly as `TraceStore.resolve` does for an unknown trace reference — do not invent a new sentinel.

**`ingest()`/`delete_document()` execution-path pattern:** follow `_execute()`'s shape (lines 356-370) — `check_consumable` → resolve → parse_wiring → run — but dispatching to the single named ingest/delete Part rather than a resolved selector wiring, since these are direct opaque-Part invocations, not modality-routed queries. `delete_document()` must pass the same MACH-11 recorder callable `_execute()` passes to `scheduler.run_wiring` (see engine.py's own module docstring on `_mach11_events`/`_accounted_store_keys`) so the deleting Part's `mutates_store` effect gets correlated for real, for the first time.

---

### `databasise/seam/rest.py` — new endpoints (route, request-response)

**Analog:** `databasise/seam/rest.py` itself (read this session, full file)

**Thin-adapter pattern** (lines 118-124, `post_resolve_evidence`):
```python
@app.post("/evidence/resolve")
async def post_resolve_evidence(ref: EvidenceRef) -> dict[str, Any]:
    return await engine.resolve_evidence(ref)
```
Every new endpoint (`POST /documents`, `GET /documents/{id}/status`, `DELETE /documents/{id}`, `GET /health`, `GET /corpus`) must be this exact one-line shape: deserialize into a `_RequestModel` subclass, await the identical `Databasise` method, return the result — no logic in `rest.py` itself (D-17's provable thin-adapter rule, enforced by an existing AST-walking test, `test_rest_transport.py`).

**Request DTO pattern** (lines 62-71):
```python
class _RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

class QueryRequest(_RequestModel):
    query: QueryObject
    selector: Selector | None = None
```
New DTOs (`IngestRequest`, `DeleteRequest`) subclass `_RequestModel` the same way — `extra="forbid"`, no logic, just field declarations. For API-01's raw-upload endpoint, the file bytes arrive via FastAPI `UploadFile` (needs `python-multipart`), not a `_RequestModel` field — validate content-type/size before touching disk (V5/V12 threat notes in RESEARCH.md).

**Refusal-mapping pattern** (lines 76-88, `_refusal_response`) is automatic and requires no new code per endpoint — it is registered once via `app.add_exception_handler(SeamRefusalError, _refusal_response)` and works generically off `vars(exc)` for any new `SeamRefusalError` subclass a delete/ingest/status method raises.

---

### `databasise/mcp/server.py`, `tools.py` (route, MCP transport)

**Analog:** `databasise/seam/rest.py` (whole-file shape, "thin adapter, provably")

No MCP-specific analog exists in the codebase yet (first phase to add this transport). Copy `rest.py`'s architectural shape wholesale, substituting the `mcp` SDK's tool-registration decorator for FastAPI's route decorator:
- One `Databasise` instance built once, held on the server object (mirrors `app.state.engine = engine`).
- Each of exactly five tools (`ingest`, `query`, `delete`, `status`, `compare`) is a one-line adapter: deserialize tool args into the same `QueryObject`/`Selector`/`EvidenceRef`/new ingest-delete DTOs REST uses, await the identical `Databasise` method, return the result.
- No selector resolution, no redaction, no envelope assembly inside `databasise/mcp/` — same separation-of-concerns rule as `rest.py`'s own docstring states, verified the same way (`test_tool_growth_invariant.py` should walk the AST/tool-registration list the way `test_rest_transport.py` walks `rest.py`'s AST).
- §18.5 growth rule ("a second modality that answers an operation an existing tool already exposes MUST add no tool") is enforced by pinning the tool count to exactly 5 in the growth-invariant test, not by convention.

---

### `databasise/tools/check_import_boundary.py` (config, exclusion-list edit)

**Analog:** itself — the existing `_SUBPROCESS_ENTRY_POINT_EXCLUSIONS` set (read this session)

**Exact pattern to extend** (line ~40):
```python
_SUBPROCESS_ENTRY_POINT_EXCLUSIONS = frozenset({"v1_driver_script.py"})
```
Add the new ingest/delete driver script filename(s) to this frozenset by name — a one-line, reviewable diff. Per the module's own docstring, this is "exactly the kind of change that deserves a human look, since it is opening a hole in an enforced boundary" — RESEARCH.md's Phase Gate already calls this out for manual review.

---

## Shared Patterns

### Subprocess-boundary crossing (v1 import ban)
**Source:** `databasise/parity/v1_driver_script.py` + `databasise/parity/v1_arm.py` + `databasise/tools/check_import_boundary.py`
**Apply to:** `full_ingest.py`, `full_delete.py`, the new driver script — every file that must reach v1's `ainsert`/`apipeline_process_enqueue_documents`/`adelete_by_doc_id`.
Rule: `databasise/` code never does `from lightrag import ...` directly (AST-enforced). All v1 access is JSON-over-stdin/stdout subprocess launch under `v1/.venv`'s own interpreter, timeout-parameterized, non-zero exit = hard refusal.

### Thin-adapter transport shape (D-17)
**Source:** `databasise/seam/rest.py` (whole file)
**Apply to:** `databasise/mcp/` (new), and every new REST endpoint added to `rest.py` this phase.
Every transport method is: deserialize → await identical `Databasise` method → return. No logic duplicated across transports; parity proven by a dual-transport test (`test_dual_transport_parity.py`), mirroring D-17's existing precedent.

### `mutates_store` / MACH-11 seam event (CONTRACT §14.4, D-09)
**Source:** `databasise/seam/engine.py` (`_mach11_events`, `_accounted_store_keys`, module docstring) + `databasise/tests/seam/test_mach11_event.py`
**Apply to:** `full_delete.py`'s Part declaration and `delete_document()`'s call into `run_wiring`.
No new envelope field — `mutates_store` correlation is already wired; this phase is the first to exercise it against a real (non-fixture) part. Declare `effects=["mutates_store", ...]` on the delete Part; pass the recorder callable through exactly as `_execute()` already does for query.

### §19.6 separate-port rule
**Source:** `docs/system-model/CONTRACT.md` §19.6 (quoted verbatim in RESEARCH.md)
**Apply to:** ingest vs. delete — these MUST be two separate Part/port registrations (different declared effects: `writes_artifact` vs `mutates_store`), never one Part with two operations, even though both share the same underlying v1 subprocess mechanism.

### Bounded/paginated read-only surfaces
**Source:** RESEARCH.md Anti-Patterns + `databasise/seam/engine.py`'s `resolve_evidence`/`resolve_trace` (open-store/finalize shape)
**Apply to:** `health()`, `corpus_status()`, `document_counts()` — never return a full corpus/index dump; bound and paginate by construction.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `databasise/mcp/__init__.py` | config | — | First MCP package in the repo; trivial re-export file, no analog needed |
| `databasise/parts_core/test_codebase_memory_mcp_admission.py`'s specific eleven-condition-verdict assertions | test | unit | The verdict table itself (`PARTS.md ## §X`) is a docs artifact, not code — the test must encode already-completed docs analysis as assertions against `CODEBASE_MEMORY_MCP_PART`'s declared fields; no prior test does this shape (closest is `test_mach11_event.py`'s declared-effects-based assertions, listed above as partial-match) |

## Metadata

**Analog search scope:** `databasise/parity/`, `databasise/parts_core/`, `databasise/seam/`, `databasise/tools/`, `databasise/tests/seam/`, `v1/lightrag/lightrag.py`
**Files scanned:** `v1_driver_script.py`, `v1_arm.py`, `declared_only.py`, `check_import_boundary.py`, `seam/engine.py`, `seam/rest.py`, `tests/seam/test_mach11_event.py`, `v1/lightrag/lightrag.py` (`adelete_by_doc_id`)
**Pattern extraction date:** 2026-09-08
