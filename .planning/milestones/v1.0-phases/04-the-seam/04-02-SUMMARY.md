---
phase: 04-the-seam
plan: 02
subsystem: api
tags: [seam, pydantic, evidence, token-accounting, refusals, lightrag]

requires:
  - phase: 04-the-seam (plan 01)
    provides: "databasise.seam.Databasise, the QueryObject/ResponseEnvelope/Selector shapes, the
      SeamRefusalError base class, and the declare-upfront closed envelope with evidence/
      token_accounting declared but empty"
provides:
  - "databasise.seam.evidence.EvidenceRef + mint_evidence_refs + resolve_evidence_ref — API-05's machine-resolvable evidence references (D-07)"
  - "databasise.seam.engine.Databasise.resolve_evidence — the second §18 operation the seam exposes"
  - "databasise.seam.tokens.TokenBreakdownEntry + assemble_token_breakdown — API-11's per-counted_by token breakdown (D-08, Pitfall 5)"
  - "databasise.seam._base._StrictModel — the shared strict Pydantic v2 base every seam model now inherits"
  - "databasise.stores.vector.FaissVectorStore.get_by_id — a public accessor for resolving one committed entry by id"
affects: [04-03-selectors-and-alias, 04-04-trace-and-mach11, 04-05-rest-transport]

actuals:
  tokens: 10163
  tasks: 3
  commits: 2
  plan_head_before: b35405abaeb6d1839165f8d246b79b4dca676e1b

tech-stack:
  added: []
  patterns:
    - "Shared strict base extracted to its own leaf module (_base.py) to break a circular import between envelope.py and the element-type modules (evidence.py, tokens.py) it needs to bind into its own fields"
    - "Assert, do not re-sort: envelope assembly preserves a node's own output order verbatim rather than re-deriving a sort the retrieval node and the store already agree on"
    - "A sentinel string reserved on an existing field (counted_by=\"unbudgetable\") rather than a new dedicated field, since no opaque node is registered anywhere in this milestone's parts registry yet"

key-files:
  created:
    - databasise/seam/evidence.py
    - databasise/seam/tokens.py
    - databasise/seam/_base.py
    - databasise/tests/seam/test_evidence_refs.py
    - databasise/tests/seam/test_token_accounting.py
  modified:
    - databasise/seam/envelope.py
    - databasise/seam/engine.py
    - databasise/stores/vector.py

key-decisions:
  - "EvidenceRef carries ref, namespace, kind, score, tier — not the full §4 ChunkRef shape (corpus_id, recipe@version, ordinal, content_hash). None of those four members is available at the retrieval position today; FA-03 records this as a named, declared limitation rather than shipping a reference that only looks like a ChunkRef."
  - "The unbudgetable sentinel is a reserved string value on TokenAccounting's existing counted_by field, not a new dedicated field — no opaque node is registered anywhere in this milestone's parts registry, so a dedicated field would be speculative surface."
  - "Envelope assembly never re-sorts evidence: the retrieval node's own output order (which already applies the store's descending-score/id-tiebreak sort) is preserved verbatim, so the store, the retrieval node, and the seam can never silently diverge into three different orderings."

patterns-established:
  - "Every new seam element-type model inherits databasise.seam._base._StrictModel, not a locally redefined strict base — the same frozen/extra-forbid contract at every nesting depth."

requirements-completed: [API-05, API-11]

