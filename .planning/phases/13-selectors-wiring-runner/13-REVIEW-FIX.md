---
phase: 13-selectors-wiring-runner
fixed_at: 2026-10-20T00:00:00Z
review_path: .planning/phases/13-selectors-wiring-runner/13-REVIEW.md
iteration: 1
findings_in_scope: 8
fixed: 8
skipped: 0
status: all_fixed
---

# Phase 13: Code Review Fix Report (iteration 1)

**Fixed at:** 2026-10-20
**Source review:** .planning/phases/13-selectors-wiring-runner/13-REVIEW.md (deep, two lanes merged: 0 critical, 8 warning, 14 info)
**Iteration:** 1

**Summary:**
- Findings in scope: 8 (A-WR-01..04, B-WR-01..04; Info findings out of scope)
- Fixed: 8
- Skipped: 0
- Blocked on a protected-test grant: 0

**Verification:** edits and commits were made in the main checkout (`workflow.use_worktrees` is `false`). Every finding was checked against the source before fixing. B-WR-01, B-WR-02, B-WR-04 and A-WR-02 were reproduced with a scratch probe against `_execute_resolved` and `parse_wiring` (TypeError / AttributeError / a 200 `partial=True, stop_reason='node_failed'`); A-WR-01, A-WR-03 and B-WR-03 were confirmed by reading the code. Each fix was followed by targeted pytest runs of the neighbouring suites. The regression tests are in the new, unprotected `databasise/tests/seam/test_review13_fixes.py` (18 tests). Baseline before the fixes, same wave command: 1833 passed, 3 deselected. Final wave command, run in the main checkout after all eight commits (`cd databasise && .venv/bin/pytest -q tests/seam tests/runner tests/validator tests/wirings tests/identity tests/parts tests/parts_core tests/evidence tests/parity`): 1851 passed, 3 deselected (the baseline plus the 18 new tests). `tests/mcp` was also run after B-WR-04 (in a 750-test targeted run) and passed. No protected test file was edited, grepped, read or diffed; the protected list was read from the ledger's `test_ref` entries with `jq`. No live (`-m live`) test was run.

## Fixed Issues

### A-WR-01: MutableStoreComparisonExcludedError puts a part `name@version` in a public field and in the message

**Files modified:** `databasise/seam/refusals.py`, `databasise/seam/engine.py`, `databasise/tests/seam/test_mutable_store_exclusion.py`, `databasise/tests/seam/test_review13_fixes.py`, `docs/gui/API-INVENTORY.md`
**Commit:** 84a538b
**Applied fix:** The public `component` is now the capability `"mutates_store"` (the D-15 rule for `SeamEvent.component`, CONTRACT §18.3). The part `name@version` is kept on the private `_component` (never exported by `refusal_body`) and logged once by `compare()` before the raise. The message names the capability and no part. The constructor keeps its `component=` keyword, so callers and the REST refusal factories are unchanged. The docstring still says "unreachable" (SEAM-16). `test_mutable_store_exclusion.py` is not in the ledger's protected list; its three assertions that pinned the old `name@version` value (lines 109-110, 142, 182) now assert `component == "mutates_store"`, that the part name is absent from the message and that `_component` keeps it. API-INVENTORY section 3.1.3 item 3 describes the new field.
**Test:** `test_the_mutable_store_refusal_names_the_capability_not_the_part` (the body carries `mutates_store` and no part name), plus the updated `test_mutable_store_exclusion.py` engine-level tests.

### A-WR-02: The D-09 evidence guard covers only a missing `items` key

**Files modified:** `databasise/seam/engine.py`, `databasise/seam/evidence.py`, `databasise/tests/seam/test_review13_fixes.py`
**Commit:** d421d06
**Applied fix:** The engine guard now refuses a dict output whose `items` is not a list (`reason="carries no 'items' list"`), and `mint_evidence_refs` refuses a non-mapping item by name (`reason="is not a mapping"`). Both raise `MalformedEvidenceItemError` inside the existing try, so they reach the 502 `ForeignEngineRefusalError(MalformedDriverOutput)` with the run's `trace_token`.
**Test:** `test_a_malformed_items_value_is_malformed_driver_output_with_a_trace`, parametrised over `None`, `["chunk-1"]`, `{"id": ...}` and a string, through an injected part.

### A-WR-03: The environment-digest handling only catches `EnvironmentDigestError`

