---
phase: 13-selectors-wiring-runner
reviewed: 2026-10-20T00:00:00Z
depth: deep
iteration: 2
diff_range: 71f708d..4c8394f
commits_reviewed: [84a538b, d421d06, 7651a34, dbb34bf, 133272d, 8067e25, 888f972, 4c8394f]
files_reviewed: 10
files_reviewed_list:
  - databasise/identity/env.py
  - databasise/runner/guards.py
  - databasise/runner/scheduler.py
  - databasise/seam/engine.py
  - databasise/seam/evidence.py
  - databasise/seam/refusals.py
  - databasise/validator/parse.py
  - databasise/tests/seam/test_mutable_store_exclusion.py
  - databasise/tests/seam/test_review13_fixes.py
  - docs/gui/API-INVENTORY.md
findings:
  critical: 0
  warning: 3
  info: 6
  total: 9
status: issues_found
---
# Phase 13: Code Review Report (iteration 2, fix verification)

**Reviewed:** 2026-10-20
**Depth:** deep. Each fix was traced into its callers: `wirings/resolve.py` `without_recipe_only_nodes`, engine `_execute_resolved`, `_run_wiring`, `_node_result_or_refuse`, ingest and delete refusal handling, `seam/tokens.py` `assemble_token_breakdown`, `runner/budget.py` `meter`, `clients/openai_compat.py` `_token_accounting`, REST `_pydantic_validation_response`, and the HippoRAG guard-signal parts.
**Files Reviewed:** 10 (the files changed by `git diff 71f708d 4c8394f`)
**Status:** issues_found (0 Critical, 3 Warning, 6 Info)

## Summary

The review checked each of the eight fix commits for two things: whether it resolves its iteration-1 finding, and whether it adds a regression, a §18 leak or a contract break. No commit adds a §18 leak. All new public refusal bodies were checked with probes:

- `InvalidGuardDeclarationError` carries exactly `{refusal_type, message, trace_token}`.
- `MutableStoreComparisonExcludedError` carries `component: "mutates_store"`.
- The `EnvironmentDigestError` message names only the exception class.

Node ids and part names go only to the server log, to `_`-prefixed attributes and to private violation messages.

| Commit | Finding | Verdict |
|---|---|---|
| 84a538b | A-WR-01 | Resolved. The test edit changes only assertions (see below). |
| d421d06 | A-WR-02 | Partly resolved. A non-numeric `score` is still a bare 500 (WR-02). |
| 7651a34 | A-WR-03 | Resolved. `functools.cache` still stores only successful results, and the message names only the class. |
| dbb34bf | B-WR-01 | Resolved inside `parse_wiring` only. On the engine query path the review's own first probe still raises `TypeError` (WR-01). |
| 133272d | B-WR-02 | Resolved. A falsy non-list `guards` is still accepted silently (IN-05). |
| 8067e25 | B-WR-03 | Resolved, and consistent with D-08 and the HIPP-19/RUN rows (analysis below). The schema and deviation text are now stale (IN-03). |
| 888f972 | B-WR-04 | Resolved on the query path. The refusal is raised after the persist and carries `trace_token`. The ingest/delete asymmetry is consistent with D-19 (IN-01). |
| 4c8394f | A-WR-04 | Incomplete. The WIRE-01 and WIRE-02 consumer rows and one RUN-02 sentence are still false (WR-03). |

### 8067e25 (B-WR-03): does keeping the unbudgetable tokens on a failed node turn a partial run into a wrong refusal?

No, with one caveat that predates this fix.

**Which D-08.** Phase 13's own D-08 is about validator robustness and does not apply here. The governing decision is Phase 4 D-08: "an `unbudgetable` participant produces an explicit refusal. Never a substituted or estimated number." `engine.py:2193` and `refusals.py:735` both cite it. CONTRACT §4 and §18.2 (CONTRACT.md:280, :773) state the same rule.

**Before the fix.** A node whose body returned `counted_by: "unbudgetable"` could fail after it was metered: an `evaluate_guards` comparison raised, or the `NodeTrace` construction raised. Its tokens were then replaced by `TokenAccounting()`, which reports `counted_by: "none"`. That is the substituted number D-08 forbids, and the run answered 200 partial.

