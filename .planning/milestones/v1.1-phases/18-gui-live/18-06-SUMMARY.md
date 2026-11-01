---
phase: 18-gui-live
plan: 06
subsystem: ui
tags: [console, evidence, trace, session-cache, abort-controller, debug-rerequest, playwright]

requires:
  - phase: 18-gui-live
    provides: "api(), Live, WIRED, setDisabled, SessionLog, renderError (18-03); Query and Compare open-evidence payload {ref, score, trace_token} and open-trace {token} (18-04, 18-05)"
provides:
  - "js/30-evidence.js: live POST /evidence/resolve with a per-session (namespace, ref) cache and AbortController, live POST /trace/resolve with the Debug re-request, inspector Open trace bound to the originating run, recent-runs picker (browser history plus GET /traces), Open in Corpus for full_doc_id records, event focus-document"
  - "databasise/tests/gui_live/test_live_04_evidence_trace.py (LIVE-04 row test and 7 more) and four Evidence & Trace cases in test_live_03_errors.py"
affects: [18-07, 18-10, 18-11, 18-gui-live]

actuals:
  tokens: 9000
  tasks: 3
  commits: 6
plan_head_before: 8835425
plan_head_after: c57b29c7e9a2f58aac6ab0c18d7dbc502e192d5d

tech-stack:
  added: []
  patterns:
    - "One AbortController per read (evidence, trace); every abort path (new open, tab switch, leaving the screen) restores the Open button next to the abort() call"
    - "The origin trace token travels with the open (payload.trace_token) and is kept per displayed record; a lookup carries none"
    - "A debug trace is a template clone shown only when the checkbox is on and the loaded trace was read with debug; every toggle re-requests with the current flag"
    - "Reason text that duplicates another screen's literal is written into the DOM only while it applies"

key-files:
  created:
    - databasise/tests/gui_live/test_live_04_evidence_trace.py
  modified:
    - databasise/console/src/js/30-evidence.js
    - databasise/console/src/screens/evidence.html
    - databasise/console/operator-console.html
    - databasise/tests/gui_live/test_live_03_errors.py
    - .planning/phases/17-gui-mockup/17-REVIEW-DISPOSITION.md

key-decisions:
  - "An unresolvable ref (404 UnresolvableEvidenceReferenceError) shows both evidence.state.refusal (the UI-SPEC banner) and the typed error banner with its HTTP footer; every other refusal shows the typed banner only"
  - "The picker is refreshed on every entry to the Evidence screen (fresh SessionLog read plus one GET /traces), with a sequence counter so an older response cannot append after a newer refresh"
  - "A real node carries tier and feed_tier, so the node table shows them and the fixture 'placeholder' badges are gone"
  - "The inspector's no-token reason is empty until a record is shown (Query's strict text lookups would otherwise match it twice)"

requirements-completed: []

duration: about 15 min
completed: 2026-10-31
status: complete
---

# Phase 18 Plan 06: Evidence & Trace on the live API Summary

**Open on a live evidence row sends the envelope's EvidenceRef to `POST /evidence/resolve` unchanged and caches the record per (namespace, ref) for the session; Load trace and every Debug toggle send `POST /trace/resolve` with the current flag; the inspector's Open trace loads the trace of the run the row came from.**

## Accomplishments