coverage:
  - id: D1
    description: "An answer's evidence reference mints from a real retrieval item and resolves back through Databasise.resolve_evidence to the same store record (same id, same metadata)"
    requirement: "API-05"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_evidence_refs.py::test_a_minted_evidence_reference_resolves_through_the_seam_to_the_same_record"
        status: pass
    human_judgment: false
  - id: D2
    description: "Dereferencing an evidence reference the store does not hold raises UnresolvableEvidenceReferenceError by exception type, never None or an empty result"
    requirement: "API-05"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_evidence_refs.py::test_dereferencing_an_unknown_evidence_reference_raises_the_named_refusal"
        status: pass
    human_judgment: false
  - id: D3
    description: "A zero-item retrieval yields an envelope whose evidence list is present and empty, and whose answer is still a non-empty string"
    requirement: "API-05"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_evidence_refs.py::test_zero_item_retrieval_yields_an_empty_but_present_evidence_list"
        status: pass
    human_judgment: false
  - id: D4
    description: "Evidence order equals the store's own output order for a top-k retrieval, with the rank k+1 record absent, equal scores in the store's own id-tiebreak order, and deterministic across two runs of the same query"
    requirement: "API-05"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_evidence_refs.py::test_evidence_reference_list_matches_the_expected_top_k_id_sequence, ::test_the_record_at_rank_top_k_plus_one_is_absent, ::test_equal_scoring_records_appear_in_the_stores_own_id_tiebreak_order, ::test_running_the_same_query_twice_yields_identical_evidence_order"
        status: pass
    human_judgment: false
  - id: D5
    description: "The module docstring names each §4 ChunkRef member (corpus_id, recipe@version, ordinal, content_hash) as unpopulated (FA-03), and EvidenceRef inherits the envelope module's strict base"
    requirement: "API-05"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_evidence_refs.py::test_module_docstring_names_each_chunkref_member_as_unpopulated, ::test_evidence_ref_inherits_the_envelope_modules_strict_base"
        status: pass
    human_judgment: false
  - id: D6
    description: "A run reporting three distinct counted_by values produces exactly three breakdown entries with disjoint, correctly summed counts, never one merged scalar (Pitfall 5)"
    requirement: "API-11"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_token_accounting.py::test_three_distinct_counted_by_values_produce_three_breakdown_entries"
        status: pass
    human_judgment: false
  - id: D7
    description: "A zero-token run still reports its real counted_by values with real zero counts; breakdown ordering is sorted by counted_by and stable across two assemblies of the same run"
    requirement: "API-11"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_token_accounting.py::test_a_zero_token_run_still_reports_its_real_counted_by_values_with_zero_counts, ::test_breakdown_ordering_is_sorted_by_counted_by_and_stable_across_two_assemblies"
        status: pass
    human_judgment: false
  - id: D8
    description: "An unbudgetable participant raises UnbudgetableParticipantError by exception type and no envelope is produced; TokenBreakdownEntry declares no allowance/capacity field and every count field is int-only (a float raises ValidationError)"
    requirement: "API-11"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_token_accounting.py::test_an_unbudgetable_participant_raises_the_named_refusal_and_no_envelope_is_produced, ::test_token_breakdown_entry_declares_no_allowance_or_capacity_field, ::test_a_fractional_float_in_a_count_field_raises_validation_error"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-09-06
status: complete
---

# Phase 4 Plan 2: Evidence References and Token Accounting Summary

**A minted evidence reference resolves through `Databasise.resolve_evidence` back to the same store
record it came from, and every token number the seam reports now carries its own `counted_by` in a
per-value breakdown — never a merged scalar, and never a substituted number for an unbudgetable
participant.**

## Performance
- **Duration:** ~45 min (continuation; implementation was inherited already-complete and uncommitted)
- **Started:** 2026-09-06 / **Completed:** 2026-09-06
- **Tasks:** 3 / **Files modified:** 8 (5 created, 3 modified)

## Accomplishments
- `databasise/seam/evidence.py`: `EvidenceRef` (frozen, extra-forbidding), `mint_evidence_refs`
  (order-preserving, no re-sort), `resolve_evidence_ref`, and
  `UnresolvableEvidenceReferenceError`. The module docstring names each of §4's four `ChunkRef`
  members and states which are unpopulated at this position and why (FA-03).
- `databasise/seam/engine.py`'s `query()` mints the evidence list from the naive arm's own
  retrieval position (`chunk-vector`) before the `RunRecord` goes out of scope, and exposes
  `async def resolve_evidence(self, ref)` — the second §18 operation the seam exposes, opening and
  finalizing the store set the same way `query()` does.
- `databasise/seam/tokens.py`: `TokenBreakdownEntry` and `assemble_token_breakdown`, grouping a
  run's node traces by their own `counted_by` value verbatim, summed only within a group, sorted
  deterministically. `UnbudgetableParticipantError` raises before any envelope is constructed if a
  node reports the `unbudgetable` sentinel — distinguished from a real, honestly-reported `"none"`
  zero.
- `databasise/seam/envelope.py`'s `evidence` and `token_accounting` fields are now bound to these
  real element types, replacing 04-01's inline placeholder classes; no field on `ResponseEnvelope`
  itself was added, renamed, or removed (the `declare-upfront` checkpoint decision's envelope stays
  closed).
