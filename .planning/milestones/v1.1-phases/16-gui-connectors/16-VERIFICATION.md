---
phase: 16-gui-connectors
verified: 2026-11-01T07:25:00Z
status: passed
score: 19/19 must-haves verified (5 roadmap SCs + 14 CONN requirements)
covered_files:
  - .planning/phases/16-gui-connectors/16-01-PLAN.md
  - .planning/phases/16-gui-connectors/16-01-SUMMARY.md
  - .planning/phases/16-gui-connectors/16-02-PLAN.md
  - .planning/phases/16-gui-connectors/16-02-SUMMARY.md
  - .planning/phases/16-gui-connectors/16-03-PLAN.md
  - .planning/phases/16-gui-connectors/16-03-SUMMARY.md
  - .planning/phases/16-gui-connectors/16-04-PLAN.md
  - .planning/phases/16-gui-connectors/16-04-SUMMARY.md
  - .planning/phases/16-gui-connectors/16-05-PLAN.md
  - .planning/phases/16-gui-connectors/16-05-SUMMARY.md
  - .planning/phases/16-gui-connectors/16-06-PLAN.md
  - .planning/phases/16-gui-connectors/16-06-SUMMARY.md
  - .planning/phases/16-gui-connectors/16-07-PLAN.md
  - .planning/phases/16-gui-connectors/16-07-SUMMARY.md
  - .planning/phases/16-gui-connectors/16-08-PLAN.md
  - .planning/phases/16-gui-connectors/16-08-SUMMARY.md
  - .planning/phases/16-gui-connectors/16-09-PLAN.md
  - .planning/phases/16-gui-connectors/16-09-SUMMARY.md
  - .planning/phases/16-gui-connectors/16-10-PLAN.md
  - .planning/phases/16-gui-connectors/16-10-SUMMARY.md
  - .planning/phases/16-gui-connectors/16-11-PLAN.md
  - .planning/phases/16-gui-connectors/16-11-SUMMARY.md
  - .planning/phases/16-gui-connectors/16-12-PLAN.md
  - .planning/phases/16-gui-connectors/16-12-SUMMARY.md
  - databasise/evidence/COVERAGE.md
  - databasise/launcher/serve_rest.py
  - databasise/ledger/ledger.py
  - databasise/parts_core/__init__.py
  - databasise/seam/engine.py
  - databasise/seam/operator_rest.py
  - databasise/seam/refusals.py
  - databasise/seam/rest.py
  - databasise/seam/trace_store.py
  - databasise/stores/graph.py
  - databasise/stores/probes.py
  - databasise/stores/vector.py
  - databasise/tests/fixtures/selector-resolution.json
  - docs/gui/API-INVENTORY.md
  - docs/gui/CODEBASE-MAP.md
  - docs/gui/refusals.json
covered_digest: "v3:sha256:9f57a3632255805c497b2c2c906045518edc331bab7ea0ace1bafed11a93dc82"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: passed
  previous_score: 19/19
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 16: GUI Connectors Verification Report

**Phase Goal:** The operator console has every read route it needs, served by the launcher's single engine through thin adapters, with nothing leaking store internals or credentials
**Verified:** 2026-11-01T07:25:00Z (re-verification at HEAD 0d9cabcf after the 2026-11-01 audit fixes; prior re-verification 2026-11-01T00:45:26Z at 4e4dc0f after Phase 18; 2026-10-31 at 7147047; original verdict 2026-10-22T16:15:00Z at 2505402)
**Status:** passed
**Re-verification:** Yes. The first report went stale because docs/gui/API-INVENTORY.md was amended by Phase 17-13 (commit f674eba). The second report went stale because Phase 18-02 (commits eff8804, 65dd699) changed databasise/launcher/serve_rest.py and docs/gui/API-INVENTORY.md; see "Re-verification 2026-10-31 (Phase 18 staleness)" below. The third report went stale because the 2026-11-01 debugging and security battery changed seven covered files (base 3aafcc62); see "Re-verification 2026-11-01 (audit fixes)" below.

### Re-verification 2026-11-01 (audit fixes)

