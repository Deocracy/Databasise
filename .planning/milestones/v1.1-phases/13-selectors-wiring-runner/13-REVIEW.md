---
phase: 13-selectors-wiring-runner
reviewed: 2026-10-20T00:00:00Z
depth: deep
diff_base: b0b5a6c
parts: "A (seam, environment identity, derived trace schema, parity report, GUI API inventory) + B (runner, validator, registry, parts, wirings, port record), merged; ids prefixed A-/B-. The two lanes' file lists are disjoint."
files_reviewed: 47
files_reviewed_list:
  - databasise/seam/engine.py
  - databasise/seam/envelope.py
  - databasise/seam/evidence.py
  - databasise/seam/promotion.py
  - databasise/seam/query.py
  - databasise/seam/redact.py
  - databasise/seam/refusals.py
  - databasise/seam/rest.py
  - databasise/seam/selectors.py
  - databasise/seam/compare.py
  - databasise/seam/corpus.py
  - databasise/seam/tokens.py
  - databasise/identity/env.py
  - databasise/evidence/parity_report.py
  - databasise/evidence/rig-trace.databasise.schema.json
  - databasise/evidence/RIG-TRACE-DEVIATIONS.md
  - databasise/evidence/PARITY-EVIDENCE.md
  - docs/gui/API-INVENTORY.md
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
  warning: 8
  info: 14
  total: 22
status: issues_found
---
# Phase 13: Code Review Report

**Reviewed:** 2026-10-20
**Depth:** deep (lane A traced into runner/scheduler.py, runner/guards.py, runner/trace.py, parts/registry.py, wirings/resolve.py, identity/canon.py, mcp/server.py; lane B traced scheduler -> guards/budget/trace, parse -> engine `_refuse_unparseable`, assemble -> engine evidence minting -> `mint_evidence_refs`, guard errors -> engine `_run_wiring` translation)
**Files Reviewed:** 47 (lane A 18, lane B 29). seam/compare.py, corpus.py and tokens.py are unchanged since b0b5a6c and were read only as callers.
**Status:** issues_found (no Critical; 8 Warning, 14 Info)

## Summary

Lane A covers the seam layer, environment identity, the derived trace schema and its deviation record, the parity report and the GUI API inventory. Lane B covers the runner (sequential dispatch, one trace per node, closed reason codes, guard signals), the validator (WIRE-06 robustness, ghost references, pointer escaping, a single placement source), the registry effect and namespace checks, the plain-dict guard parts, the KG-arm `assemble.items` evidence, and the per-arm wiring ids.

The main Phase 13 mechanisms work as the decisions describe. Each was checked against the source and with probes:

- **Capability resolution (D-01).** A probe of `resolve_selector` returned exactly the mapping in the docstring: reads_vector and reads_vector:chunks give naive; calls_llm gives bypass; reads_vector:entities gives local; reads_vector:relationships gives global; both namespace tokens give hybrid; reads_graph, alone or with reads_kv or calls_llm, gives hipporag; reads_graph with calls_rerank gives local; writes_graph is refused.
- **Node counts.** The one-node margin is correct: naive 7, local 15, global 15, hipporag 14.
- **Reason codes.** No node id, arm id or wiring id is a substring of any of the six closed reason codes, so the new substring check in `assert_no_forbidden_values` cannot fire on a legitimate code.
- **Runner.** The D-17 sequential loop, the D-13 trace completeness, the D-26 cancellation split and the D-05 codes behave as documented.
- **Persisting before refusals (D-04).** The RunRecord is persisted before any post-dispatch refusal. `refusal_body` exports `trace_token` on both REST and MCP.
- **§18 leaks in lane B's files.** None found. Node ids and part names stay in `cross_process_failure_cause`, in `Violation.pointer`/`message` (private per D-07/D-25) and in `GuardDeclarationError.node_id`, and the engine translator keeps all of them private. The one remaining leak is in the seam (A-WR-01).
- **Rendered report.** `render_markdown()` output is byte-identical to the committed PARITY-EVIDENCE.md.
- **Tests.** Lane A ran `pytest tests/seam tests/evidence tests/identity -m "not live"`: 1073 passed. Lane B did not run tests: the edit-guard hook blocks `pytest` on `tests/runner`, `tests/validator` and `tests/parts` because they contain protected files, so lane B's claims rest on standalone probe scripts against the real modules.

There are no blockers. The eight warnings fall into four groups:

1. **Errors that should be named refusals reach the consumer as an unstructured 500** (A-WR-02, A-WR-03, B-WR-01, B-WR-02). The phase goal says the wiring layer never produces an unstructured 500. Malformed `items`, a broken `dist-info`, malformed `provides`/`evidence_position` and malformed guard declarations still raise bare `TypeError`/`AttributeError`.
2. **A guard signal missing at run time** reads as an ordinary partial 200 instead of a D-19 refusal (B-WR-04), and on that path the spend already metered is thrown away (B-WR-03).
3. **Part name in a refusal.** A refusal that Phase 13 made reachable on a new path still exposes a part `name@version` (A-WR-01).
4. **Stale API inventory.** API-INVENTORY.md still states, as current behaviour, the defects Phase 13 removed, and the GUI consumers regenerate their fixtures from it (A-WR-04).

**Merge notes.** No two lane findings describe the same defect, so none was dropped. Four places where the lanes overlap are cross-referenced instead of merged:

- Lane A's summary said a missing guard signal "becomes a node failure, so it is never mislabelled as a pre-dispatch refusal". Lane B-WR-04 describes the same behaviour and classifies it as a D-19 defect. This report keeps B-WR-04's classification.
- A-WR-03 and B-WR-02 both escape the same narrow catch list in engine `_run_wiring` (`engine.py:662-683`), from different sources.
- B-WR-01 and A-IN-03 are both WIRE-06 malformed-document gaps: B-WR-01 in `parse_wiring`, A-IN-03 in the engine injectors that run before it.
- A-IN-01 and B-IN-01 both concern D-26 `cancelled` handling: A-IN-01 in the SeamEvent mapping, B-IN-01 in the scheduler's missing cause.

## Narrative Findings (AI reviewer)

## Warnings

### A-WR-01: MutableStoreComparisonExcludedError puts a part `name@version` in a public field and in the message, on a path Phase 13 widened

**File:** `databasise/seam/refusals.py:497-503`, `databasise/seam/engine.py:1107-1120`, `databasise/seam/engine.py:1259-1264`

**Issue:** `_mutates_store_component` returns `part.name_at_version`. The refusal stores it on the public attribute `component` and also interpolates it into `str(exc)`. `refusal_body` exports both `vars(exc)` and the message.

D-15 removed `name@version` from `SeamEvent.component` for exactly this reason: CONTRACT.md:630 and §18.3 say no modality-named part may appear in a consumer field. This refusal is the remaining place that carries one. Phase 13 (D-11) also moved the one-selector compare branch below the mutates_store check, so a plain `compare([selector])` now reaches this refusal.

**Failure scenario:** LEDG-12, which D-11 cites, makes a mutates_store wiring selectable. Then `POST /compare {"selectors":[{"alias":"cbm"}]}` returns 422 with `{"component": "codebase-memory-mcp/...@x.y.z", "message": "... component 'codebase-memory-mcp/...' ..."}`. That names the fitted modality's part, which §18.3's invariance rule forbids. Today the refusal is reachable only through the test-only candidate pool, but the field shape is already part of the public contract.

**Fix:** Name the capability instead of the part, the same way D-15 fixed SeamEvent. Keep the part name private for the server log:

```python
class MutableStoreComparisonExcludedError(SeamRefusalError):
    def __init__(self, *, component: str) -> None:
        self.capability = "mutates_store"
        self._component = component  # private: a part name_at_version names the modality
        super().__init__(
            "MutableStoreComparisonExcludedError: a selected wiring declares mutates_store and is "
            "excluded from §5 parity/determinism comparisons"
        )
```

The docstring must keep "unreachable", because protected SEAM-16 checks for it. API-INVENTORY.md section 3.1.3 item 3 would need the same update.

### A-WR-02: The D-09 evidence guard covers only a missing `items` key; `items: None`, a non-list value or a non-dict item still gives an unstructured 500

**File:** `databasise/seam/engine.py:2174-2184` (with `databasise/seam/evidence.py:110-111`)

**Issue:** The new guard raises `MalformedEvidenceItemError` only when `"items" not in retrieval_output`.

- `{"items": None}` reaches `mint_evidence_refs(None)` and raises `TypeError` from `enumerate(None)`.
- `{"items": [ "chunk-1" ]}` raises `AttributeError` from `item.get("id")`.
- `{"items": {"id": ...}}` iterates over the dict's keys and fails the same way.

