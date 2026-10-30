---
phase: 17-gui-mockup
plan: 08
subsystem: ui
tags: [gui, mockup, evidence, trace, debug-template, tdd]
requires:
  - phase: 17-05
    provides: "GUI-07 Wave 0 checks and the evidence hook contract"
  - phase: 17-06
    provides: "renderError/wireErrors, open-evidence/open-trace/promote events, QueryScreen"
  - phase: 17-07
    provides: "Compare columns that emit the same open-evidence / open-trace / promote payloads"
provides:
  - "Evidence & Trace screen: Evidence Inspector (row Open, manual lookup, batch, four states, mock outcome strip, planned list)"
  - "Trace Inspector: summary with sentinels and operator diagnostics, recent-runs operator wrapper, Debug view cloned from a <template>"
  - "Fixtures e-lightrag-chunk, e-hipporag-chunk, t-clean, t-partial-debug and a chunks map for the other query/compare refs"
affects: [17-09, 17-10, 17-11, 17-12, 17-13]
key-files:
  created:
    - mockups/src/js/30-evidence.js
    - mockups/src/css/30-evidence.css
    - mockups/src/fixtures/evidence.json
  modified:
    - mockups/src/screens/evidence.html
    - mockups/operator-console.html
    - docs/gui/MOCK-IDS.json
key-decisions:
  - "The three plan tasks landed in one commit: the HTML, JS and fixture are one unit and the tracer slice cannot be split by file without leaving a non-building intermediate"
  - "Evidence inspector Open trace delegates to the Open trace link of the result the evidence was opened from, so no second copy of the token exists and 20-query.js / 21-compare.js stay untouched"
  - "Token to trace fixture mapping is derived by scanning FIX.query and FIX.compare for trace_token (partial body gives t-partial-debug)"
requirements-completed: []
duration: one executor session
completed: 2026-10-30
status: complete
commits: 1
plan_head_before: c87cf8fa526b06750a981429745155a0b634f93b
plan_head_after: 86eb96b
actuals:
  tokens: 14000
  tasks: 3
  commits: 1
---

# Phase 17 Plan 08: Evidence and Trace Summary

Evidence & Trace is built: Open on a query or compare evidence row resolves the ref in the Evidence Inspector (300 ms loading, aria-busy and label Opening on the row), manual lookup and batch resolve work against fixtures, and the Trace Inspector shows the clean or partial summary with sentinel values as `not yet recorded`, while the identity panel and node table exist only as a template clone while Debug is on. All six GUI-07 nodes pass.

Requirement GUI-07 is NOT marked complete here; the orchestrator records the ledger row.

## Test results

Run by explicit node id with `DATABASISE_REQUIRE_BROWSER=1`:

- GUI-07: 6 passed, 0 failed (all five supporting nodes plus the row node `test_gui_07_evidence_and_trace_inspectors`).
- GUI-06: `[evidence]` now passes, plus `[query]`, branching and catalogue (4 passed).
- Previously-passing set, run again: GUI-01 (4), GUI-02 (3), GUI-03 supporting (4), GUI-04 (6), GUI-05 (6), smoke, build stability: all pass. Total 35 passed, 0 failed in the final run.
- `mockups/build.py --check` exits 0.

Not run (not buildable yet): GUI-03 row node, GUI-06 per-screen cases for documents, corpus, ledger, graph and the GUI-06 row node, GUI-08 to GUI-11.

## Commits

- `86eb96b` feat(17-08): evidence and trace inspectors with the Debug template

## Contract pins for later plans

