---
phase: 13-selectors-wiring-runner
verified: 2026-10-20T20:30:00Z
status: passed
score: 5/5 roadmap success criteria verified (18/18 WIRE requirements satisfied in code)
covered_files:
  - ".planning/phases/13-selectors-wiring-runner/13-01-PLAN.md"
  - ".planning/phases/13-selectors-wiring-runner/13-01-SUMMARY.md"
  - ".planning/phases/13-selectors-wiring-runner/13-02-PLAN.md"
  - ".planning/phases/13-selectors-wiring-runner/13-02-SUMMARY.md"
  - ".planning/phases/13-selectors-wiring-runner/13-03-PLAN.md"
  - ".planning/phases/13-selectors-wiring-runner/13-03-SUMMARY.md"
  - ".planning/phases/13-selectors-wiring-runner/13-04-PLAN.md"
  - ".planning/phases/13-selectors-wiring-runner/13-04-SUMMARY.md"
  - ".planning/phases/13-selectors-wiring-runner/13-05-PLAN.md"
  - ".planning/phases/13-selectors-wiring-runner/13-05-SUMMARY.md"
  - ".planning/phases/13-selectors-wiring-runner/13-06-PLAN.md"
  - ".planning/phases/13-selectors-wiring-runner/13-06-SUMMARY.md"
  - ".planning/phases/13-selectors-wiring-runner/13-07-PLAN.md"
  - ".planning/phases/13-selectors-wiring-runner/13-07-SUMMARY.md"
  - ".planning/phases/13-selectors-wiring-runner/13-08-PLAN.md"
  - ".planning/phases/13-selectors-wiring-runner/13-08-SUMMARY.md"
  - ".planning/phases/13-selectors-wiring-runner/13-09-PLAN.md"
  - ".planning/phases/13-selectors-wiring-runner/13-09-SUMMARY.md"
  - ".planning/phases/13-selectors-wiring-runner/13-10-PLAN.md"
  - ".planning/phases/13-selectors-wiring-runner/13-10-SUMMARY.md"
  - ".planning/phases/13-selectors-wiring-runner/13-11-PLAN.md"
  - ".planning/phases/13-selectors-wiring-runner/13-11-SUMMARY.md"
  - ".planning/phases/13-selectors-wiring-runner/13-12-PLAN.md"
  - ".planning/phases/13-selectors-wiring-runner/13-12-SUMMARY.md"
  - ".planning/phases/13-selectors-wiring-runner/13-13-PLAN.md"
  - ".planning/phases/13-selectors-wiring-runner/13-13-SUMMARY.md"
  - "databasise/evidence/HIPPORAG-PORT-RECORD.md"
  - "databasise/evidence/PARITY-EVIDENCE.md"
  - "databasise/evidence/RIG-TRACE-DEVIATIONS.md"
  - "databasise/evidence/parity_report.py"
  - "databasise/evidence/rig-trace.databasise.schema.json"
  - "databasise/identity/env.py"
  - "databasise/parts/registry.py"
  - "databasise/parts/schema.py"
  - "databasise/parts_core/fixpoint_body.py"
  - "databasise/parts_core/hipporag/assemble_result.py"
  - "databasise/parts_core/hipporag/fact_filter.py"
  - "databasise/parts_core/lightrag/assemble.py"
  - "databasise/parts_core/lightrag/chunk_sel_kg.py"
  - "databasise/parts_core/lightrag/chunk_vector.py"
  - "databasise/parts_core/lightrag/entity_lookup.py"
  - "databasise/parts_core/lightrag/relation_lookup.py"
  - "databasise/parts_core/lightrag/truncator_token_budget.py"
  - "databasise/runner/budget.py"
  - "databasise/runner/guards.py"
  - "databasise/runner/scheduler.py"
  - "databasise/runner/trace.py"
  - "databasise/seam/engine.py"
  - "databasise/seam/envelope.py"
  - "databasise/seam/evidence.py"
  - "databasise/seam/promotion.py"
  - "databasise/seam/query.py"
  - "databasise/seam/redact.py"
  - "databasise/seam/refusals.py"
  - "databasise/seam/rest.py"
  - "databasise/seam/selectors.py"
  - "databasise/validator/blast_radius.py"
  - "databasise/validator/depth.py"
  - "databasise/validator/errors.py"
  - "databasise/validator/execution_mode.py"
  - "databasise/validator/parse.py"
  - "databasise/wirings/hipporag/base.json"
  - "databasise/wirings/lightrag/README.md"
  - "databasise/wirings/lightrag/arm-bypass.json-patch.json"
  - "databasise/wirings/lightrag/arm-global.json-patch.json"
  - "databasise/wirings/lightrag/arm-hybrid.json-patch.json"
  - "databasise/wirings/lightrag/arm-local.json-patch.json"
  - "databasise/wirings/lightrag/arm-naive.json-patch.json"
  - "databasise/wirings/lightrag/base.json"
  - "databasise/wirings/resolve.py"
  - "docs/gui/API-INVENTORY.md"
  - "docs/gui/CODEBASE-MAP.md"
