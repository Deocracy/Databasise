---
status: complete
phase: 11-lightrag-corpus-path
source: [11-VERIFICATION.md]
started: 2026-10-18T00:00:00Z
updated: 2026-10-18T00:00:00Z
---

## Tests

### 1. Re-ingest of a held id runs a full-corpus mirror (review A3-WR-01)
expected: The owner accepts the cost of a full v1-to-v2 mirror, which heals a document left unmirrored by a sync timeout.
result: pass. Owner: "Accept (Recommended)". The cost stays marked `shortcut:` at `parts_core/lightrag/v1_index_sync.py`.

### 2. Live ingest and delete record real token counts (LRAG-11)
expected: `counted_by` is `v1-subprocess`, with real token counts from the provider.
result: skipped. The owner deferred it to .planning/TESTING-PLAN.md §2 ("Live LightRAG write metering").

### 3. Uploaded files resolve to the caller's document_id in evidence
expected: Evidence for an uploaded file shows the caller's id, not v1's `doc-<md5>`.
result: issue. The owner chose "Fix in the sync": the v1-index-sync maps `doc-<md5>` back to the caller's id with the stem rule. The fix lands before phase completion (see Gaps).

### 4. A-WR-05: in-process HippoRAG provider errors are not redacted in the server log
expected: The owner decides.
result: routed. The owner chose "Route to Phase 12": Phase 12 fixes it under a grant-check-edit on `tests/seam/test_foreign_engine_refusal.py`.

### 5. Retry of a raw upload stuck mid-parse (LRAG-07)
expected: An interrupted `parsing` upload reaches `processed` after a retry.
result: skipped. The owner deferred it to .planning/TESTING-PLAN.md §2 ("Retry of a raw upload stuck mid-parse").

## Summary

total: 5
passed: 1
issues: 1
pending: 0
skipped: 2
blocked: 0
routed: 1

## Gaps

- Item 3: map `doc-<md5>` back to the caller's document_id in the v1-index-sync (stem rule), so evidence for an uploaded file carries the caller's id. A regression test covers it. The owner chose this fix on 2026-10-18.