- **Stale cause.** `git diff --stat 3aafcc62 HEAD` over the covered files touches exactly seven: databasise/seam/engine.py (30 changed lines), operator_rest.py (4), refusals.py (192), rest.py (17), stores/graph.py (17), stores/probes.py (14) and docs/gui/refusals.json (8 added). serve_rest.py, ledger.py, trace_store.py, vector.py, parts_core/__init__.py, COVERAGE.md, API-INVENTORY.md, CODEBASE-MAP.md and selector-resolution.json are byte-identical to the version verified at 4e4dc0f. Every change is a test-first bug fix (RED/GREEN commit pairs listed in the audit change digest); none adds a route, a field or a tool.
- **What changed on the Phase 16 paths.** (a) 717d2f22: `GET /log` no longer declares `ge=1, le=1000` on the query parameter (operator_rest.py:144-147); `log_tail` checks `1 <= limit <= MAX_LOG_LINES` (engine.py:420, 2482-2483) and raises `PageBoundsError(limit=limit, offset=0)`. The D-18 bound 1..1000 is unchanged; only the error shape moved from FastAPI's schema `{detail: [...]}` to the named refusal body the other paged routes return. The route body is still one `return await engine.log_tail(limit)`. (b) 32e518ea: `ledger_history` calls `require_encodable(alias, field="alias")` before the read (engine.py:2225), so a lone-surrogate alias is a 422 `NonEncodableTextError` instead of a 500 from sqlite's binding. (c) 7a07da50/5c00aabc/13fda6a6: `refusals.py` gained `json_safe`, `bounded_echo` (ECHO_LIMIT 200, ECHO_ITEMS 20), `NonEncodableTextError` (attribute `field`) and `require_encodable`; `UnknownGraphNodeError`, `UnknownTraceReferenceError`, `InvalidPromotionAliasError` and the other echoing refusals bound the caller value they echo; `rest.py`'s `_validation_response` now emits `type`/`loc`/`msg` only (no `input` echo) through `bounded_echo`/`json_safe`. docs/gui/refusals.json gained the `NonEncodableTextError` entry (51 -> 52 types). (d) 5aec6294: `list_traces` and the ledger read path add `OverflowError` to the `StoreFault` excepts (engine.py:1959, 2270). (e) a895ef8a: `_ClientRegistry.release` keeps a client registered at refcount 0 when pycozo refuses `close()` under an in-flight `run()`, logs a warning and never raises (graph.py:177-189); `held_graph_paths` (graph.py:191-201) filters `refcount > (key in own)`, so a deferred-close entry at refcount 0 is never reported as held and `graph_busy` is unaffected. (f) 4bfdb8db: `probe_kv` opens plain `mode=ro` when both `-wal` and `-shm` exist; this is the health probe, not a Phase 16 read path (`acquire_graph`, `graph_node_page`, `graph_node_edges` are unchanged apart from moving down four lines). (g) 62d7ba91: `_held_by_v1` reads v1's track id via `asyncio.to_thread`; a Phase 11 ingest path, not an operator route.
- **Re-checked rows.** SC1/CONN-01 (thin adapters, flag-gated): `test_console_surface.py::test_operator_routes_are_thin_adapters_and_absent_without_the_flag` passes at HEAD, and `create_app` still builds one `Databasise` (rest.py:377-381) and mounts the routes only under `if operator:` (rest.py:552-556). SC2/goal clause "nothing leaking": a fresh-root `/info` body has keys `clients, graph_busy, version, workspace, write_in_flight` and neither it nor `/wirings` (six rows) contains `store_root`, the tmp path or `http`. SC3/CONN-07: a surrogate alias on `POST /ledger/history` is `422 {"refusal_type":"NonEncodableTextError","field":"alias"}`; an unknown alias is an empty page and creates no `ledger.db`. SC4/CONN-12: a 5,000-character unknown node id is a `422 UnknownGraphNodeError` whose body is 560 bytes (bounded echo); `capability: []` is still `EmptyCapabilitySelectorError`. SC5/CONN-02: `test_refusal_catalogue_file.py` passes against the 52-entry catalogue. SC5/CONN-14: `GET /log?limit=0` and `limit=1001` are `422 PageBoundsError` (previously 422 schema detail; status code unchanged), `limit=2` returns the two file lines, `limit=abc` is the bounded schema 422 without an `input` echo; `test_console_log.py` (four tests incl. the real operator launch) and `tests/launcher/test_log_file_refusal.py` pass. CONN-13: `test_store_busy_fields_are_true_during_an_ingest`, `test_status_during_write.py` and `test_graph_lock.py` pass; the registry change is covered by `tests/stores/test_graph_release_under_run.py`. The API-INVENTORY.md 5.1a row for `GET /log` ("query `limit` 1..1000, default 100") remains true.
- **Regression run at HEAD 0d9cabcf.** The 20 Phase 16 covering test files (nine test_console_*.py, test_operator_review_a/b, test_refusal_catalogue_file, test_selector_resolution_fixture, test_rest_transport, test_status_during_write, stores/test_graph_read_review_c, stores/test_graph_lock, launcher/test_log_file_refusal, ledger/test_ledger_read_only_close, mcp/test_tool_growth_invariant): 171 passed. The fix-round tests that touch these paths (test_surrogate_after_promotion, test_input_bounds incl. `test_log_limit_out_of_range_is_page_bounds_error` and `test_log_limit_in_range_still_tails`, stores/test_graph_release_under_run, stores/test_probe_kv_live_writer, test_response_builders_hardening, test_surrogate_inputs): 71 passed. Scratchpad spot-check p16rv/spot.py (TestClient, clients=None, operator=True, log_path set) produced the bodies quoted above.
- **Not rerun.** The manual launcher 500-traceback check and the 14 ledger test_refs (the code under them is unchanged except the `OverflowError` except widening, which only adds a caught class); the browser-driven LIVE-01 tests belong to Phase 18. Known consequence outside this phase: three Phase 17 mockup tests fail on the 51 -> 52 catalogue count until the mockup is rebuilt and re-frozen (owner item, recorded in the audit change digest). Goal still holds; no regression found.

