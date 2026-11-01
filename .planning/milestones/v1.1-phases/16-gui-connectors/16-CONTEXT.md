# Phase 16: GUI Connectors - Context

**Gathered:** 2026-10-22
**Status:** Ready for planning
**Mode:** Auto discuss (autonomous). In Phases 9–15 the owner delegated grey-area decisions ("You decide") and asked the run to continue in gsd-autonomous mode.

Each decision below is Claude's choice under that delegation. Each rests on a five-agent code study: four area lanes (surface, ledger and traces, corpus and graph, info and catalogue) and a critic. The critic probed the proposals against the protected tests. The lane reports, with file:line evidence, are in the session scratchpad under `p16/` (`report-surface.md`, `report-ledger.md`, `report-corpus.md`, `report-info.md`, probes).

Two decisions narrow earlier decisions. Both are marked **(owner may override)**:
- D-02 records a §18.2 operator exception.
- D-19 narrows Phase 9 D-04.

<domain>
## Phase Boundary

The operator console gets every read route it needs. The launcher's single `Databasise` engine serves each one through a thin adapter, and no response leaks store internals or credentials.

The routes:
- GET /info, with store-busy fields
- GET /wirings
- GET /ledger/aliases
- POST /ledger/history
- GET /traces
- POST /promote/preview
- POST /chunks
- POST /graph/nodes
- POST /graph/node
- GET /log

The repository artefacts:
- a generated refusal catalogue;
- a selector-resolution fixture.

Covered requirements: CONN-01 through CONN-14.

**Not in this phase:**
- The console UI (Phase 17 mockup, Phase 18 live).
- Authentication.
- MCP tools for operator operations.
- Any write route.
- Any provider spend.
</domain>

<decisions>
## Implementation Decisions

### A. Surface placement (CONN-01, ROADMAP open questions 1 and 5)

- **D-01 (OQ1a): operator routes go on the §18 app, mounted only under an explicit flag.**
  - Add `create_app(..., operator=False)` and a `databasise-rest --operator` launcher flag.
  - The routes live in a new module, `databasise/seam/operator_rest.py`: a factory that takes `engine` and adds the routes.
  - Without the flag, none of these routes is mounted (each is a 404), and the app is byte-identical to today.
  - Paths are exactly as the requirement texts give them. There is no `/operator` prefix.
  - **Why:** §18.3 "no privileged client" (CONTRACT.md:779-781) rules out a port that exists only for the console. A flag gates the whole process, so every client of that process sees the same surface. Phase 14 D-10 (14-CONTEXT.md:97) already names this "launcher-flag pattern". A second process is blocked by `.engine.lock` (G-36), and a second `uvicorn.Server` in the same process costs more code.
  - **Protections reused:** loopback bind, TrustedHost, the Origin guard and CORS (serve_rest.py:52-66).
  - **Host rule:** `--operator` with a non-loopback `--host` is a `parser.error`, even with `--allow-remote-unauthenticated`.
  - **Probe:** the critic mounted operator-shaped routes on every `create_app`. 25 leak, parity, doc and launcher test files stayed green. The flag is a design choice, not a test constraint.

- **D-02: §18.2 operator exception (owner may override).**
  - /wirings rows, the `arm` and `mutation_class` fields in preview, and the alias listing all name wirings or ledger identities. §18.2 keeps those off the consumer seam (CONTRACT.md:775). They are allowed only on the `--operator` surface.
  - The precedent is `debug=true` on /trace/resolve, which already returns `wiring_id`/`arm_id` on the ungated app (engine.py:445-450; Phase 14 D-10).
  - §18.4 forbids a wiring name as *input*. All corpus and graph routes take selectors, so the §18.5 falsifier (CONTRACT.md:810) is not triggered.
  - Record the exception in `databasise/evidence/COVERAGE.md` and in docs/gui/API-INVENTORY.md.

- **D-03 (OQ1b): every new operation is REST-only.**
  - Each operation gets one row in COVERAGE.md's "Operations deliberately absent" table (COVERAGE.md:106-119). It never goes in the §18.5 operations table.
  - The critic probed both tables:
    - an operations-table row fails `test_every_tool_has_a_coverage_row…`, because it has no `_OPERATION_TO_TOOLS` key;
    - an absent-table row passes both that test and the RUN-01 cross-check.
  - `TOOL_NAMES` stays at ten (mcp/tools.py:79-90).
  - **Why:** the MCP launcher has no operator gate, so MCP tools would expose wiring names and trace tokens to every MCP session, stdio agents included. 15-CONTEXT.md:158 already allows REST-only.
  - This supersedes the loose "REST and MCP ledger read routes" wording in 14-CONTEXT.md:21.