None of these exceptions is a `MalformedEvidenceItemError`, so none is mapped to `MalformedDriverOutput`. The phase goal says consumers never see an unstructured 500 from the wiring layer, and D-09 names this exact site. Since D-02, the KG arms read evidence from `assemble`, a second producer of `items`, so a part regression is now more likely to surface here.

**Failure scenario:** The assemble part returns `{"items": None}` when it selects no chunks, for example after a refactor of assemble.py:161. Every local, global and hybrid query then returns HTTP 500 "Internal Server Error". The run is still persisted, but the consumer never receives its `trace_token`, because the exception is not a `SeamRefusalError`.

**Fix:** Validate the shape, not just the key, inside the same try:

```python
if isinstance(retrieval_output, dict):
    items = retrieval_output.get("items", _MISSING)
    if not isinstance(items, list):
        raise MalformedEvidenceItemError(namespace=evidence_namespace, index=0, reason="carries no 'items' list")
    for index, item in enumerate(items):
        if not isinstance(item, Mapping):
            raise MalformedEvidenceItemError(namespace=evidence_namespace, index=index, reason="is not a mapping")
    retrieval_items = items
else:
    retrieval_items = []
```

An alternative is to add the per-item `Mapping` check to `mint_evidence_refs` itself.

### A-WR-03: The environment-digest handling (D-16, D-22) only catches `EnvironmentDigestError`; a broken `dist-info` raises `TypeError`, which breaks `health()` and gives every run a 500

**File:** `databasise/seam/engine.py:2018-2025`, `databasise/seam/engine.py:681-682`, `databasise/identity/env.py:74-80`

**Issue:** `_collect_environment_payload` raises `EnvironmentDigestError` for one case only: a Nix store path in a collected value. Any other failure while collecting escapes as a bare exception. Examples:

- An empty or truncated `*.dist-info` directory: `dist.version` is `None`, so `"/nix/store/" in None` raises `TypeError`.
- A RECORD file that is not UTF-8 raises `UnicodeDecodeError`.

`health()` catches only `EnvironmentDigestError`, so the exception propagates out of `health()`. Its docstring says it never raises for a faulty participant. `_run_wiring` also catches only `EnvironmentDigestError`, so query, ingest and delete fail with an unmapped exception instead of the D-22 503 `EnvironmentDigestUnavailable`.

**Verified by probe:** An empty `broken-1.0.dist-info/` on `PYTHONPATH`, then `environment_hash()`. It raised `TypeError: argument of type 'NoneType' is not iterable`, and `isinstance(e, EnvironmentDigestError)` was `False`.

**Failure scenario:** A `pip install` into the venv is interrupted and leaves an empty dist-info directory. After that, `GET /health` returns 500 instead of `degraded`, and every `/query`, `/documents` and `DELETE` returns 500. That is the failure D-16 and D-22 were meant to make legible.

**Fix:** Wrap collection failures in the named error once, at the source. Then both catch sites work unchanged:

```python
@functools.cache
def environment_hash() -> str:
    try:
        payload = _collect_environment_payload()
    except EnvironmentDigestError:
        raise
    except Exception as exc:  # any unreadable distribution makes the identity uncomputable
        raise EnvironmentDigestError(f"environment digest could not be collected: {type(exc).__name__}") from exc
    return hashlib.sha256(canonicalise(payload)).hexdigest()
```

Alternatively, make `_assert_no_nix_store_path` and the row builder handle `None` values. The `functools.cache` still memoises success only.

**Related:** B-WR-02 escapes the same `_run_wiring` catch list from the guard pre-flight.

### A-WR-04: API-INVENTORY.md still describes the pre-Phase-13 consumer contract in many sections

**File:** `docs/gui/API-INVENTORY.md:119, 126, 129-130, 134, 160, 166, 173, 175, 300, 321, 667, 774, 821`

**Issue:** The Phase 13 edits (13-13) updated SeamEvent, the compare order, HippoRAG delete and one UnbudgetableParticipant row. Many statements that Phase 13 made false were left in place:

- **:119, :129-130, :134, :321, :774, :821.** These say `stop_reason` and `degradation_reason` carry `node '<node_id>': ...` free text and that "no response-time leak gate exists". D-05 and D-23 made both fields closed codes and added `node_free_reason` at response time.
- **:126.** This says `depth_label` "defaults to `stage`" and is "typed as a free `str`". D-06 made it `Depth | None`, `null` when no provides node answered.
- **:160, :300.** These say a run that raised after dispatch "persists none". D-04 now persists the run and puts `trace_token` on the refusal.
- **:166.** This says the engine "discards `debug`". D-09 removed the keyword. The quoted signature `Databasise.query(query_object, selector=None, *, debug=False)` no longer exists.
- **:173.** This lists the cyclic wiring (`RuntimeError`), two answering provides nodes (`RuntimeError`) and the bare `KeyError` for a dict without `items` as 500s. They are now 422 `UnparseableWiringError` (`cyclic-wiring`), 422 `AmbiguousAnswerPositionError` and 502 `MalformedDriverOutput`.
- **:175, :667.** The live checks still expect `stop_reason` "naming node `embedder-query`/`generate`/`fact-score`" and `depth_label: "stage"` on a partial run.

