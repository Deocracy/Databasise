---
phase: 18-gui-live
verified: 2026-10-31T00:00:00Z
status: human_needed
score: 5/7 must-haves verified (5/5 roadmap success criteria verified in code; 2 plan 18-11 owner-gated truths pending the postponed click-through)
covered_files: [".planning/phases/18-gui-live/18-01-PLAN.md", ".planning/phases/18-gui-live/18-01-SUMMARY.md", ".planning/phases/18-gui-live/18-02-PLAN.md", ".planning/phases/18-gui-live/18-02-SUMMARY.md", ".planning/phases/18-gui-live/18-03-PLAN.md", ".planning/phases/18-gui-live/18-03-SUMMARY.md", ".planning/phases/18-gui-live/18-04-PLAN.md", ".planning/phases/18-gui-live/18-04-SUMMARY.md", ".planning/phases/18-gui-live/18-05-PLAN.md", ".planning/phases/18-gui-live/18-05-SUMMARY.md", ".planning/phases/18-gui-live/18-06-PLAN.md", ".planning/phases/18-gui-live/18-06-SUMMARY.md", ".planning/phases/18-gui-live/18-07-PLAN.md", ".planning/phases/18-gui-live/18-07-SUMMARY.md", ".planning/phases/18-gui-live/18-08-PLAN.md", ".planning/phases/18-gui-live/18-08-SUMMARY.md", ".planning/phases/18-gui-live/18-09-PLAN.md", ".planning/phases/18-gui-live/18-09-SUMMARY.md", ".planning/phases/18-gui-live/18-10-PLAN.md", ".planning/phases/18-gui-live/18-10-SUMMARY.md", ".planning/phases/18-gui-live/18-11-PLAN.md", "databasise/console/__init__.py", "databasise/console/operator-console.html", "databasise/console/src/css/00-base.css", "databasise/console/src/css/20-query.css", "databasise/console/src/css/21-compare.css", "databasise/console/src/css/30-evidence.css", "databasise/console/src/css/40-documents.css", "databasise/console/src/css/50-corpus.css", "databasise/console/src/css/60-ledger.css", "databasise/console/src/css/70-graph.css", "databasise/console/src/dialogs/delete.html", "databasise/console/src/dialogs/promote.html", "databasise/console/src/dialogs/retire.html", "databasise/console/src/dialogs/rollback.html", "databasise/console/src/js/00-app.js", "databasise/console/src/js/05-api.js", "databasise/console/src/js/10-shared.js", "databasise/console/src/js/20-query.js", "databasise/console/src/js/21-compare.js", "databasise/console/src/js/30-evidence.js", "databasise/console/src/js/40-documents.js", "databasise/console/src/js/50-corpus.js", "databasise/console/src/js/60-ledger.js", "databasise/console/src/js/70-graph.js", "databasise/console/src/js/90-start.js", "databasise/console/src/page.html", "databasise/console/src/parts/errors.html", "databasise/console/src/parts/selector.html", "databasise/console/src/screens/corpus.html", "databasise/console/src/screens/documents.html", "databasise/console/src/screens/evidence.html", "databasise/console/src/screens/graph.html", "databasise/console/src/screens/ledger.html", "databasise/console/src/screens/query.html", "databasise/launcher/serve_rest.py", "databasise/pyproject.toml", "databasise/tests/gui_live/__init__.py", "databasise/tests/gui_live/_corpus_fake.py", "databasise/tests/gui_live/_opened.py", "databasise/tests/gui_live/conftest.py", "databasise/tests/gui_live/test_live_01_serving.py", "databasise/tests/gui_live/test_live_02_query_compare.py", "databasise/tests/gui_live/test_live_03_errors.py", "databasise/tests/gui_live/test_live_04_evidence_trace.py", "databasise/tests/gui_live/test_live_05_documents.py", "databasise/tests/gui_live/test_live_06_corpus_health.py", "databasise/tests/gui_live/test_live_07_ledger.py", "databasise/tests/gui_live/test_live_08_graph.py", "databasise/tests/gui_live/test_live_09_badges_ids.py", "docs/gui/API-INVENTORY.md", "mockups/build.py", "mockups/operator-console.html"]
covered_digest: "v3:sha256:22546fe89f79759bbd2df029733012267e2432209f4f28aa50e02f248fe81123"
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Owner click-through (18-11 Task 2, D-20): start databasise-rest --operator --console --log-file on 127.0.0.1 with real model clients, open /console, walk the five success criteria and approve"
    expected: "Query, stream, compare, evidence, trace, ingest, upload, delete, corpus, health, ledger and graph screens work against real clients with no CORS error and the header showing live /health"
    why_human: "The offline suite uses stub clients and an in-process uvicorn; real provider spend and the real CLI launch are owner-only (D-19, D-20)"
  - test: "D-15 LightRAG default path: ingest a document with the default selector, then query it"
    expected: "The query returns evidence from the ingested document"
    why_human: "The offline stub does not populate the v2 stores; only the HippoRAG query-after-ingest is automated (test_query_after_hipporag_ingest_returns_that_documents_evidence)"
  - test: "Store-busy from another process: hold the graph store from a second OS process while browsing Graph"
    expected: "graph.state.store-busy with StoreBusyError, 'store busy', 'HTTP 409.'; Retry recovers once released"
    why_human: "The automated case holds a raw pycozo client in the same process as the app"
  - test: "375 px visual checks: log tail and 500-character excerpt wrap and scroll inside 240 px; corpus poll indicators wrap to two lines without horizontal scroll"
    expected: "No horizontal scroll; text wraps with overflow-wrap anywhere"
    why_human: "Backstop truths in 18-04 and 18-07 with no automated test; visual layout"
  - test: "Confirm provisional default A: keep documents.notice.store-split visible with its frozen text (roadmap open question 8, D-15 amendment)"
    expected: "Owner answers keep or remove; removal is a one-line follow-up in the live source"
    why_human: "Owner decision deferred by D-15 amendment"
  - test: "Confirm provisional default B: the two 18-07 planner assumptions (unknown stores keys appended as rows with a state badge from the value; unknown counts chips wrap with no cap)"
    expected: "Owner confirms or rejects each"
    why_human: "Unresolved UI consideration inherited from Phase 17"
  - test: "Confirm provisional default C: the LIVE-03 typed-refusal deviation (a multi-member selector renders the typed MultiMemberSelectorError banner per SEAM-02, not a field error)"
    expected: "Owner answers acknowledged or asks for a different rendering"
    why_human: "Named deviation from the LIVE-03 text, recorded in 18-04"
  - test: "Confirm provisional default D: R18-05 arm-neutral alias wording on Documents (Target, upload notice, result card, Delete dialog, seam toggle) when the alias arm is unknown"
    expected: "Owner accepts arm-neutral wording or asks for an alias-arm lookup"
    why_human: "Default chosen while the click-through is postponed (18-REVIEW-DISPOSITION R18-05)"
  - test: "Decide on R18-07: a streamed query leaves InFlight when response headers arrive, so a health poll tick during the SSE event replay is not skipped"
    expected: "Owner accepts the window (server resolves the whole envelope before the first header, so the graph lock is already released) or asks for the fix (runStream holds its own InFlight.begin('query') until readStream settles)"
    why_human: "Literal LIVE-06 text says never while a query is in flight; the review rated it info and left it open"
  - test: "18-11 Task 3 after approval: link LIVE-01..09 (test_ref, code_ref, record-fail at each RED commit, status done) via scripts/ledger-amend.py"
    expected: "All nine LIVE rows done in the BAK records"
    why_human: "Gated by the 18-11 prohibition: no row is linked before the owner approves"
