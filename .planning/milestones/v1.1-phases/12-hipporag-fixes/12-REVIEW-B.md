---
phase: 12-hipporag-fixes
lane: B
reviewed: 2026-10-19T00:00:00Z
depth: deep
files_reviewed: 27
files_reviewed_list:
  - databasise/foreign/v1_corpus_adapter.py
  - databasise/mcp/server.py
  - databasise/mcp/tools.py
  - databasise/runner/scheduler.py
  - databasise/runner/trace.py
  - databasise/seam/engine.py
  - databasise/seam/refusals.py
  - databasise/seam/rest.py
  - databasise/seam/selectors.py
  - databasise/seam/tokens.py
  - databasise/stores/probes.py
  - databasise/stores/vector.py
  - databasise/wirings/resolve.py
  - databasise/tests/foreign/test_secret_redaction.py
  - databasise/tests/runner/test_degraded_on_guard.py
  - databasise/tests/runner/test_token_sum.py
  - databasise/tests/seam/test_compare.py
  - databasise/tests/seam/test_cross_modality_run.py
  - databasise/tests/seam/test_extraction_failed_refusal.py
  - databasise/tests/seam/test_foreign_engine_refusal.py
  - databasise/tests/seam/test_hipporag_corpus_surface.py
  - databasise/tests/seam/test_hipporag_query_path.py
  - databasise/tests/seam/test_hipporag_write_gate.py
  - databasise/tests/seam/test_hipporag_write_path.py
  - databasise/tests/stores/test_kv_readonly_listing.py
  - databasise/tests/stores/test_vector_self_knn_pending.py
  - databasise/tests/wirings/test_query_run_pruning.py
findings:
  critical: 1
  warning: 4
  info: 6
  total: 11
status: issues_found
---

# Phase 12: Code Review Report (Lane B)

**Reviewed:** 2026-10-19
**Depth:** deep
**Files Reviewed:** 27
**Status:** issues_found

## Summary

Lane B covers the seam/engine, runner, stores and wiring-resolution changes of Phase 12, plus their tests. I followed the call chains into lane A where needed: `parts_core/hipporag/document_remover.py`, `openie.py`, `fact_filter.py`, `seam/promotion.py`, `runner/guards.py` and `parity/build_hipporag_index.py`. The D-08, D-09, D-11, D-13, D-14, D-16 and D-21 mechanics are implemented as decided. The 75 non-protected lane tests pass (`.venv/bin/pytest -q` on the ten non-protected files). I did not run the protected files because of the BAK guard.

The critical finding is that a HippoRAG delete removes LightRAG's staged uploads from the shared workspace inbox, and it does so without holding the v1 gate. A scratch probe confirmed it: a HippoRAG `delete_document("report")` that returns `not_found` still unlinked `corpus-inbox/report.pdf` and `corpus-inbox/__parsed__/report.pdf`. The warnings cover:
- the new HippoRAG corpus listing path, which can return a bare 500 on a bad manifest and can silently under-report;
- a promotion `AssertionError` (500) on traces persisted before Phase 12;
- test assertions that pass without checking anything.

## Critical Issues

### B-CR-01: A HippoRAG delete removes LightRAG's kept and in-flight uploads from the shared inbox

**File:** `databasise/seam/engine.py:1700-1701`
**Issue:** After a HippoRAG `delete_document` reports `success` or `not_found`, it calls `self._remove_inbox_files(document_id)`. That function unlinks every `<id>.*` file in `<store_root>/<workspace>/corpus-inbox/` and its `__parsed__/`. The inbox is v1's `INPUT_DIR` (`_inbox()`, line 1087), and only LightRAG stages files there; HippoRAG refuses raw uploads (`NoRawUploadPathForModalityError`). So for HippoRAG the call can only destroy another modality's data:
- **Lost retry source.** A LightRAG upload kept after a v1 timeout, subprocess failure or malformed output (`_KEEP_STAGED`) is deleted. `retry_document` needs that file ("a retry needs the source").
- **Race with a running LightRAG ingest.** D-12 removed the v1 gate from the HippoRAG delete path (line 1668). So the unlink can also hit a file that a concurrent LightRAG ingest of the same id has just exclusive-created and that v1 is reading.

Using the same document id in both modalities is the project's core use case ("the same corpus, N modalities side-by-side"). It also breaks D-12's rule that a HippoRAG delete never touches v1 state.

Probe result: a HippoRAG delete for `report` returned `not_found`, and the kept upload and its parsed copy were both gone afterwards.

