# Phase 16: GUI Connectors - Research

**Researched:** 2026-10-22
**Domain:** FastAPI operator read routes over the in-process `Databasise` engine (Python 3.12, FastAPI/Starlette/uvicorn, SQLite, Cozo/RocksDB, Faiss)
**Confidence:** HIGH (every load-bearing claim was read in source or probed this session; three LOW items are listed in the Assumptions Log)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

Copied verbatim from 16-CONTEXT.md `<decisions>`. In auto-discuss mode the owner delegated the choices. D-02 and D-19 are marked "owner may override".

#### A. Surface placement (CONN-01, ROADMAP open questions 1 and 5)

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

#### B. Info, wirings and catalogues (CONN-02, 03, 04, 05)

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

#### C. Ledger and traces (CONN-06, 07, 08, 09; ROADMAP open questions 2, 3, 12, 14)

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
  - **Input refusals still raise 422:**
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

#### D. Corpus and graph (CONN-10, 11, 12, 13; ROADMAP open question 6)

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

#### E. Log tail (CONN-14, ROADMAP open questions 1 and 5)

- **D-18: GET /log is mounted only when both `--operator` and a new `--log-file PATH` are given.** Otherwise it is a 404.
  - The launcher configures uvicorn's `log_config` and a root-logger FileHandler writing to that path. Today no log file is written anywhere.
  - `Databasise(log_path=...)` gets `async log_tail(limit)`, so the route stays one awaited engine call.
  - `limit` is bounded 1..1000. That is its own bound, not `checked_page`.
  - A browser console cannot read a local file, so the out-of-band option fails the requirement.
- **D-19: Phase 9 D-04 is narrowed (owner may override).**
  - D-04 said: "No operator/debug flag exposes the cause while seam authentication is undecided."
  - Narrowed: refusal and fault **bodies** stay free of stderr and causes. A separate log route, off by default, loopback only, behind `--operator --log-file`, is allowed.
  - The log holds paths and tracebacks, never env values: launcher refusals name keys only.

#### F. Execution rules

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

### Claude's Discretion

No separate `## Claude's Discretion` section exists in CONTEXT.md. Every decision above is Claude's choice under the owner's delegation (16-CONTEXT.md:5-7). Implementation details that the decisions leave open are recommended below and marked as recommendations.

### Deferred Ideas (OUT OF SCOPE)

Copied verbatim from 16-CONTEXT.md `<deferred>`:

- A graph node/edge dereference route for entity text, to build if the Phase 17 mockup (GUI-11) needs it.
- MCP tools for operator operations, once an MCP-side operator gate or seam authentication exists.
- A `created_at` index on trace.db.
- Out-of-process graph-busy detection.
- A workspace column in trace.db, for multi-workspace store roots.

Also out of scope (16-CONTEXT.md:36-41): the console UI (Phases 17-18), authentication, MCP tools for operator operations, any write route, any provider spend.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description (amended 2026-10-22, REQUIREMENTS.md:695-744) | Research Support |
|----|-------------|------------------|
| CONN-01 | Operator routes in `seam/operator_rest.py`, thin adapters over `app.state.engine`, mounted only under `create_app(operator=True)`; REST-only, recorded in COVERAGE.md's deliberately-absent table | Architecture Patterns 1 and 2; Code Examples 1, 2, 9; Pitfalls 1, 2, 8 |
| CONN-02 | `docs/gui/refusals.json`: 50 types today, keys from `refusal_body`, `http_status` from `_status_for` | Probe: 50 subclasses, 0 outside `__all__`; Code Example 10 |
| CONN-03 | `tests/fixtures/selector-resolution.json`; `reachable` true for all six; `capability: []` gives EmptyCapabilitySelectorError | Probe: all six reachable; selectors.py:266-276 |
| CONN-04 | GET /info `{version, workspace, clients}`, no network call, no store_root | engine.py:2033-2060; Code Example 3 |
| CONN-05 | GET /wirings rows; node counts 7/1/17/15/15/14; naive is default; hipporag not default-eligible | Probe rows; Code Example 3 |
| CONN-06 | GET /ledger/aliases via `Ledger.aliases()`, read-only, creates no file | ledger.py:162-216, 429-449; Code Example 5 |
| CONN-07 | POST /ledger/history with `active`/`tombstoned`, `checked_page` bounds | ledger.py:467-507; corpus.py:198-212 |
| CONN-08 | GET /traces via `TraceStore.list_page`, newest first, `node_free_reason` scrub | trace_store.py:68-101; engine.py:2263-2284 |
| CONN-09 | POST /promote/preview mirrors /promote's refusal order; no ledger write | engine.py:2286-2337, 2413-2556; Verified Open Points, Point 2 |
| CONN-10 | POST /chunks: namespace from the family base wiring's `evidence_position.namespace`; `list_ids` without reconstruct | Probe: base ns `chunks`/`hipporag-chunks`; vector.py:200-252 |
| CONN-11 | POST /graph/nodes: sorted page, prefix, one batched degree query, 409 on a held graph | l3_cozo probe rerun; graph.py:122-173; probes.py:90-120 |
| CONN-12 | POST /graph/node: edges `{src, tgt, edge_types, weight}`, unknown node → 422 `UnknownGraphNodeError` | graph.py:297-318; rest.py:116-129 |
| CONN-13 | `write_in_flight`, `graph_busy` on GET /info, read without acquiring a lock | engine.py:802-860, 1178-1185, 1472-1483; graph.py:135-173 |
| CONN-14 | GET /log behind `--operator --log-file`, limit 1..1000 | uvicorn logging probe (Verified Open Points, Point 1) |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Architecture D4 One Machine is settled. The contract vocabulary is frozen: NodeKind, the 17-member `effects[]`, the three artifact scopes, budget tokens and the ledger.
- Python only. Local NixOS host `legion`, embeddable in-process, no external DB servers, no Docker.
- The §18 seam stays modality-agnostic: swapping the fitted modality changes no field a consumer sees. D-16 makes `edge_types`/`weight` always present for this reason.
- GSD workflow enforcement: edits only through `/gsd-execute-phase` plans.
- Naming: test functions are `test_*()`. Async methods are `a`-prefixed only where a sync twin exists; the engine's seam methods are all async with no sync twin.
- Conventions: ruff with target `py310`; module and class docstrings expected; guard checks run eagerly; refusals are named, never silent clamps.
- User global rules: never read `.env*` or `v1/parity-env.txt`; plain technical language; file references as workspace-relative markdown links in chat output.
- Orchestrator rules for this phase: no `-m live`, no provider tokens, no grep/cat/diff of protected tests, no `cd` prefix in shell commands.

## Summary

Everything Phase 16 needs already exists as an engine-side building block. No new dependency is required, and every route is a closure in a new `operator_rest.py` that awaits one new `Databasise` method. The work is plumbing and tests, with four places where a naive implementation breaks a protected test or a contract rule:

1. **Logging.** A root-logger FileHandler alone does **not** capture the 500 tracebacks, which are the point of CONN-14. uvicorn's `uvicorn` logger has `propagate: False`. The file handler must be part of the `log_config` dict handed to uvicorn, with `disable_existing_loggers: False`. The engine logger is created at import, so dictConfig's default `True` would silence it. All three cases were probed (Verified Open Points, Point 1).
2. **Preview order.** /promote raises `GateNotCalibratedError` for a gate verb with no floors **before** alias or trace validation. It also raises `PartialRunEvidenceError` **before** `resolve_single_arm`. Preview must reproduce that exact order to make "reason == what /promote refuses with" true. Note that `UnknownTraceReferenceError` is a **404**, not the 422 that CONN-09 and D-12 state (`_NOT_FOUND_REFUSALS`, rest.py:124-129, probed).
3. **Reads must create nothing and must not touch the stores' write paths.** Chunks come from `load_committed`, graph reads from the `probe_graph` pattern, and the ledger from `open_existing(read_only=True)`. `_build_stores` and the `CozoGraphStore` constructor are banned on these paths.
4. **The BAK row rule.** Each CONN row test must fail by `AssertionError` at HEAD. A missing kwarg (`create_app(operator=True)`) is a `TypeError`, and a missing module is a collection error. So every row test must reach new API through `inspect.signature`, `importlib.util.find_spec` or `getattr` plus an `assert` (Code Example 9).

The ledger `REQUIREMENTS.json` CONN rows still hold the **pre-amendment** text. Examples: CONN-02 says "30 today", CONN-05 says "hipporag 13" and "share `wiring_id` `lightrag-base`", and CONN-10 says "through `_build_stores`" (ledger/REQUIREMENTS.json:1911-2083). REQUIREMENTS.md was amended, but the ledger was not re-synced. Sync the ledger text before setting test_refs, or verification will judge against stale text.

