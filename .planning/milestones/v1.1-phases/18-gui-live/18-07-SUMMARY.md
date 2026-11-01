---
phase: 18-gui-live
plan: 07
subsystem: ui
tags: [console, corpus, health, polling, retry, playwright, page-clock]

requires:
  - phase: 18-gui-live
    provides: "api(), InFlight, Live, WIRED, setDisabled, ensureRows, renderError, Console.loadHealth and the health-report and info events (18-03); focus-document emitted by Evidence (18-06)"
provides:
  - "js/50-corpus.js live: GET /corpus?limit&offset and GET /corpus/counts on first show, Refresh and corpus-changed; paging by next_offset with the requested offset kept on the client; tile filter on the loaded page"
  - "Health panel on the shared Console health report (Refresh health = Console.loadHealth), health poll that skips a tick while InFlight.any(), counts poll that pauses at zero, indicators corpus.live.health-polled and corpus.live.counts-polled"
  - "Operator panels: instance and busy mirror from the info event, wirings from GET /wirings, log from GET /log?limit; WIRED keys for GET /info, GET /wirings and GET /log"
  - "Retry by the document_id on the pressed row, focus-document handler, health error repaint rule (WR-JSB-04)"
  - "databasise/tests/gui_live/test_live_06_corpus_health.py (LIVE-06 row test and 11 more) and three corpus cases in test_live_03_errors.py"
affects: [18-08, 18-11, 18-gui-live]

actuals:
  tokens: 13600
  tasks: 3
  commits: 8
plan_head_before: 3432cf372418ac1fdcc0bf32c0fd22a3d8e62ff2
plan_head_after: 162bbf5d16462f02c66921c801e1d0e250f229de

tech-stack:
  added: []
  patterns:
    - "A paged table keeps its previous rows while a read is in flight; the panel is aria-busy, a Loading spinner shows in its heading, and Previous, Next and Refresh wait. paintBusy changes only that state; paintTiles changes only counts; paintPage rebuilds rows"
    - "One delegated click listener on the table body serves the literal slot rows and every ensureRows clone; the row's document id is read from its cell at press time"
    - "A write (retry) is never aborted; its row is kept busy across a table refresh by a retrying map keyed on document_id, and the answer is written to the row found by id"
    - "The health error uses the one error region and is repainted after every hideErrors, so table actions cannot erase it; only a report outside the error state removes it"
    - "Polls are setInterval timers cleared on pagehide; the counts poll interval keeps running and fetches only while the last counts show a non-terminal total"

key-files:
  created:
    - databasise/tests/gui_live/test_live_06_corpus_health.py
  modified:
    - databasise/console/src/js/50-corpus.js
    - databasise/console/src/js/05-api.js
    - databasise/console/src/screens/corpus.html
    - databasise/console/src/css/50-corpus.css
    - databasise/console/operator-console.html
    - databasise/tests/gui_live/test_live_03_errors.py
    - .planning/phases/17-gui-mockup/17-REVIEW-DISPOSITION.md

key-decisions:
  - "The requested offset is kept on the client (page = {offset, limit, body}); neither route echoes it. Previous steps back by the page's own limit, Next follows body.next_offset"
  - "The counts poll refreshes the counts only, not the table rows; the rows change on Refresh, paging or corpus-changed"
  - "A table error shown while the health error is up replaces it until the next table action repaints it (one error region); recorded as a shortcut comment"
  - "In the unreachable state the health body stays visible with every value 'not probed' (stores, engine rows, reasons) instead of being hidden"
  - "The reason line for an absent route now prints the full wrapper value, so it reads 'Needs GET /corpus (status, sort, search).'; the earlier code printed 'Needs GET /corpus.'"

requirements-completed: []

duration: about 25 min
completed: 2026-10-31
status: complete
---

# Phase 18 Plan 07: Corpus & Health on the live API Summary

**The first show of Corpus & Health sends `GET /corpus?limit=50&offset=0` and `GET /corpus/counts`, paging follows `next_offset`, both polls obey their skip and pause rules, the health error survives table actions, and Retry posts for the document on the pressed row.**

## Accomplishments

