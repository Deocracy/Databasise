---
phase: 17
review: 17-REVIEW.md
open_critical: 0
open_warning: 17
recorded: 2026-10-31T18:13:45Z
---

# Phase 17: Code Review Disposition

Source: 17-REVIEW.md (39 findings: 0 critical, 17 warning, 22 info). The finding IDs carry an area code (WR-<AREA>-NN, IN-<AREA>-NN), so the gate's automatic recorder matched none of them; this file is written from the headings. Every row defaults to `open` until a fix round records it. JSC-03 duplicates TST-03.

## Findings

| ID | Severity | Disposition | Title |
|----|----------|-------------|-------|
| WR-BLD-01 | warning | open | Planned-item check matches the item text anywhere in the file, not inside the named planned list |
| WR-JSA-01 | warning | fixed in Phase 18 (18-04) | Raw selector JSON accepts wrong member types, then Run throws an uncaught TypeError |
| WR-JSA-02 | warning | open | Compare.run has no blocker guard, and QueryScreen.showState re-enables Run in compare mode |
| WR-JSA-03 | warning | open | Query states render next to visible compare columns, so more than one state is shown at once |
| WR-JSA-04 | warning | open | A mode switch cancels only Compare's timers; a pending Query run still fires in compare mode |
| WR-JSA-05 | warning | open | While streaming, the result panel already shows 'Run complete.' and an enabled Promote |
| WR-JSA-06 | warning | open | Every Compare Run column carries the q-success body, so per-column Open trace and Promote target the Default/naive trace |
| WR-JSB-01 | warning | open | Evidence Inspector 'Open trace' opens an unrelated or stale trace |
| WR-JSB-02 | warning | open | 'Keep document' or Escape after pressing Delete still completes the delete |
| WR-JSB-03 | warning | open | A failed job load leaves the restored page with Previous and Next disabled |
| WR-JSB-04 | warning | open | Table actions erase the health-error banner while health is still unreachable |
| WR-JSC-01 | warning | open | Timeline fixture and status logic contradict the built POST /ledger/history 'active' semantics |
| WR-JSC-02 | warning | open | Preview promotion throws TypeError if traces are unchecked while the preview is pending |
| WR-JSC-03 | warning | open | Edge-paging check 'next disabled' passes during the loading state |
| WR-TST-01 | warning | open | Run-blocked checks use to_be_hidden on a transient state, so a Run that is not blocked still passes |
| WR-TST-02 | warning | open | The 'wrong typed version keeps Retire disabled' check passes for an unrelated reason |
| WR-TST-03 | warning | open | The edges.next disabled check passes during the 300 ms loading window, not on the last page |
| IN-BLD-02 | info | open | No-network checks miss fetch/XHR/WebSocket/EventSource and non-img/script media sources |
| IN-BLD-03 | info | open | Fixture JSON escapes '</' but not '<!--', so fixture text can still break the script block |
| IN-BLD-04 | info | open | Page-error assertion runs in fixture teardown, so a JS exception is reported as a teardown ERROR, not as a failure of the test |
| IN-BLD-05 | info | open | Shared fixtures silently overwrite a same-named src/fixtures file |
| IN-JSA-07 | info | open | Promote events from Query/Compare only add checkmarks and never clear earlier selections |
| IN-JSA-08 | info | open | Promote stays enabled on a result with trace_token null |
| IN-JSA-09 | info | open | The refusal state view always says HTTP 422, whatever the response status |
| IN-JSB-05 | info | open | Jobs poll reopens a closed drawer and keeps running on other screens |
| IN-JSB-06 | info | open | Retry confirmation can land on a different document's row |
| IN-JSB-07 | info | open | 'Open in Corpus' is shown only for HippoRAG records, but Corpus lists only v1 documents |
| IN-JSB-08 | info | open | A cancelled evidence resolve leaves the opener button stuck as 'Opening' |
| IN-JSB-09 | info | open | No test covers the inspector's Open trace link or a confirmed delete |
| IN-JSC-04 | info | open | Cancelling a dialog after Confirm still applies the promote, rollback or retire |
| IN-JSC-05 | info | open | Rollback notice and promote-success fixture mint generation ordinals that collide with other aliases |
| IN-JSC-06 | info | open | Mock outcomes return errors the graph and chunk routes cannot produce |
| IN-JSC-07 | info | open | Node and chunk fixture pages end paging while total says more rows exist |
| IN-JSC-08 | info | open | Ledger hideErrors erases the page-size validation message without re-checking it |
| IN-TST-04 | info | open | Several GUI-04 clauses are not checked by any test |
| IN-TST-05 | info | open | The GUI-10 mixed-selector warning, the success card and alias autocomplete are not tested |
| IN-TST-06 | info | open | The needs-backend wrapper walk skips graph.state.* controls and does not check the route value |
| IN-TST-07 | info | open | GUI-09 health loading, refresh/poll and corpus paging are not tested |
| IN-TST-08 | info | open | The refusal catalogue is compared by name only, so attribute drift is not detected |
