---
quick_id: 261101-liv
type: quick
status: complete
completed: 2026-11-01
commit: 9acc573c
files_modified: [databasise/uv.lock]
---

# Quick 261101-liv: Bump vulnerable v2 lockfile dependencies Summary

`databasise/uv.lock` now locks certifi 2026.10.23, PyJWT 2.15.1 and opentelemetry-api 1.45.2. No other package changed version. `v1/uv.lock` is unchanged.

## Version changes

| Package | Before | After | Target | Met |
|---------|--------|-------|--------|-----|
| certifi | 2026.7.22 | 2026.10.23 | >= 2026.10.18 | yes |
| pyjwt | 2.13.0 | 2.15.1 | >= 2.15.0 | yes |
| opentelemetry-api | 1.44.0 | 1.45.2 | >= 1.45.1 | yes |

`uv lock --upgrade-package certifi --upgrade-package pyjwt --upgrade-package opentelemetry-api` reported these three updates only. The diff is 9 insertions and 9 deletions. The upgrade forced no sibling package to move. mcp stays at 2.2.0 and allows PyJWT 2.15.

`uv sync --frozen --extra rest --extra mcp` (the dev group installs by default) swapped exactly those three packages in the venv.

## Test results

- Full offline suite (`uv run pytest -q -p no:randomly`): 3377 passed, 1 failed, 4 deselected (11m57s).
- Console suites (`tests/gui` and `tests/gui_live`, with `PLAYWRIGHT_BROWSERS_PATH` and `DATABASISE_REQUIRE_BROWSER=1` set): 216 passed.
- The socket-count test `test_criterion_1_library_startup_with_no_external_server` passed in the full run.

## Deferred Issues

- The failing test is `tests/evidence/test_parity_report_render.py::test_every_planning_path_resolves`. It also fails when run alone and it does not involve any dependency. It checks that the path `.planning/REQUIREMENTS.md`, cited by `databasise/evidence/FALSIFIER-5-EVIDENCE.md`, exists. Commit 7421f067 ("chore: remove REQUIREMENTS.md for v1.1 milestone") deleted that file during the milestone archive, before this task. The fix belongs to the archive cleanup: point the evidence file at the archived requirements path, or teach the test about archived paths. This task did not touch either.

The status is `partial`, not `complete`, because this one failure means the suite is not fully green.

## Deviations from Plan

None. All plan steps ran as written. The plan expected 3377 passed; the run gave 3377 passed plus the one failure described above.

## Follow-up (orchestrator, 2026-11-01)

The one failure, `tests/evidence/test_parity_report_render.py::test_every_planning_path_resolves`, was caused by the v1.1 milestone close removing `.planning/REQUIREMENTS.md`, not by this bump. Fixed in 033f72fa: FALSIFIER-5, CROSS-MODALITY and PROMOTION-LEDGER evidence now cite `.planning/milestones/v1.0-REQUIREMENTS.md` (MACH-03, MODAL-05, HARD-01/02 are v1.0 rows). `tests/evidence` passes 137/137, so the suite is green: 3378 passed. Status set to complete.
