---
phase: 18-gui-live
plan: 05
subsystem: ui
tags: [console, compare, alias-catalogue, abort-controller, error-shapes, playwright]

requires:
  - phase: 18-gui-live
    provides: "api(), InFlight, Live, WIRED, setDisabled, ensureRows, SessionLog (18-03, 18-04); QueryScreen.renderResult/showState and the run history (18-04)"
provides:
  - "js/21-compare.js: live Compare.run (one POST /compare, Default as {}), bare-versus-map parsing by the number of selectors sent, per-column trace tokens, extra server keys as cloned columns, Compare.cancel and Compare.hideColumns"
  - "js/10-shared.js: AliasCatalog (rows, source, load, byAlias, event aliases), fillAliasPicker, the alias branch of Resolution, live Picker options"
  - "js/20-query.js: QueryScreen.applyResponse, remember and cancel exported; WIRED query GET /ledger/aliases"
  - "databasise/tests/gui_live/test_live_02_query_compare.py (compare and alias catalogue tests) and test_live_03_errors.py (compare error cases)"
affects: [18-06, 18-09, 18-10, 18-11, 18-gui-live]

actuals:
  tokens: 12400
  tasks: 3
  commits: 8
plan_head_before: d82b3ff80798b7de83aa4a6c3b2d2f4c7f07b1ea
plan_head_after: 8a61a437b87e687ec8d0aa894f7c639334b8a471

tech-stack:
  added: []
  patterns:
    - "A compare answer is parsed by the number of selectors sent, never by inspecting keys; columns are read by the selector's own comparison key (a key named 'answer' is a column)"
    - "Columns past the four literal ones are clones of the last panel and tab whose ids get renumbered through setAttribute; one delegated listener on query.compare.columns serves all of them"
    - "Compare-mode Run is owned by Compare (blockers or in flight); QueryScreen.showState leaves it alone in compare mode and hides the columns"
    - "AliasCatalog is the one alias source: GET /ledger/aliases when in the spec, else the newest entry per alias of the sessionStorage ledger log; pickers refill on the aliases event"

key-files:
  created: []
  modified:
    - databasise/console/src/js/21-compare.js
    - databasise/console/src/js/20-query.js
    - databasise/console/src/js/10-shared.js
    - databasise/console/src/js/90-start.js
    - databasise/console/operator-console.html
    - databasise/tests/gui_live/test_live_02_query_compare.py
    - databasise/tests/gui_live/test_live_03_errors.py
    - .planning/phases/17-gui-mockup/17-REVIEW-DISPOSITION.md

key-decisions:
  - "Only the requested columns are written to the run history; a key the server added is shown as a column but is not a run this console made, so it has no selector to record"
  - "Compare history entries are added last column first, so the newest-first history reads in builder order"
  - "The no-token reason for a compare column reuses the column's no-promote line (text set per render: partial note or 'No trace token on this result.') and the button title"
  - "data-live-ready is set after AliasCatalog.load() resolves, so a picker is filled when a test or an operator first looks"
  - "A column header reads 'key' when the arm is unknown (an alias) and 'key . arm' when the embedded table knows it"

requirements-completed: []

duration: about 1 h 15 min
completed: 2026-10-31
status: complete
---

# Phase 18 Plan 05: Compare mode on the live API and the alias catalogue Summary

**Compare runs against the real server: one `POST /compare` per run, Default sent as `{}`, a bare envelope for one selector and a map read by comparison key for two or more (a key named `answer` is just a column), per-column trace tokens, extra server keys as cloned columns, blocker re-check, abort on mode switch or screen leave, and every picker listing `alias (active_version)` from `GET /ledger/aliases` or the browser's ledger log.**

## Accomplishments