The new refusals `InvalidNodeSettingError {setting}`, `InvalidGuardDeclarationError`, `AmbiguousAnswerPositionError` and the 503 `EnvironmentDigestUnavailable` are not listed anywhere. The CONTEXT out-of-scope note says the console and tool consumers (TOOL-09, CONN-03/05, GUI-04/05/07) regenerate fixtures from these rules.

**Failure scenario:** A GUI built from this inventory parses node ids out of `stop_reason`, as line 134 tells it to show the text verbatim and "not parse". It renders `depth_label` as a required string and crashes or mislabels on `null`. It treats a post-dispatch refusal as having no trace link, although `trace_token` is now in the body. It shows "500" states for paths that are now named 422 or 502 refusals.

**Fix:** Rewrite each row cited above to the Phase 13 behaviour, and add the four refusals to the `/query`, `/compare` and corpus refusal lists. Section 3.0 should state that `trace_token` appears on post-dispatch query refusals. Mark lines 774 and 821 (open question 13) as resolved by D-05.

### B-WR-01: `parse_wiring` still raises on malformed `provides` / `evidence_position` (WIRE-06 "reports, never raises")

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

**Related:** A-IN-03 covers the same WIRE-06 hardening gap in the engine injectors that run before `parse_wiring`.

### B-WR-02: Guard pre-flight raises a bare `TypeError` that the engine does not translate (WIRE-05 / D-07)

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

**Related:** A-WR-03 escapes the same `_run_wiring` catch list from the environment digest.

### B-WR-03: A post-dispatch failure discards spend that was already metered

**File:** `databasise/runner/scheduler.py:653-686` (`_stopped_trace` at `:599-616`)
**Issue:** The post-dispatch `except Exception` builds the failed trace through `_stopped_trace`, which always writes `spent=None` and `tokens=TokenAccounting()`. By that point `_body_report` and `meter()` may already have run (`:663-664`). Only `evaluate_guards` or the `NodeTrace` construction raised.
**Failure scenario:**
- A `calls_llm` node, such as HippoRAG `fact-filter`, completes a real LLM call and returns `tokens`.
- Its guard evaluation then raises because the signal key is missing (B-WR-04).
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

### B-WR-04: A guard signal missing at run time becomes a generic `node_failed` partial 200, not a refusal (D-19)

**File:** `databasise/runner/guards.py:110-118`, `databasise/runner/scheduler.py:665, 680-686`
**Issue:** D-19 says "A missing evaluating node or missing key is a refusal, never a fire." `evaluate_guards` raises `GuardDeclarationError`, but `_dispatch_node`'s catch-all records it as an ordinary node failure with `REASON_NODE_FAILED`. The engine inspects `node_exceptions` only for store faults (`engine.py:2145-2150`). The consumer therefore gets a 200 envelope with `partial=true`, `stop_reason="node_failed"` and no answer, which looks the same as a transient part crash. The pre-flight path for the same class of defect is a named 422 (`InvalidGuardDeclarationError`).
Probe: a passthrough node guarded on signal `"s"` that it never emits -> `partial=True, stop_reason='node_failed'`, with the exception in `node_exceptions`.
**Failure scenario:** A part refactor drops `guard_fired` from fact-filter's output, the inverse of the `_GuardAwareResult` removal in this phase. Every HippoRAG query then returns a degraded 200 with a null answer instead of a wiring-contract refusal. Consumers and the ledger read this as a flaky modality, not a misdeclared wiring.
**Fix:** In the engine's post-persist block, map a `GuardDeclarationError` found in `scheduled["node_exceptions"]` to `InvalidGuardDeclarationError` (it already carries `trace_token` per D-04). The alternative is to amend D-19's text to say this case is recorded as `node_failed` by design.

**Note:** Lane A's summary recorded the same scheduler behaviour (scheduler.py:677) as correct, on the grounds that it is never mislabelled as a pre-dispatch refusal. Against D-19's wording the behaviour is a defect, so this report keeps the Warning.