covered_digest: "v3:sha256:1ec1a71e6aaa2d21a53939b9f9b692a4ad7178fda0d0d6de02e234cd88f5579f"
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "B-WR-03: inject a query node whose body returns a TokenAccounting with counted_by 'unbudgetable' and then fails after dispatch (for example its guard signal raises), and run /query"
    expected: "Owner confirms the intended outcome: today the run is persisted and the query is refused 422 UnbudgetableParticipantError with trace_token, instead of a 200 partial envelope with stop_reason node_failed"
    why_human: "Policy choice between Phase 4 D-08 (an unbudgetable count is refused) and CONTRACT §9 partial outcomes; 13-REVIEW-DISPOSITION flags it for human verification. Code path: scheduler.py:688-705 keeps metered tokens on a failed node, engine.py assemble_token_breakdown refuses."
  - test: "depth_label on a budget-halted answering node: run a query whose generate (or qa) node overspends its token allowance with a real client"
    expected: "Owner confirms D-06 is intended for this case: partial=true, stop_reason budget_halt, the completion is served as the answer and depth_label is 'stage', not null"
    why_human: "ROADMAP SC2 says 'depth_label is null on partial runs'; D-06 keys the null on 'no provides node returned a completion', not on partial. scheduler.py:663 stores the output before meter() and a halt returns completed=True, so the two wordings differ exactly here. No test pins this case."
  - test: "WIRE-10 fail-first record: re-record or plant the WIRE-10 check"
    expected: "The ledger start gate no longer reports 'check edited under a grant needs plants/WIRE-10.json' and 'recorded failure is stale' for test_trace_completeness.py"
    why_human: "Ledger bookkeeping that needs the owner's BAK flow. The test file was edited under grant v647 (13-12, a different test function gained a guard signal key) after the v644 check-fail at b0b5a6c. The current test passes; the verifier may not diff protected test files."
---

# Phase 13: Selectors, Wiring & Runner Verification Report

