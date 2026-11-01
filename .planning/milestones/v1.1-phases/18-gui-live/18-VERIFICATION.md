---
phase: 18-gui-live
verified: 2026-11-01T20:27:47Z
status: passed
score: 7/7 must-haves verified (5/5 roadmap success criteria verified in code; 2 plan 18-11 owner-gated truths verified after the owner approval of 2026-11-01 and 18-11 Task 3)
covered_files: [".planning/phases/18-gui-live/18-01-PLAN.md", ".planning/phases/18-gui-live/18-01-SUMMARY.md", ".planning/phases/18-gui-live/18-02-PLAN.md", ".planning/phases/18-gui-live/18-02-SUMMARY.md", ".planning/phases/18-gui-live/18-03-PLAN.md", ".planning/phases/18-gui-live/18-03-SUMMARY.md", ".planning/phases/18-gui-live/18-04-PLAN.md", ".planning/phases/18-gui-live/18-04-SUMMARY.md", ".planning/phases/18-gui-live/18-05-PLAN.md", ".planning/phases/18-gui-live/18-05-SUMMARY.md", ".planning/phases/18-gui-live/18-06-PLAN.md", ".planning/phases/18-gui-live/18-06-SUMMARY.md", ".planning/phases/18-gui-live/18-07-PLAN.md", ".planning/phases/18-gui-live/18-07-SUMMARY.md", ".planning/phases/18-gui-live/18-08-PLAN.md", ".planning/phases/18-gui-live/18-08-SUMMARY.md", ".planning/phases/18-gui-live/18-09-PLAN.md", ".planning/phases/18-gui-live/18-09-SUMMARY.md", ".planning/phases/18-gui-live/18-10-PLAN.md", ".planning/phases/18-gui-live/18-10-SUMMARY.md", ".planning/phases/18-gui-live/18-11-PLAN.md", ".planning/phases/18-gui-live/18-11-SUMMARY.md", "databasise/console/__init__.py", "databasise/console/operator-console.html", "databasise/console/src/css/00-base.css", "databasise/console/src/css/20-query.css", "databasise/console/src/css/21-compare.css", "databasise/console/src/css/30-evidence.css", "databasise/console/src/css/40-documents.css", "databasise/console/src/css/50-corpus.css", "databasise/console/src/css/60-ledger.css", "databasise/console/src/css/70-graph.css", "databasise/console/src/dialogs/delete.html", "databasise/console/src/dialogs/promote.html", "databasise/console/src/dialogs/retire.html", "databasise/console/src/dialogs/rollback.html", "databasise/console/src/js/00-app.js", "databasise/console/src/js/05-api.js", "databasise/console/src/js/10-shared.js", "databasise/console/src/js/20-query.js", "databasise/console/src/js/21-compare.js", "databasise/console/src/js/30-evidence.js", "databasise/console/src/js/40-documents.js", "databasise/console/src/js/50-corpus.js", "databasise/console/src/js/60-ledger.js", "databasise/console/src/js/70-graph.js", "databasise/console/src/js/90-start.js", "databasise/console/src/page.html", "databasise/console/src/parts/errors.html", "databasise/console/src/parts/selector.html", "databasise/console/src/screens/corpus.html", "databasise/console/src/screens/documents.html", "databasise/console/src/screens/evidence.html", "databasise/console/src/screens/graph.html", "databasise/console/src/screens/ledger.html", "databasise/console/src/screens/query.html", "databasise/launcher/serve_rest.py", "databasise/pyproject.toml", "databasise/tests/gui_live/__init__.py", "databasise/tests/gui_live/_corpus_fake.py", "databasise/tests/gui_live/_opened.py", "databasise/tests/gui_live/conftest.py", "databasise/tests/gui_live/test_live_01_serving.py", "databasise/tests/gui_live/test_live_02_query_compare.py", "databasise/tests/gui_live/test_live_03_errors.py", "databasise/tests/gui_live/test_live_04_evidence_trace.py", "databasise/tests/gui_live/test_live_05_documents.py", "databasise/tests/gui_live/test_live_06_corpus_health.py", "databasise/tests/gui_live/test_live_07_ledger.py", "databasise/tests/gui_live/test_live_08_graph.py", "databasise/tests/gui_live/test_live_09_badges_ids.py", "docs/gui/API-INVENTORY.md", "mockups/build.py", "mockups/operator-console.html"]
covered_digest: "v3:sha256:8f9848a358096b917281ea3dcadeed1b1e2e4ffbf721cab9c44e1987a82bff86"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 5/7
  previous_verified: 2026-11-01T07:20:41Z
  trigger: owner answers of 2026-11-01 (click-through Approved), R18-07 fix (RED 13dd2334, GREEN 416b5e5e), 18-11 Task 3 run (SUMMARY 04728d47, kit record 82764feb)
  gaps_closed:
    - "18-11: owner click-through with real clients approved, including D-15 LightRAG query-after-ingest and answers A-D"
    - "18-11: LIVE-01..09 linked in the BAK records with test_ref, code_ref, record-fail, status done"
    - "R18-07 warning on SC3 (streamed query left InFlight at the headers)"
  gaps_remaining: []
  regressions: []
  history:
    - previous_status: human_needed
      previous_score: 5/7
      previous_verified: 2026-10-31T00:00:00Z
      trigger: staleness trip; audit bug-fix commits 6fdf0d2b, 3714c830, 4834188e, 3b82b241, 1323f01b touched covered console sources and gui_live tests after 3aafcc62
