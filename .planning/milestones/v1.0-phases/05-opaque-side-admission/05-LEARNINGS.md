---
phase: 05
phase_name: "opaque-side-admission"
project: "Databasise 2.0 — Fully Agnostic System"
generated: "2026-09-09"
counts:
  decisions: 22
  lessons: 16
  patterns: 20
  surprises: 12
missing_artifacts:
  - "UAT.md"
---

# Phase 05 Learnings: opaque-side-admission

## Decisions

### Admission enforcement keys on `Part.kind == "opaque"`, not `structural_depth`
`PartRegistry.register` refuses an executable opaque part with no admission record by testing `kind`, not `structural_depth`. The plan's Task 2 action text said `structural_depth`, but that would have refused the already-shipped `lightrag/embedder-index@0.1.0` (structural_depth opaque, kind embedder, no admission record) and broken `default_registry()` entirely.

**Rationale:** `kind` is what `derive_execution_mode` already keys its subprocess-placement decision on, so the two checks now agree; the plan's own `must_haves.truths` wording also said `kind`.
**Source:** 05-01-SUMMARY.md

---

### Un-exposed token spend reports `unbudgetable`, never a fabricated zero
`full_ingest_body` reports `tokens.counted_by="unbudgetable"` because v1's `apipeline_process_enqueue_documents` exposes no per-run token count back to the caller.

**Rationale:** A zero would be a fabricated fact. The seam's existing `UnbudgetableParticipantError`/`assemble_token_breakdown` mechanism was exercised for the first time against a real, non-fixture part.
**Source:** 05-01-SUMMARY.md

---

### Real zero token spend (`counted_by="none"`) is distinct from `unbudgetable`
`codebase_memory_mcp_body` reports `TokenAccounting()` with `counted_by="none"`, not the LightRAG ports' `unbudgetable` sentinel.

**Rationale:** This engine makes zero LLM calls across its fifteen-tool surface, so "no spend occurred" is the true fact, distinct from "spend occurred but was not exposed to this caller."
**Source:** 05-06-SUMMARY.md

---

### `run_wiring` returns an additive `node_exceptions` map
A subprocess-level dispatch failure never propagates out of `scheduler.run_wiring` (CONTRACT §9: partial outcomes are never discarded). An additive `node_exceptions` map on the returned dict lets `Databasise.ingest()` recover the real exception object and re-raise it as `ForeignEngineRefusalError`.

**Rationale:** Only a stringified `NodeTrace.cross_process_failure_cause` was recoverable before; the caller needs the real object.
**Source:** 05-01-SUMMARY.md

---

### v1 string constants are duplicated as bare literals, never imported
`FULL_DOCS_FORMAT_RAW`/`_PENDING_PARSE` are repeated as literals in `databasise/seam/engine.py` rather than imported from `lightrag.constants`.

**Rationale:** Importing `lightrag` anywhere under `databasise/` outside the named subprocess-entry-point exclusion list is exactly what `check_import_boundary.py` forbids.
**Source:** 05-01-SUMMARY.md

---

### MACH-04 five-engine survey list adopted as a stated default, not a sourced list
The researcher's default list (codebase-memory-mcp, postgres-mcp, supabase-mcp, code-graph-rag, a foreign-hosted LightRAG server) was adopted as-is with provenance stated in the document itself. code-graph-rag's endpoint-injection acceptance is recorded `[inference]`, not a verified yes.

**Rationale:** Falsifier 8 is explicitly non-gating and `accepted-as-stated-risk`; the output is a document and a correction is a one-edit change. Rated reversible.
**Source:** 05-02-PLAN.md, 05-02-SUMMARY.md

---

### DR-04/HARD-03 closed on `two-covering-rationale` with `selection_is_clean: false`
Both coverings were checked against live code before selection. Covering 1's §7 partial-coverage refusal has no implementation anywhere; covering 2 (`EvidenceRef`) is missing all four ChunkRef members per Phase 4's FA-03.