### Re-verification 2026-10-31 (Phase 18 staleness)

- **Stale cause.** `git diff eff8804~1 HEAD` over the covered files touches exactly two: databasise/launcher/serve_rest.py and docs/gui/API-INVENTORY.md. The same diff over databasise/evidence, databasise/parts_core, databasise/seam, databasise/stores, databasise/tests/fixtures, docs/gui/CODEBASE-MAP.md and docs/gui/refusals.json is empty, and the ledger module is likewise unchanged in the commit log, so every Phase 16 engine method, operator route, probe, store and fixture is byte-identical to the version verified on 2026-10-31.
- **What changed in serve_rest.py.** An opt-in `--console` flag (serve_rest.py:48-52); `console_csp()` (serve_rest.py:59-87), which builds a Content-Security-Policy from the sha256 hashes of the page's single inline script and single style block and raises at start-up if the counts differ; a `GET /console` route mounted only under `--console`, `include_in_schema=False`, returning the packaged `databasise/console/operator-console.html` bytes read once at start-up with fixed security headers (CSP, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `Cache-Control: no-store`) (serve_rest.py:126-143); and two parser refusals in `main` requiring a loopback `--host` and a fixed `--port` for `--console` (serve_rest.py:185-191). The `--operator` and `--log-file` arguments, the `create_app(operator=..., log_path=...)` call, the TrustedHost and Origin guards, `log_config_for` and the `--log-file` pre-open refusal are unchanged apart from moving down the file; the Phase 16 line references in this report were updated to the new positions.
- **Re-checked rows.** SC1 and CONN-01 (routes gated by `--operator`): `build_app` still passes `operator=getattr(args, "operator", False)` into the one `create_app`, and `--console` does not imply `--operator` (`test_console_does_not_imply_operator` passes). SC2/goal clause "nothing leaking store internals or credentials": the new route serves a static packaged file with constant headers, reads nothing from the engine or the store, and the packaged page contains zero occurrences of `store_root`, `/home/`, `api_key`, `apikey` or `x-api-key`; the headers carry no path, URL, model name or key. The OpenAPI surface is unchanged (`test_openapi_is_identical_with_and_without_the_flag` passes), so the documented Phase 16 route contract is the same with and without the flag. SC5/CONN-14 (`/log` tails the launcher log): `log_config_for` (serve_rest.py:148-169) and the `uvicorn.run(..., log_config=...)` call (serve_rest.py:216-217) are unchanged. The single-engine, thin-adapter claim is unaffected: operator_rest.py and rest.py did not change.
- **API-INVENTORY.md.** The only change is one additive paragraph at line 766 describing `--console` and `GET /console` (loopback host, fixed port, does not imply `--operator`, hidden from `/openapi.json`); each statement matches serve_rest.py:141, 185-191. The 5.1a operator route table and refusal columns are unchanged and still match operator_rest.py.
- **Regression run at HEAD 4e4dc0f.** `.venv/bin/python -m pytest tests/launcher tests/seam -q -p no:cacheprovider -k "console or operator or rest_transport or refusal_catalogue or selector_resolution or status_during_write or launch or log_file or bind_guard or store_lock"`: 241 passed, 1008 deselected. This covers all nine test_console_*.py files, the operator review files, catalogue, fixture, transport, write-status and every tests/launcher file. Plus tests/gui_live/test_live_01_serving.py non-browser subset (route absent without the flag, OpenAPI identity, console does not imply operator, CSP refuses a two-script page, loopback-host and fixed-port refusals): 6 passed.
- **Not rerun.** The manual launcher 500-traceback check and the 14 ledger test_refs, since the code under them is unchanged; the browser-driven LIVE-01 tests belong to Phase 18's verification. Goal still holds; no regression found.

