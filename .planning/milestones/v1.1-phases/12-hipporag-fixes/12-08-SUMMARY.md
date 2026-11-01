---
phase: 12-hipporag-fixes
plan: 08
subsystem: hipporag-corpus
tags: [hipporag, reingest, document-remover, chunk-id, evidence-ref, D-12, D-03]
requires: ["12-06"]
provides:
  - "corpus-ingest.json runs document-remover first; consumes_documents is [chunk-embed, document-remover]"
  - "engine.ingest stamps the documents on every consumes_documents node"
  - "entity-fact-embed returns new_entities (entities the remover deleted count as new)"
  - "chunk id = sha256(document_id:ordinal:text)"
affects: [12-13]
tech-stack:
  added: []
  patterns: ["remove-then-write inside one all-or-none commit", "content-addressed ids so a stale ref fails instead of aliasing"]
key-files:
  created: []
  modified:
    - databasise/wirings/hipporag/corpus-ingest.json
    - databasise/seam/engine.py
    - databasise/parts_core/hipporag/entity_fact_embed.py
    - databasise/parts_core/hipporag/chunk_embed.py
    - databasise/tests/seam/test_hipporag_write_path.py
key-decisions:
  - "D-12: the remover is the first node of corpus-ingest.json; chunk-embed stays consumes_documents[0], so parity (which stamps only [0]) still works and the remover no-ops"
  - "D-03: the chunk id includes the document id, so identical text in two documents never shares an id (departure from the requirement's 'sha256 of text' wording)"
requirements-completed: [HIPP-16, HIPP-17]
status: complete
commits: 3
plan_head_before: 6b25aed9979476cc8d3ea36bbdf08e949292c046
plan_head_after: cb6a286c6ae8945201740be3105af69641ec74f5
actuals:
  tokens: 9000
  tasks: 3
  commits: 3
metrics:
  completed: 2026-10-19
---

# Phase 12 Plan 08: HippoRAG re-ingest replacement and content-addressed chunk ids Summary

A HippoRAG re-ingest of a document id now removes the previous version and writes the new one in one commit, keeps the document's synonymy edges, and chunk ids hash the chunk text so an old evidence ref either resolves to its original text or is refused.

## Tasks

| Task | Commit | Result |
|------|--------|--------|
| 1 (tracer) re-ingest leaves no stale chunk | 8302c44 | `document-remover` first node of `corpus-ingest.json`; engine stamps documents on every `consumes_documents` node; row test |
| 2 synonymy edges survive a re-ingest | 93c7742 | `entity-fact-embed` depends on the remover in corpus-ingest only and returns `new_entities`; test |
| 3 content-addressed chunk ids | cb6a286 | `sha256(document_id:ordinal:text)` at the only mint site; row test plus twin-document test |

Tracer gate: the Task 1 verify command (54 tests with the protected `test_ingest_abort.py`, `test_concurrent_ingest_failure.py`, `test_store_effects_wired.py` and the parity build test) passed before Tasks 2 and 3.

## Ledger test_ref (intended) and fail-first evidence

| Row | test node id | Fail-first |
|-----|--------------|------------|
| HIPP-16 | `databasise/tests/seam/test_hipporag_write_path.py::test_reingest_leaves_no_stale_chunk_and_delete_removes_everything` | run on the unchanged source (HEAD 6b25aed, test written first): `AssertionError: ['464e11eb...', '631d2767...', 'fbda2e41...']  assert 3 == 1` at `assert len(new_ids) == 1` (three chunk vectors remained after the shorter re-ingest) |
| HIPP-17 | `databasise/tests/seam/test_hipporag_write_path.py::test_an_old_ref_never_resolves_to_the_new_text_after_reingest` | run on the source as left by Task 2: `AssertionError: [('resolved', 'Ed Wood also wrote pulp novels for a living.')]` (the old ref resolved to the new text) |

Supporting (not row) tests, same file:

- `test_reingesting_a_document_keeps_its_synonymy_edges` failed first with `AssertionError: assert 'synonymy' in []` after the second ingest (the remover deleted the orphaned entities and, with committed `get_by_id` alone, they counted as old).
- `test_identical_text_in_two_documents_gets_two_chunk_ids` passed on its first run: the pre-fix hash already included the document id. It is a characterisation guard for the new hash, not a fail-first test.

The phase base is 0807948; the HIPP-16 and HIPP-17 failures above were observed at the later HEAD named in each row, with the source change not yet made. The orchestrator's `record-fail --at <phase base>` route is unaffected because neither test exists at the phase base.

## Verification

- Task 1 command: 54 passed (write-path, parity build, ingest-abort, concurrent-ingest-failure, store-effects-wired).
- Task 2 command: 124 passed (`test_hipporag_write_path.py`, `tests/parts_core/hipporag`, parity build, `tests/wirings`).
- Task 3 command: 31 passed (`test_hipporag_write_path.py`, `test_index_side_extraction.py`).
- Plan verification: `pytest -q tests/seam tests/parts_core tests/stores tests/wirings tests/parity tests/mcp` -> 1509 passed, 3 deselected.
- Acceptance: `consumes_documents` prints `['chunk-embed', 'document-remover']`, chunk-embed deps `['document-remover']`, entity-fact-embed deps `['openie', 'document-remover']`; `{document_id}:{ordinal}:{piece}` on one line of `chunk_embed.py`; both test names present once.
- Protected tests unedited.

## Deviations from Plan

None - plan executed exactly as written.

## Notes

- The `chunk_embed.py` docstring says the departure from "sha256 of text" is recorded in REQUIREMENTS.md. That file is orchestrator-owned bookkeeping and was not edited here; the HIPP-17 entry (line 325) still needs the note.
- Edge bullets on chunk boundaries and Unicode normalisation follow from the hash over the UTF-8 bytes of the exact string; no dedicated test was added beyond the plan's tests.
- Stores written before this plan hold ordinal-only chunk ids; they have no `doc:` manifest either (12-06 note) and must be rebuilt.

## Known Stubs

None.

## Threat Flags

None. T-12-12 mitigated (content-addressed ids plus remover-first re-ingest; row test). T-12-13 mitigated (removal and write commit together through the existing all-or-none commit).

## Self-Check: PASSED

Commits 8302c44, 93c7742 and cb6a286 are ancestors of HEAD; the five modified files are committed.