- **D-04: SC1 enforcement, "no route body reads the ledger, trace store, registry or stores directly".**
  - **New AST test** in a new unprotected file, over `seam/operator_rest.py`:
    - Each route body is an optional docstring plus exactly `return await engine.<method>(...)`. Pure argument helpers (`checked_page`, `_selector_field`) are allow-listed.
    - It walks `fn.body` only, never the annotations.
    - Banned names: `Ledger`, `TraceStore`, `PartRegistry`, `default_registry`, `_build_stores`, `Databasise`, `ResponseEnvelope`, `resolve_selector`, the redact exports, `sqlite3`, `open`.
    - The module may import nothing from `databasise.ledger`, `seam.trace_store`, `databasise.stores` or `parts.registry`.
    - A mutant case (`return Ledger(...).aliases()`) must fail the test.
  - **Existing test, extended:** parametrize test_rest_transport.py:202's `called_names` test over both rest.py and operator_rest.py. The file is not a ledger test_ref, so no grant is needed.
  - **Why:** test_rest_transport.py:182-201 is the importability test, not the call ban. No current test fails on `Ledger(` in a route body.

### B. Info, wirings and catalogues (CONN-02, 03, 04, 05)

- **D-05: GET /info is backed by a new `Databasise.info()`.**
  - Returns `{version, workspace, clients, write_in_flight, graph_busy}`. The store-busy fields are added in D-17.
  - `version` is `databasise.__version__`, the single source since Phase 15 TOOL-01.
  - `workspace` is `engine.workspace`, a path component that does not reveal store_root.
  - `clients` is `{key: key in engine.clients}` over `CLIENT_EFFECT_TO_KEY`, factored into one helper shared with `health()` (engine.py:2060). It means "configured at startup", never "reachable". Never call `bool(client)`, and make no provider call.
    - `rerank` is true only when the RERANK_* settings are configured, because a rerank client ships (clients/rerank.py, builder.py:159-209).
    - Under `--no-clients`, all three are false.
  - Not /health: that probes stores and runs v1 with a 60 s ceiling (engine.py:1976-2030).
  - The test asserts the response contains no store_root substring, no `http`, no model value and no `api_key`.

- **D-06: GET /wirings is backed by `Databasise.wirings()`.**
  - It returns one row per `all_wirings()` name. Fields are `{name, wiring_id, wiring_version, title, node_count, effects, provides, harnesses, default_eligible, is_default, reachable}`.
  - Facts at HEAD:
    - `node_count` is the full count: 7, 1, 17, 15, 15, 14.
    - `effects` is the query-run effects, the set that selection uses.
    - `default_eligible` is false for hipporag.
    - `is_default` is true for naive only.
  - `reachable` is true when `resolve_selector(Selector(capability=sorted(query-run tokens)))` returns the same `wiring_id`. All six arms are reachable today, because each arm has its own wiring_id (Phase 13 D-03).
  - Compute `reachable` inside the engine, never in a REST module (test_rest_transport.py:202 bans `resolve_selector` there).
  - `codebase-memory-mcp` is not listed.
  - The five LightRAG arms share one `title`, so the console must key rows on `name`.

- **D-07: the refusal catalogue is a committed `docs/gui/refusals.json`.**
  - Generated by a sync test in a new file, `tests/seam/test_refusal_catalogue_file.py`. The test builds the expected entries from `_REFUSAL_FACTORIES` (imported from test_rest_transport.py, not copied), plus `refusal_body`, plus `rest._status_for`.
  - Entry fields: `refusal_type`, `module`, `attribute_keys`, `http_status`.
  - The test fails with a hint to regenerate, which runs under an env flag.
  - There are 50 types today, all in `refusals.__all__`.
  - Drop the validator `ctx.error` clause: SEAM-02 unwrapped it, so validator refusals have the normal body.

- **D-08: the selector-resolution fixture is a committed `databasise/tests/fixtures/selector-resolution.json`, with a sync test.**
  - Rows:
    - default → naive;
    - each of the 17 Effect members as a capability (most → `UnsatisfiableSelectorError`);
    - the namespace tokens `reads_vector:entities`, `reads_vector:relationships` and both together (local, global, hybrid);
    - `capability: []` → `EmptyCapabilitySelectorError`;
    - a harness → Unsatisfiable;
    - one alias promoted per arm in a tmp ledger.
  - Each row records `wiring` (name), `node_count` and `outcome`.
  - The CONN-05 test cross-checks `reachable` against this fixture.

