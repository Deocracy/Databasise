---
phase: 12-hipporag-fixes
plan: 09
subsystem: hipporag-corpus-surface
tags: [hipporag, corpus, counts, selector, read-only-listing, D-13]
requires: ["12-08"]
provides:
  - "stores.probes.list_kv_prefix: read-only, creates-nothing prefix lister over a namespace kv.sqlite3"
  - "Databasise.corpus_status(page=None, selector=None), Databasise.document_counts(selector=None)"
  - "GET /corpus and GET /corpus/counts take a selector query parameter (one shared parse, rest._selector_field)"
  - "MCP StatusToolArgs.selector, used by scopes corpus and counts"
affects: [12-13]
tech-stack:
  added: []
  patterns: ["registry-from-manifest: the doc:<id> manifest written with the data is the listing source", "optional selector leaves the no-selector path byte-identical"]
key-files:
  created:
    - databasise/tests/seam/test_hipporag_corpus_surface.py
    - databasise/tests/stores/test_kv_readonly_listing.py
  modified:
    - databasise/stores/probes.py
    - databasise/seam/engine.py
    - databasise/seam/rest.py
    - databasise/mcp/tools.py
    - databasise/mcp/server.py
    - databasise/tests/seam/test_hipporag_write_path.py
key-decisions:
  - "D-13: HippoRAG corpus listing reads the doc: manifests in hipporag-text-chunks; jobs.db stays the job registry; a non-HippoRAG selector takes the unchanged v1 path"
  - "list_kv_prefix opens plain mode=ro only when both -wal and -shm exist (a live writer), otherwise immutable; the plan said 'when -wal exists', but a -wal without -shm would make a plain read-only open create -shm (LRAG-13)"
requirements-completed: [HIPP-15]
status: complete
commits: 2
plan_head_before: fb8499e92b7cce06e0f3013525b03d3fb842ca68
plan_head_after: e8be6be85f5c0422e064a5e6f7448784d04e137d
actuals:
  tokens: 9000
  tasks: 2
  commits: 2
metrics:
  completed: 2026-10-19
---

# Phase 12 Plan 09: HippoRAG corpus status surface Summary

`/corpus`, `/corpus/counts` and MCP `status` take an optional selector; a HippoRAG selector lists and counts the documents from the per-document manifests through a read-only lister that creates nothing, and with no selector both responses are unchanged.

## Tasks

| Task | Commit | Result |
|------|--------|--------|
| 1 (tracer) HippoRAG document listed and counted under a selector | 1343612 | `list_kv_prefix`; selector-aware `corpus_status`/`document_counts`; `_selector_field` shared with the upload route; REST query parameter; row test |
| 2 MCP selector, lister guarantees, selector validation | e8be6be | `StatusToolArgs.selector` and its two server handlers; `test_kv_readonly_listing.py`; `test_hipporag_corpus_surface.py` |

Tracer gate: the Task 1 verify command (134 tests, including the protected `test_rest_corpus_endpoints.py`, `test_upload_selector_field.py`, `test_page_bounds.py`, plus `test_rest_transport.py`) passed before Task 2. The wave command `pytest -q tests/seam tests/mcp tests/stores tests/parts_core tests/parity` ended `1482 passed, 3 deselected`.

## Ledger test_ref (intended) and fail-first evidence

| Row | test node id | Fail-first |
|-----|--------------|------------|
| HIPP-15 | `databasise/tests/seam/test_hipporag_write_path.py::test_hipporag_documents_appear_in_jobs_corpus_counts_and_health` | Written first and run on the unchanged source (HEAD fb8499e). The jobs leg passed; the corpus leg failed: `AssertionError: {'documents': [], 'counts': {}, 'total': 0, 'next_offset': None}  assert 0 == 1` at `assert body["total"] == 1, body` (the route ignored the unknown `selector` parameter and answered from the empty faked v1 corpus). Passes after the fix. |

Supporting tests (not ledger rows): MCP leg `test_mcp_status_corpus_and_counts_take_the_selector` was run with `mcp/server.py` temporarily restored to HEAD: `AssertionError: assert ['v1-doc'] == ['mcp-doc']`; the change was then restored and is not reverted in any commit. The REST 422 and null-selector tests and the lister tests were written alongside the code and were not run against pre-fix source.

## Constraints checked

- Protected `test_rest_corpus_endpoints.py`, `test_tool_growth_invariant.py` and `test_health_probe.py` were not edited and pass.
- With no selector, `/corpus` and `/corpus/counts` reach the same engine code as before; a blank or `null` selector returns bytes identical to no selector (asserted).
- A HippoRAG listing on a fresh workspace adds no file under the store root and creates no workspace directory (asserted, LRAG-13). Building an engine itself creates `trace.db` and `jobs.db` at the root, which is outside this plan.
- A malformed `selector` is a 422 with a `refusal_type` on both routes; `limit` 0 and `offset` -1 are 422 on the selector path.

## Deviations from Plan

**1. [Rule 2 - Correctness] Live-WAL condition tightened.** The plan opens plain `mode=ro` when `kv.sqlite3-wal` exists. `list_kv_prefix` requires `-wal` and `-shm` both present, because a plain read-only open of a WAL database with no `-shm` creates it (the `probe_kv` finding), which would violate LRAG-13. Cost: a crash leftover with a WAL and no `-shm` is read immutably, so its uncheckpointed rows are not seen.

Otherwise the plan executed as written. Two Bash calls were refused by the BAK edit guard mid-run (a scripted append to a test file); the same edits were made with the Edit tool.

## Known Stubs

None.

## Threat Flags

None. The selector parse, SQL and listing body follow T-12-14, T-12-15 and T-12-16 (parameterised range query, read-only URI, entries carry id, status and timestamp only).

## Self-Check: PASSED

Files exist: `databasise/stores/probes.py`, `databasise/tests/seam/test_hipporag_corpus_surface.py`, `databasise/tests/stores/test_kv_readonly_listing.py`. Commits 1343612 and e8be6be are on HEAD; `git rev-list --count fb8499e..e8be6be` is 2.