**After the fix.** The same run raises `UnbudgetableParticipantError`. The rest of the system already treats an unbudgetable participant that way:

- **HIPP-19 / Phase 12 D-07.** `sum_token_accountings` gives the sentinel for mixed or unknowable counters.
- **RUN-02 / Phase 8 D-05.** `openai_compat.py:224-226` returns `call_count=1, counted_by="unbudgetable"` for a response with no `usage`.
- **Other nodes in the run.** `assemble_token_breakdown` already refused for an unbudgetable completed node, and for an unbudgetable completed node in a run where another node failed.
- **Probe.** A completed unbudgetable node and an unbudgetable node whose guard comparison raises now give the same refusal. A metered (non-unbudgetable) node whose guard comparison raises still gives the 200 partial `node_failed`.

**D-04 and CONTRACT §9 still hold.** D-04 lists the unbudgetable participant as a post-dispatch refusal. The run is persisted before the refusal, and the refusal carries `trace_token`. So the partial run is still traced and resolvable, and CONTRACT §9's "MUST NOT be discarded" is met.

**Precedence.** The token breakdown is the last refusal checked (`engine.py:2195`). It runs after the guard and store-fault checks, `AmbiguousAnswerPositionError` and `MalformedDriverOutput`, so it hides none of them. The guard-signal case that motivated B-WR-03 now refuses earlier, as `InvalidGuardDeclarationError` (888f972).

**Write paths.** Ingest and delete never call `assemble_token_breakdown`, so the change cannot affect them.

**The caveat (IN-04).** A body that raises after an unbudgetable call is still traced as `counted_by: "none"` and answers 200 partial. The D-08 outcome therefore depends on where the exception happened. That predates this fix.

### 888f972 (B-WR-04): D-19, persist order, trace_token and the ingest/delete asymmetry

**D-19 and the query path.** D-19 says "a missing evaluating node or missing key is a refusal, never a fire". On the query path the `GuardDeclarationError` is mapped to `InvalidGuardDeclarationError` (`engine.py:2150-2152`) inside the `try` that runs after `self._trace_store.persist(record_dict)`. The `except SeamRefusalError` handler then sets `trace_token`.

**Probe.** The refusal body is `{refusal_type, message, trace_token}`. `resolve_trace(trace_token)` returns `partial: true, stop_reason: "node_failed"`, and the debug trace keeps the node cause. Both shipped HippoRAG guard signals are emitted on every return path: `fact_filter.py:85, 103-105` and `assemble_result.py:72`. So no legitimate HippoRAG run reaches the new refusal.

**Ingest and delete.** On these paths the same defect reaches `_node_result_or_refuse`, which raises a 502 `ForeignEngineRefusalError` with `failure_class: "UnclassifiedEngineFailure"` (`refusals.py:808-810`). It is a refusal, never a fire, so D-19's text holds. Two caveats:

- The fixer's reason ("a different class would bypass the `except ForeignEngineRefusalError` that drops pending writes") describes the current code, not a constraint.
- The asymmetry is not documented (IN-01).

No shipped corpus wiring declares a guard, so this path cannot be reached today.

### 84a538b: the edit to test_mutable_store_exclusion.py

**What `git show 84a538b` changed.** The edit has three hunks, and every changed line is an `assert` or a comment:

- **Lines 109-112.** The removed assertions were `_CBM_NAME_AT_VERSION in message` and `component == _CBM_NAME_AT_VERSION`. The new ones are `not in message`, `component == "mutates_store"` and `_component == _CBM_NAME_AT_VERSION`.
- **Line 144.** `component == "mutates_store"`.
- **Lines 182-186.** `message.count(...) == 1` is replaced by `"mutates_store" in message`, and the forbidden tuple gains the part name and `codebase-memory-mcp`.

No fixture, setup or call changed.

**Ledger check.** The Read tool was used on `ledger/REQUIREMENTS.json` (ledger_version 678). The file is not any row's `test_ref`. WIRE-17 points to `tests/seam/test_refusal_reachability.py` and LRAG-03 to `tests/seam/test_lightrag_ingest_mach11.py`. It is also not in `check_edit_grants`, and `check_guard` is empty. The edit-guard hook allowed `pytest` on this file but blocked it on protected and helper files, which suggests the hook does not count it as a helper either.