**Rationale:** A clean-yes selection would have been the rounding-up this phase's own admission discipline forbids.
**Source:** 05-02-SUMMARY.md

---

### Document-id token regex widened to permit underscore
`_DOCUMENT_ID_TOKEN_RE` changed from `[A-Za-z0-9-]+` to `[A-Za-z0-9_-]+`.

**Rationale:** Every document id in the Phase 3 parity corpus contains an underscore; the prior pattern refused every real document. Underscore introduces no path-traversal risk since no `/`, `\`, or bare `.` is newly permitted.
**Source:** 05-03-SUMMARY.md

---

### Two ports of one engine carry two admission records, each in its own words
`lightrag/full-delete@0.1.0` states every one of its eleven verdicts itself rather than importing `lightrag/full-ingest@0.1.0`'s tuple, even where the evidence (environment hash, network-denial technique) is identical.

**Rationale:** CONTRACT §19.6's "two ports, two records" reading.
**Source:** 05-03-SUMMARY.md

---

### Declared ceilings are measured, margined, and never raised to make a test pass
`DELETE_WALL_CLOCK_CEILING_SECONDS` stayed at 300.0 against a measured 2.91s run. `codebase-memory-mcp`'s 120.0s ceiling was grounded in one real 2.88s cold-start `index_repository` measurement with a stated ~40x margin.

**Rationale:** The engine self-reports no ceiling anywhere; a ceiling must be grounded in a measurement, and raised only on measured evidence.
**Source:** 05-03-SUMMARY.md, 05-06-SUMMARY.md

---

### `mcp` and `python-multipart` cleared through a blocking package-legitimacy checkpoint
Both packages had `[SUS]` verdicts from the research audit. The human confirmed both resolve to their official upstream repos before either was added to `pyproject.toml`.

**Rationale:** The `[SUS]` flags were download-count blind spots in the checking sandbox, not slopsquat signatures. The checkpoint was not auto-approvable regardless of `workflow.auto_advance`.
**Source:** 05-04-PLAN.md, 05-04-SUMMARY.md

---

### Bounded status/health/counts reads reach the §17 adapter directly, never a registered Part
`get_job_status`/`health`/`corpus_status`/`document_counts` call `databasise.foreign.run_corpus_op` directly rather than dispatching a Part through the scheduler.

**Rationale:** A status read produces no evidence, mutates nothing, and declares no effect, so it stays structurally distinct from `ingest`/`delete_document`'s opaque-Part dispatch.
**Source:** 05-04-SUMMARY.md

---

### The `mcp` extra was added without a `[tool.setuptools] packages` entry until 05-07
05-04 declared the `mcp` optional-dependency extra but left the packages entry to 05-07, which creates the directory it names.

**Rationale:** A `uv sync` between the two plans must never name a directory that does not exist.
**Source:** 05-04-SUMMARY.md

---

### `environment_hash` is a boundary field but is pinned structurally, not by literal digest
The compat test checks `environment_hash` is non-empty, `sha256:`-prefixed, and equal between sibling ports. It does not pin the computed value.

**Rationale:** The digest legitimately drifts with a `v1/uv.lock` bump, which the rule document itself declares free to change. A literal pin would make a free change a false-positive boundary violation.
**Source:** 05-05-SUMMARY.md

---

### `AdmissionRecord`'s field set is checked via `dataclasses.fields()`, not a hand list
The compat test compares the live field-name set against a pinned frozenset.

**Rationale:** A new field added to `AdmissionRecord` fails the test immediately as an unclassified boundary widening, instead of passing silently because a hand-written projection never looked at it.
**Source:** 05-05-SUMMARY.md

---

### Optional `mcp` SDK imported lazily, function-scoped, after the binary is resolved
`codebase_memory_mcp_adapter.py` imports `mcp`/`anyio` inside `_run_with_session`, never at module level. The binary is resolved before the import.

**Rationale:** The module is reached from `default_registry()` unconditionally; a module-level import would fail nearly the whole test suite on a bare install. Resolving the binary first means `ForeignEngineUnavailableError` still fires cleanly without the extra.
**Source:** 05-06-SUMMARY.md

---

### Every `codebase-memory-mcp` item is tier-capped `below_T1` unconditionally
The cap applies regardless of tool or which fields a raw item carries.

**Rationale:** The engine supplies neither `recipe_at_version` nor `ordinal` for any tool (PARTS.md §X: "Recipe: n/a"), so no item can ever reach full T1 ChunkRef coverage. This is a structural finding, not a per-call gap.
**Source:** 05-06-SUMMARY.md

---

### `mutates_store` added additively to `CODEBASE_MEMORY_MCP_PART.effects`; discrepancy recorded, not resolved
The pre-existing `self_storage`/`fs` effects stay even though PARTS.md §X declares `mutates_store` only.

**Rationale:** `self_storage`/`fs` are already pinned as committed Falsifier-2 evidence from an earlier phase. The discrepancy is recorded in `ADMISSION-CODEBASE-MEMORY-MCP.md` rather than silently resolved either direction.
**Source:** 05-06-SUMMARY.md

---

### API-07's tool set ships as `ingest/query/delete/status/resolve`, not the literal `compare`
`compare` is absent because the comparison operation is API-08 (Phase 6) and exists behind no transport. `resolve` is added because Phase 4 shipped evidence dereference and trace resolution over REST, which an MCP client otherwise cannot follow. Both are one intention with a scope argument, not two tools.

**Rationale:** ROADMAP criterion 5 requires the MCP surface to match REST's capabilities; a stub tool would break parity in the other direction.
**Source:** 05-07-PLAN.md

---

### The shadow-safe SDK resolver excludes all of `databasise/` except the active venv
`_mcp_sdk_guard.py` strips every `sys.path` entry resolving inside the project source tree (excluding the venv's site-packages) before delegating to importlib, and evicts a wrongly-cached shadow first. It is shared by `databasise/mcp/_sdk.py` and `codebase_memory_mcp_adapter.py`.

**Rationale:** A narrower check scoped to `databasise/mcp/` caught only one of the two independently reproducing shadow shapes.
**Source:** 05-07-SUMMARY.md

---

### Lower-severity findings disposed explicitly with named triggers, not silently dropped
WR-02 (unchecked `tool` name forwarded to the foreign binary) deferred: unreachable today, wrong requirement set, and the correct guard is a COVERAGE-row subset decision. IN-02 (`IngestDocument(...)` construction loses refusal shape in both transports) deferred: a both-transports defect, not a parity divergence. 05-VALIDATION.md deferred to `/gsd-validate-phase 5`.

**Rationale:** Each item carries a trigger (first wiring declaring `config` for the part; Phase 6 review or next ingest-path edit; after both gap-closure plans land).
**Source:** 05-08-PLAN.md, 05-09-PLAN.md, 05-09-SUMMARY.md

---

### `MalformedBase64PayloadError` lives in the seam, not the MCP transport
The refusal is defined in `databasise/seam/refusals.py` and stores only `field`, never payload content. No `validate=True` was added to `b64decode`.

**Rationale:** REST's transitive `SeamRefusalError` subclass walk discovers it regardless of which extras are installed. The reproduction string already raises `binascii.Error` under default mode, so `validate=True` would be an unrequested behavior change.
**Source:** 05-09-SUMMARY.md

---

## Lessons

### A `SeamRefusalError` raised inside a pydantic validator loses its own exception object
`SeamRefusalError` subclasses `ValueError`, which pydantic v2 converts into `pydantic.ValidationError` at the construction call site. Starlette's exception middleware matches by `type(exc).__mro__`, so the registered `SeamRefusalError` handler never fires and the response is a 500, not a 422. This was the root cause of the REST page-cap bug (05-04), the MCP page-cap crash (05-09), and the deferred IN-02.

**Context:** The workaround is to raise the refusal directly in a route-adjacent helper before the model is constructed. `PageSizeExceededError` and `AmbiguousIngestPayloadError` embed their class name in their message as a second workaround. Changing the base class is a phase-scale decision.
**Source:** 05-04-SUMMARY.md, 05-09-PLAN.md, 05-01-SUMMARY.md

---

### Naming a subpackage after a third-party SDK collides in two independent shapes
`databasise/mcp/` shadows the real `mcp` SDK via (1) a CWD-shaped `sys.path[0]=''` entry resolving the regular package, and (2) a PEP 420 namespace-package leak from the `__init__.py`-less `databasise/tests/mcp/` once pytest inserts `databasise/tests/` onto `sys.path`. Both were confirmed live, and the second silently broke 05-06's pre-existing `importlib.util.find_spec("mcp")` guards.

**Context:** Not anticipated by 05-RESEARCH.md or the plan. Any future third consumer of the real SDK must route through `_mcp_sdk_guard.py` or will rediscover both shapes.
**Source:** 05-07-SUMMARY.md

---

### `pytest.importorskip("mcp")` does not skip reliably when the SDK is absent in this layout
The phantom namespace package "successfully" imports, so the `ImportError` never raises and collection crashes later. A genuinely bare `uv sync` produced a collection error, not a clean skip.

**Context:** Replaced with `try: import databasise.mcp except ImportError: pytest.skip(...)`, reaching the real failure through the shadow-safe init chain.
**Source:** 05-07-SUMMARY.md

---

### Adding `tests/mcp/__init__.py` would register the test package as `sys.modules["mcp"]`
Under pytest's prepend import mode, the dotted name walks up while `__init__.py` exists. `databasise/tests/__init__.py` does not exist, so the test file would import as bare `mcp.test_dual_transport_parity`.

**Context:** The plan's own file list named this file. Omitting it mirrors the existing `databasise/tests/fixtures/` precedent.
**Source:** 05-07-SUMMARY.md

---

### A module-level import of an optional extra breaks the whole suite when the module is reachable from `default_registry()`
The first draft of `codebase_memory_mcp_adapter.py` imported `mcp` at module level, and nearly every test failed with `ModuleNotFoundError` on a bare install.

**Context:** Only an actual `list_tools()`/`call_tool()` needs the extra; importing the module or registering the Part never does.
**Source:** 05-06-SUMMARY.md

---

### Narrow `isinstance` classification of node failures let unclassified failures fabricate success
`ingest()` only checked for `CorpusOpSubprocessError`/`CorpusOpTimeoutError`. A `MissingV1InterpreterError` fell through to a fabricated `IngestJob(enqueued=0)` with no exception; `delete_document()` degraded the same case to a causeless `DeletionOutcome(status="fail")`. Happy-path tests passed throughout.

**Context:** Found only by live reproduction during verification, not by the plan's own tests. The fix reads the scheduler's `node_exceptions`/`results` maps directly with no type test, in one shared helper.
**Source:** 05-VERIFICATION.md, 05-08-SUMMARY.md

---

### Real-corpus tests surface what stub fixtures cannot
The underscore-refusing regex and the doc-status-dependent `entities` op were both invisible to stub-driven tests and only appeared when the real Phase 3 parity build was exercised.

**Context:** The stub driver echoes what it is told; a fixture id without underscores passes a regex that every real id fails.
**Source:** 05-03-SUMMARY.md

---

### A doc_id-keyed lookup cannot observe post-deletion state
`adelete_by_doc_id` removes the document's doc-status record, so the `entities` op (keyed on doc_id) returned an empty map after deletion regardless of the graph's real state. The shared-entity assertion would have failed for the wrong reason.

**Context:** Added an `entity_info` op that looks entities up by name via `get_entity_info`, independent of any doc-status record.
**Source:** 05-03-SUMMARY.md

---

### Plan action text can contradict the plan's own `must_haves.truths`
05-01's Task 2 said `structural_depth`; the truths said `kind`. 05-05's Task 1 acceptance criteria named 11 identifiers while Task 2 required every `AdmissionRecord` field, so the anti-drift test would have failed on a documentation gap, not a real drift.

**Context:** Resolve toward the truths, toward not breaking already-shipped parts, and toward document completeness.
**Source:** 05-01-SUMMARY.md, 05-05-SUMMARY.md

---

### Literal grep acceptance criteria are matched by docstrings and table separators
A compact `|---|` separator row does not match `grep -c '^| '`. A docstring containing `Page(limit=limit, offset=offset)` inflated a `grep -cE 'Page\(limit='` count that only excluded `#` comment lines.