## Info

### A-IN-01: A cancelled mutating node is reported as SeamEvent outcome `failed`, and the `getattr` default is dead code

**File:** `databasise/seam/engine.py:1043-1047`

**Issue:** The `status != "completed"` test also catches `status == "cancelled"`. The D-26 case is a body that raised `CancelledError`, with budget `within_budget` and no cause, and it is reported as `failed`. The envelope comment and D-15 define `failed` as "a mutating node whose execution raised". Also, `NodeTrace.status` always exists (trace.py:116), so `getattr(node_trace, "status", "completed")` is just `node_trace.status`.

**Fix:** Either document that `cancelled` maps to `failed`, or test `node_trace.status == "failed" or node_trace.cross_process_failure_cause is not None`. Use the attribute directly. Related: B-IN-01 (the same D-26 path records no cause).

### A-IN-02: The `"cycle"` branch of `_node_result_or_refuse` is now dead code

**File:** `databasise/seam/engine.py:935-940`

**Issue:** Every seam path calls `_refuse_unparseable` before `_run_wiring`: lines 1377, 1574, 1638, 1722 and 2084. `_refuse_unparseable` now refuses cycles with a 422. The scheduler's `{"cycle": ...}` return can therefore never reach `_node_result_or_refuse`. Its docstring step 1 still describes a `RunIncomplete` 502 for cycles, which contradicts D-07's statement that cycles moved from 502 to 422.

**Fix:** Delete the branch and docstring step 1, or turn it into an assertion.

### A-IN-03: The WIRE-06 malformed-document hardening is applied unevenly in the injectors

**File:** `databasise/seam/engine.py:505-510`, `databasise/seam/engine.py:530-537`

**Issue:** `_inject_query` still calls `nodes[node_id].get(...)` on whatever value the node has, so `{"nodes": {"a": 1}, "consumes_query": ["a"]}` raises `AttributeError`. A non-list `consumes_query`, such as a string, is iterated character by character. `_inject_corpus_token_allowance` uses `resolved.get("nodes", {}).values()` and does not use `_node_dicts`. Both failures happen before `parse_wiring` can report the defect. This is not reachable from consumer input today, because every resolved wiring comes from committed files.

**Fix:** In `_inject_query`, skip a node that is not a dict and a `consumes_query` that is not a list. Use `_node_dicts` in `_inject_corpus_token_allowance`. Related: B-WR-01 (the same gap inside `parse_wiring`).

### A-IN-04: Retry refusals are labelled `operation: "ingest"`

**File:** `databasise/seam/engine.py:1484-1496`

**Issue:** `retry_document` runs through `_run_corpus_ingest`, which hard-codes `"ingest"` for `_run_wiring` and `_node_result_or_refuse`. A retry that fails with `EnvironmentDigestUnavailable` or a node fault therefore reports `{operation: "ingest"}`. The `NoWritePathForModalityError` refusal on the same route reports `{operation: "retry"}`.

**Fix:** Pass the operation name into `_run_corpus_ingest`.

### A-IN-05: The OpenAPI 503 description leaves out the new failure class

**File:** `databasise/seam/rest.py:175-178`

**Issue:** The `_FAULT_RESPONSES[503]` description still reads "the v1 engine is unavailable (missing interpreter or timeout)". It does not cover `V1NotConfigured` or the new `EnvironmentDigestUnavailable`.

**Fix:** Widen the text to "the engine is unavailable (v1 interpreter, timeout or configuration, or the environment digest cannot be computed)".

### A-IN-06: The derived schema and the deviation record describe `status` inaccurately

**File:** `databasise/evidence/rig-trace.databasise.schema.json:92`, `databasise/evidence/RIG-TRACE-DEVIATIONS.md` (rows D5, D9)

**Issue:** The `status` description says a node was "cancelled with its batch". Under D-17's sequential dispatch, D-26 redefines `cancelled` as a body that raised `CancelledError` while the run itself was not being cancelled (scheduler.py:641-650). Rows D5 and D9 give the forcing decision as D-14, but the per-node status is D-13 (WIRE-10).

**Fix:** Correct the description to match D-26, and cite D-13 in rows D5 and D9. The test that rebuilds the derived file from the amendment list must stay in step with the edit.

### A-IN-07: A pre-dispatch refusal during ingest leaves an orphan job row

**File:** `databasise/seam/engine.py:1466-1491`

