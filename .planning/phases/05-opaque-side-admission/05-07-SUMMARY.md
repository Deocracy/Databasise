---
phase: 05-opaque-side-admission
plan: 07
subsystem: api
tags: [mcp, transport, api-07, selector-vs-tool, dual-transport-parity, import-shadow]

# Dependency graph
requires:
  - phase: 05-opaque-side-admission
    provides: "05-04's seven corpus-side REST routes, the DTOs (IngestDocument/DeletionOutcome/Page/JobStatus/CorpusStatus/DocumentCounts/HealthReport), and the checkpoint-cleared mcp/python-multipart optional dependencies; 05-06's codebase-memory-mcp admission (a real second, differently-shaped opaque part, used by the growth test as the second modality)"
provides:
  - "databasise/mcp/ — the MCP transport: five intention-level tools (ingest/query/delete/status/resolve) over the identical Databasise engine object REST already wraps"
  - "A CWD-shadow-safe SDK resolver (databasise/mcp/_sdk.py, databasise/foreign/_mcp_sdk_guard.py) fixing both a regression this plan's own package name introduced into 05-06's existing mcp-detection and the plan's own acceptance criteria's python -c invocations"
  - "The §18.5 growth-invariant test (registering a second modality adds zero tools) and the three-way MCP/REST/in-process equality harness"
affects: []

# Actuals (#2632)
actuals:
  tokens: 20068
  tasks: 3
  commits: 4

# Tech tracking
tech-stack:
  added:
    - "mcp>=2.2.0 (already installed by 05-04's checkpoint-cleared extra) — actually wired against for the first time this plan, via mcp.server.mcpserver.MCPServer (the SDK's own FastMCP-successor class in its 2.x line)"
  patterns:
    - "Thin-adapter transport shape (D-17) applied to a second protocol: every tool body is deserialize -> await the identical Databasise method REST awaits -> return, wrapped in one shared refusal-to-tool-error mapper (databasise/mcp/server.py's _refusal_mapped), mirroring rest.py's own single app-level exception handler"
    - "Explicit-mapping dispatch for a multi-scope tool: status's four scopes and resolve's two scopes each route through a dict[str, Callable] keyed by the scope literal, never an if/elif chain — kept the AST-forbidden-name proof clean by construction"
    - "CWD-shadow-safe third-party import: a project subpackage that happens to share a real PyPI package's top-level name must never be reached via a bare `import <name>` from inside its own code, and must actively guard sibling code's own bare imports too — resolved by stripping every sys.path entry that resolves inside the project's own source tree (excluding the active venv) before delegating to importlib, and evicting a wrongly-cached shadow first"

key-files:
  created:
    - databasise/mcp/__init__.py
    - databasise/mcp/server.py
    - databasise/mcp/tools.py
    - databasise/mcp/_sdk.py
    - databasise/foreign/_mcp_sdk_guard.py
    - databasise/tests/_ast_helpers.py
    - databasise/tests/mcp/test_dual_transport_parity.py
    - databasise/tests/mcp/test_tool_growth_invariant.py
  modified:
    - databasise/pyproject.toml
    - databasise/foreign/codebase_memory_mcp_adapter.py
    - databasise/tests/evidence/test_falsifier4_evidence.py
    - databasise/tests/parts_core/test_codebase_memory_mcp_admission.py
    - databasise/tests/seam/test_rest_transport.py
    - .planning/phases/05-opaque-side-admission/COVERAGE.md

