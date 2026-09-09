---
phase: 05-opaque-side-admission
plan: 05
subsystem: modality
tags: [opaque-node, admission, contract-s8, contract-s0, contract-s19-6, lightrag, compat-test]

# Dependency graph
requires:
  - phase: 05-opaque-side-admission
    provides: "05-01's lightrag/full-ingest@0.1.0 (real Part + AdmissionRecord), 05-03's lightrag/full-delete@0.1.0 (second port, mutates_store), 05-04's confirmation both ports still pass the import-boundary check, 05-06's second-engine admission precedent this plan's rule generalizes past"
provides:
  - "databasise/parts_core/lightrag/OPAQUE-BOUNDARY-RULE.md — the written inside-vs-across-boundary change rule MODAL-02 requires, addressed to a future contributor with no plan context"
  - "databasise/tests/parts_core/lightrag/test_full_ingest_compat.py — the compat test enforcing that rule: every published boundary value pinned, nothing v1-internal pinned, a negative control proving the check has teeth"
affects: [05-06, 05-07]

# Actuals (#2632)
actuals:
  tokens: 6809
  tasks: 2
  commits: 2
  plan_head_before: 8fec9e5

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A compat test that pins across-boundary values by dataclass field enumeration (dataclasses.fields) rather than hand-listing, so a field added to AdmissionRecord fails the test until classified, instead of silently passing because the test's own hand-written list didn't know about it"
    - "Deliberately NOT pinning a content-hash boundary value (environment_hash) by its literal computed digest, because the digest legitimately drifts with an internal, non-boundary change (a v1/uv.lock bump) the rule document itself declares free — pinned structurally (present, correctly prefixed, agrees between sibling ports) instead"
    - "Driver-script protocol derived live via AST walk of the _run() dispatcher's if/elif branches, never by importing the script (which imports lightrag, not installed in this venv)"

key-files:
  created:
    - databasise/parts_core/lightrag/OPAQUE-BOUNDARY-RULE.md
    - databasise/tests/parts_core/lightrag/test_full_ingest_compat.py

key-decisions:
  - "environment_hash is documented as an across-boundary AdmissionRecord field (per the plan's own must_haves.truths) but is NOT pinned by literal computed value in the compat test — only checked structurally (non-empty, sha256:-prefixed, equal between the two sibling ports). Pinning its exact digest would make a routine v1/uv.lock dependency bump — explicitly named as free-to-change in this same document's §3 — a false-positive boundary violation, which would corrupt the very signal the compat test exists to keep honest."
  - "AdmissionRecord's field set is checked generically via dataclasses.fields() against a pinned frozenset of field names, rather than only hand-listing the fields whose values are compared — so a new field added to AdmissionRecord fails the test immediately as an unclassified boundary widening, satisfying the plan's own explicit intent for Task 2.B, rather than silently passing because a hand-written projection function never looked at it."
  - "Completed OPAQUE-BOUNDARY-RULE.md's AdmissionRecord field list (added part_name_at_version, entry_path, wall_clock_ceiling_basis, and the word 'verdicts') during Task 2 rather than leaving it at the 11-identifier subset Task 1's own acceptance criteria required — needed so the compat test's anti-drift assertion (every pinned identifier must appear in the document) actually passes, and so the document is a complete description of every AdmissionRecord field, not just the ones a fixed acceptance-criteria list happened to name."

requirements-completed: [MODAL-02]
# MODAL-02 was shared across 05-01/05-03/05-05 (each contributed one facet: real ports, delete
# port, the change rule + compat test); this plan's own completion is what made
# requirements.ready-ids report it ready, and it is now marked complete in REQUIREMENTS.md.