### Re-verification Delta (2026-10-31)

- **Stale cause.** Only docs/gui/API-INVENTORY.md changed among the covered files. `git diff 727afb1..HEAD` over databasise/launcher, ledger, parts_core, seam, stores, evidence, tests/fixtures and docs/gui shows no change to any Phase 16 code file, the COVERAGE.md rows, refusals.json or selector-resolution.json; the only docs/gui changes are API-INVENTORY.md plus new Phase 17 files (GAP-ROUTES.json, INVENTORY-MAP.json, MOCK-IDS.json, MOCKUP-APPROVAL.md).
- **What the amendment touched.** It edits the /health engine paragraph (3.4.1, Phase 11 route), the /corpus and /corpus/counts Gaps text (3.4.2, 3.4.3, Phase 12 selector parameter), adds proposed routes 15 and 16 to the Phase 17+ route list (POST /graph/node/attrs, GET /corpus filters), and adds one note to the 5.1a operator-routes section about the mockup badge. The 5.1a route table (the Phase 16 contract) is unchanged.
- **Amended claims checked against code.** HealthReport carries `clients` and `engine_reason` (databasise/seam/corpus.py:312-342); `/corpus` and `/corpus/counts` accept the JSON `selector` query parameter via `_selector_field` (rest.py:317-327); `POST /documents/{id}/retry` exists. The new badge note says ten operator routes; docs/gui/GAP-ROUTES.json lists exactly ten `kind: operator` entries whose paths equal the ten routes in the 5.1a table. No TBD/FIXME/XXX in the file. The Phase 16 operator documentation (routes, refusals, exceptions) is intact and does not contradict the code.
- **Regression check at HEAD.** 9 test_console_*.py files: 43 passed. Review, catalogue, fixture, transport, write-gate, graph, launcher, ledger and MCP-coverage files (11 files): 127 passed. Same counts as the first run. Truths whose behavior tests were rerun: CONN-09 preview equals mint, CONN-11 busy 409, CONN-13 flags during an ingest, CONN-14 /log.
- **Requirements cross-reference.** All 14 CONN IDs are declared in the phase PLAN frontmatter (CONN-14 in 16-11 and 16-12; CONN-01..13 across the others), checked `[x]` in REQUIREMENTS.md lines 695-742 and "Complete" in the traceability table lines 971-984. No orphans. This closes the earlier bookkeeping note about CONN-13/14 showing `[ ]`.
- **Not rerun.** The manual launcher log check and the 14 ledger test_refs from the first run were not repeated, since the code under them is byte-identical; the full offline gate belongs to the orchestrator.


Full offline gate (`databasise/tools/check_offline_suite.py`): **reported by orchestrator** (not run by the verifier, per instruction). This verdict rests on the targeted runs below; if the orchestrator's gate is red, this status must be revisited.

## Goal Achievement

