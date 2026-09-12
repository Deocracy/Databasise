---
phase: 05-opaque-side-admission
plan: 06
subsystem: modality
tags: [opaque-node, admission, mcp, foreign-adapter, codebase-memory-mcp, contract-s8, contract-s17, falsifier-4, falsifier-6]

# Dependency graph
requires:
  - phase: 05-opaque-side-admission
    provides: "05-01's §8 admission-record machinery (AdmissionRecord/ConditionVerdict/validate_admission/cross_check_conditions) and the databasise/foreign/ adapter-layer precedent (v1_corpus_adapter.py); 05-04's confirmation that the mcp/python-multipart optional dependencies were already checkpoint-cleared and installed"
provides:
  - "codebase-memory-mcp@0.1.0 — the second, differently-shaped opaque part, admitted whole-engine with a real body and a real eleven-verdict §8 admission record; no longer a body=None declaration-only stub"
  - "databasise/foreign/codebase_memory_mcp_adapter.py — the §17 foreign-part adapter for the MCP-served engine shape, the concrete second data point for Falsifier 6's fixed-cost claim"
  - "databasise/evidence/FALSIFIER-4-EVIDENCE.md — Falsifier 4 run for real on both legs, not merely declared unrun"
  - ".planning/phases/05-opaque-side-admission/COVERAGE.md — this phase's real capability matrix over a live-enumerated tool surface"
affects: [05-07]

# Actuals (#2632)
actuals:
  tokens: 34000
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A second foreign-part adapter shape (databasise/foreign/codebase_memory_mcp_adapter.py, MCP-over-stdio) deliberately structured like the first (v1_corpus_adapter.py, subprocess-JSON) — process lifecycle/RPC/health/evidence-normalization as the fixed cost, per §17 and Falsifier 6, checkable from the diff between the two rather than merely asserted"
    - "Lazy, function-scoped import of an optional PyPI extra (mcp) inside the one function that actually needs it, never at module level — the module is reached from default_registry() unconditionally, so a module-level import would make nearly the entire test suite fail on a bare install with no extras"
    - "A verdict vocabulary wider than a boolean: satisfied | confirms-the-rule | open-question | machine-side-obligation — so a not-clean-yes stays recorded as what it is rather than being forced into a pass/fail shape"
    - "Per-tool evidence-kind mapping (code_snippet | graph_path | derived_finding) driven by tool name, with a parser for the engine's own observed (undeclared) compact tabular text convention as a best-effort fallback when structured_content is absent"

key-files:
  created:
    - databasise/foreign/codebase_memory_mcp_adapter.py
    - databasise/parts_core/codebase_memory_mcp.py
    - databasise/wirings/codebase-memory-mcp.json
    - databasise/evidence/ADMISSION-CODEBASE-MEMORY-MCP.md
    - databasise/evidence/FALSIFIER-4-EVIDENCE.md
    - databasise/tests/parts_core/test_codebase_memory_mcp_admission.py
    - databasise/tests/evidence/test_falsifier4_evidence.py
    - databasise/tests/fixtures/codebase_memory_mcp_raw_items.json
    - .planning/phases/05-opaque-side-admission/COVERAGE.md
  modified:
    - databasise/parts_core/declared_only.py
    - databasise/pyproject.toml
    - databasise/evidence/FALSIFIER-2-EVIDENCE.md
    - databasise/tests/parts/test_admission.py
    - databasise/tests/parts/test_registry.py

