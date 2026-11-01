---
phase: 12-hipporag-fixes
plan: 14
subsystem: seam
tags: [refusals, redaction, hipporag, logging, owner-grant]

requires:
  - phase: 12-hipporag-fixes
    provides: 12-09, 12-12, 12-13 (ExtractionFailed refusal, write-path tests, port record)
provides:
  - ForeignEngineRefusalError.node_id (private _node_id, read-only property)
  - _foreign_fault logs node=, cause=, detail= (redacted, no attached exception)
  - redact_secrets masks ?key=/&key= query values
  - cross_process_failure_cause redacted in the scheduler
  - declared fallback (stop_reason without partial) never refuses a write
affects: [phase-12 gate, ledger HIPP-03, HIPP-04, SEAM-05]

actuals:
  tokens: 14000
  tasks: 3
  commits: 4  # measured 7e9866f..HEAD; 2 are the plan's (00c4b68, ea1cbe9), 2 are orchestrator ledger commits (0d4bf62, 2bc642e)

plan_head_before: 7e9866f37541c981c0b8a7f7a9dbc80822001ee5
plan_head_after: ea1cbe9261916ed871320c3eba3477b93acb4a32

key-files:
  modified:
    - databasise/seam/refusals.py
    - databasise/seam/engine.py
    - databasise/foreign/v1_corpus_adapter.py
    - databasise/runner/scheduler.py
    - databasise/tests/seam/test_hipporag_write_path.py
    - databasise/tests/foreign/test_secret_redaction.py
    - databasise/tests/seam/test_foreign_engine_refusal.py

key-decisions:
  - "The failing node id is private (_node_id): never in str(refusal) or a transport body (D-09)"
  - "The engine fault log carries a redacted, URL-scrubbed traceback and no exc_info (D-11)"
  - "stop_reason alone never refuses a write run; only partial does (D-21)"

requirements-completed: [HIPP-04, HIPP-03]

completed: 2026-10-19
status: complete
---

# Phase 12 Plan 14: node-private refusals and redacted fault logs Summary

**A HippoRAG write refusal now names the failing node privately (chunk-embed) with its real ClientNotWiredError cause, a declared fallback can no longer refuse a write, and in-process provider errors reach the server log and debug trace with keys and URLs removed.**

## Accomplishments

- `ForeignEngineRefusalError(node_id=...)` stores `_node_id` and exposes a read-only `node_id`; `_node_result_or_refuse` passes the key of the exception it used (provides node first, else first recorded).
- `_node_result_or_refuse` refuses on `partial` only (D-21).
- `_foreign_fault` logs `operation, failure_class, node, cause (type name), detail` where detail is `_URL_RE.sub("<url>", redact_secrets(traceback))`; no exception is attached to the record.
- `redact_secrets` gains the `?key=` / `&key=` pattern; `base_url=...`, `risk-free`, `monkey=1` stay untouched.
- Scheduler applies `redact_secrets` to the text in `cross_process_failure_cause`.
- HIPP-03 row test added (passes at base, as D-10 expects).

## Task Commits

1. Task 1 (tracer): `00c4b68` fix(12-14): node-private refusal, declared fallback
2. Task 2: checkpoint:human-action, owner ran `grant-check-edit` (ledger granted_at 605)
3. Task 3: `ea1cbe9` fix(12-14): redacted fault log and trace, granted line-118 edit

## Ledger test_refs and fail-first evidence

| Row | Intended test_ref | Fail-first |
|-----|-------------------|-----------|
| HIPP-04 | `databasise/tests/seam/test_hipporag_write_path.py::test_an_ingest_with_no_embedding_client_names_chunk_embed_privately` | Pre-fix: `AssertionError: assert None == 'chunk-embed'` |
| HIPP-03 | `databasise/tests/seam/test_hipporag_write_path.py::test_an_ingest_with_no_llm_client_refuses_and_commits_nothing` | Passes at the phase base (D-10); recorded `--at feadf3e^` by the orchestrator |
| D-21 (no row) | `databasise/tests/seam/test_hipporag_write_path.py::test_a_declared_fallback_never_refuses_a_write_run` | Pre-fix: `assert ForeignEngineRefusalError("... operation 'ingest' failed (RunIncomplete)") is None` |
| A-WR-05 (no row) | `databasise/tests/foreign/test_secret_redaction.py::test_an_in_process_provider_error_is_logged_without_its_key_or_url` | Pre-fix: `AssertionError: assert 'sk-SECRET123' not in 'ERROR    da...AIzaSECRET\n'` |
| A-WR-05 (no row) | `databasise/tests/foreign/test_secret_redaction.py::test_a_failed_query_nodes_debug_cause_is_redacted` | Pre-fix: `AssertionError: assert 'sk-SECRET123' not in 'NodeExecuti...y=AIzaSECRET'` |
| D-11 pattern | `test_redact_secrets_masks_key_shaped_tokens_only[url?key=AIzaSECRET&x=1-...]` | Pre-fix: `assert 'url?key=AIzaSECRET&x=1' == 'url?key=[REDACTED]&x=1'` |
| SEAM-05 (granted edit) | `databasise/tests/seam/test_foreign_engine_refusal.py` | Only line 118 changed, to `assert not records[0].exc_info` plus `assert "detail=" in records[0].getMessage()` |

## Phase gate

`cd databasise && .venv/bin/python tools/check_offline_suite.py`:
- `pytest -q -rs: 2178 passed, 4 deselected in 568.88s (0:09:28)`
- `python -m pytest -q -rs: 2178 passed, 4 deselected in 569.68s (0:09:29)`

## Deviations from Plan

**1. [Rule 1 - plan text mismatch] Debug-cause test asserts the real cause format.** The plan said the failed node's `cross_process_failure_cause` should contain "RuntimeError". The scheduler format is `NodeExecutionError: <message>` and carries no inner type name, so the test asserts the `NodeExecutionError: ` prefix and the absence of `sk-SECRET123` and `AIzaSECRET`. The scheduler format is unchanged. Files: `databasise/tests/foreign/test_secret_redaction.py`. Commit: ea1cbe9.

**2. Tooling note.** The BAK hook blocks Bash writes to test files and Bash commands that name ledger test_ref files, so test edits used the Edit tool and test_hipporag_write_path.py was not named in Bash after it became a test_ref.

**3. Commit count.** `commits: 4` is the measured count from the ledger base; two of those are orchestrator ledger commits, not this plan's.

## Auth gates

Task 2: owner-only `grant-check-edit` for the protected SEAM-05 test; granted, then verified by reading `ledger/REQUIREMENTS.json` (lines 2418-2421).

## Known Stubs

None.

## Threat Flags

None. T-12-22 to T-12-25 are mitigated as planned.

## Self-Check: PASSED

Commits 00c4b68 and ea1cbe9 exist on main; the modified files exist; the offline gate is green in both pytest styles.