**Phase Goal:** Every query arm is selectable, the runner records every node truthfully, and consumers never see internal node ids or an unstructured 500 from the wiring layer
**Verified:** 2026-10-20T20:30:00Z
**Status:** passed (human items resolved 2026-10-20; see Human Verification Resolution at the end)
**Re-verification:** No, initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Six arms selectable by a production §18.4 selector without a promote; docstring states the mapping; every resolved wiring names only its own nodes; a local-arm query returns non-empty evidence | VERIFIED | Own probe through `resolve_selector(Selector(capability=...), registry=default_registry())`: `[reads_vector]`→naive (7 nodes), `[calls_llm]`→bypass (1), `[reads_vector:entities]`→local (15), `[reads_vector:relationships]`→global (15), both tokens→hybrid (17), `[reads_graph, reads_kv]`→hipporag (14). Tokens come from the new `Part.reads_namespaces` field (`parts/schema.py:149`), matched in `_capability_tokens` (`selectors.py:176`), validated at registration (`registry.py:180`). The `selectors.py` docstring lists every mapping and the one-node margin. Probe: every `all_wirings()` entry parses ok; `provides` and `evidence_position.node` are in `nodes`; bypass `evidence_position` is null; KG arms point at `assemble`; an injected ghost `provides` gives `unknown-provides`. `test_a_local_arm_query_returns_non_empty_evidence_that_resolves` (test_evidence_position.py) passes. |
| 2 | Consumers never see internals: closed node-free reason codes (detail only under debug); preflight refusals, cycles and invalid concurrency/budget reach REST by name; malformed wiring docs yield a report; depth_label null on partial runs and typed | VERIFIED (one wording divergence, see Human Verification 2) | `REASON_CODES` closed set in `runner/trace.py:47-58`; `node_free_reason` (`redact.py:139`) runs at response time on both envelope reasons (`engine.py` envelope build) and on the non-debug trace (`resolve_trace`), mapping anything else to `node_failed`, never raising. `run_wiring` docstring lists every pre-dispatch raise; strict int checks at `scheduler.py:379,397`. test_preflight_refusals.py (cycles on query/ingest/delete/retry, True/2.7/'100'/0.9/False refused, guard 422, digest 503) passes. Probe: `parse_wiring([])`, `{'nodes': None}`, `{'nodes': [1]}` return `invalid-wiring-document` without raising. `ResponseEnvelope.depth_label` annotation is `Optional[Literal['opaque','evidence','stage']]`; `_select_answer` returns `None` unless a provides node returned a completion (D-06). |
| 3 | Complete, truthful run records: one NodeTrace per node with completed/failed/cancelled/not-scheduled; measured wall time on failure; execution_mode stamped; unreported fields null; per-arm wiring identity stable across queries; post-dispatch raises persist a resolvable trace | VERIFIED | Scheduler dispatches one node at a time (`scheduler.py:799-821`) and appends a `not-scheduled` trace for every node that never ran (`:825-846`); post-dispatch exceptions are recorded against the node (`:688-705`). test_trace_completeness.py (11 tests incl. measured wall time, malformed tokens, raising `__ne__`, CancelledError body, real cancellation propagates) and test_node_trace_fields.py (derived-schema validation, null cache_hit/tier, spent/allowance) pass. Probe: wiring ids `lightrag-base` (naive), `lightrag-bypass`, `lightrag-hybrid`, `lightrag-local`, `lightrag-global`, `hipporag-base`. `wiring_bytes = canonicalise(resolved)` is taken before the three injections (`engine.py` `_execute_resolved`); the RunRecord is persisted before the refusable block and `exc.trace_token` is set on any `SeamRefusalError` after it. test_run_record_identity.py (unbudgetable, two answering provides, malformed evidence each carry a resolvable trace_token; shared hash on two local queries) passes. |
| 4 | Guards fire only on the declared value and misdeclared guards are refused before dispatch; LightRAG keyword guards removed with their docs; seam events report failed vs halted; ingest returns seam events | VERIFIED | test_guard_evaluation.py (signal key fires only on its value, plain dict does not fire, misplaced evaluating node / wrong keys / non-mapping refused) passes. `_GuardAwareResult` and `_StandInResult` are gone from source. No wiring JSON has a top-level `guards` key (probe and test_lightrag_guards.py); README records the D-20 deviation. `_mach11_events` tests `status != completed` or a failure cause first ("failed"), then `budget_state == halted`, and names `component="mutates_store"`; test_seam_events.py and protected test_lightrag_ingest_mach11.py pass. |
| 5 | Engine internals fail by name with no dead API: malformed evidence, four advanced members, env-digest failure on /health; one placement source; partly-reachable refusals pinned; unused scheduling/budget APIs wired or deleted | VERIFIED | A retrieval output without an `items` list raises `MalformedEvidenceItemError` (502 MalformedDriverOutput with trace_token). Probe: `PartRegistry().register` of `effects=('reads_space',)` raises `UnknownPartEffectError`; `validator.depth` has no `derive_execution_mode`; no `WiringValidationError` in the validator; `runner.budget` has none of split_allowance/apportion/ApportionmentPolicy/Allowance/BudgetHalted and `BudgetState` is `('within_budget','halted')`. `environment_hash` hashes system/machine/libc, not `platform.platform()`; test_env.py (health degraded on digest failure, recovers, kernel update does not change hash) passes. test_refusal_reachability.py (one-selector compare on a mutates_store wiring refused; unbudgetable on HippoRAG; retry with a HippoRAG selector has no write path) and test_runner_surface.py pass. |