key-decisions:
  - "mcp is imported lazily, function-scoped inside _run_with_session, never at module level — codebase_memory_mcp_adapter.py is reached from default_registry() (via parts_core.codebase_memory_mcp -> parts_core.declared_only), so a module-level import would have made the entire registry, and therefore nearly the whole test suite, fail to import on a bare `uv run pytest -q` with no extras installed. Only an actual list_tools()/call_tool() call needs the extra; importing the module or registering the Part never does. The binary is resolved before that lazy import, so ForeignEngineUnavailableError still fires cleanly even without the mcp extra installed."
  - "Every normalized item's evidence tier is capped below_T1 unconditionally, not merely when a given call happens to omit a field — this engine supplies neither recipe_at_version nor ordinal for any tool at all (PARTS.md ## §X: 'Recipe: n/a'), so no item from this engine can ever reach full T1 ChunkRef coverage regardless of which tool is called or which fields a particular raw item happens to carry."
  - "Token spend for codebase_memory_mcp_body is reported as a real, honest zero (TokenAccounting(), counted_by='none'), not the sibling LightRAG ports' 'unbudgetable' sentinel — this engine has zero LLM calls anywhere in its fifteen-tool surface (condition 3's own evidence), so 'no spend occurred' is the true fact here, distinct from 'spend occurred but was not exposed back to this caller.'"
  - "CODEBASE_MEMORY_MCP_PART.effects gained mutates_store additively, keeping the pre-existing self_storage/fs — the built stub's three declared effects diverge from PARTS.md ## §X's own mutates_store-only declaration, and this discrepancy is recorded in ADMISSION-CODEBASE-MEMORY-MCP.md rather than silently resolved either direction, because self_storage/fs are already pinned as committed Falsifier-2 evidence (w2-codebase-memory-mcp.json / FALSIFIER-2-EVIDENCE.md) from an earlier phase."
  - "The wall-clock ceiling (120.0s) is grounded in one real measurement (2.88s cold-start index_repository against this repository's own databasise/ directory) with a stated ~40x margin for a substantially larger target repository — never invented, since the engine self-reports no ceiling anywhere in its source or README."

patterns-established:
  - "A second port of a second engine shape reuses the first port's adapter structure deliberately, not by coincidence — the diff between v1_corpus_adapter.py and codebase_memory_mcp_adapter.py is itself the evidence Falsifier 6 asks for."

requirements-completed: [MODAL-03]

