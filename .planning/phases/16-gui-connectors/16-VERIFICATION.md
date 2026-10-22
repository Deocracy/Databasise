---
phase: 16-gui-connectors
verified: 2026-10-22T16:15:00Z
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
covered_digest: "v3:sha256:946f86491067fc59bb65c85c974bc3f8a8a1a4c917a3f7ff5184d3e52e73c1e8"
behavior_unverified: 0
overrides_applied: 0
---

# Phase 16: GUI Connectors Verification Report

**Phase Goal:** The operator console has every read route it needs, served by the launcher's single engine through thin adapters, with nothing leaking store internals or credentials
**Verified:** 2026-10-22T16:15:00Z (code at HEAD 2505402, after the review fix rounds)
**Status:** passed
**Re-verification:** No (initial verification)

Full offline gate (`databasise/tools/check_offline_suite.py`): **reported by orchestrator** (not run by the verifier, per instruction). This verdict rests on the targeted runs below; if the orchestrator's gate is red, this status must be revisited.

## Goal Achievement

### Observable Truths (Roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC1 | Operator read routes served from the launcher's process by the single engine through thin adapters; each new operation has an MCP tool with a COVERAGE.md row or is recorded REST-only | VERIFIED | `create_app` builds one `Databasise` and passes it to `add_operator_routes` (databasise/seam/rest.py:370-374, 545-549). Every route body in databasise/seam/operator_rest.py:80-145 is one `return await engine.<method>(...)`. COVERAGE.md REST-ONLY rows for all ten operations (databasise/evidence/COVERAGE.md:120-129). Spot check: all ten paths are 404 without `operator=True`. Tests: test_console_surface.py, test_rest_transport.py, test_tool_growth_invariant.py pass. |
| SC2 | Instance info and wiring list without store_root, base URLs, model names or keys, and without any provider call; write-in-flight and graph-busy readable during an ingest | VERIFIED | engine.py:2124-2145 (`info`, `_write_in_flight`), engine.py:2147-2174 (`wirings`, reachability via `resolve_selector`). Spot check on a fresh root: /info and /wirings bodies contain no store_root, no "http", no codebase-memory row; six rows naive 7, bypass 1, hybrid 17, local 15, global 15, hipporag 14; `is_default` only naive; `default_eligible` false only for hipporag; all reachable. `test_store_busy_fields_are_true_during_an_ingest` passes (behavioral). |
| SC3 | List aliases, page alias history with active/tombstoned flags, list traces newest first, preview a promotion that writes nothing and matches what /promote mints | VERIFIED | engine.py:2176-2250 (`ledger_aliases`, `ledger_history` under `snapshot()`), engine.py:2252-2277 (`list_traces`), engine.py:2279-2351 (`preview_promotion` sharing `_promotion_prologue`/`_plan_promotion`, engine.py:2878), ledger.py:531-550, trace_store.py:103-121. Spot check: fresh root gives `[]`, empty history page, no `ledger.db`; limit 0 -> PageBoundsError, 101 -> PageSizeExceededError; unknown trace -> 404 UnknownTraceReferenceError. `test_preview_matches_what_promote_mints_and_refuses` passes (preview == minted version). |
| SC4 | Page chunk refs and graph nodes (batched degrees, prefix filter), open a node's edges, chosen by selector only; unknown node and busy graph are named refusals | VERIFIED | engine.py:2353-2456; probes.py:139-228 (one ordered id statement plus one batched `is_in` edge query per page, probes.py:173-184); vector.py:293-299 (`list_ids`, no reconstruct). Request models take a `selector`, never a namespace (operator_rest.py:46-72). Spot check: unknown node -> 422 UnknownGraphNodeError; malformed selector -> 422; `capability: []` -> EmptyCapabilitySelectorError. `test_graph_nodes_page_degrees_prefix_and_busy_409` passes (busy 409 behavioral). |
| SC5 | Generated refusal catalogue and selector-resolution fixture kept in sync by tests; flag-gated GET /log tails the launcher's log (404 without the flag) | VERIFIED | docs/gui/refusals.json (51 entries incl. UnknownGraphNodeError, 422); databasise/tests/fixtures/selector-resolution.json (29 rows: default, 17 effects, 3 namespace tokens, harness, 6 aliases, empty capability; `reachable` for all six arms). GET /log mounted only when `operator` and `log_path` (rest.py:545-549, operator_rest.py:132-145). Manual launcher check below: real 500 traceback lands in the file and is served by GET /log. |

### CONN Requirements (amended 2026-10-22)