**Issue:** `self._record_job(track_id, ...)` runs before `_run_wiring`. If `_run_wiring` then refuses before any node starts, the job row stays in the job store although v1 never saw the track id. The refusal can be the new `InvalidNodeSettingError`, `InvalidGuardDeclarationError` or `EnvironmentDigestUnavailable`. The `/jobs` route then lists a job that cannot progress. This predates Phase 13 for a raw 500, but Phase 13 now presents it as a clean, named 422 or 503.

**Fix:** Record the job after pre-flight succeeds, or remove the row in the `except` path when the refusal is one of the pre-dispatch classes.

### A-IN-08: The parity report always says the pinned hashes predate Phase 13, and refusal bodies differ in whether they have `trace_token`

**File:** `databasise/evidence/parity_report.py:1381-1387`, `databasise/seam/engine.py:2206-2209`

**Issue:**

- **Fixed paragraph.** The "Pinned hashes" paragraph is a fixed string rendered on every run. Once any comparison result is re-minted after Phase 13, the paragraph becomes false for that result, and nothing ties the text to the data.
- **Optional key.** `trace_token` is added only to post-dispatch query refusals. Elsewhere the attribute is absent, not `null`, so one refusal class (for example `ForeignEngineRefusalError` with `StoreFault`) has different key sets on `/query` and on `/documents`. Clients that use a strict schema must treat the key as optional.

**Fix:** For the report, derive the note from a minted-before marker or date in each result file. For the refusals, document `trace_token` as optional on `RefusalBody`, or set it to `None` on the base class.

### B-IN-01: A cancelled node leaves no cause in the trace or in `node_exceptions`

**File:** `databasise/runner/scheduler.py:642-651`
**Issue:** The D-26 path returns `_NodeOutcome(trace, False, None, REASON_CANCELLED)` with `cause=None`. Even `debug=True` cannot show which body raised `CancelledError` or why. A probe confirmed that `node_exceptions == {}`.
**Fix:** Pass `"CancelledError: node body raised CancelledError outside run cancellation"` as the cause. Related: A-IN-01 (the seam maps this same `cancelled` status to `failed`).

### B-IN-02: `run_wiring` echoes any `concurrency_setting` while always running sequentially

**File:** `databasise/runner/scheduler.py:695-696, 843-844`
**Issue:** D-17 makes `sequential` true by construction, but the value passed in is echoed back unvalidated. The public `databasise.run_wiring` (`__init__.py:87`) forwards a caller value, so `"parallel"` would be recorded for a run that executed sequentially, which falsifies the A/A key the echo exists to protect.
**Fix:** Refuse any value other than `"sequential"`, or ignore the argument and always echo `"sequential"`.

### B-IN-03: Stale `InvalidMaxConcurrencyError` docstring

**File:** `databasise/runner/scheduler.py:210-213`
**Issue:** The docstring still says "a value `int()` cannot coerce". Since D-07 no value is coerced: a float or a bool is refused too. `InvalidTokenAllowanceError` (`:224-228`) has the same wording.
**Fix:** Change it to "any value that is not a true `int` (bools, floats and strings are never coerced)".

### B-IN-04: The unpatched LightRAG base shares `wiring_id` with the naive arm and carries no `arm_id`

**File:** `databasise/wirings/lightrag/base.json` (top level), `databasise/wirings/lightrag/arm-naive.json-patch.json:6`
**Issue:**
- naive keeps `wiring_id: "lightrag-base"` (D-03). The 17-node base itself also has that id, and it has no `arm_id`.
- Any path that runs `load_base()` directly, such as the parity or storage-audit harnesses, records `arm_id="seam"` (`engine.py:2123` fallback) under the same `wiring_id` as naive, with a different node set.
- Promotion matches traces on node sets, so this is not a live bug, but `wiring_id` alone does not identify the arm.

**Fix:** Either give the base its own id, such as `lightrag-full`, with naive's patch setting `lightrag-base`, or record in `resolve.py` that the raw base is never a run identity.

### B-IN-05: `evaluate_guards` does not require the signal value to be a boolean

**File:** `databasise/runner/guards.py:117`
**Issue:** D-19 defines `signal` as "the boolean output key", but the comparison is a plain `!=`. A part that emits `"guard_fired": None`, or a string, fires the guard (`None != False`) and marks the run degraded with `fallback_path_taken`.
**Fix:** Raise `GuardDeclarationError` when `not isinstance(output[guard.signal], bool)`.

### B-IN-06: KG-arm evidence has `score: null` on every item

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