coverage:
  - id: D1
    description: "OPAQUE-BOUNDARY-RULE.md states, as a rule a reader can apply without reading a plan, exactly which values are the opaque boundary (version bump + re-admission required) and which are internals (free to change), plus the one case that is neither (new capability disguised as an internal edit)"
    requirement: "MODAL-02"
    verification:
      - kind: other
        ref: "grep-based identifier-presence check (11 required identifiers, this SUMMARY's own verification run) + git show --name-only confirming no docs/system-model/ path was touched"
        status: pass
    human_judgment: true
    rationale: "The plan's own plan-level <verification> block asks a human to read the document once as a contributor would and confirm section 4's 'neither' case is stated clearly enough to stop the shortcut it exists to stop — a judgment call on prose clarity, not a fact an automated test can settle."
  - id: D2
    description: "test_full_ingest_compat.py fails if any pinned boundary value of lightrag/full-ingest@0.1.0 or lightrag/full-delete@0.1.0 changes without a version bump; the driver script's per-operation stdin/stdout key sets are pinned; nothing inside the subprocess is pinned"
    requirement: "MODAL-02"
    verification:
      - kind: unit
        ref: "tests/parts_core/lightrag/test_full_ingest_compat.py::test_ingest_part_boundary_matches_the_pin"
        status: pass
      - kind: unit
        ref: "tests/parts_core/lightrag/test_full_ingest_compat.py::test_delete_part_boundary_matches_the_pin"
        status: pass
      - kind: unit
        ref: "tests/parts_core/lightrag/test_full_ingest_compat.py::test_driver_protocol_matches_the_pin"
        status: pass
      - kind: unit
        ref: "tests/parts_core/lightrag/test_full_ingest_compat.py::test_driver_dispatches_on_exactly_the_pinned_operation_set"
        status: pass
      - kind: unit
        ref: "tests/parts_core/lightrag/test_full_ingest_compat.py::test_the_comparison_has_teeth_a_mutated_part_copy_differs_from_the_pin"
        status: pass
      - kind: unit
        ref: "tests/parts_core/lightrag/test_full_ingest_compat.py::test_rule_document_and_check_agree"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-09-09
status: complete
---

# Phase 5 Plan 5: Opaque-side admission — the inside-vs-across-boundary change rule, and the compat test that enforces it Summary

**`OPAQUE-BOUNDARY-RULE.md` states exactly which of `lightrag/full-ingest@0.1.0`/`lightrag/full-delete@0.1.0`'s declared values require a version bump and re-admission to change, and `test_full_ingest_compat.py` pins every one of them — deriving the driver script's stdin/stdout protocol live via AST walk, pinning nothing inside the subprocess, and proving its own comparison has teeth with a negative control.**

## Performance

- **Duration:** ~45 min
- **Completed:** 2026-09-09
- **Tasks:** 2 completed
- **Files:** 2 created, 0 modified (the rule document was created and then completed in the same plan, across its two tasks)

## Accomplishments

- `databasise/parts_core/lightrag/OPAQUE-BOUNDARY-RULE.md`: the written inside-vs-across-boundary change rule ROADMAP criterion 1 and MODAL-02 require — six across-boundary `Part` fields, every `AdmissionRecord` field, and the driver script's per-operation protocol, all enumerated by name; what is free to change inside the subprocess/v1 venv; the one "neither" case (a new capability landing inside the opaque core disguised as an internal edit).
- `databasise/tests/parts_core/lightrag/test_full_ingest_compat.py`: seven tests enforcing that rule — literal pins for both ports' `Part`/`AdmissionRecord` boundary values (checked via a generic `dataclasses.fields()` enumeration so a genuinely new `AdmissionRecord` field fails until classified, not just the fields this test happened to hand-list), a live AST-derived driver protocol compared against a literal pin, a structural (not literal-value) check on `environment_hash`, an anti-drift assertion keeping the prose document and this check from diverging, and a negative control proving the comparison helper actually distinguishes a mutated `Part` copy from the pin.

## Task Commits

Each task was committed atomically:

1. **Task 1: The written inside-vs-across-boundary change rule** - `3eb65dd` (docs)
2. **Task 2: The compat test that enforces the rule** - `106cacb` (test)

_No separate plan-metadata commit is issued by this executor run; STATE.md/ROADMAP.md updates are committed alongside this SUMMARY._

## Files Created/Modified

- `databasise/parts_core/lightrag/OPAQUE-BOUNDARY-RULE.md` - the rule document (created in Task 1, completed with the remaining `AdmissionRecord` field names in Task 2)
- `databasise/tests/parts_core/lightrag/test_full_ingest_compat.py` - the compat test enforcing it

## Decisions Made