| Req | Delivering code | Covering test (run at HEAD) | Status |
|-----|-----------------|-----------------------------|--------|
| CONN-01 | operator_rest.py:75-145; rest.py:370-374, 545-549; COVERAGE.md:120-133 | test_console_surface.py::test_operator_routes_are_thin_adapters_and_absent_without_the_flag; test_rest_transport.py; test_tool_growth_invariant.py | VERIFIED |
| CONN-02 | docs/gui/refusals.json; refusals.py (UnknownGraphNodeError) | test_refusal_catalogue_file.py::test_the_refusal_catalogue_file_matches_the_code | VERIFIED |
| CONN-03 | databasise/tests/fixtures/selector-resolution.json; selectors.py | test_selector_resolution_fixture.py::test_every_fixture_row_resolves_as_recorded | VERIFIED |
| CONN-04 | engine.py:2124-2140 (`__version__` import engine.py:203; `_client_presence`) | test_console_info.py::test_info_reports_version_workspace_and_client_presence | VERIFIED |
| CONN-05 | engine.py:2147-2174 | test_console_wirings.py::test_wirings_lists_six_reachable_rows_matching_the_fixture | VERIFIED |
| CONN-06 | engine.py:2176-2205; ledger.py:531-539 | test_console_ledger.py::test_aliases_lists_each_alias_once_and_creates_no_file; tests/ledger/test_ledger_read_only_close.py | VERIFIED |
| CONN-07 | engine.py:2207-2250; ledger.py:541-550; `checked_page` in operator_rest.py:98 | test_console_ledger.py::test_history_flags_active_and_tombstoned_and_bounds_the_page | VERIFIED |
| CONN-08 | engine.py:2252-2277; trace_store.py:103-121 | test_console_traces.py::test_traces_list_newest_first_with_paging | VERIFIED |
| CONN-09 | engine.py:2279-2351, 2878 (`_plan_promotion`) | test_console_preview.py::test_preview_matches_what_promote_mints_and_refuses | VERIFIED |
| CONN-10 | engine.py:2353-2377 (namespace from `wiring_family` base wiring, no `_build_stores`); vector.py:293-299 | test_console_chunks.py::test_chunks_page_lists_the_selected_modalitys_refs | VERIFIED |
| CONN-11 | engine.py:2403-2431; probes.py:154-192 | test_console_graph.py::test_graph_nodes_page_degrees_prefix_and_busy_409 (fail-first and killed plant on ledger) ; tests/stores/test_graph_read_review_c.py | VERIFIED |
| CONN-12 | engine.py:2433-2456; probes.py:195-228; refusals.py UnknownGraphNodeError | test_console_graph.py::test_graph_node_edges_and_unknown_node_422 (killed plant on ledger) | VERIFIED |
| CONN-13 | engine.py:2124-2145; graph.py:180-190 (`held_graph_paths`, own-hold excluded); engine.py:2387-2401 (`_hold_graph`) | test_console_info.py::test_store_busy_fields_are_true_during_an_ingest; test_status_during_write.py; test_graph_lock.py | VERIFIED |
| CONN-14 | serve_rest.py:38-47, 90-111, 137-152; engine.py:2458-2496; operator_rest.py:132-145 | test_console_log.py::test_log_tails_the_launcher_log_and_is_404_without_both_flags; tests/launcher/test_log_file_refusal.py; plus the manual launcher check below | VERIFIED |

**Score:** 19/19 truths verified (0 present, behavior-unverified). The behavior-dependent truths (CONN-09 preview equals mint, CONN-11 busy 409, CONN-13 flags during an in-flight ingest) each have a named behavioral test that passed in this run.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| databasise/seam/operator_rest.py | ten thin-adapter routes | VERIFIED | 145 lines; mounted only by `create_app(operator=True)` |
| databasise/seam/engine.py (operator methods) | info, wirings, ledger_aliases, ledger_history, list_traces, preview_promotion, chunk_page, graph_nodes, graph_node, log_tail | VERIFIED | lines 2122-2496 |
| databasise/stores/probes.py | `acquire_graph`, `graph_node_page`, `graph_node_edges` | VERIFIED | no `CozoGraphStore` on the read path |
| databasise/stores/vector.py | `FaissVectorStore.list_ids` | VERIFIED | reads the entry map only |
| databasise/seam/trace_store.py | `TraceStore.list_page` | VERIFIED | page and count in one read transaction |
| databasise/ledger/ledger.py | `Ledger.aliases`, `history_for_alias`, `snapshot` | VERIFIED | `LedgerEntry` carries id and created_at |
| databasise/launcher/serve_rest.py | `--operator`, `--log-file`, `log_config_for` | VERIFIED | bad log file refused before the store lock |
| docs/gui/refusals.json | refusal catalogue | VERIFIED | 51 entries, test-synced |
| databasise/tests/fixtures/selector-resolution.json | selector fixture | VERIFIED | 29 rows, 6 reachable flags |
| databasise/evidence/COVERAGE.md | REST-ONLY rows and exceptions | VERIFIED | rows 120-129, D-02/D-09/D-10/D-19 bullets 136-143 |

### Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| serve_rest.build_app | create_app | `operator=`, `log_path=` (serve_rest.py:60-67) | WIRED |
| create_app | add_operator_routes | `if operator:` with `log=log_path is not None` (rest.py:545-549) | WIRED |
| operator routes | app.state.engine | the same `engine` object (rest.py:370-374) | WIRED |
| engine.graph_nodes/graph_node | probes.graph_node_page/edges | `asyncio.to_thread` plus `_hold_graph` | WIRED |
| engine.info | graph.held_graph_paths, write gates | `own=self._graph_holds`, `_gate_for(...).locked()` | WIRED |
| serve_rest.main | uvicorn file logging | `log_config_for(args.log_file)` (serve_rest.py:151) | WIRED (proved by the manual launcher check) |

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
| databasise/seam/engine.py | 2486 | `shortcut:` full read per /log call | Info | documented limit |
| databasise/stores/probes.py | 172 | `shortcut:` O(N) ids per page | Info | documented limit |
| databasise/seam/trace_store.py | 108 | `shortcut:` full sort per page | Info | documented limit |

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

_Verified: 2026-10-22T16:15:00Z_
_Verifier: Claude (gsd-verifier)_