**Files modified:** `databasise/identity/env.py`, `databasise/tests/seam/test_review13_fixes.py`
**Commit:** 7651a34
**Applied fix:** `environment_hash` wraps any collection failure other than `EnvironmentDigestError` in `EnvironmentDigestError` (class name only in the message, `from exc` kept). Both existing catch sites are unchanged: `health()` reads degraded with "environment digest unavailable", and `_run_wiring` raises the D-22 503 `ForeignEngineRefusalError(EnvironmentDigestUnavailable)`. `functools.cache` still memoises success only.
**Test:** `test_an_uncollectable_environment_is_an_environment_digest_error` (an empty dist-info with `version=None` raises the named error and leaves the cache empty) and `test_an_uncollectable_environment_refuses_a_query_as_environment_digest_unavailable`.

### A-WR-04: API-INVENTORY.md still describes the pre-Phase-13 consumer contract

**Files modified:** `docs/gui/API-INVENTORY.md`
**Commit:** 4c8394f (the A-WR-01 and B-WR-03 rows landed with those commits: 84a538b, 8067e25)
**Applied fix:** Rewrote every cited row to Phase 13 behaviour: the envelope intro and `stop_reason` / `degradation_reason` rows (closed codes, the `node_free_reason` gate, D-05/D-23); `depth_label` (`Depth | null`, D-06); `partial` / `degraded` (a guard-fired completed run is degraded, not partial); the partial-run paragraph (no node ids, two non-partial exceptions); `trace_token` on post-dispatch refusals in section 3.0 (D-04); section 3.1.1 (no `debug` keyword, persist-before-refuse, the cyclic wiring, two answering nodes and a missing `items` are no longer 500s). Added `UnparseableWiringError {violations}`, `InvalidNodeSettingError {setting}`, `InvalidGuardDeclarationError`, `AmbiguousAnswerPositionError` and the 503 `EnvironmentDigestUnavailable` to the `/query`, `/compare` and corpus refusal lists. The `/trace/resolve` rows now follow D-03 (per-arm `wiring_id`, pre-injection hash), D-12..D-14 (NodeTrace fields) and D-17 (truthful sequential dispatch). Open question 13 and its section 5.2 defect row are marked resolved by D-05. The `/query` and MCP live checks are marked as recorded before Phase 13, with the expected values; they were not re-run live.
**Test:** none (documentation only).

### B-WR-01: `parse_wiring` still raises on malformed `provides` / `evidence_position`

**Files modified:** `databasise/validator/parse.py`, `databasise/tests/seam/test_review13_fixes.py`
**Commit:** dbb34bf
**Applied fix:** A non-list `provides` and a non-mapping `evidence_position` are `invalid-wiring-document` violations; a non-string `provides` entry is `unknown-provides` and a non-string evidence node is `unknown-evidence-node`. No unhashable value reaches the `in raw_nodes` test. The module docstring records the rule.
**Test:** `test_a_malformed_top_level_reference_is_reported_not_raised`, parametrised over the review's three probes plus a string `evidence_position`.

### B-WR-02: Guard pre-flight raises a bare `TypeError`

**Files modified:** `databasise/runner/scheduler.py`, `databasise/runner/guards.py`, `databasise/tests/seam/test_review13_fixes.py`
**Commit:** 133272d
**Applied fix:** `_validated_guards` raises `GuardDeclarationError` (with `node_id`) for a `config.guards` that is not a list. `declare_guard` raises `GuardDeclarationError` for a non-string `name` or `evaluating_node`; the check sits after the granularity check, so the protected four-keyword call in `test_dpr_fallback_guard.py` still reaches the granularity refusal first. The engine's existing mapping turns both into the 422 `InvalidGuardDeclarationError` before dispatch.
**Test:** `test_a_malformed_guard_declaration_is_a_named_422_before_dispatch`, parametrised over `guards: 5`, a string, a list `evaluating_node`, a list name and an int name; it also asserts no `trace_token` (pre-dispatch).

### B-WR-03: A post-dispatch failure discards spend that was already metered

**Files modified:** `databasise/runner/scheduler.py`, `databasise/tests/seam/test_review13_fixes.py`, `docs/gui/API-INVENTORY.md`
**Commit:** 8067e25
**Status:** fixed: requires human verification (budget-accounting semantics)
**Applied fix:** `_stopped_trace` takes optional `spent` and `tokens`. In the post-dispatch `except`, when `meter()` had already run, the failed trace keeps the body's reported `TokenAccounting` and the metered `spent`; when `_body_report` or `meter()` itself raised, the trace keeps `spent=None` and an empty `TokenAccounting()` as before. `budget_state` stays `halted` and `realised_budget_share` stays 0.0, unchanged from the review's suggested fix.
**Test:** `test_a_post_dispatch_failure_keeps_the_spend_already_metered` (a `calls_llm` node reports 5+3 tokens, its guard then raises; the failed trace has `spent == 8` and the reported tokens).
**Needs a human look:** a failed node whose kept tokens carry `counted_by: "unbudgetable"` now makes `assemble_token_breakdown` raise `UnbudgetableParticipantError` on that run, where before the zeroed tokens hid it. That follows CONTRACT §9, but it changes which refusal such a run gets.