- `databasise/seam/_base.py`: the shared strict Pydantic v2 base extracted to its own leaf module,
  breaking what would otherwise be a circular import between `envelope.py` (which needs to import
  `EvidenceRef`/`TokenBreakdownEntry`) and `evidence.py`/`tokens.py` (which need the same strict
  base `envelope.py`'s own models use).
- `databasise/stores/vector.py`: `FaissVectorStore.get_by_id` — a public accessor so evidence
  dereference reads the store's public surface instead of reaching into `_entries`.
- `databasise/tests/seam/test_evidence_refs.py` (10 tests) and
  `databasise/tests/seam/test_token_accounting.py` (7 tests): mint/resolve round trip, the
  unresolvable-reference refusal by exception type, the empty-evidence case, ordering and the
  top-k boundary with an explicit id tiebreak, three distinct `counted_by` values driven from real
  stub clients, a zero-token run, deterministic ordering, the unbudgetable refusal, and int-only
  field validation.

## Task Commits
1. **Task 1 + 2: Evidence reference minting/resolution, ordering and the top-k boundary** -
   `a8c74a3` (feat)
2. **Task 3: The counted_by token breakdown and the unbudgetable refusal** - `136f676` (feat)

**Plan metadata:** committed after this SUMMARY (see completion report for hash).

## Files Created/Modified
- `databasise/seam/evidence.py` - `EvidenceRef`, `mint_evidence_refs`, `resolve_evidence_ref`,
  `UnresolvableEvidenceReferenceError`, `CHUNKS_NAMESPACE`, `TEXT_CHUNK_KIND`
- `databasise/seam/tokens.py` - `TokenBreakdownEntry`, `assemble_token_breakdown`,
  `UnbudgetableParticipantError`, `UNBUDGETABLE_SENTINEL`
- `databasise/seam/_base.py` - `_StrictModel`, the shared frozen/extra-forbid Pydantic v2 base
- `databasise/seam/envelope.py` - `evidence`/`token_accounting` fields bound to the real element
  types; `SeamEvent.spend` retyped to `TokenBreakdownEntry`
- `databasise/seam/engine.py` - `query()` mints evidence and assembles the token breakdown before
  constructing the envelope; new `resolve_evidence()` method
- `databasise/stores/vector.py` - `FaissVectorStore.get_by_id(doc_id)`
- `databasise/tests/seam/test_evidence_refs.py` - 10 new tests (Tasks 1 and 2)
- `databasise/tests/seam/test_token_accounting.py` - 7 new tests (Task 3)

## Decisions Made
See `key-decisions` above. Also:

- **Commit-history reconstruction (continuation-specific).** The inherited work arrived as one
  uncommitted diff with `engine.py`/`envelope.py` carrying both the evidence wiring (Task 1/2) and
  the token wiring (Task 3) in the same hunks. To produce two atomic, independently-verifiable task
  commits rather than one commit for the whole plan, I temporarily rolled `envelope.py`/`engine.py`
  back to the state they would have been in after Task 1/2 alone (evidence bound, `tokens.py` not
  yet imported, `TokenAccountingEntry` kept as 04-01's original inline placeholder), confirmed
  `tests/seam/test_evidence_refs.py` passed at that state and `tests/seam/test_token_accounting.py`
  genuinely failed (proving the split was real, not just an import error), committed, then reapplied
  the token-wiring diff verbatim (confirmed byte-identical via `git diff` before staging) and
  committed Task 3 separately. No test content or production logic was altered by this process —
  only the sequencing of two already-correct hunks across two commits.

## Deviations from Plan

**1. [Rule 2 - missing critical functionality] `databasise/stores/vector.py` gained a new public
`get_by_id(doc_id)` accessor, not listed in this plan's `files_modified`.**
- **Found during:** Task 1 (inherited already-implemented).
- **Issue:** `resolve_evidence_ref`'s dereference (D-07's deref-raising discipline) needs to look up
  one committed vector-store entry by id. Without a public accessor, it would have to reach into
  `FaissVectorStore._entries` directly — the exact private-attribute-reaching pattern Phase 3's code
  review already rejected once for `iter_vectors` (WR-02).
- **Fix:** A minimal accessor mirroring `iter_vectors`'s own public-surface reasoning:
  `get_by_id` returns the same per-item shape `query()` returns (`{"id": doc_id, **metadata}`,
  score-free), or `None` if the store holds no committed entry for that id.
- **Files affected:** `databasise/stores/vector.py`.
- **Verification:** `databasise/tests/seam/test_evidence_refs.py::test_a_minted_evidence_reference_resolves_through_the_seam_to_the_same_record` exercises it directly; full suite green.
- **Commit:** `a8c74a3`.

**2. [Deviation - new shared module, not a Rule 1-4 fix] `databasise/seam/_base.py` was created,
not listed in this plan's `files_modified`.**
- **Found during:** Task 1 (inherited already-implemented).
- **Issue:** 04-RESEARCH.md's Pitfall 7 requires every nested seam model to inherit a shared strict
  base. `envelope.py` needs to import `EvidenceRef`/`TokenBreakdownEntry` from `evidence.py`/
  `tokens.py` to bind them into its own fields; those modules in turn need the same strict base
  `envelope.py`'s own models use. Defining the base in `envelope.py` itself would make
  `envelope.py` and `evidence.py`/`tokens.py` import each other — a literal circular import.
- **Fix:** Extracted `_StrictModel` into its own dependency-free leaf module (`_base.py`) that
  every seam model module imports downward from, breaking the cycle.
- **Files affected:** `databasise/seam/_base.py` (new), `databasise/seam/envelope.py` (now imports
  from `_base` instead of defining `_StrictModel` locally).
- **Verification:** `databasise/tests/seam/test_evidence_refs.py::test_evidence_ref_inherits_the_envelope_modules_strict_base`, `test_token_accounting.py::test_token_breakdown_entry_inherits_the_envelope_modules_strict_base`; full suite green; import boundary check passes.
- **Commit:** `a8c74a3`.

**Total deviations:** 2 (Rule 2 - missing critical functionality; and one new shared module
required by the research's own documented Pitfall 7, judged sound and in house style).
**Impact on plan:** None on shipped behaviour — every task's acceptance criteria and the
plan-level `<verification>` block all pass. Both deviations are additive, out-of-declared-scope
files rather than changes to any declared file's intended shape.

## TDD Gate Compliance

**The RED phase was not observable for this continuation.** All three of this plan's tasks are
`tdd="true"`, but the implementation and its tests arrived already complete and passing — the prior
executor's session ended before committing, and this continuation's job was to verify and commit
inherited work honestly, not to fabricate a RED→GREEN sequence that did not happen. No RED commit
was created; no claim is made that a failing-test-first cycle was observed for this plan's tasks.
What was verified instead: every task's `<acceptance_criteria>` was actually re-run against the
inherited code (see Task Commits section — `10 passed` for evidence refs, `7 passed` for token
accounting), and the full suite was run twice (once before any commit, once after the commit-history
reconstruction) at `500 passed, 0 failed`.

## Issues Encountered

None beyond the deviations and the TDD-gate honesty note documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

`databasise/seam/envelope.py`'s `evidence` and `token_accounting` fields are now real, non-empty
for any run with retrieved items or reported tokens. `.planning/WINDOWS.md` entry 1 (the
evidence/token_accounting stub) is marked `fixed`. Entry 2 (`trace_token`/`seam_events`) remains
open for 04-04. 04-03 (selectors/alias) and 04-05 (REST transport) are unaffected by this plan's
changes and can proceed independently. No blockers.

## Self-Check: PASSED

- `databasise/seam/evidence.py`, `databasise/seam/tokens.py`, `databasise/seam/_base.py` — all
  present (`[ -f ]` verified).
- `databasise/tests/seam/test_evidence_refs.py`, `test_token_accounting.py` — both present.
- `git log --oneline --all --grep="04-02"` returns 2 commits (`a8c74a3`, `136f676`).
- `cd databasise && uv run pytest -q tests/seam/test_evidence_refs.py -x` — 10 passed.
- `cd databasise && uv run pytest -q tests/seam/test_token_accounting.py -x` — 7 passed.
- `cd databasise && uv run pytest -q tests/seam/` — 34 passed.
- `cd databasise && uv run pytest -q` — 500 passed (baseline 486 + 14 new; at/above the plan's
  own 466 floor).
- `cd databasise && uv run python -m databasise.tools.check_import_boundary` — exit 0, no
  violations.

---
*Phase: 04-the-seam*
*Completed: 2026-09-06*