**Context:** Both were cosmetic rewrites, but each would have failed the plan's own literal check.
**Source:** 05-02-SUMMARY.md, 05-09-SUMMARY.md

---

### A system-wide process-count assertion is flaky on a developer machine running other instances
Counting all `codebase-memory-mcp` processes drifted between measurements for reasons unrelated to the adapter.

**Context:** Count only direct children of the test process via `pgrep -P <os.getpid()>`.
**Source:** 05-06-SUMMARY.md

---

### Parallel worktrees lack `v1/.venv` and `v1/.parity_working_dir`, so test-count baselines differ
The "no fewer than 738 passed" baseline read 730/731 in worktrees because 11-12 pre-existing `skipif` gates depend on those gitignored builds.

**Context:** Compare `passed + skipped` against the recorded baseline instead of `passed` alone; read each skip reason to confirm none touches the plan's own files.
**Source:** 05-08-SUMMARY.md, 05-09-SUMMARY.md

---

### `git stash` in a worktree-isolated agent touches a shared ref
The stash ref is shared across all worktrees off one repo. Recovered immediately via `git stash pop` in the same turn.

**Context:** Compare against a baseline with `git show <commit>:<path> > /tmp/...` instead, which never touches the working tree or any shared ref.
**Source:** 05-08-SUMMARY.md