**Score:** 5/5 roadmap truths verified, 0 behavior-unverified.

### Requirements Coverage

All 18 WIRE IDs appear in PLAN frontmatter (01: 06/07; 02: 01/16; 03: 11/10; 04: 10/03/12/18; 05: 04/14; 06: 02; 07: 17/15/13; 08: 05/08; 09: 09; 10: 12/03; 11: 12/13; 12: 12/08/15/18; 13: 13/11). No orphaned WIRE IDs. All 18 ledger rows are `done`, each with a test_ref and a v6xx check-fail record.

| Requirement | Status | Evidence |
|-------------|--------|----------|
| WIRE-01 | SATISFIED | six-arm probe; test_selector_reachability.py (16 tests) |
| WIRE-02 | SATISFIED | ghost probe; test_top_level_refs.py over every full and pruned wiring incl. corpus wirings; test_evidence_position.py |
| WIRE-03 | SATISFIED | closed codes, response-time gate; test_stop_reason_leak.py (substring check, legacy record mapped) |
| WIRE-04 | SATISFIED (D-06 keying, see Human 2) | typed `Depth \| None`; test_depth_label.py |
| WIRE-05 | SATISFIED (exception: codes-only public violations, recorded) | test_preflight_refusals.py |
| WIRE-06 | SATISFIED | malformed-doc probe; test_parse_report.py (RFC 6901, dedup cycles, kind mismatch) |
| WIRE-07 | SATISFIED | single source probe; test_execution_mode_single_source.py |
| WIRE-08 | SATISFIED | test_guard_evaluation.py; protected test_dpr_fallback_guard.py passes without the `__eq__` override |
| WIRE-09 | SATISFIED (exception: dropped, recorded) | test_lightrag_guards.py; README deviation |
| WIRE-10 | SATISFIED (exceptions: pruned wiring D-13, recorded; cancelled case per D-26) | test_trace_completeness.py; ledger fail-first stale (Human 3) |
| WIRE-11 | SATISFIED (exception: null tier, spent/allowance, derived schema, recorded) | test_node_trace_fields.py; `rig-trace.databasise.schema.json`, `RIG-TRACE-DEVIATIONS.md` |
| WIRE-12 | SATISFIED (exception: pre-injection hash, recorded) | wiring-id probe; test_run_record_identity.py; protected test_query_trace_nodes.py passes under grant v645 |
| WIRE-13 | SATISFIED (exception: component is mutates_store, recorded) | test_seam_events.py; protected test_lightrag_ingest_mach11.py passes under grant v646 |
| WIRE-14 | SATISFIED | test_engine_internals.py (13 tests) |
| WIRE-15 | SATISFIED | `env.py` inputs; test_env.py |
| WIRE-16 | SATISFIED | registration probe; test_advanced_query_members.py |
| WIRE-17 | SATISFIED (exception: retry not delete for NoWritePath, recorded) | test_refusal_reachability.py; API-INVENTORY lists refusals per route |
| WIRE-18 | SATISFIED | budget probe; test_runner_surface.py |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 18 WIRE row test files | pytest of the 18 test_ref files | 232 passed in 20.65s | PASS |
| Related protected and seam tests (LRAG-19, LRAG-03, STOR-06, STOR-05, SEAM-04/14/16, HIPP query/write paths, evidence position, REST transport, health) | pytest of 15 files | 278 passed in 84.93s | PASS |
| Selector, ghost, identity, malformed-doc, registration, placement and budget-surface probe | `probe13.py` in the session scratchpad (real `default_registry()` and `all_wirings()`) | outputs quoted above | PASS |
| Full offline gate, both invocation styles | run separately by the orchestrator (not run here) | orchestrator to add | - |

### Probe Execution

