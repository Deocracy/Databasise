---
phase: 17-gui-mockup
plan: 04
subsystem: testing
tags: [gui, playwright, wave-0, tdd, query, compare, errors]
requires:
  - phase: 17-01
    provides: "ui fixture, MockUI helpers, mockup_path"
  - phase: 17-02
    provides: "window.__mock shell, embedded refusals catalogue"
  - phase: 17-03
    provides: "amended UI-SPEC and GUI requirement text (D-06, D-07, D-09)"
provides:
  - "test_gui_04_query_mode.py: GUI-04 row node and five focused nodes"
  - "test_gui_05_compare.py: GUI-05 row node and five focused nodes"
  - "test_gui_06_errors.py: GUI-06 row node, catalogue node, per-screen shape node (6 cases), branching node"
affects: [17-06, 17-07, 17-08, 17-09, 17-10, 17-11, 17-12]
key-files:
  created:
    - databasise/tests/gui/test_gui_04_query_mode.py
    - databasise/tests/gui/test_gui_05_compare.py
    - databasise/tests/gui/test_gui_06_errors.py
  modified: []
key-decisions:
  - "Compare rows: query.rowN.kind is a select with option labels Default, Alias, Capability, Harness (matches 17-07 Task 1 text); tests use select_option(label=...)"
  - "The branching node sends a 422 body carrying both refusal_type and detail, so it proves refusal_type wins over the detail array"
requirements-completed: []
duration: one executor session
completed: 2026-10-30
status: complete
commits: 2
plan_head_before: 0e326a671d4d4ab25afd9ffd9229948d8823471f
plan_head_after: 412b6c2d3667d5480bae4af3e642c29b41acb1ff
actuals:
  tokens: 5250
  tasks: 2
  commits: 2
---

# Phase 17 Plan 04: Wave 0 Query, Compare and error-shape checks Summary

Three complete Wave 0 test files (21 collected nodes) pin the Query & Compare ids, the verbatim strings, the `window.__mock` hooks and the amended rules D-06, D-07 and D-09; against the shell-only mockup 20 fail on a missing hook or id and the catalogue node passes.

Requirements GUI-04, GUI-05 and GUI-06 are NOT marked complete here; the orchestrator records the ledger rows.

## Test results

`DATABASISE_REQUIRE_BROWSER=1 databasise/.venv/bin/python -m pytest -q <the three files> -p no:cacheprovider`:

- test_gui_04_query_mode.py: `6 failed`, no ERROR line.
- test_gui_05_compare.py plus test_gui_06_errors.py: `14 failed, 1 passed` (the passing node is `test_refusal_catalogue_matches_the_code_and_the_mockup`), no ERROR line.
- `--collect-only` on the 05 and 06 files: `15 tests collected`. `ruff check` on the three files: clean.
- `grep -c "^def test_"` on the 05 file prints 6; `__subclasses__` appears in the 06 file; no hard-coded `51` (D-09).

First failure line of the GUI-04 row node `test_gui_04_query_mode_blocks_and_states`: `playwright._impl._errors.TimeoutError: Locator.fill: Timeout 3000ms exceeded. ... waiting for locator("[data-mock-id=\"query.text.input\"]")`.

First failure of the GUI-05 row node: `Locator.click: Timeout 3000ms exceeded` waiting for the `query.mode.compare` / compare id. GUI-06 nodes fail with `Page.evaluate: Error: <screen> has no inject` (an unregistered `window.__mock` screen hook).

## Fail-first bases

All three files were added after `0e326a6` and failed (or, for the catalogue node, passed) in the commit that added them.

- GUI-04 row node `test_gui_04_query_mode_blocks_and_states`: tests added at `cc62d73` (parent `0e326a6`); all 6 nodes of the file fail there.
- GUI-05 row node `test_gui_05_compare_keys_columns_and_narrow_tabs`: tests added at `412b6c2` (shell-only mockup, same as `cc62d73`); fails.
- GUI-06 row node `test_gui_06_four_error_shapes_and_catalogue`: tests added at `412b6c2`; fails on the first `inject`. Its catalogue half already holds (the node's first statement passes).

## Commits

- `cc62d73` test(17-04): Wave 0 GUI-04 query mode checks
- `412b6c2` test(17-04): Wave 0 GUI-05 compare and GUI-06 error checks

## Deviations from Plan

None - plan executed as written. Judgment calls inside the plan's freedom:

- The GUI-04 row node asserts the `Enter an alias, or choose Default.` message between the two hash cases (a spec'd message, UI-SPEC Client-side blocks) so the second hash case proves the error re-evaluates.
- The `Tier` column index in the evidence table is read from the `thead th` texts instead of being hard-coded.
- The catalogue helper also asserts the runtime set is non-empty.

## Contract notes for the screen plans (not deviations)

- `query.rowN.kind` must be a `<select>` with option labels `Default`, `Alias`, `Capability`, `Harness`; `query.rowN.capability` a multi-select accepting the same token values as `query.selector.capability`.
- `query.selector.kind-<kind>` must be radios (tests call `check()`); `query.advanced.toggle` is the clickable `<summary>` that opens `query.advanced.panel`.
- Evidence and token tables need `thead th` headers with the literal text `Tier` (evidence), and visible-row filtering relies on hidden slots being `hidden` rows.
- The two result pieces of text `No trace token on this result.` and `A partial run cannot be promoted.` must be visible text nodes (found with `get_by_text(...).filter(visible=True)`).

## Known Stubs

None. These are test files.

## Threat Flags

None.

## Self-Check: PASSED

- The three files exist; commits `cc62d73` and `412b6c2` are ancestors of HEAD; `git rev-list --count 0e326a6..HEAD` was 2 before this SUMMARY commit.