- `EvidenceScreen` registers `setState` (idle, loading, resolved, refusal, trace-loading), `inject({status, body})` and `loadFixture` (e-lightrag-chunk, e-hipporag-chunk, t-clean, t-partial-debug). Errors render through `renderError("evidence", ...)` into one shared box above the tab panes.
- `open-evidence {ref:{id,namespace,kind}, score}` resolves `chunks` (fixture records for c-7f3a91, c-02be44, c-91d0c7, c-3d98fa, c-5ac3e0, c-e1b7d2; any other `c-` + 6 hex ref gets a generic record) and `hipporag-chunks` (chunk:7f3a91 and any `chunk:` + 6 or more hex). Anything else renders `evidence.state.refusal` (`record no longer present`). So 17-12 chunk-browser Open needs no change for `c-xxxxxx` refs.
- `open-trace {token}` shows the trace tab, prefills `evidence.trace.reference` and enables Load trace; it does not auto-load. A known token loads `t-clean` or `t-partial-debug`, an unknown one renders the `UnknownTraceReferenceError` banner with the token in a `mark`.
- `evidence.trace.use-in-ledger` calls `Console.show("ledger")` then emits `promote {trace: <reference value>}` (same payload as query and compare), so 17-11 needs nothing new.
- The Debug toggle is `evidence.trace.debug`; the clone inserts after `evidence.trace.summary`. A fixture without `nodes` (t-clean) shows a muted note instead of a clone.
- Document link `evidence.inspector.document-link` only calls `Console.show("corpus")`; it emits no event.
- `evidence.mock.outcome` values: success, refusal, validation, server-failure, generic, unknown-trace; it applies to the next Open, lookup or Load trace.
- New ids were added only (57 in MOCK-IDS.json); nothing removed or renamed.

## Deviations from Plan

- **Single commit instead of three.** The plan asks for one commit per task; the screen HTML, JS, CSS and fixtures were written as one unit and verified together, and the built mockup is a single generated file, so the tasks cannot be committed separately without a stale or partial build in between. Behaviour of all three tasks is covered by the final test run. No code is missing.
- **Extra fixture records** (`chunks` map with five LightRAG-shaped records, one of 5,000 characters with a long file_path) so every ref in the query and compare fixtures resolves, and so the E5 long-text case can be checked. Not in the plan list; additive.
- Judgment calls inside the plan: a cached record resolves without the 300 ms loading state; the Trace tab's empty heading is a plain block (no id, no region class); the Debug note for fixtures without debug fields is a plain paragraph.

## Auto-fixed Issues

**1. [Rule 1 - Bug] Recent-runs select forced a horizontal scroll at 375 px**
- **Found during:** ad-hoc 375 px check of the Debug view
- **Issue:** long option text gave the select an intrinsic width wider than the viewport (page scrollWidth 475)
- **Fix:** `.ev-recent` block wrapper with `max-width: 100%` on the label and select
- **Files modified:** mockups/src/screens/evidence.html, mockups/src/css/30-evidence.css
- **Commit:** 86eb96b (fixed before commit)

## Test defects

None. No Wave 0 assertion conflicted with the plan or the UI-SPEC.

## Hook blocks met

The BAK `check-edit-guard` blocked three read-only Bash commands that named or resolved protected test files: one `grep` over a test file, one pytest invocation built with a shell variable path (`F=...`), and one `--collect-only` over two whole test files. Each was a shell command, not an edit. I did not work around them: literal node-id invocations (which pass) and the Read tool were used instead. No hook was disabled and no test file was touched.

Message: `CHECK GUARD: databasise/tests/gui/test_gui_07_evidence_trace.py is a check, harness or helper file; only the owner can allow this edit (grant-check-edit).`

## Known Stubs

None. Every control acts on fixtures. The batch resolve is a documented needs-backend control that sets a fixture status line.

## Threat Flags

None. T-17-10: chunk content, kv values, node failure causes and typed references reach the DOM through `textContent` / `createTextNode` only (`grep -c "\.innerHTML" mockups/src/js/30-evidence.js` prints 0). T-17-11: identities appear only behind the Debug toggle, fixture values only.

## Self-Check: PASSED

- Files exist: mockups/src/js/30-evidence.js, mockups/src/css/30-evidence.css, mockups/src/fixtures/evidence.json, mockups/src/screens/evidence.html, mockups/operator-console.html.
- Commit `86eb96b` is an ancestor of HEAD; `git rev-list --count c87cf8f..HEAD` was 1 before this SUMMARY commit.
- Acceptance greps: resolve-batch wrapper 1, `evidence.planned.list` 1, `GET /traces` wrapper 1, `evidence.trace.nodes` 1, `"tier": null` 2.
