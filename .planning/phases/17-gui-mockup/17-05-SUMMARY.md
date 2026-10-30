---
phase: 17-gui-mockup
plan: 05
subsystem: testing
tags: [gui, playwright, wave-0, tdd, evidence, documents, corpus, ledger, graph]
requires:
  - phase: 17-01
    provides: "ui fixture, MockUI helpers, mockup_path"
  - phase: 17-03
    provides: "amended UI-SPEC and GUI requirement text (D-05, D-07, D-08, D-10, D-14)"
  - phase: 17-04
    provides: "Query hooks and ids (query.evidence.open-N, query.result.trace-link)"
provides:
  - "test_gui_07_evidence_trace.py: GUI-07 row node and five focused nodes"
  - "test_gui_08_documents.py: GUI-08 row node and six focused nodes"
  - "test_gui_09_corpus.py: GUI-09 row node and five focused nodes"
  - "test_gui_10_ledger.py: GUI-10 row node and five focused nodes"
  - "test_gui_11_graph.py: GUI-11 row node and six focused nodes"
affects: [17-08, 17-09, 17-10, 17-11, 17-12, 17-13]
key-files:
  created:
    - databasise/tests/gui/test_gui_07_evidence_trace.py
    - databasise/tests/gui/test_gui_08_documents.py
    - databasise/tests/gui/test_gui_09_corpus.py
    - databasise/tests/gui/test_gui_10_ledger.py
    - databasise/tests/gui/test_gui_11_graph.py
  modified: []
key-decisions:
  - "Document ids in dialogs and selectors use the amended label rule: Default, capability reads_graph"
  - "Tests that need an optional empty/visible state assert to_be_hidden, so both a hidden attribute and an empty element pass"
requirements-completed: []
duration: one executor session
completed: 2026-10-30
status: complete
commits: 3
plan_head_before: 3f2c3644097cbc83409da00615f45fff9c1ccb54
plan_head_after: 268874f20380576a843a0596499753d1a88c2d81
actuals:
  tokens: 8600
  tasks: 3
  commits: 3
---

# Phase 17 Plan 05: Wave 0 Evidence, Documents, Corpus, Ledger and Graph checks Summary

Five complete Wave 0 test files (32 collected nodes) pin the Evidence & Trace, Documents & Jobs, Corpus & Health, Ledger and Graph ids, verbatim strings and `window.__mock` hooks, encoding D-05, D-07, D-08, D-10 and D-14; against the shell-only mockup all 32 fail on a missing id or an unregistered screen hook. With 17-04 every GUI row check now exists.

Requirements GUI-07 to GUI-11 are NOT marked complete here; the orchestrator records the ledger rows.

## Test results

`DATABASISE_REQUIRE_BROWSER=1 databasise/.venv/bin/python -m pytest -q <files> -p no:cacheprovider`:

- test_gui_07_evidence_trace.py: `6 failed`, no ERROR line.
- test_gui_08_documents.py plus test_gui_09_corpus.py: `13 failed`, no ERROR line.
- test_gui_10_ledger.py plus test_gui_11_graph.py: `13 failed`, no ERROR line.
- `--collect-only` on all five files: `32 tests collected`. `ruff check` on all five: clean. `grep -c "^def test_"` prints 6, 7, 6, 6, 7.

Failure reasons: `Locator.fill/click: Timeout 3000ms exceeded` waiting for a `query.*`, `documents.*`, `graph.*` id; `Page.evaluate: Error: <screen> has no loadFixture` for the unregistered `corpus`, `ledger` and `graph` hooks. Both graph walks fail on their presence assertions (`Locator expected to be attached` / `to be visible`). No skip, no collection or fixture error.

## Wave 0 end

`268874f20380576a843a0596499753d1a88c2d81` (`test(17-05): Wave 0 GUI-10 ledger and GUI-11 graph checks`). All five files exist and every row node fails there, so `record-fail --at 268874f` works for GUI-07 to GUI-11.

## Fail-first bases (row node per GUI row)