human_verification_resolved:
  - test: "Owner click-through (18-11 Task 2, D-20): start databasise-rest --operator --console --log-file on 127.0.0.1 with real model clients, open /console, walk the five success criteria and approve"
    expected: "Query, stream, compare, evidence, trace, ingest, upload, delete, corpus, health, ledger and graph screens work against real clients with no CORS error and the header showing live /health"
    why_human: "The offline suite uses stub clients and an in-process uvicorn; real provider spend and the real CLI launch are owner-only (D-19, D-20)"
    resolution: "Owner 2026-11-01: \"Approved\""
  - test: "D-15 LightRAG default path: ingest a document with the default selector, then query it"
    expected: "The query returns evidence from the ingested document"
    why_human: "The offline stub does not populate the v2 stores; only the HippoRAG query-after-ingest is automated (test_query_after_hipporag_ingest_returns_that_documents_evidence)"
    resolution: "Covered by the owner click-through \"Approved\" (2026-11-01); real-client check"
  - test: "Store-busy from another process: hold the graph store from a second OS process while browsing Graph"
    expected: "graph.state.store-busy with StoreBusyError, 'store busy', 'HTTP 409.'; Retry recovers once released"
    why_human: "The automated case holds a raw pycozo client in the same process as the app"
    resolution: "Covered by the owner click-through \"Approved\" (2026-11-01); real-client check"
  - test: "375 px visual checks: log tail and 500-character excerpt wrap and scroll inside 240 px; corpus poll indicators wrap to two lines without horizontal scroll"
    expected: "No horizontal scroll; text wraps with overflow-wrap anywhere"
    why_human: "Backstop truths in 18-04 and 18-07 with no automated test; visual layout"
    resolution: "Covered by the owner click-through \"Approved\" (2026-11-01); visual check"
  - test: "Confirm provisional default A: keep documents.notice.store-split visible with its frozen text (roadmap open question 8, D-15 amendment)"
    expected: "Owner answers keep or remove; removal is a one-line follow-up in the live source"
    why_human: "Owner decision deferred by D-15 amendment"
    resolution: "Owner 2026-11-01: \"Keep notice\"; no console change"
  - test: "Confirm provisional default B: the two 18-07 planner assumptions (unknown stores keys appended as rows with a state badge from the value; unknown counts chips wrap with no cap)"
    expected: "Owner confirms or rejects each"
    why_human: "Unresolved UI consideration inherited from Phase 17"
    resolution: "Owner 2026-11-01: \"Accept as assumed\""
  - test: "Confirm provisional default C: the LIVE-03 typed-refusal deviation (a multi-member selector renders the typed MultiMemberSelectorError banner per SEAM-02, not a field error)"
    expected: "Owner answers acknowledged or asks for a different rendering"
    why_human: "Named deviation from the LIVE-03 text, recorded in 18-04"
    resolution: "Owner 2026-11-01: \"Acknowledged\""
  - test: "Confirm provisional default D: R18-05 arm-neutral alias wording on Documents (Target, upload notice, result card, Delete dialog, seam toggle) when the alias arm is unknown"
    expected: "Owner accepts arm-neutral wording or asks for an alias-arm lookup"
    why_human: "Default chosen while the click-through is postponed (18-REVIEW-DISPOSITION R18-05)"
    resolution: "Owner 2026-11-01: \"Store-neutral\"; wording of a0483f4e kept"
  - test: "Decide on R18-07: a streamed query leaves InFlight when response headers arrive, so a health poll tick during the SSE event replay is not skipped"
    expected: "Owner accepts the window (server resolves the whole envelope before the first header, so the graph lock is already released) or asks for the fix (runStream holds its own InFlight.begin('query') until readStream settles)"
    why_human: "Literal LIVE-06 text says never while a query is in flight; the review rated it info and left it open"
    resolution: "Owner 2026-11-01: \"Fix it\"; fixed test-first in 13dd2334 (RED) and 416b5e5e (GREEN); test_stream_holds_inflight_until_the_body_settles[close|error] passes"
  - test: "18-11 Task 3 after approval: link LIVE-01..09 (test_ref, code_ref, record-fail at each RED commit, status done) via scripts/ledger-amend.py"
    expected: "All nine LIVE rows done in the BAK records"
    why_human: "Gated by the 18-11 prohibition: no row is linked before the owner approves"
    resolution: "Ran after approval: 27 kit commands (versions 916 to 942), each row exit 1 at its RED commit and green at HEAD, status done; recorded in 82764feb; session-start kit summary reports open=0"