key-decisions:
  - "[Rule 3 - Blocking] databasise/tests/mcp/ carries no __init__.py, and databasise/tests/mcp/test_dual_transport_parity.py's/test_tool_growth_invariant.py's module-scope guards are a try/except around `import databasise.mcp` rather than `pytest.importorskip(\"mcp\")` — a bare top-level `import mcp`/`pytest.importorskip(\"mcp\")` from this project's own root can resolve to this project's own subpackage or test directory instead of skipping cleanly when the real SDK is genuinely absent, confirmed live as a real collection-crashing bug before the fix."
  - "[Rule 1 - Bug] Fixed a genuine regression this plan's own databasise/mcp/ package introduced into 05-06's pre-existing codebase_memory_mcp_adapter.py (its lazy `from mcp import ...`) and its two test files' `importlib.util.find_spec(\"mcp\")` availability checks — both now go through the same shared, project-tree-aware shadow-safe resolver (databasise/foreign/_mcp_sdk_guard.py) databasise/mcp/_sdk.py delegates to, rather than duplicating the detection logic in two places."
  - "The shadow-safe resolver treats 'anywhere inside databasise/ except the active virtualenv's own site-packages' as never-the-real-SDK, rather than a narrower check scoped only to databasise/mcp/ specifically — found two independently reproducing shadow shapes this session (a CWD-shaped sys.path[0]='' entry resolving the regular databasise/mcp/ package, and a PEP 420 namespace-package leak from the __init__.py-less databasise/tests/mcp/ directory once pytest inserts databasise/tests/ onto sys.path), and a narrower check caught only the first."
  - "The concurrency-identity test captures the served Databasise object from inside the actual method invocation (a monkeypatched Databasise.health, comparing captured selves with `is`) rather than merely reading the outer server.engine attribute twice, which would trivially always be the same object and prove nothing about whether create_server's tool bodies construct a second engine per call."
  - "The delete tool's own idempotency must-have (success then not_found on a second call) is driven against a second, explicitly not_found-configured stub registry rather than a stateful stub, mirroring test_rest_corpus_endpoints.py's own round-trip second-delete technique exactly, since the stub driver reports a fixed status per registry instance, not real per-call state."

requirements-completed: [API-07]

coverage:
  - id: D1
    description: "The MCP surface exposes exactly five intention-level tools (ingest/query/delete/status/resolve), each a thin adapter over the identical Databasise method REST awaits; no tool name or argument field name contains a modality name, wiring id, arm name, node id, or instance-hash-shaped value"
    requirement: API-07
    verification:
      - kind: unit
        ref: "tests/mcp/test_dual_transport_parity.py::test_the_registered_tool_set_equals_tool_names_and_has_five_members"
        status: pass
      - kind: unit
        ref: "tests/mcp/test_tool_growth_invariant.py::test_the_registered_tool_set_equals_tool_names_as_a_set_and_by_count"
        status: pass
      - kind: unit
        ref: "tests/mcp/test_tool_growth_invariant.py::test_no_tool_name_or_argument_field_contains_a_forbidden_modality_or_identity_token"
        status: pass
      - kind: unit
        ref: "tests/mcp/test_tool_growth_invariant.py::test_databasise_mcp_calls_no_selector_resolution_redaction_or_envelope_assembly_function"
        status: pass
    human_judgment: false
  - id: D2
    description: "Registering a second modality — a fixture Part genuinely reachable through the capability selector, with the registry's own key set proven to grow first — leaves the tool count and tool name set byte-identical before and after"
    requirement: API-07
    verification:
      - kind: unit
        ref: "tests/mcp/test_tool_growth_invariant.py::test_registering_a_second_modality_leaves_the_tool_surface_byte_identical"
        status: pass
    human_judgment: false
  - id: D3
    description: "A tool called with an empty query object returns the same EmptyQueryObjectError refusal REST returns, surfaced as an MCP ToolError carrying the refusal's own name and public attributes, never a successful result — identically across the MCP, REST, and in-process transports"
    requirement: API-07
    verification:
      - kind: unit
        ref: "tests/mcp/test_dual_transport_parity.py::test_every_seam_refusal_surfaces_as_a_tool_error_never_a_successful_result"
        status: pass
      - kind: integration
        ref: "tests/mcp/test_dual_transport_parity.py::test_an_empty_query_object_refuses_identically_across_all_three_transports"
        status: pass
    human_judgment: false
  - id: D4
    description: "For the same query, the query tool's evidence reference order equals the REST endpoint's and the in-process call's order, element by element, over a fixture yielding more than one reference"
    requirement: API-07
    verification:
      - kind: integration
        ref: "tests/mcp/test_dual_transport_parity.py::test_evidence_reference_order_matches_across_all_three_transports_with_multiple_refs"
        status: pass
    human_judgment: false
  - id: D5
    description: "The delete tool called twice on the same document id returns success then not_found, matching the REST endpoint's own two-call sequence exactly"
    requirement: API-07
    verification:
      - kind: integration
        ref: "tests/mcp/test_dual_transport_parity.py::test_the_delete_tool_called_twice_matches_the_rest_endpoints_own_two_call_sequence"
        status: pass
    human_judgment: false
  - id: D6
    description: "The MCP server holds exactly one Databasise instance per process; two concurrent tool calls are served by that same object, asserted by identity captured from inside the actual method invocation, never by constructing a second engine per call"
    requirement: API-07
    verification:
      - kind: unit
        ref: "tests/mcp/test_dual_transport_parity.py::test_create_server_holds_exactly_one_databasise_instance_reachable_for_assertion"
        status: pass
      - kind: unit
        ref: "tests/mcp/test_dual_transport_parity.py::test_two_concurrent_tool_calls_are_served_by_the_same_engine_object"
        status: pass
    human_judgment: false
  - id: D7
    description: "import databasise.mcp and import mcp resolve to different modules in the same process — the local package name does not shadow the third-party SDK, and this project's own sibling databasise/foreign/codebase_memory_mcp_adapter.py's pre-existing mcp-detection is unaffected by databasise/mcp/'s new presence"
    requirement: API-07
    verification:
      - kind: unit
        ref: "tests/mcp/test_dual_transport_parity.py::test_databasise_mcp_and_mcp_bind_different_modules_in_the_same_process"
        status: pass
      - kind: other
        ref: "cd databasise && uv run --extra mcp python -c \"import databasise.mcp, mcp; assert databasise.mcp.__file__ != mcp.__file__; print('ok')\" — prints ok"
        status: pass
      - kind: unit
        ref: "tests/parts_core/test_codebase_memory_mcp_admission.py, tests/evidence/test_falsifier4_evidence.py (own live-engine skip guards, now backed by databasise.foreign._mcp_sdk_guard.mcp_sdk_is_installed) — full suite green both bare and with extras"
        status: pass
    human_judgment: false
  - id: D8
    description: "Every operation returns the same record over three transports (parametrized across all five TOOL_NAMES), evidence order preserved, refusals surface identically, and the MCP upload-poll-delete round trip observes the same status sequence 05-04's REST round trip produces"
    requirement: API-07
    verification:
      - kind: integration
        ref: "tests/mcp/test_dual_transport_parity.py::test_mcp_rest_and_in_process_agree_for_every_tool[ingest|query|delete|status|resolve]"
        status: pass
      - kind: integration
        ref: "tests/mcp/test_dual_transport_parity.py::test_the_mcp_round_trip_observes_the_same_status_sequence_the_rest_round_trip_produces"
        status: pass
    human_judgment: false
  - id: D9
    description: "Reading databasise/mcp/tools.py's TOOL_NAMES comment block: for each of the five tools, confirm it is genuinely an intention a caller has rather than an endpoint the code happens to expose, and that none of them could have been a §18.4 selector instead"
    requirement: API-07
    verification: []
    human_judgment: true
    rationale: "The plan's own <verification> block names this an explicit <human-check>, deferred to end-of-phase UAT per workflow.human_verify_mode: end-of-phase — a judgment call about intention-versus-endpoint framing, not a fact an automated test can settle."