**Fix:**
```python
            if family == "lightrag" and result.get("status") in ("success", "not_found"):
                self._remove_inbox_files(document_id)
```
Add a test: stage `corpus-inbox/<id>.pdf`, run a HippoRAG-selected delete, and assert the file still exists.

## Warnings

### B-WR-01: The HippoRAG corpus listing turns an undecodable or non-dict manifest into a bare 500

**File:** `databasise/seam/engine.py:1774-1795`, `databasise/stores/probes.py:160`
**Issue:** `_hipporag_manifests` catches only `sqlite3.Error`. Three other failures escape:
- `list_kv_prefix` returns `json.loads(value)` unchecked, so a `doc:` row that is not valid JSON raises `JSONDecodeError`.
- A row that decodes to a non-dict makes `manifest.get(...)` raise `AttributeError`.
- `db_path.stat()` can raise `OSError` (for example `PermissionError`).

All three reach FastAPI and MCP as unhandled exceptions. The v1 read routes in this module follow the 09 REVIEW WR-01 / SEAM-06 rule that a read route never answers with a bare 500: they map `_MALFORMED_RESULT` to `MalformedDriverOutput` and `OSError` to `StoreFault`. The new HippoRAG branch of `/corpus` and `/corpus/counts` (and MCP `status`) breaks that rule.
**Fix:** In `_hipporag_manifests`, catch `OSError` as `StoreFault` and `_MALFORMED_RESULT` (`TypeError`, `ValueError`, `AttributeError`, `KeyError`) as `StoreCorrupted` or `MalformedDriverOutput`. Also validate `isinstance(manifest, dict)` before calling `.get`.

### B-WR-02: `list_kv_prefix` can silently miss committed documents, or create `-shm`, around WAL edge states