coverage:
  - id: D1
    description: "The §17 foreign-part adapter for the MCP-served engine shape reaches the real, installed codebase-memory-mcp binary, enumerates its own tool surface live, and normalizes every returned item to a §4 ItemKind member; an untyped tool name, a timeout, and a transport failure are each refused by name carrying their own diagnostic fields"
    requirement: MODAL-03
    verification:
      - kind: integration
        ref: "tests/parts_core/test_codebase_memory_mcp_admission.py::test_list_tools_against_the_live_engine_returns_the_engines_own_nonempty_tool_name_list"
        status: pass
      - kind: integration
        ref: "tests/parts_core/test_codebase_memory_mcp_admission.py::test_a_timeout_raises_a_named_refusal_carrying_the_tool_name_and_ceiling"
        status: pass
      - kind: integration
        ref: "tests/parts_core/test_codebase_memory_mcp_admission.py::test_the_adapter_terminates_the_child_process_on_both_the_success_and_the_failure_path"
        status: pass
      - kind: unit
        ref: "tests/parts_core/test_codebase_memory_mcp_admission.py::test_a_transport_failure_refusal_carries_both_endpoint_placements"
        status: pass
      - kind: unit
        ref: "tests/parts_core/test_codebase_memory_mcp_admission.py::test_normalise_to_item_kind_raises_untyped_for_a_non_evidence_tool_name"
        status: pass
      - kind: integration
        ref: "tests/parts_core/test_codebase_memory_mcp_admission.py::test_a_cross_process_failure_is_recorded_on_the_nodes_trace_never_silently_dropped"
        status: pass
    human_judgment: false
  - id: D2
    description: "codebase-memory-mcp@0.1.0 carries a real, executable body and an eleven-verdict §8 admission record projected from PARTS.md ## §X, with the three not-clean-yeses (condition 1, condition 3, conditions 7/8/9) recorded as such via a non-boolean verdict vocabulary; the ceiling is measured, the version drift is stated, and registration/cross-check succeed"
    requirement: MODAL-03
    verification:
      - kind: unit
        ref: "tests/parts_core/test_codebase_memory_mcp_admission.py::test_the_verdict_vocabulary_contains_a_non_satisfied_value_in_use"
        status: pass
      - kind: unit
        ref: "tests/parts_core/test_codebase_memory_mcp_admission.py::test_the_ceiling_is_strictly_greater_than_the_measured_duration_and_the_basis_names_it"
        status: pass
      - kind: unit
        ref: "tests/parts_core/test_codebase_memory_mcp_admission.py::test_registering_the_part_succeeds_and_validate_admission_and_cross_check_conditions_pass"
        status: pass
      - kind: integration
        ref: "tests/parts_core/test_codebase_memory_mcp_admission.py::test_the_live_tool_surface_matches_the_admission_records_known_tool_names"
        status: pass
      - kind: unit
        ref: "tests/validator/test_falsifier2_evidence.py::test_committed_evidence_document_matches_a_fresh_render"
        status: pass
    human_judgment: true
    rationale: "The plan's own <verification> block asks a human to read the three not-clean-yes rows and the version-drift section in ADMISSION-CODEBASE-MEMORY-MCP.md and confirm acceptance of admitting this engine on verdicts inherited from a different build than the one installed — an automated proof that the fields are populated and non-empty is not the same as a human judgment call on whether the inheritance is acceptable, which the plan explicitly asks for."
  - id: D3
    description: "Falsifier 4 is run for real on the native-chunking leg and recorded as not-runnable-as-worded (with the structural reason) on the machine-chunks leg; this phase's COVERAGE.md is a real capability matrix over the live tool surface, not a no-integration declaration"
    requirement: MODAL-03
    verification:
      - kind: integration
        ref: "tests/evidence/test_falsifier4_evidence.py::test_the_native_leg_is_reproducible_live_get_code_snippet_still_derives_a_content_hash"
        status: pass
      - kind: unit
        ref: "tests/evidence/test_falsifier4_evidence.py::test_leg_1_table_carries_one_row_per_chunkref_field"
        status: pass
      - kind: unit
        ref: "tests/evidence/test_falsifier4_evidence.py::test_leg_2_machine_chunks_carries_a_disposition_and_the_section_x5_structural_reason"
        status: pass
      - kind: unit
        ref: "tests/evidence/test_falsifier4_evidence.py::test_verdict_section_exists_and_states_what_falsifier_4_calibrates"
        status: pass
    human_judgment: true
    rationale: "The plan's own <verification> block asks a human to read COVERAGE.md's opt-out reasons and confirm none of them is a capability the owner actually wanted — a judgment call on product scope, not a fact an automated test can settle."

duration: 105min
completed: 2026-09-09
status: complete
---

# Phase 5 Plan 6: Opaque-side admission — codebase-memory-mcp, the second engine shape, and Falsifier 4 run for real Summary

**`codebase-memory-mcp@0.1.0` gained a real MCP-over-stdio adapter and a genuine eleven-verdict §8 admission record — the three rows `PARTS.md ## §X` already flagged as not-clean-yeses stay recorded as an open question and machine-side obligations rather than rounded up — and Falsifier 4 ran for real: the native-chunking leg produces a machine-resolvable but permanently tier-capped ref, and the machine-chunks leg is confirmed structurally not-runnable, exactly as `## §X.5` anticipated.**

## Performance

- **Duration:** ~105 min
- **Started:** 2026-09-08 (session)
- **Completed:** 2026-09-09T00:40Z
- **Tasks:** 3 completed
- **Files:** 9 created, 5 modified

## Accomplishments

