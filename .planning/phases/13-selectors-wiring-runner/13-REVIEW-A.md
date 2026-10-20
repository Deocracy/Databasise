---
phase: 13-selectors-wiring-runner
lane: A
reviewed: 2026-10-20T00:00:00Z
depth: deep
diff_base: b0b5a6c
files_reviewed: 18
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
findings:
  critical: 0
  warning: 4
  info: 8
  total: 12
status: issues_found
---

# Phase 13: Code Review Report (Lane A)

**Reviewed:** 2026-10-20
**Depth:** deep (call chains traced into runner/scheduler.py, runner/guards.py, runner/trace.py, parts/registry.py, wirings/resolve.py, identity/canon.py, mcp/server.py)
**Files Reviewed:** 18 (seam/compare.py, corpus.py and tokens.py are unchanged since b0b5a6c; they were read only as callers)
**Status:** issues_found

## Summary

Lane A covers the seam layer, environment identity, the derived trace schema and its deviation record, the parity report and the GUI API inventory. The main Phase 13 mechanisms work as the decisions describe. I checked each one against the source and with probes:

- **Capability resolution (D-01).** A probe of `resolve_selector` returned exactly the mapping in the docstring: reads_vector and reads_vector:chunks give naive; calls_llm gives bypass; reads_vector:entities gives local; reads_vector:relationships gives global; both namespace tokens give hybrid; reads_graph, alone or with reads_kv or calls_llm, gives hipporag; reads_graph with calls_rerank gives local; writes_graph is refused.
- **Node counts.** The one-node margin is correct: naive 7, local 15, global 15, hipporag 14.
- **Reason codes.** No node id, arm id or wiring id is a substring of any of the six closed reason codes, so the new substring check in `assert_no_forbidden_values` cannot fire on a legitimate code.
- **Runner pre-flight errors.** All of them are translated by `_run_wiring`. A guard signal missing at evaluation time is caught by the scheduler's post-dispatch handler (scheduler.py:677) and becomes a node failure, so it is never mislabelled as a pre-dispatch refusal.
- **Persisting before refusals (D-04).** The RunRecord is persisted before any post-dispatch refusal. `refusal_body` exports `trace_token` on both REST and MCP.
- **Rendered report.** `render_markdown()` output is byte-identical to the committed PARITY-EVIDENCE.md.
- **Tests.** `pytest tests/seam tests/evidence tests/identity -m "not live"`: 1073 passed.

There are no blockers. The four warnings are:

1. **Part name in a refusal.** A refusal that Phase 13 made reachable on a new path still exposes a part `name@version`.
2. **Unstructured 500 on malformed `items`.** The D-09 evidence guard covers only a missing `items` key. Other malformed shapes still produce an unstructured 500.
3. **Narrow digest catch.** The D-16 and D-22 handling only catches `EnvironmentDigestError`. A probe showed that an ordinary broken `dist-info` directory raises a bare `TypeError` instead. That error then breaks `health()` and every run.
4. **Stale API inventory.** API-INVENTORY.md still states, as current behaviour, the exact defects Phase 13 removed. The GUI consumers regenerate their fixtures from that document.

## Warnings

### WR-01: MutableStoreComparisonExcludedError puts a part `name@version` in a public field and in the message, on a path Phase 13 widened

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

### WR-02: The D-09 evidence guard covers only a missing `items` key; `items: None`, a non-list value or a non-dict item still gives an unstructured 500

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

### WR-03: The environment-digest handling (D-16, D-22) only catches `EnvironmentDigestError`; a broken `dist-info` raises `TypeError`, which breaks `health()` and gives every run a 500

**File:** `databasise/seam/engine.py:2018-2025`, `databasise/seam/engine.py:681-682`, `databasise/identity/env.py:74-80`

**Issue:** `_collect_environment_payload` raises `EnvironmentDigestError` for one case only: a Nix store path in a collected value. Any other failure while collecting escapes as a bare exception. Examples:

- An empty or truncated `*.dist-info` directory: `dist.version` is `None`, so `"/nix/store/" in None` raises `TypeError`.
- A RECORD file that is not UTF-8 raises `UnicodeDecodeError`.

`health()` catches only `EnvironmentDigestError`, so the exception propagates out of `health()`. Its docstring says it never raises for a faulty participant. `_run_wiring` also catches only `EnvironmentDigestError`, so query, ingest and delete fail with an unmapped exception instead of the D-22 503 `EnvironmentDigestUnavailable`.

**Verified by probe:** I put an empty `broken-1.0.dist-info/` on `PYTHONPATH` and called `environment_hash()`. It raised `TypeError: argument of type 'NoneType' is not iterable`, and `isinstance(e, EnvironmentDigestError)` was `False`.

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

### WR-04: API-INVENTORY.md still describes the pre-Phase-13 consumer contract in many sections

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

## Info

### IN-01: A cancelled mutating node is reported as SeamEvent outcome `failed`, and the `getattr` default is dead code

**File:** `databasise/seam/engine.py:1043-1047`

**Issue:** The `status != "completed"` test also catches `status == "cancelled"`. The D-26 case is a body that raised `CancelledError`, with budget `within_budget` and no cause, and it is reported as `failed`. The envelope comment and D-15 define `failed` as "a mutating node whose execution raised". Also, `NodeTrace.status` always exists (trace.py:116), so `getattr(node_trace, "status", "completed")` is just `node_trace.status`.

