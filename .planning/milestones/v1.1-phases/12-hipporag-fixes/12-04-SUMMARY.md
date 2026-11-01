---
phase: 12-hipporag-fixes
plan: 04
subsystem: hipporag-index-side
tags: [hipporag, openie, extraction, refusal, concurrency, fact-provenance]
status: complete

requires:
  - phase: 12-hipporag-fixes
    provides: 12-02 token-sum helper and chunk vertices
provides:
  - "OpenIE extraction failures counted and refused as ExtractionFailed (REST 502), nothing committed"
  - "Bounded concurrent OpenIE via the scheduler max_concurrency semaphore (default 4 in both wirings)"
  - "Fact KV record and fact vector metadata keep the union of chunk_ids across ingests"
affects: [12-13 port record, hipporag query side]

actuals:
  tokens: 9000
  tasks: 2
  commits: 2
plan_head_before: cc050d111a78a8d8819698a72d4685c705c92c34
plan_head_after: 843ace2fc7948834be83b986ee6fb24c50cff82f

tech-stack:
  added: []
  patterns:
    - "Closed-code failure reasons (regex grammar, capped at 10) on a refusal instead of provider text"
    - "Semaphore held across one chunk's NER+triple pair so call order per chunk stays serial"

key-files:
  created:
    - databasise/tests/seam/test_extraction_failed_refusal.py
  modified:
    - databasise/parts_core/hipporag/openie.py
    - databasise/seam/refusals.py
    - databasise/wirings/hipporag/base.json
    - databasise/wirings/hipporag/corpus-ingest.json
    - databasise/parts_core/hipporag/entity_fact_embed.py
    - databasise/tests/parts_core/hipporag/test_index_side_extraction.py

key-decisions:
  - "D-08: a per-chunk NER/triple failure refuses the whole ingest after every chunk was attempted (costly reversibility: real-provider ingests that used to degrade now refuse; record in the 12-13 port record)"
  - "Semaphore wraps the whole chunk (NER then triples), not each call, so a max_concurrency of 1 reproduces the old strict call order and existing index-ordered stubs keep working"
  - "D-06: KV fact:<id> is the source of truth for the union; stored ids first, then new ids"

requirements-completed: [HIPP-10, HIPP-09]

duration: 45min
completed: 2026-10-19
---

# Phase 12 Plan 04: OpenIE failure counting, bounded concurrency, fact chunk-id union Summary

OpenIE now refuses an ingest with a counted, closed-code `ExtractionFailed` (REST 502, no raw text, nothing committed) while running chunks under a bounded semaphore, and a fact seen in several ingests keeps every source chunk id.

## Tasks

| Task | Name | Commit |
| ---- | ---- | ------ |
| 1 | Tracer: malformed OpenIE response refused as ExtractionFailed over REST, nothing committed (HIPP-10) | 40e541f |
| 2 | Fact keeps the union of chunk_ids across ingests; concurrency bound changes behaviour (HIPP-09) | 843ace2 |

The tracer feedback gate: the Task 1 seam test drives the real REST app end to end (502, body under 1 KB, no raw text, no committed chunk vector), and the full wave command passed (1423 passed) before Task 2 expanded.

## Intended ledger test_ref per row, with fail-first evidence

Pre-fix source is the state at plan start (HEAD cc050d1, which carries no change to the files below since the phase base for these modules).

### HIPP-10
`databasise/tests/parts_core/hipporag/test_index_side_extraction.py::test_openie_counts_failed_chunks_refuses_and_overlaps_calls`

Pre-fix run (plain AssertionError):

```
>       assert type(caught).__name__ == "ExtractionFailedError", repr(caught)
E       AssertionError: RuntimeError('provider down: secret-key-123')
E       assert 'RuntimeError' == 'ExtractionFailedError'
```

Post-fix: passes. Supporting tests, same run: `test_openie_attempts_every_chunk_before_refusing`, `test_openie_valid_empty_triples_is_not_a_failure`, `test_openie_max_concurrency_bounds_calls_in_flight` (pre-fix it failed: max in flight was not 3), and in `tests/seam/test_extraction_failed_refusal.py`: `test_a_malformed_openie_response_is_a_502_extraction_failed_refusal_and_commits_nothing` (pre-fix `AssertionError: assert 200 == 502`) and `test_the_refusal_caps_failure_reasons_at_ten_and_drops_codes_outside_the_grammar` (pre-fix `AssertionError: assert 'UnclassifiedEngineFailure' == 'ExtractionFailed'`).

### HIPP-09
`databasise/tests/parts_core/hipporag/test_index_side_extraction.py::test_a_fact_from_two_ingests_keeps_both_chunk_ids_in_kv_and_vector_metadata`

Pre-fix run (plain AssertionError):

```
E       AssertionError: assert (['c2'], ['c2']) == (['c1', 'c2'], ['c1', 'c2'])
E         At index 0 diff: ['c2'] != ['c1', 'c2']
```

Post-fix: passes, including the re-run of the second ingest leaving `["c1", "c2"]` unchanged.

## Verification

- `tests/parts_core/hipporag/test_index_side_extraction.py tests/seam/test_extraction_failed_refusal.py tests/seam/test_foreign_engine_refusal.py tests/seam/test_refusal_status_codes.py tests/seam/test_refusal_catalogue.py`: 83 passed.
- Wave command `tests/parts_core/hipporag tests/seam tests/stores tests/runner tests/parity tests/wirings tests/mcp`: 1424 passed, 3 deselected (after Task 2).

## Deviations from Plan

None - plan executed as written. Two notes:

- The `test_openie_max_concurrency_bounds_calls_in_flight` test is listed under Task 2 in the plan but needs the Task 1 openie rewrite to pass, so it was written and committed with Task 1. Task 2 acceptance greps still find it.
- The pre-existing `_StubOpenieLLMClient` (call-index based) is kept; it keeps working because the default `max_concurrency` of 1 with the semaphore held across a whole chunk preserves strict call order.

## Known Stubs

None.

## Threat Flags

None. T-12-05 mitigated (closed code grammar, cap 10, fixed message `OpenIE extraction failed for N chunk(s)`, seam test asserts body under 1024 bytes and no raw text; the part test asserts the provider exception text is absent from `str(exc)`). T-12-06 mitigated (bound is the scheduler-validated `max_concurrency`; wiring value 4).

## Self-Check: PASSED

- Files created/modified exist; commits 40e541f and 843ace2 are ancestors of HEAD.
- `ExtractionFailedError`, `"ExtractionFailedError": "ExtractionFailed"` and `"max_concurrency": 4` (both wirings) present; the lenient malformed-triple test is removed.