**Test runs.** `tests/seam/test_review13_fixes.py` and `tests/seam/test_mutable_store_exclusion.py` were run: 23 passed. The edit-guard hook blocks `pytest` on directories or files that contain protected tests, so the protected suites were not re-run in this iteration. That includes `test_refusal_reachability.py` (WIRE-17) and `test_dpr_fallback_guard.py` (HIPP-14). The fixer reports 1851 passed on the full wave command. No `-m live` test was run.

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: B-WR-01 is fixed in parse_wiring, but on the engine query path a malformed `provides` still gives an unstructured 500

**File:** `databasise/wirings/resolve.py:166-176` (called from `databasise/seam/engine.py:2084`, before `parse_wiring` at :2085)
**Issue:** `_execute_resolved` runs `_without_recipe_only_nodes(resolved)` before `parse_wiring`. That function iterates `provides` without checking its type. At line 168, `node_id in nodes` raises `TypeError: unhashable type: 'list'` for `provides: [["a"]]`, which is the first probe in B-WR-01. B-WR-01's failure scenario was this engine path ("the TypeError passes every named refusal and the consumer gets an unstructured 500"), and that path still reproduces.

**Probe results** (through `Databasise._execute_resolved`):

| Input | Result |
|---|---|
| `{"provides": [["a"]]}` | `builtins.TypeError: unhashable type: 'list'`, traceback ending at resolve.py:168 |
| `{"provides": "a"}` and the two `evidence_position` shapes | `UnparseableWiringError` (fixed) |

**Coverage gap.** The regression test `test_a_malformed_top_level_reference_is_reported_not_raised` calls `parse_wiring` directly, so it does not cover the engine path.

**Other callers.** `without_recipe_only_nodes` is also shared by capability matching and promotion's trace-to-arm match (resolve.py:158-160).

**Reachability.** Not reachable from consumer input today, because every resolved wiring comes from committed files. This is the same exposure as the original finding.
**Fix:** Make the pruning step tolerate any shape and leave the reporting to `parse_wiring`:
```python
run_copy = copy.deepcopy(resolved)
nodes = run_copy.get("nodes")
if not isinstance(nodes, dict):
    return run_copy  # parse_wiring reports the malformed document
provides = run_copy.get("provides")
frontier = [n for n in (provides if isinstance(provides, list) else []) if isinstance(n, str) and n in nodes]
if frontier:
    keep: set[str] = set()
    while frontier:
        node_id = frontier.pop()
        if node_id in keep or node_id not in nodes:
            continue
        keep.add(node_id)
        node = nodes[node_id]
        deps = node.get("deps") if isinstance(node, dict) else None
        frontier.extend(d for d in (deps if isinstance(deps, list) else []) if isinstance(d, str))
```
Add one engine-level case (`_execute_resolved` with `provides: [["a"]]` raises `UnparseableWiringError`) to `test_review13_fixes.py`.

### WR-02: A-WR-02 still lets a non-numeric `score` escape as a pydantic `ValidationError`, which is an unstructured 500 with no `trace_token`

**File:** `databasise/seam/evidence.py:118-126`; `databasise/seam/rest.py:305-312`
**Issue:** `mint_evidence_refs` checks only `numbers.Real` scores for finiteness. Any other score type is passed straight to `EvidenceRef(score=score)` at line 126.

**Probe results:**

| `score` value | Result |
|---|---|
| `"x"`, `{"a": 1}`, `[1]` | `pydantic_core.ValidationError` |
| `"0.5"` | Silently coerced to `0.5` |

The `ValidationError` is not a `MalformedEvidenceItemError`, so the engine's `except MalformedEvidenceItemError` at `engine.py:2189` misses it. The exception is not a `SeamRefusalError` either, so it never receives `trace_token`. REST's `_pydantic_validation_response` re-raises a `ValidationError` that carries no refusal, so the result is a 500. This is the D-09 site and the failure class that A-WR-02 covered ("a part regression ... every local, global and hybrid query then returns HTTP 500"). Since D-02, the KG arms take their evidence from `assemble.items`, where `c.get("score")` is also the B-IN-06 field.
**Fix:**
```python
score = item.get("score")
if score is not None and (isinstance(score, bool) or not isinstance(score, numbers.Real)):
    raise MalformedEvidenceItemError(namespace=namespace, index=index, reason="carries a non-numeric score")
if isinstance(score, numbers.Real):
    ...  # the existing finiteness check
```
Add `{"id": "c1", "score": "x"}` to the parametrised A-WR-02 test.