---

# Phase 18: GUI Live Verification Report

**Phase Goal:** The operator runs the whole console against the live engine (query, compare, evidence, trace, ingest, corpus, health, ledger and graph/vector browsing) from a browser served by the launcher
**Verified:** 2026-10-31 (initial); re-verified 2026-11-01T07:20:41Z after the audit bug fixes; re-verified 2026-11-01T20:27:47Z after the owner approval, the R18-07 fix and 18-11 Task 3
**Status:** passed
**Re-verification:** Yes (staleness trip after bug-fix commits; see "Re-verification 2026-11-01 (audit fixes)" below; then the owner answers, see "Re-verification 2026-11-01 (owner approval, R18-07, 18-11 Task 3)"). Initial verification 2026-10-31.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SC1: launcher bound to 127.0.0.1 serves the console; a UI query completes with no CORS error; header shows live /health | VERIFIED | `serve_rest.py` has `--console`, `GET /console` with `include_in_schema=False`, hash CSP, loopback and fixed-port refusals (lines 49-187). Tests: test_page_fetch_post_query_returns_200_without_cors_errors, test_console_needs_a_loopback_host, test_console_needs_a_fixed_port, test_header_health_shows_the_live_health_result, test_header_shows_unreachable_when_the_health_fetch_is_rejected, test_header_shows_checking_then_times_out_after_60_seconds |
| 2 | SC2: query, stream, compare live; early-closed stream shows disconnected; one-selector bare vs keyed-map compare; every run in client history; refusals, 422 and 500 render through error states | VERIFIED | `05-api.js` holds the only `fetch(` call; `20-query.js:341` checks `res.ok` and `text/event-stream` before parsing; `showDisconnected()` renders the mockup's stream-disconnected generic variant; `21-compare.js:390-395` decides bare vs map by count sent. Tests: test_stream_renders_evidence_then_final, test_early_closed_stream_shows_disconnected, test_stream_ignores_comment_lines, test_compare_one_selector_is_parsed_as_a_bare_envelope, test_compare_two_selectors_fills_each_column_from_its_own_key, test_each_run_lands_in_the_history, plus 26 test_live_03 error cases across all six screens. Re-verified 2026-11-01: SessionLog (05-api.js:125-150) now drops entries whose stored selector is malformed; test_malformed_history_entry_does_not_stop_the_console and test_each_run_lands_in_the_history pass. Re-verified 2026-11-01T20:27Z after R18-07 (416b5e5e): the res.ok / content-type check now sits at 20-query.js:343; the readStream chain is still returned and `remember(env, body)` still runs on a "result" (20-query.js:374), so streamed runs still land in the history; test_stream_renders_evidence_then_final, test_early_closed_stream_shows_disconnected and test_each_run_lands_in_the_history pass |
| 3 | SC3: evidence one request per ref per session; trace re-requested with debug; ingest, upload, delete with Query disabled during a write; corpus refreshes after delete; health and counts poll only when allowed | VERIFIED | `30-evidence.js:156` cache hit returns with no request; `/trace/resolve` sends `{trace_reference, debug}`; `20-query.js` and `21-compare.js` gate Run on `InFlight.writing()`; `50-corpus.js:190` skips a health tick on `InFlight.any()`; NON_TERMINAL gate for counts. Tests: test_open_resolves_the_envelope_ref_unchanged_once_per_session, test_trace_loads_then_re_requests_in_detail_mode, test_query_run_is_disabled_while_an_ingest_is_in_flight, test_confirmed_delete_refreshes_corpus_and_counts_and_the_row_is_gone, test_health_poll_skips_ticks_while_a_query_is_in_flight, test_counts_poll_only_while_a_non_terminal_count_is_above_zero. Warning: R18-07 (streamed query leaves InFlight at headers) is open. Re-verified 2026-11-01: Corpus Retry now also follows `InFlight.writing()` (50-corpus.js:229-246, `Console.on("inflight", syncWrites)` at :555, write-note in corpus.html:150); the Documents jobs poll reloads quietly (40-documents.js:330, 433-446) so error banners stay visible; test_retry_is_disabled_while_another_write_is_in_flight, test_jobs_poll_keeps_a_visible_error_banner, test_health_poll_skips_ticks_while_a_query_is_in_flight, test_confirmed_delete_refreshes_corpus_and_counts_and_the_row_is_gone, test_query_run_is_disabled_while_an_ingest_is_in_flight pass. Re-verified 2026-11-01T20:27Z: the R18-07 warning is closed. `runStream` takes `InFlight.begin("query")` (20-query.js:338) and the raw `api()` call no longer passes `kind` (:339), so 05-api.js:40 registers nothing for it; the whole chain, including the returned `readStream(...).then(...)`, ends in `.then(done, done)` (:375), so the count drops only after the body settles on success, error, refusal, unreachable or abort. `done` is idempotent (05-api.js:8-16). `InFlight.any()` therefore stays true for the whole SSE replay and `50-corpus.js:190` skips the health tick. test_stream_holds_inflight_until_the_body_settles[close] and [error] (added in RED 13dd2334, failed there with `assert 0 == 1`) pass, with test_health_poll_skips_ticks_while_a_query_is_in_flight and test_counts_poll_only_while_a_non_terminal_count_is_above_zero |
| 4 | SC4: promote a trace to an alias then query through it; rollback and retire from the timeline; browse nodes, node edges, chunks by selector; store-busy refusal while the graph is held | VERIFIED | test_promote_then_query_through_the_alias asserts the exact POST /promote body and the follow-up alias query; test_rollback_and_retire_through_the_timeline_update_the_rows; test_nodes_list_and_node_edges_by_selector; test_chunks_open_in_the_evidence_inspector; test_store_busy_renders_the_refusal_and_retry_recovers holds a raw `pycozo.Client` on `ws/hipporag-graph/graph.cozo` and asserts StoreBusyError, 'store busy', 'HTTP 409.', no generic view, and Retry repeats the request; test_no_namespace_input_on_the_graph_screen. Re-verified 2026-11-01: the timeline clears its loading state when the page size is invalid (60-*.js:592-595); the Graph screen writes graph.selector.family from the picker arm, arm-neutral when unknown (70-graph.js:14-15, 360-361); test_invalid_page_size_during_an_in_flight_load_leaves_no_loading_state, test_selector_family_line_follows_the_arm, test_rollback_and_retire_through_the_timeline_update_the_rows, test_store_busy_renders_the_refusal_and_retry_recovers, test_nodes_list_and_node_edges_by_selector pass |
| 5 | SC5: a control keeps its needs-backend badge exactly when its route is absent from live /openapi.json; no mockup control removed; frozen mockup id check exits 0 | VERIFIED | test_badge_kept_exactly_when_the_route_is_absent compares the remaining badges to the app's own /openapi.json in three launch modes; test_expected_badge_counts_per_launch_mode; test_no_mockup_control_is_removed; test_mockup_id_check_exits_0. Run by the verifier: `scripts/mockup-id-check.py --root .` exit 0, `mockups/build.py --check` exit 0, console `build.py --src ... --out ... --check` exit 0, sha256 of `mockups/operator-console.html` = bf98e79e...4d20, no working-tree change under `mockups/` or `databasise/console/`. Re-verified 2026-11-01: id check exit 0, live console build check exit 0, frozen mockup sha256 unchanged (bf98e79e...4d20), test_no_mockup_control_is_removed and test_mockup_id_check_exits_0 pass; the one added corpus.html element (write-note) carries no data-mock-id so the frozen catalogue is untouched. `mockups/build.py --check` on the frozen mockup now exits 1 ("stale") because docs/gui/refusals.json gained a 52nd type in Phase 17's scope (7a07da50), not because of any Phase 18 source; owner rebuild-and-refreeze item recorded in the change digest. Re-verified 2026-11-01T20:27Z: after the owner re-freeze (cda59dc3) the frozen sha256 is 3ac0e278c929ba41179249a47606edb910ae4b6032b1d0acb9fc19a739c0c837; `mockups/build.py --check` exits 0 again; id check exits 0; live console build check exits 0 |
| 6 | 18-11: owner click-through with real clients approved, including D-15 LightRAG query-after-ingest and answers A-D | VERIFIED | (Was UNCERTAIN, owner-deferred: 18-11 Task 2 not run; owner postponed it. No approval exists. Routed to Human Verification.) Re-verified 2026-11-01T20:27Z: the owner answered on 2026-11-01, click-through "Approved", A "Keep notice", B "Accept as assumed", C "Acknowledged", D "Store-neutral", R18-07 "Fix it", debug-trace redaction "Keep literal cause" (see "Human Verification Resolution (owner, 2026-11-01)"). Recorded in 18-11-SUMMARY.md key-decisions and "Owner answers", commit 04728d47 |
| 7 | 18-11: LIVE-01..09 linked in the BAK records with test_ref, code_ref, record-fail, status done | VERIFIED | (Was UNCERTAIN, owner-deferred: Task 3 runs only after approval and has not run. `git log` shows no LIVE linking or record-fail commit; session start reports 9 open rows. This also confirms the 18-11 prohibition holds (no row linked before approval).) Re-verified 2026-11-01T20:27Z: Task 3 ran after the approval and after the R18-07 test edit: 9 set, 9 record-fail (each exit 1 at its RED commit, control green at HEAD), 9 set-status done, kit versions 916 to 942, committed in 82764feb (HEAD). The session-start kit summary now reports ledger_version 942, open=0, checksums ok. The prohibition held: the linking commit 82764feb follows the approval and the R18-07 commits 13dd2334 and 416b5e5e |