- `databasise/foreign/codebase_memory_mcp_adapter.py`: the §17 foreign-part adapter for the second, MCP-served engine shape — `list_tools`/`call_tool` over the `mcp` SDK's `stdio_client`/`ClientSession`, `normalise_to_item_kind` mapping every returned item to a §4 `ItemKind` member and capping its evidence tier `below_T1` unconditionally, and named refusals (`ForeignEngineUnavailableError`, `CbmToolTimeoutError`, `CbmTransportError`) carrying both endpoint placements for a cross-process failure. Deliberately structured like `v1_corpus_adapter.py` — the concrete second data point for Falsifier 6's fixed-cost claim.
- `databasise/parts_core/codebase_memory_mcp.py`: `CODEBASE_MEMORY_MCP_ADMISSION`, the eleven-`ConditionVerdict` §8 record projecting `PARTS.md ## §X`'s already-run analysis into executable data, plus a measured wall-clock ceiling (120.0s, grounded in a real 2.88s `index_repository` run) and the version drift between the pinned clone (`61b3b1b2`) `## §X`'s verdicts were code-verified against and the installed binary (`0.10.8`) this admission actually runs.
- `databasise/parts_core/declared_only.py`: `CODEBASE_MEMORY_MCP_PART` gains a real body and admission record — no longer a `body=None` declaration-only stub; `effects` widened additively with `mutates_store`.
- `databasise/wirings/codebase-memory-mcp.json`: a one-node wiring making the admitted engine reachable through the same `parse_wiring -> run_wiring` machinery the LightRAG corpus-side ports use.
- `databasise/evidence/FALSIFIER-4-EVIDENCE.md`: both legs, real. The native-chunking leg's per-`ChunkRef`-field table over real calls against this repository; the machine-chunks leg's disposition and `## §X.5`'s structural finding carried forward verbatim, re-confirmed live rather than merely re-read.
- `.planning/phases/05-opaque-side-admission/COVERAGE.md`: this phase's real capability matrix — fifteen live-enumerated `codebase-memory-mcp` tools, the v1 corpus-side operations plans 05-01/05-03/05-04 consume, a pointer to Phase 3's authoritative model-endpoint record, and the §18.5 operations table extended with this phase's six new operations.

## Task Commits

Each task was committed atomically:

1. **Task 1: The §17 adapter — process lifecycle, RPC, health, and evidence normalization** - `204023a` (feat)
2. **Task 2: The eleven verdicts as executable data, the measured ceiling, and the version drift** - `d6db9c8` (feat)
3. **Task 3: Falsifier 4, run twice — and this phase's COVERAGE.md** - `0b2660f` (test)

## Files Created/Modified

- `databasise/foreign/codebase_memory_mcp_adapter.py` - the §17 adapter (process lifecycle, RPC, health, evidence normalization)
- `databasise/parts_core/codebase_memory_mcp.py` - `CODEBASE_MEMORY_MCP_ADMISSION` + `codebase_memory_mcp_body`
- `databasise/parts_core/declared_only.py` - `CODEBASE_MEMORY_MCP_PART` gets a real body + admission + additive `mutates_store`
- `databasise/wirings/codebase-memory-mcp.json` - the one-node wiring
- `databasise/pyproject.toml` - `databasise.wirings` package-data widened to include root-level `*.json`
- `databasise/evidence/ADMISSION-CODEBASE-MEMORY-MCP.md` - the code-inspected admission manifest
- `databasise/evidence/FALSIFIER-4-EVIDENCE.md` - both Falsifier-4 legs, real
- `databasise/evidence/FALSIFIER-2-EVIDENCE.md` - regenerated via `python -m databasise.evidence.falsifier2` (never hand-edited) to reflect the additive effects change
- `.planning/phases/05-opaque-side-admission/COVERAGE.md` - this phase's capability matrix
- `databasise/tests/parts_core/test_codebase_memory_mcp_admission.py`, `tests/evidence/test_falsifier4_evidence.py`, `tests/fixtures/codebase_memory_mcp_raw_items.json` - new test coverage
- `databasise/tests/parts/test_admission.py`, `tests/parts/test_registry.py` - updated for this plan's own required behavior changes