- `Run compare` sends `{query: {text}, selectors}`; a Default row is `{}`, never `null` (Pitfall 1). With two or more selectors each column is filled from `body[comparisonKey(selector)]`; with one the answer goes through `QueryScreen.renderResult` as a bare envelope. The count sent decides, so an alias literally named `answer` renders as a column (tested with a promoted alias `answer`).
- Each column's Open trace, Promote this arm and Open (evidence row) use that column's own envelope through one delegated listener, so cloned columns work too. The `open-evidence` payload is `{ref: <EvidenceRef unchanged>, score, trace_token}`. Evidence rows past five are cloned with `ensureRows`.
- Column Open trace is disabled (no `href`, `aria-disabled`) and Promote this arm is disabled with `No trace token on this result.` (title and the column's note line) when that column's token is null; a partial run keeps `A partial run cannot be promoted.` (IN-JSA-08, compare half).
- `Compare.run` re-checks `update()` (row blockers, duplicate key, zero rows) and `InFlight.counts.compare` before sending, so a button enabled by a script still sends nothing (WR-JSA-02).
- `QueryScreen.showState` no longer touches Run in compare mode and hides the compare columns; a successful compare uses `hideStates()` then `showColumns()`. Exactly one view is visible (WR-JSA-03).
- A mode switch (`setMode` calls `QueryScreen.cancel()` and `Compare.cancel()` when the mode changes) and leaving the screen (`Console.on("show")`) abort both reads; an aborted run renders nothing and adds no history row (WR-JSA-04).
- Server keys the console did not send are appended as columns inside `.cmp-scroll`; the builder cap of 4 is unchanged. Five columns were tested (three extras), including the 5th column's Open payload.
- `AliasCatalog` (`rows`, `source`, `load`, `byAlias`, event `aliases`): `GET /ledger/aliases` rows when in the spec, else the newest entry per alias of `databasise.console.ledger-log`. Every `Picker` and the four compare row pickers are filled by `fillAliasPicker` with `alias (active_version)`; under the log source a muted `From this browser's ledger log; no route lists aliases.` line sits next to the select. For an alias in the catalogue `Resolves to` reads `alias <name>, active version <v>; the server resolves the arm at run time`; the fixture alias merge is deleted.
- Compare error shapes go through `QueryScreen.applyResponse`: typed refusal (`DuplicateComparisonKeyError`, HTTP 422), validation list with the offending row's `query.rowN.kind` marked and `query.rowN.error` filled (row `data-field-loc` and `data-error-id` are set at init through `setAttribute`), and the generic 500.

## Task Commits

1. Task 1 RED `b29644e` test(18-05): failing keyed-map compare test
2. Task 1 GREEN `684b8e6` feat(18-05): live keyed-map compare with per-column tokens
3. Task 1 disposition `4cc4b72` docs(18-05): WR-JSA-06 fixed in Phase 18
4. Task 2 RED `9775b19` test(18-05): failing compare parsing, blocker and abort tests
5. Task 2 GREEN `a7e44f6` feat(18-05): compare parsing, blocker re-check and abort on mode switch
6. Task 2 disposition `ae96675` docs(18-05): WR-JSA-02, 03, 04 and IN-JSA-08 fixed in Phase 18
7. Task 3 RED `7b85d2b` test(18-05): failing alias catalogue and compare error tests
8. Task 3 GREEN `8a61a43` feat(18-05): live alias catalogue for every picker and compare error shapes

## Fail-first proof

- RED commit `b29644e` proves LIVE-02 (compare, keyed map and per-column tokens): the tracer failed with a timeout waiting for `POST /compare`, which the mockup path never sent. After `684b8e6` it passes. The tracer gate (the Task 1 `<verify>` re-run) passed, so the plan expanded.
- RED commit `9775b19` proves LIVE-02 (compare blockers, aborts, one view, extra keys, IN-JSA-08): 7 of 9 new tests failed (`default_row` as first written, `rechecks_blockers`, `mode_switch_aborts_the_pending_query`, `leaving_the_screen`, `only_one_view`, `promote_disabled_without_trace_token`, `extra_server_key`). `test_compare_one_selector_is_parsed_as_a_bare_envelope` and `test_mode_switch_aborts_the_pending_compare` passed on arrival, because the Task 1 build already handled a bare envelope and `sync()` already aborted the compare on a mode change. `test_compare_default_row_is_sent_as_an_empty_object` failed first on my own assertion about the server answer (Default plus a capability set refuses on this store); I loosened it to what the plan states (`selectors[0] == {}` and no validation view) before the RED commit, so it too passed on arrival. After `a7e44f6` all pass.
- RED commit `7b85d2b` proves LIVE-07 (alias catalogue) and LIVE-03 (compare errors): the two alias tests failed (fixture labels). The three compare error tests passed on arrival: Task 1's `applyResponse` path and the init-time `data-field-loc` already produced the shapes. After `8a61a43` all 5 pass.
- LIVE-02, LIVE-03 and LIVE-07 are not marked complete here; the rows close in plan 18-11.

## Verification

- `test_live_02_query_compare.py`, `test_live_03_errors.py`, `test_live_01_serving.py`: 47 passed (wheel test included).
- `test_live_09_badges_ids.py`: 16 passed and the same 5 red-by-design nodes as in 18-04 (badge counts and badge-kept for `operator` and `operator-log`, and `test_no_live_button_is_labelled_run_or_submit`: 18-11 and 18-08). The query-scope operator-route badges for the alias pickers (1 selector plus 4 compare rows) now drop, as the plan's WIRED key requires.
- `mockups/build.py --check`, the live-console `--check` and `scripts/mockup-id-check.py --root .` all exit 0 with no output.
- Acceptance greps: `"/compare"` 1 in `21-compare.js`; `Run compare` 1 in `20-query.js`; `var AliasCatalog` 1; `the server resolves the arm at run time` 1; `WIRED["query GET /ledger/aliases"]` 1; five `fixed in Phase 18 (18-05)` rows (WR-JSA-02, 03, 04, 06, IN-JSA-08). No `FIX.`, timer or `innerHTML` use in `21-compare.js` or `20-query.js`.
- Not checked: the 375 px layout of five compare columns and the tab bar (the tab row only shows below 768 px); no screenshot was taken.

## Deviations from Plan

**1. [Rule 3 - Blocking] Disposition edits in separate docs commits**
- **Found during:** Task 1 commit. The lefthook `no-planning-in-code-commit` hook refuses a commit that mixes `.planning/` files with other files, so the plan's "same commit" rule (D-16) cannot be met. Same as 18-04.
- **Fix:** the disposition rows are the docs commits right after the GREEN commits (`4cc4b72`, `ae96675`).

**2. [Discretion] Compare spec step 7 was already in place**
- The plan's Task 3 step 7 (row `data-field-loc` and `data-error-id` set at init through `setAttribute`) was already in `21-compare.js` from Phase 17. I kept it and added a comment. Row blocker messages now go through `setFieldError(kind control, msg)` so a blocker and a server field error share one element and one `aria-invalid`.

**3. [Discretion] Extra tests beyond the plan list**
- `test_mode_switch_aborts_the_pending_query` and `test_leaving_the_screen_aborts_the_pending_compare` (WR-JSA-04 for the Query direction and the screen-leave half), and `test_alias_picker_falls_back_to_the_client_log` (log source, newest version per alias, no `GET /ledger/aliases`) with a `plain_app` module fixture started without `--operator`. The last one pre-seeds `sessionStorage` with the entry shape 18-09 writes (`{alias, version, record_kind, generation_ordinal, created_at}`); if 18-09 changes that shape this test is the first to show it.

**4. [Process] One no-op heredoc**
- I ran `cat >> /dev/null <<'EOF'` with an empty body once, by habit. It wrote nothing and no file was created through a heredoc. Two later shell commands were rejected by the BAK hook (a `|` inside a grep pattern, and one with the word that is forbidden); I re-ran them without those.

**Total deviations:** 1 blocking fix, 2 discretion calls, 1 process slip. **Impact:** none on behavior.

## Notes for the later plans

- 18-06 (Evidence): `Compare` emits the same `open-evidence` payload as Query, `{ref, score, trace_token}`, and `open-trace` as `{token}`. 30-evidence.js still reads the Phase 17 shape and `FIX.compare` (line 38); this plan did not touch it.
- 18-09 (Ledger): the `promote` event from a compare column carries `{trace: token}` as before. `AliasCatalog.load()` is the call to make after a ledger write, and the log shape above is what the fallback reads. `60-ledger.js` still uses `FIX.aliases` for its own alias list.
- `Resolution.resolve` still returns `arm: null` for catalogue aliases, so a compare column header for an alias shows only its key.

## Known Stubs

- An extra (server-added) column shows `Resolves to: unknown here (needs backend)` and is not written to the run history, because the console holds no selector for it.
- The history table's Partial column still shows a dash for every row (inherited from 18-04).

## Threat Flags

None. T-18-13: option labels, column headers, tab text and the alias note use `textContent` only (`h()`, `fillAliasPicker`, `fillHeader`, `selectTab`). T-18-14: one `AbortController` per read; an aborted or superseded result returns before any render, history write or state change.

## Self-Check: PASSED

- Modified files present; commits b29644e, 684b8e6, 4cc4b72, 9775b19, a7e44f6, ae96675, 7b85d2b and 8a61a43 are ancestors of HEAD.
