---
phase: 06-hipporag-2-side-by-side
plan: 07
subsystem: rag-engine
tags: [hipporag, guard, data-guard, dpr-fallback, wiring, evidence, tdd]

# Dependency graph
requires:
  - phase: 06-hipporag-2-side-by-side
    plan: "06-01"
    provides: "the five query-side parts (fact-score, fact-filter, reset-vector-join, ppr, assemble-result), fact-filter's own guard_fired output with no consumer yet, reset-vector-join's KV-read expectation for fact:<id> chunk associations"
  - phase: 06-hipporag-2-side-by-side
    plan: "06-02"
    provides: "entity-fact-embed's fact vector metadata (chunk_ids, entities) — the other side of the fact-chunk-association gap this plan closes"
  - phase: 06-hipporag-2-side-by-side
    plan: "06-05"
    provides: "the completed index side (12 of 13 positions), the disposition naming this plan as owner of the entity-fact-embed KV-write gap"
provides:
  - "hipporag/dpr-fallback@0.1.0 — the thirteenth and final HippoRAG base-wiring position, sharing one dense_passage_retrieval() implementation with reset-vector-join's own passage-weight construction"
  - "The zero_surviving_facts_dpr_fallback §19.8 data guard, declared on fact-filter's own config.guards, observable per query via the run record's guards_fired field reached through resolve_trace — no new envelope field minted"
  - "assemble-result routes between ppr's items (guard not fired) and dpr-fallback's items (guard fired), reading the outcome from ctx.inputs[\"fact-filter\"] — never the run record"
  - "entity-fact-embed's additive fact:<id> -> {chunk_ids} KV write, closing the fact-chunk-association gap 06-05-SUMMARY.md disposed to this plan"
  - "databasise/evidence/HIPPORAG-PORT-RECORD.md — the committed declared-effects reconciliation for all four divergent HippoRAG nodes, plus the guard-placement, guard-observability and nearest-signature-typing rows, plus the stated parity-measurement deferral"
  - "databasise/tests/parts_core/hipporag/test_thirteen_positions.py — MODAL-04's decomposition claim pinned against PARTS.md ## §H at test time"
affects: [06-09]

# Actuals (#2632)
actuals:
  tokens: 18474
  tasks: 3
  commits: 4
