---
phase: 17-gui-mockup
plan: 03
subsystem: ui
tags: [mockup, gui, badges, requirements, ui-spec]
requires:
  - phase: 17-02
    provides: "assembler, shell, window.__mock, MOCK-IDS.json"
provides:
  - "docs/gui/GAP-ROUTES.json: 20 {route, kind} entries (10 operator, 10 missing)"
  - "databasise/tests/gui/test_gui_03_needs_backend.py: registry vs live create_app route table, badge shape, GUI-03 row node"
  - "shell.instance.chip inside the GET /info operator-route wrapper"
  - "Amended GUI-02..GUI-11 and LIVE-09 text in REQUIREMENTS.md; amended 17-UI-SPEC.md"
affects: [17-04, 17-05, 17-06, 17-07, 17-08, 17-09, 17-10, 17-11, 17-12, 17-13]
tech-stack:
  added: []
  patterns:
    - "Badge kind is data: GAP-ROUTES.json Kind column; operator kind is checked against create_app(operator=True) minus create_app() at test time"
    - "A badge belongs to its nearest [data-needs-backend] wrapper"
key-files:
  created:
    - docs/gui/GAP-ROUTES.json
    - databasise/tests/gui/test_gui_03_needs_backend.py
    - mockups/src/fixtures/shell.json
  modified:
    - mockups/src/page.html
    - mockups/src/js/00-app.js
    - mockups/operator-console.html
    - docs/gui/MOCK-IDS.json
    - .planning/REQUIREMENTS.md
    - .planning/phases/17-gui-mockup/17-UI-SPEC.md
key-decisions:
  - "Instance chip text is 'version <v> · workspace <w>' filled from FIX.shell.info"
  - "GAP-ROUTES.json Kind lives in the registry table of the UI-SPEC as a mirrored column; the file is the authority"
requirements-completed: []
duration: one executor session
completed: 2026-10-30
status: complete
commits: 3
plan_head_before: 4674f1a6e4731667caaa814635d7855f31bc221c
plan_head_after: bcddc11ac052db681ed3ce5f87f8237b52408b1c
actuals:
  tokens: 14000
  tasks: 3
  commits: 3
---

# Phase 17 Plan 03: Gap route registry, GUI-03 test and amended contract Summary

`docs/gui/GAP-ROUTES.json` now fixes the badge registry (10 operator routes, 10 missing routes), the GUI-03 test checks it against the live FastAPI route table and against the badges in the mockup, the shell instance chip carries the first operator-route badge, and REQUIREMENTS.md and 17-UI-SPEC.md carry the D-05 to D-10, D-13 and D-14 amendments plus the code drift.

GUI-03 is NOT marked complete: its row node `test_gui_03_every_gap_route_is_marked_and_badged` fails until 17-12 adds the last screen. `requirements-completed` is empty on purpose; no ledger step was run.

## What was built

- Task 1 (tracer): `GAP-ROUTES.json` (sorted, unique, `indent=2`); `test_gui_03_needs_backend.py` with five nodes (file shape, operator kind equals `create_app(operator=True, log_path=...)` minus `create_app()`, missing kind absent from the operator app with `GET /corpus` exposing no `status`/`sort`/`search` parameter, wrapper badge shape, row node); `shell.json` key `info`; the header wrapper `<span data-needs-backend="GET /info" data-backend-state="operator" title="Mounted only with --operator">` holding the `operator route` badge and `shell.instance.chip` (`role="status"`), filled in `00-app.js`. MOCK-IDS.json gained exactly one id (`shell.instance.chip`), nothing removed.
- Task 2: ten requirement entries amended in REQUIREMENTS.md (GUI-02, GUI-03, GUI-04, GUI-05, GUI-06, GUI-08, GUI-09, GUI-10, GUI-11, LIVE-09), each ending `*(Amended 2026-10-25 per Phase 17 CONTEXT D-NN.)*`; GUI-02 and LIVE-09 also carry the D-13 `Decided in` sub-bullet. Ledger text untouched.
- Task 3: UI-SPEC amended in place (badge kinds and operator token, selector label rule, D-07/D-08/D-09/D-14 rulings, code drift: `v1_reachable`, `interrupted` status/tile/retry, null `tier`/`feed_tier`, GET /corpus selector caption, contradicting UI Considerations rows E1/E3/E4/E6/E9/E10/E14, two missing planned items, region-marker classes, createElement rule for control-less rows).