**Fix:** Either document that `cancelled` maps to `failed`, or test `node_trace.status == "failed" or node_trace.cross_process_failure_cause is not None`. Use the attribute directly.

### IN-02: The `"cycle"` branch of `_node_result_or_refuse` is now dead code

**File:** `databasise/seam/engine.py:935-940`

**Issue:** Every seam path calls `_refuse_unparseable` before `_run_wiring`: lines 1377, 1574, 1638, 1722 and 2084. `_refuse_unparseable` now refuses cycles with a 422. The scheduler's `{"cycle": ...}` return can therefore never reach `_node_result_or_refuse`. Its docstring step 1 still describes a `RunIncomplete` 502 for cycles, which contradicts D-07's statement that cycles moved from 502 to 422.

**Fix:** Delete the branch and docstring step 1, or turn it into an assertion.

### IN-03: The WIRE-06 malformed-document hardening is applied unevenly in the injectors

**File:** `databasise/seam/engine.py:505-510`, `databasise/seam/engine.py:530-537`

**Issue:** `_inject_query` still calls `nodes[node_id].get(...)` on whatever value the node has, so `{"nodes": {"a": 1}, "consumes_query": ["a"]}` raises `AttributeError`. A non-list `consumes_query`, such as a string, is iterated character by character. `_inject_corpus_token_allowance` uses `resolved.get("nodes", {}).values()` and does not use `_node_dicts`. Both failures happen before `parse_wiring` can report the defect. This is not reachable from consumer input today, because every resolved wiring comes from committed files.

**Fix:** In `_inject_query`, skip a node that is not a dict and a `consumes_query` that is not a list. Use `_node_dicts` in `_inject_corpus_token_allowance`.

### IN-04: Retry refusals are labelled `operation: "ingest"`

**File:** `databasise/seam/engine.py:1484-1496`

**Issue:** `retry_document` runs through `_run_corpus_ingest`, which hard-codes `"ingest"` for `_run_wiring` and `_node_result_or_refuse`. A retry that fails with `EnvironmentDigestUnavailable` or a node fault therefore reports `{operation: "ingest"}`. The `NoWritePathForModalityError` refusal on the same route reports `{operation: "retry"}`.

**Fix:** Pass the operation name into `_run_corpus_ingest`.

### IN-05: The OpenAPI 503 description leaves out the new failure class

**File:** `databasise/seam/rest.py:175-178`

**Issue:** The `_FAULT_RESPONSES[503]` description still reads "the v1 engine is unavailable (missing interpreter or timeout)". It does not cover `V1NotConfigured` or the new `EnvironmentDigestUnavailable`.

**Fix:** Widen the text to "the engine is unavailable (v1 interpreter, timeout or configuration, or the environment digest cannot be computed)".

### IN-06: The derived schema and the deviation record describe `status` inaccurately

**File:** `databasise/evidence/rig-trace.databasise.schema.json:92`, `databasise/evidence/RIG-TRACE-DEVIATIONS.md` (rows D5, D9)

**Issue:** The `status` description says a node was "cancelled with its batch". Under D-17's sequential dispatch, D-26 redefines `cancelled` as a body that raised `CancelledError` while the run itself was not being cancelled (scheduler.py:641-650). Rows D5 and D9 give the forcing decision as D-14, but the per-node status is D-13 (WIRE-10).

**Fix:** Correct the description to match D-26, and cite D-13 in rows D5 and D9. The test that rebuilds the derived file from the amendment list must stay in step with the edit.

### IN-07: A pre-dispatch refusal during ingest leaves an orphan job row

**File:** `databasise/seam/engine.py:1466-1491`

**Issue:** `self._record_job(track_id, ...)` runs before `_run_wiring`. If `_run_wiring` then refuses before any node starts, the job row stays in the job store although v1 never saw the track id. The refusal can be the new `InvalidNodeSettingError`, `InvalidGuardDeclarationError` or `EnvironmentDigestUnavailable`. The `/jobs` route then lists a job that cannot progress. This predates Phase 13 for a raw 500, but Phase 13 now presents it as a clean, named 422 or 503.

**Fix:** Record the job after pre-flight succeeds, or remove the row in the `except` path when the refusal is one of the pre-dispatch classes.

### IN-08: The parity report always says the pinned hashes predate Phase 13, and refusal bodies differ in whether they have `trace_token`

**File:** `databasise/evidence/parity_report.py:1381-1387`, `databasise/seam/engine.py:2206-2209`

**Issue:**

- **Fixed paragraph.** The "Pinned hashes" paragraph is a fixed string rendered on every run. Once any comparison result is re-minted after Phase 13, the paragraph becomes false for that result, and nothing ties the text to the data.
- **Optional key.** `trace_token` is added only to post-dispatch query refusals. Elsewhere the attribute is absent, not `null`, so one refusal class (for example `ForeignEngineRefusalError` with `StoreFault`) has different key sets on `/query` and on `/documents`. Clients that use a strict schema must treat the key as optional.

**Fix:** For the report, derive the note from a minted-before marker or date in each result file. For the refusals, document `trace_token` as optional on `RefusalBody`, or set it to `None` on the base class.

---

_Reviewed: 2026-10-20_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