### WR-03: A-WR-04 left the WIRE-01 and WIRE-02 consumer rows stating pre-Phase-13 behaviour, and 8067e25 kept a false RUN-02 sentence in the paragraph it edited

**File:** `docs/gui/API-INVENTORY.md:108, 124, 146, 256, 260, 776, 787, 821`
**Issue:** The fix report says every cited row was rewritten. The finding itself, though, was that the inventory "still describes the pre-Phase-13 consumer contract", and the sections the console builds from still contradict shipped Phase 13 behaviour:

- **:108, the `capability` selector row.** It says "only naive, bypass, local and hipporag are reachable … hybrid and global can never be selected", that `writes_graph`/`writes_kv`/`writes_vector` resolve to HippoRAG, and that `capability: []` silently resolves to bypass. In fact:
  - D-01 (WIRE-01) added `reads_vector:<namespace>` tokens: `reads_vector:entities` gives local, `reads_vector:relationships` gives global, and both give hybrid.
  - `writes_graph` is refused (Phase 12 D-16).
  - `capability: []` is refused (SEAM-10).
  - The row also claims the selectors.py docstring is false, which D-01 rewrote.
- **:124, the `evidence` row.** It says "evidence is always `[]` for hybrid, local and global". D-02 (WIRE-02) points those arms' `evidence_position` at `assemble` (for example `arm-local.json-patch.json:11`).
- **:256, :260.** "Do not offer hybrid or global as columns (unreachable)" and "Only four arms … can be compared."
- **:776, :787, :821.** The defect row, the dry-run note and open question 10 ("Unreachable arms") are not marked resolved by D-01. Open question 13 was marked resolved.
- **:146.** This paragraph was edited by 8067e25. It still says "An `OpenAICompatibleClient` response without `usage` is metered as zero calls and zero tokens (openai_compat.py:159-161)". `openai_compat.py:224-226` returns `TokenAccounting(call_count=1, counted_by="unbudgetable")` (RUN-02, Phase 8 D-05). Such a response therefore makes the query refuse with `UnbudgetableParticipantError`, which is the behaviour B-WR-03's human-verification note is about.

**Failure scenario:** CONTEXT says the console and tool consumers (CONN-03/05, GUI-04/05/07) regenerate fixtures from this inventory. A selector-resolution fixture built from :108 would have no hybrid or global column, would offer `capability: []` and `writes_graph` as working selectors, and would render KG-arm evidence as always empty. A token table built from :146 would show zeros for a run the engine refuses.
**Fix:**
- Rewrite :108 to the D-01 mapping in the selectors.py docstring, and :124 to D-02 (KG arms mint evidence from `assemble.items`; bypass declares none).
- Drop the hybrid/global caveats at :256 and :260.
- Mark :776, :787 and open question 10 resolved by D-01 (WIRE-01).
- Replace the :146 sentence with: "a response without `usage` reports `call_count: 1, counted_by: \"unbudgetable\"`, so the query refuses with `UnbudgetableParticipantError` (RUN-02)."

## Info

### IN-01: A guard signal missing at run time is a 422 on query but a 502 `UnclassifiedEngineFailure` on ingest and delete, and the inventory does not say so

**File:** `databasise/seam/engine.py:2150-2152`, `:938-948` (`_node_result_or_refuse`), `:1496-1500`, `:1758-1762`; `databasise/seam/refusals.py:808-810`; `docs/gui/API-INVENTORY.md:144`
**Issue:**
- **Consistency with D-19.** Both outcomes are refusals and neither is a fire, so D-19 holds on all three paths.
- **Classification differs.** On a write path the same wiring-contract defect is classified as a server-side foreign-engine failure, with the catch-all class.
- **Undocumented.** API-INVENTORY:144 lists `InvalidGuardDeclarationError` for ingest, delete and upload only before dispatch.
- **Reachability.** Latent: no shipped corpus wiring declares a guard.
**Fix:** Either document the write-path outcome at :144, or map `GuardDeclarationError` inside `_node_result_or_refuse` and widen the two `except ForeignEngineRefusalError` blocks to `except SeamRefusalError`, so the staged writes are still dropped.