commits: 4
plan_head_before: 866eed9f9d7f94db60b5779bb33c32397a3ffde4

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Shared dense-passage-retrieval helper (dpr_fallback.py's dense_passage_retrieval()) imported by a second node (reset_vector_join.py) rather than re-implemented — the same helper upstream calls in both places, per PARTS.md ## §H's own citation"
    - "_GuardAwareResult: a dict subclass overriding __eq__/__ne__ so evaluate_guards's whole-runtime-output `!=` comparison (runner/guards.py) can read a single boolean field of a data-bearing node's own rich output against a JSON-literal value_when_not_fired sentinel, without a second guard-evaluation mechanism — the first real production use of a per-node live guard in this codebase (the LightRAG local/global guard remains illustrative-only, never wired into config.guards)"
    - "Control-channel-is-a-read (§11): a node needing another node's own emitted control signal (here, fact-filter's guard_fired) becomes an explicit additional dep so the signal reaches it through ctx.inputs, never through a mid-run read of the run record"

key-files:
  created:
    - databasise/parts_core/hipporag/dpr_fallback.py
    - databasise/tests/parts_core/hipporag/test_dpr_fallback_guard.py
    - databasise/tests/parts_core/hipporag/test_thirteen_positions.py
    - databasise/evidence/HIPPORAG-PORT-RECORD.md
    - databasise/tests/evidence/test_hipporag_port_record.py
  modified:
    - databasise/parts_core/hipporag/reset_vector_join.py
    - databasise/parts_core/hipporag/fact_filter.py
    - databasise/parts_core/hipporag/assemble_result.py
    - databasise/parts_core/hipporag/entity_fact_embed.py
    - databasise/parts_core/hipporag/__init__.py
    - databasise/wirings/hipporag/base.json
    - databasise/tests/parts_core/hipporag/test_registration.py
    - databasise/tests/parts_core/hipporag/test_index_side_extraction.py
    - databasise/tests/parts_core/hipporag/test_graph_construction.py
    - databasise/tests/parts/test_registry.py

key-decisions:
  - "The guard is declared on fact-filter's own wiring config.guards (the shape declare_guard() actually consumes: name/evaluating_node/value_when_not_fired/granularity), never a top-level 'guards' array — runner/guards.py's own module docstring requires config.guards so config_hash covers the declaration; the illustrative docs/system-model/wirings/hipporag-base.json's top-level, richer-shaped guards array is evidence PARTS.md cites, never parsed by validator/parse.py or reached by runner/scheduler.py's per-node guard validation."
  - "assemble-result's deps are [ppr, dpr-fallback, fact-filter] — a documented divergence from the illustrative wiring's [ppr, dpr-fallback] — so the guard's own outcome reaches it through ctx.inputs (the sanctioned control channel) rather than a mid-run run-record read, which §11 forbids. evidence_position moved from ppr to assemble-result in the same commit so the envelope's evidence reflects whichever branch was actually selected, not always ppr's raw output."
  - "entity-fact-embed additionally writes a fact:<id> -> {chunk_ids} KV record (writes_kv effect added) — the disposition 06-05-SUMMARY.md's own 'Next Phase Readiness' section named to this plan explicitly, closing the gap between reset-vector-join's already-committed KV read and entity-fact-embed's vector-metadata-only write."
  - "_GuardAwareResult (a dict subclass with overridden __eq__/__ne__) resolves the mismatch between evaluate_guards's whole-runtime-output comparison and fact-filter's own rich, per-query-variable output — dict's own C-level __ne__ slot does not fall back to a subclass __eq__ override the way plain Python classes do, so both had to be defined explicitly."

patterns-established:
  - "The dense-passage-retrieval shared helper: two nodes computing the same upstream formula import one function rather than each computing its own, so a future edit cannot silently diverge them."

requirements-completed: [MODAL-04]

coverage:
  - id: D1
    description: "dpr-fallback (the thirteenth position) emits sorted text_chunk items over the full passage matrix via score_all, sharing dense_passage_retrieval() with reset-vector-join, unconditionally dispatched, empty-namespace-safe"
    requirement: MODAL-04
    verification:
      - kind: unit
        ref: "tests/parts_core/hipporag/test_dpr_fallback_guard.py#test_dpr_fallback_emits_text_chunk_items_for_every_stored_chunk_sorted_by_descending_score"
        status: pass
      - kind: unit
        ref: "tests/parts_core/hipporag/test_dpr_fallback_guard.py#test_dpr_fallback_scores_match_reset_vector_joins_own_passage_weight_scores"
        status: pass
      - kind: unit
        ref: "tests/parts_core/hipporag/test_dpr_fallback_guard.py#test_dpr_fallback_runs_unconditionally_reading_no_guard_state"
        status: pass
      - kind: unit
        ref: "tests/parts_core/hipporag/test_dpr_fallback_guard.py#test_dpr_fallback_with_empty_chunk_namespace_emits_empty_items_never_raises"
        status: pass
    human_judgment: false
  - id: D2
    description: "The zero_surviving_facts_dpr_fallback guard fires exactly when zero facts survive fact-filter, routes assemble-result to dpr-fallback's items instead of ppr's, and its firing is observable via resolve_trace's guards_fired without appearing in the serialised envelope or marking the run degraded/partial"
    requirement: MODAL-04
    verification:
      - kind: integration
        ref: "tests/parts_core/hipporag/test_dpr_fallback_guard.py#test_facts_survive_assemble_result_uses_ppr_and_guard_does_not_fire"
        status: pass
      - kind: integration
        ref: "tests/parts_core/hipporag/test_dpr_fallback_guard.py#test_zero_facts_survive_assemble_result_uses_dpr_fallback_and_guard_fires"
        status: pass
      - kind: integration
        ref: "tests/parts_core/hipporag/test_dpr_fallback_guard.py#test_guard_fired_run_reports_degraded_false_and_partial_false_on_the_envelope"
        status: pass
      - kind: integration
        ref: "tests/parts_core/hipporag/test_dpr_fallback_guard.py#test_guard_name_appears_nowhere_in_the_serialised_envelope"
        status: pass
      - kind: unit
        ref: "tests/parts_core/hipporag/test_dpr_fallback_guard.py#test_fact_filter_node_declares_the_guard_at_config_guards_with_per_query_granularity"
        status: pass
      - kind: unit
        ref: "tests/parts_core/hipporag/test_dpr_fallback_guard.py#test_guard_declaration_missing_granularity_raises_guarddeclarationerror"
        status: pass
    human_judgment: false
  - id: D3
    description: "HIPPORAG_PARTS holds exactly thirteen members matching PARTS.md ## §H's node table, none opaque-kinded, none carrying an admission record, all opaque-effective-depth, all in-process"
    requirement: MODAL-04
    verification:
      - kind: unit
        ref: "tests/parts_core/hipporag/test_thirteen_positions.py#test_the_built_wirings_resolved_node_id_set_equals_the_governing_thirteen"
        status: pass
      - kind: unit
        ref: "tests/parts_core/hipporag/test_thirteen_positions.py#test_no_hipporag_part_is_opaque_kinded_and_none_carries_an_admission_record"
        status: pass
      - kind: unit
        ref: "tests/parts_core/hipporag/test_thirteen_positions.py#test_effective_depth_is_opaque_at_all_thirteen_positions"
        status: pass
    human_judgment: false
  - id: D4
    description: "Every declared-effect divergence from PARTS.md ## §H is enumerated in one committed evidence record with a per-row reason, and a test asserts the record's own reconciliation table exactly covers the divergent-node set computed at test time"
    requirement: MODAL-04
    verification:
      - kind: unit
        ref: "tests/parts_core/hipporag/test_thirteen_positions.py#test_declared_effects_union_equals_the_governing_union_plus_exactly_the_additive_set"
        status: pass
      - kind: unit
        ref: "tests/evidence/test_hipporag_port_record.py#test_reconciliation_table_covers_exactly_the_computed_divergent_node_set"
        status: pass
    human_judgment: false

# Metrics
duration: ~90 min
completed: 2026-09-10
status: complete
---

# Phase 6 Plan 7: HippoRAG 2 Thirteenth Position and the §19.8 Guard Summary

**The thirteenth HippoRAG 2 position (dpr-fallback) lands sharing one dense-passage-retrieval implementation with reset-vector-join, the zero_surviving_facts_dpr_fallback data guard is declared on fact-filter's own config.guards and routes assemble-result between the two arms with its firing observable only through the trace, and every one of this port's declared-effect divergences from PARTS.md ## §H — including a new fact-chunk-association KV write on entity-fact-embed — is enumerated in one committed record.**

## Performance

- **Duration:** ~90 min
- **Started:** 2026-09-10
- **Completed:** 2026-09-10
- **Tasks:** 3
- **Files modified/created:** 15

## Accomplishments

- `databasise/parts_core/hipporag/dpr_fallback.py`: `hipporag/dpr-fallback@0.1.0` — the thirteenth and final base-wiring position, `effects=["calls_embedding", "reads_vector"]` exactly matching `## §H`'s declared set with no additive discrepancy. Its `dense_passage_retrieval()` helper is imported by `reset_vector_join.py`, which no longer computes its own embed+`score_all` call — the two positions cannot silently diverge on what dense passage retrieval means.
- The `zero_surviving_facts_dpr_fallback` `§19.8` guard is declared on `fact-filter`'s own `config.guards` (the shape `runner/guards.py`'s `declare_guard` actually consumes), evaluated at `fact-filter`, `granularity="per-query"`. `fact_filter.py`'s `_GuardAwareResult` (a `dict` subclass overriding `__eq__`/`__ne__`) makes `evaluate_guards`'s whole-runtime-output comparison correctly read this node's own `guard_fired` key against a JSON-literal `value_when_not_fired: false` — no second guard-evaluation mechanism, no change to `runner/guards.py` or `runner/scheduler.py`.
- `assemble-result` now has `deps=["ppr", "dpr-fallback", "fact-filter"]` and selects `ppr`'s items when the guard did not fire, `dpr-fallback`'s when it did — reading the outcome from `ctx.inputs["fact-filter"]`, never the run record (`§11`'s control-channel-is-a-read rule). `evidence_position` moved from `ppr` to `assemble-result` so the envelope's own evidence reflects whichever branch was actually selected.
- A guard-fired run reports `degraded=False`/`partial=False` (a declared, correctly-firing guard is not an unhealthy run) and the guard's own firing is reachable only through `resolve_trace(..., debug=True)`'s `guards_fired` — never present in the serialised `ResponseEnvelope`.
- **Closed the two-plan-old fact-chunk-association gap** 06-05-SUMMARY.md disposed to this plan: `entity-fact-embed` now additionally writes a `fact:<id>` -> `{chunk_ids}` KV record (`writes_kv` effect added), so `reset-vector-join`'s already-committed `reads_kv` read has real data from a real `chunk-embed` → ... → `entity-fact-embed` run, not only the test fixture's hand-seeded stand-in.
- `databasise/evidence/HIPPORAG-PORT-RECORD.md`: the declared-effects reconciliation table (four divergent nodes, each with `## §H`'s value, the built value, and its mechanical cause), the guard-placement divergence, the guard-observability resolution, the `assemble-result` deps divergence, and the nearest-signature-typing row — plus a Limits section naming the deliberately-unrun upstream-package parity measurement.
- `databasise/tests/parts_core/hipporag/test_thirteen_positions.py` and `databasise/tests/evidence/test_hipporag_port_record.py` pin MODAL-04's decomposition claim and the evidence record itself against the registry at test time — a future part gaining an undeclared effect fails as an unrecorded divergence rather than passing by omission.
- HippoRAG base wiring grown from 12 to 13 of the governing 13 positions — **the port is complete**.
- Full suite: 886 passed, 1 skipped (both bare and `--extra rest --extra mcp`) — up from the 855/1 baseline by exactly this plan's own 31 new tests, zero regressions.

## Task Commits

Each task followed RED → GREEN (TDD, Tasks 1-2 share one RED commit since `-k dpr` selects the whole shared test file by its own filename):

1. **RED (Tasks 1+2)**: `174efa9` (test) — verified against a temporarily stubbed `dpr-fallback` body: real assertion failures (item counts, score mismatches), not collection errors.
2. **Task 1 GREEN: dpr-fallback**: `e25cf02` (feat) — includes the authorized `entity-fact-embed` KV-write deviation and pinned-count fixes.
3. **Task 2 GREEN: the §19.8 guard**: `e5d785f` (feat).
4. **Task 3 (no TDD): thirteen positions pinned + port record**: `ccd0b6e` (docs).

_No REFACTOR commits — each GREEN implementation was clean once passing._

## TDD Gate Compliance

Tasks 1-2 (`type="auto" tdd="true"`) share one test file due to a genuine file-naming interaction:
Task 1's own `<verify>` command is `pytest -q tests/parts_core/hipporag/test_dpr_fallback_guard.py
-k dpr` — since the **file name itself** contains `dpr`, `-k dpr` selects every test in the file
(pytest matches the full node id, which includes the file path), not only functions whose own name
contains `dpr`. Both tasks' tests were therefore authored and RED-verified together in one commit,
then GREEN-verified in two separate task-scoped commits as their respective production code landed.

- **RED (`174efa9`):** `dpr_fallback.py`'s body was temporarily stubbed to `return {"items": []}` (ignoring config, making zero client calls) before this commit. Verified via `uv run pytest -q tests/parts_core/hipporag/test_dpr_fallback_guard.py -k dpr`: **6 of 12 tests failed on real assertions** (`assert 0 == 3`, a raw dict-mismatch on scores, `KeyError: 'nodes'`/`'guards'` from the not-yet-built guard machinery) — genuine RED evidence, not a collection error. The stub was then reverted before this commit landed (the test file itself is what's committed as RED evidence; the stub never reached git).
- **Task 1 GREEN (`e25cf02`):** real `dpr-fallback` implementation, `reset-vector-join`'s shared-helper import, the wiring node, and the KV-write deviation restored/added; all dpr-tagged tests plus the full existing hipporag/registry/index-side/graph-construction test suites pass (only the 3 not-yet-implemented Task 2 tests still failed at this point, confirmed expected).
- **Task 2 GREEN (`e5d785f`):** the guard declaration, `_GuardAwareResult`, and `assemble_result.py`'s routing landed. One real bug surfaced and was fixed during this GREEN pass (see Deviations): the first `_GuardAwareResult.__eq__` implementation had an inverted boolean, and separately `dict`'s own C-level `__ne__` slot does not consult a subclass's `__eq__` override — both required an explicit fix before the guard correctly distinguished fired/not-fired. All 12 tests in the file pass.
- **Tool note:** `gsd_run check tdd-red-evidence` remains TAP/Node-test-runner-oriented and does not natively parse pytest's default output format for this Python project (same finding recorded in every prior Phase 6 plan's own SUMMARY.md); RED evidence was verified manually via pytest's own exit code and per-test failure attribution instead of running that tool mechanically.

## Files Created/Modified

- `databasise/parts_core/hipporag/dpr_fallback.py` - `hipporag/dpr-fallback@0.1.0`, `dense_passage_retrieval()` shared helper
- `databasise/parts_core/hipporag/reset_vector_join.py` - imports the shared helper instead of computing its own
- `databasise/parts_core/hipporag/fact_filter.py` - `_GuardAwareResult`
- `databasise/parts_core/hipporag/assemble_result.py` - guard-based ppr/dpr-fallback selection
- `databasise/parts_core/hipporag/entity_fact_embed.py` - additive `fact:<id>` KV write, `writes_kv` effect
- `databasise/parts_core/hipporag/__init__.py` - `HIPPORAG_PARTS` grown from 12 to 13 members
- `databasise/wirings/hipporag/base.json` - `dpr-fallback` node, `fact-filter`'s `config.guards`, `assemble-result`'s deps/`evidence_position`, `consumes_query`
- `databasise/tests/parts_core/hipporag/test_dpr_fallback_guard.py` - all Task 1/2 behavior tests
- `databasise/tests/parts_core/hipporag/test_thirteen_positions.py` - Task 3's conformance pins
- `databasise/evidence/HIPPORAG-PORT-RECORD.md` - the declared-effects reconciliation and limits
- `databasise/tests/evidence/test_hipporag_port_record.py` - structural assertions over the record
- `databasise/tests/parts_core/hipporag/test_registration.py`, `test_index_side_extraction.py`, `test_graph_construction.py`, `databasise/tests/parts/test_registry.py` - pinned counts and `kv`-store fixture updates

## Decisions Made

See `key-decisions` in frontmatter. Most load-bearing: `_GuardAwareResult`'s `dict`-subclass `__eq__`/`__ne__` override is the mechanism that lets a static JSON `value_when_not_fired` sentinel (`false`) correctly express a per-query, data-dependent condition through `evaluate_guards`'s existing whole-output `!=` comparison — the first time this codebase's `runner/guards.py` machinery has been wired against a real, rich-payload production node rather than a scalar/no-op stub.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] `entity-fact-embed` additionally writes a `fact:<id>` -> `{chunk_ids}` KV record**
- **Found during:** Task 1 (authorized in advance by the orchestrator's own `<prior_wave_context>`, per 06-05-SUMMARY.md's explicit disposition naming this plan as owner)
- **Issue:** `reset-vector-join.py` (06-01, already committed) reads each surviving fact's own chunk association from a KV `fact:<id>` record; before this plan, no code wrote that record for a real end-to-end run — only the test fixture hand-seeded it.
- **Fix:** `entity_fact_embed.py`'s body now also writes `{f"fact:{fid}": {"chunk_ids": ...}}` to `ctx.stores["kv"]`; `writes_kv` added to its declared effects.
- **Files modified:** `databasise/parts_core/hipporag/entity_fact_embed.py`, plus four existing test call sites in `test_index_side_extraction.py`/`test_graph_construction.py` that previously constructed this node's `NodeContext` with no `kv` store (a direct, expected consequence — `CapabilityScopedStores.require` now hands this node's body a `kv` store handle it did not have before).
- **Verification:** Full suite green; `test_entity_fact_embed_*` tests all pass with the added `kv` store.
- **Committed in:** `e25cf02`

**2. [Rule 1 - Bug] `_GuardAwareResult.__eq__`'s boolean logic and `dict`'s `__ne__` slot**
- **Found during:** Task 2's own GREEN verify step
- **Issue:** The first `__eq__` implementation compared `bool(self.get("guard_fired")) is (not other)` — an inverted condition that made the guard fire even when facts survived. Separately, `dict`'s own C-level `__ne__` slot does not fall back to a subclass's `__eq__` override the way plain Python classes do (confirmed with a standalone repro: `d != False` returned `True` even when `d == False` was `True`), so `evaluate_guards`'s `!=` comparison silently bypassed `__eq__` entirely until `__ne__` was also defined.
- **Fix:** Corrected the boolean to `bool(self.get("guard_fired")) == other`, and added an explicit `__ne__` delegating to `__eq__`.
- **Files modified:** `databasise/parts_core/hipporag/fact_filter.py`
- **Verification:** `test_facts_survive_assemble_result_uses_ppr_and_guard_does_not_fire` and `test_zero_facts_survive_assemble_result_uses_dpr_fallback_and_guard_fires` both pass, confirming both directions.
- **Committed in:** `e5d785f`

**3. [Rule 3 - Blocking] `resolve_trace` requires `debug=True` for the node-by-node trace**
- **Found during:** Task 2's own test-writing
- **Issue:** `Databasise.resolve_trace` filters to `_NON_DEBUG_TRACE_FIELDS` (excluding `nodes`) unless `debug=True` is passed — the test's first draft called it without `debug=True` and hit `KeyError: 'nodes'`.
- **Fix:** Passed `debug=True` in both guard-branch tests.
- **Files modified:** `databasise/tests/parts_core/hipporag/test_dpr_fallback_guard.py`
- **Verification:** Both tests pass.
- **Committed in:** `e5d785f`

**4. [Rule 3 - Blocking] Pinned-count and pinned-shape test updates**
- **Found during:** Each task's own full-suite verify step
- **Issue:** `test_registration.py`'s `_EXPECTED_SHAPE` (12→13 members, `entity-fact-embedder`'s effects) and `test_registry.py`'s `test_default_registry_holds_exactly_thirty_four_entries` (34→35) — direct, expected consequences of this plan's own additions, per every prior Phase 6 plan's own recorded precedent for this exact class of fix.
- **Files modified:** `databasise/tests/parts_core/hipporag/test_registration.py`, `databasise/tests/parts/test_registry.py`
- **Verification:** Full suite green (886 passed, 1 skipped).
- **Committed in:** `e25cf02`

---

**Total deviations:** 4 auto-fixed (1 missing critical, 1 bug, 2 blocking)
**Impact on plan:** All four necessary for correctness/consistency; no scope creep. The KV-write deviation was explicitly pre-authorized by the orchestrator's own prior-wave context, closing a gap two plans old rather than deferring it a third time.

## Issues Encountered

None beyond the deviations above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- HippoRAG 2's decomposition is complete: all thirteen `## §H` positions are registered, executable, opaque-effective-depth, none opaque-kinded, no arms, no patch file — MODAL-04's decomposition half is satisfied and checkable.
- MODAL-04's own text conditions the index side's `opaque` status on an upstream-package parity measurement that is deliberately not run in this phase (see `HIPPORAG-PORT-RECORD.md`'s Limits section) — plan 06-09 carries the deferral forward with its own trigger; the effective depth stays `opaque` under the taint rule until that measurement lands.
- The fact-chunk-association gap flagged open across 06-02/06-05's own "Next Phase Readiness" sections is now closed — a real end-to-end run from `chunk-embed` through `reset-vector-join` no longer depends on the conftest fixture's hand-seeded `fact:<id>` KV stand-in.
- `synonymy-edges`' own guard-proxy decision (06-05, unrelated to this plan's `zero_surviving_facts_dpr_fallback` guard) is unchanged and restated in `HIPPORAG-PORT-RECORD.md`'s Limits section only to prevent a reader from conflating the two guard-shaped mechanisms on this same wiring.
- 06-08/06-09 (side-by-side comparison, MACH-10) can now compare HippoRAG 2 against LightRAG with HippoRAG's own retrieval chain fully decomposed and its guard behavior observable through the same trace machinery LightRAG's own `local`/`global` fall-through would use if it were ever wired live (it currently is not — illustrative-only, per this plan's own port-record finding).

## Self-Check: PASSED

- All `key-files.created` verified present on disk.
- `git log --oneline --all | grep -E "174efa9|e25cf02|e5d785f|ccd0b6e"` returns all four commits.
- Every task's `<acceptance_criteria>` re-verified: `HIPPORAG_DPR_FALLBACK_PART.effects == ["calls_embedding", "reads_vector"]`; `reset_vector_join.py` imports `dense_passage_retrieval` from `dpr_fallback.py` (identity-checked in `test_dpr_fallback_scores_match_reset_vector_joins_own_passage_weight_scores`); `dpr-fallback` node's `deps == ["fact-filter"]`; `fact-filter`'s `config.guards[0]` names `zero_surviving_facts_dpr_fallback` with `granularity == "per-query"`; no second arm/patch file; guard-fired run reports `degraded=False`/`partial=False`; guard name absent from `envelope.model_dump_json()`; `assemble_result.py`'s body source contains no `resolve_trace`/`trace_store`/`RunRecord`; `HIPPORAG_PARTS` has exactly 13 members, all non-`None` body; no `hipporag/` part `kind == "opaque"` or carries `admission`; built wiring's node id set equals the governing 13; `effective_depth` opaque at all 13; the port record's reconciliation table covers exactly the 4 nodes whose built effects differ from `## §H`, computed at test time.
- Plan-level `<verification>`: `cd databasise && uv run pytest -q` exits 0 (886 passed, 1 skipped, bare and with `--extra rest --extra mcp`); `uv run python -m databasise.tools.check_import_boundary` exits 0; the HippoRAG base wiring declares thirteen nodes matching the governing document, all executable, all opaque-depth, none opaque-kinded.

## Self-Check: PASSED (re-verified)

- File existence: all five `key-files.created` confirmed present on disk via `[ -f ]`.
- Commit existence: all four task commit hashes (`174efa9`, `e25cf02`, `e5d785f`, `ccd0b6e`) confirmed via `git log --oneline --all`.
- Direct assertion re-run: `HIPPORAG_DPR_FALLBACK_PART.effects == ["calls_embedding", "reads_vector"]`; `HIPPORAG_PARTS` has 13 members, all non-`None` body, none `kind == "opaque"`, none carries `admission`.
- `uv run pytest -q tests/parts_core/hipporag/test_dpr_fallback_guard.py tests/parts_core/hipporag/test_thirteen_positions.py tests/evidence/test_hipporag_port_record.py` -> 31 passed.
- `uv run python -m databasise.tools.check_import_boundary` -> exit 0.

---
*Phase: 06-hipporag-2-side-by-side*
*Completed: 2026-09-10*