---

### Removing an import in Task 1 broke Task 2's still-referencing code
Task 1's action text said to prune the two exception-type imports, but `delete_document()` still referenced them until Task 2's fix landed. Pruning early would have raised `NameError` in the full-suite `<verify>` Task 1 itself runs.

**Context:** Sequence the pruning to the task after which no reference remains; every intermediate commit must stay green.
**Source:** 05-08-SUMMARY.md

---

### A mass status revert left five never-defective requirement rows stale
Commit `7c5b9f1` flipped all 8 Phase-5 rows to `Gaps Found` when the phase status was `gaps_found`, but only three requirements carried actual defects. Gap-closure restored those three; the other five were never restored.

**Context:** Revert requirement status per-requirement from the verifier's own assessment, not en masse from the phase status.
**Source:** 05-VERIFICATION.md

---

### An unrelated live-endpoint parity test flakes on shared on-disk state
`tests/parity/test_naive_arm_end_to_end.py` shares `v1/.parity_v2_store` and is order-dependent. It passed in isolation and in every other full-suite run.

**Context:** Pre-existing test-isolation concern, out of scope for the plan that observed it; not investigated further.
**Source:** 05-07-SUMMARY.md

---

## Patterns

### Subprocess-backed opaque Part body
A leaf driver script runs under v1's pinned interpreter, JSON over stdin/stdout, launched by a timeout-parameterized adapter (`run_corpus_op`). Mirrors Phase 3's read-only `v1_arm.py`/`v1_driver_script.py` for the write side.