Step 7c: SKIPPED. No `probe-*.sh` is declared by any Phase 13 PLAN or SUMMARY.

### Anti-Patterns Found

No TBD/FIXME/XXX/TODO/HACK marker in any Phase 13 source file (46 files changed since c4256a8, tests excluded). The review closed with 0 critical and 0 warning open; 20 info findings remain open as advisory (13-REVIEW-DISPOSITION.md).

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `docs/gui/CODEBASE-MAP.md` | 332 | G-25 row was edited for D-20 but still says fact-filter "compensates with a dict subclass overriding `__eq__`", that `evaluate_guards` "compares a node's whole output" and "never validates `evaluating_node`", and that fact-filter never receives the query text | Info | Stale after WIRE-08 and HIPP-05; GUI phases read this map. Not a WIRE requirement. |
| `.planning/REQUIREMENTS.md` | 375-378 | WIRE-10 test text still describes a "slow sibling" TaskGroup cancellation; D-26 rewrote it to the CancelledError-body case, and no D-26 exception clause is recorded | Info | Sequential dispatch (D-17) removed the TaskGroup case; record the D-26 clause for traceability |
| `databasise/runner/scheduler.py` | 663, 707 | a budget-halted answering node keeps its output, so a partial run can carry a non-null depth_label | Info | See Human Verification 2 |

### Human Verification Required

1. **B-WR-03 unbudgetable refusal on a failed node.** Inject a query node that reports `counted_by: "unbudgetable"` and then fails after dispatch. Today the query is refused 422 `UnbudgetableParticipantError` with a `trace_token`, not served as a partial envelope. The owner confirms this is the intended policy (Phase 4 D-08 against CONTRACT §9 partial outcomes).
2. **depth_label on a budget-halted answer.** With a real client, make generate (or qa) overspend. Expect partial=true, stop_reason `budget_halt`, the answer served and depth_label `stage`. The owner confirms D-06's keying covers this, or asks for null to match ROADMAP SC2's literal wording.
3. **WIRE-10 ledger proof.** Re-record the WIRE-10 fail-first, or add `plants/WIRE-10.json`, so the BAK start gate stops reporting the stale check-fail.

Owner-run items carried in `.planning/TESTING-PLAN.md` under the no-live-runs policy: pre-Phase-13 API-INVENTORY live checks were not re-run live (A-WR-04), and archived parity and evidence hashes were annotated, not re-minted (D-24).

### Gaps Summary

No goal-blocking gap. Every success criterion and every WIRE row is backed by code read here and tests run here. Bookkeeping for the orchestrator:

- `.planning/REQUIREMENTS.md` still shows WIRE-01..07, 09, 10, 14, 16 and 17 as `[ ]` and "Pending" (lines 339-404, 917-933). Only 08, 11, 12, 13, 15 and 18 are Complete. Mark all 18 Complete when the phase closes.
- The BAK completion gate also reports every S3 trace part (`trace/s3-phase08..12-*.json`) stale on a REQUIREMENTS.md hash mismatch, and every row `not-checked at S3`. That affects all phases, not Phase 13 code.

---

_Verified: 2026-10-20T20:30:00Z_
_Verifier: Claude (gsd-verifier)_

## Human Verification Resolution (2026-10-20)

| Item | Owner decision |
|------|----------------|
| B-WR-03: a failed query node that reports `counted_by: "unbudgetable"` | **Keep.** The query refuses with 422 UnbudgetableParticipantError, carrying `trace_token`, under Phase 4 D-08: a count that cannot be measured is refused, never replaced by a number. |
| `depth_label` on a budget-halted answering node | **D-06.** depth_label is null only when no provides node returned a completion. A served completion keeps its real depth, even on a `budget_halt` partial run. ROADMAP SC2's "null on partial runs" means the D-06 case. |
| WIRE-10 fail-first record | Resolved by the orchestrator. The check failed again at b0b5a6c by AssertionError (v679), and plants/WIRE-10.json killed 2/2 (v680). |

Final offline gate at the final HEAD, `tools/check_offline_suite.py`: 2482 passed, 4 deselected, in both styles; exit 0.
