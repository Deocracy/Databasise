---
phase: 08-run-the-engine
plan: 02
subsystem: clients
tags: [openai-compat, token-accounting, tdd, response-validation]

requires:
  - phase: 08-run-the-engine
    provides: "08-01 live marker so default pytest stays offline"
provides:
  - "OpenAICompatibleClient counts a no-usage response as one unbudgetable call (RUN-02, D-05)"
  - "EmptyChoicesError, MissingCompletionContentError, EmbeddingBatchMismatchError named client errors (RUN-03, D-06)"
  - "embed() returns vectors in input order using each item's index"
affects: [08-10]

actuals:
  tokens: 4479
  tasks: 2
  commits: 4
plan_head_before: 194b5fddd58d4d0381508f2bb0bc57636b5cc257
plan_head_after: 0dfdfbcd67840ec499e6b53de5c426079e7fb003
commits: 4

tech-stack:
  added: []
  patterns:
    - "tests import phase-created error classes inside test bodies (reach them as openai_compat.<Name>) so the file collects on the pre-phase tree"

key-files:
  created: []
  modified:
    - databasise/clients/openai_compat.py
    - databasise/tests/clients/test_openai_compat.py
    - databasise/tests/seam/test_token_accounting.py

key-decisions:
  - "clients/ keeps the literal 'unbudgetable' with a comment naming seam.tokens.UNBUDGETABLE_SENTINEL, because clients/ must not import seam/; test_16 asserts the two are equal"
  - "__all__ in openai_compat.py is now sorted (RUF022 was already failing on the old unsorted list)"

requirements-completed: [RUN-02, RUN-03]

coverage:
  - id: D1
    description: "chat() and embed() with usage=None return call_count 1, counted_by 'unbudgetable', zero counts; value equals UNBUDGETABLE_SENTINEL"
    requirement: "RUN-02"
    verification:
      - kind: unit
        ref: "databasise/tests/clients/test_openai_compat.py#test_16_a_chat_response_with_no_usage_counts_one_unbudgetable_call"
        status: pass
      - kind: unit
        ref: "databasise/tests/clients/test_openai_compat.py#test_17_an_embed_response_with_no_usage_counts_one_unbudgetable_call"
        status: pass
    human_judgment: false
  - id: D2
    description: "A present all-zero usage and a None prompt_tokens keep counting by the resolved model with call_count 1"
    requirement: "RUN-02"
    verification:
      - kind: unit
        ref: "databasise/tests/clients/test_openai_compat.py#test_18_a_present_all_zero_usage_still_counts_by_the_resolved_model"
        status: pass
      - kind: unit
        ref: "databasise/tests/clients/test_openai_compat.py#test_19_a_usage_with_none_prompt_tokens_reports_zero_and_one_call"
        status: pass
    human_judgment: false
  - id: D3
    description: "/query over a no-usage OpenAI-compatible embedding client refuses with UnbudgetableParticipantError"
    requirement: "RUN-02"
    verification:
      - kind: integration
        ref: "databasise/tests/seam/test_token_accounting.py#test_a_no_usage_openai_compatible_embedding_makes_query_refuse"
        status: pass
    human_judgment: false
  - id: D4
    description: "Empty choices and None content raise named errors; empty-string content is returned unchanged"
    requirement: "RUN-03"
    verification:
      - kind: unit
        ref: "databasise/tests/clients/test_openai_compat.py#test_20_empty_choices_raise_empty_choices_error"
        status: pass
      - kind: unit
        ref: "databasise/tests/clients/test_openai_compat.py#test_21_none_content_raises_missing_completion_content_error"
        status: pass
      - kind: unit
        ref: "databasise/tests/clients/test_openai_compat.py#test_22_empty_string_content_is_returned_unchanged"
        status: pass
    human_judgment: false
  - id: D5
    description: "A mis-sized embedding batch, duplicate indices or a missing index raise EmbeddingBatchMismatchError; out-of-order items return in input order"
    requirement: "RUN-03"
    verification:
      - kind: unit
        ref: "databasise/tests/clients/test_openai_compat.py#test_23_two_vectors_for_three_inputs_raise_embedding_batch_mismatch_error"
        status: pass
      - kind: unit
        ref: "databasise/tests/clients/test_openai_compat.py#test_24_out_of_order_items_return_vectors_in_input_order"
        status: pass
      - kind: unit
        ref: "databasise/tests/clients/test_openai_compat.py#test_25_duplicate_or_missing_indices_raise_embedding_batch_mismatch_error"
        status: pass
    human_judgment: false

duration: ~10min (not timed at start)
completed: 2026-10-17
status: complete
---

# Phase 8 Plan 02: Hardened OpenAI-compatible client Summary