**Score:** 5/7 truths verified (0 present, behavior-unverified; 2 pending owner)

**Score (re-verified 2026-11-01T20:27Z):** 7/7 truths verified (0 present, behavior-unverified; 0 pending owner)

Backstop (held-out) truths with explicit passing test evidence in the 141-pass run: 12 evidence rows (test_more_evidence_rows_than_slots_all_render), 50 of 60 history (test_history_shows_the_50_newest_of_60), extra server key column (test_compare_extra_server_key_appends_a_column), /openapi.json failure keeps badges (test_openapi_failure_keeps_every_badge), busy chips 0/1/2 (test_store_busy_chips_zero_one_many). The two 375 px visual backstops have no test and are listed for the owner.

### Required Artifacts

`gsd-tools verify.artifacts` on all eleven plans: 29/29 passed (18-01 5/5, 18-02 4/4, 18-03 3/3, 18-04 3/3, 18-05..18-10 2/2 each, 18-11 2/2). All console modules are loaded into the single built `databasise/console/operator-console.html`, which the console build check reproduces from `databasise/console/src/` (exit 0).

### Key Link Verification

`gsd-tools verify.key-links`: 21/22 verified. The one unverified link is 18-11's `scripts/ledger-amend.py record-fail -> each LIVE row's RED commit`, which is Task 3 (owner-gated, not run) and is also malformed (the `to` is not a file path). Not a code wiring gap.

Re-verified 2026-11-01T20:27Z: the 22nd link is now satisfied in substance. Task 3 ran nine `record-fail --at <RED sha>` commands (18-11-SUMMARY.md, record-fail table), each recorded exit 1 at its RED commit; the tool still cannot parse the link because its `to` is not a file path.

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
| (2026-11-01) Frozen mockup unchanged | sha256sum mockups/operator-console.html | bf98e79e0a0312940963efae9028e708a012021bfc62f51ebdbca57918034d20 | PASS |
| (2026-11-01) Frozen build reproduces | python mockups/build.py --check | exit 1, "mockups/operator-console.html is stale" | CHANGED, not a Phase 18 regression: refusals.json 51 -> 52 types (Phase 17 catalogue, commit 7a07da50); the frozen file itself is byte-identical; owner rebuild-and-refreeze item |
| (2026-11-01) Live console build in sync | python mockups/build.py --src databasise/console/src --out databasise/console/operator-console.html --check | exit 0 | PASS |
| (2026-11-01) Frozen id check | python scripts/mockup-id-check.py --root . | exit 0, no output | PASS |
| (2026-11-01) Targeted gui_live tests on the changed modules | pytest tests/gui_live -k (5 new tests + 9 regression tests named in truths 2-5) | 14 passed, 132 deselected in 31 s (146 collected) | PASS |
| (2026-11-01) Full gui_live suite | orchestrator run at HEAD, DATABASISE_REQUIRE_BROWSER=1 | 146 passed | PASS (cited from the audit change digest; not re-run under load) |
| (2026-11-01T20:27Z) Frozen mockup after owner re-freeze | sha256sum mockups/operator-console.html | 3ac0e278c929ba41179249a47606edb910ae4b6032b1d0acb9fc19a739c0c837 (cda59dc3) | PASS |
| (2026-11-01T20:27Z) Frozen build reproduces | python3 mockups/build.py --check | exit 0 | PASS (the earlier exit 1 is resolved by the re-freeze) |
| (2026-11-01T20:27Z) Live console build in sync | python3 mockups/build.py --src databasise/console/src --out databasise/console/operator-console.html --check | exit 0 | PASS |
| (2026-11-01T20:27Z) Frozen id check | python3 scripts/mockup-id-check.py --root . | exit 0, no output | PASS |
| (2026-11-01T20:27Z) R18-07 and criterion 2/3 tests by name | pytest -k (test_stream_holds_inflight_until_the_body_settles, test_health_poll_skips_ticks_while_a_query_is_in_flight, test_counts_poll_only_while_a_non_terminal_count_is_above_zero, test_each_run_lands_in_the_history, test_stream_renders_evidence_then_final, test_early_closed_stream_shows_disconnected), DATABASISE_REQUIRE_BROWSER=1 | 7 passed, 3375 deselected in 9.04 s | PASS (run by the verifier) |
| (2026-11-01T20:27Z) Full gui_live suite | orchestrator run at HEAD, DATABASISE_REQUIRE_BROWSER=1 | 148 passed (146 + the 2 parametrized R18-07 cases) | PASS (cited from the orchestrator and 18-11-SUMMARY.md; not re-run) |
| (2026-11-01T20:27Z) Working tree clean of phase sources | git status --short | only .planning/state.json, trace/rounds.jsonl and untracked non-source paths | PASS |

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

Re-verified 2026-11-01T20:27Z: all nine are SATISFIED. LIVE-03 deviation C is acknowledged by the owner ("Acknowledged"); the LIVE-06 warning R18-07 is fixed (416b5e5e). 18-11 Task 3 has run: the nine BAK rows are linked, proven fail-first and done (82764feb). REQUIREMENTS.md was not edited by this verification; `phase.complete` marks the rows.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (all phase-18 console js, html, serve_rest.py) | - | TBD/FIXME/XXX | none found | - |
| databasise/console/src/js/05-api.js | 40-63 | R18-07: raw (stream) call releases InFlight at headers | Warning | Health poll tick during SSE replay is not skipped; server work is already done by then |
| databasise/console/src/js/20-query.js | 260-275 | R18-10: raw selector JSON bypasses picker blockers | Info | Server still refuses by name |
| R18-12..R18-15 | - | build tool, start-up traceback, sessionStorage text, comment escaping | Info | Advisory, per 18-REVIEW-DISPOSITION |
| (2026-11-01T20:27Z) databasise/console/src/js/20-query.js | 337-339, 375 | R18-07 resolved: runStream holds its own InFlight("query") and releases it after the body settles; the raw call passes no kind | Resolved | The 05-api.js warning above no longer applies to the stream path |
| (2026-11-01T20:27Z) 20-query.js, operator-console.html (416b5e5e diff) | - | TBD/FIXME/XXX | none found | - |

### Re-verification 2026-11-01 (audit fixes)

Trigger: the covered-file digest tripped after five test-first bug-fix commits from the 2026-11-01 debugging and security battery landed on top of 3aafcc62: 6fdf0d2b (Corpus Retry disabled with a visible write-note while any ingest, upload or delete is in flight), 3714c830 (the 30 s jobs poll reloads quietly, keeping error banners and the drawer), 4834188e (graph.selector.family written from the picker arm, arm-neutral when unknown), 3b82b241 (an invalid timeline page size clears the loading state after dropping the read in flight), 1323f01b (SessionLog drops a stored entry with a malformed selector; selectorLabel/comparisonKey tolerate a non-array capability). Changed covered sources: 05-api.js, 10-shared.js, 40-documents.js, 50-corpus.js, 60-*.js, 70-graph.js, screens/corpus.html, the rebuilt operator-console.html, and tests/gui_live test_live_02/05/06/07/08 (five new tests, 146 total). No new source file; the covered_files list is unchanged and only covered_digest moved.

What was re-checked: the full diff of every changed console source against 3aafcc62 (51 insertions, 11 deletions, all defensive or gating additions; no fetch path, status-code handling, route, refusal name or error-state renderer changed; `05-api.js` is still the only `fetch(` site), the wiring of each addition (`Console.emit("inflight")` exists in 05-api.js:10,15 and is consumed by the new `syncWrites` in 50-corpus.js:555; `control(row, "retry")` at 50-corpus.js:224; `Picker.arm()` at 10-shared.js:228; `graph.selector.family` at graph.html:49), the line numbers cited in truths 2-3 and the anti-pattern table (30-evidence.js:156, 20-query.js:341, 21-compare.js:390-395, 50-corpus.js:190, 05-api.js:40-63 all unchanged because every edit lands below them), and the five roadmap success criteria against the changed sources. Targeted tests: the five new tests plus nine regression tests named in truths 2-5 (store lifecycle: store-busy refusal and Retry recovery, rollback and retire, delete-then-refresh, Run disabled during a write, health poll skip) pass, 14/14, with 132 deselected (146 collected at HEAD, matching the cited full run).

Result: the goal still holds exactly as before. No regression found. The one changed spot-check (frozen `mockups/build.py --check` exit 1) is caused by docs/gui/refusals.json growing to 52 types in a Phase 17-scoped fix, not by any Phase 18 source: the frozen mockup file is byte-identical, the id check exits 0, the live console build reproduces, and the Phase 18 suite is unaffected. That is an owner rebuild-and-refreeze item for Phase 17 (three locked tests/gui mockup tests fail for the same reason, per the change digest). Status stays human_needed with the same ten owner items; the two 18-11 truths remain owner-gated.

### Re-verification 2026-11-01 (owner approval, R18-07, 18-11 Task 3)

Trigger: the owner answered the ten open items on 2026-11-01; R18-07 was fixed test-first (RED 13dd2334, GREEN 416b5e5e); 18-11 Task 3 ran (SUMMARY 04728d47; kit record 82764feb, HEAD); the phase 18 S5 code trace was refreshed (d6f1806b, 4d609b43); the owner re-froze the mockup (cda59dc3). The covered_files list gains `.planning/phases/18-gui-live/18-11-SUMMARY.md`; `test_live_02_query_compare.py` was already listed. covered_digest regenerated with `verification.fingerprint`.

What was re-checked:

- R18-07 diff (`git show 416b5e5e`): 2 files, `20-query.js` (+3/-1 in source plus one comment line) and the rebuilt `operator-console.html`. `runStream` now calls `var done = InFlight.begin("query")` before `api("POST", "/query/stream", body, { raw: true, signal: mine.signal })`, and the outer promise ends in `.then(done, done)`. The inner handler returns `readStream(...).then(...)` and `res.text().then(...)`, so `done` waits for the body on every path; the early returns (abort, superseded controller, status 0) release it at once. `InFlight.begin` returns an idempotent closure (05-api.js:8-16), and `api()` registers nothing when `opts.kind` is absent (05-api.js:40), so the count cannot be released twice or dropped at the headers.
- Criterion 2 (streamed query, history): the response handling and `remember(env, body)` are unchanged apart from the wrapper; the streamed run still lands in the history. test_stream_renders_evidence_then_final, test_early_closed_stream_shows_disconnected and test_each_run_lands_in_the_history pass.
- Criterion 3 (health and counts poll only when allowed): `50-corpus.js:190` skips a health tick on `InFlight.any()`, which now holds for the whole SSE replay. test_stream_holds_inflight_until_the_body_settles[close] and [error] assert `InFlight.counts.query == 1` and `InFlight.any()` while the body is open, then 0 after it closes or errors; both failed at 13dd2334 (`assert 0 == 1`, per 18-11-SUMMARY.md) and pass at HEAD. test_health_poll_skips_ticks_while_a_query_is_in_flight and test_counts_poll_only_while_a_non_terminal_count_is_above_zero pass. Verifier run: 7 passed, 3375 deselected in 9.04 s. Orchestrator full run: tests/gui_live 148/148 at HEAD.
- Criterion 5: frozen sha256 3ac0e278c929ba41179249a47606edb910ae4b6032b1d0acb9fc19a739c0c837 after the re-freeze; frozen build check, live build check and id check all exit 0.
- 18-11 truths: owner answers recorded verbatim in 18-11-SUMMARY.md and below; Task 3 commands, RED shas and kit versions 916 to 942 recorded in 18-11-SUMMARY.md and committed in 82764feb; the session-start kit summary reports open=0 with checksums ok.

Item-by-item resolution of the ten human items:

| # | Item | Resolved by |
|---|------|-------------|
| 1 | Owner click-through (18-11 Task 2, D-20) | Owner: "Approved" |
| 2 | D-15 LightRAG ingest-then-query on a real store | Owner: "Approved" (real-client check inside the click-through) |
| 3 | Store-busy from another process | Owner: "Approved" (real-client check inside the click-through) |
| 4 | 375 px visual check | Owner: "Approved" (visual check inside the click-through) |
| 5 | Default A | Owner: "Keep notice" |
| 6 | Default B | Owner: "Accept as assumed" |
| 7 | Default C | Owner: "Acknowledged" |
| 8 | Default D | Owner: "Store-neutral" |
| 9 | R18-07 decision | Owner: "Fix it"; fixed in 13dd2334 (RED) and 416b5e5e (GREEN) |
| 10 | 18-11 Task 3 | Ran after approval; LIVE-01..09 done (82764feb) |

Result: no item remains open, no regression found, no new gap. Status moves to passed, score 7/7.

### Human Verification Resolution (owner, 2026-11-01)

The owner's answers, verbatim:

- Click-through: "Approved".
- A: "Keep notice".
- B: "Accept as assumed".
- C: "Acknowledged".
- D: "Store-neutral".
- R18-07: "Fix it".
- Debug-trace redaction: "Keep literal cause".

The "Approved" answer covers every item that only real clients could test: real provider spend, the D-15 ingest-then-query, store-busy from a second process, and the 375 px check.

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

All ten items above are resolved as of 2026-11-01; see "Human Verification Resolution (owner, 2026-11-01)" and the item table in the 2026-11-01 owner-approval re-verification. None remain open.

### Gaps Summary

No code gaps. All five roadmap success criteria are implemented, wired and exercised by the stub-client Playwright suite (141 passed at the initial verification; 146 passed at HEAD after the 2026-11-01 audit fixes). The phase is not complete: plan 18-11 has two truths that depend only on the owner click-through, which the owner postponed, and four provisional defaults (A-D) plus the R18-07 decision wait for the owner.

Re-verified 2026-11-01T20:27Z: no gaps remain. The owner approved the click-through and answered A-D; R18-07 is fixed and tested; 18-11 Task 3 linked and closed LIVE-01..09; tests/gui_live passes 148/148 at HEAD. The phase is complete.

---

_Verified: 2026-10-31; re-verified 2026-11-01T07:20:41Z; re-verified 2026-11-01T20:27:47Z_
_Verifier: Claude (gsd-verifier)_