### C. Ledger and traces (CONN-06, 07, 08, 09; ROADMAP open questions 2, 3, 12, 14)

- **D-09 (OQ2): GET /ledger/aliases is allowed behind `--operator`.**
  - This relaxes the project's no-enumeration rule, which lives in selectors.py:281-302 and is not CONTRACT text. §18.4 calls an alias the machine's "stable public handle" (CONTRACT.md:791).
  - Why not a client-side log: it would miss promotions by peer clients (MCP, CLI, rig; §18.3), and it would not survive a reload.
  - The selector's identical refusal stays as it is.
  - Record the exception in COVERAGE.md and here. Do **not** edit the selectors.py or ledger.py docstrings: that keeps the protected test_docstring_currency.py untouched.
  - Implementation: `Ledger.aliases()` is `SELECT DISTINCT alias` plus a per-alias `by_alias` projection. It is read with `open_existing(read_only=True)` inside `with`, so it creates no file and leaves no open handle.

- **D-10 (OQ3): `promotion_trace_ids` are returned, and trace tokens are listed, behind `--operator`.**
  - Tokens are random bearer handles (trace_store.py:7-13, 85). The app already has no auth. Any local caller can already promote, roll back and use `debug=true` (Phase 14 D-10).
  - Mitigations: loopback only, the operator flag, the Origin guard and CORS.

- **D-11 (OQ14): one store_root is one workspace (Phase 14 D-10, engine.py:1142-1146).**
  - trace.db has no workspace column (trace_store.py:71-75), so there is no filter. Nothing to build.

- **D-12 (OQ12): CONN-09 is already settled by LEDG-03 (Phase 14 D-05).**
  - A complete HippoRAG trace previews as `promotable: true`; it mints 1.0.0 in a probe.
  - **Shared helper:** extract the body of `_promote_sync` (engine.py:2496-2527: `by_alias`, `wiring_for_name`, `derive_mutation_class`, `declared_surface`, `mint_version`) into `_plan_promotion(ledger_or_None, alias, resolved)`.
    - Promote calls it inside `ledger.transaction()`.
    - Preview calls it on `open_existing(read_only=True)`, or on None, which yields 1.0.0.
    - Promote's refusal order and transaction span stay unchanged.
  - **Outcome refusals** become `promotable: false, reason: <refusal_type>`:
    - `PartialRunEvidenceError`
    - `GateNotCalibratedError`
    - `GateVerbNotBuiltError`
    - `MeasurementPostureRefusalError`
  - **Input refusals still raise (422, except `UnknownTraceReferenceError`, which is 404 per SEAM-04):**
    - `UnknownTraceReferenceError`
    - `InvalidPromotionAliasError`
    - `InvalidChangeOriginError`
    - empty or disagreeing trace ids
    - `UnrecognisedPromotionVerbError`
  - On a partial trace, preview still tries `resolve_single_arm` to report `arm`. That is null for an old record with no `arm_id`.
  - A degraded but complete run is promotable.
  - `next_version` is guaranteed only when no write lands between preview and promote. Preview runs outside BEGIN IMMEDIATE; the docstring says so.
  - Name the route and docs so they are not confused with the unbuilt §5 ladder verb "preview" (promotion.py:56-63).

- **D-13a: POST /ledger/history.**
  - Rows come from `history_for_alias` (ledger.py:498-507).
  - `active` = `set(lineage(alias, by_alias(alias).minted_version))`. `tombstoned` = the `targets_version` values of tombstone rows.
  - Paged with `corpus.checked_page`: `limit < 1` gives `PageBoundsError` (422), `limit > 100` gives `PageSizeExceededError`.
  - `generation_ordinal` is the global row id.
  - `mutation_id`, `parent` and `arm_instance_hashes` are not returned.

- **D-13b: GET /traces.**
  - Backed by a new `TraceStore.list_page(limit, offset)`: `ORDER BY created_at DESC, rowid DESC`, plus `COUNT(*)`.
  - `partial`, `degraded` and `stop_reason` are read from the stored JSON. A missing `partial` counts as false.
  - `stop_reason` passes through the same `node_free_reason` scrub as `resolve_trace` (engine.py:2275-2283), extracted into one shared helper.
  - `created_at` has no index. Mark it `shortcut: full sort per page, add an index if traces exceed ~10^5`.