| Row | Row node | File added at | First failure |
|-----|----------|---------------|---------------|
| GUI-07 | `databasise/tests/gui/test_gui_07_evidence_trace.py::test_gui_07_evidence_and_trace_inspectors` | `d5fcedd` | `Locator.fill: Timeout 3000ms exceeded` waiting for `query.text.input` |
| GUI-08 | `databasise/tests/gui/test_gui_08_documents.py::test_gui_08_ingest_prechecks_jobs_and_delete` | `ef0b4fc` | `Locator.click: Timeout 3000ms exceeded` waiting for `documents.tabs.paste` |
| GUI-09 | `databasise/tests/gui/test_gui_09_corpus.py::test_gui_09_health_tiles_and_corpus_table` | `ef0b4fc` | `Page.evaluate: Error: corpus has no loadFixture` (the shell's placeholder screen already carries the h1; the missing hook is the first failure) |
| GUI-10 | `databasise/tests/gui/test_gui_10_ledger.py::test_gui_10_promote_preflight_and_timeline` | `268874f` | `Page.evaluate: Error: ledger has no loadFixture` |
| GUI-11 | `databasise/tests/gui/test_gui_11_graph.py::test_gui_11_graph_browser` | `268874f` | `AssertionError: Locator expected to be visible` (graph.nodes.table) |

Every row fails at its own file's commit and at Wave 0 end.

## Commits

- `d5fcedd` test(17-05): Wave 0 GUI-07 evidence and trace checks
- `ef0b4fc` test(17-05): Wave 0 GUI-08 documents and GUI-09 corpus checks
- `268874f` test(17-05): Wave 0 GUI-10 ledger and GUI-11 graph checks

## Deviations from Plan

None - plan executed as written. Judgment calls inside the plan's freedom (screen plans must match these, or list a "Test defects" correction):

- GUI-07 row node asserts `evidence.trace.reference` equals a 43-character URL-safe token (`^[A-Za-z0-9_-]{43}$`, the `q-success` trace token shape) because the tests cannot read the token otherwise.
- GUI-10 retire dialog: after typing `3.0.0` the confirm stays disabled until a trace (`select_option(index=0)` on `shell.dialog.retire-traces`) and `retire-origin-human` are chosen (UI-SPEC rule: all three conditions).
- GUI-10 roll-back-first node loads `timeline-prod` first, then `refusal-active-retire`; the timeline must stay rendered under the banner.
- GUI-08 row node closes the jobs drawer (`documents.jobs.close`) before changing the selector, then reopens it and reloads `j-page1`, so it works whether the drawer is modal or not.

## Contract pins for the screen plans (17-08 to 17-12)

- Evidence: score element contains `0.8731`; header contains ref, namespace and kind; `evidence.trace.status` contains `partial`/`clean`; `evidence.trace.summary` contains `operator diagnostics`; bundle-ref and snapshot-hash contain `not yet recorded` with a `title` starting `sentinel:`; unknown-trace injection (404, `trace_reference`) renders a `<mark>` in `evidence.error.refusal`; Debug view `evidence.trace.nodes` / `.identity` count 0 until toggled; flagged rows are `tr[data-row-state="failed"|"halted"]`; the node table contains `placeholder`; `Do not paste this hash into a selector` is page text.
- Documents: `documents.tabs.paste|upload` are tabs; `documents.jobs.open|close`; the `documents.upload.file` input accepts `set_input_files`; empty error elements are hidden when no error; `documents.state.in-flight` must be visible long enough for Playwright to see it before `documents.result.card`; delete dialog (`shell.dialog.delete`) contains document id and selector label, focus on `shell.dialog.delete-cancel` (read through `document.activeElement` `data-mock-id`).
- Corpus: `corpus.health.stores` rows carry key text (`vector:chunks`, `...hipporag-...` exactly five rows containing `hipporag-`); `corpus.health.overall` has exact text and `data-state`; `corpus.health.busy` has an ancestor `[data-needs-backend="GET /info"][data-backend-state="operator"]`; `clients` and `reasons` have no `[data-needs-backend]` ancestor; fixture `health-degraded` carries `model clients not configured`; every table body row has `data-status`; the failed fixture must leave at least two failed rows and fewer than all.
- Ledger: Retire wrapper is the nearest `span[title]` ancestor; verb options carry value `operator-asserted` for the selected one; preflight text includes the verbatim blocker strings; `shell.dialog.retire-traces` is a select with at least one option.
- Graph: `graph.node.degree` text contains `12` as a whole word; the node-table `Open` buttons sit in `tr`; every element whose `data-mock-id` starts with the six graph prefixes (including `graph.selector.alias-picker`) has a `[data-needs-backend]` ancestor; no input, select, textarea or button on the screen (id, name, aria-label, placeholder, label text, button text) and no `th` of `graph.chunks.table` contains `namespace`.

## Known Stubs

None. These are test files.

## Threat Flags

None. T-17-06: the files are complete now; later plans list any correction under "Test defects" and never remove an assertion.

## Self-Check: PASSED

- The five files exist; commits `d5fcedd`, `ef0b4fc`, `268874f` are ancestors of HEAD; `git rev-list --count 3f2c364..HEAD` was 3 before this SUMMARY commit.