### Observable Truths (Roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC1 | Operator read routes served from the launcher's process by the single engine through thin adapters; each new operation has an MCP tool with a COVERAGE.md row or is recorded REST-only | VERIFIED | `create_app` builds one `Databasise` and passes it to `add_operator_routes` (databasise/seam/rest.py:377-381, 552-556). Every route body in databasise/seam/operator_rest.py:80-147 is one `return await engine.<method>(...)`. COVERAGE.md REST-ONLY rows for all ten operations (databasise/evidence/COVERAGE.md:120-129). Spot check: all ten paths are 404 without `operator=True`. Tests: test_console_surface.py, test_rest_transport.py, test_tool_growth_invariant.py pass. |
| SC2 | Instance info and wiring list without store_root, base URLs, model names or keys, and without any provider call; write-in-flight and graph-busy readable during an ingest | VERIFIED | engine.py:2134-2155 (`info`, `_write_in_flight`), engine.py:2157-2184 (`wirings`, reachability via `resolve_selector`). Spot check on a fresh root: /info and /wirings bodies contain no store_root, no "http", no codebase-memory row; six rows naive 7, bypass 1, hybrid 17, local 15, global 15, hipporag 14; `is_default` only naive; `default_eligible` false only for hipporag; all reachable. `test_store_busy_fields_are_true_during_an_ingest` passes (behavioral). |
| SC3 | List aliases, page alias history with active/tombstoned flags, list traces newest first, preview a promotion that writes nothing and matches what /promote mints | VERIFIED | engine.py:2186-2261 (`ledger_aliases`, `ledger_history` under `snapshot()`, `require_encodable` on the alias at 2225), engine.py:2263-2288 (`list_traces`), engine.py:2290-2362 (`preview_promotion` sharing `_promotion_prologue`/`_plan_promotion`, engine.py:2896), ledger.py:531-550, trace_store.py:103-121. Spot check: fresh root gives `[]`, empty history page, no `ledger.db`; limit 0 -> PageBoundsError, 101 -> PageSizeExceededError; unknown trace -> 404 UnknownTraceReferenceError. `test_preview_matches_what_promote_mints_and_refuses` passes (preview == minted version). |
| SC4 | Page chunk refs and graph nodes (batched degrees, prefix filter), open a node's edges, chosen by selector only; unknown node and busy graph are named refusals | VERIFIED | engine.py:2364-2467; probes.py:143-232 (one ordered id statement plus one batched `is_in` edge query per page, probes.py:177-188); vector.py:293-299 (`list_ids`, no reconstruct). Request models take a `selector`, never a namespace (operator_rest.py:46-72). Spot check: unknown node -> 422 UnknownGraphNodeError; malformed selector -> 422; `capability: []` -> EmptyCapabilitySelectorError. `test_graph_nodes_page_degrees_prefix_and_busy_409` passes (busy 409 behavioral). |
| SC5 | Generated refusal catalogue and selector-resolution fixture kept in sync by tests; flag-gated GET /log tails the launcher's log (404 without the flag) | VERIFIED | docs/gui/refusals.json (52 entries incl. UnknownGraphNodeError and NonEncodableTextError, 422); databasise/tests/fixtures/selector-resolution.json (29 rows: default, 17 effects, 3 namespace tokens, harness, 6 aliases, empty capability; `reachable` for all six arms). GET /log mounted only when `operator` and `log_path` (rest.py:552-556, operator_rest.py:132-147); limit outside 1..1000 is PageBoundsError from `log_tail` (engine.py:2482-2483). Manual launcher check below: real 500 traceback lands in the file and is served by GET /log. |

### CONN Requirements (amended 2026-10-22)