---

# Phase 18: GUI Live Verification Report

**Phase Goal:** The operator runs the whole console against the live engine (query, compare, evidence, trace, ingest, corpus, health, ledger and graph/vector browsing) from a browser served by the launcher
**Verified:** 2026-10-31
**Status:** human_needed
**Re-verification:** No (initial verification)

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SC1: launcher bound to 127.0.0.1 serves the console; a UI query completes with no CORS error; header shows live /health | VERIFIED | `serve_rest.py` has `--console`, `GET /console` with `include_in_schema=False`, hash CSP, loopback and fixed-port refusals (lines 49-187). Tests: test_page_fetch_post_query_returns_200_without_cors_errors, test_console_needs_a_loopback_host, test_console_needs_a_fixed_port, test_header_health_shows_the_live_health_result, test_header_shows_unreachable_when_the_health_fetch_is_rejected, test_header_shows_checking_then_times_out_after_60_seconds |
| 2 | SC2: query, stream, compare live; early-closed stream shows disconnected; one-selector bare vs keyed-map compare; every run in client history; refusals, 422 and 500 render through error states | VERIFIED | `05-api.js` holds the only `fetch(` call; `20-query.js:341` checks `res.ok` and `text/event-stream` before parsing; `showDisconnected()` renders the mockup's stream-disconnected generic variant; `21-compare.js:390-395` decides bare vs map by count sent. Tests: test_stream_renders_evidence_then_final, test_early_closed_stream_shows_disconnected, test_stream_ignores_comment_lines, test_compare_one_selector_is_parsed_as_a_bare_envelope, test_compare_two_selectors_fills_each_column_from_its_own_key, test_each_run_lands_in_the_history, plus 26 test_live_03 error cases across all six screens |
| 3 | SC3: evidence one request per ref per session; trace re-requested with debug; ingest, upload, delete with Query disabled during a write; corpus refreshes after delete; health and counts poll only when allowed | VERIFIED (with warning R18-07) | `30-evidence.js:156` cache hit returns with no request; `/trace/resolve` sends `{trace_reference, debug}`; `20-query.js` and `21-compare.js` gate Run on `InFlight.writing()`; `50-corpus.js:190` skips a health tick on `InFlight.any()`; NON_TERMINAL gate for counts. Tests: test_open_resolves_the_envelope_ref_unchanged_once_per_session, test_trace_loads_then_re_requests_in_detail_mode, test_query_run_is_disabled_while_an_ingest_is_in_flight, test_confirmed_delete_refreshes_corpus_and_counts_and_the_row_is_gone, test_health_poll_skips_ticks_while_a_query_is_in_flight, test_counts_poll_only_while_a_non_terminal_count_is_above_zero. Warning: R18-07 (streamed query leaves InFlight at headers) is open |
| 4 | SC4: promote a trace to an alias then query through it; rollback and retire from the timeline; browse nodes, node edges, chunks by selector; store-busy refusal while the graph is held | VERIFIED | test_promote_then_query_through_the_alias asserts the exact POST /promote body and the follow-up alias query; test_rollback_and_retire_through_the_timeline_update_the_rows; test_nodes_list_and_node_edges_by_selector; test_chunks_open_in_the_evidence_inspector; test_store_busy_renders_the_refusal_and_retry_recovers holds a raw `pycozo.Client` on `ws/hipporag-graph/graph.cozo` and asserts StoreBusyError, 'store busy', 'HTTP 409.', no generic view, and Retry repeats the request; test_no_namespace_input_on_the_graph_screen |
| 5 | SC5: a control keeps its needs-backend badge exactly when its route is absent from live /openapi.json; no mockup control removed; frozen mockup id check exits 0 | VERIFIED | test_badge_kept_exactly_when_the_route_is_absent compares the remaining badges to the app's own /openapi.json in three launch modes; test_expected_badge_counts_per_launch_mode; test_no_mockup_control_is_removed; test_mockup_id_check_exits_0. Run by the verifier: `scripts/mockup-id-check.py --root .` exit 0, `mockups/build.py --check` exit 0, console `build.py --src ... --out ... --check` exit 0, sha256 of `mockups/operator-console.html` = bf98e79e...4d20, no working-tree change under `mockups/` or `databasise/console/` |
| 6 | 18-11: owner click-through with real clients approved, including D-15 LightRAG query-after-ingest and answers A-D | UNCERTAIN (owner-deferred) | 18-11 Task 2 not run; owner postponed it. No approval exists. Routed to Human Verification |
| 7 | 18-11: LIVE-01..09 linked in the BAK records with test_ref, code_ref, record-fail, status done | UNCERTAIN (owner-deferred) | Task 3 runs only after approval and has not run. `git log` shows no LIVE linking or record-fail commit; session start reports 9 open rows. This also confirms the 18-11 prohibition holds (no row linked before approval) |

