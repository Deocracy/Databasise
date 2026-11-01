---
phase: 13-selectors-wiring-runner
reviewed: 2026-10-20T00:00:00Z
depth: deep
lane: B
diff_base: b0b5a6c
files_reviewed: 28
files_reviewed_list:
  - databasise/runner/budget.py
  - databasise/runner/guards.py
  - databasise/runner/scheduler.py
  - databasise/runner/trace.py
  - databasise/validator/blast_radius.py
  - databasise/validator/depth.py
  - databasise/validator/errors.py
  - databasise/validator/execution_mode.py
  - databasise/validator/parse.py
  - databasise/parts/registry.py
  - databasise/parts/schema.py
  - databasise/parts_core/fixpoint_body.py
  - databasise/parts_core/hipporag/assemble_result.py
  - databasise/parts_core/hipporag/fact_filter.py
  - databasise/parts_core/lightrag/assemble.py
  - databasise/parts_core/lightrag/chunk_sel_kg.py
  - databasise/parts_core/lightrag/chunk_vector.py
  - databasise/parts_core/lightrag/entity_lookup.py
  - databasise/parts_core/lightrag/relation_lookup.py
  - databasise/parts_core/lightrag/truncator_token_budget.py
  - databasise/wirings/resolve.py
  - databasise/wirings/lightrag/base.json
  - databasise/wirings/lightrag/arm-bypass.json-patch.json
  - databasise/wirings/lightrag/arm-global.json-patch.json
  - databasise/wirings/lightrag/arm-hybrid.json-patch.json
  - databasise/wirings/lightrag/arm-local.json-patch.json
  - databasise/wirings/lightrag/arm-naive.json-patch.json
  - databasise/wirings/hipporag/base.json
  - databasise/evidence/HIPPORAG-PORT-RECORD.md
findings:
  critical: 0
  warning: 4
  info: 6
  total: 10
status: issues_found
---

# Phase 13: Code Review Report (Lane B)

**Reviewed:** 2026-10-20
**Depth:** deep (cross-file: scheduler -> guards/budget/trace, parse -> engine `_refuse_unparseable`, assemble -> engine evidence minting -> `mint_evidence_refs`, guard errors -> engine `_run_wiring` translation)
**Files Reviewed:** 28 source/wiring files plus one evidence record
**Status:** issues_found

## Summary

I reviewed the runner (sequential dispatch, one trace per node, closed reason codes, guard signals), the validator (WIRE-06 robustness, ghost references, pointer escaping, a single placement source), the registry effect and namespace checks, the plain-dict guard parts, the KG-arm `assemble.items` evidence, and the per-arm wiring ids. The D-17 sequential loop, the D-13 trace completeness, the D-26 cancellation split and the D-05 codes behave as documented. I confirmed each one with a scratchpad probe against the real modules.

None of the findings is a BLOCKER. No §18 leak was found in this lane: node ids and part names stay in `cross_process_failure_cause`, in `Violation.pointer`/`message` (private per D-07/D-25) and in `GuardDeclarationError.node_id`, and the engine translator keeps all of them private.