### B-WR-04: A guard signal missing at run time becomes a generic `node_failed` partial 200

**Files modified:** `databasise/seam/engine.py`, `databasise/seam/refusals.py`, `databasise/tests/seam/test_review13_fixes.py`
**Commit:** 888f972
**Status:** fixed: requires human verification (D-19 reading)
**Applied fix:** D-19 says "A missing evaluating node or missing key is a refusal, never a fire", so the review's first option was taken; D-19's text was not amended. In the query path's post-persist block, a `GuardDeclarationError` found in `scheduled["node_exceptions"]` is logged with its node id and raised as `InvalidGuardDeclarationError`, which picks up the persisted run's `trace_token` through the existing D-04 handler. It is checked before the store-fault check. The `InvalidGuardDeclarationError` docstring records the run-time case. The write paths (ingest, delete) were left unchanged: they already refuse any node exception with a `ForeignEngineRefusalError` after dropping staged writes, so the failure is already a refusal and never a fire there. Raising a different class there would bypass the `except ForeignEngineRefusalError` that drops the pending writes.
**Test:** `test_a_signal_missing_at_run_time_is_a_named_refusal_with_a_trace` (a passthrough guarded on a signal it never emits; the body is exactly `refusal_type`, `message`, `trace_token`, so no node id is exposed).
**Needs a human look:** on ingest and delete, a missing guard signal is still the 502 `ForeignEngineRefusalError`, not the 422. No shipped corpus wiring declares a guard.

## Skipped Issues

None.

## Notes for the orchestrator

- Info findings (A-IN-*, B-IN-*) were out of scope and are untouched. A-IN-03 (the engine injectors that run before `parse_wiring`) is the remaining WIRE-06 gap next to B-WR-01.
- Commits this iteration, each with the `phase/13` trailer and the Co-Authored-By line: 84a538b (A-WR-01), d421d06 (A-WR-02), 7651a34 (A-WR-03), dbb34bf (B-WR-01), 133272d (B-WR-02), 8067e25 (B-WR-03), 888f972 (B-WR-04), 4c8394f (A-WR-04). This report is not committed; it belongs in a separate `.planning/` commit.

---

_Fixed: 2026-10-20_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_

## Iteration 2

**Fixed at:** 2026-10-20
**Source review:** .planning/phases/13-selectors-wiring-runner/13-REVIEW-ITER2.md (deep, fix verification: 0 critical, 3 warning, 6 info)
**Iteration:** 2

**Summary:**
- Findings in scope: 3 (WR-01..03; IN-01..06 out of scope)
- Fixed: 3
- Skipped: 0
- Status: all_fixed

Each finding was checked against the source before the fix. Isolation: `workflow.use_worktrees` is `false`, so the fixes were edited and committed in the main checkout, and the gates below ran there.

### WR-01: a malformed `provides` on the engine query path was a bare TypeError

**Files modified:** `databasise/wirings/resolve.py`, `databasise/tests/seam/test_review13_fixes.py`
**Commit:** cb93354
**Status:** fixed
**Confirmed against source:** `without_recipe_only_nodes` had three unchecked reads:
- It ran `node_id in nodes` over `provides` with no type check, a TypeError for `[["a"]]`.
- It called `.get` on each node, an AttributeError for a non-object node.
- It called `.values()` on `recipe`.

The other steps before `parse_wiring` in `_execute_resolved` do not read `provides` or `evidence_position`: `canonicalise`, `_inject_query`, `_inject_token_allowance` and `_inject_max_total_tokens`. The reads of both fields after `parse_wiring` are guarded by its refusal.
**Applied fix:**
- When `nodes` is not an object, the function returns the copy unchanged.
- It reads `provides`, `deps` and `recipe` values only when they are lists of strings, or a dict for `recipe`. Anything else is skipped and left for `parse_wiring` to report.
- Capability matching and promotion share the function, so they get the same tolerance.

**Regression test:** `test_a_malformed_wiring_on_the_engine_query_path_is_unparseable_wiring` goes through `Databasise._execute_resolved` and expects `UnparseableWiringError` for six shapes:
- a list in `provides`
- a string `provides`
- a list `evidence_position.node`
- a string `evidence_position`
- a non-object node
- a list inside `deps`

### WR-02: a non-numeric evidence `score` escaped as a pydantic ValidationError

