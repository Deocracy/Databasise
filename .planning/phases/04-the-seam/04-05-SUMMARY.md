---
phase: 04-the-seam
plan: 05
subsystem: api
tags: [seam, rest, fastapi, sse, pydantic, envelope, dual-transport]

requires:
  - phase: 04-the-seam (plans 01-04)
    provides: "databasise.seam.Databasise, the QueryObject/ResponseEnvelope/Selector/EvidenceRef/
      TokenBreakdownEntry/SeamEvent shapes, the SeamRefusalError hierarchy (including
      UnknownTraceReferenceError, UnbudgetableParticipantError, UnresolvableEvidenceReferenceError),
      databasise.seam.redact's two-tier leak gate, and databasise.seam.trace_store.TraceStore —
      every piece this plan's REST transport adapts rather than reimplements"
provides:
  - "databasise.seam.rest.create_app — the optional FastAPI application factory (import-guarded),
    exposing the same four §18 operations in-process already exposes: query, streaming query
    (SSE), evidence dereference, trace resolution"
  - "databasise.seam.engine.Databasise.query_stream — the async-generator streaming variant
    sharing query()'s own _execute() path verbatim"
  - "the rest optional-dependency extra ([project.optional-dependencies], databasise[rest]) —
    fastapi>=0.135, uvicorn"
  - "the dual-transport conformance test (D-17): both transports proven to produce the same
    envelope for the same query, field by field, with each exclusion named and justified"
affects: []

actuals:
  tokens: 12976
  tasks: 3
  commits: 3
  plan_head_before: b15c05581a4929e0498d9e139a9af995d152d682

tech-stack:
  added: [fastapi, uvicorn, httpx]
  patterns:
    - "Application factory over a single shared Databasise instance (databasise.seam.rest.create_app)
      — every endpoint body is deserialize -> await the identical in-process method -> serialize,
      proven by AST-walking rest.py's own source for calls to selector-resolution/redaction/
      envelope-assembly functions rather than trusting convention"
    - "One base-class exception handler (app.add_exception_handler(SeamRefusalError, ...)),
      never per-endpoint try/except — Starlette dispatches by MRO, so every current and future
      SeamRefusalError subclass is caught without the handler needing to enumerate types itself;
      the refusal's own named constructor attributes are read generically via vars(exc)"
    - "query()/_execute() split so a streaming variant can share the exact same execution path
      (selector resolution, run, evidence mint, token breakdown, MACH-11 correlation, trace
      persist) and differ only in how the result is delivered (return vs. yield)"
    - "check_same_thread=False on a long-lived SQLite connection constructed once at engine
      startup but used across whatever OS thread the ASGI server's event loop happens to run on
      — safe because access is always sequential, never concurrent, from more than one thread"
    - "pytest.importorskip('fastapi') at the top of every REST-transport-dependent test module,
      so a bare `uv run pytest -q` (no optional extra installed) skips those modules cleanly
      instead of failing collection — the mechanism the plan's own verification step depends on"

key-files:
  created:
    - databasise/seam/rest.py
    - databasise/tests/seam/test_rest_transport.py
    - databasise/tests/seam/test_dual_transport.py
  modified:
    - databasise/pyproject.toml
    - databasise/seam/engine.py
    - databasise/seam/trace_store.py
    - databasise/tests/test_embed_startup.py

key-decisions:
  - "Checkpoint answer applied verbatim: approved — fastapi, uvicorn, httpx all confirmed by the
    developer 2026-09-06 (see .planning/phases/04-the-seam/04-CHECKPOINT-ANSWERS.md). fastapi and
    uvicorn go under [project.optional-dependencies] rest (never [dependency-groups], which is not
    pip-installable by an external consumer); httpx goes in the existing dev group."
  - "FastAPI version floor: >=0.135 (the first release to ship native fastapi.sse.EventSourceResponse
    per 04-RESEARCH.md Pattern 4/FA-11). Verified installed at 0.141.1 — no floor raise needed, no
    sse-starlette dependency added."
  - "FA-10 (EMBED-02 partial scope, resolved): EMBED-02's own requirement text names 'the REST + MCP
    server.' This plan ships only the REST half — the MCP transport is CONTEXT.md's Deferred Idea
    API-07, out of this phase's scope entirely. Marked complete per the plan's own instruction to
    state the qualification in the SUMMARY rather than leaving it silently unqualified; a later
    phase implementing API-07 inherits the same one-seam-many-transports invariant this plan proves
    for REST, not a fresh design question."
  - "Streaming design (D-16): query_stream() is a real async generator sharing _execute()'s
    identical code path, yielding one SSE event per evidence reference (in the envelope's own
    order) followed by one final event carrying every remaining envelope field. This is honest
    about what the underlying scheduler actually produces — a single completed run, not an
    incrementally-generated LLM token stream — rather than fabricating token-level streaming the
    execution model does not support. No requirement in this phase's set asks for token-level
    streaming; the requirement is that streamed content assembles to the same answer/evidence the
    non-streaming endpoint returns, which is what is proven."