**Score:** 5/7 truths verified (0 present, behavior-unverified; 2 pending owner)

Backstop (held-out) truths with explicit passing test evidence in the 141-pass run: 12 evidence rows (test_more_evidence_rows_than_slots_all_render), 50 of 60 history (test_history_shows_the_50_newest_of_60), extra server key column (test_compare_extra_server_key_appends_a_column), /openapi.json failure keeps badges (test_openapi_failure_keeps_every_badge), busy chips 0/1/2 (test_store_busy_chips_zero_one_many). The two 375 px visual backstops have no test and are listed for the owner.

### Required Artifacts

`gsd-tools verify.artifacts` on all eleven plans: 29/29 passed (18-01 5/5, 18-02 4/4, 18-03 3/3, 18-04 3/3, 18-05..18-10 2/2 each, 18-11 2/2). All console modules are loaded into the single built `databasise/console/operator-console.html`, which the console build check reproduces from `databasise/console/src/` (exit 0).

### Key Link Verification

`gsd-tools verify.key-links`: 21/22 verified. The one unverified link is 18-11's `scripts/ledger-amend.py record-fail -> each LIVE row's RED commit`, which is Task 3 (owner-gated, not run) and is also malformed (the `to` is not a file path). Not a code wiring gap.

### Data-Flow Trace (Level 4)

| Artifact | Data | Source | Real data | Status |
|----------|------|--------|-----------|--------|
| 20-query.js | answer, evidence rows, tokens | POST /query and /query/stream through `api()` | yes, rendered from the response envelope | FLOWING |
| 21-compare.js | columns | POST /compare, keyed by server comparison key | yes | FLOWING |
| 30-evidence.js | record, trace node table | POST /evidence/resolve, POST /trace/resolve | yes | FLOWING |
| 50-corpus.js | rows, KPI tiles | GET /corpus, GET /corpus/counts | yes | FLOWING |
| 70-graph.js | nodes, edges, chunks | POST /graph/nodes, /graph/node, /chunks | yes | FLOWING |
| screen fixtures | n/a | removed from the live build in 252c4551 | n/a | removed |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Frozen mockup unchanged | sha256sum mockups/operator-console.html | bf98e79e...4d20 | PASS |
| Frozen build reproduces | python mockups/build.py --check | exit 0 | PASS |
| Live console build in sync | python mockups/build.py --src databasise/console/src --out databasise/console/operator-console.html --check | exit 0 | PASS |
| Frozen id check | python scripts/mockup-id-check.py --root . | exit 0, no output | PASS |
| Live GUI suite | orchestrator run, DATABASISE_REQUIRE_BROWSER=1 | 141 passed at HEAD | PASS (cited, not re-run) |

### Probe Execution

Not applicable: no probe scripts declared in the phase plans.

### Requirements Coverage

| Requirement | Source Plan | Status | Evidence |
|-------------|-------------|--------|----------|
| LIVE-01 | 18-01, 18-02, 18-03, 18-11 | SATISFIED in code | Truth 1 |
| LIVE-02 | 18-04, 18-05, 18-11 | SATISFIED in code | Truth 2 |
| LIVE-03 | 18-04..18-10, 18-11 | SATISFIED in code (deviation C pending owner acknowledgement) | 26 test_live_03 cases |
| LIVE-04 | 18-06, 18-11 | SATISFIED in code | Truth 3 |
| LIVE-05 | 18-08, 18-11 | SATISFIED in code | Truth 3 |
| LIVE-06 | 18-07, 18-11 | SATISFIED in code (warning R18-07) | Truth 3 |
| LIVE-07 | 18-05, 18-09, 18-11 | SATISFIED in code | Truth 4 |
| LIVE-08 | 18-10, 18-11 | SATISFIED in code | Truth 4 |
| LIVE-09 | 18-01, 18-03, 18-11 | SATISFIED in code | Truth 5 |

All nine IDs mapped to Phase 18 in REQUIREMENTS.md are claimed by at least one plan. No orphaned requirements. REQUIREMENTS.md still lists them as Pending, and the BAK rows stay open until 18-11 Task 3.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (all phase-18 console js, html, serve_rest.py) | - | TBD/FIXME/XXX | none found | - |
| databasise/console/src/js/05-api.js | 40-63 | R18-07: raw (stream) call releases InFlight at headers | Warning | Health poll tick during SSE replay is not skipped; server work is already done by then |
| databasise/console/src/js/20-query.js | 260-275 | R18-10: raw selector JSON bypasses picker blockers | Info | Server still refuses by name |
| R18-12..R18-15 | - | build tool, start-up traceback, sessionStorage text, comment escaping | Info | Advisory, per 18-REVIEW-DISPOSITION |

### Human Verification Required

1. **Owner click-through (18-11 Task 2, D-20).** Start `databasise-rest --operator --console --log-file` on 127.0.0.1 with real clients, open /console, walk the five success criteria, approve.
2. **D-15 LightRAG ingest-then-query** on a real store. Expected: evidence from the ingested document.
3. **Store-busy from another process.** Expected: StoreBusyError state, HTTP 409, Retry recovers.
4. **375 px visual check** of log tail, response excerpt and corpus poll indicators.
5. **Default A:** keep the store-split notice (or remove it).
6. **Default B:** the two 18-07 planner assumptions.
7. **Default C:** acknowledge the LIVE-03 typed-refusal deviation.
8. **Default D:** accept the R18-05 arm-neutral alias wording.
9. **R18-07 decision:** accept the streamed-query InFlight window or request the fix.
10. **After approval:** run 18-11 Task 3 to link LIVE-01..09.

### Gaps Summary

No code gaps. All five roadmap success criteria are implemented, wired and exercised by the stub-client Playwright suite (141 passed). The phase is not complete: plan 18-11 has two truths that depend only on the owner click-through, which the owner postponed, and four provisional defaults (A-D) plus the R18-07 decision wait for the owner.

---

_Verified: 2026-10-31_
_Verifier: Claude (gsd-verifier)_