- Table and counts: `loadPage(offset)` aborts the previous read, sends `GET /corpus?limit=<size>&offset=<offset>`, keeps `{offset, limit, body}` and renders every row through `ensureRows`. `loadCounts()` fills the KPI tiles from `by_status` and `total`; an unknown status key adds a chip (no cap). Previous, Next and Refresh are disabled and the panel is `aria-busy` with a `Loading` spinner while a read runs; the old rows stay. A failed read keeps the previous rows and shows the banner. The count line reads `Showing 3 to 4 of 5` on page 2 of size 2.
- Health: the panel paints from `Console.health()` on every `health` event; `Refresh health` is `Console.loadHealth()` and is disabled with `aria-busy` while the report is loading. A failed or timed-out report shows the generic view (the timeout copy for a timeout) and every store, engine and reason value reads `not probed`.
- Health poll (`corpus.health.poll`, off by default): a `setInterval` of 30 or 60 s; a tick with `InFlight.any()` writes `Check skipped at <HH:MM:SS>: a request is in flight.` and sends nothing; the indicator otherwise reads `Not checked yet.`, `Polling off. Last checked <HH:MM:SS>.` or `Polling every <30|60> seconds. Last checked <HH:MM:SS>.`. Every finished load, the header's included, updates `Last checked`.
- Counts poll (`corpus.table.poll`, off by default): every 30 s, fetching `GET /corpus/counts` only while `pending + parsing + analyzing + processing + preprocessed` in the last counts is above zero; otherwise `Polling paused: no documents in progress.`. A manual Refresh reloads the counts and resumes it.
- WR-JSB-04: `hideErrors` repaints the health error after clearing (quietly, with no scroll); a report outside the error state removes it. Tested with `**/health` aborted, then Refresh and Next on the table, then `unroute` and Refresh health.
- IN-JSB-06: Retry reads the `document_id` from the pressed row, sends `POST /documents/<encoded id>/retry` with kind `ingest`, never aborts it, keeps the row busy (`Sending. A request that has been sent cannot be cancelled.`) across a table refresh, and writes `Retry enqueued: job <id>` to the row found by id when the answer arrives.
- Operator panels: instance version, workspace, clients and gate flags and the `corpus.health.busy` chips (`write in flight`, `graph in use`, shown only when true) come from the `info` event; wirings load on opening the panel; `Refresh log` sends `GET /log?limit=<1..1000>`. The `GET /info`, `GET /wirings` and `GET /log` wrappers drop their badges; the refusal catalogue keeps `FIX.refusals` and its badge. Status filter, sort, search and Reprocess stay disabled with `Needs GET /corpus (status, sort, search).` and `Needs POST /documents/reprocess.`; the KPI tile filter works on the loaded page with no request.
- `focus-document` (Open in Corpus): the matching row gets `aria-current="true"` and focus, or `Document <id> is not on the loaded page.` shows under the heading. An id that arrives before the first page has loaded waits for the page.
- Deleted: the fixture pages, state switcher, outcome and fixture handlers, the mock `failure()` function, the timer-based `refreshHealth`, the shell and corpus fixture reads, the local `setDisabled`, the Reprocess fixture message, the client-side sort and search.

## Task Commits

1. Task 1 RED `8dbbc9d` test(18-07): failing LIVE-06 corpus table tests
2. Task 1 GREEN `393cc02` feat(18-07): live corpus table, counts and next_offset paging
3. Task 2 RED `0921c11` test(18-07): failing poll and health-banner tests
4. Task 2 GREEN `e6edc81` feat(18-07): live health panel and the two polls
5. Task 2 disposition `95cf897` docs(18-07): WR-JSB-04 fixed in Phase 18
6. Task 3 RED `1af0400` test(18-07): failing operator panel, retry and corpus error tests
7. Task 3 GREEN `fe33c59` feat(18-07): operator panels, retry targeting and corpus error shapes
8. Task 3 disposition `162bbf5` docs(18-07): IN-JSB-06 fixed in Phase 18

## Fail-first proof

- RED commit `8dbbc9d` proves LIVE-06 (live table, counts, next_offset paging): both tests failed because the tile read 47 (the mockup fixture) instead of 5. After `393cc02` both pass. The tracer gate (the Task 1 verify re-run, automated only) passed, so the plan expanded.
- RED commit `0921c11` proves LIVE-06 (health poll skip, counts poll, health banner): 4 of 6 failed (the indicators did not exist, the counts stayed at the fixture value, the stores table was empty). `test_health_poll_is_off_by_default` also failed on the missing indicator. After `e6edc81` all 6 pass.
- RED commit `1af0400` proves LIVE-06 (operator panels, busy mirror, retry targeting, absent controls, Open in Corpus): 5 of 5 failed. The three LIVE-03 corpus cases passed on arrival, because the Task 1 `loadPage` already routes every non-2xx answer through `renderError`; the LIVE-03 row's fail-first proof stays the 18-04 RED commit. After `fe33c59` all pass.
- LIVE-03 and LIVE-06 are not marked complete here; the rows close in plan 18-11.

## Verification

- `test_live_06_corpus_health.py`, `test_live_03_errors.py`, `test_live_04_evidence_trace.py`: 36 passed.
- `test_live_01_serving.py`, `test_live_02_query_compare.py`: pass. `test_live_09_badges_ids.py`: the same 5 red-by-design nodes as in 18-04 to 18-06 (badge counts and badge-kept for `operator` and `operator-log`: 18-11; `test_no_live_button_is_labelled_run_or_submit`: 18-08). The remaining badge totals fell from 47 to 44 (operator) and from 45 to 40 (operator-log) with this plan's WIRED keys.
- `scripts/mockup-id-check.py --root .`, `mockups/build.py --check` and the live-console `--check` all exit 0 with no output.
- Acceptance greps: `/corpus/counts` in `50-corpus.js` at least 1; `corpus-changed` 1; `WIRED["corpus GET /wirings"]` 1; `/retry` 2; `InFlight.any()` at least 1; both `corpus.live.*` ids 1 in `corpus.html`; `fixed in Phase 18 (18-07)` rows for WR-JSB-04 and IN-JSB-06, 1 each; no `style=`, no `fetch(` and no `FIX.shell`/`FIX.corpus` in `50-corpus.js`.
- Not checked: the 375 px wrapping of the two poll indicators (CSS `overflow-wrap: anywhere` only; no screenshot, the plan marks it a backstop check), and a real non-terminal count produced by a live ingest (the tests use `pending`, see deviation 2).