requirements-completed: [API-04, EMBED-02]

coverage:
  - id: D1
    description: "An HTTP client posts a query object to POST /query and receives the same closed
      envelope an in-process caller receives, from a transport holding no logic of its own"
    requirement: "API-04"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_rest_transport.py::test_an_http_client_posts_a_query_and_receives_the_same_closed_envelope"
        status: pass
      - kind: unit
        ref: "databasise/tests/seam/test_rest_transport.py::test_rest_module_calls_no_selector_resolution_redaction_or_envelope_assembly_function"
        status: pass
    human_judgment: false
  - id: D2
    description: "Installing databasise without the rest extra leaves import databasise/import
      databasise.seam working with no web framework present; only an explicit import of the REST
      module raises, naming the extra to install"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_rest_transport.py::test_databasise_and_databasise_seam_are_importable_with_no_web_framework_present"
        status: pass
      - kind: integration
        ref: "cd databasise && uv run pytest -q (no --extra rest): 552 passed, 2 skipped — the two
          REST-dependent test modules skip cleanly via pytest.importorskip('fastapi') rather than
          failing collection"
        status: pass
    human_judgment: false
  - id: D3
    description: "A caller streams a query response over SSE and the streamed content assembles to
      the same answer and evidence references the non-streaming endpoint returns for the same query"
    requirement: "API-04"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_rest_transport.py::test_the_streamed_events_assemble_to_the_same_content_the_non_streaming_endpoint_returns"
        status: pass
    human_judgment: false
  - id: D4
    description: "Every seam refusal maps to a REST refusal response naming its own value, never a
      success response, via one application-level exception handler — enumerated from
      SeamRefusalError's own subclass set, never a hand-maintained list"
    requirement: "API-04"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_rest_transport.py::test_every_refusal_subclass_maps_to_a_non_success_status_carrying_its_named_value[EmptyQueryObjectError-ForbiddenSelectorInputError-UnbudgetableParticipantError-UnconsumableQueryMemberError-UnknownTraceReferenceError-UnresolvableEvidenceReferenceError-UnsatisfiableSelectorError]"
        status: pass
      - kind: unit
        ref: "databasise/tests/seam/test_rest_transport.py::test_the_refusal_handler_is_registered_once_at_the_application_level"
        status: pass
    human_judgment: false
  - id: D5
    description: "The REST response passes the same two-tier leak gate databasise/seam/redact.py
      exports, imported rather than reimplemented, over a real serialized response body"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_rest_transport.py::test_the_rest_response_body_passes_both_leak_gate_tiers_via_the_imported_redact_module"
        status: pass
    human_judgment: false
  - id: D6
    description: "Both transports produce the same envelope for the same query and selector, field
      by field over the envelope's complete declared field set (derived by introspection), with
      only the trace reference excluded and named explicitly; the two trace references
      independently resolve to records agreeing on their non-timing/non-run-identity fields"
    requirement: "EMBED-02"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_dual_transport.py::test_both_transports_produce_the_same_envelope_for_the_same_query"
        status: pass
      - kind: unit
        ref: "databasise/tests/seam/test_dual_transport.py::test_the_derived_field_list_is_non_empty_and_the_exclusion_set_is_named_explicitly"
        status: pass
    human_judgment: false
  - id: D7
    description: "The full test suite passes both with the rest extra active (570 passed) and
      without it (552 passed, 2 skipped) — proving the embedded library's dependency set is
      unchanged when the extra is not installed"
    verification:
      - kind: integration
        ref: "cd databasise && uv run --extra rest pytest -q: 570 passed"
        status: pass
      - kind: integration
        ref: "cd databasise && uv run pytest -q: 552 passed, 2 skipped"
        status: pass
    human_judgment: false
  - id: D8
    description: ".planning/phases/04-the-seam/COVERAGE.md records this phase's API coverage
      position and matches exactly what shipped"
    verification:
      - kind: manual_procedural
        ref: "Reconciled by inspection against the four endpoints create_app() registers and the
          four public Databasise operations — no divergence found, no edit needed (see Deviations)"
        status: pass
    human_judgment: true
    rationale: "Reconciliation against a written record is a judgment call about completeness of
      the record itself, not a mechanically-checkable property; documented in this SUMMARY's
      Deviations section for a human/verifier to confirm the 'no changes needed' claim."