**A provider response with no usage is now one unbudgetable call, and empty choices, None content and mis-sized or badly indexed embedding batches raise named errors; out-of-order embeddings come back in input order**

## Accomplishments
- `_token_accounting` returns `TokenAccounting(call_count=1, counted_by="unbudgetable")` when `usage is None`; a `/query` through such a provider refuses with `UnbudgetableParticipantError`.
- `chat()` raises `EmptyChoicesError` or `MissingCompletionContentError` (carries `finish_reason`, no refusal text or tool arguments in the message); `""` content is returned unchanged.
- `embed()` raises `EmbeddingBatchMismatchError(expected, received, indices)` unless item indices are exactly `0..n-1`, then returns vectors sorted by index.

## TDD Gate Compliance

Plan frontmatter is `type: execute` with `tdd="true"` tasks. RED then GREEN commits exist for both tasks.

**Task 1 (RUN-02)**
- RED (`436712c`): `pytest -k "test_16 or test_17 or test_18 or test_19"` gave `2 failed, 2 passed`. Target failures: test_16 `assert 0 == 1` on `call_count` (counted_by was `'served-model'`), test_17 the same on `embed-model`. The seam test failed with `DID NOT RAISE UnbudgetableParticipantError`. Semantic assessment: each failed on the planned assertion for the intended reason (call_count 0 and model-identity counted_by today).
- Tests 18 and 19 passed on the pre-change code. They pin the usage-present branch that the plan says to leave unchanged (all-zero usage, `prompt_tokens=None`); the plan expected four reds, but only the two no-usage cases can be red. No `gsd_run check tdd-red-evidence` record was produced (the plan is `type: execute`, not `type: tdd`).
- GREEN (`02ec8d1`): 4 passed; seam file 8 passed.

**Task 2 (RUN-03)**
- RED (`24851b4`): `6 failed, 20 passed`. Tests 20, 21, 23 and both test_25 cases failed with `AttributeError: module 'databasise.clients.openai_compat' has no attribute '<Error>'` (the error classes did not exist yet, reached as `openai_compat.<Name>` per the fail-first constraint). test_24 failed on its own assertion, `[[2.0], [1.0]] == [[1.0], [2.0]]` (provider order returned). Semantic assessment: the AttributeError reds are the expected missing-class failures, not collection or fixture faults; test_22 passed because it pins existing `""` behaviour.
- GREEN (`0dfdfbc`): 26 passed in the client file; `tests/clients tests/parts_core tests/seam/test_token_accounting.py tests/seam/test_dual_transport.py` 207 passed. No REFACTOR commit.

## Task Commits

1. Task 1 RED `436712c` (test), GREEN `02ec8d1` (feat)
2. Task 2 RED `24851b4` (test), GREEN `0dfdfbc` (feat)

## Files Created/Modified
- `databasise/clients/openai_compat.py` - three error classes, no-usage accounting, index-ordered embed, sorted `__all__`, docstring paragraph on the no-usage rule
- `databasise/tests/clients/test_openai_compat.py` - tests 16-25; `_embedding_response(count=...)` emitting per-item `index`; `test_15` now embeds two texts against two items
- `databasise/tests/seam/test_token_accounting.py` - no-usage embedding double and the end-to-end refusal test

## Decisions Made
See `key-decisions` above; both follow the plan.

## Deviations from Plan

None - plan executed exactly as written. Implementation notes:
- The `embed()` guard uses `None in indices` before `sorted(indices)`, so a missing index never reaches a comparison of `None` with `int`.
- `ruff check` on the client file passes. `tests/clients/test_openai_compat.py` still reports I001 (import block order at lines 6-17); that finding exists on the pre-plan file and was left alone. `tests/seam/test_token_accounting.py` is clean.

## Issues Encountered
None. The 08-01 reinstall overlap (coupling note in the plan) did not occur.

## User Setup Required
None.

## Known Stubs
None.

## Threat Flags
None.

## Next Phase Readiness
- Plan 08-10's fail-first run can collect `test_openai_compat.py` on the pre-phase tree: new error classes are only referenced inside test bodies.
- RUN-11's `tokens.call_count > 0` assertion now holds for providers that omit usage.

## Self-Check: PASSED

- FOUND: databasise/clients/openai_compat.py, databasise/tests/clients/test_openai_compat.py, databasise/tests/seam/test_token_accounting.py
- FOUND commits: 436712c, 02ec8d1, 24851b4, 0dfdfbc
- `grep -n 'call_count=1, counted_by="unbudgetable"'` returns one line; three `class ...Error` definitions present; `"EmbeddingBatchMismatchError"` is in `__all__`.

---
*Phase: 08-run-the-engine*
*Completed: 2026-10-17*