**Files modified:** `databasise/seam/evidence.py`, `databasise/tests/seam/test_review13_fixes.py`
**Commit:** 8427350
**Status:** fixed
**Confirmed against source:** `mint_evidence_refs` checked finiteness only for `numbers.Real` scores and passed anything else to `EvidenceRef(score=...)`. Pydantic then raised `ValidationError`, which the engine's `except MalformedEvidenceItemError` does not catch.
**Applied fix:** a score that is not `None` must be a `numbers.Real` and not a `bool`. Anything else raises `MalformedEvidenceItemError(reason="carries a non-numeric score")`. The engine maps that error to the 502 `MalformedDriverOutput`, which carries the persisted run's `trace_token`.
**Decision on `"0.5"`: refused.**
- The shipped parts emit floats: the vector store builds `float(score)` (`stores/vector.py:399`), and PPR does the same (`parts_core/hipporag/ppr.py:87`).
- A string score is therefore a part regression, and coercing it would hide that regression from the trace.
- `bool` is refused for the same reason, because pydantic would coerce it to 0.0 or 1.0.

**Regression test:** the A-WR-02 parametrised test `test_a_malformed_items_value_is_malformed_driver_output_with_a_trace` gains `"x"`, `"0.5"`, `True`, `[1]` and `{"a": 1}`. Each case asserts `failure_class == "MalformedDriverOutput"` and a non-empty `trace_token`.

### WR-03: API-INVENTORY still described pre-Phase-13 selector, evidence and RUN-02 behaviour

**Files modified:** `docs/gui/API-INVENTORY.md`
**Commit:** f31fbca
**Status:** fixed
**Confirmed against source:** the selector mapping was checked with an in-process probe of `resolve_selector` over the default registry. The probe gave:
- `reads_vector:entities` → local, `reads_vector:relationships` → global, both → hybrid
- `reads_graph` alone, with `calls_llm`, or with `reads_kv` → hipporag
- `reads_graph` with `calls_rerank` → local
- the write effects and `mutates_store` → `UnsatisfiableSelectorError`
- `[]` → `EmptyCapabilitySelectorError`
- node counts: naive 7, bypass 1, hybrid 17, local 15, global 15, hipporag 14

The `evidence_position` values were read from the arm patches and from `base.json`. `openai_compat.py:224-226` returns `call_count=1, counted_by="unbudgetable"`.

**Applied fix:**
- **Rewritten:**
  - the `capability` row (:108): the D-01 mapping, its refusals and SEAM-10
  - the `evidence` row (:124): the D-02 per-arm positions, the HippoRAG `top_k` cut, the WR-02 MalformedDriverOutput rule and updated citations
  - the :146 sentence, to the RUN-02 behaviour
- **Removed:** the hybrid/global caveats in the compare pre-submit checks (:256) and in the gaps paragraph (:260).
- **Marked resolved by D-01:** the defect row (:776), the dry-run note (:787) and open question 10 (:821).
- **Nearby text in the same state:**
  - the compare refusal list (:244) now names the usage-less shipped-client case
  - the wirings-list row (:717) now gives hipporag 14 nodes, says every arm is reachable, and says the index-side nodes never dispatch on a query

### Iteration 2 skipped issues

None.

### Iteration 2 verification

- **Where:** the main checkout (`workflow.use_worktrees: false`), using `databasise/.venv`.
- **Per fix:** each fix was re-read after the edit and checked with `ast.parse`. `tests/seam/test_review13_fixes.py` was run after each code fix; the final run gave 29 passed.
- **Wave command:** `cd databasise && .venv/bin/pytest -q tests/seam tests/runner tests/validator tests/wirings tests/identity tests/parts tests/parts_core tests/evidence tests/parity` gave 1862 passed, 3 deselected, in 526s.
- **Not run:** no `-m live` test was run.

### Iteration 2 notes for the orchestrator

- **Commits:** cb93354 (WR-01), 8427350 (WR-02) and f31fbca (WR-03). Each carries the `phase/13` trailer and the Co-Authored-By line.
- **Stale inventory text outside WR-03's scope (not edited):**
  - The default-selector paragraph (:111) and the `answer` row (:123) still describe HippoRAG's provides node as `assemble-result`, with a passage-dump answer. `base.json` now has `provides: ["qa"]`.
  - The promote-helper note (:352) gives full-wiring node counts (hipporag 13). Promotion matches the query-run node set instead.
- **Hardening without a test:** WR-01 also makes a non-dict `recipe` tolerated. `parse_wiring` does not validate `recipe`, so that shape now runs instead of raising AttributeError. No test pins it.

_Iteration 2 fixed: 2026-10-20_
_Fixer: Claude (gsd-code-fixer)_
