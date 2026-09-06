---
phase: 03-lightrag-query-side
fixed_at: 2026-09-06T01:45:00Z
review_path: .planning/phases/03-lightrag-query-side/03-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 3
skipped: 1
status: partial
---

# Phase 03: Code Review Fix Report

**Fixed at:** 2026-09-06T01:45:00Z
**Source review:** .planning/phases/03-lightrag-query-side/03-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope (Critical + Warning): 4
- Fixed: 3
- Skipped: 1

Verification for all three fixes ran in the isolated worktree
(`.claude/worktrees/rf-03-2098297-1788658415`, fast-forwarded into `main` after this report was
written): `uv run pytest -q` (441 passed, 3 skipped, 1 deselected — the deselected test hits live
OpenRouter endpoints) plus a manual run of `uv run python -m databasise.evidence.parity_report
--check-results` to confirm the WR-03 CLI output by hand.

## Fixed Issues

### CR-01: `entity-hydrate-expand`/`relation-hydrate-expand` crash the whole node on any seed item missing its expected key

**Files modified:** `databasise/parts_core/lightrag/entity_hydrate_expand.py`, `databasise/parts_core/lightrag/relation_hydrate_expand.py`, `databasise/tests/parts_core/lightrag/test_graph_half_parts.py`
**Commit:** 1827695
**Applied fix:** Mirrored the existing absent-graph-node → `missing_seeds` pattern for a malformed
seed. `entity_hydrate_expand.py` now uses `seed.get("entity_name")` instead of a bare subscript; a
seed with no `entity_name` is appended to `missing_seeds` with `malformed_seed: True` and a
`diagnostic` string naming the missing field, instead of raising `KeyError`. The symmetric change
was applied to `relation_hydrate_expand.py` for `src_id`/`tgt_id` (diagnostic names whichever of
the two is absent). All `seed["id"]` reads were also switched to `seed.get("id")` for consistency,
so a seed missing `id` no longer raises either. Docstrings for both modules were updated to state
the malformed-seed rule alongside the existing absent-node rule. Added two regression tests (one
per module) asserting a seed missing the required field lands in `missing_seeds` with the expected
diagnostic rather than raising.

### WR-01: `run_arm._build_clients` reads four required `.env.parity` keys with bare subscript access

**Files modified:** `databasise/parity/run_arm.py`, `databasise/tests/parity/test_naive_arm_end_to_end.py`
**Commit:** 35898e8
**Applied fix:** Added a named `MissingParityEnvKeyError` (mirroring the existing
`MissingParityEnvError` for the absent-file case) and a `_REQUIRED_ENV_KEYS` tuple of all six keys
`_build_clients` needs. `_build_clients` now checks for every missing key up front and raises
`MissingParityEnvKeyError` naming all of them, instead of a bare, unnamed `KeyError` on whichever
key happens to be read first. `storage_audit.run_audit` reuses this same helper, so the fix reaches
both callers with no further change. Added two tests: one asserting the new error names every
missing key, one asserting normal construction still succeeds when all six keys are present.

### WR-03: `check_results()` has no rule catching a `status="completed"` record whose `decomposed_run_record.degraded=true` alongside a vacuous zero diff

**Files modified:** `databasise/evidence/parity_report.py`, `databasise/tests/parity/test_parity_evidence.py`
**Commit:** b54d7b8
**Applied fix:** Per the review's option (b): added `_degraded_but_vacuous_arms()`, which scans each
arm's committed comparison file for a `status="completed"` record whose
`decomposed_run_record.degraded` is true and whose `chunk_diff`/`entity_diff`/`relation_diff` are
all empty — the exact shape `check_results()`'s existing rules cannot see. `check_results()`
itself is left unchanged (the `degraded`/`degradation_reason` fields are already honestly
disclosed on the record, so this is not a new provenance violation); instead, `main()`'s
`--check-results` CLI path now calls the new helper and, when it returns any arms, prints
`"clean (5 arms, 3 degraded — `hybrid`, `local`, `global` measured a zero diff only because the
decomposed run crashed before completing a real retrieval; see PARITY-EVIDENCE.md for
disclosure)"` instead of a bare `"clean (5 arms)"`. Manually confirmed against the real committed
`parity_results/` directory. Added three tests: a synthetic degraded-vacuous record is flagged, a
synthetic clean completed record is not flagged, and a non-vacuous proof against the real committed
data names exactly `hybrid`/`local`/`global` (the three arms CR-01's crash currently affects).

## Skipped Issues

### WR-02: `human_findings.json`'s two `declared_causes` entries are AI-authored, not human-authored

**File:** `databasise/evidence/human_findings.json:12-14,26-27`, `databasise/evidence/DECLARED-DEVIATIONS.md:9-10`
**Reason:** CONTRACT §5 requires a human-authored cause for every named excursion. This agent
cannot fabricate a human-authored replacement — that would create a false attestation of human
review that did not happen, which is worse than the disclosed gap already on file. Verified the
review's fallback condition instead: both files' `recorded_by` fields already read `"Claude (AI
agent, gsd-code-fixer) — commit 2ce3c30; NOT recorded by the human owner, despite this file's own
name"` — the provenance is accurately and honestly labelled today, matching what the review itself
noted ("This is honestly disclosed... which is why this is a Warning rather than a Critical"). No
further mechanical change closes the underlying gap; it requires the human owner to actually
review and re-record the two causes (fix option (a) in the review), which is out of scope for this
automated fixer.

---

_Fixed: 2026-09-06T01:45:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