duration: 45min
completed: 2026-09-07
status: complete
---

# Phase 4 Plan 5: The Seam — REST Transport, SSE Streaming, Dual-Transport Conformance Summary

**A thin, optional FastAPI transport (`databasise[rest]`) exposes the same four seam operations
in-process already exposes — query, SSE-streaming query, evidence dereference, trace resolution —
through one application factory and one base-class refusal handler, with a conformance test
proving both transports produce field-identical envelopes for the same query and the embedded
library's dependency set is unchanged when the extra is absent.**

## Performance
- **Duration:** ~45 min
- **Started:** 2026-09-06 / **Completed:** 2026-09-07
- **Tasks:** 3 (plus one pre-answered checkpoint) / **Files created:** 3 / **Files modified:** 4

## Package Legitimacy Confirmation

**Confirmed by the developer 2026-09-06** (recorded in
`.planning/phases/04-the-seam/04-CHECKPOINT-ANSWERS.md`, applied verbatim by this executor):
`approved` for all three of `fastapi`, `uvicorn`, and `httpx`. All three resolve to their
canonical repositories (`fastapi/fastapi`, `Kludex/uvicorn`, `encode/httpx`) and are already
approved, in-use dependencies of `v1/pyproject.toml` in this same monorepo. The research audit's
`[SUS]` verdict on all three was recorded as a tool data-source artifact (no PyPI download-count
signal, "too-new" on every package's newest-release timestamp), not a substantive finding.

## Accomplishments

- `databasise/seam/rest.py`: `create_app()` builds one `Databasise` instance and wires four
  endpoints, each exactly deserialize → await the identical in-process method → serialize —
  `POST /query`, `POST /query/stream` (SSE via FastAPI's native `fastapi.sse.EventSourceResponse`,
  no `sse-starlette`), `POST /evidence/resolve`, `POST /trace/resolve`. One
  `app.add_exception_handler(SeamRefusalError, ...)` maps every current and future refusal
  subclass to a 422 carrying the refusal's own named attribute(s) — Starlette dispatches by MRO,
  so the handler needs no per-type enumeration of its own.
- `databasise/seam/engine.py`: `query()` is now `return await self._execute(...)`;
  `query_stream()` is a new async generator over the identical `_execute()`, yielding one SSE
  event per evidence reference then one final event with every remaining field — the streaming
  variant D-16 requires, sharing selector resolution, execution and redaction by construction
  rather than convention.
- `databasise/seam/trace_store.py`: `TraceStore`'s SQLite connection now opens with
  `check_same_thread=False` (Rule 3 — see Deviations) — the engine is constructed once but served
  from whatever thread the ASGI app's event loop runs on, which differs from the constructing
  thread under `starlette.testclient.TestClient`.
- `databasise/pyproject.toml`: `[project.optional-dependencies] rest = ["fastapi>=0.135",
  "uvicorn"]` (never `[dependency-groups]`, which a `pip install package[group]` cannot reach);
  `httpx>=0.28.1` added to the existing `dev` group.
- `databasise/tests/seam/test_rest_transport.py` (16 tests) and
  `databasise/tests/seam/test_dual_transport.py` (2 tests): the tracer, the import-guard and
  no-seam-logic-call AST-walk proofs, SSE content-equality, the four-operation REST/in-process
  parity checks, the parametrized refusal-mapping proof over all 7 currently-defined
  `SeamRefusalError` subclasses, the leak-gate proof over a real REST response body, and the
  field-by-field dual-transport conformance test with the trace-record cross-check.
- `databasise/tests/test_embed_startup.py`: Test 5's dependency-count assertion updated to
  separate unconditional from extra-gated `Requires-Dist` entries (Rule 3 — see Deviations).

## Task Commits
1. **Checkpoint (pre-answered): package legitimacy** — applied verbatim, no separate commit (recorded above)
2. **Task 1: REST transport tracer, one endpoint (D-15, D-17)** — `699b9c5` (feat)
3. **Task 2: SSE streaming, refusal mapping, evidence/trace endpoints (API-04, D-16, D-10)** — `4c16d20` (feat)
4. **Task 3: Dual-transport conformance test, embeddability regression fix (D-17)** — `8080aa7` (feat)

**Plan metadata:** committed after this SUMMARY (see completion report for hash).

## Files Created/Modified
- `databasise/seam/rest.py` — `create_app()`, `QueryRequest`/`TraceRequest` DTOs, the one
  `SeamRefusalError` exception handler
- `databasise/seam/engine.py` — `query()`/`_execute()` split; `query_stream()` added
- `databasise/seam/trace_store.py` — `check_same_thread=False` on the SQLite connection
- `databasise/pyproject.toml` — the `rest` extra; `httpx` added to `dev`
- `databasise/tests/seam/test_rest_transport.py` — 16 tests (Tasks 1 and 2)
- `databasise/tests/seam/test_dual_transport.py` — 2 tests (Task 3)
- `databasise/tests/test_embed_startup.py` — Test 5's dependency-count assertion corrected for the
  new optional extra

## Decisions Made

See `key-decisions` above for the checkpoint application, the FastAPI version floor, EMBED-02's
partial-scope resolution (FA-10), and the streaming design. Also:

- The refusal HTTP status is uniformly 422 across every refusal kind (empty query object,
  unconsumable member, unsatisfiable selector, forbidden selector input, unknown trace reference,
  unbudgetable participant, unresolvable evidence reference) — all are "the request, as given,
  cannot be satisfied," never a 400 (malformed request) or 500 (machine fault).
- The REST layer's own request DTOs (`QueryRequest`, `TraceRequest`) are separate, logic-free
  Pydantic models — never the seam's own frozen `QueryObject`/`Selector`, which stay exactly as
  04-01/04-03 declared them. Nesting `QueryObject`/`Selector` as fields inside a wrapper DTO adds
  no logic; it exists only so FastAPI has a request-body shape.

## Deviations from Plan

**1. [Rule 3 — blocking issue] `TraceStore`'s SQLite connection required `check_same_thread=False`.**
- **Found during:** Task 1, running the tracer test through `starlette.testclient.TestClient`.
- **Issue:** `Databasise.__init__` opens `TraceStore`'s SQLite connection once, in whatever thread
  constructs the engine. `TestClient` runs the ASGI app's event loop on its own `anyio` portal
  thread — different from the thread that built the `Databasise` instance in the test fixture.
  `sqlite3.connect()`'s default `check_same_thread=True` raised `sqlite3.ProgrammingError` the
  instant a request handler tried to use the connection.
- **Fix:** `sqlite3.connect(db_path, check_same_thread=False)`, documented in `trace_store.py`'s
  own module docstring with the exact reasoning: access is always sequential (one thread at a
  time), never concurrent, so disabling the same-thread check is the correct, safe escape hatch —
  distinct from `databasise/stores/kv.py`'s own documented, deliberately-deferred version of this
  same question (which is about genuine multi-threaded concurrent access under the runner's
  structured concurrency, not addressed by, or needed for, this change).
- **Files affected:** `databasise/seam/trace_store.py`.
- **Verification:** `databasise/tests/seam/test_rest_transport.py`'s tracer test passes; the full
  seam suite (104 tests with the extra active) passes.
- **Commit:** `699b9c5`.

**2. [Rule 3 — blocking issue] `tests/test_embed_startup.py` Test 5's dependency-count assertion
broke when the `rest` extra was added.**
- **Found during:** Task 3, running the full suite with `--extra rest` active.
- **Issue:** `importlib.metadata.distribution("databasise").requires` includes every
  `[project.optional-dependencies]` entry as a `Requires-Dist` line (each marked `; extra ==
  "rest"`), inflating the previously-exact count of 6 to 8. This is Phase 1's own EMBED-01
  falsifier test, not named in this plan's `<files_modified>` list, but the failure was caused
  directly by this plan's own change.
- **Fix:** The test now separates unconditional (`extra ==` absent) from extra-gated requirements
  before asserting the count of 6 — the metadata-level proof that D-15's claim ("the embedded
  library's dependency set is unchanged") actually holds, plus a new assertion that every
  extra-gated entry is gated behind exactly `"rest"`.
- **Files affected:** `databasise/tests/test_embed_startup.py`.
- **Verification:** `uv run --extra rest pytest -q tests/test_embed_startup.py` — 8 passed.
- **Commit:** `8080aa7`.

**3. [Sequencing note, not a Rule 1-4 deviation] `databasise/seam/rest.py`'s streaming endpoint,
evidence/trace endpoints, and exception handler were all written in Task 1's own commit
(`699b9c5`), one task ahead of Task 2's own plan text.**
- **Why:** The file was authored as one coherent module in a single pass; the plan's own
  task-by-task `<files>` breakdown names `rest.py` under both Task 1 and Task 2. Task 1's own
  acceptance criteria (a working `create_app`, the tracer test, the two AST-walk proofs) all
  passed against the file as committed, so this is a commit-granularity note, not a functional gap
  — mirrors 04-01-SUMMARY.md's own precedent for the identical kind of note.
- **Impact:** None on shipped behaviour. Task 2's own commit (`4c16d20`) supplies only the tests
  that exercise the code already present, documented explicitly in that commit's own message.

**4. [Not a deviation — explicit non-change] `.planning/phases/04-the-seam/COVERAGE.md` required
no edits.** Task 3's instruction was to reconcile the planner-authored COVERAGE.md against what
shipped, correcting only what diverged. The exposed-operation table already named exactly the four
operations this plan built (query, streaming query, evidence dereference, trace resolution) across
exactly the two transports this plan proves equivalent — no row was missing, no row claimed an
operation that does not exist, and no operation shipped that the table does not name. No edit was
made rather than a cosmetic one for its own sake.

**Total deviations:** 2 auto-fixed (Rule 3, both blocking issues), 1 sequencing note, 1 explicit
non-change.
**Impact on plan:** None on the plan's own stated goals — every task's acceptance criteria and the
plan-level `<verification>` block all pass, including the full suite both with and without the
`rest` extra active.

## Requirement Note: EMBED-02 Partial Scope (FA-10)

EMBED-02's own requirement text names "the REST + MCP server ... one seam, two transports." This
plan ships the REST half only, proven by the dual-transport conformance test (D6 above) and the
full suite's both-with-and-without-extra pass (D7). The MCP transport is CONTEXT.md's Deferred
Idea `API-07`, out of this phase's scope entirely — no plan in this phase attempts it. Marked
complete per this plan's own FA-10 instruction to state the qualification here rather than leave
it unqualified; a later phase shipping `API-07` inherits the identical thin-adapter/one-seam
invariant this plan already proves for REST, not a fresh design question.

## User Setup Required

None. The REST transport is optional and off by default (`databasise[rest]` must be explicitly
installed). No external service configuration is required. An operator choosing to run the REST
app in production is responsible for binding, TLS termination, and access control — stated
explicitly in `databasise/seam/rest.py`'s own module docstring (T-04-25, T-04-26; disposition:
transfer) and in `.planning/phases/04-the-seam/COVERAGE.md`'s "Authentication and transport
hardening" section.