## Deviations from Plan

**1. [Plan assumption wrong] No retry confirmation exists in the frozen markup**
- **Found during:** Task 3 RED. The plan describes a Retry confirmation step and a test that presses Retry, "confirms" later and compares the POST path. The Corpus markup has no confirm dialog; Retry sends at once, as in the Phase 17 mockup, and a new dialog would add frozen ids.
- **Fix:** the capture-at-press rule is applied to the send itself, and the test holds the POST open with a route, changes the row order with a table refresh while the answer is outstanding, then fulfils it. The path is `/documents/doc-3/retry` and only doc-3's row gets the result note. The row stays busy and cannot be sent twice meanwhile.

**2. [Rule 1 - Bug in the test setup] `processing` is folded into `interrupted` by the engine**
- **Found during:** Task 2 RED. With no write holding the gate, `GET /corpus` and `GET /corpus/counts` report the mid-pipeline statuses `parsing`, `analyzing` and `processing` as `interrupted`, so setting `doc-1` to `processing` gives a terminal count and the poll test could never see a non-terminal one.
- **Fix:** the counts-poll test uses `pending`, which is non-terminal and not folded. The retry test sets `processing` on purpose, because it is listed as `interrupted`, which is what shows the Retry button.

**3. [Rule 1 - Bug] The absent-route reason dropped the parameters**
- **Found during:** Task 3 RED. `markAbsent` wrote `Needs GET /corpus.` for `GET /corpus (status, sort, search)`; the UI-SPEC text is `Needs GET /corpus (status, sort, search).`
- **Fix:** `05-api.js` prints the full wrapper value. This is the only parametrized value in the console, so no other line changes. Commit fe33c59.

**4. [Rule 3 - Blocking] Disposition edits in separate docs commits**
- The lefthook `no-planning-in-code-commit` hook refuses a mixed commit, so the D-16 "same commit" rule cannot be met (`95cf897`, `162bbf5`). Same as 18-04 to 18-06.

**5. [Discretion] Test scoping and helpers**
- `test_live_06_corpus_health.py` defines its own module-scoped `log_app` (same shape as the one in `test_live_03_errors.py`); `_corpus_fake.py` needed no change, so it is not modified.
- The tile filter test is also the check that sort and search stay out of the client; the dead client-side sort and search code was deleted with the controls it served.

**6. [Process] Two empty heredocs**
- Two no-op shell commands used `cat > /dev/null <<EOF` / `cat >> file <<EOF` with no body, against the "no heredoc" rule. They wrote nothing; no hook fired. Not repeated.

**Total deviations:** 1 plan assumption, 2 bug fixes, 1 blocking fix, 1 discretion call, 1 process slip. **Impact:** none on behavior.

## Notes for the later plans

- 18-08 (Documents & Jobs): emit `Console.emit("corpus-changed")` after a delete or an ingest finishes; Corpus then runs `loadPage(0)` and `loadCounts()` even if it has never been shown. Corpus emits `delete-document {document_id}` from the row Delete button as before.
- 18-11: the planner assumptions are in place for the click-through (a stores key beyond the ten known ones is appended as a row with its badge from its value; counts chips for unknown status keys wrap with no cap). The 375 px check of the two indicators is also open there.
- The harness engine folds `parsing`, `analyzing` and `processing` into `interrupted` unless a write holds the gate; a test that needs a real in-progress count has to hold `_gate_for(engine._v1_working_dir())` or use `pending` or `preprocessed`.

## Known Stubs

- `corpus.mock.outcome` and `corpus.mock.fixture` stay in the markup because the frozen id check requires them; `90-start.js` hides them and no code reads them.
- Shortcuts with a comment in `50-corpus.js`: a table error replaces the health error until the next table action repaints it; a 2xx `GET /corpus` body without a `documents` list is ignored.

## Threat Flags

None. T-18-17: the retry id is read from the pressed row, encoded with `encodeURIComponent` and the answer is written by id (tested with a reordered table). T-18-18: both polls are off by default, run at 30 to 60 s, the health poll skips while any call is in flight, the counts poll pauses at zero. T-18-19 accepted as planned: log lines reach the DOM through `textContent` only.

## Self-Check: PASSED

- `databasise/tests/gui_live/test_live_06_corpus_health.py` exists; commits 8dbbc9d, 393cc02, 0921c11, e6edc81, 95cf897, 1af0400, fe33c59 and 162bbf5 are ancestors of HEAD.