### D. Corpus and graph (CONN-10, 11, 12, 13; ROADMAP open question 6)

- **D-14 (CONN-10): POST /chunks.**
  - The selector resolves through `resolve_selector`, then `wiring_family`, then the family's **base** wiring's `evidence_position.namespace`: `chunks` for LightRAG, `hipporag-chunks` for HippoRAG. Use the base wiring because the bypass arm declares no evidence_position.
  - Page `sorted(load_committed(dir).entries)`, which never calls `reconstruct`. A missing directory gives `total: 0` and creates nothing.
  - Refs are minted by `mint_evidence_refs(..., kind=TEXT_CHUNK_KIND)`, so each one resolves through /evidence/resolve.
  - **Never** call `_build_stores` on a read path. It constructs a `CozoGraphStore`, which runs mkdir and `_ensure_relations` (graph.py:183-191).

- **D-15 (CONN-11, 12): the graph reads copy `probe_graph`'s pattern (stores/probes.py:90-120).**
  - A missing `graph.cozo` gives `total: 0`.
  - A missing RocksDB marker gives the StoreCorrupted fault.
  - Otherwise: acquire the client through the registry, run immutably, release in `finally`.
  - A cross-process lock is mapped to `StoreBusyError(store_kind="graph")`, the same way `_build_stores` maps it (engine.py:607-611). It answers **409** (Phase 10 D-02; rest.py:150-152). The CONN-11 text saying 422 is stale.
  - The test holds the lock with a raw `pycozo.Client("rocksdb", path)`, because a second `CozoGraphStore` shares the client and returns 200.
  - **Node page:** sorted with `:order id :limit :offset`, plus an optional `starts_with(id, $prefix)`.
  - **Degrees:** one batched query (`is_in(src,$ids)` unioned with `is_in(tgt,$ids)`), counted in Python, with no `count()` (Cozo bug #244). A spy test proves one degree query per page.

- **D-16 (OQ6, CONN-12): references plus an allowlist, matching API-06 and §18.2.**
  - Edges are `{src, tgt, edge_types, weight}`. `edge_types` and `weight` are **always present**, null when the store has none, so no field appears for one modality only (§18.3 invariance).
  - No other attrs. LightRAG attrs carry extracted corpus text, and HippoRAG `cooccurrence_by_chunk` has no size bound.
  - The dereference call is deferred until the Phase 17 mockup needs entity text.
  - An unknown node raises a new `UnknownGraphNodeError` at **422**, not 404. Adding it to `_NOT_FOUND_REFUSALS` fails the protected `test_refusal_status_codes.py::test_status_for_maps_exactly_the_four_lookups_to_404…`, and the rest.py:116-123 comment rules it out: "404 never discloses whether an internal identity (wiring, arm, node) exists".
  - Add the type to `refusals.__all__`, add a factory to test_rest_transport.py's `_REFUSAL_FACTORIES` (an unprotected file), and regenerate refusals.json.

- **D-17 (CONN-13): `write_in_flight` and `graph_busy` live on GET /info.**
  - `write_in_flight` = the existing `_write_gate_held`: `.locked()` on the v1 or HippoRAG write gate (engine.py:1178-1185). It never acquires the lock.
  - `graph_busy` = true if a `list()` snapshot of `_ClientRegistry._entries` holds a key under `<store_root>/<workspace>/`. A small public helper in stores/graph.py exposes it.
  - `graph_busy` means "in use in this process". It does not see out-of-process holders, so the console labels it "in use", not "locked".
  - The test blocks a stub ingest node on an `asyncio.Event` (pattern: test_status_during_write.py) and uses an in-process graph write.

### E. Log tail (CONN-14, ROADMAP open questions 1 and 5)

- **D-18: GET /log is mounted only when both `--operator` and a new `--log-file PATH` are given.** Otherwise it is a 404.
  - The launcher configures uvicorn's `log_config` and a root-logger FileHandler writing to that path. Today no log file is written anywhere.
  - `Databasise(log_path=...)` gets `async log_tail(limit)`, so the route stays one awaited engine call.
  - `limit` is bounded 1..1000. That is its own bound, not `checked_page`.
  - A browser console cannot read a local file, so the out-of-band option fails the requirement.
- **D-19: Phase 9 D-04 is narrowed (owner may override).**
  - D-04 said: "No operator/debug flag exposes the cause while seam authentication is undecided."
  - Narrowed: refusal and fault **bodies** stay free of stderr and causes. A separate log route, off by default, loopback only, behind `--operator --log-file`, is allowed.
  - The log holds paths and tracebacks, never env values: launcher refusals name keys only.

### F. Execution rules

- **No provider spend, and never `-m live`.** All tests use `clients=None` or stubs.
- **No protected test needs a grant** under these decisions. The following must pass unchanged:
  - the promote-path suites: test_partial_run_evidence.py, test_promote_refuses_partial.py, test_operator_alias_validation.py, test_promotion_posture.py, test_promotion_floor.py;
  - test_refusal_status_codes.py and test_refusal_catalogue.py;
  - test_docstring_currency.py;
  - test_graph_lock.py;
  - test_health_probe.py and test_health_honesty.py;
  - test_stop_reason_leak.py;
  - test_page_bounds.py;
  - test_evidence_namespace_guard.py;
  - test_run01_coverage_crosscheck.py and test_tool_growth_invariant.py.
- **Not protected, so plans may edit them:** test_rest_transport.py, test_tool_growth_invariant.py, test_leak.py, test_store_refusal_status.py.
- **Requirement text:** amend REQUIREMENTS.md CONN-01 to CONN-14 per the Specifics list before planning.
- **OpenAPI:** store-reading operator routes declare their fault responses (502, 503, 409) in OpenAPI, as Phase 9 D-04 requires for store-reading routes.
- **Merge conflicts:** every wave-2 plan touches operator_rest.py and engine.py. Run them sequentially on the main tree, or give each plan its own section of each file.
</decisions>

<canonical_refs>
## Canonical References

- `docs/system-model/CONTRACT.md` §18.2 (775), §18.3 (777-785), §18.4 (789-791), §18.5 (810), §5 ladder verbs, §6, §9: frozen.
- `.planning/REQUIREMENTS.md` CONN-01 to CONN-14, amended per Specifics.
- `.planning/ROADMAP.md` Phase 16, including SC1-SC5 and the owner questions.
- `.planning/phases/14-promotion-ledger/14-CONTEXT.md`: D-03, D-04, D-05, D-06, D-10.
- `.planning/phases/15-offline-tooling-packaging/15-CONTEXT.md`: D-13, D-18 and line 158.
- `.planning/milestones/v1.0-phases/` and `09-CONTEXT.md` D-04 (find the 09 phase dir), for D-19.
- `docs/gui/API-INVENTORY.md`: :694, :710 and :719 are stale, and :710/:719 must be fixed.
- `docs/gui/CODEBASE-MAP.md` (:397).
- `databasise/evidence/COVERAGE.md`: the deliberately-absent table (106-119).
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **REST and launcher:**
  - `create_app`: one engine, kept on `app.state.engine` (rest.py:350-536).
  - `build_app` with its guard wrapping, `check_engine_arguments` and `is_loopback_host` (serve_rest.py, launcher/__init__.py).
  - `_FAULT_RESPONSES`, the `_RequestModel` frozen base, `_status_for` and `_NOT_FOUND_REFUSALS` (rest.py).
- **Paging and selectors:**
  - `corpus.checked_page` and `MAX_PAGE_SIZE=100` (corpus.py:198-212).
  - `_selector_field`, `resolve_selector` and `wiring_family`/`load_wiring`.
  - `mint_evidence_refs` (evidence.py:95-131).
- **Ledger and promotion:**
  - The ledger: `Ledger.open_existing(read_only=True)`, `by_alias`, `lineage`, `history_for_alias`, `LedgerEntry`.
  - Promotion: `refuse_partial_evidence`, `resolve_single_arm`, `derive_mutation_class`, `declared_surface`, `mint_version`, `PROMOTION_VERBS`, `_refuse_gate_verb`.
- **Traces:** `TraceStore.resolve`, and the non-debug projection in `resolve_trace` (`node_free_reason`).
- **Stores:**
  - `probe_graph` (open, marker check, release) and `list_kv_prefix` (probes.py).
  - `load_committed` (vector.py:200-252).
  - `_ClientRegistry` (graph.py:135-173).
  - `_write_gate_held`/`_gate_for` (engine.py:1178-1185).
- **Tests:** `_REFUSAL_FACTORIES` (test_rest_transport.py: one factory for each of the 50 types). test_status_during_write.py is the pattern for concurrent reads.

### Integration Points
- **rest.py:** the `create_app(operator=)` parameter, plus the include of `operator_rest.add_operator_routes(app, engine)`.
- **serve_rest.py:** the `--operator`, `--log-file` and non-loopback refusal arguments.
- **engine.py:** the `info`, `wirings`, `ledger_aliases`, `ledger_history`, `list_traces`, `preview_promotion`, `chunk_page`, `graph_nodes`, `graph_node` and `log_tail` methods, and the `_plan_promotion` extraction.
- **Stores and their APIs:**
  - stores/vector.py: `list_ids`.
  - stores/probes.py: `graph_page`, `node_edges_page`.
  - stores/graph.py: a held-paths helper.
  - ledger.py: `aliases()`.
  - trace_store.py: `list_page`.
</code_context>

<specifics>
## Specific Ideas

Requirement-text amendments to make in REQUIREMENTS.md before planning (from the critic's consolidated list):
- **CONN-01:**
  - The test is a new AST test over operator_rest.py with a `Ledger(` mutant, and line 202's call-ban test is parametrized over both modules.
  - Each new operation gets a REST-only row in COVERAGE.md's deliberately-absent table. Drop the MCP-09 dependency.
  - The routes mount only under `--operator` / `create_app(operator=True)`.
- **CONN-02:**
  - The count is 50, all in `__all__`.
  - Delete the "four types" sentence and the `ctx.error` clause.
  - The body is what `refusal_body` builds, plus `http_status`.
- **CONN-03:**
  - All six arms are reachable.
  - `capability: []` gives `EmptyCapabilitySelectorError`.
  - Add the namespace-token rows.
  - Delete the open-question-10 clause.
- **CONN-04:** `rerank` is true only when RERANK_* is configured. The test builds with `operator=True`.
- **CONN-05:** add that hipporag has `default_eligible` false, and that the five LightRAG arms share one title.
- **CONN-06:** rows are projected from `LedgerEntry`, which carries `id`/`created_at`. The route is behind `--operator`, and the no-enumeration exception is recorded.
- **CONN-07:** `PageBoundsError` via `corpus.checked_page`.
- **CONN-08:** `stop_reason` passes through the `node_free_reason` scrub.
- **CONN-09:**
  - Test (2) matches /promote's 422 `PartialRunEvidenceError`, not a 500.
  - `arm` and `mutation_class` are operator-only.
  - State the `next_version` race caveat.
  - Open question 12 is resolved by LEDG-03.
- **CONN-10:** the namespace comes from the base wiring's `evidence_position`, without constructing any store.
- **CONN-11:** the graph is held by another process, which gives `StoreBusyError` 409. The test uses a raw `pycozo.Client`.
- **CONN-12:** edges are `{src, tgt, edge_types, weight}`, with the last two null when absent. `UnknownGraphNodeError` stays at 422.
- **CONN-13:** the fields are named `write_in_flight` and `graph_busy`, and `graph_busy` sees in-process holders only.
- **CONN-14:** the route needs `--operator` plus `--log-file PATH`, and the Phase 9 D-04 narrowing is recorded.
- **ROADMAP:** the OQ2 wording "D-12/FA-06" should cite the selectors.py:281-302 no-enumeration rule. 14-CONTEXT D-12 is a different decision.

Proposed plan split (critic):
- **Wave 1:**
  - 16-01: operator surface + /info tracer (CONN-01 partial, CONN-04).
  - 16-02: refusal catalogue (CONN-02).
  - 16-03: selector fixture (CONN-03).
  - 16-04: store read helpers.
- **Wave 2, all needing 16-01:**
  - 16-05: /wirings, needs 16-03.
  - 16-06: ledger aliases + history.
  - 16-07: trace list.
  - 16-08: promote preview.
  - 16-09: chunks, needs 16-04.
  - 16-10: graph routes, needs 16-02 and 16-04.
  - 16-11: store-busy fields, needs 16-04.
  - 16-12: log tail.
- **Wave 3:** 16-13: COVERAGE rows, the §18.2 note, the API-INVENTORY fixes, the RUN-01 and growth runs.
</specifics>

<deferred>
## Deferred Ideas

- A graph node/edge dereference route for entity text, to build if the Phase 17 mockup (GUI-11) needs it.
- MCP tools for operator operations, once an MCP-side operator gate or seam authentication exists.
- A `created_at` index on trace.db.
- Out-of-process graph-busy detection.
- A workspace column in trace.db, for multi-workspace store roots.
</deferred>