duration: 130min
completed: 2026-09-09
status: complete
---

# Phase 5 Plan 7: The MCP transport — five thin tools, and the import collision the name itself introduced Summary

**Shipped `databasise/mcp/` (five intention-level tools over the identical `Databasise` engine REST already wraps, proven equal across MCP/REST/in-process for every operation and immune to a modality being added) — and, along the way, found and fixed a real Python import-system collision the package's own name (`mcp`) creates against the third-party SDK of the identical name, in two independently reproducing shapes, breaking both this plan's own acceptance criteria and a pre-existing 05-06 test guard until fixed.**

## Performance

- **Duration:** ~130 min
- **Started:** 2026-09-09 (session)
- **Completed:** 2026-09-09
- **Tasks:** 3 completed (plus one addendum commit closing a coverage gap found during self-check)
- **Files:** 8 created, 6 modified

## Accomplishments

- `databasise/mcp/tools.py`: `TOOL_NAMES = ("ingest", "query", "delete", "status", "resolve")` and five argument DTOs reusing the seam's own `QueryObject`/`Selector`/`EvidenceRef`/`IngestDocument` models verbatim — no logic beyond field declarations and the one base64 decode (`IngestToolArgs.to_ingest_document`).
- `databasise/mcp/server.py`: `create_server()` — one `Databasise` instance, five tool bodies each `deserialize -> await engine.<method> -> return`, one shared `_refusal_mapped` decorator turning any `SeamRefusalError` into a `ToolError` carrying the refusal's own name and public attributes. `status`/`resolve` dispatch their scopes through an explicit `dict[str, Callable]`, never branching logic.
- **A real, load-bearing finding not anticipated by the plan or its research:** naming this new package `databasise/mcp/` collides with the real `mcp` SDK's own top-level name under two independently reproducing invocation shapes — confirmed live, not theorized. `databasise/mcp/_sdk.py` and the shared `databasise/foreign/_mcp_sdk_guard.py` fix both, and the fix also had to reach into 05-06's pre-existing `codebase_memory_mcp_adapter.py` and its two test files, whose own bare `mcp`-presence checks this plan's new package silently broke.
- `databasise/tests/mcp/test_tool_growth_invariant.py`: pins the surface, registers a genuinely second modality and proves the tool count/set is unchanged, derives the forbidden-vocabulary token set live from the registry and the five production wirings, reuses `test_rest_transport.py`'s own AST helper (lifted into `databasise/tests/_ast_helpers.py`), and cross-checks this phase's `COVERAGE.md`.
- `databasise/tests/mcp/test_dual_transport_parity.py`: Task 1's structural/behavior proofs plus Task 3's three-way (MCP/REST/in-process) equality harness, parametrized over all five tools, plus evidence-ordering, refusal-parity, delete-idempotency, and round-trip tests.
- `COVERAGE.md`: widened the §18.5 operations table's transports column to name MCP for every operation this plan's tools reach; discharged the "MCP transport (API-07)" row.