**Primary recommendation:** Build a wave-1 tracer: `create_app(operator=)`, `operator_rest.add_operator_routes`, the AST test, GET /info, and the launcher flags with the probed `log_config`. Then add one engine method plus one route plus one row test per requirement. Write each row test in the guarded form of Code Example 9.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Route mounting, flag gating, request DTOs, paging args | API transport (`seam/operator_rest.py`) | Launcher (`launcher/serve_rest.py`) | D-01/D-04: the transport only deserializes and awaits |
| `--operator`, `--log-file`, host refusal, uvicorn `log_config` | Launcher | — | The process-level gate (§18.3 no privileged client) |
| Selector resolution, namespace choice, reachability, preview planning, scrubbing | Engine (`seam/engine.py`) | `seam/selectors.py`, `seam/promotion.py`, `seam/redact.py` | Banned in REST modules (test_rest_transport.py:202-220) |
| Ledger alias listing, history rows | Storage (`ledger/ledger.py`) | Engine (projection to `active`/`tombstoned`) | SQL lives beside `by_alias`/`history_for_alias` |
| Trace listing | Storage (`seam/trace_store.py`) | Engine (scrub) | `TraceStore` owns trace.db |
| Chunk id paging | Storage (`stores/vector.py` `list_ids`) | Engine (namespace, ref minting) | Read the snapshot, never reconstruct |
| Graph node/edge paging, held-path check | Storage (`stores/probes.py`, `stores/graph.py`) | Engine (busy → `StoreBusyError`) | Mirrors `probe_graph` and `_build_stores`' mapping |
| Refusal catalogue, selector fixture | Repository artefacts + sync tests | — | Static files, regenerated under an env flag |

## 6. Protected Tests Constraining Each Touched Module

Source: the `check_locks.files` map in ledger/REQUIREMENTS.json:2376-2496, read with the Read tool only. These are the protected test_refs. A row marked **not protected** is absent from check_locks, so a plan may edit it. Note that the BAK guard hook refused even read-only shell commands that named the bare package directory; plans that edit unprotected test files should still expect the guard to inspect them (Pitfall 9).

| Touched module | Protected tests that constrain it (must pass unchanged) | What they pin |
|---|---|---|
| `seam/rest.py` (add `operator=`/`log_path=` params, conditional include) | `tests/seam/test_refusal_status_codes.py`, `test_refusal_body_shape.py`, `test_rest_cors.py`, `test_corpus_adapter_failures.py`, `test_trace_resolve_strict_flag.py`, `test_rest_corpus_endpoints.py`, `test_run10_upload_poll_delete_counts.py`, `test_upload_selector_field.py`, `test_ingest_input_refusals.py`, `test_seam_doc_consistency.py` | `_status_for` gives exactly four 404s, plus 409 and 502/503; the default app's routes and OpenAPI fault declarations on the three corpus read routes; the docstring facts. **Do not mutate `_FAULT_RESPONSES`** |
| `seam/operator_rest.py` (new) | none directly. Unprotected: `tests/seam/test_rest_transport.py` (parametrize the line-202 call ban) | — |
| `launcher/serve_rest.py`, `launcher/__init__.py` | `tests/launcher/test_launchers.py` | Help output, defaults, `--workers` refusal, the second-launcher lock error, the installed-script health serve. Use `getattr(args, "operator", False)` and pass `log_config` only when `--log-file` is set (Pitfall 3) |
| `seam/engine.py`: `_plan_promotion` extraction, preview | `test_partial_run_evidence.py`, `test_promote_refuses_partial.py`, `test_operator_alias_validation.py`, `test_promotion_posture.py`, `test_promotion_floor.py`, `test_promote_alias_validation.py`, `test_retire_lineage.py`, `tests/ledger/test_ledger_lifecycle.py` | Promote's refusal order (engine.py:2427-2451), transaction span, closed connections |
| `seam/engine.py`: health helper for `clients` | `test_health_probe.py`, `test_health_honesty.py` | HealthReport content and read-only behaviour |
| `seam/engine.py`: trace scrub helper | `test_stop_reason_leak.py`, `test_trace_resolve_strict_flag.py` | The non-debug projection and `node_free_reason` |
| `seam/engine.py`: `_build_stores` (untouched, but its busy mapping is copied) | `tests/stores/test_graph_lock.py`, `test_build_stores_cleanup.py`, `test_evidence_resolve_stores.py` | Busy → 409; no extra handles |
| `seam/refusals.py` (add `UnknownGraphNodeError`) | `test_refusal_catalogue.py` (SEAM-14: every subclass in `__all__`), `test_refusal_status_codes.py` (exactly four 404s), `tests/mcp/test_mcp_refusal_mapping.py`, `test_refusal_reachability.py`. Unprotected: `test_rest_transport.py::_REFUSAL_FACTORIES` (must gain a factory in the same plan) | New type in `__all__`, status 422 |
| `ledger/ledger.py` (`aliases()`) | `tests/ledger/test_ledger_history.py`, `test_ledger_lifecycle.py`, `test_docstring_currency.py` (LEDG-14), `test_alias_resolution.py` | Read-only open, close; **do not edit FA-06 docstrings** (D-09) |
| `seam/selectors.py` (untouched) | `test_selector_reachability.py`, `test_capability_effects.py`, `test_empty_capability_selector.py`, `test_docstring_currency.py` | Tie-break and reachability, which the fixture records |
| `seam/trace_store.py` (`list_page`) | `test_trace_resolve_strict_flag.py`, plus every promote suite through `resolve` | `resolve` unchanged |
| `stores/vector.py` (`list_ids`) | `tests/stores/test_vector_crash_window.py`, `test_vector_validation.py`, `test_vector_reserved_keys.py`, `test_delete_commit_contract.py` | `load_committed` semantics |
| `stores/graph.py` (held-paths helper), `stores/probes.py` (page readers) | `tests/stores/test_graph_lock.py`, `test_graph_delete_cascade.py`, `test_health_probe.py` | Registry refcounting; probe stays read-only |
| `evidence/COVERAGE.md` | `tests/seam/test_run01_coverage_crosscheck.py`. Unprotected: `tests/mcp/test_tool_growth_invariant.py` | Ops-table rows map to tools; the absent table must not mention `compare` |
| `docs/gui/API-INVENTORY.md` | none | — |
| `databasise/tests/fixtures/` (new JSON) | `tests/test_packaging.py` (TOOL-01 wheel RECORD) | Only `fixtures/corpus/**` and `fixtures/eval-corpus/**` are packaged (pyproject.toml:174); a new top-level fixture JSON is not packaged and needs no change |

## Verified Open Points

The orchestrator asked for these four points to be checked.

### Verified Point 1: does uvicorn `log_config` capture the engine's root-logger lines? (CONN-14)

**Answer: only when the file handler is inside the `log_config` dict, on both `uvicorn` and root, with `disable_existing_loggers: False`.** [VERIFIED: probe scratchpad/p16/log_probe.py on uvicorn 0.52.4, real `uvicorn.Server`, one route logging via `logging.getLogger("databasise.seam.engine").error(...)` and one raising]

| Variant | engine line in file | unhandled-500 traceback in file | access line in file |
|---|---|---|---|
| A: default `LOGGING_CONFIG` plus a root `FileHandler` added before `uvicorn.run` | true | **false** | false |
| B: copy of `LOGGING_CONFIG` with a `file` handler on `uvicorn`, `uvicorn.access` and `root` | true | true | true |
| C: as B but `disable_existing_loggers` dropped (dictConfig default `True`) | **false** | true | true |

Why A fails: uvicorn's default config, quoted verbatim from `uvicorn.config.LOGGING_CONFIG` at runtime, is `"uvicorn": {"handlers": ["default"], "level": "INFO", "propagate": false}`, `"uvicorn.error": {"level": "INFO"}`, `"uvicorn.access": {"handlers": ["access"], "level": "INFO", "propagate": false}`, `"disable_existing_loggers": false`. "Exception in ASGI application" is logged on `uvicorn.error`, which propagates only to `uvicorn`, never to root. Why C fails: `engine.py:312` creates `logger = logging.getLogger(__name__)` at import, before uvicorn configures logging, and dictConfig disables pre-existing loggers by default. [VERIFIED: engine.py:312; ledger.py:136 `_log = logging.getLogger(__name__)`; redact.py:61]

What the engine logs today: `_foreign_fault` logs `"engine fault: operation=%s failure_class=%s node=%s cause=%s detail=%s"` with a `redact_secrets`-then-`_URL_RE`-scrubbed traceback (engine.py:326-337), plus warnings such as `"graph store busy"` (engine.py:610). A raw 500 traceback from uvicorn is **not** redacted. [VERIFIED: engine.py:315-338]

### Verified Point 2: the exact refusal order /promote applies, which preview must mirror (CONN-09)

[VERIFIED: engine.py:2463-2485 and 2314-2337; promotion.py:46, 63-64, 144-200; rest.py:124-129, 150-155]