**When to use:** Any foreign engine whose imports must never enter the `databasise/` import boundary.
**Source:** 05-01-SUMMARY.md

---

### Admission enforced at registration time, not only at run time
`PartRegistry.register` refuses an executable opaque part with no admission record or an invalid one (`UnadmittedOpaquePartError`, `validate_admission`).

**When to use:** Any invariant that should fail at wire time rather than mid-run.
**Source:** 05-01-SUMMARY.md

---

### Generic subclass-enumerating refusal-mapping test with a factory per subclass
`test_rest_transport.py` walks every `SeamRefusalError` subclass and requires a registered factory in `_REFUSAL_FACTORIES`. Adding a refusal without one fails loudly.

**When to use:** Any closed vocabulary that must stay complete across transports. Fired three times this phase (05-03, 05-04, 05-09).
**Source:** 05-03-SUMMARY.md, 05-04-SUMMARY.md, 05-09-SUMMARY.md

---

### Transport-local `_checked_page` pre-check raising the refusal before model construction
Raise `PageSizeExceededError` directly in a route-adjacent helper; never let `Page`'s own validator raise it. Each transport owns its own copy, never importing across the fastapi boundary.

**When to use:** Any refusal that would otherwise be raised inside a pydantic validator.
**Source:** 05-04-SUMMARY.md, 05-09-SUMMARY.md

