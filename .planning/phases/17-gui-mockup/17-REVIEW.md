---
phase: 17
status: issues_found
depth: standard
files_reviewed: 62
findings:
  critical: 0
  warning: 17
  info: 22
  total: 39
reviewed: 2026-10-30
method: 5 area reviewers + 1 adversarial verifier per area (workflow wf_11d5386c-5a0); every finding below was re-read against source and confirmed by the verifier
---

# Phase 17 Code Review

Scope: 62 source files changed in phase 17 (mockups/src/**, mockups/build.py, databasise/tests/gui/**, docs/gui/*), excluding the generated mockups/operator-console.html. Read-only review; no tests were run by the reviewers.

Duplicate: JSC-03 is the same defect as TST-03 (test_gui_11_graph.py:153).

## Warnings

### WR-BLD-01: Planned-item check matches the item text anywhere in the file, not inside the named planned list

**File:** `databasise/tests/gui/test_inventory_map.py:79`

For {"planned": "<screen>.planned.list", "item": ...} the test checks only that the planned id is in MOCK-IDS.json and that `value["item"] in mockup_text` (the whole 370 KB built file, including the inlined fixtures JSON, the JS and the CSS). It never checks that the item sits inside the element with that data-mock-id. Today all 22 items appear once and inside the correct list (checked by locating each item's nearest preceding data-mock-id), so the defect is latent.

**Failure scenario:** An item is removed from documents.planned.list while the same words remain in a fixture string, a button label, or another screen's planned list (for example 'Graph editing' moved from graph.planned.list to ledger.planned.list). The test still passes and the D-03 'every inventory control is stamped or planned' criterion is reported as met when the screen named in INVENTORY-MAP.json no longer lists it.

**Fix:** Use the `ui` fixture (or html.parser) to read the text of `[data-mock-id="<planned>"]` and assert `value["item"]` is in that element's text content, not in the raw file.

**Verifier:** Confirmed at test_inventory_map.py:79. The check is `value["item"] not in mockup_text` against the whole built file, and nothing ties the item to the element named by value["planned"]. If an item moves to another screen's planned list, or survives only in a fixture string or a label, the test still passes. The docstring (line 8-9) admits the verbatim-anywhere rule, but D-03 means the item is on that screen's planned list, so the check is weaker than the requirement. The defect is latent today.

### WR-JSA-01: Raw selector JSON accepts wrong member types, then Run throws an uncaught TypeError

**File:** `mockups/src/js/20-query.js:246`

validate() only checks that the raw JSON is a non-array object with at most one non-null key. It then returns that object as the selector. run() passes it to selectorLabel() (10-shared.js:28), which calls value.capability.join(...). Any capability value that is not an array therefore throws. Unknown keys and `{}` pass validation too, and selectorLabel falls through to `"harness " + value.harness`.

**Failure scenario:** Open Advanced query members and enter `{"capability":"reads_kv"}` as Raw selector JSON. Enter query text and click Run. selectorLabel throws `value.capability.join is not a function` at 20-query.js:302 before showState("running"). Nothing renders and the console shows an uncaught error. With `{}` or `{"foo":1}` the run succeeds, and Query history records the selector as `harness undefined`, which breaks the UI-SPEC label rule.

**Fix:** In validate(), accept only a known member: `alias` must be a string, `capability` an array of strings, `harness` a string. Treat an all-null object or `{}` as Default (null), or reject it with MSG.badJson. Do not hand an unvalidated object to selectorLabel.

**Verifier:** Confirmed. validate() at 20-query.js:244-246 checks only that the value is a plain object with at most one non-null key, then sets override = parsed. run() at line 302 calls selectorLabel(check.selector), and 10-shared.js:28 calls value.capability.join, which throws on a string. Input {} or {foo:1} falls through to 'harness ' + undefined, and that label is stored in history.

### WR-JSA-02: Compare.run has no blocker guard, and QueryScreen.showState re-enables Run in compare mode

**File:** `mockups/src/js/21-compare.js:336`

Compare-mode blockers (duplicate key, empty capability, empty or hash alias, zero rows) are enforced only by disabling query.run.submit in syncRun(). QueryScreen.showState (20-query.js:60) always calls setDisabled(run.submit, name === "running"). The mock state switcher, the fixture select and __mock.setState/inject all reach showState in compare mode without a later Compare.update(), so Run becomes enabled again. Compare.run itself only checks the query text.

**Failure scenario:** Switch to Compare and click Add selector. Two Default rows now show the duplicate-key warning and Run is disabled. Choose any value in the State switcher, for example `idle`. Run is enabled. Enter text and click Run. Two columns render, both keyed `default`, although the screen states the server refuses duplicate keys. An empty-capability row also reaches the unsatisfiable path, which renders UnsatisfiableSelectorError instead of EmptyCapabilitySelectorError.

**Fix:** At the top of Compare.run, recompute the blockers (model.length === 0, any blockerOf(...), any duplicate key) and return early with focus on the first row error. Also make QueryScreen.showState skip setDisabled while data-mode is compare, or call Compare's update() after it.

**Verifier:** Confirmed. QueryScreen.showState (line 60) always calls setDisabled(run.submit, name==='running'), and setState, reached from the state-switcher change handler, calls showState with no Compare.update() afterwards. Compare.run (21-compare.js:336-347) checks only the query text. Two Default rows have no blocker, so Resolution does not report 'not satisfiable' and two columns keyed 'default' render.

### WR-JSA-03: Query states render next to visible compare columns, so more than one state is shown at once

**File:** `mockups/src/js/20-query.js:52`

showState() and applyResponse() toggle the state views, result.panel and the errors box. They never hide query.compare.columns, which only Compare's hideColumns()/sync() hide. In compare mode, any Query-side render leaves the columns on screen. This breaks the rule in the comment on line 51 that exactly one state view is visible.

**Failure scenario:** Call __mock.loadFixture('query','cmp-3col'). Three columns are visible. Then select `refusal-422` (or `success`) in query.mock.state-switcher. The refusal banner, or the single-result panel, appears above the same three columns. A GUI test that checks only the banner's visibility still passes.

**Fix:** When data-mode is compare and the new state is not a compare render, have showState hide query.compare.columns. Alternatively, expose Compare.hideColumns and call it from applyResponse/setState.

**Verifier:** Confirmed. showState toggles only the state views, result.panel and errorsBox. query.compare.columns (query.html:230) is compare-only and is hidden only by Compare.hideColumns. The state views and result.panel carry no query-only class. In compare mode, setState('success') therefore shows the single-result panel above the visible columns.

### WR-JSA-04: A mode switch cancels only Compare's timers; a pending Query run still fires in compare mode

**File:** `mockups/src/js/21-compare.js:415`

sync() calls cancel(), which clears only Compare's own timers, and then QueryScreen.showState('idle'). The 800 ms timer and the streaming timers that QueryScreen.run() queued (20-query.js:305, 281, 285) stay pending. They later call finish()/renderResult() and remember().

**Failure scenario:** In Query mode, enter text and click Run. Within 800 ms, click the Compare tab. The screen shows idle, then the query-mode single result appears in compare mode, Run is re-enabled (see JSA-02), and Query history gains a new row for a run the operator left.

**Fix:** Expose QueryScreen's cancelTimers and call it from Compare.sync() on every mode change. Alternatively, have setMode() in 20-query.js call cancelTimers() before it changes data-mode.

**Verifier:** Confirmed. The mode.compare click handler calls only setMode. sync() calls cancel(), which clears Compare's own timers array only. QueryScreen's timers (later(800) at line 305 and the stream timers) stay pending and later call finish, renderResult/showState and remember in compare mode.

### WR-JSA-05: While streaming, the result panel already shows 'Run complete.' and an enabled Promote

**File:** `mockups/src/js/20-query.js:279`

finish() renders the placeholder envelope with opts.state 'success', so query.state.success ('Run complete.') is visible while the answer still reads 'Streaming. The answer arrives with the final event.'. partial is false, so result.promote is enabled while lastTrace is null. UI-SPEC line 308 says the final fields arrive after the evidence rows. For the stream-disconnected fixture, 'Run complete.' is visible until the generic error replaces it.

**Failure scenario:** Check 'Stream the response' and click Run. For about 600 ms after the running state ends, the green 'Run complete.' banner shows next to the streaming placeholder. Clicking 'Promote from this result' in that window opens the Ledger and emits promote with trace null.

**Fix:** Render the streaming phase with its own state: keep query.state.running visible or hide every state banner, and keep result.promote and result.compare disabled until the final applyFixture call.

**Verifier:** Confirmed. finish() at line 279 calls renderResult with {streaming:true, state:'success'} and partial:false. That shows query.state.success ('Run complete.', query.html:165-166) and enables result.promote while lastTrace is null. The promote handler emits {trace:null}. This contradicts UI-SPEC: the final fields should arrive after the evidence rows.

### WR-JSA-06: Every Compare Run column carries the q-success body, so per-column Open trace and Promote target the Default/naive trace

**File:** `mockups/src/js/21-compare.js:366`

Compare.run gives each column the same FIX.query['q-success'].body, whatever arm it resolved to. The header reads, for example, 'reads_graph+calls_llm · hipporag', but the trace token, evidence and Promote payload belong to the naive Default trace ypeBEsob…. In the Ledger fixture that trace has selector 'Default'.

**Failure scenario:** In Compare, set row 1 to Default and row 2 to capability reads_graph+calls_llm, then click Run. Click 'Promote this arm' on the hipporag column. The Ledger checks the 'Default / naive' trace, not a hipporag trace. renderDiff also reports every ref as shared, because the columns are identical.

**Fix:** Pick a body per resolved arm. FIX.compare.bodies already has naive-ok, local-ok and hipporag-ok, so map arm to body and fall back to q-success only for arms without a body.

**Verifier:** Confirmed. Compare.run line 366 uses FIX.query['q-success'].body for every column, so every column's trace_token is ypeBEsob…, which ledger.json:25 lists with selector 'Default', arm 'naive'. Per-arm bodies are available in FIX.compare.bodies, and loadFixture uses them. renderDiff counts every ref as shared because the columns are identical.

### WR-JSB-01: Evidence Inspector 'Open trace' opens an unrelated or stale trace

**File:** `mockups/src/js/30-evidence.js:443`

The inspector's trace-link click handler uses `originLink || $id("query.result.trace-link")`. Two code paths leave `originLink` wrong. (1) submitLookup (line 179) resets busyEl but not originLink, so after a manual lookup the link still points at the result the previous Open came from. (2) For evidence opened from graph.chunks.open-N, the closest() at line 460 finds no query panel or compare column, so the link falls back to the Query result's trace-link. That link holds whatever query ran last, or nothing at all. The link itself is always rendered enabled (href=#evidence), which conflicts with UI-SPEC lines 111 and 244: Open trace must carry the token of the result the evidence came from, and must be disabled when no token exists.

**Failure scenario:** Run a query, then on the Graph screen click Open on chunk c-4e81d3. In the inspector, click Open trace: the Trace Inspector loads the Query result's token (ypeBEsob...), which has no relation to the graph chunk. If no query has run yet, the click does nothing and no reason is shown. Separately, open evidence from compare column 2 and then resolve chunk:7f3a91 by manual lookup: Open trace loads column 2's trace.

**Fix:** Set originLink = null in submitLookup. In the open-evidence handler, set originLink to null when the opener is not inside a query or compare result, and leave it null rather than falling back to the query link. In renderRecord, disable inspector.trace-link (remove href, set aria-disabled and tabindex=-1, show reason text) whenever originLink is null or its result has no trace token.

**Verifier:** Confirmed. submitLookup (line 179) resets busyEl but leaves originLink alone. The open-evidence handler (lines 460-461) sets originLink to null for graph.chunks openers, and line 443 then falls back to query.result.trace-link. The evidence.html line 57 link always has href and is never disabled, which contradicts UI-SPEC lines 111 and 272.

### WR-JSB-02: 'Keep document' or Escape after pressing Delete still completes the delete

**File:** `mockups/src/js/40-documents.js:603`

The confirm handler schedules `later(() => { dialog.close(); finishDelete(p); }, CONFIRM_MS)` with p captured in the closure. While that timer is pending, the Keep document button stays enabled and Escape still closes the native dialog. The close handler (lines 591-596) clears pending, hides the spinner and re-enables confirm, which tells the operator the delete was cancelled. It does not cancel the timer, so finishDelete still runs and a 'success' outcome is shown.

**Failure scenario:** Open the delete dialog for contract-2026-q1, click Delete, then click Keep document (or press Escape) within 300 ms. The dialog closes and looks cancelled, then documents.delete.outcome shows '✓ success contract-2026-q1 Document deleted.'

**Fix:** While the confirm is in flight, disable shell.dialog.delete-cancel and block Escape (a 'cancel' event listener that calls preventDefault). Alternatively, keep the timer id and clearTimeout it in the dialog's close handler, so that dismissing really aborts the action.

**Verifier:** Confirmed. The confirm handler queues later(dialog.close+finishDelete(p)) with p captured in the closure. The close handler (lines 591-596) only resets pending and the spinner and never calls clearTimers. delete-cancel stays enabled, so dismissing the dialog still shows a delete success.

### WR-JSB-03: A failed job load leaves the restored page with Previous and Next disabled

**File:** `mockups/src/js/40-documents.js:403`

jobView('loading') disables jobs.prev and jobs.next. When the load fails, loadJob calls jobView(jobsShown) to put back the previous table, but nothing re-applies the pager state from `current.rec`. The job-id input also keeps the id that failed, so 'Refresh job' then re-requests that failing id instead of the job on screen.

**Failure scenario:** Load j-page1 (Next is enabled). Set Outcome to 'generic 5xx' and click Refresh job: the error banner shows and page 1 stays visible. Set Outcome back to success: Next page stays disabled even though next_offset is 5, so the operator cannot page forward without reloading.

**Fix:** In the failure branch, when `current` is set, restore the pager: setDisabled(prev, current.rec.offset <= 0) and setDisabled(next, current.rec.next_offset === null). Optionally restore the job-id input to current.rec.job_id.

**Verifier:** Confirmed. jobView('loading') disables prev and next (lines 321-324). The failure branch calls jobView(jobsShown) only, and only renderJob re-applies the pager state (lines 377-378). Next stays disabled after a failed refresh of j-page1.

### WR-JSB-04: Table actions erase the health-error banner while health is still unreachable

**File:** `mockups/src/js/50-corpus.js:298`

The health error and table errors share one errors region. openPage, retryDocument and setState all call hideErrors(), which hides the banner and resets healthErrorShown even when Console.health() is still in the error state. paintHealth already keeps health-body hidden in that state, so the Health panel is left showing only the 'unreachable' badge with no error detail and no Check health button. The reverse also happens: when health recovers, line 160 calls hideErrors(), which clears an unrelated table error.

**Failure scenario:** Set the shell health fixture to 'error'. Corpus shows the generic 5xx banner with Check health, and the health body is hidden. Click 'Refresh documents', or wait for the 30-second table poll: the banner disappears and nothing on screen explains the empty Health panel.

**Fix:** Track the health error separately from table errors. In hideErrors (or after it in openPage and retryDocument), re-run paintHealth() when healthState(Console.health()) === 'error', or give the health panel its own error container.

**Verifier:** Confirmed. hideErrors (lines 79-86) hides the shared errors box and resets healthErrorShown. openPage (line 298), retryDocument (line 315) and the table poll (lines 482-483) call it while paintHealth keeps health-body hidden in the error state, so the health error detail and Check health disappear.

### WR-JSC-01: Timeline fixture and status logic contradict the built POST /ledger/history 'active' semantics

**File:** `mockups/src/fixtures/ledger.json:5`

Engine.ledger_history (databasise/seam/engine.py:2223,2236) sets active = minted_version in Ledger.lineage(alias, head.minted_version). Ledger.lineage (databasise/ledger/ledger.py:500-519) includes the rollback target, so for timeline-prod the server returns active:true on BOTH row 1 (1.0.0) and row 5 (4.0.0). API-INVENTORY section 5.1 says the same ('derive active for the target of the active rollback row too'). The fixture marks only row 5 active. 60-ledger.js assumes exactly one active row: it uses records.filter(r=>r.active)[0] at lines 439 and 507, and statusOf at line 421 builds the 'target' status from that single row. The server also returns tombstoned:true for the tombstone record itself (engine.py:2237, (None or targets_version) in tombstoned), and the fixture has false at line 8. UI-SPEC section 5 and test_gui_10 (_check_retire_rules, TIP_TARGET) encode the fixture's model, so the tests pass while the contract is wrong.

**Failure scenario:** In Phase 18 the console feeds the real /ledger/history page for prod into renderTimeline. filter(active)[0] returns row 1 (1.0.0, a promotion), so statusOf never yields 'target'. Rows 1 and 5 both read 'active'. The rollback dialog reads 'from active version 1.0.0'. The rollback notice computes newVersion from 1.0.0 and reports 2.0.0. The 'roll back first' link focuses row 1 rather than the head row. Row 4 (the tombstone record) shows status 'tombstoned'.

**Fix:** Change the fixture to the server shape (row 1 active:true, row 4 tombstoned:true). Derive the head row from the newest active row, or the row with the highest generation_ordinal among active rows. Show 'target of active rollback' for every other active row. Update UI-SPEC section 5 and test_gui_10 to match, or record that the server semantics are being changed instead.

**Verifier:** Confirmed. engine.py ledger_history computes active = set(lineage(alias, head.minted_version)). Ledger.lineage follows the rollback row, so for prod it yields {4.0.0, 1.0.0} and row 1 gets active:true. Tombstoned is tested with (minted_version or targets_version), so the tombstone row (minted null, targets 2.0.0) gets true. The fixture has row 1 active:false and row 4 tombstoned:false. 60-ledger.js:439 and :507 take filter(active)[0], which is row 1 in the server shape, so statusOf never yields 'target' and the rollback dialog and notice would report 1.0.0.

### WR-JSC-02: Preview promotion throws TypeError if traces are unchecked while the preview is pending

**File:** `mockups/src/js/60-ledger.js:232`

showPreview sets busy, but the trace checkboxes stay enabled. When the 300 ms timer fires it reads selectedTraces()[0].arm with no guard. The input handler (refreshPreflight with busy=true) has already disabled Preview and Promote, and the exception skips the refreshPreflight call at line 233.

**Failure scenario:** Tick trace-1, pick an origin, enter alias 'staging' and click 'Preview promotion'. Within 300 ms, untick trace-1. The timer throws 'Cannot read properties of undefined (reading arm)'. No preview or error banner appears, and the Preview and Promote buttons stay disabled until the next form edit.

**Fix:** At the top of the timer callback, re-run refreshPreflight() and return if it reports blockers or if selectedTraces() is empty. Alternatively, disable the trace fieldset while busy.

**Verifier:** Confirmed. refreshPreflight never disables the trace checkboxes. The form input handler reruns it with busy=true, which disables Preview. The timer at line 232 then calls selectedTraces()[0].arm on an empty array and throws before the refreshPreflight call at line 233, so Preview and Promote stay disabled until the next form edit.

### WR-JSC-03: Edge-paging check 'next disabled' passes during the loading state

**File:** `databasise/tests/gui/test_gui_11_graph.py:153`

After edges.next is clicked, later() sets loading.edges=true and paint() runs pager(..., busy=true), which disables Next immediately. expect(...).to_be_disabled() therefore succeeds on the first poll, during the 300 ms loading window, before the second page renders. Next is never checked again after the page loads.

**Failure scenario:** A regression leaves next_offset non-null on the last edge page (for example an off-by-one in the next_offset expression at 70-graph.js:251). Next would be enabled after loading, but the test still passes because the assertion already succeeded while the edge list was loading.

**Fix:** First wait for the loaded state, either expect('graph.edges.loading').to_be_hidden() or expect('graph.edges.prev').to_be_enabled(). Then assert that Next is disabled.

**Verifier:** Confirmed. later() sets loading.edges and paints immediately, and pager() disables Next while busy, so line 153 can pass during the loading window. Line 154 (Prev enabled) waits for the loaded state, but Next is never asserted again after load, so a regression that leaves Next enabled on the last page still passes.

### WR-TST-01: Run-blocked checks use to_be_hidden on a transient state, so a Run that is not blocked still passes

**File:** `databasise/tests/gui/test_gui_04_query_mode.py:101`

In mockups/src/js/20-query.js run() (lines 290-308), a Run that passes validation calls showState("running") and later(800, finish), so query.state.running is visible for only 800 ms before success replaces it. ui.expect(...).to_be_hidden() retries for 5 s (conftest sets the expect timeout to 5000), so it waits through that 800 ms window and passes. The checks at lines 101, 114, 193 and 198 are the only assertions that Run is blocked for an empty capability set, a hash-shaped alias, multi-member raw JSON and invalid JSON. The inline-message assertions only show that a message was rendered, not that the run was stopped. Case (a) at line 93 is sound because it asserts query.state.idle is visible, which cannot recover once a run has started.

**Failure scenario:** validate() is changed so that it shows MSG_HASH_ALIAS but returns ok:true. Run then goes to running and, 800 ms later, to success. query.selector.error still contains the message, and to_be_hidden on query.state.running passes after the 800 ms timer. test_gui_04_query_mode_blocks_and_states and test_raw_selector_json_blocks_multi_member both pass while GUI-04's 'Run is blocked' clause is broken.

**Fix:** After each blocked click, assert a state that stays fixed when nothing runs: ui.expect("query.state.idle").to_be_visible() together with ui.expect("query.state.success").to_be_hidden(), or use a non-retrying check such as assert not ui.el("query.state.running").is_visible() taken right after the click. Apply this at lines 101, 114, 193 and 198.

**Verifier:** Confirmed. In 20-query.js run() (lines 290-308), a run that passes validation calls showState('running') and then later(800, finish), so the running view lasts only 800 ms. to_be_hidden() at lines 101, 114, 193 and 198 retries until that window ends, so it passes even if the run was not blocked. Only case (a) asserts that the idle view is visible.

### WR-TST-02: The 'wrong typed version keeps Retire disabled' check passes for an unrelated reason

**File:** `databasise/tests/gui/test_gui_10_ledger.py:104`

The retire dialog's confirm button is also gated on a trace selection and a change_origin choice: the test has to set retire-traces and retire-origin-human (lines 107-108) before confirm becomes enabled, and 60-ledger.js wires those fields into d.update. When '3.0' is typed at line 104, no trace or origin has been chosen yet, so confirm is disabled whatever the version check returns. The same thing happens in test_gui_10_promote_preflight_and_timeline at lines 159-160. No assertion fills traces and origin and then shows that a wrong version still keeps confirm disabled.

**Failure scenario:** The retire predicate in 60-ledger.js (retireVersion.value === d.pending.version) is changed to return true, or to a prefix match. '3.0' still leaves confirm disabled because no traces or origin are chosen, and '3.0.0' plus traces plus origin enables it. Both tests pass while GUI-10's 'Retire with typed version confirmation' is broken.

**Fix:** Choose retire-traces and retire-origin-human first. Then fill '3.0' and assert confirm is disabled, then fill '3.0.0' and assert it is enabled. Make the same change at lines 159-160.

**Verifier:** Confirmed. makeDialog's ok() (60-ledger.js line 270) also requires a picked trace and a change_origin. openFor clears both, so typing '3.0' at test lines 104 and 159-160 leaves confirm disabled whatever the predicate at line 306 returns. No test chooses traces and origin and then types a wrong version.

### WR-TST-03: The edges.next disabled check passes during the 300 ms loading window, not on the last page

**File:** `databasise/tests/gui/test_gui_11_graph.py:153`

Clicking graph.edges.next calls later(["edges"], ...) in 70-graph.js. That sets loading.edges=true and repaints, and pager() calls setDisabled(next, busy || next_offset === null), so Next is disabled while the request loads (LOAD_MS = 300). to_be_disabled() passes at once against this loading state. Line 154 (prev enabled) does wait for the load to finish, but by then the Next assertion has already passed. The test therefore never checks that Next stays disabled on page 2 because next_offset is null.

**Failure scenario:** The edge pager is changed so that next_offset is never null (for example, an off-by-one in edgeOffset + EDGE_PAGE < rows.length). After the load, page 2 shows Next enabled, but line 153 has already passed during loading and line 154 passes after it. test_gui_11_graph_browser passes while GUI-11's next_offset paging is broken.

**Fix:** First wait for the load to finish, for example with ui.expect("graph.edges.prev").to_be_enabled() or ui.expect("graph.edges.loading").to_be_hidden(). Only then assert ui.expect("graph.edges.next").to_be_disabled(), and swap the order of lines 153 and 154.

**Verifier:** Confirmed. later() in 70-graph.js (lines 294-300) sets loading.edges=true and calls paint() synchronously. pager() at line 183 then disables Next while busy, so the assertion at test line 153 passes during the 300 ms load. Line 154 waits for the load to end, but Next is never re-checked after that.

## Info

### IN-BLD-02: No-network checks miss fetch/XHR/WebSocket/EventSource and non-img/script media sources

**File:** `databasise/tests/gui/test_gui_01_shell.py:22`

The static scan covers only <link, <script src, <img src, @import and url(http. The runtime check in conftest.py records the Playwright 'request' event only, and only for code paths the test actually triggers (nav clicks). Playwright does not emit 'request' for WebSocket connections. `fetch(`, `XMLHttpRequest`, `new WebSocket`, `EventSource`, `navigator.sendBeacon`, `<iframe src`, `<video|audio|source src`, `srcset`, `<object data` and `<meta http-equiv=refresh` all pass both checks. A grep of the current build finds none of these, so the requirement is met today, but the test would not catch a regression.

**Failure scenario:** A later plan adds `fetch('http://127.0.0.1:9621/health')` in a click handler that test_gui_01 never clicks, or opens a WebSocket on load. test_file_references_no_network_resource and `ui.requests == []` both still pass, and the GUI-01 'zero network requests' requirement is reported as met while the file makes requests.

**Fix:** Add patterns to _NETWORK_REFERENCES for `\bfetch\s*\(`, `XMLHttpRequest`, `WebSocket`, `EventSource`, `sendBeacon`, `\bsrcset\s*=`, `<(iframe|video|audio|source|embed|track)\b[^>]*\bsrc\s*=`, `<object\b[^>]*\bdata\s*=` and `http-equiv`. In conftest.py, also register `page.on('websocket', ...)` to record WebSocket connections.

**Verifier:** Confirmed. _NETWORK_REFERENCES (lines 22-28) covers only link, script src, img src, @import and url(http). The runtime check records only page 'request' events from code paths the test drives, and does not record websockets. A fetch in an unclicked handler, or a WebSocket, iframe or media src, would pass both checks. The line 21 shortcut comment admits the regex scope, and nothing makes requests today, so this is latent: info.

### IN-BLD-03: Fixture JSON escapes '</' but not '<!--', so fixture text can still break the script block

**File:** `mockups/build.py:51`

fixtures_json() replaces '</' with '<\/' to stop fixture text from closing the <script type="application/json"> block. HTML script-data parsing also changes state on '<!--' followed by '<script': this enters the double-escaped state, and in that state the real closing '</script>' does not end the element. The embedded files include generated input (docs/gui/refusals.json, selector-resolution.json) that a person does not retype.

**Failure scenario:** A fixture or refusal message contains the literal text '<!-- <script'. The JSON block then absorbs the following inline <script> holding all the mockup JS. window.__mock is never defined, every `ui` test times out on wait_for_function, and the parse of #mock-fixtures fails.

**Fix:** Also escape '<' outright, e.g. `text.replace('<', '\\u003c')`. This is valid JSON and removes every script-data state transition.

**Verifier:** Confirmed at build.py:51. Only '</' is escaped. The HTML tokenizer handles '<!--' followed by '<script ' inside script data with the escaped and double-escaped states, so the closing '</script>' of the JSON block and of the next inline script would not end the element. The input that triggers it is unlikely. Escaping every '<' as < is a one-line, complete fix.

### IN-BLD-04: Page-error assertion runs in fixture teardown, so a JS exception is reported as a teardown ERROR, not as a failure of the test

**File:** `databasise/tests/gui/conftest.py:139`

The module docstring (lines 8-9) says 'a JS exception fails the test that caused it'. The `assert errors == []` sits after `yield` in the `ui` fixture. pytest reports that as the test PASSED plus an ERROR at teardown, and a failure summary filtered on 'failed' does not count it. The same docstring makes a point of distinguishing failed from errored outcomes for the missing-file case.

**Failure scenario:** A screen's JS throws on navigation, but the test's own expect() calls still succeed. The run shows '1 passed, 1 error'. A gate or a person counting failed tests (the fail-first convention described in this docstring) sees no failure for the test, which reads as green.

**Fix:** Use a `pytest_runtest_call` hookwrapper (or check the errors inside pytest_pyfunc_call after the call) that asserts on the page errors recorded for the item, so a page error fails the call phase. Alternatively, change the docstring to say page errors surface as teardown errors.

**Verifier:** Confirmed at conftest.py:139. The assert runs after yield, in fixture teardown, so pytest reports the test as passed plus a teardown error. The docstring (lines 8-9) says a JS exception 'fails the test that caused it', and the same docstring separates failed from errored outcomes. The session still exits nonzero, so this is doc/behavior drift: info.

### IN-BLD-05: Shared fixtures silently overwrite a same-named src/fixtures file

**File:** `mockups/build.py:49`

data[path.stem] is filled from mockups/src/fixtures/*.json first. Then the 'refusals' and 'resolution' keys are assigned from SHARED_FIXTURES with no collision check.

**Failure scenario:** Someone adds mockups/src/fixtures/resolution.json (or refusals.json) as a screen fixture. The build succeeds, but the screen reads the shared selector-resolution data instead of the new file, with no error.

**Fix:** Before the second loop, fail(...) when `key in data`.

**Verifier:** Confirmed at build.py:48-49. data[key] for 'refusals' and 'resolution' overwrites any same-stem src/fixtures/*.json entry with no check or error. Latent, and needs someone to add a fixture with a colliding name.

### IN-JSA-07: Promote events from Query/Compare only add checkmarks and never clear earlier selections

**File:** `mockups/src/js/60-ledger.js:628`

The 'promote' handler checks the box whose trace matches and leaves every earlier checked box alone. Query and Compare emit promote for one result each. Successive promotes therefore pile up traces from different selectors.

**Failure scenario:** Load cmp-3col-clean. Click Promote on the naive column, go back, and click Promote on the hipporag column. The Ledger form now has two traces checked from different selectors. Its preflight shows a disagreeing-selector blocker that the operator never chose.

**Fix:** In the promote handler, uncheck all boxes before checking the matching one, because a promote from a single result means 'start from this trace'.

**Verifier:** Confirmed. The Console.on('promote') handler in 60-ledger.js only sets boxes[i].checked = true for the matching trace and never unchecks the others, so checks from successive promotes accumulate. Whether preflight then flags disagreeing selectors depends on refreshPreflight, which I did not open, but the accumulation itself is real.

### IN-JSA-08: Promote stays enabled on a result with trace_token null

**File:** `mockups/src/js/20-query.js:184`

result.promote is disabled only for partial results. For q-trace-null, lastTrace is null, but Promote still navigates to the Ledger and emits {trace:null}. That matches no trace, and the operator is left on the Ledger with nothing selected.

**Failure scenario:** Select Fixture 'trace_token null'. The panel says 'No trace token on this result.' and 'Promote from this result' is still active. Clicking it switches to the Ledger with no trace selected.

**Fix:** Use setDisabled(ID('result.promote'), partial || !lastTrace), after lastTrace is assigned, and show a matching no-promote reason.

**Verifier:** Confirmed. Line 184 calls setDisabled(result.promote, partial) only. The q-trace-null fixture (query.json:67) has trace_token null and partial false, so Promote stays enabled and emits {trace:null}, which matches no ledger trace.

### IN-JSA-09: The refusal state view always says HTTP 422, whatever the response status

**File:** `mockups/src/screens/query.html:219`

SHAPE_STATE maps every refusal to the 'refusal-422' view, whose static text is 'The server refused the request (HTTP 422).'. Refusals such as StoreBusyError or PageSizeExceededError can arrive with other statuses, and the banner footer prints the real status.

**Failure scenario:** Call __mock.inject('query', {status: 409, body: {refusal_type: 'StoreBusyError', message: 'busy'}}). The state view reads 'HTTP 422' and the refusal footer reads 'HTTP 409.' on the same screen.

**Fix:** Remove the status from the static text ('The server refused the request.') or fill it from the response status in applyResponse.

**Verifier:** Confirmed. classifyResponse (10-shared.js:218) returns 'refusal' for any string refusal_type whatever the status. SHAPE_STATE maps that to refusal-422, whose static text (query.html:219) says 'HTTP 422', while the banner footer (10-shared.js:259) prints the real status. inject with status 409 shows both values.

### IN-JSB-05: Jobs poll reopens a closed drawer and keeps running on other screens

**File:** `mockups/src/js/40-documents.js:548`

The 30-second poll clicks jobs.refresh, which calls loadJob, which calls setDrawer(true). The interval is never cleared when the operator closes the drawer or leaves the screen, and it re-runs hideErrors(), which clears any error the operator is reading.

**Failure scenario:** Load a job, tick 'Refresh every 30 seconds', then close the Jobs drawer. Within 30 seconds the drawer reopens without operator action. Any error banner on Documents is wiped on each tick.

**Fix:** Poll only while the drawer is open: skip the tick when jobs.drawer is hidden, or uncheck and clear the poll in the jobs.close handler.

**Verifier:** Confirmed. The poll interval (lines 547-549) clicks jobs.refresh whenever current is set. loadJob calls setDrawer(true) and hideErrors. jobs.close (lines 523-526) does not clear the interval, so the drawer reopens.

### IN-JSB-06: Retry confirmation can land on a different document's row

**File:** `mockups/src/js/50-corpus.js:323`

retryDocument captures the row by slot index and writes 'Retry enqueued' into that slot after a 300 ms timer. The timer is not tracked, so a filter, sort, search or page change during that window re-renders the slots, and the message appears under whichever document now occupies slot n.

**Failure scenario:** In counts-preprocessed, click Retry on the interrupted row, then change Sort to updated_at within 300 ms. The message 'Retry enqueued: job a41c...' appears under another document.

**Fix:** Store the timer and clear it in paintPage and openPage, or find the target row by document_id when the timer fires.

**Verifier:** Confirmed. retryDocument captures tbody.rows[n-1] and its retry-msg element, and the setTimeout is not tracked. paintPage refills the same row slots on filter or sort, so the message lands on whichever document now occupies the slot.

### IN-JSB-07: 'Open in Corpus' is shown only for HippoRAG records, but Corpus lists only v1 documents

**File:** `mockups/src/js/30-evidence.js:438`

document-link is shown only when the record has document_id. In the fixtures only hipporag-chunks records have that field; LightRAG records use full_doc_id. The link then opens Corpus & Health, which per its own header (corpus.html line 2-3) and documents.notice.store-split lists only LightRAG (v1) documents and applies no filter. The cross-screen link can never show the document it names. UI-SPEC line 318 specifies this behaviour, so the spec and the screens contradict each other.

**Failure scenario:** Resolve chunk:7f3a91 in hipporag-chunks and click Open in Corpus. The Corpus screen shows the v1 table, where contract-2026-q1 from the HippoRAG store is not present and is not searched for.

**Fix:** Either show the link for LightRAG records (keyed on full_doc_id) and prefill corpus.table.search with the id, or hide it for HippoRAG records and amend UI-SPEC line 318.

**Verifier:** Confirmed. Line 123 shows document-link only when document_id is present, which only HippoRAG records have, and the click just calls Console.show('corpus'). The Corpus screen lists only LightRAG v1 documents and applies no filter. This is a spec/screen contradiction that follows UI-SPEC line 318.

### IN-JSB-08: A cancelled evidence resolve leaves the opener button stuck as 'Opening'

**File:** `mockups/src/js/30-evidence.js:234`

loadTrace (line 234) and openTrace (line 349) call clearTimeout(timer). That timer may be a pending evidence resolve, but neither function calls busy(false), so the Open button that started the resolve keeps aria-busy=true and aria-label='Opening' on the Query or Graph screen.

**Failure scenario:** Click Open on query.evidence.open-1, then within 300 ms switch to the Trace tab and press Load trace. query.evidence.open-1 now permanently announces 'Opening' to screen readers.

**Fix:** Call busy(false) next to clearTimeout(timer) in loadTrace and openTrace.

**Verifier:** Confirmed. loadTrace (line 234) and openTrace (line 349) call clearTimeout(timer) without busy(false), so busyEl keeps aria-busy and aria-label='Opening'. The next open-evidence overwrites busyEl, so the stale attributes are never removed.

### IN-JSB-09: No test covers the inspector's Open trace link or a confirmed delete

**File:** `databasise/tests/gui/test_gui_07_evidence_trace.py:139`

test_gui_07 checks Open trace only on query.result.trace-link, never on evidence.inspector.trace-link, so JSB-01 passes the suite. test_gui_08 always dismisses the delete dialog with Keep document and never clicks shell.dialog.delete-confirm, so documents.delete.outcome, the seam-events heading text 'reported by the v1 delete node' (UI-SPEC line 348) and JSB-02 are all unexercised.

**Failure scenario:** Delete the inspector trace-link handler, or break showDeleteOutcome: every GUI-07 and GUI-08 test still passes.

**Fix:** Add one test that opens evidence from compare column 2 and asserts that evidence.inspector.trace-link loads that column's token. Add one test that confirms a delete and asserts that documents.delete.outcome contains 'success' and 'reported by the v1 delete node'. The test files are owner-guarded, so this needs an owner grant.

**Verifier:** Confirmed by reading test_gui_07 (lines 139-144 use only query.result.trace-link) and test_gui_08 (both delete flows click delete-cancel and none clicks delete-confirm or checks documents.delete.outcome). test_gui_06 does not cover either. I could not run a full-text search over every test file because the hook blocks grep and the code index returned nothing, so this rests on reading files 06, 07, 08 and 09.

### IN-JSC-04: Cancelling a dialog after Confirm still applies the promote, rollback or retire

**File:** `mockups/src/js/60-ledger.js:384`

The confirm handlers (lines 350-359 and 377-393) schedule finish() or showResult() with a captured payload. The Cancel button and Escape stay active while the spinner runs. The close handler clears pending, but the timer is not cancelled.

**Failure scenario:** In the Retire dialog, type 3.0.0, choose a trace and an origin, and click Retire. Then click 'Keep version' within 300 ms. The dialog closes, but row 3 is still marked tombstoned and the notice 'Retired version 3.0.0 ... Nothing un-retires it.' appears. Promote behaves the same: 'Keep alias' is followed by the 'Alias promoted' card.

**Fix:** While a confirm is in flight, disable the cancel button and call preventDefault on the dialog's 'cancel' event, so the dialog cannot close until the result arrives. Alternatively, clear the timer on close and state that the request was abandoned.

**Verifier:** Confirmed. The cancel handlers only call close(). The close listeners clear pending but not the timer. The confirm timers captured p and still call finish(kind, p) or showResult after the dialog closes. The cancel button is never disabled, so Cancel or Escape during the 300 ms spinner still applies the action.

### IN-JSC-05: Rollback notice and promote-success fixture mint generation ordinals that collide with other aliases

**File:** `mockups/src/js/60-ledger.js:332`

generation_ordinal is the ledger row id, which is global across aliases (engine.py:2194, 2229). The aliases fixture gives staging ordinal 6 and hr ordinal 7. finish() computes the new ordinal as the maximum within the current alias plus 1, which is 6. The promote-success fixture always reports version 2.0.0 and ordinal 6 for any alias.

**Failure scenario:** Roll back prod to 3.0.0. The notice reads 'Version 5.0.0 minted as generation 6', but 6 already belongs to staging; the next row id would be 8. Promoting prod shows 'version 2.0.0, generation_ordinal 6', although prod's active version is already 4.0.0.

**Fix:** Compute the next ordinal as the maximum generation_ordinal across FIX.aliases and the current records, plus 1. Make the promote-success fixture alias-neutral (ordinal 8), or derive its version from the alias's active version.

**Verifier:** Confirmed. aliases.json gives staging ordinal 6 and hr ordinal 7. finish() line 332 computes the maximum over current.records plus 1, which is 6 for prod. engine.py uses e.id (the global row id) as generation_ordinal. promote-success hardcodes version 2.0.0 and ordinal 6 for every alias.

### IN-JSC-06: Mock outcomes return errors the graph and chunk routes cannot produce

**File:** `mockups/src/js/70-graph.js:137`

With outcome 'refusal', failure() returns 409 StoreBusyError for the 'chunks' operation. POST /chunks has no StoreBusyError (API-INVENTORY 5.1a; engine.chunk_page maps only VectorStoreCorruptedError). With outcome 'server-failure', it returns failure_class 'StoreFault', but /graph/nodes, /graph/node and /chunks raise only 'StoreCorrupted' (engine.py:2371, 2425, 2452).

**Failure scenario:** The owner clicks chunks Next with outcome=refusal and sees the 'store busy' 409 banner on the chunk browser. Phase 18 ports a busy-state branch for /chunks that never fires, and the approved mockup shows a fault class the backend never emits on this screen.

**Fix:** For op 'chunks', return a selector refusal (for example UnsatisfiableSelectorError, 422) on 'refusal'. Use failure_class 'StoreCorrupted' for the graph and chunk server-failure body.

**Verifier:** Confirmed. failure() returns the store-busy 409 for op 'chunks' under 'refusal', and failure_class 'StoreFault' under 'server-failure'. In engine.py, chunk_page maps only VectorStoreCorruptedError to StoreCorrupted (line 2371), and graph_nodes and graph_node raise StoreBusyError or StoreCorrupted (lines 2425 and 2452), never StoreFault.

### IN-JSC-07: Node and chunk fixture pages end paging while total says more rows exist

**File:** `mockups/src/fixtures/graph.json:19`

Page 2 has offset 8, 8 rows, total 214 and next_offset null. The server sets next_offset = end if end < total (engine.py:2430), so this response is impossible. The chunk pages (line 69, total 96) and the hipporag pages (lines 98 and 122) have the same problem.

**Failure scenario:** On the Graph screen, click nodes Next. The range reads 'Showing 9 to 16 of 214' and Next is disabled, so the approved mockup shows the operator 214 nodes with no way to reach node 17.

**Fix:** Set next_offset to 16 on the second pages and either add a third page or set total to 16 (and 16 for chunks) so the fixtures match the server's paging rule.

**Verifier:** Confirmed. graph.json lines 19, 69, 98 and 122 have offset 8, total 214/96/342/96 and next_offset null. The engine's paging rule (next_offset = end if end < total) cannot produce that. The pager shows 'of 214' with Next disabled.

### IN-JSC-08: Ledger hideErrors erases the page-size validation message without re-checking it

**File:** `mockups/src/js/60-ledger.js:82`

renderError clears every [data-error-id] field message. 70-graph.js reruns its client checks afterwards (checkAll, with a comment explaining why), but 60-ledger.js does not call checkSize after hideErrors or showError.

**Failure scenario:** Type 0 into the timeline page size: 'Page size must be between 1 and 100.' appears. Then pick a fixture or click Preview promotion. hideErrors clears the message and aria-invalid while the field still holds 0.

**Fix:** Call checkSize() at the end of hideErrors() and showError() in 60-ledger.js, as the graph screen does with checkAll().

**Verifier:** Confirmed. The ledger page-size input has data-error-id, and renderError clears every [data-error-id] field in the screen. hideErrors and showError in 60-ledger.js never call checkSize again, unlike 70-graph.js, which calls checkAll afterwards.

### IN-TST-04: Several GUI-04 clauses are not checked by any test

**File:** `databasise/tests/gui/test_gui_04_query_mode.py:136`

No test in the file checks these GUI-04 clauses: that the advanced panel starts collapsed (the test clicks the toggle and only asserts that the panel is visible afterwards), the stream toggle, the degraded badge and the stop_reason/degradation_reason tooltips, that the Capability multi-select offers exactly the 17 Effect literals, or that the token table has one row per counted_by plus a totals row (only the text 'Total' is checked). The section 3.0 resolution strings are also hard-coded and are not compared with databasise/tests/fixtures/selector-resolution.json, which the requirement names as the source. They match today, so any drift would only show up after the fixture changes.

**Failure scenario:** The advanced panel ships expanded by default, or the capability select loses one Effect literal. Every GUI-04 test still passes.

**Fix:** Add assertions for the missing clauses: assert query.advanced.panel is hidden before the toggle is clicked, count the capability select options against the Effect literal set, and assert the degraded badge's title text. Build the resolves-to cases from selector-resolution.json instead of literal strings.

**Verifier:** Confirmed by reading the file. Nothing asserts that the panel starts collapsed (it is a details element, so to_be_visible after the toggle proves nothing). Nothing tests the stream toggle, the degraded badge or tooltips, or counts the Effect options. The token table check is only the text 'Total', and the resolves-to strings are hard-coded. These are coverage gaps, not current bugs.

### IN-TST-05: The GUI-10 mixed-selector warning, the success card and alias autocomplete are not tested

**File:** `databasise/tests/gui/test_gui_10_ledger.py:122`

GUI-10 requires the pre-flight to warn when the chosen traces came from different selectors, a success card showing alias, version, record_kind, provenance and generation_ordinal, and alias autocomplete from the client-side ledger log. No test selects traces from different selectors (for example trace-1 Default with trace-6 alias prod) or confirms a promote to reach the success card.

**Failure scenario:** The mixed-selector warning or the success card is removed from the ledger screen. test_gui_10_promote_preflight_and_timeline and the other tests in the file still pass.

**Fix:** Check trace-1 and trace-6 and assert that the pre-flight contains the warning text from the spec. Confirm the promote dialog and assert the fields of the success card.

**Verifier:** Confirmed. test_gui_10_ledger.py never selects traces from mixed selectors, never confirms a promote to reach the success card, and never checks alias autocomplete. The GUI-10 requirement text names all three.

### IN-TST-06: The needs-backend wrapper walk skips graph.state.* controls and does not check the route value

**File:** `databasise/tests/gui/test_gui_11_graph.py:17`

NODE_PREFIXES leaves out graph.state.* (the 'Retry request' button) and graph.planned.*. The walk also only checks that some [data-needs-backend] ancestor exists, not that its value is one of the five routes GUI-11 lists. The retry button is wrapped today (graph.html line 25), so nothing fails now, but the requirement 'every control on this screen' is not enforced.

**Failure scenario:** graph.state.retry is moved out of its busy-wrap div, or a wrapper's route is mistyped (for example 'POST /graph/nodez'). test_every_graph_control_is_in_a_needs_backend_wrapper still passes.

**Fix:** Walk every input, select, textarea and button under screen-graph, excluding mock-only controls (graph.mock.*), instead of a prefix list. Assert that each wrapper's data-needs-backend value is one of the five proposed routes.

**Verifier:** Confirmed. NODE_PREFIXES leaves out graph.state.* and graph.planned.*, and UNWRAPPED_JS only checks for a [data-needs-backend] ancestor without validating its route value. Today graph.state.retry is wrapped (graph.html line 25), so this is a coverage gap only.

### IN-TST-07: GUI-09 health loading, refresh/poll and corpus paging are not tested

**File:** `databasise/tests/gui/test_gui_09_corpus.py:96`

GUI-09 requires a health loading state, manual refresh, an optional 30-60 s poll, a corpus page-size limit of 1..100 and prev/next paging by next_offset. None of these is asserted in the file. Only the health fixtures, the KPI filter, Retry and the empty state are covered.

**Failure scenario:** corpus.table.next stays enabled when next_offset is null, or page-size accepts 0. All GUI-09 tests still pass.

**Fix:** Add assertions for the page-size error at 0 and 101, for next being disabled on a last-page fixture (counts-last exists in 50-corpus.js), and for health.refresh showing the loading state.

**Verifier:** Confirmed. test_gui_09_corpus.py has no assertions on the health loading state, refresh or poll, page-size bounds, or prev/next paging, all of which the GUI-09 requirement body lists. The requirement's own Test clause leaves them out, so the gap is against the requirement body.

### IN-TST-08: The refusal catalogue is compared by name only, so attribute drift is not detected

**File:** `databasise/tests/gui/test_gui_06_errors.py:79`

GUI-06 requires a static catalogue of all SeamRefusalError subclasses 'and their attributes'. _assert_catalogue_matches compares only the sets of refusal_type names in docs/gui/refusals.json, in the embedded mock-fixtures and in the runtime subclasses. If an attribute is added to or renamed on a refusal class in databasise/seam/refusals.py, the catalogue becomes stale and the test still passes.

**Failure scenario:** UnknownTraceReferenceError renames trace_reference to reference. The catalogue still lists trace_reference, the banner highlights a field the server no longer sends, and test_refusal_catalogue_matches_the_code_and_the_mockup passes.

**Fix:** For each class, also compare the catalogue's attribute list with the attributes the class sets (for example from its __init__ signature or a declared field tuple) in both the file catalogue and the embedded one.

**Verifier:** Confirmed. _assert_catalogue_matches compares only refusal_type name sets. refusals.json carries attribute_keys, which 10-shared.js lines 258-259 render in the banner footer, and GUI-06 says the catalogue covers subclasses 'and their attributes'. A renamed attribute would leave a stale catalogue that the test does not catch.