`promote()`:
1. `if verb not in PROMOTION_VERBS: raise UnrecognisedPromotionVerbError(verb=verb)`
2. `if verb in _NOT_BUILT_VERBS: raise GateVerbNotBuiltError(verb=verb)`, where `_NOT_BUILT_VERBS: tuple[str, ...] = ("check", "preview", "run")`
3. `if verb in _GATE_VERBS:` (`("promote-next", "promote-now")`), then `self._floors.any_floor()`. A sqlite error gives `_foreign_fault("promote", exc, failure_class="StoreFault")`, and no floor gives `GateNotCalibratedError(verb=verb)`. **This happens before alias validation and trace resolution.**
4. `_resolve_operator_preconditions(alias, trace_ids, change_origin, refuse_partial=True)`:
   - a. `if alias == "" or _INSTANCE_HASH_PATTERN.match(alias): raise InvalidPromotionAliasError(alias=alias)`
   - b. `if change_origin not in CHANGE_ORIGINS: raise InvalidChangeOriginError(...)`, where `CHANGE_ORIGINS = frozenset({"human_edit", "machine_mutation"})`
   - c. `resolved_records = [self._trace_store.resolve(trace_id) for trace_id in trace_ids]`, which raises `UnknownTraceReferenceError` (**HTTP 404**: `_NOT_FOUND_REFUSALS` holds `UnknownTraceReferenceError, UnknownJobError, UnresolvableEvidenceReferenceError, UnknownGenerationVersionError`; probe printed `UnknownTraceReferenceError status: 404`)
   - d. `refuse_partial_evidence(resolved_records, list(trace_ids))`, which raises `PartialRunEvidenceError`. **Before** arm matching.
   - e. `resolve_single_arm(...)`: `EmptyPromotionTraceIdsError(alias=alias)` for an empty list, `DisagreeingPromotionTraceIdsError(trace_ids=...)` for more than one arm. A non-partial record whose node set matches no arm gives `UnknownTraceReferenceError` (promotion.py:141, 404). A partial record that cannot be identified gives `PartialRunEvidenceError` (promotion.py:156-157).
5. `new_resolved = _wiring_for_row(arm_name, alias=alias)`, which raises `UnsatisfiableSelectorError(selector_kind="alias", requested=alias)` when the arm no longer resolves. This is unreachable today because all six arms resolve.
6. Gate verb with floors: `_refuse_gate_verb`, which always raises `GateNotCalibratedError`, `GateVerbNotBuiltError` (retrieval-side) or `MeasurementPostureRefusalError` (engine.py:2359-2411).
7. `operator-asserted`: `_promote_sync` in `with Ledger(self.store_root) as ledger, ledger.transaction():` (engine.py:2496-2552).

**Prescription for preview (refines D-12; it does not change any decision).** Run steps 1-6 in the same order. When a step raises an outcome refusal (`PartialRunEvidenceError`, `GateNotCalibratedError`, `GateVerbNotBuiltError`, `MeasurementPostureRefusalError`; recommended: also `UnsatisfiableSelectorError` from step 5), return `promotable: false, reason: type(exc).__name__`. When a step raises an input refusal, let it propagate unchanged, with the same status /promote gives. After an outcome refusal, fill `arm`, `mutation_class` and `next_version` on a best-effort basis: re-resolve the records, call `resolve_single_arm`, and catch `SeamRefusalError` as `None`. The testable invariant is: **for any body, preview is 200 with reason X iff /promote raises outcome refusal X; preview raises R iff /promote raises input refusal R; preview is promotable with `next_version` V iff /promote mints V.** Consequence: with no floors, a gate verb plus an unknown trace previews as 200 `GateNotCalibratedError`, exactly as /promote answers 422 `GateNotCalibratedError` for it.

To avoid touching `_resolve_operator_preconditions`, preview calls it unchanged with `refuse_partial=True`. On `PartialRunEvidenceError` it re-resolves the records with `self._trace_store.resolve` (already proven resolvable) to attempt the arm.

### Verified Point 3: does `test_docstring_currency.py` pin the FA-06 docstrings? (D-09)

**Unresolved by black-box probing. Moot under D-09.** [ASSUMED]

Three probes ran the protected test without reading it, with the FA-06 passages appended to or stripped from: selectors.py:50-55, selectors.py:280-302 (`_resolve_alias` docstring), ledger.py:25-33 and ledger.py:429-449 (`by_alias`).
1. In-process plugin. It rewrote `__doc__`, `Path.read_text`/`read_bytes`, `open` and linecache. Result: 10 passed in every variant, **including a positive control that inserted LEDG-14-forbidden text** ("The registry is empty, so every lookup refuses."), with 0 `open` hits.
2. On-disk overlay. Symlinks to the real package, real modified copies of selectors.py and ledger.py, `--import-mode=importlib`, and the test run through the overlay path. Result: 10 passed in every variant, **including a control2 that made selectors.py syntactically invalid**.

Conclusion: the test locates those sources by a route neither probe reached, probably a resolved real path, so the probes cannot tell whether FA-06 wording is pinned. D-09 already forbids editing those docstrings, so no plan depends on the answer. **Rule for plans:** record the D-09 exception in COVERAGE.md and API-INVENTORY.md only, never in selectors.py or ledger.py. Probe scripts: scratchpad/p16/docpin_plugin.py, run_docpin.py, run_docpin_overlay.py.

### Verified Point 4: OpenAPI fault declarations for store-reading routes

[VERIFIED: rest.py:168-180 and a probe of `create_app(...).openapi()` at HEAD]

`_FAULT_RESPONSES` declares only `502` ("Machine fault: an engine run, a store or the v1 engine failed…") and `503` ("Machine fault: the v1 engine is unavailable…"). At HEAD:
- These routes carry `['200', '422', '502', '503']`: `/corpus`, `/corpus/counts`, `/documents`, `/documents/upload`, `DELETE /documents/{document_id}`, `/documents/{document_id}/retry` and `/jobs/{job_id}`.
- These carry only `['200', '422']`: `/evidence/resolve`, `/query`, `/compare`, `/promote`, `/rollback`, `/retire` and `/trace/resolve`. `/health` carries `['200']`.
- **No route declares 409 or 404.**

**Prescription:** add a module-level `_OPERATOR_STORE_RESPONSES = {**_FAULT_RESPONSES, 409: {"model": RefusalBody, "description": "Store busy: …"}}` in operator_rest.py. Never mutate `_FAULT_RESPONSES` in place: that would change the OpenAPI of the seven routes above, which the protected test_corpus_adapter_failures.py checks. Apply it to every operator route that reads a store: /ledger/aliases, /ledger/history, /traces, /promote/preview, /chunks, /graph/nodes, /graph/node and /log. Do not apply it to /info or /wirings, which read no store. 409 is reachable only on the graph routes; declaring the full locked set (502, 503, 409) on each store-reading route follows D-F literally. [ASSUMED: that "declares 502, 503, 409" is meant per route, not as reachability]

## Standard Stack

### Core (all already installed; no new dependency)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.141.1 | Routes, DTOs, OpenAPI `responses=` | The existing transport [VERIFIED: venv import] |
| Starlette | 1.6.0 | TestClient, middleware | The existing transport [VERIFIED: venv import] |
| uvicorn | 0.52.4 | Server; `log_config` dict | The existing launcher [VERIFIED: venv import, probe] |
| pycozo[embedded] | 0.7.6 | Immutable graph reads via the shared registry client | The existing graph store [VERIFIED: l3_cozo probe rerun] |
| sqlite3 (stdlib) | Python 3.12.13 | ledger.db, trace.db reads | The existing ledger and trace store [VERIFIED: venv] |
| logging / logging.config (stdlib) | 3.12 | `FileHandler` inside the uvicorn dict | Probed (Verified Point 1) |
| collections.deque (stdlib) | 3.12 | `deque(file, maxlen=limit)` log tail | One line, no dependency [ASSUMED: adequate at console log sizes] |