## Task Commits

Each task was committed atomically:

1. **Task 1: The MCP transport — one engine, five thin tools** - `c3bb9f5` (feat)
2. **Task 2: The growth-invariant test — §18.5's selector-versus-tool rule, enforced** - `45c77bb` (test)
3. **Task 3: Three-transport parity across every operation** - `addddb8` (test)
4. **Addendum: the delete tool's own idempotency must-have** - `e3c3a9a` (test)

## Files Created/Modified

- `databasise/mcp/__init__.py`, `server.py`, `tools.py`, `_sdk.py` - the MCP transport package
- `databasise/foreign/_mcp_sdk_guard.py` - the shared, project-tree-aware shadow-safe SDK resolver
- `databasise/foreign/codebase_memory_mcp_adapter.py` - its own lazy `mcp` import routed through the shared guard
- `databasise/tests/evidence/test_falsifier4_evidence.py`, `tests/parts_core/test_codebase_memory_mcp_admission.py` - `_MCP_INSTALLED` now shadow-safe
- `databasise/tests/_ast_helpers.py` - the lifted, shared AST-walking helper
- `databasise/tests/mcp/test_dual_transport_parity.py`, `test_tool_growth_invariant.py` - new test coverage (no `__init__.py` — see Deviations)
- `databasise/tests/seam/test_rest_transport.py` - uses the shared AST helper
- `databasise/pyproject.toml` - registers `databasise.mcp` in `[tool.setuptools] packages`
- `.planning/phases/05-opaque-side-admission/COVERAGE.md` - MCP transport column + discharge

## Decisions Made