**File:** `databasise/stores/probes.py:143-145`
**Issue:** The URI is `mode=ro&immutable=1` unless both `kv.sqlite3-wal` and `kv.sqlite3-shm` exist.
- **Missed documents.** When a `-wal` with committed frames exists but `-shm` does not (a crash leftover or a copied store, the case `probe_kv`'s own comment names), the immutable connection ignores the WAL. The listing then omits manifests that are committed. `probe_kv` can accept stale WAL content because it only checks that the file opens. This function returns the document registry for D-13, so stale content here is a wrong answer.
- **Created file.** The existence check and `sqlite3.connect` are not atomic. If the last writer closes in between and SQLite deletes both files, the `mode=ro` open runs on a WAL database with no `-shm`. `probe_kv`'s comment documents that this creates `-shm`, which breaks the "read path creates nothing" claim (LRAG-13).
**Fix:** When `-wal` exists without `-shm`, refuse as `StoreBusy` or `StoreCorrupted` (or document the under-report). Re-check that `-shm` exists after connecting, and fall back to an immutable reopen if it has gone. At minimum, state in the docstring that a WAL-without-SHM store lists only checkpointed rows.

### B-WR-03: Promoting a HippoRAG trace persisted before Phase 12 raises `AssertionError` (500)

**File:** `databasise/wirings/resolve.py:148-180` (called from `databasise/seam/promotion.py:122-127`, `engine.py:2161`)
**Issue:** `_arm_name_for_node_ids` accepts either the pruned run set or the full node set. After D-16 and D-19, HippoRAG's pruned set has 7 nodes and its full set has 14. A query trace persisted before Phase 12 dispatched the old 13 nodes (no `qa`, nothing pruned), so it matches neither and raises `AssertionError`. The function documents that as an "internal invariant, never a consumer-reachable refusal", but `POST /promote` with an old trace token reaches it.

Verified: `_arm_name_for_node_ids(frozenset(full - {"qa"}))` raises `AssertionError`.

This contradicts D-16's statement that "promotion.py:122-127 still matches old full-set traces".
**Fix:** Convert the no-match case into a typed `SeamRefusalError` (a stale-trace refusal, 422). Alternatively, if old traces must stay promotable, record each wiring's prior node sets.

### B-WR-04: Several new seam tests pass without verifying what they claim

**File:** `databasise/tests/seam/test_hipporag_write_path.py:310-316, 394-399`; `databasise/tests/seam/test_hipporag_query_path.py:230-240`
**Issue:**
- **Post-delete "no evidence" checks.** Both wrap `engine.query(...)` in `except Exception` and then `assert not evidence`. Any exception satisfies the assertion, including a regression such as a `KeyError` in the pruned run, a store fault or a `TypeError`. Lines 397-398 discard the exception entirely.
- **HIPP-11 top_k test.** It asserts `len(refs) <= 5` and `all(ref.score > 0 ...)`. Both hold when no evidence is returned, and nothing checks that the second arm took the PPR branch (`guards_fired == []`). Twenty documents that returned zero evidence would pass.
**Fix:**
- Catch only the refusal the comment names (for example `pytest.raises(EmptyNamespaceError)`), or assert that `query_error is None` or is of that type.
- In the top_k test, assert `0 < len(dpr_refs) <= 5` and `0 < len(ppr_refs) <= 5`. Also assert from `resolve_trace(debug=True)` that fact-filter's `guards_fired` is `[]` for the PPR arm and non-empty for the DPR arm.

## Info

### B-IN-01: Query pruning can drop the `evidence_position` node without any signal

**File:** `databasise/wirings/resolve.py:162-174`
**Issue:** The ancestor walk starts only from `provides`. If a wiring's `evidence_position.node` is not an ancestor of `provides`, it is pruned, and `_execute_resolved` then mints an empty evidence list without any refusal. Every shipped wiring satisfies this today; the rule is not enforced.
**Fix:** Seed `frontier` with `evidence_position["node"]` as well (and possibly `consumes_query` nodes), or have the validator refuse a wiring whose evidence node is not an ancestor of `provides`.

### B-IN-02: The MCP `status` selector is silently ignored for `job` and `health`

**File:** `databasise/mcp/tools.py:181-189`, `databasise/mcp/server.py:130-146`
**Issue:** The docstring says the selector "is read only for scope in {corpus, counts}", but `job` and `health` accept and discard it. A caller who sends `{"scope": "health", "selector": ...}` expecting a per-modality answer gets the workspace-wide answer. (Selector-scoped health is deferred.)
**Fix:** Refuse a selector for `job` and `health` (for example `MissingScopeArgumentError`'s sibling), or document the behaviour in the tool description.

### B-IN-03: `sum_token_accountings` merges counts labelled `"none"` under another label

**File:** `databasise/runner/trace.py:66-80`
**Issue:** `"none"` entries are excluded from the label set but their counts are still summed. An accounting that is labelled `"none"` but carries non-zero `prompt_tokens` or `call_count` (a client bug or stub) is reported under the other counter's label. That is the mixing HIPP-19 is meant to prevent.
**Fix:** Ignore `"none"` only when its counts are all zero. Otherwise treat it as a distinct label, which yields the sentinel.

### B-IN-04: The gate-ceiling test can hang for 900 s instead of failing

**File:** `databasise/tests/seam/test_hipporag_write_gate.py:76`
**Issue:** `monkeypatch.setattr(engine_module, "_HIPPORAG_GATE_WAIT_SECONDS", 0.1, raising=False)`. If the constant is renamed, the patch silently adds an unused attribute and the test waits the real 900 s ceiling.
**Fix:** Drop `raising=False`. The attribute exists now, and the test should fail loudly if it is renamed.

### B-IN-05: The runner imports the v1 adapter module for `redact_secrets`

**File:** `databasise/runner/scheduler.py:126`
**Issue:** The modality-agnostic scheduler now depends on `databasise.foreign.v1_corpus_adapter`, which holds the v1 subprocess driver, just to get a pure regex helper. Redaction is a cross-cutting utility, and this couples the runner layer to the LightRAG foreign adapter.
**Fix:** Move `_SECRET_PATTERNS` and `redact_secrets` to a neutral module (for example `databasise/identity/redact.py` or `databasise/_redact.py`) and re-export it from the adapter.

### B-IN-06: Redaction and node-id coverage gaps

**File:** `databasise/foreign/v1_corpus_adapter.py:60-66`; `databasise/seam/engine.py:2019`
**Issue:**
- `redact_secrets` does not mask `?access_token=`, `?token=` or a bare Google `AIza...` key outside a `key=` parameter. All three appear in provider SDK error strings.
- The query-path store fault calls `_foreign_fault` without `node_id`, so its log line reads `node=-`, while the ingest and delete paths name the node (D-09). The difference is minor but makes query faults harder to trace.
**Fix:**
- Add `(?i)([?&](?:access_)?token=)[^\s'\",&]+` and `\bAIza[0-9A-Za-z_-]{20,}`.
- Pass the failing node id at line 2019 (iterate `node_exceptions.items()`).

---

_Reviewed: 2026-10-19_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