## Next Phase Readiness

Phase 4 ("The Seam") is now complete: all five plans (query object + envelope, evidence + token
accounting, selectors + alias registry, trace token + MACH-11 + leak gate, REST transport) have
landed. ROADMAP criterion 5 — "the same seam reachable two ways with identical behavior" — is
proven by this plan's dual-transport conformance test. No blockers for the next phase; the seam's
envelope, refusal vocabulary, and both transports are frozen inputs a later phase's LightRAG
ingest/opaque-side work (Phase 5) can build against without reopening this phase's own decisions.

## Self-Check: PASSED

- `databasise/seam/rest.py`, `databasise/tests/seam/test_rest_transport.py`,
  `databasise/tests/seam/test_dual_transport.py` — all present (`[ -f ]` verified).
- `git log --oneline --all --grep="04-05"` returns 3 commits (`699b9c5`, `4c16d20`, `8080aa7`).
- `cd databasise && uv run --extra rest pytest -q tests/seam/ -x` — 104 passed.
- `cd databasise && uv run --extra rest pytest -q` — 570 passed.
- `cd databasise && uv run pytest -q` (no extra) — 552 passed, 2 skipped (the two REST-dependent
  modules skip cleanly via `pytest.importorskip`).
- `cd databasise && uv run --extra rest python -m databasise.tools.check_import_boundary` — exit 0,
  no violations.
- `cd databasise && uv run --extra rest python -c "from databasise.seam.rest import create_app; print('ok')"` — prints `ok`.
- `cd databasise && uv run --extra rest python -c "from fastapi.sse import EventSourceResponse; print('ok')"` — prints `ok`.

---
*Phase: 04-the-seam*
*Completed: 2026-09-07*