### IN-02: The run-time `InvalidGuardDeclarationError` says the wiring "declares a malformed guard"

**File:** `databasise/seam/refusals.py:925-937`
**Issue:**
- **Message.** In the 888f972 case the declaration is well formed: the evaluating part's output lacks the key. The message reads the same as the pre-dispatch case, and the class docstring still opens with "Raised before any node is dispatched".
- **Telling the cases apart.** Consumers can tell the two cases apart only by whether `trace_token` is present.
**Fix:** Pass a reason into the constructor and choose between two fixed messages ("…emitted no declared guard signal at run time"). Do not add a public attribute.

### IN-03: B-WR-03 makes the derived schema's `spent` description and deviation row D7 inaccurate

**File:** `databasise/evidence/rig-trace.databasise.schema.json:102`, `databasise/evidence/RIG-TRACE-DEVIATIONS.md:22` (D7), `databasise/runner/scheduler.py:696-705`
**Issue:**
- **Stale text.** Both files say `spent` is "null where the node never completed". A `status: "failed"` node is now stamped with a non-null `spent` (8 in the regression test).
- **Inconsistent fields.** The same trace has `realised_budget_share: 0.0` and `budget_state: "halted"` even when the meter returned `within_budget`.
**Fix:** Change both descriptions to "null where the node's report was never metered". Either compute `realised_budget_share` from the kept token, or document the 0.0. Keep the schema-rebuild test in step.

### IN-04: A body that raises after an unbudgetable call still substitutes `counted_by: "none"`, so the D-08 refusal depends on where the failure happened

**File:** `databasise/runner/scheduler.py:626-648` (the `NodeExecutionError` branch through `_stopped_trace` with default `tokens`)
**Issue:** The probe gave two results:

| Case | Result |
|---|---|
| A `calls_llm` body reports unbudgetable tokens and then its guard comparison raises | `UnbudgetableParticipantError` |
| The same body raises after its call | 200 partial with `token_accounting: [{counted_by: "none"}]` |

This is not a regression: the body-raise path has no report to keep, and API-INVENTORY:146 says that a "none" row can hide an attempted call. After 8067e25, however, the two failure paths of the same node give opposite D-08 outcomes.
**Fix:** Record it as a known limit in the RUN/HIPP-19 notes, or have the context's metered clients accumulate `TokenAccounting` and carry it on `NodeExecutionError`.

### IN-05: A falsy non-list `config.guards` is still accepted silently, and a non-dict `config` is a bare `ValueError`

**File:** `databasise/runner/scheduler.py:429`; the engine injectors (A-IN-03)
**Issue:**
- **Falsy `guards`.** `(config or {}).get("guards") or []` turns `False`, `0`, `""` and `{}` into "no guards". A probe ran each to a clean 200. So B-WR-02's "named, never silent" rule does not cover them.
- **Non-dict `config`.** `config: "x"` raises `ValueError: dictionary update sequence element #0 …` before pre-flight. This predates the fixes and is A-IN-03 territory.
**Fix:** Use `raw_guards = (config or {}).get("guards", [])`, then apply the `isinstance(list)` check to the raw value. Leave the `config` shape to the A-IN-03 hardening.

### IN-06: Comments, docstrings and one test name contradict the fixed behaviour

**File:** `databasise/seam/engine.py:1246-1248`, `databasise/seam/engine.py:2143-2146`, `databasise/tests/seam/test_mutable_store_exclusion.py:171`
**Issue:**
- **`engine.py:1246-1248`.** The `compare` docstring says the refusal is raised "naming the offending component" (A-WR-01 made it name the capability).
- **`engine.py:2143-2146`.** The comment says that every other node exception keeps a degraded envelope "whose stop_reason carries the exception class name only". Since D-05 it is a closed code, and the comment now sits directly above the new guard refusal.
- **`test_mutable_store_exclusion.py:171`.** The test name `test_refusal_names_only_the_excluded_component` now asserts that the component is not named.
**Fix:** Update the two comments. Rename the unprotected test, for example to `test_refusal_names_the_capability_and_no_component`.

---

_Reviewed: 2026-10-20_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