| Req | Delivering code | Covering test (run at HEAD) | Status |
|-----|-----------------|-----------------------------|--------|
| CONN-01 | operator_rest.py:75-147; rest.py:377-381, 552-556; COVERAGE.md:120-133 | test_console_surface.py::test_operator_routes_are_thin_adapters_and_absent_without_the_flag; test_rest_transport.py; test_tool_growth_invariant.py | VERIFIED |
| CONN-02 | docs/gui/refusals.json; refusals.py (UnknownGraphNodeError, NonEncodableTextError) | test_refusal_catalogue_file.py::test_the_refusal_catalogue_file_matches_the_code | VERIFIED |
| CONN-03 | databasise/tests/fixtures/selector-resolution.json; selectors.py | test_selector_resolution_fixture.py::test_every_fixture_row_resolves_as_recorded | VERIFIED |
| CONN-04 | engine.py:2134-2150 (`__version__` import engine.py:203; `_client_presence`) | test_console_info.py::test_info_reports_version_workspace_and_client_presence | VERIFIED |
| CONN-05 | engine.py:2157-2184 | test_console_wirings.py::test_wirings_lists_six_reachable_rows_matching_the_fixture | VERIFIED |
| CONN-06 | engine.py:2186-2215; ledger.py:531-539 | test_console_ledger.py::test_aliases_lists_each_alias_once_and_creates_no_file; tests/ledger/test_ledger_read_only_close.py | VERIFIED |
| CONN-07 | engine.py:2217-2261; ledger.py:541-550; `checked_page` in operator_rest.py:98 | test_console_ledger.py::test_history_flags_active_and_tombstoned_and_bounds_the_page; test_surrogate_after_promotion.py::test_a_surrogate_history_alias_is_the_named_422_on_the_operator_route | VERIFIED |
| CONN-08 | engine.py:2263-2288; trace_store.py:103-121 | test_console_traces.py::test_traces_list_newest_first_with_paging | VERIFIED |
| CONN-09 | engine.py:2290-2362, 2896 (`_plan_promotion`) | test_console_preview.py::test_preview_matches_what_promote_mints_and_refuses | VERIFIED |
| CONN-10 | engine.py:2364-2388 (namespace from `wiring_family` base wiring, no `_build_stores`); vector.py:293-299 | test_console_chunks.py::test_chunks_page_lists_the_selected_modalitys_refs | VERIFIED |
| CONN-11 | engine.py:2414-2442; probes.py:158-196 | test_console_graph.py::test_graph_nodes_page_degrees_prefix_and_busy_409 (fail-first and killed plant on ledger) ; tests/stores/test_graph_read_review_c.py | VERIFIED |
| CONN-12 | engine.py:2444-2467; probes.py:199-232; refusals.py UnknownGraphNodeError (bounded echo) | test_console_graph.py::test_graph_node_edges_and_unknown_node_422 (killed plant on ledger) | VERIFIED |
| CONN-13 | engine.py:2134-2155; graph.py:191-201 (`held_graph_paths`, own-hold excluded; deferred-close entries at refcount 0 never counted); engine.py:2398-2412 (`_hold_graph`) | test_console_info.py::test_store_busy_fields_are_true_during_an_ingest; test_status_during_write.py; test_graph_lock.py; tests/stores/test_graph_release_under_run.py | VERIFIED |
| CONN-14 | serve_rest.py:38-47, 90-106, 148-169, 200-217; engine.py:420, 2469-2511; operator_rest.py:132-147 | test_console_log.py::test_log_tails_the_launcher_log_and_is_404_without_both_flags; test_input_bounds.py::test_log_limit_out_of_range_is_page_bounds_error; tests/launcher/test_log_file_refusal.py; plus the manual launcher check below | VERIFIED |

**Score:** 19/19 truths verified (0 present, behavior-unverified). The behavior-dependent truths (CONN-09 preview equals mint, CONN-11 busy 409, CONN-13 flags during an in-flight ingest) each have a named behavioral test that passed in this run.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| databasise/seam/operator_rest.py | ten thin-adapter routes | VERIFIED | 147 lines; mounted only by `create_app(operator=True)` |
| databasise/seam/engine.py (operator methods) | info, wirings, ledger_aliases, ledger_history, list_traces, preview_promotion, chunk_page, graph_nodes, graph_node, log_tail | VERIFIED | lines 2132-2511 |
| databasise/stores/probes.py | `acquire_graph`, `graph_node_page`, `graph_node_edges` | VERIFIED | no `CozoGraphStore` on the read path |
| databasise/stores/vector.py | `FaissVectorStore.list_ids` | VERIFIED | reads the entry map only |
| databasise/seam/trace_store.py | `TraceStore.list_page` | VERIFIED | page and count in one read transaction |
| databasise/ledger/ledger.py | `Ledger.aliases`, `history_for_alias`, `snapshot` | VERIFIED | `LedgerEntry` carries id and created_at |
| databasise/launcher/serve_rest.py | `--operator`, `--log-file`, `log_config_for` | VERIFIED | bad log file refused before the store lock; Phase 18 added `--console` and `GET /console` without touching these |
| docs/gui/refusals.json | refusal catalogue | VERIFIED | 52 entries (51 + NonEncodableTextError), test-synced |
| databasise/tests/fixtures/selector-resolution.json | selector fixture | VERIFIED | 29 rows, 6 reachable flags |
| databasise/evidence/COVERAGE.md | REST-ONLY rows and exceptions | VERIFIED | rows 120-129, D-02/D-09/D-10/D-19 bullets 136-143 |

### Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| serve_rest.build_app | create_app | `operator=`, `log_path=` (serve_rest.py:99-106) | WIRED |
| create_app | add_operator_routes | `if operator:` with `log=log_path is not None` (rest.py:552-556) | WIRED |
| operator routes | app.state.engine | the same `engine` object (rest.py:377-381) | WIRED |
| engine.graph_nodes/graph_node | probes.graph_node_page/edges | `asyncio.to_thread` plus `_hold_graph` | WIRED |
| engine.info | graph.held_graph_paths, write gates | `own=self._graph_holds`, `_gate_for(...).locked()` | WIRED |
| serve_rest.main | uvicorn file logging | `log_config_for(args.log_file)` (serve_rest.py:216-217) | WIRED (proved by the manual launcher check) |

### Data-Flow Trace (Level 4)

| Artifact | Data | Source | Real data | Status |
|----------|------|--------|-----------|--------|
| /ledger/aliases, /ledger/history | rows | ledger.db via read-only `Ledger.open_existing` | yes | FLOWING |
| /traces | items | trace.db `SELECT ... ORDER BY created_at DESC` | yes | FLOWING |
| /chunks | refs | committed Faiss snapshot entry map | yes | FLOWING |
| /graph/nodes, /graph/node | nodes, edges | Cozo immutable queries | yes | FLOWING |
| /log | lines | the `--log-file` file, redacted per line | yes | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 14 ledger test_refs | `databasise/.venv/bin/python -m pytest -q <14 node ids> -p no:cacheprovider -v` | 14 passed | PASS |
| Console test files | pytest on the 9 test_console_*.py files (test_console_info.py run separately) | 40 passed + 3 passed | PASS |
| Review, catalogue, fixture, transport, lock, launcher, ledger, MCP coverage | pytest on test_operator_review_a/b, test_refusal_catalogue_file, test_selector_resolution_fixture, test_rest_transport, test_status_during_write, stores/test_graph_read_review_c, stores/test_graph_lock, launcher/test_log_file_refusal, ledger/test_ledger_read_only_close, mcp/test_tool_growth_invariant | 127 passed | PASS |
| Surface and leak check on a fresh tmp root | scratchpad p16v/surface_check.py (TestClient, clients=None) | 10 routes 404 without operator; /log 404 without log_path; no store_root/URL in /info or /wirings; only trace.db created (no ledger.db) | PASS |
| Unknown trace on preview | scratchpad p16v/preview_check.py | 404 UnknownTraceReferenceError | PASS |
| Real 500 traceback reaches --log-file and GET /log | scratchpad p16v/log500_check.py: real `serve_rest.main(["--operator","--log-file",tmp,"--no-clients","--store-root",tmp,"--port",free])` in a subprocess, `Databasise.wirings` patched to raise | /wirings 500; server.log line 8 `ERROR uvicorn.error: Exception in ASGI application` with the injected RuntimeError traceback; GET /log?limit=1000 returned 72 lines including the traceback; `Uvicorn running on <url>` redacted; limit=0 and 1001 -> 422; server kept answering /info after the 500 | PASS |
| Phase 18 staleness rerun (HEAD 4e4dc0f) | `.venv/bin/python -m pytest tests/launcher tests/seam -q -p no:cacheprovider -k "console or operator or rest_transport or refusal_catalogue or selector_resolution or status_during_write or launch or log_file or bind_guard or store_lock"` | 241 passed, 1008 deselected | PASS |
| /console route gating and OpenAPI identity (HEAD 4e4dc0f) | `.venv/bin/python -m pytest tests/gui_live/test_live_01_serving.py -q -p no:cacheprovider -k "absent_without_the_flag or openapi_is_identical or does_not_imply_operator or refuses_a_page_with_two_scripts or needs_a_loopback_host or needs_a_fixed_port"` | 6 passed, 8 deselected | PASS |
| Packaged console page leak scan | grep -c on databasise/console/operator-console.html for `store_root`, `/home/`, `api_key`/`apikey`/`x-api-key` | 0, 0, 0 | PASS |
| Audit-fix rerun, Phase 16 covering files (HEAD 0d9cabcf) | `.venv/bin/python -m pytest <20 covering test files> -q -p no:cacheprovider` | 171 passed | PASS |
| Audit-fix rerun, fix-round tests on Phase 16 paths (HEAD 0d9cabcf) | `.venv/bin/python -m pytest tests/seam/test_surrogate_after_promotion.py tests/seam/test_input_bounds.py tests/stores/test_graph_release_under_run.py tests/stores/test_probe_kv_live_writer.py tests/seam/test_response_builders_hardening.py tests/seam/test_surrogate_inputs.py -q -p no:cacheprovider` | 71 passed | PASS |
| /log error shape, surrogate alias, leak and bounded-echo check (HEAD 0d9cabcf) | scratchpad p16rv/spot.py (TestClient, clients=None, operator=True, log_path set) | limit 0 and 1001 -> 422 PageBoundsError; limit 2 -> `{"lines":["a","b"]}`; limit abc -> schema 422 without `input`; surrogate alias -> 422 NonEncodableTextError field alias; unknown alias -> empty page, no ledger.db; /info keys clients/graph_busy/version/workspace/write_in_flight, no store_root/path/http; /wirings 6 rows, no path/http; 5,000-char node id -> 422 UnknownGraphNodeError, 560-byte body; `capability: []` -> EmptyCapabilitySelectorError | PASS |
| Full offline gate | check_offline_suite.py | reported by orchestrator | not run here |