- `open-evidence` payload `{ref, score, trace_token}`: `payload.ref` is the request body as it came (same keys, values, order, never `id`). A hit in the cache shows the record at once with no request and no loading view; errors are not cached. The caption `Cached for this session by namespace and ref.` stays.
- `Manual lookup` sends `{ref, namespace, kind}` from its inputs through the same path and carries no trace token.
- Trace: `Load trace`, Enter and the Query/Compare/error-banner `Open trace` links send `{trace_reference, debug}`. Debug on re-requests with `debug: true` and clones the node-table template from the live record (real `tier`/`feed_tier`, null-safe token cells); Debug off removes the clone first and re-requests with `debug: false`.
- WR-JSB-01: the inspector link opens the origin token captured at open time (tested: query A, open its row, run query B, the link loads A). With no token the link has no `href`, `aria-disabled="true"` and the visible reason `No trace token on this result.`
- IN-JSB-08: a new open, a tab switch or leaving the screen aborts the read; nothing is shown for it, the loading view returns to idle and the Open button loses `aria-busy` and its `Opening` label (tested under `LiveApp.hold("resolve_evidence")`).
- IN-JSB-07: `Open in Corpus` is shown only for a record with `full_doc_id`, hidden for HippoRAG `document_id`; it shows Corpus & Health and emits `focus-document` with the id (18-07 handles it).
- Recent runs lists the browser history (selector label, time, token prefix) and, with `GET /traces` in the spec, the server's traces not already listed. The `GET /traces` wrapper in this screen drops its badge (`WIRED["evidence GET /traces"]`, `WIRED["evidence GET /log"]`). `Resolve all evidence` stays disabled with `Needs POST /evidence/resolve-batch.`; `evidence.batch.status` is empty and has `hidden`.
- Every non-2xx goes through `renderError("evidence", ...)`: UnknownTraceReferenceError and UnresolvableEvidenceReferenceError with HTTP 404, a validation 422 marking `body.ref`, a 500 generic view.
- Deleted: the fixture finder, the token-to-fixture scan, timers, the outcome handler, the batch fixture, `setState`/`loadFixture`/`inject`, the local `setDisabled`.

## Task Commits

1. Task 1 RED `fed824e` test(18-06): failing LIVE-04 evidence resolve test
2. Task 1 GREEN `25074e1` feat(18-06): live evidence resolve with a per-session cache
3. Task 2 RED `1c96a8f` test(18-06): failing trace, origin-link and abort tests
4. Task 2 GREEN `064bd80` feat(18-06): live trace, debug re-request and the origin trace link
5. Task 2 disposition `4c7b41c` docs(18-06): WR-JSB-01, IN-JSB-07 and IN-JSB-08 fixed in Phase 18
6. Task 3 `c57b29c` test(18-06): LIVE-03 evidence and trace cases

## Fail-first proof

- RED commit `fed824e` proves LIVE-04 (evidence resolve, unchanged ref, session cache): the test failed with a timeout waiting for `POST /evidence/resolve`, which the mockup path never sent. After `25074e1` it passes. The tracer gate (the Task 1 verify re-run) passed, so the plan expanded.
- RED commit `1c96a8f` proves LIVE-04 (trace, Debug re-request, origin link, Open in Corpus, abort, recent runs): 6 of 7 new tests failed. `test_resolve_all_evidence_is_disabled_with_its_route` passed on arrival because the 18-03 absent-route rule already disables the control and writes its reason. After `064bd80` all pass.
- The four LIVE-03 evidence cases passed on arrival (the Task 2 code already routes every non-2xx through `renderError`), so no separate RED commit exists for them; the LIVE-03 row's fail-first proof stays the 18-04 RED commit.
- LIVE-03 and LIVE-04 are not marked complete here; the rows close in plan 18-11.

## Verification

- `test_live_01_serving.py`, `test_live_02_query_compare.py`, `test_live_03_errors.py`, `test_live_04_evidence_trace.py`: 59 passed.
- `test_live_09_badges_ids.py`: 16 passed and the same 5 red-by-design nodes as in 18-04 and 18-05 (badge counts and badge-kept for `operator` and `operator-log`, and `test_no_live_button_is_labelled_run_or_submit`: 18-11 and 18-08).
- `scripts/mockup-id-check.py --root .`, `mockups/build.py --check` and the live-console `--check` all exit 0 with no output.
- Acceptance greps: `"/evidence/resolve"` 1, `u0001` 1, `"/trace/resolve"` 1, `WIRED["evidence GET /traces"]` 1 in `30-evidence.js`; `fixed in Phase 18 (18-06)` 3 in the disposition file; `def test_unknown_trace_reference_renders_its_typed_banner` 1.
- Not checked: the 375 px layout of the evidence inspector and the node table (no screenshot), and a real trace with a failed or halted node (the stub run has none; `data-row-state` logic is unchanged from Phase 17).