## Decisions Made

See `key-decisions` in frontmatter — five decisions: the lazy, function-scoped `mcp` import (so the optional extra never gates `default_registry()` itself); the unconditional `below_T1` tier cap (a structural finding, not a per-call gap); the real-zero (`counted_by='none'`) token report instead of `'unbudgetable'`; the additive `mutates_store` effect with the discrepancy recorded rather than resolved; and the measured, margined wall-clock ceiling.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `mcp` imported at module level would have broken nearly the entire test suite on a bare install**
- **Found during:** Task 1, full-suite verification pass (`uv run pytest -q` with no extras installed)
- **Issue:** `databasise/foreign/codebase_memory_mcp_adapter.py`'s first draft imported `mcp`/`anyio` at module level. Because this module is reached from `default_registry()` (via `parts_core.codebase_memory_mcp` → `parts_core.declared_only`), a module-level import made the whole registry — and therefore nearly every test in the suite — fail with `ModuleNotFoundError` the moment `mcp` was not installed, breaking the plan's own required `cd databasise && uv run pytest -q` (no extras) verification bullet.
- **Fix:** Moved the `mcp`/`anyio` imports to be function-scoped inside `_run_with_session`, called only when an actual `list_tools()`/`call_tool()` call is made; the binary is resolved *before* that import so `ForeignEngineUnavailableError` still fires cleanly without the extra installed. Updated both new test files' skip guards to check `importlib.util.find_spec("mcp")` in addition to the binary's presence, so a live-engine test skips cleanly rather than failing with a bare `ModuleNotFoundError` when the binary is present but the extra is not.
- **Files modified:** `databasise/foreign/codebase_memory_mcp_adapter.py`, `databasise/tests/parts_core/test_codebase_memory_mcp_admission.py`, `databasise/tests/evidence/test_falsifier4_evidence.py`
- **Verification:** `uv run pytest -q` (no extras) — 656 passed, 11 skipped, exit 0; `uv run --extra mcp --extra rest pytest -q` — 706 passed, 1 skipped, exit 0.
- **Committed in:** `204023a` (Task 1 commit) and `d6db9c8` (Task 2 commit, for the admission-half tests added to the same file)

