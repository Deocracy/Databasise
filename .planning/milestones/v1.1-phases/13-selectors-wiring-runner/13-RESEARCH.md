# Phase 13: Selectors, Wiring & Runner - Research

**Researched:** 2026-10-19
**Domain:** Python seam engine (`databasise/seam`), runner (`databasise/runner`), validator, wirings, run-record schema
**Confidence:** HIGH for code locations and mechanisms (every cited file was opened this session); MEDIUM for the items in the Assumptions Log and Open Questions

Provenance tags used below: `[VERIFIED: path:lines]` = file opened with Read this session and the value quoted beside the claim; `[VERIFIED: probe]` = a read-only script run this session (scripts are in the session scratchpad, nothing in the repo changed); `[CITED: p13-research.txt]` = prior six-agent study, not re-verified here; `[ASSUMED]` = inference, needs confirmation.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### A. Arm selection, evidence and identity (WIRE-01, 02, 12)

- **D-01 (WIRE-01, read-namespace capability):**
  - **Problem.** Hybrid, local and global share one pruned effect union: {calls_embedding, calls_llm, calls_rerank, reads_graph, reads_kv, reads_vector}. No tie-break can tell them apart.
  - **Mechanism.** Add read-namespace capability tokens of the form `reads_vector:<namespace>` (a Databasise token format under CONTRACT §14.2's read-namespace rows and CONTRACT.md:793).
    - Parts declare them in a new `Part` field (`reads_namespaces`). They never go in `Part.effects`, which WIRE-16 validates against the 17-member Effect literal.
    - `_match_capability` matches them through a matching-only helper.
    - `_wiring_effects` is unchanged, because promotion's `declared_surface` and the compare `mutates_store` check also read it.
  - **Resulting resolution:**
    - `{reads_vector:entities}` → local
    - `{reads_vector:relationships}` → global
    - both → hybrid
    - effect-only selectors resolve exactly as at HEAD: `{reads_vector}` → naive, `{calls_llm}` → bypass, `{reads_graph}` and `{reads_graph, reads_kv}` → hipporag (the protected HIPP and STOR selector tests rely on this).
  - **Docstring.** The `selectors.py` docstring states every capability-to-arm mapping and the one-node margin (hipporag has 14 full nodes against local/global's 15).
    - It must keep `all_wirings()` and must avoid the phrases protected SEAM-16 forbids ('registry is empty', 'five arms', 'five Phase 3 arms', '_ARM_NAMES').
  - **Not in scope:** the §14.2 load-time namespace typecheck (see Deferred).
- **D-02 (WIRE-02, KG-arm evidence):**
  - LightRAG `assemble` emits `items`: the chunks it actually put into the context, which is v1's truncated_chunks reference list, in context order.
  - The hybrid, local and global arm patches set `evidence_position` to `{node: assemble, namespace: chunks}`.
  - naive is unchanged (base.json keeps chunk-vector).
  - bypass sets `evidence_position: null` and returns no evidence by declaration.
  - The validator gains a check: `provides` and `evidence_position.node` must name nodes the resolved wiring contains. This is the 'ghost' test.
  - The `MalformedEvidenceItemError` guard for an output without `items` (WIRE-14, engine.py:2074) lands with or before this change.
- **D-03 (WIRE-12, arm identity and hash):**
  - **Identity.** `resolve_arm` gives each arm its own `wiring_id`: `lightrag-<arm>` for the patched arms; naive keeps `lightrag-base`. `RunRecord.arm_id` becomes the candidate arm name.
    - `wiring_family()` still returns 'lightrag', so corpus routing is unaffected.
    - The `redact.py` forbidden-value set picks up the new ids automatically.
  - **Hash.** `wiring_instance_hash` is computed from the FULL resolved wiring before query, token-allowance and max_total_tokens injection, so it is stable across queries on one arm.
    - Protected `tests/seam/test_query_trace_nodes.py` (LRAG-19) pins the after-injection hash at lines 33-38 and 51. It needs the owner's `grant-check-edit`.
  - **Unprotected test follow-up.** `test_cross_modality_run.py:117,123` move to `wiring_family(...) == 'lightrag'`.
- **D-04 (WIRE-12, a refusal carries trace_token):**
  - On the query path, the engine persists the RunRecord before raising any post-dispatch refusal. These are: a store fault, two answering provides nodes, malformed evidence, and an unbudgetable participant.
  - It then sets `trace_token` as a public attribute on that refusal. The generic `refusal_body` exports it on both transports. Pre-dispatch refusals carry none.
  - Two answering provides nodes (engine.py:1008-1013, a bare RuntimeError today, so a 500) become a named refusal in `refusals.__all__`. That refusal also needs a factory in the unprotected `test_rest_transport.py::_REFUSAL_FACTORIES`.
  - The `ForeignEngineRefusalError` docstring sentence 'Every other class keeps exactly operation and failure_class' is updated.

#### B. Consumer vocabulary and refusals (WIRE-03, 04, 05, 06, 14, 16, 17)

- **D-05 (WIRE-03, closed node-free reason codes):**
  - `stop_reason` and `degradation_reason` come from one closed set, defined in `runner/trace.py`:
    - `node_failed` (any node exception)
    - `placement_refused`
    - `budget_halt` (kept; protected STOR-06 uses it)
    - `declared_fallback`, the existing Phase 12 D-21 stop_reason code
    - `fallback_path_taken`, the existing Phase 12 D-21 degradation_reason code
    - `cancelled`
  - The node-level detail stays on `NodeTrace.cross_process_failure_cause` (redacted since Phase 12 D-11). Only `debug=True` returns it.
  - The leak gate in `seam/redact.py` also runs at response time:
    - It applies a node-id substring check to the two reason fields only, on the envelope and on the non-debug trace.
    - Every other field keeps its equality key-walk, so an answer containing 'generate' or 'qa' never trips it.
    - The docstring keeps the literal phrase 'test-time gate' (protected SEAM-16 test).
  - `resolve_trace` maps pre-Phase-13 stored free-text reasons to `node_failed`.
- **D-06 (WIRE-04, depth_label):**
  - The answering node's effective depth: the provides node, which after Phase 12 D-16 equals the minimum over the pruned path.
  - It is `null` when no provides node returned a completion. Key the null on that, not on `partial`.
  - The envelope field becomes `Depth | None`, using the existing `parts/schema.py:51` literal. The 'stage' default at engine.py:1002 is removed.
- **D-07 (WIRE-05, named pre-dispatch refusals):**
  - **Cycles.** `parsed.report.cycles` is checked inside `_refuse_unparseable`. That gives one 422 on query, ingest, delete and retry before any store opens. It moves ingest and delete cycles from 502 to 422; no shipped wiring is cyclic.
  - **Runner pre-flight errors.** The engine translates `InvalidMaxConcurrencyError`, `InvalidTokenAllowanceError`, `GuardDeclarationError` and `EnvironmentDigestError` (D-16) into seam refusals defined in `seam/refusals.py`, all listed in `__all__`.
    - The runner classes stay runner classes, because protected SEAM-14 requires every SeamRefusalError subclass to live in refusals.py.
    - The node id stays private (the `_node_id` precedent).
    - The status is 422 unless noted. Protected SEAM-04 requires 422 for any new class unless it is listed elsewhere.
  - **Integer checks.** `isinstance(raw, int) and not isinstance(raw, bool)` at scheduler.py:366 and 385.
  - **Violation detail (an exception to the requirement text).** The public 422 body keeps each violation's `code` only. `pointer` and `message` stay private, on the refusal and in the server log, because pointers embed node ids and messages listed registered parts. This follows the phase goal and the Phase 12 D-09 precedent. It is recorded as an exception clause on WIRE-05.
- **D-08 (WIRE-06, validator robustness):**
  - `parse_wiring` reports and never raises on `[]`, `{'nodes': None}` or `{'nodes': [1]}`.
  - Cycle node ids are deduplicated.
  - Pointers are RFC 6901-escaped.
  - A wiring node kind that differs from `Part.kind` is a violation. Verified at HEAD that no shipped wiring trips this.
  - The CODE_UNKNOWN_COMPONENT message no longer lists registered parts or quotes a KeyError.
- **D-09 (WIRE-14, engine internals):**
  - A retrieval output with no `items` raises `MalformedEvidenceItemError`, inside the try at engine.py:2074-2078.
  - `delete_document` builds stores from the corpus-delete wiring's `store_namespaces`.
  - `resolve_evidence` never opens the Cozo graph.
  - HippoRAG ingest reports the upstream node's real exception from `node_exceptions`. Partly done in Phase 12 D-09; finish the remaining leg.
  - `query`, `query_stream` and `compare` stop accepting a `debug` keyword they discard. Check every REST, MCP and tools caller first.
  - The `_build_stores` docstring is corrected.
- **D-10 (WIRE-16):**
  - `PartRegistry.register` validates `effects` against the Effect literal, so `Part(effects=['reads_space'])` is refused.
  - The `query.py:24-27` docstring is rewritten to say what is actually reachable.
  - The four-member `UnconsumableQueryMemberError` leg already passes at HEAD. Its fail-first proof comes from the registration and docstring legs.
- **D-11 (WIRE-17, keep both refusals):**
  - `MutableStoreComparisonExcludedError` stays. CONTRACT.md:629 makes it a MUST, and LEDG-12 may make it reachable.
    - The one-selector compare branch (engine.py:1181-1182) moves below the mutates_store check, so `compare([s])` on a mutates_store wiring refuses with 422.
    - Its docstring keeps 'unreachable' (protected SEAM-16).
  - The ingest `NoWritePathForModalityError` mapping stays (LEDG-13 requires it).
  - **Exception clause.** The requirement's 'DELETE with {capability: writes_graph}' case can no longer occur. HippoRAG delete succeeds (HIPP-16), and writes_graph is unsatisfiable (Phase 12 D-16). The test pins the reachable case instead: `retry_document` with a HippoRAG selector raises `NoWritePathForModalityError`.
  - **Unbudgetable negative test.** It gives the shipped client a usage-bearing response, because a no-usage response makes LightRAG arms unbudgetable too.

#### C. Run-record truth (WIRE-10, 11, 13, 18)

- **D-12 (frozen-schema handling for WIRE-10 and WIRE-11):**
  - **Problem.** `docs/system-model/rig-trace.schema.json` is a frozen verbatim copy. Its NodeTrace has `additionalProperties: false`, a boolean `cache_hit`, a T0..T3 `tier` enum and `realised_budget_share ≤ 1`. The WIRE-10 and WIRE-11 fields cannot validate against it.
  - **Mechanism.** The frozen copy and RIG.md stay unedited. Databasise adds a derived schema, `databasise/evidence/rig-trace.databasise.schema.json`: the frozen schema plus additive amendments.
    - nullable `cache_hit`, `tier` and `feed_tier`
    - `status`
    - `execution_mode`
    - `spent` and `allowance`
    - the D-05 reason codes
  - **Records.** A deviation record (`databasise/evidence/RIG-TRACE-DEVIATIONS.md`) lists each amendment against RIG.md §TR.1, in the §R defect-row form RIG.md:110 asks for. The conftest `assert_valid_trace` validates against the derived schema.
- **D-13 (WIRE-10, one NodeTrace per node):**
  - Every node of the Phase 12 D-16 PRUNED run wiring (`run_resolved`, engine.py:1982) gets exactly one NodeTrace. Its status is completed, failed, cancelled or not-scheduled.
  - Pruned recipe-only nodes get no trace. Protected LRAG-19 asserts `embedder-index not in node_ids`, and D-16 holds.
  - **Failures.** Measured wall time comes from `_run_node`'s start carried on `NodeExecutionError`. The exceptions after dispatch (meter, guards, NodeTrace build) are guarded.
  - **Promotion.** `promotion._dispatched_node_ids` filters on `status == completed` (or uses the D-03 wiring_id), so a partial run is never matched to the full arm set.
  - `result['node_exceptions']` stays (protected STOR-05).
- **D-14 (WIRE-11):**
  - `tier` and `feed_tier` are `null`, since the runner has no evidence-item tier machinery (CONTRACT.md:276), the same as the `bundle_ref` sentinel precedent.
  - Budget overspend is reported in new `spent` and `allowance` integers. The share stays capped at 1.
  - `cache_hit` is `null` unless a part reports it.
    - Known effect: `eval/calibration.py` then refuses real-engine A/A calibration. That is TOOL-12's intent (Phase 15); record it in STATE.
  - `execution_mode` is stamped on every NodeTrace.
  - The stale in-process comments (now scheduler.py:659-660 and 687) are fixed.
- **D-15 (WIRE-13, seam events):**
  - `SeamEvent.component` is the resolved capability (`mutates_store`), not a `part.name_at_version` that carries 'lightrag/'. This follows CONTRACT.md:630 and §18.3.
    - Protected `tests/seam/test_lightrag_ingest_mach11.py` (LRAG-03, lines 17, 28 and 34) pins the old value. It needs the owner's `grant-check-edit`.
  - The outcome is 'failed' when the node failed (the D-13 status, or `cross_process_failure_cause is not None`), and 'halted' only on a budget halt.
  - The ingest-returns-events half is already met at HEAD (LRAG-03). Its fail-first proof uses `record-fail --at` a commit before 11-01.
  - The failed-event test uses an injected query candidate or a `_mach11_events` unit test, because ingest and delete refuse before events are built.
- **D-16 (WIRE-15, environment identity):**
  - `environment_hash` drops `platform.platform()` and folds in OS and architecture (`platform.system()`, `platform.machine()`) plus the libc version (`platform.libc_ver()`). That keeps CONTRACT.md:178's runtime-closure coverage (native wheels link glibc) without identity changing on every kernel update.
  - **Health.** `health()` computes the digest. On failure it appends one fixed text to `engine_reason` and reads `degraded`. No new field: protected LRAG-13 and STOR-04 pin the engine and stores key sets.
  - **Query paths.** `EnvironmentDigestError` reaching query, ingest or delete becomes a named seam refusal (D-07).
  - The failure is not cached, and tests use `cache_clear()`.
- **D-17 (WIRE-18 and concurrency truth):**
  - `ctx._semaphore` and per-node `max_concurrency` stay; openie uses them (Phase 12 D-08). That leg's fail-first proof uses `record-fail --at` before 40e541f.
  - `run_wiring` echoes `determinism_setting` and `concurrency_setting` into its result, so 'threaded through' becomes true. Protected STOR-05 passes them, so nothing is removed.
  - The budget-apportionment API (`budget.py:42-125`) and the eight unparsed `apportionment_policy` / `apportioning_node` strings in `databasise/wirings/` are deleted:
    - base.json:95, 108, 119-120, 130-131 and 162
    - arm-global and arm-local :20
    - arm-hybrid :12
    - CONTRACT §9 D4's MUST is vacuous while no node apportions a metered budget. Record that in the port record.
  - The frozen `docs/system-model/wirings` and `evidence/wirings` copies are left alone.
  - **Concurrency truth.** `concurrency_setting` stays 'sequential' and the scheduler is made to run it truthfully: it awaits nodes one at a time within a ready batch, instead of an asyncio.TaskGroup.
    - That keeps bundle@v1's A/A keying (RIG §AA.1).
    - The latency cost is limited to parallel branches, which are vector lookups on the shipped arms.
    - Intra-node concurrency such as openie's semaphore is unaffected.

#### D. Guards and placement (WIRE-07, 08, 09)

- **D-18 (WIRE-07):**
  - Nodes that call machine-owned LLM, embedding or rerank clients through `ctx.clients` count as in-process (pure for placement). The machine injects and meters the client (CONTRACT.md:72, 529, 599). Moving them would refuse every query arm at dispatch.
  - `validator/depth.py`'s duplicate `derive_execution_mode` is deleted, so placement has one source: `validator/execution_mode.py`. Unprotected `tests/parts/test_reference_parts.py` moves to the single source (a fixpoint is `long-lived-service`).
  - Dead items are removed: the stale 'Phase 1' text, the 'read-only' docstring at parse.py:101 and the getattr at blast_radius.py:57.
  - The `derive_execution_mode(['calls_llm'], 'stage')` check already passes. Fail-first comes from the deleted-duplicate and dead-text legs.
- **D-19 (WIRE-08, a guard reads one declared signal):**
  - A guard declaration gains an explicit `signal` key, the boolean output key the evaluating node emits: fact-filter's `guard_fired`, assemble-result's `dpr_stand_in`.
  - `evaluate_guards` reads `output[signal]`. A missing evaluating node or missing key is a refusal, never a fire.
  - `_GuardAwareResult` (fact_filter.py) and `_StandInResult` (assemble_result.py) are deleted, and both parts return plain dicts.
  - **Ordering.** `signal` comes after `granularity` in `declare_guard`, and granularity is validated first. Protected test_dpr_fallback_guard.py:311-322 calls it with four keywords.
  - **Misdeclared guards** (bad keys, an evaluating node that is not an ancestor of a consumer) are refused before dispatch, with `GuardDeclarationError` translated by D-07. The check runs on the D-16-pruned wiring.
  - The hipporag `config_hash` shifts (see D-21).
- **D-20 (WIRE-09):**
  - The declared LightRAG keyword fall-through guards are dropped from `databasise/wirings/lightrag/arm-local.json-patch.json` and `arm-global.json-patch.json` (the `guards` arrays at :29-41), from `wirings/lightrag/README.md:129-130` and from `docs/gui/CODEBASE-MAP.md:332`.
  - Reinstating v1's chain switch would put the relation chain back into local. That would give local hybrid's node set, which breaks promotion's node-set arm matching and CONN-05's pinned counts.
  - The frozen `docs/system-model` copies keep them, as a recorded deviation in the LightRAG port record.

#### E. Cross-cutting

- **D-21 (hash-shift batching):**
  - D-03 (per-arm wiring_id and pre-injection hash), D-16 (environment inputs), D-17 (deleted config strings) and D-19 (the guard `signal` key) each shift config, instance or wiring-instance hashes.
  - They land in one plan. Pinned hashes in evidence and parity records are re-minted or annotated once.
  - Promotion compares no stored hash (engine.py:2168-2174 only collects them).

#### Requirement text exceptions (to record in REQUIREMENTS.md)

- **WIRE-05:** the public violation entry carries `code` only; `pointer` and `message` are private (D-07).
- **WIRE-09:** the guards are dropped, not implemented (D-20).
- **WIRE-10:** "every node in the wiring" means the D-16-pruned run wiring (D-13).
- **WIRE-11:** `tier` and `feed_tier` are null; overspend is reported in `spent`/`allowance`; the amended fields validate against the Databasise derived trace schema, not the frozen copy (D-12, D-14).
- **WIRE-12:** `wiring_instance_hash` is computed from the full resolved wiring before query injection (D-03).
- **WIRE-13:** `component` is the resolved capability `mutates_store` (D-15).
- **WIRE-17:** the reachable NoWritePath case is retry with a HippoRAG selector (D-11).

### Claude's Discretion
- Exact names for the new refusals, the namespace field and the reason-code constants.
- The derived schema's file layout.
- The plan split. Constraints:
  - D-09's KeyError guard lands with or before D-02.
  - D-12 lands before D-13 and D-14.
  - D-21's hash-shifting changes go in one plan.
  - The two grant-needing edits (D-03 LRAG-19, D-15 LRAG-03) sit behind owner checkpoints, so the rest of the phase is not blocked.

### Deferred Ideas (OUT OF SCOPE)
- **The CONTRACT §14.2 load-time read-namespace typecheck** (the machine checks a declared namespace against the resolved store at load). D-01 is matching-only; revisit with the GUI capability picker (GUI-04/05).
- **The HippoRAG empty-namespace pre-check** (Phase 12 D-15). No WIRE row requires it, and it changes what protected STOR-06 means. It needs an owner grant, either an EmptyNamespaceError expectation or a populate-first rewrite.
- **A refusal for a trace whose run was refused at the seam but whose record is clean** (the D-04 unbudgetable case). This is Phase 14 (LEDG-02).
- **Real-engine A/A calibration once cache_hit is null.** This is TOOL-12 (Phase 15).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| WIRE-01 | Each of the six candidates is resolvable by a production §18.4 selector; selectors.py docstring states the mapping | Section 1: `Part.reads_namespaces` + matching-only helper; prototype run resolved all six arms and the three pinned `reads_graph` mappings (`[VERIFIED: probe]`) |
| WIRE-02 | parse_wiring reports ghost `provides`/`evidence_position.node`; KG arms mint non-empty evidence; bypass null | Section 2: assemble `items`, four patch edits, validator check, single minting site engine.py:2068-2078 |
| WIRE-03 | `stop_reason`/`degradation_reason` node-free on envelope and non-debug trace; response-time gate | Section 4/6: construction site scheduler.py:635-640, closed set in trace.py, scoped gate in redact.py, `resolve_trace` mapping |
| WIRE-04 | `depth_label` null when no provides node answered; `Depth` literal | Section 4: `_select_answer` engine.py:986-1019, envelope field, test_seam_tracer coupling |
| WIRE-05 | Pre-dispatch refusals are named 422s; strict ints; cycles on all four paths | Section 4: `_refuse_unparseable`, preflight translation, strict int sites scheduler.py:366/385, catalogue coupling |
| WIRE-06 | parse_wiring never raises; cycles deduped; RFC 6901 pointers; kind mismatch; message cleanup | Section 8: parse.py sites, blast_radius pointer also unescaped |
| WIRE-07 | One placement source; dead items removed | Section 8: depth.py:68 duplicate, `_REQUIRES_CONTAINMENT`, execution_mode.py stale text |
| WIRE-08 | Guards read a declared `signal`; ancestor check; GuardDeclarationError | Section 7: guards.py, fact_filter/assemble_result, base.json guard entries, protected test constraint |
| WIRE-09 | LightRAG fall-through guards dropped from wirings and docs | Section 7: patch `guards` arrays, README, CODEBASE-MAP |
| WIRE-10 | One NodeTrace per node with status; measured failure wall time; post-dispatch exceptions guarded | Section 5: scheduler restructure |
| WIRE-11 | NodeTrace fields report what was measured | Section 5 + derived schema (Section 3) |
| WIRE-12 | Per-arm `wiring_id`, pre-injection hash, truthful concurrency, trace_token on post-dispatch refusals | Sections 3/4/5 |
| WIRE-13 | SeamEvent component/outcome correct | Section 7 |
| WIRE-14 | Engine internals fail by name; `debug` kw removed | Section 2/4: only the `items` guard and `debug` legs fail at HEAD |
| WIRE-15 | environment_hash inputs documented; /health reports digest failure | Section 7 |
| WIRE-16 | Registry validates effects; query.py docstring | Section 1 |
| WIRE-17 | Reachability tests; compare one-selector mutates_store refusal | Section 4 |
| WIRE-18 | No unused scheduling/budget API; echo settings | Sections 5/7 |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

`[VERIFIED: .claude/CLAUDE.md as injected in the session context]`
- GSD workflow: no direct repo edits outside a GSD command; `/gsd-execute-phase` for planned work.
- Constraint "Compatibility": the §18 seam stays modality-agnostic; swapping the fitted modality changes no field a consumer sees (this is the motive for D-03 `arm_id`/`wiring_id` being debug-only, D-15 `component = mutates_store`, D-05 node-free reasons).
- Constraint "Runtime": local NixOS, embeddable in-process, no external DB servers, no Docker. Language: Python (ruff, target py310; venv runs 3.12.13).
- Conventions: async-first; guard checks run before lazy factory invocation; module docstrings explain why; tests are one behaviour per test.
- CONTEXT phase rules `[CITED: 13-CONTEXT.md code_context]`: commits carry a `phase/13` trailer; `.planning/` changes are separate from code commits; interpreter is `databasise/.venv/bin/python`; executors run no ledger command.
- Memory notes that bind this phase: never read `.env*` or `v1/parity-env.txt`; never run `pytest -m live`; protected tests are edited only with the owner's `grant-check-edit`.

## Summary

Phase 13 is internal to the seam, runner, validator and wiring files. It adds no external package. Four mechanisms carry most of the risk: (1) a Part-level read-namespace token so hybrid, local and global become distinguishable without touching the frozen 17-member `Effect` literal; (2) a scheduler rewrite that dispatches one node at a time and returns one `NodeTrace` per pruned node with a status; (3) a derived trace schema, because the frozen schema (`additionalProperties: false`, boolean `cache_hit`, `T0..T3` tier enum) rejects every new field; (4) a batch of identity changes (per-arm `wiring_id`, pre-injection hash, environment inputs, deleted config strings, guard `signal` key) that must land together.

All numbered decisions are implementable as written. Verified blockers and corrections the planner needs: (a) the derived schema cannot be built with `allOf`/`$ref` over the frozen file, because `additionalProperties: false` in the frozen `NodeTrace` cannot be loosened by intersection; it must be a patched copy, kept honest by a drift test; (b) the two protected edits are exact and small (Section 10); (c) `check_edit_grants` in the ledger already grants edits to eight files (including `test_refusal_status_codes.py`), and `check_guard`/`check_locks` are empty, so the protected set is exactly the `test_ref` files `[VERIFIED: ledger/REQUIREMENTS.json:2388-2424 and the hook source]`; (d) with sequential dispatch the `cancelled` status is only reachable when a node body itself raises `CancelledError` while the run is not being cancelled; the WIRE-10 requirement text ("a slow sibling runs") no longer describes reality and the test must be rewritten around `not-scheduled`; (e) three WIRE-14 legs and one WIRE-05 leg already pass at HEAD, so the fail-first proof must come from the other legs (Section 9).

**Primary recommendation:** Execute in five waves with one owner per hot file per wave: W1 validator / parts+selectors / run-record model+derived schema; W2 scheduler / engine-A; W3 wiring+evidence / engine-B; W4 the single hash-shift plan (behind the LRAG-19 grant); W5 seam events (behind the LRAG-03 grant) and phase closeout. Details in Section 11.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Arm selection by capability token | Seam (`seam/selectors.py`) | Parts registry (declares tokens) | Selector matches over `all_wirings()`; tokens belong on the part, not the wiring (wiring is untrusted author input, CR-01) |
| Wiring validation (ghost refs, kind, cycles) | Validator (`validator/parse.py`) | Seam `_refuse_unparseable` | Validator accumulates; engine converts a non-ok report to one 422 before any store opens |
| Pre-flight refusals (ints, guards, env digest) | Runner (`scheduler.py`) detects | Seam engine translates to `refusals.py` classes | SEAM-14 forces every `SeamRefusalError` subclass into `refusals.py`; runner classes stay runner classes |
| Per-node execution record | Runner (`scheduler.py`, `trace.py`) | Evidence (derived schema) | Runner owns truth about dispatch; schema is the contract for the record |
| Consumer vocabulary (reason codes, depth_label) | Seam (`engine.py`, `redact.py`, `envelope.py`) | Runner (`trace.py` holds the closed set) | §18.2 closed envelope; node detail stays in the debug trace |
| Run identity (`wiring_id`, `arm_id`, hash) | Wirings (`resolve.py`) | Seam engine (hash timing) | Identity is a property of the resolved wiring, hashed before per-query injection |
| Evidence minting | Seam engine (single site) | LightRAG `assemble` part (emits `items`) | Wiring declares position; the part must emit what the position expects |
| Environment identity | Identity (`identity/env.py`) | Seam `health()` | Digest is computed per process; health reports failure |

## Standard Stack

No new package is added by this phase. `[VERIFIED: probe]` versions in `databasise/.venv` (Python 3.12.13).

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest / pytest-asyncio | 9.1.1 / 1.4.0 | Tests; `asyncio_mode = "auto"`, `addopts = '-m "not live"'` `[VERIFIED: databasise/pyproject.toml tool.pytest.ini_options]` | Existing harness |
| pydantic | 2.13.5 | `ResponseEnvelope` (`_StrictModel`, extra forbid) | Existing |
| jsonpatch | 1.33 | RFC 6902 arm patches; also usable in the schema drift test (`make_patch`) | Already a declared dependency (`pyproject.toml:36`) |
| jsonschema | 4.26.0 | `Draft7Validator` in `tests/conftest.py` | Existing; declared `jsonschema>=4.0` (`pyproject.toml:64`) |
| graphlib / asyncio (stdlib) | 3.12 | `TopologicalSorter` readiness; `Task.cancelling()` exists (3.11+) `[VERIFIED: probe]` | Existing |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Patched-copy derived schema | `allOf`/`$ref` over the frozen file | Impossible: frozen `NodeTrace` has `additionalProperties: false`, `cache_hit` boolean, `tier` enum, `realised_budget_share` max 1 `[VERIFIED: docs/system-model/rig-trace.schema.json:49-107]`; intersection cannot loosen them |
| `jsonpointer.escape` for RFC 6901 | two `str.replace` calls | `jsonpointer` is only a transitive dependency (via jsonpatch); two replaces (`~` then `/`) are exact and keep the validator free of a transitive import |

**Installation:** none.

## Package Legitimacy Audit

No external package is installed or added by this phase, so the audit table is empty. `jsonpatch` and `jsonschema` already ship in the project's dependency list. **Packages removed due to [SLOP] verdict:** none. **Packages flagged [SUS]:** none.

## Architecture Patterns

### System Architecture Diagram (query path after Phase 13)

```
caller (REST / MCP / in-process)
   |  QueryObject, Selector
   v
check_consumable ------------------------------> UnconsumableQueryMemberError (422)
   |
resolve_selector -- capability tokens: effects UNION part.reads_namespaces (matching-only) --> arm (resolved dict)
   |                 resolve_arm stamps wiring_id = lightrag-<arm> (naive: lightrag-base) and arm id
   |   hash(full resolved)  <== computed HERE, before injection (D-03)
   v
inject query / token allowance / max_total_tokens ; prune recipe-only + non-ancestors of provides  -> run_resolved
   |
parse_wiring(run_resolved): ghost provides/evidence, kind mismatch, cycles, malformed doc (reports, never raises)
   |-- not ok / cycles --> UnparseableWiringError (422, codes only)
   v
runner pre-flight (strict ints, guard declarations + ancestor check, env digest)
   |-- error --> translated seam refusal (422, node id private)
   v
_build_stores -> _refuse_empty_namespaces -> run_wiring
   |        sequential: one node at a time per ready batch
   |        per node: completed | failed | cancelled ; unreached nodes: not-scheduled
   |        every dispatch step after the body is guarded -> failure recorded against that node
   v
RunRecord (all pruned nodes, closed reason codes, spent/allowance, execution_mode, null tier/cache_hit)
   |-- trace_store.persist  <== BEFORE any post-dispatch refusal (D-04)
   v
post-dispatch: store-fault check -> _select_answer (one answering node, else refusal) -> evidence from
   evidence_position.node 'items' (missing key -> MalformedEvidenceItemError) -> token breakdown (Unbudgetable)
   |-- refusal gets public .trace_token
   v
ResponseEnvelope (depth_label = answering node depth | None; reasons mapped through the closed set)
```

### Recommended Project Structure (new or changed files)
```
databasise/
├── parts/schema.py, registry.py          # Part.reads_namespaces; effect validation in register
├── parts_core/lightrag/{entity_lookup,relation_lookup,chunk_vector,chunk_sel_kg,assemble}.py
├── seam/{selectors,engine,refusals,redact,envelope,promotion,query}.py
├── runner/{scheduler,trace,guards,budget}.py
├── validator/{parse,errors,depth,execution_mode,blast_radius}.py
├── wirings/{resolve.py, lightrag/*.json(-patch), hipporag/base.json}
├── identity/env.py
├── evidence/rig-trace.databasise.schema.json, RIG-TRACE-DEVIATIONS.md   (new)
└── tests/ (18 new files named in REQUIREMENTS.md, plus updates listed in Section 9)
```

### Pattern 1: matching-only namespace tokens (D-01)
**What:** a `Part` field of full capability tokens; a helper beside `_wiring_effects` that unions them; `_match_capability` tests `requested <= (effects | tokens)`.
**Why this shape:** `Part.effects` is validated against the 17-member literal by the WIRE-16 registration check, so tokens cannot live there. Instance identity is `(name@version, config_hash, resolved_dependency_ids)`, so a new Part field does not shift any hash `[VERIFIED: runner/scheduler.py:345-350]`.
```python
# Source: prototype run this session (scratchpad probe2.py), declared tokens per part:
#   lightrag/entity-lookup@0.1.0          -> ("reads_vector:entities",)
#   lightrag/relation-lookup@0.1.0        -> ("reads_vector:relationships",)
#   lightrag/retriever-chunk-topk@0.1.0   -> ("reads_vector:chunks",)
#   lightrag/chunk-selector-kg@0.1.0      -> ("reads_vector:chunks",)
def _wiring_read_namespaces(resolved, registry) -> set[str]:
    tokens: set[str] = set()
    for node in resolved.get("nodes", {}).values():
        tokens.update(registry.get(node["component"]).reads_namespaces)
    return tokens
# in _match_capability:  requested <= (_wiring_effects(pruned, registry) | _wiring_read_namespaces(pruned, registry))
```
Prototype results (same fewest-full-nodes tie-break): `[reads_vector]`->naive, `[calls_llm]`->bypass, `[reads_vector:entities]`->local, `[reads_vector:relationships]`->global, both->hybrid, `[reads_graph,reads_kv]`->hipporag, `[reads_graph]`->hipporag, `[reads_graph,calls_llm]`->hipporag, `[reads_graph,calls_rerank]`->local, `[writes_graph]`->no match `[VERIFIED: probe]`.

### Pattern 2: sequential dispatch with a trace per pruned node (D-13/D-17)
```python
# Skeleton for scheduler.run_wiring after pre-flight (names illustrative)
traces: list[NodeTrace] = []; stop = False
while ts.is_active() and not stop:
    for node_id in sorted(ts.get_ready()):           # same sort as today
        outcome = await _dispatch_one(node_id, ...)  # never raises; returns trace + results/exception
        traces.append(outcome.trace)
        if outcome.stops_run: stop = True; break     # failed, cancelled, or budget halt
        ts.done(node_id)
for node_id in sorted(set(parsed.nodes) - {t.node_id for t in traces}):
    traces.append(_not_scheduled_trace(node_id, ...))   # status "not-scheduled", execution_mode stamped
```
`_dispatch_one` wraps three phases in try/except: body dispatch (measure elapsed from `_run_node`'s start), then `_body_report`/`meter`/`evaluate_guards`/`NodeTrace(...)`. An exception in either records `status="failed"`, `node_exceptions[node_id]`, a zero `TokenAccounting()`, and the measured wall time. `asyncio.CancelledError` raised by the body while `asyncio.current_task().cancelling() == 0` is a node-level cancellation (`status="cancelled"`, reason `cancelled`); otherwise re-raise `[VERIFIED: probe: Task.cancelling exists]`.

### Anti-Patterns to Avoid
- **Putting namespace tokens in `Part.effects` or `WiringNode.effects`:** refused by the WIRE-16 check and by `CODE_UNKNOWN_EFFECT`.
- **Editing `_wiring_effects` to include tokens:** `promotion.declared_surface` and the compare `mutates_store` check would change meaning.
- **Hashing the pruned `run_resolved`:** protected LRAG-19 requires the full resolved wiring (test docstring: "derived from the full resolved wiring") `[VERIFIED: tests/seam/test_query_trace_nodes.py:1-5]`.
- **Substring-scanning the whole envelope in the response-time gate:** an answer containing `generate`, `qa` or `keywords` would fail (redact.py design, CR-04) `[VERIFIED: seam/redact.py:15-30]`.
- **Raising a bare `TypeError`/`RuntimeError` from a new pre-dispatch check:** WIRE-05 exists to remove those.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Schema-amendment drift check | A hand-written field-by-field comparer | `jsonpatch.make_patch(frozen, derived)` and assert the set of patch paths equals the declared amendment paths | Catches any unrecorded divergence and any edit of the frozen file's content carried into the copy |
| Trace validation | Custom checks | `jsonschema.Draft7Validator` on the derived schema (already in conftest) | Same engine as today |
| Arm patch edits | Python string surgery on JSON | RFC 6902 `replace` ops in the existing patch files (`resolve_arm` applies them with `jsonpatch`) | Missing-target errors stay fail-closed (resolve.py docstring) |
| Readiness bookkeeping | New topological code | `graphlib.TopologicalSorter` already in `run_wiring` | Only the dispatch loop changes |
| Refusal body export | A new serializer for `trace_token` | Set a public attribute; `refusal_body` exports every public `vars()` entry `[VERIFIED: seam/refusals.py:47-61]` | One mechanism for REST and MCP |

**Key insight:** the phase is mostly deletions and tightenings of existing mechanisms. The only new machinery is the namespace token matcher, the derived schema file and the per-node dispatch helper.

## Runtime State Inventory

Rename-like changes in this phase: `wiring_id` values (D-03), reason-code vocabulary (D-05), `SeamEvent.component` (D-15), `environment_hash` inputs (D-16).

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `trace.db` (durable, `seam/trace_store.py` persists `json.dumps(run_record)`) holds pre-Phase-13 records with free-text `stop_reason`, `wiring_id='lightrag-base'`, `arm_id='seam'`, node lists without `status` `[VERIFIED: seam/trace_store.py:80-101]`. `ledger.db` stores `arm_instance_hashes` per promotion but never compares them `[CITED: p13-research.txt]`. | Code edit: `resolve_trace` maps unknown reasons to `node_failed`; `promotion._dispatched_node_ids` reads `node.get("status", "completed")`. No data migration. |
| Live service config | None found. No external service stores these strings. | None |
| OS-registered state | None found. | None |
| Secrets / env vars | None. Do not read `.env*` or `v1/parity-env.txt`. | None |
| Build artifacts | Archived evidence `databasise/evidence/parity_results/*-comparison.json` embed `wiring_id`/instance hashes (hash counts: naive 16, bypass 4, hybrid 36, local 32, global 32) `[VERIFIED: grep count]`; `evidence/HIPPORAG-PORT-RECORD.md` mentions `config_hash` (3). No test pins their values (`test_parity_evidence.py` uses synthetic records). | Annotate (do not re-mint: re-minting needs live provider spend) in the hash-shift plan; one note in `evidence/PARITY-EVIDENCE.md`. |

## Common Pitfalls

### Pitfall 1: a validator `provides`/`evidence_position` check landing before the wiring edits
**What goes wrong:** bypass, hybrid, local, global all inherit `evidence_position {node: chunk-vector}` and four of them remove that node `[VERIFIED: probe: all six arms report ok today; bypass/hybrid/local/global declare chunk-vector]`. The check turns every query into `UnparseableWiringError`.
**How to avoid:** the validator check, the four patch edits and the `assemble` `items` change are one plan.

### Pitfall 2: the evidence node is pruned out of the run wiring
The query path parses `run_resolved` (pruned to ancestors of `provides`). `evidence_position.node` must be an ancestor of `provides`; `assemble` is a dep of `generate`, `assemble-result` is a dep of `qa`. A test fixture wiring whose evidence node is not an ancestor will start failing at parse (unprotected fixtures only; run the suite).

### Pitfall 3: `declare_guard` signature
Protected `test_dpr_fallback_guard.py:316-322` calls `declare_guard(name=..., evaluating_node=..., value_when_not_fired=..., granularity="")` with exactly four keywords and expects `GuardDeclarationError`. `signal` therefore needs a default (`None`) and is validated after granularity; a required positional parameter would raise `TypeError` first `[VERIFIED: tests/parts_core/hipporag/test_dpr_fallback_guard.py:311-322]`.

### Pitfall 4: `test_selectors_source_has_no_stale_phrase` scans the whole source
It checks `'registry is empty'`, `'five arms'`, `'five Phase 3 arms'`, `'_ARM_NAMES'` in the entire `selectors.py` source, not only the docstring, and requires `'all_wirings()'` in the module docstring `[VERIFIED: tests/seam/test_seam_doc_consistency.py:163-171]`. The same file requires `'test-time gate'` in the `redact.py` docstring (line 149-150), `'unreachable'` in `MutableStoreComparisonExcludedError`'s docstring (line 83), and that `assert_no_forbidden_values({'component': 'node-x'}, {'node-x'})` still raises under `python -O` (lines 128-135).

### Pitfall 5: `_wiring_effects` consumers
`promotion.declared_surface` and `compare()` (engine.py:1186-1190) call `_wiring_effects`; leave it unchanged.

### Pitfall 6: failed-node `budget_state`
Today a failed node is stamped `budget_state="halted"` (scheduler.py:624) and `RunRecord.__post_init__` refuses a halted node on a non-partial run (trace.py). Keep `halted` for failed nodes (unchanged, now disambiguated by `status`) and use `within_budget` for `cancelled`/`not-scheduled`; the frozen enum has only `within_budget`, `halted`, `degraded` `[VERIFIED: rig-trace.schema.json:69-73]`. See Open Question 3.

### Pitfall 7: `assert_valid_trace` flip timing
Once `NodeTrace.to_dict()` emits `status`/`execution_mode`/`spent`/`allowance`, any real-record validation against the frozen schema fails. The conftest flip to the derived schema must be in the same plan that adds the fields (13-03), including for protected `tests/parity/test_naive_arm_end_to_end.py`, which calls `assert_valid_trace` on real records (behaviour change by fixture only, file untouched).

### Pitfall 8: sequential dispatch changes test text, not just timing
Unprotected `tests/runner/test_scheduler.py::test_8` stays green (sorted order puts `fail` before `slow`, so `slow` never starts) `[VERIFIED: tests/runner/test_scheduler.py:285-314]`. The WIRE-10 requirement test ("a slow sibling runs") cannot be written as stated; see Section 5.

### Pitfall 9: `WiringRefusedError` / `GuardDeclarationError` are ValueError subclasses
They are not `SeamRefusalError`s; nothing in the seam maps them today (500 on REST). Translate at the four `run_wiring` call sites: `_run_corpus_ingest` (engine.py:1408), `_mirror_v1_index_only` (1505), `delete_document` (1670), `_execute_resolved` (1998).

### Pitfall 10: Bash hook false positives while researching or executing
`2>/dev/null`, glob tokens that resolve into protected test directories, the word `debug`, and any command naming `ledger/` are blocked by the BAK hooks (pattern in `check-edit-guard.py`: any token resolving under a protected `test_ref` path counts). Use `2>&1`, `deb[u]g`, and the Read tool for protected tests and the ledger.

## Code Examples

### Derived-schema drift test (D-12)
```python
# Source: designed from jsonpatch 1.33 API; allowed amendment paths come from the deviation record
import json, jsonpatch
frozen = json.loads(FROZEN_PATH.read_text()); derived = json.loads(DERIVED_PATH.read_text())
ops = jsonpatch.make_patch(frozen, derived).patch
assert {op["path"] for op in ops} == EXPECTED_AMENDMENT_PATHS   # listed once, mirrored in RIG-TRACE-DEVIATIONS.md
```
Amendments to apply to the copy (all additive or nullable): NodeTrace `cache_hit` `type: ["boolean","null"]`; `tier`/`feed_tier` `type: ["string","null"]` with `null` added to the enum; new required properties `status` (enum `completed`, `failed`, `cancelled`, `not-scheduled`), `execution_mode` (enum from `derive_execution_mode`'s docstring: `in-process`, `subprocess`, `confined-unit`, `long-lived-service` `[VERIFIED: validator/execution_mode.py:58-62]`), `spent` and `allowance` (`type: ["integer","null"]`, `minimum: 0`); run-level `stop_reason` and `degradation_reason` gain an `enum` of the six D-05 codes plus `null`. `realised_budget_share` stays `maximum: 1`. The frozen run-level `status` property (a string project marker) is unrelated to the node-level `status`.

### Strict integer check (D-07)
```python
# scheduler.py:366 / :385 replacement shape
if not (isinstance(raw, int) and not isinstance(raw, bool)):
    raise InvalidMaxConcurrencyError(node_id, raw)
```
Probe at HEAD: `max_concurrency=True` is accepted (returns 1), `0.9` is refused only because `int(0.9)==0 < 1`, `2.7` is accepted as 2, `'100'` is accepted; `token_allowance=0.9` becomes 0 and `'100'` becomes 100 `[VERIFIED: probe]`.

### Cycle dedupe (D-08)
Today nodes `a(deps [a,b])`, `b(deps [a])` give `cycles == [['a','b'], ['a']]` `[VERIFIED: probe]`. Add the one-member self-loop entry only when the node is not already in a multi-member SCC.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Free-text `stop_reason` with node ids | Closed six-code vocabulary | this phase | `test_query_store_fault.py:69` asserts `"RuntimeError" in text` and must be rewritten |
| `TaskGroup` per ready batch | Sequential awaits | this phase | `concurrency_setting="sequential"` becomes true |
| Frozen trace schema validates every record | Derived schema validates Databasise records | this phase | `rig_trace_schema` fixture stays frozen |

**Deprecated/outdated claims found:** WIRE-05's "ingest/delete hit KeyError on scheduled['results']" is stale since feadf3e `[CITED: p13-research.txt]`; WIRE-13's "ingest() passes no recorder" is stale since LRAG-03 (engine.py:1365-1368, 1415 `[VERIFIED: seam/engine.py:1363-1416]`); WIRE-17's DELETE/`writes_graph` case is stale (D-11).

## Section 1: Selectors, Part field and identity (questions 1 and 3)

### 1.1 D-01 `reads_namespaces` (question 1)
- **Field:** add `reads_namespaces: tuple[str, ...] = ()` as the LAST field of the `Part` dataclass (`parts/schema.py:115-141`, currently ends with `admission: "AdmissionRecord | None" = None`). A trailing default keeps every keyword and positional construction site valid.
- **Content:** full capability tokens (`"reads_vector:entities"`), not bare namespaces, so the matcher needs no parsing. In `PartRegistry.register` validate each token as `<effect>:<namespace>` with the effect one of `reads_kv`/`reads_vector`/`reads_graph` AND present in `part.effects`, and the namespace matching `[A-Za-z0-9-]+` (the same rule as `validate_evidence_namespace`, `seam/evidence.py`).
- **Which parts declare what** `[VERIFIED: parts_core/lightrag entity_lookup.py:29,41,55 / relation_lookup.py:28,40,51 / chunk_vector.py:23,40,55 / chunk_sel_kg.py:52,177,210]`: `entity-lookup` (`_ENTITIES_NAMESPACE = "entities"`, `effects=["reads_vector"]`), `relation-lookup` (`_RELATIONSHIPS_NAMESPACE = "relationships"`), `retriever-chunk-topk` (`_CHUNKS_NAMESPACE = "chunks"`), `chunk-selector-kg` (`effects=["reads_kv", "reads_vector"]`, selects `chunks` at line 177). HippoRAG parts declare none (HippoRAG resolves by the unchanged effect-only mappings).
- **Why this is enough:** local = {entities, chunks}, global = {relationships, chunks}, hybrid = {entities, relationships, chunks}, naive = {chunks}; the existing fewest-full-nodes tie-break (naive 7, local 15, global 15, hybrid 17, hipporag 14 `[VERIFIED: probe]`) then picks local for `{entities}`, global for `{relationships}`, hybrid for both.
- **`_match_capability` consumption:** `_match_capability(requested, candidates, *, registry)` keeps its signature (unit tests pass a hand-built candidate list); add the helper next to `_wiring_effects` (selectors.py:147-154) and OR its result into the superset test at selectors.py:165. Matching still runs over `without_recipe_only_nodes(candidate[1])`.
- **Identity shift:** none. `_resolve_identities` hashes `part.name_at_version`, `config_hash(node.config, env=env)` and dependency instance hashes only `[VERIFIED: runner/scheduler.py:345-350]`. Do not bump any part version.
- **Selector input validation:** `Selector.capability` accepts any string; only `_INSTANCE_HASH_PATTERN` is refused (`seam/selectors.py:98,121-135`), and `compare` joins capabilities with `+` (`seam/compare.py:40,60-76`), so `:` tokens need no schema change.
- **Docstring:** rewrite selectors.py lines 4-14 (the "sufficient to distinguish the candidate wirings" claim is false) and list each mapping plus the one-node margin. Keep `all_wirings()` in the docstring and keep the four stale phrases out of the whole source (Pitfall 4).
- **Fail-first:** hybrid and global are unreachable at HEAD (WIRE-01 test fails at HEAD).

### 1.2 D-03 `resolve_arm` and identity (question 3)
- **`resolve_arm`** (`wirings/resolve.py:100-110`) applies the RFC 6902 `operations` to `load_base()` and returns the dict. After `jsonpatch.apply_patch`, set `resolved["wiring_id"] = f"lightrag-{arm_name}"` for every arm except `naive`, which keeps `lightrag-base`. Also stamp the candidate arm name on the dict (recommended top-level key `arm_id`; the engine needs it for `RunRecord.arm_id`, and `all_wirings()` must stamp `"hipporag"` for the non-LightRAG base) so alias, capability, harness and default branches all carry it. This is an addition to the full resolved dict and therefore part of the D-21 hash shift. Recommendation, see Open Question 7.
- **`wiring_family`** (resolve.py:69-80) matches `wiring_id == name or startswith(f"{name}-")`, so `lightrag-local` still returns `lightrag`. Update its docstring, which says arm-patched wirings keep the base `wiring_id` "per resolve_arm" (resolve.py:69-73).
- **Readers of `wiring_id` / `arm_id`** (production) `[VERIFIED: grep this session]`:
  | Reader | Line | Effect |
  |---|---|---|
  | `seam/engine.py` | 2029 (`wiring_id = resolved.get("wiring_id") or ...`), 2038, 2040 (`arm_id="seam"`) | change `arm_id` to the stamped arm name; move the hash (below) |
  | `parity/run_arm.py` | 221, 227 (`arm_id=arm_name` already) | picks up per-arm `wiring_id` automatically |
  | `parity/run_comparison.py` | 377, 381 | same |
  | `parity/build_hipporag_index.py` | 243, 249 | unchanged (`hipporag-base`) |
  | `databasise/__init__.py` | 106, 112 (`arm_id="base"`) | unchanged |
  | `seam/redact.py` | 66 (`low_entropy = {run_record["wiring_id"], run_record["arm_id"]}`) | new ids join the equality set automatically |
  | `seam/promotion.py` | docstring 8-20 only | docstring becomes stale ("every LightRAG arm's own resolved wiring_id is the shared lightrag-base"); matching stays node-id-set based |
  | `_NON_DEBUG_TRACE_FIELDS` (engine.py:448-461) | excludes `wiring_id`, `arm_id`, `wiring_instance_hash` | new values stay debug-only |
- **Unprotected tests that read them:** `tests/seam/test_cross_modality_run.py:117,123` (`assert resolved.get("wiring_id") == "lightrag-base"`), `tests/seam/test_selectors.py:92` (builds `all_wiring_ids` from `resolve_arm`), `tests/seam/test_leak.py:358,372` (`forbidden = {"chunk-vector", "seam", "lightrag-base"}`, own list, stays valid). Protected: `test_query_trace_nodes.py` (Section 10).
- **Hash relocation:** in `_execute_resolved` (engine.py:1964-2103) the first three statements mutate `resolved` in place (`_inject_query`, `_inject_token_allowance`, `_inject_max_total_tokens`, lines 1979-1981) and the hash is taken at 2027-2028 from the mutated dict. Compute `wiring_bytes = canonicalise(resolved)` BEFORE line 1979 (deep copy is not needed because `canonicalise` returns bytes). The pruned copy (`run_resolved`, 1982) must not be hashed. `compare` passes each resolved wiring to exactly one `_execute_resolved` call (docstring 1969-1973), so the relocation is safe there.
- **Archived values:** `engine.py:2168-2174` (promote) only collects `wiring_instance_hash` into `arm_instance_hashes`; nothing compares stored hashes `[CITED: p13-research.txt]`.

## Section 2: Evidence and `assemble` (question 2)

- **`assemble` output today:** `{context, order_policy, template_kind, chunk_count}` `[VERIFIED: parts_core/lightrag/assemble.py:152-157]`. The truncated list is the local `chunks` built at lines 136-142 (items accepted until the token budget overflows). Emit `"items": [{"id": chunk.get("chunk_id") or chunk.get("id"), "score": chunk.get("score")} for chunk in chunks]`. Items hydrated by `chunk-sel-kg` carry both `id` and `chunk_id` equal to the chunk id (`_hydrate`, chunk_sel_kg.py:138-148), the same string that keys the `chunks` vector namespace, so `resolve_evidence` works with namespace `chunks` unchanged. KG items carry no `score` (None is valid for `EvidenceRef`).
- **Single minting site:** `mint_evidence_refs` is called only at engine.py:2076; `evidence_position` is read only at 2068-2070 `[VERIFIED: grep of seam, parity, eval, mcp, tools, evidence, launcher, runner]`.
- **Missing `items`:** `retrieval_items = retrieval_output["items"] if isinstance(retrieval_output, dict) else []` (engine.py:2074) sits outside the `try` at 2075-2078. Move the lookup inside the `try` and raise `MalformedEvidenceItemError(namespace=..., index=0, reason="carries no 'items' key")` (constructor takes `namespace`, `index`, `reason`: `seam/evidence.py:77-92`). The engine re-raises it as `ForeignEngineRefusalError(failure_class="MalformedDriverOutput")` (502), so an in-process test asserts on `refusal.cause`, not `pytest.raises(MalformedEvidenceItemError)` `[CITED: p13-research.txt]`. Land this in the plan BEFORE the wiring edits (Section 11, 13-05 before 13-06).
- **Patch edits** (each is one `replace` op in the existing patch file; paths verified in the patch files): `arm-hybrid`, `arm-local`, `arm-global`: `{"op":"replace","path":"/evidence_position","value":{"node":"assemble","namespace":"chunks"}}`; `arm-bypass`: `{"op":"replace","path":"/evidence_position","value":null}`. `arm-naive` unchanged. `base.json` keeps `{"node": "chunk-vector", "namespace": "chunks"}` `[VERIFIED: probe output of base top-level keys]`. HippoRAG already declares `{'node': 'assemble-result', 'namespace': 'hipporag-chunks'}`.
- **Validator check:** in `parse_wiring` add two codes (suggested `unknown-provides`, `unknown-evidence-node`; pointers `/provides/<i>` and `/evidence_position/node`) that run whenever `doc` has a mapping `nodes`, independent of other violations. `engine._execute_resolved` already parses the pruned `run_resolved`, and `selectors._is_default_eligible` parses the full wiring, so both paths are covered. Corpus wirings declare `provides` that name their own nodes and no `evidence_position` `[VERIFIED: probe of wirings/*/corpus-*.json]`; `_mirror_v1_index_only` builds `provides: [sync_id]` with the matching single node (engine.py:1492-1497), so it passes.
- **Callers:** none besides engine.py:2068-2078. Evidence for `bypass` is `[]` by declaration, with no error.
- **Test infrastructure:** KG-arm evidence needs a populated store. `v1/.venv/bin/python` exists in this checkout `[VERIFIED: ls]`, so `requires_v1` tests run here; reuse the `tests/parts_core/lightrag/test_kg_fidelity.py::_ingested_engine` pattern (real-driver ingest through `real_v1`, `_inject_pinned_keywords(resolve_arm("local"), ...)`, `engine._execute_resolved`) `[VERIFIED: test_kg_fidelity.py:93-123]`. `tests/parts_core/lightrag/test_v1_index_sync.py::mixed_v1_dir` is NOT a usable KG fixture for retrieval (its entity rows carry only `source_id`, no `entity_name`). A part-level test of `assemble` emitting `items` plus an engine-level test with a monkeypatched `run_wiring` result gives offline coverage if the v1 venv is absent.

## Section 3: Derived trace schema (question 5)

- **How `assert_valid_trace` loads the schema today:** `tests/conftest.py` fixture `rig_trace_schema` reads `docs/system-model/rig-trace.schema.json` (session scope) and `assert_valid_trace` builds `Draft7Validator(rig_trace_schema)`, sorts errors by path and raises `AssertionError` with path-qualified messages `[VERIFIED: tests/conftest.py:43-69]`. conftest.py is not a ledger `test_ref` and `check_guard` is empty, so editing it needs no grant (the CONTEXT note about imported helpers is policy, not hook-enforced) `[VERIFIED: ledger/REQUIREMENTS.json:2376,2388 and check-edit-guard.py protected_sets]`.
- **Construction:** ship `databasise/evidence/rig-trace.databasise.schema.json` as a patched copy of the frozen file (not `allOf`/`$ref`; see Alternatives). Add a session fixture `databasise_trace_schema`; switch `assert_valid_trace` to it; leave `rig_trace_schema` on the frozen file (its shape test, `tests/test_conftest_fixtures.py::test_rig_trace_schema_loads_expected_shape`, is unprotected and stays valid).
- **Callers of `assert_valid_trace`:** `tests/runner/test_run_record.py`, `tests/runner/test_live_metering.py`, `tests/test_tracer_end_to_end.py`, `tests/test_phase_success_criteria.py`, `tests/parity/test_naive_arm_end_to_end.py` (protected file, fixture-only behaviour change) `[CITED: p13-research.txt]`.
- **Record:** `databasise/evidence/RIG-TRACE-DEVIATIONS.md` uses the §R columns `| # | Clause | Defect | Repair direction | Forcing requirement | ANATOMY re-projection | Status |` with no empty cell and terminal Status `recorded, no amendment` (the frozen RIG.md is not amended) `[VERIFIED: docs/system-model/RIG.md:654-668]`. One row per amendment, `Clause` = §TR.1 field. Existing `tests/evidence/test_*_record.py` files are the pattern for a presence test.
- **`NodeTrace`/`RunRecord` changes** (`runner/trace.py`, the only production `NodeTrace(` sites are scheduler.py:616 and 680 `[VERIFIED: grep]`): add defaulted fields so keyword constructions in tests keep working: `status: str = "completed"`, `execution_mode: str | None = None`, `spent: int | None = None`, `allowance: int | None = None`; change `cache_hit: bool` to `bool | None`; `tier`/`feed_tier` default `None`; delete `TIER_PLACEHOLDER` (only referenced in trace.py:42,97,98 and a docstring mention in `seam/evidence.py:18`); extend `to_dict()`. Add the six reason-code constants plus a `REASON_CODES` frozenset beside the existing `STOP_REASON_DECLARED_FALLBACK = "declared_fallback"` and `DEGRADATION_REASON_FALLBACK_PATH = "fallback_path_taken"` `[VERIFIED: runner/trace.py:40-41]`. Update the module docstring (it still says tier/feed_tier carry a documented `T3` placeholder).
- **Recommendation:** land all of this in plan 13-03 (W1), including the conftest flip, so every later plan validates against the derived schema.

## Section 4: Engine, refusals, catalogue coupling (questions 4 and parts of 6)

### 4.1 `stop_reason` construction and the gate (D-05)
- **Single production construction site:** scheduler.py:635-640 builds `f"node {node_id!r}: {reason}"` where `reason` is `cause` (placement) or `f"NodeExecutionError: {type(exc.cause).__name__}"`; `"budget_halt"` is set at line 678; D-21 codes at 706-707. Replace with the constants: failure -> `node_failed`, placement refusal -> `placement_refused`, budget halt -> `budget_halt`, cancelled -> `cancelled`; `degradation_reason = stop_reason` for partial runs stays (line 709).
- **HEAD behaviour** `[VERIFIED: probe]`: `create_app(clients=None)` + `POST /query` with `capability ["reads_graph","reads_kv"]` on a fresh root returns 200, `partial True`, `stop_reason "node 'fact-score': NodeExecutionError: ClientNotWiredError"`, same in `degradation_reason`, same string in the non-debug trace, `depth_label 'stage'`; debug trace holds one node (`fact-score`, `wall_clock_ms 0`, `budget_state 'halted'`, `cache_hit False`, `tier 'T3'`), `wiring_id 'hipporag-base'`, `arm_id 'seam'`.
- **Consumers of the string:** copy/print only (`parity/run_arm.py:237`, `run_comparison.py:391`, `build_hipporag_index.py:259-267`, `run_cross_modality.py:283`) `[CITED: p13-research.txt]`; protected `test_ingest_abort.py:163` feeds `'budget_halt'`; protected `test_dpr_fallback_guard.py:277-280` requires no HippoRAG node id, `guard` or `@` in the two reasons `[VERIFIED: that file]`.
- **Gate design (recommended):** `redact.py` gains `reason_leaks_identity(reason, low_entropy) -> bool` (substring over the two reason fields only) and an `assert_reasons_node_free(obj, low_entropy)` that raises `AssertionError` explicitly (same `python -O`-safe style). The engine applies one function `_consumer_reason(value)`: `None` passes; a member of `REASON_CODES` passes; anything else (old stored text or a regression) becomes `node_failed` and logs once at error level when the substring check also hits. It is used on the envelope fields (engine.py:2092-2103) and in `resolve_trace` (engine.py:2128-2141) for the non-debug branch. Fail-closed-by-mapping avoids a response-time 500, which the phase goal forbids. Existing function signatures in redact.py stay unchanged. See Open Question 10.
- **Old tokens:** `resolve_trace(debug=False)` filters the stored dict by `_NON_DEBUG_TRACE_FIELDS` (engine.py:448-461); apply `_consumer_reason` to the two reason keys there. `debug=True` returns the record untouched.
- **Existing test to rewrite:** `tests/seam/test_query_store_fault.py:55-70` asserts `"RuntimeError" in text` for both reasons; it must assert `node_failed` and that the class name and secret are absent, with the class name still in the debug trace's `cross_process_failure_cause`.

### 4.2 `depth_label` (D-06)
- `_select_answer` (engine.py:986-1019) returns `(answer, depth_label)` with `depth_label = "stage"` default (line 1002) and the answering node's `effective_depth` when a node trace exists. Change the default to `None` and the type to `Depth | None`; keep the 2-tuple return because `tests/seam/test_seam_tracer.py:105-114` unpacks `answer, depth_label = _select_answer(...)` and expects `"stage"` for an answering node. `ResponseEnvelope.depth_label` is a required `str` today (envelope.py, `ResponseEnvelope` body) -> `Depth | None` with no default, importing `Depth` from `databasise.parts.schema` (`Depth = Literal["opaque", "evidence", "stage"]`, schema.py:51 `[VERIFIED]`). Tests that build envelopes by hand pass `depth_label="stage"` and keep working.
- At HEAD a partial run reports `'stage'` (probe above). The null keys on "no provides node returned a completion", not on `partial`.

### 4.3 Two answering provides nodes, `trace_token`, persist order (D-04)
- **Order today:** store-fault check (2020-2025) -> hash/ids (2027-2031) -> `RunRecord(...)` (2036-2050) -> `_select_answer` (2056; raises `RuntimeError` at 1008-1013) -> evidence (2074-2078) -> `assemble_token_breakdown` (2082) -> `_mach11_events` (2086) -> `persist` (2090). Move record construction and `persist` to immediately after `scheduled` is available (cycle already refused by D-07), wrap the rest in one `try/except SeamRefusalError as exc: exc.trace_token = trace_token; raise`. `MalformedEvidenceItemError` is not a `SeamRefusalError` but becomes `ForeignEngineRefusalError` via `_foreign_fault` inside the try, so it is covered.
- **New refusal:** suggested `AmbiguousAnswerPositionError` (Claude's discretion), no public attributes, 422, in `refusals.__all__`, a factory in `tests/seam/test_rest_transport.py::_REFUSAL_FACTORIES` (the dict starts around line 420 `[VERIFIED: that file lines 425-460]`). `tests/seam/test_seam_tracer.py:131-140` currently expects `pytest.raises(RuntimeError)` for two answering nodes and must change.
- **`trace_token` exposure:** `refusal_body` exports every non-underscore `vars(exc)` entry (refusals.py:47-61), so a plain attribute works on REST and MCP. The generic factory test (`test_rest_transport.py` around 544-565) compares only attributes present on the factory instance, so adding `trace_token` post-construction does not break it. Update the `ForeignEngineRefusalError` docstring sentence at refusals.py:788-789 ("Every other class keeps exactly ``operation`` and ``failure_class``").

### 4.4 Refusal catalogue and status coupling
- Protected `test_refusal_catalogue.py`: every `SeamRefusalError` subclass must be defined in `seam/refusals.py` and named in `__all__`; names compared as sets `[VERIFIED: that file lines 33-49]`.
- Protected `test_refusal_status_codes.py`: every name in `__all__` except `SeamRefusalError`, `ForeignEngineRefusalError`, `StoreBusyError` must be in `_REFUSAL_FACTORIES` and map to 422 (404 for four lookups) `[VERIFIED: that file lines 19-27, 91-96]`. This file is already in `check_edit_grants` (reason: StoreBusyError), so adding to `_MAPPED_ELSEWHERE` needs no new grant `[VERIFIED: ledger/REQUIREMENTS.json:2398-2401]`. Keep every new refusal at 422 to avoid even that edit.
- `rest._status_for`: 409 `StoreBusyError`, four 404 lookups, otherwise 422; `ForeignEngineRefusalError` 503 for `_ENGINE_UNAVAILABLE = frozenset({"MissingV1InterpreterError", "CorpusOpTimeoutError", "DriverUnavailable", "V1NotConfigured"})`, else 502 `[VERIFIED: seam/rest.py:131-143]`.
- MCP maps refusals generically through `refusal_body` (`tests/mcp/test_mcp_refusal_mapping.py`, protected, picks new refusals up without edit) `[CITED: p13-research.txt]`.

### 4.5 Pre-dispatch translation (D-07)
- **Cycles:** `_refuse_unparseable(parsed)` (engine.py:608-612) raises `UnparseableWiringError(violations=sorted({v.code ...}))`. Add the code `cyclic-wiring` when `parsed.report.cycles` is non-empty (define a `CODE_CYCLIC_WIRING` constant in validator/errors.py). It is called at engine.py:1301 (ingest), 1499 (`_mirror_v1_index_only`), 1564 (retry), 1648 (delete), 1984 (query). Replace the defensive `RuntimeError` at 2011-2015 with the same refusal. The ingest/delete cycle path that returns 502 `RunIncomplete` today (`_node_result_or_refuse`, engine.py:865-870) becomes unreachable except for direct `run_wiring` callers.
- **Runner pre-flight:** recommended shape: extract `preflight(parsed) -> (max_concurrencies, token_allowances, guards_by_node)` from `run_wiring` (scheduler.py:546-559) and call it from a new `engine._refuse_unrunnable(parsed)` placed next to every `_refuse_unparseable` call, so refusals are raised before any store opens or any upload is staged. Translation targets (names are discretion): `InvalidMaxConcurrencyError`/`InvalidTokenAllowanceError` -> `InvalidNodeSettingError(setting=...)` (422, node id private in `_node_id`); `GuardDeclarationError` -> `InvalidGuardDeclarationError()` (422); `EnvironmentDigestError` -> reuse `ForeignEngineRefusalError` with a new allow-listed `failure_class` (for example `EnvironmentDigestUnavailable`, keyed in `_FOREIGN_FAILURE_CLASSES` refusals.py:753-762, 502) or a 422 class; see Open Question 9. If the planner prefers not to touch the scheduler's structure, wrap the four `run_wiring` call sites in one `_run_wiring_or_refuse` helper that catches these runner classes; the run raises before any node dispatch in both designs. Ingest stages an upload before `run_wiring` (engine.py:1393-1407); a raised `SeamRefusalError` without a `failure_class` in `_KEEP_STAGED` removes the staged file (engine.py:1438-1446), so the wrapper design is also safe.
- **`UnparseableWiringError.violations`** stays `list[str]` of codes (refusals.py:874-885). D-07 says "keeps each violation's code only", which is satisfied by the current shape. Changing it to `[{code}]` would force a change to the unprotected factory and is not needed. Open Question 1.
- **WIRE-05 test constraints:** with the default selector a registry missing a part returns `UnsatisfiableSelectorError` before parse (selectors consult the registry), so violations tests must monkeypatch `databasise.seam.engine.resolve_selector` (imported name in engine.py) or `engine._corpus_wiring` to return a hand-built wiring `[CITED: p13-research.txt]`.

### 4.6 Other engine legs
- **`debug` keyword (D-09):** `query` (engine.py:1092-1104), `query_stream` (1106-1124) and `compare` (1126-1175) take `debug: bool = False` and `del debug`. Production callers pass `debug` only to `resolve_trace` (`seam/rest.py:206,423`, `mcp/server.py:171`, `mcp/tools.py:200`) `[VERIFIED: grep]`. No unprotected seam test passes `debug` to `query`/`query_stream`/`compare` `[VERIFIED: grep over the 25 unprotected seam test files]`. Protected tests could not be searched with Bash; run the suite after the removal and treat a failure in a protected file as a grant item, not an edit.
- **`delete_document` store namespaces and `resolve_evidence` graph avoidance:** already correct at HEAD: `_build_stores(self.store_root, self.workspace, resolved, into=stores, operation="delete")` (engine.py:1665) and `resolve_evidence` builds only `MultiNamespaceVectorStore` (2105-2126). They are satisfied by STOR-07/STOR-03 and need no fail-first fabrication.
- **`_build_stores` docstring** (engine.py:548-581) does not list `health` as a caller at HEAD `[VERIFIED: read]`; it names `ingest`, `delete_document` and `_execute_resolved` and omits `retry_document`/`_run_corpus_ingest`; correct that list.
- **HippoRAG ingest real exception:** `_node_result_or_refuse` (engine.py:849-894) already raises the first recorded node exception (`node_exceptions`) and treats `partial` without an exception as `RunIncomplete`; the synthesized "produced no result and no exception" message is reachable only when no exception, no `partial` and no result exist. Likely already satisfied by HIPP-04 (`test_an_ingest_with_no_embedding_client_names_chunk_embed_privately`); write the openie test, run it at HEAD, and if it passes record it as satisfied by the earlier commit. `[ASSUMED]` until that test runs.
- **WIRE-17 compare:** engine.py:1177-1190: `if len(selectors) == 1: return await self._execute(...)` precedes the `mutates_store` loop. Restructure: resolve every selector first, run the `_wiring_effects` `mutates_store` check for the one-selector case too, then `_execute_resolved`. Update the `compare` docstring and the refusal docstring ("one-selector ``compare()`` path never raise this" at refusals.py:487-491) while keeping the word `unreachable`.

## Section 5: Scheduler restructure (question 6)

**Construction sites** `[VERIFIED: runner/scheduler.py]`: pre-flight 546-559; identities 562; `ts.prepare()` 565; batch loop 581-700; `TaskGroup` 586-600; `except* NodeExecutionError` 601-603; failed-node trace 615-630 (`wall_clock_ms=0`, `cache_hit=False`, `budget_state="halted"`, `realised_budget_share=0.0`, `tokens=TokenAccounting()`); cancelled-sibling branch 650-657 (no trace); success trace 679-691; stale comments at 659-660 and 687 ("in-process only"); halt/failure break 694-700; return dict 710-718.

Design (D-13, D-14, D-17):
1. **One `NodeTrace` per pruned node.** `parsed.nodes` already is the pruned set (the engine parses `run_resolved`). After the loop, append `not-scheduled` traces for every node without one, sorted by node id after the dispatched ones. `_pending_node_trace` (scheduler.py:493-504) already builds the identity fields; add `execution_mode = derive_execution_mode(part.effects, part.kind)` (pure; `[VERIFIED: validator/execution_mode.py:58-75]`), `allowance = token_allowances[node_id]`, `spent=None` for unreached nodes. Identities are resolved for all nodes before dispatch (scheduler.py:562), so `instance_hash` is available for unscheduled nodes.
2. **Failure wall time.** `NodeExecutionError.__init__(node_id, cause)` (scheduler.py:232-235) gains an optional `wall_clock_ms`; `_run_node` computes it from its existing `start = time.monotonic()` (line 482) when dispatch raises (line 487-488). Placement refusals occur before `start` (line 446-448) and report 0. Use `math.ceil` or assert `>= 50` after a 60 ms sleep in the test to avoid sub-millisecond flooring.
3. **Guard the post-dispatch steps** (`_body_report`, `meter`, `evaluate_guards`, `NodeTrace(...)`, lines 672-691) in the same `try`; on exception record `status="failed"`, zero `TokenAccounting()`, `node_exceptions[node_id] = exc`, `stop_reason=node_failed`. This removes the escape of an `ExceptionGroup` for non-`NodeExecutionError` exceptions.
4. **Sequential dispatch:** replace the `TaskGroup` with `for node_id in sorted(ts.get_ready()): await ...`. `_run_node` is unchanged apart from the elapsed carrier. Intra-node concurrency (`ctx._semaphore`, scheduler.py:454,480) is unaffected.
5. **`cancelled`:** reachable when a body raises `asyncio.CancelledError` while `asyncio.current_task().cancelling() == 0`; otherwise re-raise so a real cancellation of the run propagates. A WIRE-10 test can use a body that raises `asyncio.CancelledError()` itself.
6. **Fields:** `status` in {`completed`, `failed`, `cancelled`, `not-scheduled`}; `cache_hit` = the part's own `bool` if present in a mapping output, else `None` (`_body_report`, lines 405-422, currently `bool(output.get("cache_hit"))`); `tier`/`feed_tier` None; `spent`/`allowance` ints from `BudgetToken` (`meter` returns `allowance` and `spent`, budget.py `BudgetToken`); `realised_budget_share` stays `realised_share(...)` capped at 1.0 (budget.py:110-118); `execution_mode` on every trace.
7. **Echo (D-17/WIRE-18):** add `"determinism_setting"` and `"concurrency_setting"` to the returned dict (710-718). Protected `test_capability_scoping_modes.py:71-80` passes both keywords and reads `result["node_exceptions"]`; keep both.
8. **Stale text:** rewrite the module docstring paragraph at scheduler.py:42-48 (says `validator.depth.derive_execution_mode` "is left untouched") and the comments at 659-660 and 687.
9. **`promotion._dispatched_node_ids`** (seam/promotion.py:111-114) -> `frozenset(node["node_id"] for node in record.get("nodes", []) if node.get("status", "completed") == "completed")`. Records persisted before Phase 13 have no `status`.
10. **Side effects to expect:** `assemble_token_breakdown` already counts failed nodes' zero accountings under `counted_by="none"` (tokens.py:49-72), so extra `none` entries add zeros to the same bucket; `_log_corpus_overrun` is unaffected; a budget-halted node still gets `status="completed"` with `budget_state="halted"` and the run breaks after it, so later nodes in that ready batch are now `not-scheduled` instead of having run concurrently.

**Tests that depend on within-batch concurrency:** none found among unprotected runner tests (`test_scheduler.py` concurrency tests measure intra-node `gather`, `test_5` checks dispatch order inside one batch, `test_8` passes by order). Protected HIPP-10 (`test_index_side_extraction.py::test_openie_counts_failed_chunks_refuses_and_overlaps_calls`) overlaps calls inside openie, unaffected `[CITED: p13-research.txt]`. The full gate will reveal any other.

**WIRE-10 test rewrite:** "batch-1 node fails while a slow sibling runs" becomes: nodes `a-fail` (sorts first, raises after `asyncio.sleep(0.06)`), `z-sibling` (same batch, `not-scheduled`), and two later batches (`not-scheduled`); assert the trace id set equals the wiring node set, statuses, `wall_clock_ms >= 50` on the failed node, `partial True`, `stop_reason == "node_failed"`. A separate test covers `cancelled` via a body raising `CancelledError`.

**`concurrency_setting` truth test (WIRE-12):** two dependency-free nodes whose bodies record in-flight count; assert the peak is 1 while the record says `sequential`. At HEAD the peak is 2 (TaskGroup), so it fails at HEAD.

## Section 6: Reason gate, tier and cache_hit side effects

- **Calibration:** `eval/calibration.py:217-235` refuses any node whose `cache_hit` is not exactly `False`; after D-14 real-engine A/A calibration raises `UnusableFloorError`, which is TOOL-12's intent. Record it in STATE (a one-line Blockers/Concerns entry) in the closeout plan. Stub-engine eval tests used by protected `test_lightrag_eval_store.py` are unaffected `[CITED: p13-research.txt]`.
- **Allow-list:** `_NON_DEBUG_TRACE_FIELDS` (engine.py:448-461) still excludes `nodes`, so every new NodeTrace field is debug-only.

## Section 7: Seam events, environment, guards, WIRE-09, WIRE-16/18 (questions 7 and parts of 6)

### 7.1 Seam events (D-15)
- `SeamEvent(component=part.name_at_version, spend=spend, outcome=outcome)` is the only production construction (engine.py:968); `outcome = "halted" if node_trace is not None and node_trace.budget_state == "halted" else "completed"` (967). New logic: `outcome = "failed"` when `node_trace.status != "completed"` (or `cross_process_failure_cause is not None`), `"halted"` when `status == "completed"` and `budget_state == "halted"`, else `"completed"`. `component` becomes the constant `"mutates_store"` (CONTEXT quote: "`SeamEvent.component` is the resolved capability (`mutates_store`)"). Update `envelope.py:64-69` docstring and the `SeamEventOutcome` comment (envelope.py:47-54).
- **Reach:** `_mach11_events` runs after a successful run; ingest and delete refuse before events are built (engine.py:1419-1424, 1683-1688), and a query store fault refuses before events. The 'failed' outcome can only be produced on the query path (injected candidate) or via a direct `_mach11_events(parsed, touches, node_by_id)` unit test; build `node_by_id` with a failed `NodeTrace` and a `parsed` whose part declares `mutates_store`.
- **Unprotected tests to update:** `tests/seam/test_mach11_event.py:375`, `tests/seam/test_compare.py:233-250` (forbidden set), `tests/seam/test_rest_transport.py:767-808` `[CITED: p13-research.txt]`. Docs: API-INVENTORY.md lines 669 and neighbours.

### 7.2 Environment (D-16)
- Current payload: `{"python_version": list(sys.version_info[:3]), "platform": platform.platform(), "distributions": dist_rows}` (identity/env.py:71-77); `environment_hash` is `functools.cache`d (80-83); the only runtime caller is `_resolve_identities` (scheduler.py:339); `config_hash` also defaults to it (identity/canon.py:100-107).
- New payload keys: `"system": platform.system()`, `"machine": platform.machine()`, `"libc": list(platform.libc_ver())`. On this host these return `Linux`, `x86_64`, `('glibc', '2.42')`, while `platform.platform()` is `Linux-6.18.56-x86_64-with-glibc2.42` `[VERIFIED: probe]`. Rewrite the module docstring to list every input (python version, system, machine, libc, per-distribution name/version/RECORD digest) and drop the claim list that omitted `platform`.
- **Health (engine.py:1880-1950):** compute the digest inside `asyncio.to_thread` (cold ~0.11 s, 55 distributions `[CITED: p13-research.txt]`); on `EnvironmentDigestError` append one fixed reason (for example `"environment digest unavailable"`) to `reasons`, and AND the result into `overall_ok`. No new `HealthReport` field: `HealthReport` is `extra="forbid"` with `status: Literal['ok','degraded']` `[CITED: p13-research.txt, seam/corpus.py:336-342]`, and protected `test_health_honesty.py:35,62` pins the three-key `engine` set and `test_health_probe.py` pins the stores keys, and `test_health_honesty.py:121,123,135` assert `engine_reason` equality, which keeps passing only because the digest computes in the test env.
- **Test for the failure branch:** this venv has no `/nix/store/` in any RECORD `[CITED: p13-research.txt]`, so monkeypatch `databasise.identity.env.distributions` with a fake distribution whose `read_text("RECORD")` contains `/nix/store/`, and call `environment_hash.cache_clear()` first and after.
- **Query paths:** `EnvironmentDigestError` is a `RuntimeError` (env.py:35-38) raised from `_resolve_identities`, so every query/ingest/delete would return an unstructured 500 today. Covered by the 4.5 translation.

### 7.3 Guards (D-19) and WIRE-09 (D-20)
- **Files:** `runner/guards.py` (`GuardDeclarationError(guard_name, granularity)`, `GuardDeclaration` dataclass, `declare_guard`, `evaluate_guards`); `scheduler._validated_guards` (393-402: `declare_guard(**entry)` -> bare `TypeError` on bad keys, reproduced `[VERIFIED: probe]`); call site scheduler.py:674 `evaluate_guards(guards_by_node[node_id], results)`.
- **Behaviour change:** `GuardDeclaration` gains `signal: str`; `declare_guard(name, evaluating_node, value_when_not_fired, granularity, signal=None)` raises `GuardDeclarationError` for a bad granularity first, then for `signal is None`/non-str. `GuardDeclarationError` gains optional keyword `node_id` (WIRE-08 text: "raises GuardDeclarationError with .node_id set"). `evaluate_guards` reads `results[evaluating_node][signal]`; a missing node or missing key raises (never fires). HEAD behaviour for reference: a plain dict output fires and a missing evaluating node fires `[VERIFIED: probe]`.
- **Pre-flight checks (on the pruned parsed wiring):** entry must be a mapping with exactly the five keys; `evaluating_node` must equal the guarded node or be in its transitive dependency closure (`parsed.deps`). Both shipped guards evaluate their own node (`fact-filter`, `assemble-result` `[VERIFIED: wirings/hipporag/base.json guards]`).
- **Parts:** `fact_filter.py` (`_GuardAwareResult` lines 64-86; returns at 117 and 137) and `assemble_result.py` (`_StandInResult` lines 48-52; returns at 81) become plain dicts; the bodies already emit `guard_fired` / `dpr_stand_in` booleans. `assemble_result.py` imports `_GuardAwareResult` from `fact_filter` (line 36) and reads `fact_filter_output.get("guard_fired", False)`, which stays valid.
- **Wiring edit:** add `"signal": "guard_fired"` to the `zero_surviving_facts_dpr_fallback` entry (`fact-filter` config) and `"signal": "dpr_stand_in"` to `empty_ppr_dpr_stand_in` (`assemble-result` config) in `wirings/hipporag/base.json`. This changes the hipporag `config_hash` (D-21). Protected `test_dpr_fallback_guard.py:301-308` reads only `name`, `evaluating_node`, `granularity` and `len(guards) == 1`; protected `test_registration.py:130-156` checks a fixed `_UNREAD_KEYS` list that does not include `signal`/`guards`.
- **Unprotected tests to update** `[CITED: p13-research.txt]`: `tests/runner/test_run_record.py:114-122,177-183` (four-argument `declare_guard`, scalar runtime values), `tests/runner/test_degraded_on_guard.py:34-41` (whole-output `value_when_not_fired {'ok': True}`).
- **WIRE-09:** remove the top-level `guards` arrays at `arm-local.json-patch.json` and `arm-global.json-patch.json` (lines 29-41 `[VERIFIED: patch files read in full]`), and the sentences "carries a declared guard" in `wirings/lightrag/README.md` table rows (the table at lines 123-130), `docs/gui/CODEBASE-MAP.md:332` (G-25), and record the retained frozen copies as a deviation. No file named "LightRAG port record" exists (`git ls-files` search); record the deviation in `wirings/lightrag/README.md`. The test scans `databasise/wirings/**/*.json` for a top-level `guards` key; node-level `config.guards` in hipporag is legitimate.

### 7.4 WIRE-16 and WIRE-18
- **WIRE-16:** in `PartRegistry.register` (parts/registry.py, the `register` method before the opaque check) raise a named `ValueError` subclass for any `effect` not in `typing.get_args(Effect)`. Existing unprotected tests that register `effects=['reads_space']` to demonstrate "a later phase flips consumable" must change (likely `tests/seam/test_query_object.py`); find them by running `tests/seam tests/parts`. Rewrite `seam/query.py` docstring lines 8-27 (the "by absence, not by permanent exclusion" paragraph and "A later phase that registers a part/store declaring the matching capability flips one of these four" at lines 24-27 `[VERIFIED: seam/query.py:8-27]`).
- **WIRE-18 deletions** (code): `runner/budget.py` `split_allowance`, `apportion`, `ApportionmentPolicy`, `Allowance`, `BudgetHalted` and `BudgetState`'s `"degraded"` member (budget.py:34-125); keep `meter`, `realised_share`, `BudgetToken`. Update `tests/runner/test_budget.py` (imports the deleted symbols; unprotected). JSON strings: `wirings/lightrag/base.json` (join-entities, join-relations, budget-entities, budget-relations, join-chunks), `arm-global`/`arm-local` join-chunks config, `arm-hybrid` join-chunks config; the `budget-*` nodes' `config` becomes empty after deleting both keys. Either spelling (drop `config`, or keep `{}`) hashes the same at node level, because the scheduler hashes `node.config or {}` `[VERIFIED: runner/scheduler.py:348 "c_hash = config_hash(node.config or {}, env=env)"]`; drop the key so the wiring file does not carry an empty object. (Inside one config dict an absent key still hashes differently from an explicit empty value: `tests/identity/test_config_hash.py:100` `test_7`.) `truncator_token_budget.py:25` docstring cites the deleted config text; update it. The frozen copies under `docs/system-model/wirings` and `databasise/evidence/wirings` stay.
- **Runner-surface test (`tests/runner/test_runner_surface.py`)** must not import deleted names; assert absence with `hasattr(module, name)` or an AST scan over `databasise/` excluding `tests/`, so it fails by assertion at HEAD.

## Section 8: Validator and placement (question: WIRE-06, WIRE-07 map)

- `parse_wiring` (validator/parse.py:145-272): `raw_nodes: dict = doc.get("nodes", {})` (147) is the AttributeError source for `[]`, `{'nodes': None}`, `{'nodes': [1]}` `[VERIFIED: probe]`. Guard `isinstance(doc, dict)` and `isinstance(nodes, dict)` first; report one violation (suggest `invalid-wiring-document` / reuse `empty-wiring`) and continue with an empty node map so a `ParsedWiring` is still returned.
- **RFC 6901:** unescaped pointers at parse.py:155 (`/nodes`, fine), 165 (`/nodes/{node_id}/{field_path}`), 195 (`/nodes/{node_id}/component`), 213, 228, 240 (`/nodes/{node_id}/deps/{dep_index}`), AND `validator/blast_radius.py` (`pointer=f"/nodes/{node_id}/effects"`), which the WIRE-06 text does not mention. Escape every dynamic token (`~` -> `~0` first, then `/` -> `~1`). `field_path` parts from pydantic `loc` also need escaping. HEAD gives `/nodes/x/y/component` for node id `x/y` `[VERIFIED: probe]`.
- **Message:** line 197 `message=str(exc)` stringifies `UnknownPartError`, whose message starts with a quote and embeds `registered parts: [...]` (registry.py `UnknownPartError`) `[VERIFIED: probe output]`. Use `f"component {node.component!r} is not a registered part"` (the wiring's own value, no registry content).
- **Kind mismatch:** compare `node.kind != part.kind` in the `else` branch of the registry lookup; new code (suggest `kind-mismatch`). Probe: no shipped wiring file (base, patches resolved, corpus-*, codebase-memory-mcp, hipporag) mismatches `[VERIFIED: probe]`.
- **Cycles:** dedupe as in Code Examples.
- **WIRE-07:** delete `derive_execution_mode` and `_REQUIRES_CONTAINMENT` from `validator/depth.py` (lines 30-50 and 68-82; keep `effective_depth` and `_DEPTH_RANK`). Imports of the depth copy: only `tests/parts/test_reference_parts.py:19` (lines 29 and 93 assert `"in-process"` and `"subprocess"`; the fixpoint expectation becomes `"long-lived-service"` from `execution_mode.py`) `[VERIFIED: grep]`; protected `test_registration.py:25` already imports from `validator.execution_mode` `[VERIFIED]`. Delete `WiringValidationError` (parse.py:88-95; no importer in `validator`, `parts_core`, `runner`, `tests/validator`, `tests/parts` `[VERIFIED: grep]`). Rewrite the `ParsedWiring` docstring (parse.py:98-108, "every collection here is a read-only view") to say only `nodes`/`parts`/`deps` are read-only views and `report` is mutable (parse_wiring extends `report.violations` after the snapshot). `blast_radius.py`: replace `getattr(part, "artifact_scope", None) or "shared"` with `part.artifact_scope or "shared"` and delete the module-docstring rationale paragraph. `execution_mode.py` stale text at the module docstring ("D-08: Phase 1 hosted ``in-process`` only"), the `UnimplementedPlacementError` docstring ("Phase 1 implements ``in-process`` hosting only (D-08)") and the `host()` message ("Phase 1's runner implements in-process hosting only (D-08)"); `parts_core/fixpoint_body.py:8-11` still says the depth copy derives `subprocess`. WIRE-07 placement decision (D-18) needs no behaviour change: `derive_execution_mode(['calls_llm'], 'stage')` is already `in-process` (execution_mode.py returns `in-process` unless `net`, `fs`, `self_storage`, `mutates_store`, kind `fixpoint` or `opaque`).

## Section 9: Per-WIRE-row fail-first table (question 8)

Every new test file is new and therefore unprotected today (none of the 18 names in REQUIREMENTS.md exists; none is a ledger `test_ref`). To fail by assertion and not by `ImportError`, a test must not import a symbol this phase adds: resolve it with `getattr(module, "Name", None)` and `assert ... is not None`, or catch the base class (`pytest.raises(ValueError)` then assert the type name).

| Row | Test file (new) | Fails at HEAD | Already passes at HEAD (needs `record-fail --at` older commit, or skip as satisfied) | Suggested test nodes / notes |
|---|---|---|---|---|
| WIRE-01 | `tests/seam/test_selector_reachability.py` | hybrid, global unreachable; docstring lacks mapping tokens | `{reads_graph}`, `{reads_graph,calls_llm}`, `{reads_graph,calls_rerank}` mappings (pin them) | `test_each_candidate_has_a_selector[hybrid|global|...]` (compare returned dict to `all_wirings()` entry; do not depend on wiring_id), `test_documented_reads_graph_mappings`, `test_docstring_states_every_mapping` |
| WIRE-02 | `tests/validator/test_top_level_refs.py`; `tests/seam/test_evidence_position.py` | ghost `provides`/`evidence_position.node` produce no violation; KG-arm evidence is `[]` | `parse_wiring(all_wirings()[name])` ok for every arm (passes at HEAD; keep green); bypass evidence `[]` | KG evidence via `real_v1` ingest + pinned keywords (Section 2) |
| WIRE-03 | `tests/seam/test_stop_reason_leak.py` | all legs: naive on `synthetic_naive_store` with `clients=None`, HippoRAG on a fresh root, `/trace/resolve` non-debug, legacy stored text mapping, monkeypatched leaky scheduler result | none | HippoRAG leg needs no store (empty-namespace pre-check deferred); LightRAG leg needs `synthetic_naive_store` |
| WIRE-04 | `tests/seam/test_depth_label.py` | partial run reports `'stage'`; `depth_label='bogus'` accepted | naive complete run `'stage'` | |
| WIRE-05 | `tests/seam/test_preflight_refusals.py` | cyclic query -> `RuntimeError` 500; cyclic ingest/delete -> 502 `RunIncomplete` not 422; `max_concurrency=True/2.7/'100'`, `token_allowance=0.9/'100'` accepted; runner pre-flight errors -> 500; bad guard entry -> `TypeError` | KeyError-on-`scheduled['results']` leg (stale since feadf3e); non-ok report -> 422 `UnparseableWiringError` (Phase 10 D-15) | monkeypatch `engine.resolve_selector`/`engine._corpus_wiring` for injected wirings; guard legs land in the hash-shift plan |
| WIRE-06 | `tests/validator/test_parse_report.py` | every leg (probe) | none | |
| WIRE-07 | `tests/validator/test_execution_mode_single_source.py` | `hasattr(depth, 'derive_execution_mode')`, `WiringValidationError` present, `'read-only'` docstring, `getattr(` in blast_radius source, `'Phase 1'` in `host()` message and `UnimplementedPlacementError.__doc__` | `derive_execution_mode(['calls_llm'],'stage')=='in-process'`; `ForeignEngineRefusalError` body free of `'Phase 1'` | `tests/parts/test_reference_parts.py` edit proves the fixpoint `long-lived-service` |
| WIRE-08 | `tests/runner/test_guard_evaluation.py` | plain-dict output fires; missing node fires; non-ancestor evaluating node accepted; bad keys `TypeError`; | HippoRAG fired/not-fired cases (protected HIPP-14 tests) | five-argument `declare_guard`; keep protected four-keyword call green |
| WIRE-09 | `tests/wirings/test_lightrag_guards.py` | two patch files carry top-level `guards`; README/CODEBASE-MAP text | none | scan `wirings/**/*.json` for top-level `guards` |
| WIRE-10 | `tests/runner/test_trace_completeness.py` | missing traces for cancelled/unscheduled; failure `wall_clock_ms 0`; post-dispatch exception escapes | none | Section 5 test rewrite |
| WIRE-11 | `tests/runner/test_node_trace_fields.py` | `cache_hit False`, `tier 'T3'`, no `execution_mode`/`spent`/`allowance` | none | subprocess node: reuse `tests/parts/test_admission.py::_opaque_part` / `_valid_admission_record` helpers (unprotected) so `host('subprocess', ceiling>0)` succeeds |
| WIRE-12 | `tests/seam/test_run_record_identity.py` | equal `wiring_id` for local and naive; hash differs across queries; no `trace_token` on post-dispatch refusal; parallel siblings overlap while record says `sequential` | none | local-arm hash test can run partial (`clients=None`) after committing only an `entities` vector dir |
| WIRE-13 | `tests/seam/test_seam_events.py` | outcome `'halted'` for a failed node; component is a part name | ingest returns events (LRAG-03, Phase 11) | `_mach11_events` unit test for failed outcome; ingest half needs `record-fail --at` before 11-01 |
| WIRE-14 | `tests/seam/test_engine_internals.py` | no-`items` output raises bare `KeyError`; `debug` still in signatures | `delete_document` namespaces (STOR-07), `resolve_evidence` no graph (STOR-03), `_build_stores` docstring has no `health`, likely the openie real-exception leg | assert via `refusal.cause` for MalformedEvidence |
| WIRE-15 | `tests/identity/test_env.py` | kernel string changes the hash; docstring omits inputs; health `ok` despite digest failure | none | `cache_clear()`; fake distribution with `/nix/store/` |
| WIRE-16 | `tests/seam/test_advanced_query_members.py` | `register(Part(effects=['reads_space']))` succeeds; `query.py` docstring still has the "later phase that registers" claim | `check_consumable` refuses all four members | `pytest.raises(ValueError)` then assert type name |
| WIRE-17 | `tests/seam/test_refusal_reachability.py` | `compare([s])` on a `mutates_store` wiring executes | HippoRAG `UnbudgetableParticipantError`; `retry_document` HippoRAG -> `NoWritePathForModalityError(operation='retry')` | use the `cbm_reachable`-style patch of `selectors._capability_candidates` (`tests/seam/test_mutable_store_exclusion.py`); usage-bearing client for the "not on LightRAG arms" leg |
| WIRE-18 | `tests/runner/test_runner_surface.py` | deleted names present; strings present; `run_wiring` result lacks the two settings | `ctx._semaphore` / `max_concurrency` used by openie (commit 40e541f) | assert absence via `hasattr`/AST |

## Section 10: Protected-test inventory (question 9)

Protected set = every `test_ref` file in `ledger/REQUIREMENTS.json` (`check_guard` is `[]`, `check_locks` is `null`) `[VERIFIED: ledger/REQUIREMENTS.json:2376,2388 and the hook's protected_sets]`. Files relevant to this phase (from the rows read):

| Decision | Protected files touched or constrained | Constraint |
|---|---|---|
| D-01 | `tests/seam/test_hipporag_write_path.py`, `test_hipporag_query_path.py`, `test_ingest_abort.py`, `test_empty_inputs.py` (HippoRAG selector `['reads_graph','reads_kv']`), `test_seam_doc_consistency.py` | mapping and docstring phrases unchanged |
| D-02 | `tests/parts_core/lightrag/test_kg_fidelity.py` (asserts assemble keys one at a time), `test_lightrag_corpus_path.py`, `tests/eval/test_lightrag_eval_store.py` | an added `items` key is harmless |
| D-03 | **`tests/seam/test_query_trace_nodes.py` (LRAG-19)** | **grant needed** |
| D-04/D-07 | `test_foreign_engine_refusal.py` (granted earlier), `test_refusal_catalogue.py`, `test_refusal_status_codes.py` (granted), `tests/mcp/test_mcp_refusal_mapping.py`, `test_refusal_body_shape.py` | new refusals: in `__all__`, 422, factory in unprotected `test_rest_transport.py` |
| D-05 | `test_seam_doc_consistency.py`, `test_ingest_abort.py`, `tests/parts_core/hipporag/test_dpr_fallback_guard.py` | `'test-time gate'`, `-O` behaviour, `budget_halt`, node-free D-21 codes |
| D-13/D-17 | `tests/runner/test_capability_scoping_modes.py`, `tests/runner/test_token_sum.py`, `tests/parts_core/hipporag/test_index_side_extraction.py` | `run_wiring` kwargs and `node_exceptions` stay; openie overlap |
| D-15 | **`tests/seam/test_lightrag_ingest_mach11.py` (LRAG-03)** | **grant needed** |
| D-16 | `tests/seam/test_health_honesty.py`, `test_health_probe.py` (and helper `test_corpus_status.py`) | `engine`/`stores` key sets and `engine_reason` equality |
| D-18/D-19 | `tests/parts_core/hipporag/test_registration.py`, `test_dpr_fallback_guard.py` | imports `validator.execution_mode`; four-keyword `declare_guard` |

**The two grant-needing edits (exact lines)**
1. `databasise/tests/seam/test_query_trace_nodes.py` lines 33-38 (`_expected_instance_hash`) currently inject query, allowance and `max_total_tokens` before hashing; line 51 asserts `trace["wiring_instance_hash"] == _expected_instance_hash(arm, question)`. Replacement for lines 33-38: `return f"sha256:{hashlib.sha256(canonicalise(resolve_arm(arm))).hexdigest()}"` (hash of the full resolved wiring before injection); line 51 is unchanged; drop the now-unused `engine_module._inject_*` calls. Tests at lines 54-95 that do not hash stay valid. The naive test at line 77 does not need `real_v1`, so it fails the moment D-03 lands.
2. `databasise/tests/seam/test_lightrag_ingest_mach11.py` line 17 `_SYNC = "lightrag/v1-index-sync@0.1.0"`; line 28 `assert [event.component for event in job.seam_events] == [_SYNC]`; line 34 `assert [event.component for event in outcome.seam_events] == [_SYNC]`. Replace the constant with `"mutates_store"` and keep the two assertions. Both tests are `@requires_v1` and run in this checkout.

Existing grants (no new grant needed) `[VERIFIED: ledger/REQUIREMENTS.json:2389-2421]`: `test_rest_corpus_endpoints.py`, `tests/mcp/test_tool_growth_invariant.py`, `test_refusal_status_codes.py`, `tests/wirings/test_store_effects_wired.py`, `test_ingest_file_name.py`, `test_ingest_input_refusals.py`, `test_empty_inputs.py`, `test_foreign_engine_refusal.py`.

## Section 11: Suggested plan split and wave order (question 10)

Constraints honoured: D-09's `items` guard (13-05) before D-02 (13-06); D-12 (13-03) before D-13/D-14 (13-04); the four hash-shifting changes in one plan (13-08), with the single re-mint/annotation as its last task; each grant-gated edit isolated at the start of its own plan; one owner per hot file per wave.

| Wave | Plan | Rows | Files (owner) |
|---|---|---|---|
| 1 | 13-01 Validator robustness and placement source | WIRE-06, WIRE-07 | `validator/*`, `parts_core/fixpoint_body.py` (docstring), `tests/parts/test_reference_parts.py`, new validator tests |
| 1 | 13-02 Read-namespace tokens and registration checks | WIRE-01, WIRE-16 | `parts/schema.py`, `parts/registry.py`, four LightRAG parts, `seam/selectors.py`, `seam/query.py`, tests |
| 1 | 13-03 Run-record model and derived schema | prerequisite of WIRE-10/11 (D-12) | `runner/trace.py`, `evidence/rig-trace.databasise.schema.json`, `evidence/RIG-TRACE-DEVIATIONS.md`, `tests/conftest.py`, `tests/runner/test_run_record.py`, `tests/evidence/` |
| 2 | 13-04 Scheduler: one trace per node, sequential | WIRE-10, WIRE-11, WIRE-12 (concurrency), WIRE-03 (construction), WIRE-05 (strict ints) | `runner/scheduler.py`, `seam/promotion.py`, runner tests |
| 2 | 13-05 Engine A: refusals, persist-before-raise, depth, reason gate, cycles, translation, `items` guard, `debug` kw | WIRE-03 (gate), WIRE-04, WIRE-05, WIRE-12 (trace_token), WIRE-14 | `seam/engine.py`, `seam/refusals.py`, `seam/redact.py`, `seam/envelope.py`, `tests/seam/test_rest_transport.py`, `test_seam_tracer.py`, `test_query_store_fault.py` |
| 3 | 13-06 Wiring evidence and LightRAG guard removal | WIRE-02, WIRE-09 | `wirings/lightrag/arm-*.json-patch.json`, `parts_core/lightrag/assemble.py`, `validator/parse.py`+`errors.py`, README, `docs/gui/CODEBASE-MAP.md` |
| 3 | 13-07 Engine B: compare, health | WIRE-17, WIRE-15 (health) | `seam/engine.py`, `seam/refusals.py` docstring, `docs/gui/API-INVENTORY.md` |
| 4 | 13-08 Hash-shift plan (first task: owner grant for LRAG-19) | WIRE-12 (identity, hash), WIRE-08, WIRE-18, WIRE-15 (env inputs), WIRE-05 (guard legs) | `wirings/resolve.py`, `seam/engine.py` (hash, arm_id), `identity/env.py`, `runner/guards.py`, `runner/scheduler.py` (guards, echo), `runner/budget.py`, `parts_core/hipporag/{fact_filter,assemble_result}.py`, `wirings/hipporag/base.json`, `wirings/lightrag/base.json` and arm patches (apportionment strings), `tests/seam/test_query_trace_nodes.py` (after grant), evidence annotation |
| 5 | 13-09 Seam events (first task: owner grant for LRAG-03) | WIRE-13 | `seam/engine.py` (`_mach11_events`), `seam/envelope.py`, `tests/seam/test_lightrag_ingest_mach11.py` (after grant), `test_mach11_event.py`, `test_compare.py`, `test_rest_transport.py` |
| 5 | 13-10 Closeout | all | `docs/gui/API-INVENTORY.md` stale refusal rows, STATE concern (cache_hit/TOOL-12), `evidence/PARITY-EVIDENCE.md` annotation if not already done, full gate |

Notes: 13-06 also shifts `wiring_instance_hash` (patch edits); the re-mint annotation in 13-08 must cover it. WIRE-12 spans 13-04, 13-05 and 13-08, so its row-level fail-first proof is recorded per leg and the row is verified after 13-08. Plans 13-08 and 13-09 are `autonomous: false` because the grants are owner-only (the hook says only the owner can allow the edit); everything else proceeds without them.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1, pytest-asyncio 1.4.0 (`asyncio_mode = "auto"`) `[VERIFIED: probe, pyproject.toml]` |
| Config file | `databasise/pyproject.toml` `[tool.pytest.ini_options]` (`testpaths = ["tests"]`, `addopts = '-m "not live"'`) |
| Quick run command | `cd databasise && .venv/bin/pytest -q tests/<dir>/<file>.py -x` (a 3-directory slice ran in 2.9 s: `tests/seam/test_selectors.py tests/runner/test_scheduler.py tests/validator`) |
| Per-wave command | `cd databasise && .venv/bin/pytest -q tests/seam tests/runner tests/validator tests/wirings tests/identity tests/parts tests/parts_core tests/evidence tests/parity` |
| Full suite command | `cd databasise && .venv/bin/python tools/check_offline_suite.py` (runs `pytest -q -rs` then `python -m pytest -q -rs`; RUN-12 gate) |

Never pass `-m live`. Baseline at HEAD (fdbc145) `[VERIFIED: probe]`: `.venv/bin/pytest -q` gave `2203 passed, 4 deselected in 590.48s (0:09:50)` with the v1 venv present. `check_offline_suite.py` runs the suite twice (about 20 minutes), so use it at wave merges and the phase gate, not per task.

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WIRE-01 | all six candidates reachable; mapping documented | unit | `.venv/bin/pytest -q tests/seam/test_selector_reachability.py` | Wave 0 (new) |
| WIRE-02 | ghost refs; KG evidence | unit + integration (`real_v1`) | `.venv/bin/pytest -q tests/validator/test_top_level_refs.py tests/seam/test_evidence_position.py` | Wave 0 |
| WIRE-03 | node-free reasons | integration | `.venv/bin/pytest -q tests/seam/test_stop_reason_leak.py` | Wave 0 |
| WIRE-04 | depth_label | unit | `.venv/bin/pytest -q tests/seam/test_depth_label.py` | Wave 0 |
| WIRE-05 | named pre-dispatch refusals | integration | `.venv/bin/pytest -q tests/seam/test_preflight_refusals.py` | Wave 0 |
| WIRE-06 | parse never raises | unit | `.venv/bin/pytest -q tests/validator/test_parse_report.py` | Wave 0 |
| WIRE-07 | single placement source | unit | `.venv/bin/pytest -q tests/validator/test_execution_mode_single_source.py tests/parts/test_reference_parts.py` | Wave 0 |
| WIRE-08 | guard signal | unit | `.venv/bin/pytest -q tests/runner/test_guard_evaluation.py` | Wave 0 |
| WIRE-09 | no ignored `guards` key | unit | `.venv/bin/pytest -q tests/wirings/test_lightrag_guards.py` | Wave 0 |
| WIRE-10 | trace completeness | unit | `.venv/bin/pytest -q tests/runner/test_trace_completeness.py` | Wave 0 |
| WIRE-11 | NodeTrace fields | unit | `.venv/bin/pytest -q tests/runner/test_node_trace_fields.py` | Wave 0 |
| WIRE-12 | identity, persist, concurrency | integration | `.venv/bin/pytest -q tests/seam/test_run_record_identity.py` | Wave 0 |
| WIRE-13 | seam events | unit | `.venv/bin/pytest -q tests/seam/test_seam_events.py` | Wave 0 |
| WIRE-14 | engine internals | unit | `.venv/bin/pytest -q tests/seam/test_engine_internals.py` | Wave 0 |
| WIRE-15 | env inputs; health | unit | `.venv/bin/pytest -q tests/identity/test_env.py` | Wave 0 |
| WIRE-16 | registry effect validation | unit | `.venv/bin/pytest -q tests/seam/test_advanced_query_members.py` | Wave 0 |
| WIRE-17 | reachability pins | integration | `.venv/bin/pytest -q tests/seam/test_refusal_reachability.py` | Wave 0 |
| WIRE-18 | runner surface | unit | `.venv/bin/pytest -q tests/runner/test_runner_surface.py` | Wave 0 |

Additional new test: `tests/evidence/test_derived_trace_schema.py` (drift test + deviation-record presence).

### Sampling Rate
- **Per task commit:** the one new test file plus the directory it lives in.
- **Per wave merge:** the per-wave command above, then the protected files named in Section 10 for any decision touched in that wave.
- **Phase gate:** `check_offline_suite.py` green under both invocation styles before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] 18 new test files named above, created in the plan that implements the row (tests first, failing by assertion).
- [ ] `tests/evidence/test_derived_trace_schema.py`.
- [ ] A small helper for "committed `entities` vector dir only" (WIRE-12 local-arm partial run) in `tests/seam/_probes.py` (unprotected).
- [ ] Framework install: none.

## Security Domain

`security_enforcement` is `false` in `.planning/config.json`, so no ASVS table is required. The phase's security-relevant behaviour is the information-disclosure fix in D-05/D-07 (node ids, part names, exception class names and registered-part lists must not reach a consumer) and strict input typing (bool/float/str rejected for `max_concurrency` and `token_allowance`).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `databasise/.venv` Python | all tests | yes | 3.12.13 | none needed |
| `v1/.venv/bin/python` | `requires_v1` tests (KG arms, mach11, LRAG fixtures) | yes | not probed | those tests skip when absent; use part-level tests |
| jsonschema, jsonpatch | derived-schema tests | yes | 4.26.0, 1.33 | none needed |
| External services / Docker | none | n/a | n/a | n/a |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The WIRE-14 HippoRAG "real exception" leg already passes at HEAD (HIPP-04 plus `_node_result_or_refuse`) | 4.6 | Low: an extra fix would then be needed in `_node_result_or_refuse` |
| A2 | No protected test passes `debug=` to `query`/`query_stream`/`compare` | 4.6 | Medium: removal would need an owner grant; check by running the suite |
| A3 | Stamping a top-level `arm_id` key on resolved wirings is acceptable (no consumer rejects unknown top-level keys) | 1.2 | Low: `parse_wiring` reads only `nodes`; protected `test_query_trace_nodes.py` hashes `resolve_arm(arm)` itself |
| A4 | A failed node keeps `budget_state="halted"` | Pitfall 6 | Low: only the frozen enum meaning is stretched; status disambiguates |
| A5 | Reusing `ForeignEngineRefusalError` with a new `failure_class` for `EnvironmentDigestError` satisfies D-07's "named seam refusal" | 4.5 | Low: a dedicated class is a one-class addition |
| A6 | Annotating, not re-minting, archived parity evidence satisfies D-21 | Runtime State Inventory | Medium: re-minting needs live provider spend |
| A7 | The closed-set mapping gate (never 500) satisfies D-05's "response-time gate" wording | 4.1 | Medium: owner may want a raising gate |

## Open Questions

1. **WIRE-05 public violation shape.** What we know: `UnparseableWiringError.violations` is `list[str]` of codes and D-07 keeps "code only". Unclear: whether the owner wants `[{"code": ...}]` objects. Recommendation: keep `list[str]` (no factory or catalogue change); the WIRE-05 fail-first comes from cycles, strict ints and translation legs.
2. **`cancelled` reachability.** With sequential dispatch only a body-raised `CancelledError` produces it. Recommendation: implement as in Section 5 item 5 and say so in the WIRE-10 exception note.
3. **Failed node `budget_state`.** Recommendation: keep `halted` (unchanged); `cancelled`/`not-scheduled` use `within_budget`.
4. **Re-mint vs annotate** archived evidence hashes. Recommendation: annotate in `evidence/PARITY-EVIDENCE.md` (A6).
5. **WIRE-14 delete/resolve legs** are satisfied by earlier commits; record as such rather than fabricating a fail-first run.
6. **Protected tests using `debug=`** (A2): confirm during execution.
7. **`arm_id` mechanism** (A3): stamping versus deriving from `wiring_id`; deriving needs a special case for naive (`lightrag-base`) and for `hipporag-base`.
8. **Where the LightRAG deviation record lives** (no LightRAG port record file exists): recommendation `wirings/lightrag/README.md`.
9. **`EnvironmentDigestError` refusal class and status** (A5): 502 via `ForeignEngineRefusalError`, 503 by adding the class to `_ENGINE_UNAVAILABLE`, or a 422 class.
10. **Gate behaviour on a hit** (A7).

## Sources

### Primary (HIGH confidence, files opened this session)
- `.planning/phases/13-selectors-wiring-runner/13-CONTEXT.md`, `.planning/REQUIREMENTS.md` (WIRE rows 336-412), `.planning/STATE.md`
- `databasise/seam/{selectors,engine,refusals,redact,envelope,evidence,tokens,query,trace_store,promotion,rest}.py`
- `databasise/runner/{scheduler,trace,guards,budget}.py`; `databasise/validator/{parse,errors,depth,execution_mode,blast_radius}.py`
- `databasise/wirings/resolve.py`, `wirings/lightrag/*.json(-patch)`, `wirings/hipporag/base.json`, `parts/{schema,registry}.py`, `identity/{env,instance}.py`
- `databasise/parts_core/lightrag/{assemble,chunk_sel_kg,entity_lookup,chunk_vector,rerank}.py`, `parts_core/hipporag/{fact_filter,assemble_result}.py`
- Tests: `tests/conftest.py`, `tests/seam/{test_query_trace_nodes,test_lightrag_ingest_mach11,test_seam_doc_consistency,test_refusal_catalogue,test_refusal_status_codes,test_seam_tracer,test_query_store_fault,conftest,_probes}.py`, `tests/runner/{test_scheduler,test_capability_scoping_modes,test_live_metering}.py`, `tests/parts_core/hipporag/{test_dpr_fallback_guard,test_registration}.py`, `tests/parts_core/lightrag/{test_kg_fidelity,test_v1_index_sync}.py`, `tests/seam/test_lightrag_corpus_path.py`
- `docs/system-model/rig-trace.schema.json`, `docs/system-model/RIG.md` (§R columns)
- `ledger/REQUIREMENTS.json` (Read tool), `/home/chris/coding/GUI-research/adapters/claude-code/hooks/check-edit-guard.py`
- Read-only probes in the session scratchpad (`probe1.py`-`probe4.py`)

### Secondary (MEDIUM confidence)
- `p13-research.txt` six-agent study (claims tagged `[CITED]`)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH (no new package; versions probed)
- Architecture: HIGH for mechanism and file/line locations; MEDIUM for the plan split (planner owns it)
- Pitfalls: HIGH where tagged `[VERIFIED]`; MEDIUM for protected-test interactions I could only read selectively

**Research date:** 2026-10-19
**Valid until:** 2026-11-02 (the code base moves quickly; re-check line numbers after any plan merges)