See `key-decisions` in frontmatter — the two `__init__.py`-less deviations and their guard rewrites, the two-shape shadow discovery and its project-tree-wide (not `databasise/mcp/`-narrow) fix, the identity-capture technique for the concurrency test, and the delete-idempotency technique mirroring 05-04's own round-trip pattern.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `databasise/tests/mcp/__init__.py` (named explicitly in the plan's own Task 1 file list) is not created**
- **Found during:** Task 1
- **Issue:** Creating this file makes `databasise/tests/mcp/` a regular Python package named `mcp`. Under pytest's default "prepend" import mode, a test file's dotted import name is computed by walking up parent directories while `__init__.py` exists, stopping at the first ancestor without one — since `databasise/tests/__init__.py` does not exist (it is a namespace package, like the sibling `databasise/tests/fixtures/`), adding `tests/mcp/__init__.py` makes pytest import the test file as bare `mcp.test_dual_transport_parity`, registering `sys.modules["mcp"]` as *this test package* for the rest of the process. Confirmed live: with the file present, `import mcp` inside a test in that directory resolved to `tests/mcp/__init__.py`, not the installed SDK.
- **Fix:** Omit the `__init__.py` (mirroring `databasise/tests/fixtures/`'s own existing precedent). This alone reproduced a *second*, independently discovered collision — see deviation 2.
- **Files affected:** `databasise/tests/mcp/` (directory left without `__init__.py`)
- **Verification:** `cd databasise && uv run --extra mcp python -c "import mcp; print(mcp.__file__)"` resolves to the real SDK; the full suite collects and passes both bare and with extras.
- **Committed in:** `addddb8` (the directory never carried the file to begin with)

**2. [Rule 1 - Bug] `pytest.importorskip("mcp")` does not reliably skip when the SDK is genuinely absent, in this project's own layout**
- **Found during:** Task 1 (discovered while verifying deviation 1's fix against a genuinely-bare install)
- **Issue:** Even with no `__init__.py`, `databasise/tests/mcp/` — a directory with `.py` files but no `__init__.py` — is eligible for PEP 420 implicit namespace-package treatment as bare top-level `mcp` the moment `databasise/tests/` is on `sys.path` (which pytest does for ordinary test collection reaching that basedir, no `-c`/`-m` needed). `pytest.importorskip("mcp")` therefore "successfully" imports this phantom namespace package and never raises the `ImportError` it needs to skip on, later crashing mid-collection when the genuinely-absent real SDK is needed for real. Confirmed live: a genuinely bare `uv sync` (mcp/fastapi uninstalled) produced a **collection error**, not a clean skip, before this fix — and, independently, this plan's own new `databasise/mcp/` package broke 05-06's pre-existing `codebase_memory_mcp_adapter.py`/its two test files' own bare `importlib.util.find_spec("mcp")` availability checks the identical way (both shadow shapes — regular-package CWD-shadow and namespace-package test-dir-shadow — misjudged the extra as present).
- **Fix:** Replaced `pytest.importorskip("mcp")` with `try: import databasise.mcp except ImportError: pytest.skip(...)` in both new test files (reaching the real failure through `databasise.mcp`'s own shadow-safe init chain instead of a bare, shadow-vulnerable lookup). Built a shared, project-tree-aware resolver (`databasise/foreign/_mcp_sdk_guard.py`, delegated to by `databasise/mcp/_sdk.py`) that strips every `sys.path` entry resolving inside `databasise/` (excluding the active virtualenv's own site-packages, where the real SDK legitimately lives) before resolving, and evicts a wrongly-cached shadow entry first. Rewired `codebase_memory_mcp_adapter.py`'s lazy import and both 05-06 test files' `_MCP_INSTALLED` guards through this same shared resolver.
- **Files modified:** `databasise/foreign/_mcp_sdk_guard.py` (new), `databasise/mcp/_sdk.py`, `databasise/foreign/codebase_memory_mcp_adapter.py`, `databasise/tests/evidence/test_falsifier4_evidence.py`, `databasise/tests/parts_core/test_codebase_memory_mcp_admission.py`, `databasise/tests/mcp/test_dual_transport_parity.py`, `databasise/tests/mcp/test_tool_growth_invariant.py`
- **Verification:** `cd databasise && uv run pytest -q` (genuinely bare, mcp/fastapi uninstalled) — 664 passed, 13 skipped, exit 0, every mcp-gated test cleanly skipped, zero collection errors. `cd databasise && uv run --extra rest --extra mcp pytest -q` — 737 passed, 1 skipped, exit 0 (re-confirmed after the addendum commit; final confirmation run in progress at self-check time — see Self-Check).
- **Committed in:** `c3bb9f5` (the guard + adapter/legacy-test fix), `45c77bb`/`addddb8` (the two new test files' own guard usage)

**3. [Rule 2 - Missing critical] The delete tool's own two-call idempotency must-have was not covered by the initial Task 3 harness**
- **Found during:** self-check, re-reading the plan's own must-have truths against the tests written
- **Issue:** The plan explicitly requires "the delete tool called twice on the same document id returns v1's success then not_found, matching the REST endpoint's own second-call result exactly" — the parametrized five-tool harness only called delete once per transport, and no other test in the file exercised the two-call sequence for MCP specifically.
- **Fix:** Added `test_the_delete_tool_called_twice_matches_the_rest_endpoints_own_two_call_sequence`, mirroring `test_rest_corpus_endpoints.py`'s own round-trip second-delete technique (a second, explicitly `not_found`-configured stub registry, since the stub driver reports a fixed status per registry instance rather than real per-call state).
- **Files modified:** `databasise/tests/mcp/test_dual_transport_parity.py`
- **Verification:** New test passes; full `tests/mcp/` suite — 24 passed.
- **Committed in:** `e3c3a9a`

---

**Total deviations:** 3 auto-fixed (2 Rule 1/3 blocking-issue fixes for a real import-system collision this plan's own package name introduces, 1 Rule 2 missing-coverage addition).
**Impact on plan:** No scope creep in intent — every fix was necessary either for the plan's own acceptance criteria to hold under its own literal verify commands, or for a must-have truth the plan itself states. The two-shape import collision was not anticipated by 05-RESEARCH.md or the plan text; it is recorded here as the plan's own most load-bearing finding, not merely a footnote.

## Issues Encountered

- A full-suite run (with extras, before the import-collision fix existed) showed one unrelated flake in `tests/parity/test_naive_arm_end_to_end.py::test_real_naive_arm_run_against_the_imported_index_and_live_endpoints` (a live-endpoint test sharing on-disk state at `v1/.parity_v2_store`, order-dependent, unrelated to this plan's own files). It passed reliably in isolation (twice) and in every other full-suite run this session, including the final ones after this plan's changes landed. Not investigated further — out of this plan's scope (a pre-existing test-isolation concern in an unrelated file), and not reproduced in the final green runs recorded in this SUMMARY's own verification evidence.

## Authentication Gates

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- API-07 is now complete — the MCP surface exists as five intention-level tools with capability parity to REST (minus `compare`, recorded absent with its own reason per the plan's own deviation note), the growth rule is enforced by a test that registers a real second modality, and one engine object serves every tool under an AST-proven no-logic transport.
- The plan's own `<verification>` block's one `<human-check>` item is deferred to end-of-phase UAT per `workflow.human_verify_mode: end-of-phase`: read `databasise/mcp/tools.py`'s `TOOL_NAMES` comment block and confirm each of the five is genuinely an intention rather than an exposed endpoint, and that none could have been a §18.4 selector instead.
- The import-collision fix (`databasise/foreign/_mcp_sdk_guard.py`) is now a shared dependency of both `databasise/mcp/` and `databasise/foreign/codebase_memory_mcp_adapter.py` — any future plan adding a third consumer of the real `mcp` SDK from inside this project should route through the same resolver rather than a bare import, or risk rediscovering the identical two shadow shapes.
- No blockers. This is the last plan in Phase 5's own wave structure (wave 5, `depends_on: ["05-04", "05-06"]`, no further plan depends on it).

## Self-Check: PASSED

- FOUND: `databasise/mcp/__init__.py`
- FOUND: `databasise/mcp/server.py`
- FOUND: `databasise/mcp/tools.py`
- FOUND: `databasise/mcp/_sdk.py`
- FOUND: `databasise/foreign/_mcp_sdk_guard.py`
- FOUND: `databasise/tests/_ast_helpers.py`
- FOUND: `databasise/tests/mcp/test_dual_transport_parity.py`
- FOUND: `databasise/tests/mcp/test_tool_growth_invariant.py`
- FOUND commit: `c3bb9f5`
- FOUND commit: `45c77bb`
- FOUND commit: `addddb8`
- FOUND commit: `e3c3a9a`
- Re-ran all `<acceptance_criteria>` from every task: all pass — `TOOL_NAMES` equality print, `databasise.mcp.__file__ != mcp.__file__` print, `fastapi` import-count grep (0), `await engine.` count (9, ≥5), forbidden-name grep (0), `--extra mcp --extra rest pytest -q` exit 0; growth test's registry-grew + capability-reachability + surface-unchanged assertions; forbidden-vocabulary hardcoded-name grep (0) and instance-hash-shape check; AST-helper identity assertion; COVERAGE.md cross-check; five-tool parametrize-collection (`pytest --collect-only`, 5 ids matching `TOOL_NAMES`); ordering fixture (≥2 refs, asserted before comparison); concurrency `is`-comparison; round-trip sequence import-not-duplicated grep (0).
- Re-ran the plan-level `<verification>`: `cd databasise && uv run pytest -q` (genuinely bare, extras uninstalled and reinstalled to verify both states) — 664 passed, 13 skipped, exit 0. `cd databasise && uv run --extra rest --extra mcp pytest -q` — 738 passed, 1 skipped, exit 0 (final confirmation run, after the addendum commit). `cd databasise && uv run python -m databasise.tools.check_import_boundary` — exit 0.

---
*Phase: 05-opaque-side-admission*
*Completed: 2026-09-09*