## Test results

- Verify command (4 supporting GUI-03 nodes + GUI-01 + GUI-02 + build stability): `12 passed`.
- Whole `databasise/tests/gui`: `1 failed, 13 passed`; the one failure is the GUI-03 row node (expected). `build.py --check` exits 0.
- Row node failure, quoted: `AssertionError: 19 route strings not yet in the mockup: ['GET /corpus (status, sort, search)', 'GET /jobs', 'GET /ledger/aliases', 'GET /log', 'GET /pipeline', 'GET /refusals', 'GET /traces', 'GET /wirings', 'POST /chunks', 'POST /documents/reprocess', 'POST /evidence/resolve-batch', 'POST /graph/node', 'POST /graph/node/attrs', 'POST /graph/nodes', 'POST /jobs/{job_id}/cancel', 'POST /ledger/history', 'POST /promote/preview', 'POST /selectors/resolve', 'POST /stores/counts']` (test_gui_03_needs_backend.py:142).
- Acceptance greps: REQUIREMENTS.md `per Phase 17 CONTEXT` 10 (>= 9), all six removal greps 0, `Decided in Phase 17 CONTEXT D-13` 2, `POST /graph/node/attrs` 1. UI-SPEC: `operator route` 7, all removal greps 0, `corpus.kpi.interrupted` 1, `removes it from the HippoRAG stores` 1, `v1_reachable` 2, `state-view` 2, both planned items 1.

## GUI fail-first base (for the ledger)

GUI-03 row test: `databasise/tests/gui/test_gui_03_needs_backend.py::test_gui_03_every_gap_route_is_marked_and_badged`. The test file is created in `aaa71d4` (`feat(17-03): gap route registry and GUI-03 badge test`), which is also the first commit where it can run; it fails there (19 route strings missing). Parent `4674f1a` has no such file, so a record-fail base of `aaa71d4` is the earliest runnable state. Row passes only after 17-12.

## Commits

- `aaa71d4` feat(17-03): gap route registry and GUI-03 badge test
- `b97a9d8` docs(17-03): amend GUI requirement text per Phase 17 CONTEXT
- `bcddc11` docs(17-03): amend UI-SPEC per Phase 17 CONTEXT rulings

## Deviations from Plan

None - plan executed as written. Judgment calls inside the plan's freedom:

- `.planning/` changes (Tasks 2 and 3) are separate commits from code, as required; the two lefthook hooks (`no-planning-in-code-commit`, `commit-msg`) passed without bypass.
- GUI-02 and LIVE-09 also received the `*(Amended ... D-13.)*` marker so the plan's `>= 9` grep on `per Phase 17 CONTEXT` holds (10 hits); the plan text only required the sub-bullet.
- The row node asserts the D-14 health ids (`corpus.health.clients`, `.reasons`, `.busy`) after the route-set check, so today it fails on the route list first.

## Known Stubs

None added. `shell.instance.chip` shows fixture data (`shell.json`), as the whole mockup does by design.

## Threat Flags

None. T-17-03: every amended entry names its CONTEXT decision and date; no ledger file or ledger verb was touched. T-17-04: the operator badge and title state `Mounted only with --operator`.

## Self-Check: PASSED

- docs/gui/GAP-ROUTES.json, databasise/tests/gui/test_gui_03_needs_backend.py, mockups/src/fixtures/shell.json present.
- Commits aaa71d4, b97a9d8, bcddc11 are ancestors of HEAD; `git rev-list --count` from the recorded base is 3.