---

### One shared no-result-is-a-refusal helper for every write operation
`_node_result_or_refuse(scheduled, node_id, operation)` reads `node_exceptions`/`results` directly. Any recorded exception refuses with `.cause` set to it; a node with neither refuses with a synthesized cause.

**When to use:** Whenever two call sites classify the same failure; a per-call-site copy had already drifted into two independently incomplete versions.
**Source:** 05-08-SUMMARY.md

---

### A second adapter deliberately structured like the first as Falsifier 6 evidence
`codebase_memory_mcp_adapter.py` (MCP-over-stdio) mirrors `v1_corpus_adapter.py` (subprocess-JSON): process lifecycle, RPC, health, evidence normalization as the fixed cost. The diff between them is the evidence.

**When to use:** Every future foreign-engine adapter.
**Source:** 05-06-SUMMARY.md

---

### Node-reported vs machine-observed store touches
`NodeContext.record_store_touch` lets a subprocess-hosted `mutates_store` node self-report mutations the scheduler's `_ScopedStoresView` cannot observe. `TOUCH_KIND_OBSERVED` and `TOUCH_KIND_NODE_REPORTED` are correlated together but never merged.

**When to use:** Any opaque node that mutates a store the machine holds no handle to.
**Source:** 05-03-SUMMARY.md

---

### Monkeypatch a module-level default global to redirect a production Part in tests
`monkeypatch.setattr(databasise.foreign.v1_corpus_adapter, "DEFAULT_V1_WORKING_DIR", ...)` redirects the real Part's subprocess at a copied working directory with zero test-only plumbing in production code.

**When to use:** Real-engine integration tests that must drive the unmodified production Part end to end.
**Source:** 05-03-SUMMARY.md

---

### Compat test: enumerate fields generically, pin drifting hashes structurally, derive protocol via AST
`dataclasses.fields()` against a pinned frozenset; `environment_hash` checked for presence/prefix/sibling-agreement; the driver script's per-op stdin/stdout keys derived by walking `_run()`'s if/elif branches, never by importing the script.

**When to use:** Any published boundary that must fail red on an unclassified widening without false-positiving on a free internal change.
**Source:** 05-05-SUMMARY.md

---

### Negative control proving a comparison has teeth
`test_the_comparison_has_teeth_a_mutated_part_copy_differs_from_the_pin` mutates a Part copy and asserts the helper detects it.

**When to use:** Any equality-based guard test; without it a broken comparator passes forever.
**Source:** 05-05-SUMMARY.md

---

### Anti-drift assertion binding a prose rule document to its enforcing test
`test_rule_document_and_check_agree` asserts every identifier the test pins appears in `OPAQUE-BOUNDARY-RULE.md`.