## Deviations from Plan

**1. LIVE-04 naive query substituted: the automated LIVE-04 test opens evidence and traces from a HippoRAG query instead of a naive query on a populated temp store.**
- The reason is 18-CONTEXT D-15 and 18-RESEARCH Open Question 1: the offline stub does not populate the LightRAG v2 stores, so a naive query on a temp store is refused.
- The owner walkthrough in 18-11 Task 2 opens evidence and traces on the default (LightRAG) path with real clients.
- REQUIREMENTS.md is not edited, which keeps the BAK S3 traces valid.

**2. [Rule 1 - Bug in my test] Request body compared as parsed pairs**
- **Found during:** Task 1 GREEN. The plan compares the post data with `json.dumps(evidence[0])`. JavaScript writes the score `1.0` as `1`, so the text differs while the keys, values and order are identical.
- **Fix:** the test parses the sent body with `object_pairs_hook`, checks the key order equals the envelope's, the values equal, and `id` is absent. Committed with the Task 1 GREEN commit (the RED commit still had the string form).

**3. [Rule 3 - Blocking] Disposition edit in a separate docs commit**
- The lefthook `no-planning-in-code-commit` hook refuses a mixed commit, so the D-16 "same commit" rule cannot be met (`4c7b41c`). Same as 18-04 and 18-05.

**4. [Rule 1 - Bug] Duplicate reason text broke an 18-04 test**
- **Found during:** regression run after Task 2. The inspector's hidden `No trace token on this result.` paragraph made Query's strict `get_by_text` match two elements in `test_promote_from_result_disabled_without_trace_token`.
- **Fix:** the note is empty in the HTML and written only while a record without a token is shown (`c57b29c`).

**5. [Discretion] Test scoping**
- The recent-runs badge assertion is scoped to `screen-evidence`: the Ledger picker has its own `GET /traces` wrapper that 18-09 wires.
- `Open in Corpus` is tested through the lookup form with a fulfilled `LightRAG` record, since the stub store has no LightRAG chunks.

**Total deviations:** 1 named substitution, 2 bug fixes, 1 blocking fix, 1 discretion call. **Impact:** none on behavior.

## Notes for the later plans

- 18-07 (Corpus): `Console.emit("focus-document", full_doc_id)` follows `Console.show("corpus")`; Corpus has no handler yet.
- 18-10 (Graph): `70-graph.js` still emits `open-evidence` as `{ref: {id, namespace, kind}}`. Evidence now sends `payload.ref` as the body, so that emit produces a 422 until 18-10 sends the real EvidenceRef.
- 18-09 (Ledger): the `promote` event from `Use trace in Ledger` is unchanged (`{trace}`). The run history key `databasise.console.history` is read fresh on each entry to Evidence.

## Known Stubs

- `evidence.mock.outcome` (the Phase 17 outcome select) stays in the markup because its frozen id is required by the id check; 90-start hides it and no code reads it.
- Recent runs shows no browser history when `sessionStorage` is blocked (a fresh `SessionLog` read cannot see another instance's memory list); noted as a `shortcut` comment in `refreshRecent`.

## Threat Flags

None. T-18-15: record content, trace fields, node cells, option labels and debug identities reach the DOM through `textContent` and `h()` only. T-18-16 accepted as planned.

## Self-Check: PASSED

- `databasise/tests/gui_live/test_live_04_evidence_trace.py` exists; commits fed824e, 25074e1, 1c96a8f, 064bd80, 4c7b41c and c57b29c are ancestors of HEAD.