Note on the launcher check: the 500 was induced by patching one engine method in the child process, not by a naturally occurring fault; the launcher, uvicorn, the log config and GET /log were all the real code. A first attempt with the child's console on an unread pipe stalled the server after the traceback; that was the test harness's unread pipe, and the rerun with the console written to a file was clean.

### Probe Execution

Step 7c: no probes declared by the phase; `scripts/*/tests/probe-*.sh` not applicable (not a migration phase). SKIPPED.

### Requirements Coverage

All 14 CONN IDs are declared by the plans and mapped to Phase 16 in REQUIREMENTS.md; no orphaned IDs. All SATISFIED (table above).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| all 13 non-test files changed in d608162..HEAD | - | TBD/FIXME/XXX/TODO/HACK/placeholder | none found | - |
| databasise/seam/engine.py | 2501 | `shortcut:` full read per /log call | Info | documented limit |
| databasise/stores/probes.py | 176 | `shortcut:` O(N) ids per page | Info | documented limit |
| databasise/seam/trace_store.py | 108 | `shortcut:` full sort per page | Info | documented limit |
| databasise/seam/refusals.py | 72 | `shortcut:` bounded_echo caps dict values, not key count | Info | documented limit (audit fix 5c00aabc) |

### Carried Items (recorded, not failures)

1. **503 declaration residual.** The operator store-reading routes declare 503 in OpenAPI but no route raises a 503 class. Pinned by the 16-CONTEXT D-01 OpenAPI line and a protected CONN-11 test; needs an owner amendment to drop (16-REVIEW-DISPOSITION A-WR-04, ITER2-IN-03). Info.
2. **graph_busy sees in-process holders only.** This is by design (D-17) and stated in the amended CONN-13; the console must label it "in use", not "locked". Info.
3. **Preview `next_version` can go stale under a concurrent write.** Stated in CONN-09 and in the route description. Info.

### Bookkeeping Notes (not goal gaps)

- .planning/REQUIREMENTS.md still shows CONN-13 and CONN-14 as `[ ]` (lines 738, 742) and "Pending" in the traceability table (lines 981-982), while the code, the tests and the ledger rows say done. The orchestrator should tick them on phase completion.
- The CONN row texts in the ledger file are the pre-amendment wording (examples: CONN-02 "30 today", CONN-05 "hipporag 13", CONN-10 "through `_build_stores`", CONN-14 "operator or debug flag"). The code follows the amended REQUIREMENTS.md. The ledger hook also reports trace files stale against the REQUIREMENTS.md hash. Re-sync the ledger texts if the ledger is meant to mirror the amended wording.
- 16-VALIDATION.md is still `status: draft`, `nyquist_compliant: false`; its one manual-only item is now recorded above as PASS.

### Human Verification Required

None. The one deferred human-check (16-12-PLAN.md:241, 16-VALIDATION.md manual-only row) was run offline by the verifier and passed.

### Gaps Summary

No gaps. Every roadmap success criterion and every amended CONN requirement has delivering code at HEAD and a covering test that passed in this run. The review fixes (C-CR-01, C-WR-01/02, B-WR-01..05, A-WR-03/04, ITER2-WR-01) are present in the code read here and their covering tests passed.

---

_Verified: 2026-11-01T07:25:00Z (original 2026-10-22T16:15:00Z)_
_Verifier: Claude (gsd-verifier)_