**When to use:** Whenever a human-readable rule and a machine check describe the same set.
**Source:** 05-05-SUMMARY.md

---

### Verdict vocabulary wider than a boolean
`satisfied | confirms-the-rule | open-question | machine-side-obligation` so a not-clean-yes is recorded as what it is rather than forced into pass/fail.

**When to use:** Admission records and evidence documents where rounding up would misstate the finding.
**Source:** 05-06-SUMMARY.md

---

### Evidence-document house format with structural table parsing in tests
Dated header, claim-under-test quoted verbatim, findings table with a per-row `[code-verified]/[docs-verified]/[inference]` tag, verdict, method/limits. Tests parse the markdown table and YAML front matter rather than whole-file grep, so an emptied row fails the specific assertion.

**When to use:** Any committed evidence document.
**Source:** 05-02-SUMMARY.md

---

### Thin-adapter transport with one shared refusal mapper and dict-dispatch for scopes
Every MCP tool body is deserialize, await the identical `Databasise` method REST awaits, return. `_refusal_mapped` turns any `SeamRefusalError` into a `ToolError`. `status`/`resolve` route scopes through `dict[str, Callable]`, never if/elif, keeping the AST forbidden-name proof clean by construction.

**When to use:** Any new transport over the seam.
**Source:** 05-07-SUMMARY.md

---

### Growth-invariant test that registers a real second modality
Register a fixture Part reachable through the capability selector, prove the registry key set grew, then assert the tool count and name set are byte-identical. Forbidden-vocabulary tokens are derived live from the registry and the five production wirings.

**When to use:** Enforcing §18.5's selector-versus-tool rule against any consumer surface.
**Source:** 05-07-SUMMARY.md

---

### Identity capture from inside the invoked method for concurrency tests
Monkeypatch `Databasise.health` to capture `self` on each call and compare with `is`; reading the outer `server.engine` twice would trivially match and prove nothing.

**When to use:** Any "one instance per process" claim.
**Source:** 05-07-SUMMARY.md

---

### Bounded read surface owned by the adapter, never a registered Part
Status/health/counts models are frozen, `extra="forbid"`, and carry no content-bearing field; `test_no_corpus_status_model_declares_a_content_bearing_field` enforces it.

**When to use:** Any introspection endpoint that must never become a corpus dump.
**Source:** 05-04-SUMMARY.md

---

### Scope-decisions table in a gap-closure plan
Each lower-severity item gets INCLUDED or DEFERRED with the reason and, for deferrals, a named trigger to close.

**When to use:** Every gap-closure plan, so nothing is silently dropped.
**Source:** 05-08-PLAN.md, 05-09-PLAN.md

---

### Verification re-reproduces live rather than accepting SUMMARY claims
The re-verification pass monkeypatched `DEFAULT_V1_INTERPRETER` and called both write methods directly, and called `server.call_tool` for both MCP edge cases, printing the observed refusal.

**When to use:** Every gap-closure verification.
**Source:** 05-VERIFICATION.md

---

### Child-process leak check via `pgrep -P <own pid>`
Count only direct children of the test process before and after the call.

**When to use:** Any adapter that spawns a subprocess and must terminate it on both success and failure paths.
**Source:** 05-06-SUMMARY.md

---

## Surprises

### The package name `mcp` itself was the phase's most load-bearing finding
Neither research nor the plan anticipated that `databasise/mcp/` would shadow the third-party SDK. The fix reached back into 05-06's already-shipped adapter and its two test files.

**Impact:** A new shared module (`_mcp_sdk_guard.py`), two test-file guard rewrites, and a constraint on every future SDK consumer in the project.
**Source:** 05-07-SUMMARY.md

---

### Initial verification scored 5/7 and required two gap-closure plans
Both blockers (fabricated ingest success; MCP crashes on page-cap and malformed base64) were found by live reproduction, not by the nine plans' own 738-test suite.