Four defects are real and reproducible:
- two "never raises" contracts (WIRE-06 `parse_wiring`, and the runner's pre-flight guard validation) still raise a bare `TypeError` on malformed author data;
- a post-dispatch failure throws away spend that was already metered;
- a guard whose signal is missing at run time reaches the consumer as a generic `node_failed` partial 200 instead of a refusal.

Tests were not run. The edit-guard hook blocks `pytest` on the `tests/runner`, `tests/validator` and `tests/parts` directories because they contain protected files, so every claim below was checked with standalone probe scripts in the session scratchpad.

## Warnings

### WR-01: `parse_wiring` still raises on malformed `provides` / `evidence_position` (WIRE-06 "reports, never raises")

**File:** `databasise/validator/parse.py:284-303`
**Issue:** The new ghost-reference check tests `name not in raw_nodes` and `evidence_position.get("node") not in raw_nodes`. `raw_nodes` is a dict, so an unhashable value raises `TypeError: unhashable type`. A non-list `provides` (for example the string `"generate"`) is skipped by `provides if isinstance(provides, list) else []`, so it is accepted without any violation.
Probe results:
- `{"nodes": {...}, "provides": [["a"]]}` -> `TypeError`
- `{"nodes": {...}, "evidence_position": {"node": ["a"]}}` -> `TypeError`
- `{"nodes": {...}, "provides": "ghost"}` -> no violations

**Failure scenario:**
- The engine calls `parse_wiring` at `engine.py:2083` before `_refuse_unparseable`, so the `TypeError` passes every named refusal and the consumer gets an unstructured 500. That is the outcome WIRE-06 and the phase goal ("never an unstructured 500 from the wiring layer") rule out.
- A string `provides` passes validation. At `engine.py:2153` the engine then iterates it character by character, and `_select_answer` finds no answering node.

**Fix:**
```python
provides = doc.get("provides")
if provides is not None and not isinstance(provides, list):
    violations.append(Violation(CODE_INVALID_WIRING_DOCUMENT, "/provides", "`provides` must be a list of node ids"))
for index, name in enumerate(provides if isinstance(provides, list) else []):
    if not isinstance(name, str) or name not in raw_nodes:
        violations.append(Violation(CODE_UNKNOWN_PROVIDES, f"/provides/{index}", ...))
evidence_position = doc.get("evidence_position")
if evidence_position is not None and not isinstance(evidence_position, dict):
    violations.append(Violation(CODE_INVALID_WIRING_DOCUMENT, "/evidence_position", ...))
elif isinstance(evidence_position, dict):
    node = evidence_position.get("node")
    if not isinstance(node, str) or node not in raw_nodes:
        violations.append(Violation(CODE_UNKNOWN_EVIDENCE_NODE, "/evidence_position/node", ...))
```

### WR-02: Guard pre-flight raises a bare `TypeError` that the engine does not translate (WIRE-05 / D-07)

**File:** `databasise/runner/scheduler.py:429-450`, `databasise/runner/guards.py:73-97`
**Issue:**
- `_validated_guards` iterates `(config or {}).get("guards") or []` without checking that it is a list. `"guards": 5` raises `TypeError: 'int' object is not iterable`.
- `declare_guard` type-checks only `granularity` and `signal`, so `name` and `evaluating_node` can be any JSON value. `guard.evaluating_node not in reachable` (a `set`) then raises `TypeError: unhashable type: 'list'` for `"evaluating_node": ["a"]`.

Both probes raised out of `run_wiring`. Engine `_run_wiring` (`engine.py:662-683`) catches only `InvalidMaxConcurrencyError`, `InvalidTokenAllowanceError`, `GuardDeclarationError` and `EnvironmentDigestError`.

**Failure scenario:** A misdeclared guard reaches the consumer as a 500, not as `InvalidGuardDeclarationError` (422). This contradicts the `run_wiring` docstring at `:729-732`, which promises `GuardDeclarationError` for "an entry that is not a mapping, has missing or extra keys...". A non-string `name` is also accepted and stored in `NodeTrace.guards_fired`, which the derived trace schema types as strings.
**Fix:** Raise `GuardDeclarationError` instead of letting the `TypeError` escape:
```python
raw_guards = (config or {}).get("guards") or []
if not isinstance(raw_guards, list):
    raise GuardDeclarationError(str(raw_guards), None, node_id=node_id, problem="config.guards must be a list")
```
In `declare_guard`, add `if not isinstance(name, str) or not isinstance(evaluating_node, str): raise GuardDeclarationError(...)` before the granularity check, so the protected four-keyword call keeps its ordering.

### WR-03: A post-dispatch failure discards spend that was already metered

**File:** `databasise/runner/scheduler.py:653-686` (`_stopped_trace` at `:599-616`)
**Issue:** The post-dispatch `except Exception` builds the failed trace through `_stopped_trace`, which always writes `spent=None` and `tokens=TokenAccounting()`. By that point `_body_report` and `meter()` may already have run (`:663-664`). Only `evaluate_guards` or the `NodeTrace` construction raised.
**Failure scenario:**
- A `calls_llm` node, such as HippoRAG `fact-filter`, completes a real LLM call and returns `tokens`.
- Its guard evaluation then raises because the signal key is missing (WR-04).
- The trace records zero tokens and `spent: null`. `assemble_token_breakdown(record.nodes)` (`engine.py:2183`) under-reports the run's real spend, and the budget record says nothing was spent at a boundary that was crossed and billed.

This breaks CONTRACT §9's "the cost belongs to the node that declared the boundary it crossed".

**Fix:** Carry whatever was already measured into the failed trace:
```python
tokens = TokenAccounting(); token = None
try:
    tokens, cache_hit = _body_report(output)
    token = meter(node_id, part.effects, allowance, tokens)
    ...
except Exception as exc:
    trace = _stopped_trace("failed", execution_mode, wall_clock_ms, cause, "halted")
    trace.tokens = tokens
    trace.spent = token.spent if token is not None else None
```

### WR-04: A guard signal missing at run time becomes a generic `node_failed` partial 200, not a refusal (D-19)

**File:** `databasise/runner/guards.py:110-118`, `databasise/runner/scheduler.py:665, 680-686`
**Issue:** D-19 says "A missing evaluating node or missing key is a refusal, never a fire." `evaluate_guards` raises `GuardDeclarationError`, but `_dispatch_node`'s catch-all records it as an ordinary node failure with `REASON_NODE_FAILED`. The engine inspects `node_exceptions` only for store faults (`engine.py:2145-2150`). The consumer therefore gets a 200 envelope with `partial=true`, `stop_reason="node_failed"` and no answer, which looks the same as a transient part crash. The pre-flight path for the same class of defect is a named 422 (`InvalidGuardDeclarationError`).
Probe: a passthrough node guarded on signal `"s"` that it never emits -> `partial=True, stop_reason='node_failed'`, with the exception in `node_exceptions`.
**Failure scenario:** A part refactor drops `guard_fired` from fact-filter's output, the inverse of the `_GuardAwareResult` removal in this phase. Every HippoRAG query then returns a degraded 200 with a null answer instead of a wiring-contract refusal. Consumers and the ledger read this as a flaky modality, not a misdeclared wiring.
**Fix:** In the engine's post-persist block, map a `GuardDeclarationError` found in `scheduled["node_exceptions"]` to `InvalidGuardDeclarationError` (it already carries `trace_token` per D-04). The alternative is to amend D-19's text to say this case is recorded as `node_failed` by design.

## Info

### IN-01: A cancelled node leaves no cause in the trace or in `node_exceptions`

**File:** `databasise/runner/scheduler.py:642-651`
**Issue:** The D-26 path returns `_NodeOutcome(trace, False, None, REASON_CANCELLED)` with `cause=None`. Even `debug=True` cannot show which body raised `CancelledError` or why. A probe confirmed that `node_exceptions == {}`.
**Fix:** Pass `"CancelledError: node body raised CancelledError outside run cancellation"` as the cause.

### IN-02: `run_wiring` echoes any `concurrency_setting` while always running sequentially

**File:** `databasise/runner/scheduler.py:695-696, 843-844`
**Issue:** D-17 makes `sequential` true by construction, but the value passed in is echoed back unvalidated. The public `databasise.run_wiring` (`__init__.py:87`) forwards a caller value, so `"parallel"` would be recorded for a run that executed sequentially, which falsifies the A/A key the echo exists to protect.
**Fix:** Refuse any value other than `"sequential"`, or ignore the argument and always echo `"sequential"`.

### IN-03: Stale `InvalidMaxConcurrencyError` docstring

**File:** `databasise/runner/scheduler.py:210-213`
**Issue:** The docstring still says "a value `int()` cannot coerce". Since D-07 no value is coerced: a float or a bool is refused too. `InvalidTokenAllowanceError` (`:224-228`) has the same wording.
**Fix:** Change it to "any value that is not a true `int` (bools, floats and strings are never coerced)".

### IN-04: The unpatched LightRAG base shares `wiring_id` with the naive arm and carries no `arm_id`

**File:** `databasise/wirings/lightrag/base.json` (top level), `databasise/wirings/lightrag/arm-naive.json-patch.json:6`
**Issue:**
- naive keeps `wiring_id: "lightrag-base"` (D-03). The 17-node base itself also has that id, and it has no `arm_id`.
- Any path that runs `load_base()` directly, such as the parity or storage-audit harnesses, records `arm_id="seam"` (`engine.py:2123` fallback) under the same `wiring_id` as naive, with a different node set.
- Promotion matches traces on node sets, so this is not a live bug, but `wiring_id` alone does not identify the arm.

**Fix:** Either give the base its own id, such as `lightrag-full`, with naive's patch setting `lightrag-base`, or record in `resolve.py` that the raw base is never a run identity.

### IN-05: `evaluate_guards` does not require the signal value to be a boolean

**File:** `databasise/runner/guards.py:117`
**Issue:** D-19 defines `signal` as "the boolean output key", but the comparison is a plain `!=`. A part that emits `"guard_fired": None`, or a string, fires the guard (`None != False`) and marks the run degraded with `fallback_path_taken`.
**Fix:** Raise `GuardDeclarationError` when `not isinstance(output[guard.signal], bool)`.

### IN-06: KG-arm evidence has `score: null` on every item

**File:** `databasise/parts_core/lightrag/assemble.py:161`
**Issue:**
- On hybrid, local and global, `items` come from `chunk-sel-kg` -> `rerank`. `_hydrate` (`chunk_sel_kg.py:139-151`) copies the KV record, which has no `score`, and `rerank` adds none (`rerank*.py:26-39`).
- `c.get("score")` is therefore `None` for every KG-arm evidence ref, while naive returns cosine scores.
- `mint_evidence_refs` accepts `None`, so nothing fails. However, consumers comparing arms on the §18 envelope see a field whose presence depends on the modality arm. That is a consumer-visible difference the compatibility constraint is meant to avoid.

**Fix:** Either document `score: null` as the KG-arm contract in the evidence record, or emit the rank position (or the rerank score, when rerank is enabled) as the score.

---

_Reviewed: 2026-10-20_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