### Supporting (tests)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 9.1.1 | Runner (`asyncio_mode = "auto"`, `addopts = '-m "not live"'`) | Every test [VERIFIED: venv, pyproject.toml] |
| pytest-asyncio | 1.4.0 | `async def test_*` | CONN-13 concurrent read |
| httpx | 0.28.1 | `httpx.AsyncClient(transport=httpx.ASGITransport(app=app))` for a same-loop request during an in-flight ingest | CONN-13 [ASSUMED: the API shape is httpx's documented one, not exercised in this repo] |

**Installation:** none.

## Package Legitimacy Audit

No external package is installed by this phase. Every library above is already in the locked venv. Audit not applicable.

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
databasise-rest --operator [--log-file P] --host 127.0.0.1
   │  parser: --operator + non-loopback host → parser.error (before open_engine)
   │  open_engine → .engine.lock, clients
   │  log_config = LOGGING_CONFIG + file handler(P) on uvicorn/uvicorn.access/root   (only if --log-file)
   ▼
build_app(args) → create_app(store_root, workspace, clients, cors, operator=True, log_path=P)
   │   engine = Databasise(..., log_path=P)  (ONE engine, app.state.engine)
   │   if operator: from databasise.seam.operator_rest import add_operator_routes; add_operator_routes(app, engine, log=bool(P))
   ▼
TrustedHost → Origin guard → [CORS] → route (deserialize DTO / Query) ──await──► engine.<method>()
                                                                                   │
        ┌──────────────┬───────────────┬───────────────┬──────────────┬─────────────┼───────────────┐
        ▼              ▼               ▼               ▼              ▼             ▼               ▼
   info()         wirings()      ledger_*()      list_traces()  preview_*()   chunk_page()   graph_*()      log_tail()
   gates.locked() all_wirings +  Ledger.open_    TraceStore.    promote order resolve_sel →  resolve_sel →  deque(P)
   registry keys  resolve_sel    existing(ro)    list_page +    (Point 2) +   family base    store_ns.graph
   CLIENT_EFFECT  per row        aliases()/      node_free_     _plan_        ev_pos.ns →    → probes.graph_
   _TO_KEY                       history_for_    reason         promotion(ro) Faiss.list_ids   page/node_edges
                                 alias                                        → mint_refs     (registry acquire,
                                                                                               immutable, release)
                                                                                               busy → StoreBusyError 409
   SeamRefusalError raised anywhere → app-level _refusal_response (status from _status_for)
```

### Recommended file layout

```
databasise/seam/operator_rest.py         # NEW: DTOs, _OPERATOR_STORE_RESPONSES, add_operator_routes(app, engine, *, log)
databasise/seam/rest.py                  # create_app(..., operator=False, log_path=None): lazy import + call
databasise/seam/engine.py                # 10 methods, _plan_promotion, _client_presence, _public_reason helper
databasise/seam/refusals.py              # UnknownGraphNodeError (+ __all__)
databasise/ledger/ledger.py              # Ledger.aliases()
databasise/seam/trace_store.py           # TraceStore.list_page(limit, offset)
databasise/stores/vector.py              # FaissVectorStore.list_ids(offset, limit)
databasise/stores/graph.py               # held_graph_paths(prefix) helper
databasise/stores/probes.py              # graph_node_page(...), graph_node_edges(...)
databasise/launcher/serve_rest.py        # --operator, --log-file, host refusal, log_config
docs/gui/refusals.json                   # generated
databasise/tests/fixtures/selector-resolution.json   # generated
databasise/tests/seam/test_console_*.py, test_refusal_catalogue_file.py, test_selector_resolution_fixture.py
databasise/tests/stores/test_console_reads.py
```

### Pattern 1: flag-gated include, lazy import

**What:** `create_app` imports and calls `add_operator_routes` only when `operator=True`, so the default app object, its routes and its OpenAPI stay byte-identical. The lazy import also leaves `test_databasise_and_databasise_seam_are_importable_with_no_web_framework_present` (test_rest_transport.py:179-199) unaffected.
**When:** always. **Example:** Code Example 1.

### Pattern 2: route body is exactly one awaited engine call

**What:** `return await engine.<method>(<args built from the DTO, checked_page(...)>)`. Bounds that FastAPI can express (`Query(ge=1, le=1000)` for /log) live in the **signature**, which D-04's AST walk skips. Selectors arrive as `Selector | None` in a `_RequestModel` JSON body, so a malformed selector is the existing 422 refusal path (rest.py:293-314).
**Why:** D-04 and SC1. The call-ban test reads its forbidden set from `selectors.__all__` (`['Selector', 'resolve_selector']`, with `Selector` excluded) and `redact.__all__` (`['FREEFORM_VALUE_KEYS', 'REASON_VALUE_KEYS', 'node_free_reason', 'forbidden_identities', 'assert_no_forbidden_keys', 'assert_no_forbidden_values']`) [VERIFIED: runtime print]. None of the proposed engine method names collide with these.

### Pattern 3: read paths create nothing

- Ledger: `Ledger.open_existing(store_root, read_only=True)` returns `None` when ledger.db is absent, and gives a `PRAGMA query_only` connection with no checkpoint on close (ledger.py:162-206). Always use it as `with handle:`.
- Chunks: `load_committed(dir)` returns `None` when neither file exists and never creates a directory (vector.py:200-218).
- Graph: copy `probe_graph`. Existence check, then the marker check under `_ClientRegistry._lock`, then `acquire`, then `client.run(script, params, True)` (immutable), then `release` in `finally` (probes.py:90-120).
- Never `_build_stores`, never `CozoGraphStore(...)` (its constructor runs `mkdir` and `_ensure_relations`, graph.py:183-194), never `SqliteKVStore(...)`.

### Pattern 4: engine maps store exceptions to seam refusals, once

`GraphStoreBusyError` maps to `logger.warning("graph store busy", exc_info=exc)` and then `raise StoreBusyError(store_kind="graph") from None`, as engine.py:607-611 does. A missing marker, a pycozo bare `Exception` or `VectorStoreCorruptedError` maps to `_foreign_fault(op, exc, failure_class="StoreCorrupted")`. An `OSError` or `sqlite3.Error` on ledger.db or trace.db maps to `_foreign_fault(op, exc, failure_class="StoreFault")`. [VERIFIED: engine.py:607-619] The stores modules raise their own errors and never import seam refusals.

### Anti-patterns to avoid

- **A root-only FileHandler for the log** (Verified Point 1, variant A). It misses every 500 traceback.
- **`log_config=None` when no `--log-file`.** This disables uvicorn's own logging config. Pass `log_config` only when the flag is set.
- **Adding `UnknownGraphNodeError` to `_NOT_FOUND_REFUSALS`.** This breaks the protected exactly-four-404 test (D-16).
- **Spying on `CozoGraphStore` for the degree-query count.** The D-15 read path constructs no `CozoGraphStore`, so such a spy counts zero. Spy on the query function instead (Pitfall 6).
- **Computing `reachable` or calling `resolve_selector` in operator_rest.py.** The parametrized call ban fails.
- **Returning raw `attrs`** on graph routes (D-16).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Page bounds | own limit checks | `corpus.checked_page(limit, offset)`: `PageSizeExceededError(requested, limit=MAX_PAGE_SIZE)` first, then `PageBoundsError(limit, offset)` (corpus.py:198-212) | Existing named refusals, already in the catalogue |
| Selector parsing | query-param selector parse | `Selector \| None` in a JSON `_RequestModel` (rest.py:183-197) | Validator refusals unwrap through `_validation_response` |
| Evidence refs | dict literals | `mint_evidence_refs(items, namespace=ns, kind=TEXT_CHUNK_KIND)`, with `TEXT_CHUNK_KIND = "text_chunk"` (evidence.py:55, 97-131) | Refs then resolve through /evidence/resolve |
| Reason scrubbing | regex in the route | `node_free_reason(value, low_entropy)` with `forbidden_identities(record)[1]`, exactly as `resolve_trace` does (engine.py:2277-2283) | WIRE-03 leak rules |
| Busy detection | new locks | `_gate_for(path).locked()` (engine.py:802-804) and a `_ClientRegistry._entries` snapshot (graph.py:140) | Never acquires, so the read cannot block a write |
| Version minting | own semver | `mint_version`, `declared_surface`, `derive_mutation_class` (promotion.py:203-260) through `_plan_promotion` | /promote parity is the requirement |
| Log formatting | custom JSON log | a copy of `uvicorn.config.LOGGING_CONFIG` plus one `logging.FileHandler` entry | Probed; keeps uvicorn's console output |
| Refusal body keys | hand list | `refusal_body(instance).keys() - {"refusal_type", "message"}` over `_REFUSAL_FACTORIES` (refusals.py:49-63) | The catalogue stays generated, not maintained |

## Common Pitfalls

### Pitfall 1: row tests that fail by TypeError or ImportError at HEAD
**What goes wrong:** `create_app(..., operator=True)` raises `TypeError` and `from databasise.seam.operator_rest import ...` is a collection error, so the BAK pre-fix check sees no AssertionError.
**How to avoid:** use Code Example 9. Assert `"operator" in inspect.signature(create_app).parameters`, `importlib.util.find_spec("databasise.seam.operator_rest") is not None`, `callable(getattr(engine, "info", None))`, `getattr(refusals, "UnknownGraphNodeError", None) is not None` and `Path(...).is_file()`, all inside the test function. Module-level imports only of HEAD names.
**Warning sign:** `ERROR collecting` or `TypeError` in the pre-fix run.

### Pitfall 2: test_rest_transport.py's refusal walk breaks when the new refusal lands
`test_every_refusal_subclass_maps_to_a_non_success_status_carrying_its_named_value` asserts `exc_cls in _REFUSAL_FACTORIES` for every subclass (test_rest_transport.py:537-575). Add `UnknownGraphNodeError: lambda: UnknownGraphNodeError(node_id="n1")` in the **same commit** as the refusal. Constructor shape: keyword `node_id`, a public attribute, the caller's own input. [ASSUMED]

### Pitfall 3: protected launcher tests and new args
`test_launchers.py` is protected and its body was not read. `build_app(args, clients)` may be called with a hand-built `Namespace`, and `uvicorn.run` may be monkeypatched with exact kwargs. Use `getattr(args, "operator", False)` and `getattr(args, "log_file", None)`, and add `log_config=` to the `uvicorn.run(...)` call (serve_rest.py:94) only when `--log-file` is given. Run test_launchers.py after the launcher plan. [ASSUMED: the shapes the protected test uses]

### Pitfall 4: preview diverges from /promote's order
See Verified Point 2. The two traps are a gate verb with no floors, which refuses before any trace lookup, and a partial trace, which refuses before `resolve_single_arm`. Use a differential test: for each body in a small matrix, call preview, then /promote on the same root, and assert the invariant.

### Pitfall 5: `UnknownTraceReferenceError` is 404
CONN-09 test (4) as written ("422 `UnknownTraceReferenceError`") fails against HEAD's `_status_for`. Assert 404. Amend the requirement text (see Requirement-Text Corrections).

### Pitfall 6: degree spy target
CONN-11's test text says "A spy on `CozoGraphStore`". Under D-15 no `CozoGraphStore` exists on the read path. Put the Cozo calls through one small module-level function in probes.py (e.g. `_run_immutable(client, script, params)`) and have the test monkeypatch it to count scripts containing `is_in`. Also assert `CozoGraphStore.node_degree` is never called.

### Pitfall 7: self-loop double count
The batched degree loop `for n in (s, t)` counts a self-loop `(a, a)` twice, while `node_degree` counts the key once (graph.py:291-295). Count `for n in {s, t}`. Cozo rule union is set semantics, so an edge between two page ids appears once and is credited to both. [VERIFIED: l3_cozo rerun, `batched {'a1': 3, 'a2': 2, 'lonely': 0} vs [3, 2, 0]`]

### Pitfall 8: COVERAGE.md absent-table parse
`_parse_markdown_table` stops at the first non-`|` line and splits on `|` (test_tool_growth_invariant.py:276-290). Add rows contiguously inside the existing table, put no `|` inside a cell, and keep the word "compare" out of every operation cell (line 329 asserts `"compare" not in operation.lower()`). Never add an operator op to the `| operation | transports | plan |` table: its `_OPERATION_TO_TOOLS` lookup would fail (lines 301-308).

### Pitfall 9: the BAK check-edit guard is broad
In this session the guard refused **read-only** shell commands whose text named the bare package directory, naming `databasise/tests/clients/test_build_clients.py` each time. Executors should name specific subpaths in shell commands, or run pytest through a script. Edits to unprotected test files (test_rest_transport.py, test_tool_growth_invariant.py) may still be classified as check or helper edits. [ASSUMED: guard behaviour on Edit, not exercised] If the guard blocks one, that is an owner grant checkpoint, not a redesign.

### Pitfall 10: `write_in_flight` must include the HippoRAG gate
`_write_gate_held()` checks only the v1 gate: `return _gate_for(self._v1_working_dir()).locked()` (engine.py:1183-1185). The HippoRAG gate is a separate `_gate_for(self._hipporag_gate_path())` threading lock (engine.py:844-859, 1476-1477). Use `_gate_for(v1).locked() or _gate_for(hipporag).locked()` in a new helper. Do not change `_write_gate_held`, which drives the interrupted-document logic (engine.py:1923-1971).

### Pitfall 11: `graph_busy` key prefix
Registry keys are `str(Path(db_path).resolve())` (graph.py:145). Compare against `str((store_root / workspace).resolve()) + os.sep`, never the raw path, or a relative or symlinked store_root reads false.

### Pitfall 12: an unredacted traceback over HTTP
A raw 500 traceback in the log is not passed through `redact_secrets`; only `_foreign_fault` redacts (engine.py:329). Recommendation: `log_tail` maps each returned line through `_URL_RE.sub("<url>", redact_secrets(line))`, which costs one line and protects the trust boundary that D-19 opens. [ASSUMED: provider exception text can carry a URL]

## Code Examples

All examples are recommended shapes [ASSUMED]. Every name in them that already exists is quoted from source above. New names (`operator`, `log_path`, `add_operator_routes`, `_OPERATOR_STORE_RESPONSES`, the method names and helper names) are proposals.

### 1. create_app include (rest.py)
```python
def create_app(*, store_root, workspace, registry=None, clients=None, cors_origins=(),
               operator: bool = False, log_path: str | Path | None = None) -> FastAPI:
    engine = Databasise(store_root=store_root, workspace=workspace, registry=registry,
                        clients=clients, log_path=log_path)
    ...  # existing body unchanged
    if operator:
        from databasise.seam.operator_rest import add_operator_routes  # lazy: default app unchanged
        add_operator_routes(app, engine, log=log_path is not None)
    return app
```

### 2. operator_rest.py route shapes
```python
_OPERATOR_STORE_RESPONSES = {**_FAULT_RESPONSES, 409: {"model": RefusalBody,
    "description": "Store busy: the graph store is held by another process (StoreBusyError)"}}

class GraphNodesRequest(_RequestModel):
    selector: Selector | None = None
    prefix: str = ""
    limit: int = 50
    offset: int = 0

def add_operator_routes(app: FastAPI, engine: Any, *, log: bool) -> None:
    @app.get("/info")
    async def get_info() -> dict[str, Any]:
        return await engine.info()

    @app.post("/graph/nodes", responses=_OPERATOR_STORE_RESPONSES)
    async def post_graph_nodes(body: GraphNodesRequest) -> dict[str, Any]:
        return await engine.graph_nodes(body.selector, body.prefix, checked_page(body.limit, body.offset))

    @app.get("/traces", responses=_OPERATOR_STORE_RESPONSES)
    async def get_traces(limit: int = Query(default=50), offset: int = Query(default=0)) -> dict[str, Any]:
        return await engine.list_traces(checked_page(limit, offset))

    if log:
        @app.get("/log", responses=_OPERATOR_STORE_RESPONSES)
        async def get_log(limit: int = Query(default=100, ge=1, le=1000)) -> dict[str, Any]:
            return await engine.log_tail(limit)
```
Out-of-range `limit` gives FastAPI's `{detail: [...]}` 422, the documented schema-error shape (rest.py:49-51). Reuse `PromoteRequest` from rest.py for /promote/preview.

### 3. Engine info and wirings
```python
def _client_presence(clients: dict | None) -> dict[str, bool]:
    clients = clients or {}
    return {key: key in clients for key in CLIENT_EFFECT_TO_KEY.values()}   # engine.py:2060, shared with health()

async def info(self) -> dict[str, Any]:
    root = str((self.store_root / self.workspace).resolve()) + os.sep
    return {"version": databasise.__version__, "workspace": self.workspace,
            "clients": _client_presence(self.clients),
            "write_in_flight": _gate_for(self._v1_working_dir()).locked()
                               or _gate_for(self._hipporag_gate_path()).locked(),
            "graph_busy": held_graph_paths(root)}

async def wirings(self) -> list[dict[str, Any]]:
    default_id = resolve_selector(None, registry=self.registry)["wiring_id"]
    rows = []
    for name, w in all_wirings():
        run = without_recipe_only_nodes(w)
        tokens = sorted(_capability_tokens(run, self.registry))
        reached = resolve_selector(Selector(capability=tokens), registry=self.registry)["wiring_id"]
        rows.append({"name": name, "wiring_id": w["wiring_id"], "wiring_version": w.get("wiring_version"),
                     "title": w.get("title"), "node_count": len(w.get("nodes", {})),
                     "effects": sorted(_wiring_effects(run, self.registry)),
                     "provides": w.get("provides") or [], "harnesses": w.get("harnesses") or [],
                     "default_eligible": _is_default_eligible(w, self.registry),
                     "is_default": w["wiring_id"] == default_id, "reachable": reached == w["wiring_id"]})
    return rows
```
Probe output at HEAD [VERIFIED: research_probe.py]:
- `wiring_version` `"1"` for all six rows.
- `harnesses` `[]` for all six.
- `provides`: `["generate"]` for the LightRAG arms, `["qa"]` for hipporag.
- `reachable: true` for all six.
- `is_default` only naive (`lightrag-base`).
- `default_eligible: false` only hipporag.
- Node counts 7/1/17/15/15/14, with query-run counts 6/1/16/14/14/7.

Import `_capability_tokens` and `_is_default_eligible` from selectors (private; the engine already imports `_INSTANCE_HASH_PATTERN` and `_wiring_effects`, engine.py:296-301).

### 4. Graph page reader (probes.py), following probe_graph
```python
def graph_node_page(dir_path: Path, prefix: str, limit: int, offset: int) -> tuple[list[tuple[str, int]], int]:
    db_path = Path(dir_path) / "graph.cozo"
    if not db_path.exists():
        return [], 0
    key = str(db_path.resolve())
    with _ClientRegistry._lock:
        if key not in _ClientRegistry._entries and not _rocksdb_marker_present(db_path):
            raise GraphStoreCorruptedError()        # engine maps to StoreCorrupted
    key, shared = _ClientRegistry.acquire(db_path)  # GraphStoreBusyError propagates; engine maps to 409
    try:
        run = lambda s, p: _cozo_rows(_run_immutable(shared.client, s, p))
        ids = [r[0] for r in run("?[id] := *nodes{id}, starts_with(id, $p) :order id :limit $l :offset $o",
                                 {"p": prefix, "l": limit, "o": offset})]
        total = len(run("?[id] := *nodes{id}, starts_with(id, $p)", {"p": prefix}))  # shortcut: O(N) count, no count() (#244)
        rows = run("?[src, tgt] := *edges{src, tgt}, is_in(src, $ids)\n"
                   "?[src, tgt] := *edges{src, tgt}, is_in(tgt, $ids)", {"ids": ids})
        degree = dict.fromkeys(ids, 0)
        for src, tgt in rows:
            for n in {src, tgt}:
                if n in degree:
                    degree[n] += 1
        return [(i, degree[i]) for i in ids], total
    finally:
        _ClientRegistry.release(key)
```
The query strings are those verified by the l3_cozo probe. `_run_immutable(client, script, params)` is `client.run(script, params, True)`, as probes.py:113 calls it. Node edges: `"?[src,tgt,attrs] := *edges{src,tgt,attrs}, src = $id or tgt = $id :order src, tgt :limit $l :offset $o"`, then project `{src, tgt, edge_types: attrs.get("edge_types"), weight: attrs.get("weight")}`. An unknown node is `"?[id] := *nodes{id}, id = $id"` returning empty, which gives `UnknownGraphNodeError`. A missing `graph.cozo` on /graph/node is also an unknown node (422), since there is nothing to page.

### 5. Ledger.aliases (one query, LedgerEntry rows)
```python
def aliases(self) -> list[LedgerEntry]:
    cur = self._conn.execute(
        "SELECT * FROM ledger WHERE id IN (SELECT MAX(id) FROM ledger "
        "WHERE alias IS NOT NULL AND record_kind != 'tombstone' GROUP BY alias) ORDER BY alias")
    return [self._row_to_record(r, cls=LedgerEntry) for r in cur.fetchall()]
```
This applies the same active-row rule as `by_alias` (`WHERE alias = ? AND record_kind != 'tombstone' ORDER BY id DESC LIMIT 1`, ledger.py:443-447), and `_row_to_record(r, cls=LedgerEntry)` is the projection history_for_alias uses (ledger.py:507). `active_version` = `entry.minted_version`. Record kinds are `"promotion"`, `"rollback"` or `"tombstone"` (ledger.py:36-38 docstring). It is a single SELECT, equivalent to D-09's "DISTINCT alias plus a per-alias by_alias", with no N+1. [ASSUMED: equivalence; covered by the CONN-06 test]

### 6. TraceStore.list_page
```python
def list_page(self, limit: int, offset: int) -> tuple[list[tuple[str, str, dict]], int]:
    # shortcut: full sort per page (created_at has no index), add an index if traces exceed ~10^5
    rows = self._conn.execute("SELECT token, created_at, run_record FROM traces "
                              "ORDER BY created_at DESC, rowid DESC LIMIT ? OFFSET ?", (limit, offset)).fetchall()
    total = self._conn.execute("SELECT COUNT(*) FROM traces").fetchone()[0]
    return [(r["token"], r["created_at"], json.loads(r["run_record"])) for r in rows], int(total)
```
Schema: `token TEXT PRIMARY KEY, run_record TEXT NOT NULL, created_at TEXT NOT NULL`. `created_at` is `datetime.now(UTC).isoformat()` (trace_store.py:71-75, 88). The engine projects `{trace_reference, created_at, partial: bool(rec.get("partial")), degraded: bool(rec.get("degraded")), stop_reason: _public_reason(rec, "stop_reason")}`. `_public_reason` is the helper extracted from engine.py:2277-2283.

### 7. log_config (serve_rest.py main)
```python
run_kwargs: dict[str, Any] = {}
if args.log_file is not None:
    cfg = copy.deepcopy(uvicorn.config.LOGGING_CONFIG)          # keeps "disable_existing_loggers": False
    cfg["formatters"]["file"] = {"format": "%(asctime)s %(name)s %(levelname)s %(message)s"}
    cfg["handlers"]["file"] = {"class": "logging.FileHandler", "filename": str(args.log_file), "formatter": "file"}
    cfg["loggers"]["uvicorn"]["handlers"].append("file")
    cfg["loggers"]["uvicorn.access"]["handlers"].append("file")
    cfg["root"] = {"handlers": ["file"], "level": "INFO"}
    run_kwargs["log_config"] = cfg
uvicorn.run(build_app(args, clients), host=args.host, port=args.port, workers=1, **run_kwargs)
```
This is the variant-B shape, verified by the probe.

### 8. FaissVectorStore.list_ids
```python
def list_ids(self, offset: int, limit: int) -> tuple[list[str], int]:
    snapshot = load_committed(self._dir)            # never reconstructs, never mkdirs
    ids = sorted(snapshot.entries) if snapshot is not None else []
    return ids[offset:offset + limit], len(ids)
```
`_Committed.entries: Mapping[str, dict[str, Any]]` (vector.py:145-153). The constructor does not create the directory (vector.py:273-275). `VectorStoreCorruptedError` propagates, and the engine maps it to StoreCorrupted.

### 9. Row-test guard pattern (BAK pre-fix AssertionError)
```python
import importlib.util, inspect
from databasise.seam.rest import create_app              # exists at HEAD

def _operator_app(tmp_path, **kw):
    assert "operator" in inspect.signature(create_app).parameters, "create_app has no operator flag (CONN-01)"
    return create_app(store_root=tmp_path, workspace="ws", operator=True, **kw)

def test_operator_routes_are_thin_adapters():
    spec = importlib.util.find_spec("databasise.seam.operator_rest")
    assert spec is not None, "databasise/seam/operator_rest.py does not exist (CONN-01)"
    ...
```
The AST rule is the one already probed in scratchpad/p16/surface_ast_probe.py: route decorators `get/post/delete/put/patch`, body equals optional docstring plus `Return(Await(Call(Attribute(Name('engine'), _))))`, banned names, plus a mutant `return Ledger(engine.store_root).aliases()` that must be flagged. Restrict the walk to `fn.body` (D-04).

### 10. Refusal catalogue generator (inside the sync test)
```python
from databasise.tests.seam.test_rest_transport import _REFUSAL_FACTORIES, _all_seam_refusal_subclasses
entries = sorted(({"refusal_type": cls.__name__, "module": cls.__module__,
                   "attribute_keys": sorted(set(refusal_body(f := _REFUSAL_FACTORIES[cls]()) ) - {"refusal_type", "message"}),
                   "http_status": _status_for(f)} for cls in _all_seam_refusal_subclasses()),
                 key=lambda e: e["refusal_type"])
```
`ForeignEngineRefusalError` keys vary by `failure_class` (`missing_keys`/`unsupported_keys` for `V1NotConfigured`, `failed_chunks`/`failure_reasons` for `ExtractionFailed`, refusals.py:851-860), and its `http_status` is 502 or 503. Record the factory's instance (`operation`, `failure_class`, status 502) and add a `notes` string. [ASSUMED: D-07 permits an extra field; otherwise document it in API-INVENTORY.md]

## Row Test Design (one file and one primary test per requirement)

Rule: the primary test named in test_ref must fail by `AssertionError` at HEAD (9ea2fec). Import only HEAD names at module level and guard new API as in Code Example 9. Set test_ref as `path::test_name`; list secondary tests in `evidence`.

| Req | Intended row test (test_ref) | Pre-fix failure (AssertionError) |
|---|---|---|
| CONN-01 | `databasise/tests/seam/test_console_surface.py::test_operator_routes_are_thin_adapters_and_absent_without_the_flag` | `find_spec("databasise.seam.operator_rest") is None`. Secondary: the parametrized `test_rest_transport.py` call ban; a COVERAGE absent-row check for the ten ops; `create_app()` without the flag gives 404 on all ten paths |
| CONN-02 | `databasise/tests/seam/test_refusal_catalogue_file.py::test_the_refusal_catalogue_file_matches_the_code` | `Path("docs/gui/refusals.json").is_file()` is false |
| CONN-03 | `databasise/tests/seam/test_selector_resolution_fixture.py::test_every_fixture_row_resolves_as_recorded` | fixture file absent |
| CONN-04 | `databasise/tests/seam/test_console_info.py::test_info_reports_version_workspace_and_client_presence` | signature assert |
| CONN-05 | `databasise/tests/seam/test_console_wirings.py::test_wirings_lists_six_reachable_rows_matching_the_fixture` | signature assert |
| CONN-06 | `databasise/tests/seam/test_console_ledger.py::test_aliases_lists_each_alias_once_and_creates_no_file` | signature assert |
| CONN-07 | `databasise/tests/seam/test_console_ledger.py::test_history_flags_active_and_tombstoned_and_bounds_the_page` | signature assert |
| CONN-08 | `databasise/tests/seam/test_console_traces.py::test_traces_list_newest_first_with_paging` | signature assert |
| CONN-09 | `databasise/tests/seam/test_console_preview.py::test_preview_matches_what_promote_mints_and_refuses` | signature assert |
| CONN-10 | `databasise/tests/seam/test_console_chunks.py::test_chunks_page_lists_the_selected_modalitys_refs` | signature assert. Secondary: `databasise/tests/stores/test_console_reads.py::test_list_ids_never_reconstructs` (`getattr(FaissVectorStore, "list_ids", None)` assert) |
| CONN-11 | `databasise/tests/seam/test_console_graph.py::test_graph_nodes_page_degrees_prefix_and_busy_409` | signature assert. Secondary: a one-degree-query spy in test_console_reads.py |
| CONN-12 | `databasise/tests/seam/test_console_graph.py::test_graph_node_edges_and_unknown_node_422` | `getattr(refusals, "UnknownGraphNodeError", None) is not None` assert first |
| CONN-13 | `databasise/tests/seam/test_console_info.py::test_store_busy_fields_are_true_during_an_ingest` | signature assert |
| CONN-14 | `databasise/tests/seam/test_console_log.py::test_log_tails_the_launcher_log_and_is_404_without_both_flags` | `assert "--log-file" in build_parser().format_help()` (never `parse_args` with the new flags at HEAD: argparse exits with SystemExit 2, not AssertionError) |

Test-data recipes (no provider spend):
- **Traces for promote, preview and history:** persist through `TraceStore(store_root).persist({...})` with `"arm_id": "<arm>"` and `"nodes": [{"node_id": n} for n in run node ids]`. This is the `_seed_trace` pattern at test_rest_transport.py:603-616. A partial trace adds `"partial": True`.
- **CONN-08 real traces:** `synthetic_naive_store` fixture (tests/seam/conftest.py) with `_stub_clients`, three POST /query calls.
- **CONN-13:** HippoRAG ingest with `Selector(capability=["reads_graph"])` and a stub LLM whose `chat` awaits an `asyncio.Event`. The ingest takes the HippoRAG gate and then `_build_stores` (with the `CozoGraphStore`) before nodes run (engine.py:1476-1480), so both flags are true while blocked. Read with `await engine.info()` and with `httpx.AsyncClient(transport=httpx.ASGITransport(app=app))` in the same loop.
- **CONN-11 busy:** open `pycozo.Client("rocksdb", str(path.resolve()), dataframe=False)` in-process with the registry empty. The route's `acquire` then raises the lock error that `_is_lock_error` recognises (`"kIOError"` and `"lock hold by current process"`, graph.py:122-125), giving 409. [VERIFIED: l3_cozo rerun printed `rocksdb::kIOError` "lock hold by current proc"]
- **CONN-06 "no open connection":** count `/proc/self/fd` links resolving to `<store_root>/ledger.db` before and after the call. [ASSUMED: the protected LEDG-06 test uses a similar path-based check (ledger.py:186-188 says "the LEDG-06 lifecycle check recognises ledger connections by their file path")]

## Requirement-Text Corrections (make before setting test_refs)

1. **CONN-09:** "An unknown trace id returns 422 `UnknownTraceReferenceError`" and test (4) should say **404** (rest.py:124-129, 150-155; probe). D-12's "input refusals still raise 422" should read "raise with /promote's status (404 for an unknown trace)".
2. **CONN-11 test:** "A spy on `CozoGraphStore` asserts one degree query per page" should read "a spy on the probes read function", because the D-15 path builds no `CozoGraphStore`.
3. **Ledger sync:** ledger/REQUIREMENTS.json CONN-01..14 `text` still holds the pre-amendment wording (lines 1897-2079). Re-sync from REQUIREMENTS.md through the ledger's amend path before the executor sets test_refs.
4. **CONN-14:** state that out-of-range `limit` is FastAPI's schema 422 (`{detail: [...]}`, no `refusal_type`), or choose a named refusal. The recommendation is the schema 422, with no new refusal type.
5. **CONN-12:** a missing `graph.cozo` under /graph/node answers `UnknownGraphNodeError` (422), while /graph/nodes answers `total: 0`. Say so, or the two routes look inconsistent.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Shared `lightrag-base` wiring_id for all LightRAG arms | each arm has its own `wiring_id`; `arm_id` = name | Phase 13 D-03 | `/wirings` rows are distinct by id, but `title` is still shared |
| `LedgerRecord` only | `LedgerEntry` adds `id`, `created_at` (ledger.py:125-133) | Phase 14 LEDG-07 | CONN-06/07 project from it; no raw-row read |
| Validator refusal wrapped in `ctx.error` | unwrapped to the normal body (rest.py:293-314) | Phase 9 SEAM-02 | Catalogue has one body shape |
| 30 refusal types, some outside `__all__` | 50, all in `__all__` | Phases 9-15 | CONN-02 count |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | test_docstring_currency.py does not pin the FA-06 wording | Verified Point 3 | None while D-09's no-edit rule holds; a plan that edits those docstrings must run the test |
| A2 | "declares 502, 503, 409" applies to every store-reading route, not only where reachable | Verified Point 4 | Cosmetic OpenAPI over-declaration |
| A3 | protected test_launchers.py builds `Namespace` by hand or checks `uvicorn.run` kwargs exactly | Pitfall 3 | If not, the getattr and conditional-kwarg care is harmless |
| A4 | the BAK guard may block Edit on unprotected test files | Pitfall 9 | An owner grant checkpoint mid-execution |
| A5 | `UnknownGraphNodeError(node_id=...)` keyword shape | Pitfall 2 | Only the factory and catalogue entry change |
| A6 | Code examples' new names and shapes | Code Examples | Plans may rename; behaviour is what the tests pin |
| A7 | a single-SELECT `aliases()` is equivalent to DISTINCT plus by_alias | Code Example 5 | Covered by the CONN-06 test |
| A8 | read-time redaction in `log_tail` is wanted | Pitfall 12 | One line; drop it if the owner wants raw lines |
| A9 | an extra `notes` field in refusals.json for `ForeignEngineRefusalError` is acceptable | Code Example 10 | Move the note to API-INVENTORY.md |
| A10 | `deque(file, maxlen=N)` is fast enough | Standard Stack | Full scan per call; acceptable at console log sizes; `shortcut:` comment |
| A11 | httpx `ASGITransport` same-loop pattern works for CONN-13 | Supporting stack | Fall back to an engine-level `await engine.info()` only |

## Open Questions

1. **Should `UnsatisfiableSelectorError` from `_wiring_for_row` be an outcome or an input refusal in preview?**
   - Known: it is unreachable today (all arms resolve). D-12 lists neither.
   - Recommendation: outcome (`promotable: false`), since the caller's input is well-formed. A planner may leave it propagating; no test can reach it.
2. **`tombstoned` for the tombstone row itself.**
   - Known: tombstone rows have `minted_version` None and a `targets_version`.
   - Recommendation: `tombstoned = (r.minted_version or r.targets_version) in tombstoned_versions` and `active = r.minted_version in active_set`. The CONN-07 test pins only V1, V2 and V3.
3. **Does `--log-file` without `--operator` still write the file?**
   - Recommendation: yes (log file written, route not mounted). D-18 gates only the route.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python venv `databasise/.venv` | all | ✓ | 3.12.13 | — |
| fastapi / starlette / uvicorn | routes, launcher | ✓ | 0.141.1 / 1.6.0 / 0.52.4 | — |
| pycozo embedded (RocksDB) | graph routes | ✓ | 0.7.6 | — |
| pytest / pytest-asyncio / httpx | tests | ✓ | 9.1.1 / 1.4.0 / 0.28.1 | — |
| uv | `test_command` (`cd databasise && uv run pytest -q`) | ✓ | 0.11.21 | `.venv/bin/python -m pytest` |
| v1 interpreter | not needed: no CONN test uses the real driver | — | — | — |
| Provider endpoints | none (no spend) | — | — | — |

**Missing dependencies with no fallback:** none.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 + pytest-asyncio 1.4.0 (`asyncio_mode = "auto"`) |
| Config file | `databasise/pyproject.toml` `[tool.pytest.ini_options]` (`testpaths = ["tests"]`, `addopts = '-m "not live"'`) |
| Quick run command | from `databasise/`: `.venv/bin/python -m pytest -q tests/seam/test_console_*.py tests/seam/test_refusal_catalogue_file.py tests/seam/test_selector_resolution_fixture.py tests/stores/test_console_reads.py` |
| Phase guard suite | from `databasise/`: `.venv/bin/python -m pytest -q tests/seam/test_rest_transport.py tests/seam/test_refusal_status_codes.py tests/seam/test_refusal_catalogue.py tests/mcp/test_tool_growth_invariant.py tests/seam/test_run01_coverage_crosscheck.py tests/seam/test_page_bounds.py tests/stores/test_graph_lock.py tests/seam/test_store_refusal_status.py tests/launcher/test_launchers.py tests/seam/test_partial_run_evidence.py tests/seam/test_promote_refuses_partial.py tests/seam/test_promotion_posture.py tests/seam/test_health_probe.py tests/seam/test_selector_reachability.py tests/seam/test_leak.py`. Baseline at HEAD: **276 passed in 60 s** [VERIFIED: run this session] |
| Full suite command | `cd databasise && uv run pytest -q` (config `test_command`), or `.venv/bin/pytest` and `.venv/bin/python -m pytest` both (RUN-12 style) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command (from `databasise/`) | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CONN-01 | thin adapters, AST mutant, 404 without flag, REST-only rows | unit (AST) + TestClient | `.venv/bin/python -m pytest -q tests/seam/test_console_surface.py tests/seam/test_rest_transport.py -k "thin or forbidden or calls_no"` | ❌ Wave 0 |
| CONN-02 | catalogue in sync | unit | `.venv/bin/python -m pytest -q tests/seam/test_refusal_catalogue_file.py` | ❌ Wave 0 |
| CONN-03 | fixture in sync | unit | `.venv/bin/python -m pytest -q tests/seam/test_selector_resolution_fixture.py` | ❌ Wave 0 |
| CONN-04 | /info presence-only, no store_root | TestClient | `.venv/bin/python -m pytest -q tests/seam/test_console_info.py -k presence` | ❌ Wave 0 |
| CONN-05 | /wirings six rows, cross-check fixture | TestClient | `.venv/bin/python -m pytest -q tests/seam/test_console_wirings.py` | ❌ Wave 0 |
| CONN-06 | aliases, no file, no open fd | TestClient | `.venv/bin/python -m pytest -q tests/seam/test_console_ledger.py -k aliases` | ❌ Wave 0 |
| CONN-07 | history active/tombstoned, bounds | TestClient | `.venv/bin/python -m pytest -q tests/seam/test_console_ledger.py -k history` | ❌ Wave 0 |
| CONN-08 | traces newest first, paging, scrub | TestClient | `.venv/bin/python -m pytest -q tests/seam/test_console_traces.py` | ❌ Wave 0 |
| CONN-09 | preview/promote differential, no ledger.db | TestClient | `.venv/bin/python -m pytest -q tests/seam/test_console_preview.py` | ❌ Wave 0 |
| CONN-10 | chunks per family, refs resolve, no reconstruct | TestClient + unit spy | `.venv/bin/python -m pytest -q tests/seam/test_console_chunks.py` ; `.venv/bin/python -m pytest -q tests/stores/test_console_reads.py -k list_ids` | ❌ Wave 0 |
| CONN-11 | node page, one degree query, 409 busy | TestClient + spy | `.venv/bin/python -m pytest -q tests/seam/test_console_graph.py -k nodes` ; `.venv/bin/python -m pytest -q tests/stores/test_console_reads.py -k degree` | ❌ Wave 0 |
| CONN-12 | edges allowlist, unknown → 422 | TestClient | `.venv/bin/python -m pytest -q tests/seam/test_console_graph.py -k node_edges` | ❌ Wave 0 |
| CONN-13 | busy flags during blocked ingest | async integration (stub clients) | `.venv/bin/python -m pytest -q tests/seam/test_console_info.py -k busy` | ❌ Wave 0 |
| CONN-14 | /log tail, 404 without both flags, 422 bounds | TestClient + parser | `.venv/bin/python -m pytest -q tests/seam/test_console_log.py` | ❌ Wave 0 |
| (manual) | a real `databasise-rest --operator --log-file` writes a 500 traceback to the file | manual / smoke | probe pattern scratchpad/p16/log_probe.py variant B | — |

### Sampling Rate

- **Per task commit:** the quick run command plus the row test the task targets.
- **Per wave merge:** the quick run plus the phase guard suite (60 s).
- **Phase gate:** full suite green under both `.venv/bin/pytest` and `.venv/bin/python -m pytest` before `/gsd-verify-work`; then each row's pre-fix AssertionError check at 9ea2fec.

### Wave 0 Gaps

- [ ] `tests/seam/test_console_surface.py`: CONN-01 (AST rule, mutant, flag-off 404s, COVERAGE absent rows)
- [ ] `tests/seam/test_refusal_catalogue_file.py`: CONN-02 (regenerate under an env flag, e.g. `DATABASISE_REGENERATE=1` [ASSUMED name])
- [ ] `tests/seam/test_selector_resolution_fixture.py`: CONN-03
- [ ] `tests/seam/test_console_info.py`, `test_console_wirings.py`, `test_console_ledger.py`, `test_console_traces.py`, `test_console_preview.py`, `test_console_chunks.py`, `test_console_graph.py`, `test_console_log.py`
- [ ] `tests/stores/test_console_reads.py`: `list_ids` no-reconstruct spy, one-degree-query spy, `held_graph_paths`
- [ ] Shared helper: `_operator_app(tmp_path, **kw)` (Code Example 9). Put it in each file, or in `tests/seam/conftest.py` only as a plain function, never a module-level new-API import.
- [ ] Framework install: none.

## Security Domain

`security_enforcement` is `false` in .planning/config.json, so the ASVS section is omitted. The phase-specific exposure controls are locked in D-01, D-10 and D-19: loopback-only plus `--operator`, the Origin guard and CORS reuse, no credentials or URLs in /info, and refusal bodies free of causes. Pitfall 12 adds a recommended read-time redaction on /log.

## Sources

### Primary (HIGH confidence; read or run this session)
- databasise/seam/rest.py:1-552; launcher/serve_rest.py:1-101; launcher/__init__.py:1-129
- databasise/seam/engine.py:305-338, 440-464, 575-620, 790-860, 1118-1192, 1462-1501, 1960-2062, 2240-2556
- databasise/seam/promotion.py:100-260; seam/refusals.py:40-69, 350-390, 725-1032; seam/selectors.py:1-60, 140-305; seam/evidence.py:1-170; seam/corpus.py:195-215, 312-332; seam/trace_store.py:1-104
- databasise/ledger/ledger.py:25-40, 120-230, 400-507; stores/graph.py:80-330; stores/probes.py:1-176; stores/vector.py:145-285; wirings/resolve.py:36-235
- databasise/tests/seam/test_rest_transport.py:100-230, 410-635, 780-850; tests/mcp/test_tool_growth_invariant.py:255-335; tests/_ast_helpers.py; tests/seam/test_status_during_write.py:1-80 (all unprotected)
- databasise/evidence/COVERAGE.md:80-128; docs/gui/API-INVENTORY.md:690-722; ledger/REQUIREMENTS.json (Read tool); .planning/REQUIREMENTS.md:690-745; ROADMAP.md:431-455; 09-CONTEXT.md:21
- Probes (scratchpad/p16/): log_probe.py (new), research_probe.py (new), docpin_plugin.py, run_docpin.py, run_docpin_overlay.py (new), l3_cozo.py (rerun), run_baseline.py (new; 276 passed)
- Lane reports: report-surface.md, report-ledger.md, report-corpus.md, report-info.md (built on, not redone)

### Secondary
- uvicorn `LOGGING_CONFIG` printed from the installed 0.52.4 package (runtime).

### Tertiary
- none. Graph-context step (graphify) skipped: every capability was located by direct source reads.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH. All libraries are installed and version-printed; nothing new.
- Architecture: HIGH. Each read path mirrors an existing, tested pattern (probe_graph, open_existing, load_committed).
- Pitfalls: HIGH for 1, 2, 4, 5, 7, 8, 10, 11 (source or probe); MEDIUM for 3 and 9 (protected or guard internals not readable).
- Verified Point 3: LOW (inconclusive by design), moot under D-09.

**Research date:** 2026-10-22
**Valid until:** 2026-11-21 (stable codebase; re-check if Phases 17-18 touch rest.py or engine.py first)