See `key-decisions` in frontmatter — three decisions: not literal-pinning `environment_hash`'s computed digest (a structural check instead, to avoid a false-positive on a legitimately free internal change); checking `AdmissionRecord`'s field set generically via `dataclasses.fields()` rather than only hand-listing compared fields; and completing the rule document's `AdmissionRecord` field list during Task 2 so the compat test's own anti-drift assertion (every pinned identifier must appear in the prose) actually passes.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `OPAQUE-BOUNDARY-RULE.md`'s Task-1 identifier list under-described `AdmissionRecord`, which would have made Task 2's own anti-drift check fail**
- **Found during:** Task 2 (writing `test_rule_document_and_check_agree`)
- **Issue:** Task 1's acceptance criteria required only 11 specific identifiers to appear in the rule document's prose. Task 2's action text B separately requires the compat test to pin *every* `AdmissionRecord` field, and Task 2's action text D requires every identifier the test pins to also appear in the prose document. The rule document as written after Task 1 did not name `part_name_at_version`, `entry_path`, `wall_clock_ceiling_basis`, or the word `verdicts` — so a compat test pinning those fields (as Task 2.B requires) would have failed its own anti-drift assertion (Task 2.D) the moment it was written, not because of a real drift but because the document was never complete in the first place.
- **Fix:** Extended `OPAQUE-BOUNDARY-RULE.md` §2's `AdmissionRecord` bullet to name all eleven of that dataclass's fields explicitly, including a dedicated explanation for why `environment_hash`'s literal value is deliberately not pinned by the compat test (a genuinely new piece of information the document needed regardless of the anti-drift mechanics, since a reader would otherwise wonder why a listed boundary field's value is not enforced literally).
- **Files modified:** `databasise/parts_core/lightrag/OPAQUE-BOUNDARY-RULE.md`
- **Verification:** `test_rule_document_and_check_agree` passes; a grep-based identifier-presence check for all 17 Part+AdmissionRecord field names (run manually during this session) confirms every one appears in the document text.
- **Committed in:** `106cacb` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 Rule 1 — a plan-structure gap between Task 1's narrower acceptance criteria and Task 2's broader "every field" requirement, resolved toward Task 2's explicit instruction and toward document completeness).
**Impact on plan:** No scope creep — the fix only added missing identifier names to a document Task 1 already created, and was necessary for Task 2's own compat test to pass its own anti-drift assertion rather than fail immediately on a documentation gap that had nothing to do with a real boundary change.

## Issues Encountered

None beyond the deviation documented above.

## Authentication Gates

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- MODAL-02's written change rule now exists and is enforced by a compat test with a negative control — the failure mode `.planning/research/PITFALLS.md` names directly (the opaque-node quarantine becoming a dumping ground) now has both a documented rule and a red-on-violation check, for both of this phase's LightRAG corpus-side ports.
- The rule's structure (six `Part` fields, every `AdmissionRecord` field enumerated generically, driver-script protocol derived live via AST) generalizes cleanly to any future opaque port — 05-06's `codebase-memory-mcp@0.1.0` admission (a differently-shaped foreign engine, MCP-over-stdio rather than subprocess-JSON) was not retrofitted with an equivalent compat test by this plan, since this plan's own `<files>`/`files_modified` scope names only the two LightRAG corpus-side ports; a future phase admitting a new opaque port should follow this same pattern rather than re-deriving one.
- One `<human-check>` item from the plan's own `<verification>` block is deferred to end-of-phase UAT per `workflow.human_verify_mode: end-of-phase`: read `OPAQUE-BOUNDARY-RULE.md` once as a contributor would and confirm section 4's "neither" case (new capability disguised as an internal edit) is stated clearly enough to stop the shortcut it exists to stop.
- No blockers for 05-06 (already complete) or 05-07.

## Self-Check: PASSED

- FOUND: `databasise/parts_core/lightrag/OPAQUE-BOUNDARY-RULE.md`
- FOUND: `databasise/tests/parts_core/lightrag/test_full_ingest_compat.py`
- FOUND commit: `3eb65dd`
- FOUND commit: `106cacb`
- Re-ran all `<acceptance_criteria>` from every task: all pass (11-identifier presence check, both `name_at_version`s present, `test_full_ingest_compat.py` named as enforcement, CONTRACT §0 named for the version-bump sentence, `git show --name-only` confirms no `docs/system-model/` path touched by Task 1's commit; the `ast`-based top-level-name check for `PINNED_INGEST_BOUNDARY`/`PINNED_DELETE_BOUNDARY`/`PINNED_DRIVER_PROTOCOL` prints `ok`; negative-control test passes; `grep -c 'lightrag'` occurrences are all path/name literals, no `import lightrag`/`from lightrag` statement; no assertion references a v1 chunking parameter, prompt, or facade constructor argument).
- Re-ran the plan-level `<verification>`: `cd databasise && uv run pytest -q` — 714 passed, 1 skipped, exit 0. `cd databasise && uv run python -m databasise.tools.check_import_boundary` — exit 0.

---
*Phase: 05-opaque-side-admission*
*Completed: 2026-09-09*