**2. [Rule 1 - Bug] A global process-count assertion was flaky against unrelated `codebase-memory-mcp` instances on the developer machine**
- **Found during:** Task 1
- **Issue:** The first draft of the child-process-termination test counted *all* running `codebase-memory-mcp` processes system-wide before/after a call — this developer machine legitimately runs other, unrelated instances (other sessions/tools), so the count drifted between the two measurements for reasons having nothing to do with this adapter leaking a process.
- **Fix:** Counts only *direct children of the test process itself* (`pgrep -P <os.getpid()>`), which is reliably zero both before and after any call this adapter makes, regardless of what else is running on the machine.
- **Files modified:** `databasise/tests/parts_core/test_codebase_memory_mcp_admission.py`
- **Verification:** `test_the_adapter_terminates_the_child_process_on_both_the_success_and_the_failure_path` passes reliably across repeated runs.
- **Committed in:** `204023a` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (1 Rule 3 blocking issue necessary for the plan's own bare-install verification bullet to pass at all; 1 Rule 1 bug fix for a flaky assertion).
**Impact on plan:** No scope creep. Both fixes were necessary corrections directly caused by, or required to prove, this plan's own required behavior; neither changes what the plan set out to build.

## Issues Encountered

None beyond the deviations documented above.

## Threat Flags

| Flag | File | Description |
|------|------|--------------|
| threat_flag: unvalidated-tool-arguments | `databasise/parts_core/codebase_memory_mcp.py` | `codebase_memory_mcp_body` passes `ctx.config['arguments']` straight through to the foreign engine's `call_tool` with no validation of tool name or argument shape — e.g. a caller-controlled `repo_path` for `index_repository` would let the machine ask the foreign engine to index an arbitrary filesystem path. Not reachable by any consumer-facing operation this phase adds (no seam/REST/MCP method calls this body with external input) — 05-07's MCP transport is the first plan that could make this reachable, and should validate the tool/arguments pair against an intention-level surface before threading raw config through, per §18.5's tool-growth rule and the general deny-by-default posture this project applies elsewhere. |

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `codebase-memory-mcp@0.1.0` and `lightrag/full-ingest@0.1.0`/`lightrag/full-delete@0.1.0` are now all real, admitted, executable opaque parts — three separate admission records exercising `databasise/parts/admission.py`'s machinery against two genuinely different foreign-engine shapes (subprocess-JSON, MCP-over-stdio), which is the concrete evidence Falsifier 6 asked for.
- `MODAL-03` is now complete (this plan's own sole declared requirement; `gsd_run query requirements.ready-ids` reports 1/1 ready).
- Two `<human-check>` items from the plan's own `<verification>` block are deferred to end-of-phase UAT per `workflow.human_verify_mode: end-of-phase`: (1) read the three not-clean-yes rows and the version-drift section in `ADMISSION-CODEBASE-MEMORY-MCP.md` and confirm acceptance of admitting this engine on verdicts inherited from a different build than the one installed; (2) read `COVERAGE.md`'s opt-out reasons and confirm none is a capability the owner actually wanted.
- The Threat Flag above (unvalidated tool arguments reaching the foreign engine) is not a blocker for this plan — nothing consumer-facing calls `codebase_memory_mcp_body` yet — but is a real note for whoever builds 05-07's MCP transport or any future seam method that dispatches this part.
- No blockers for 05-05 or 05-07.

## Self-Check: PASSED

- FOUND: `databasise/foreign/codebase_memory_mcp_adapter.py`
- FOUND: `databasise/parts_core/codebase_memory_mcp.py`
- FOUND: `databasise/wirings/codebase-memory-mcp.json`
- FOUND: `databasise/evidence/ADMISSION-CODEBASE-MEMORY-MCP.md`
- FOUND: `databasise/evidence/FALSIFIER-4-EVIDENCE.md`
- FOUND: `.planning/phases/05-opaque-side-admission/COVERAGE.md`
- FOUND: `databasise/tests/parts_core/test_codebase_memory_mcp_admission.py`
- FOUND: `databasise/tests/evidence/test_falsifier4_evidence.py`
- FOUND: `databasise/tests/fixtures/codebase_memory_mcp_raw_items.json`
- FOUND commit: `204023a`
- FOUND commit: `d6db9c8`
- FOUND commit: `0b2660f`
- Re-ran all `<acceptance_criteria>` from every task: all pass (live `list_tools()` sorted-name print; `grep -c` for admission-data leakage into the adapter returns 0; every committed fixture normalizes; child-process termination on both timeout and success paths; both-endpoint-placement assertion on a transport failure; the `default_registry()` admission-record acceptance script prints `ok`; `61b3b1b2`/installed-version/drift-heading presence in the manifest; `N12`/no-OS-isolation presence; measured-vs-declared ceiling comparison; `test_falsifier2_evidence.py` full pass; both `FALSIFIER-4-EVIDENCE.md` legs present with a per-`ChunkRef`-field table and a disposition value; `COVERAGE.md`'s row count equals the live tool count (15) with every `OPT-OUT` reason non-empty; the Phase-3 `COVERAGE.md` pointer present with no row restated; the §18.5 table lists every 05-01/05-03/05-04 operation).
- Re-ran the plan-level `<verification>`: `cd databasise && uv run pytest -q` — 656 passed, 11 skipped, exit 0. `cd databasise && uv run --extra mcp --extra rest pytest -q` — 706 passed, 1 skipped, exit 0. `cd databasise && uv run python -m databasise.tools.check_import_boundary` — exit 0.

---
*Phase: 05-opaque-side-admission*
*Completed: 2026-09-09*