**Impact:** Plans 05-08 and 05-09 were added; the phase closed at 745 tests.
**Source:** 05-VERIFICATION.md

---

### Plan durations ranged from 16 to 165 minutes
05-01: 165 min (24 files). 05-02: 16 min (4 files, docs only). 05-07: 130 min. 05-08: 33 min. 05-09: 40 min.

**Impact:** Documentation-only plans and gap-closure plans are an order of magnitude cheaper than first-of-a-kind infrastructure plans.
**Source:** STATE.md, 05-01-SUMMARY.md, 05-02-SUMMARY.md

---

### A real deletion took 2.91s against a 300s ceiling and reached no LLM call
Deleting `a_kiss_for_corliss` reduced the shared entity Shirley Temple's source set from two chunks to one and removed all 8 orphan-only entities without triggering a partial rebuild.

**Impact:** The real-world cost floor for a rebuild-triggering deletion is still unmeasured; a future run against a document whose deletion triggers a rebuild is the next data point.
**Source:** 05-03-SUMMARY.md

---

### Every real document id was refused by the id regex
The hex-only pattern excluded underscore, which every Phase 3 parity document id contains.

**Impact:** The real-deletion test could not reach the deletion path at all until the regex was widened.
**Source:** 05-03-SUMMARY.md

---

### Both DR-04 coverings fall short of the model text as built
Covering 1's partial-coverage refusal has zero implementation; covering 2's `EvidenceRef` is missing all four ChunkRef members.

**Impact:** HARD-03 closed on a not-clean selection; two concrete, currently-unowned gaps are named in `DR-04-DECISION.md` as the reference point if a requirement is raised later.
**Source:** 05-02-SUMMARY.md

---

### The research audit's `[SUS]` flags were sandbox blind spots
Both `mcp` 2.2.0 and `python-multipart` 0.0.32 resolve to their official upstream repos; the `too-new` flag came from reading the latest release date, not the founding date.

**Impact:** Both packages installed after a human checkpoint; no change to the audit protocol.
**Source:** 05-04-SUMMARY.md

---

### Admission verdicts were code-verified against a different build than the one installed
PARTS.md §X's verdicts were verified against pinned clone `61b3b1b2`; the installed `codebase-memory-mcp` binary is `0.10.8`.

**Impact:** The version drift is recorded in the admission manifest, and a human check on accepting inherited verdicts is deferred to end-of-phase UAT.
**Source:** 05-06-SUMMARY.md

---

### The `entities` op returned nothing after deletion for a design reason, not an over-deletion
The doc-status record the op keys on was already removed by the deletion itself.

**Impact:** A new `entity_info` op was needed for the "after" side of the proof; without it the shared-entity assertion would have failed for the wrong reason.
**Source:** 05-03-SUMMARY.md

---

### Two independently reproducing import-shadow shapes, where a narrow fix caught only one
The CWD-shaped `sys.path[0]=''` shadow and the PEP 420 namespace-package shadow from `tests/mcp/` appeared separately; fixing the first exposed the second.

**Impact:** The resolver had to exclude the whole project tree, not just `databasise/mcp/`.
**Source:** 05-07-SUMMARY.md

---

### Worktree test baselines were 7-8 tests lower than the recorded 738
Gap-closure plans executed in fresh worktrees without the v1 build artifacts saw 730/731 passed plus 12 skipped.

**Impact:** The `<verify>` block's literal "no fewer than 738 passed" check could not be used as written; `passed + skipped` reconciled to the baseline plus the plans' own new tests.
**Source:** 05-08-SUMMARY.md, 05-09-SUMMARY.md

---

### Five requirement rows sat at `Gaps Found` after never having been defective
MACH-04, MODAL-02, MODAL-03, API-06, and HARD-03 were reverted en masse with the phase status and never restored.

**Impact:** Traceability-only staleness, flagged by the verifier; corrected in commit `3243502` after verification.
**Source:** 05-VERIFICATION.md
