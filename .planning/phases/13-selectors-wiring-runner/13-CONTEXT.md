# Phase 13: Selectors, Wiring & Runner - Context

**Gathered:** 2026-10-19
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous). The owner delegated grey-area decisions in Phases 9–12 ("You decide") and asked the run to continue with "Run what you recommend next". Each decision below is Claude's choice under that delegation and is grounded in a six-agent code study (five areas and a critic; probes run against HEAD c4256a8 after Phase 12). Each one is numbered, so planning and verification treat it as binding.

<domain>
## Phase Boundary

Every query arm can be selected. The runner records every node truthfully. Consumers never see an internal node id or an unstructured 500 from the wiring layer. Requirements: WIRE-01 to WIRE-18.

**Out of scope:**
- ledger and promotion semantics (Phase 14: LEDG-01/02/12/13 consume WIRE-12 and WIRE-17);
- console and tool consumers (TOOL-09, CONN-03/05, GUI-04/05/07; they regenerate fixtures from these rules);
- the HippoRAG empty-namespace pre-check (Phase 12 D-15, still deferred, see Deferred).
</domain>

<decisions>
## Implementation Decisions

### A. Arm selection, evidence and identity (WIRE-01, 02, 12)

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

### B. Consumer vocabulary and refusals (WIRE-03, 04, 05, 06, 14, 16, 17)

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

### C. Run-record truth (WIRE-10, 11, 13, 18)

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

### D. Guards and placement (WIRE-07, 08, 09)

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

### E. Cross-cutting

- **D-21 (hash-shift batching):**
  - D-03 (per-arm wiring_id and pre-injection hash), D-16 (environment inputs), D-17 (deleted config strings) and D-19 (the guard `signal` key) each shift config, instance or wiring-instance hashes.
  - They land in one plan. Pinned hashes in evidence and parity records are re-minted or annotated once.
  - Promotion compares no stored hash (engine.py:2168-2174 only collects them).

### Requirement text exceptions (to record in REQUIREMENTS.md)

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

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- **Phase scope:**
  - `.planning/ROADMAP.md`: the Phase 13 goal, success criteria and owner-decision list.
  - `.planning/REQUIREMENTS.md`: WIRE-01 to WIRE-18, with the exception clauses above.
- **Defects:** `docs/gui/DEFECTS.json`: M-08, M-11, G-21, G-23..G-26, G-31, VAL-03, D-15, T-17, RUN-*, VAL-*, ENG-*.
- **Contract and frozen documents (read only):**
  - `docs/system-model/CONTRACT.md`: §9 D4 at :400; §14 at :529, :570-578, :599, :629, :630; §18 at :771-810; :72, :178, :236-238, :276.
  - `RIG.md` (§TR.1, :110, §AA.1) and `rig-trace.schema.json`: frozen, read only.
- **Locked decisions:**
  - `.planning/phases/08-*` to `12-hipporag-fixes/12-CONTEXT.md`.
  - From Phase 12 in particular: D-16 (prune), D-19 (qa), D-21 (degraded codes), D-08 (max_concurrency), D-09 (private node id).
- **Research output** (session scratchpad, not tracked): the evidence for each decision, with file:line citations and probes.

</canonical_refs>

<code_context>
## Existing Code Insights

**Measured at HEAD.**
- Node counts, full/pruned: naive 7/6, bypass 1/1, hybrid 17/16, local 15/14, global 15/14, hipporag 14/7.
- All five LightRAG arms have wiring_id 'lightrag-base' and evidence_position chunk-vector.
- The default selector resolves to naive.

**Line drift in the requirement texts.** Current locations:

| Requirement | Code | Current location |
|---|---|---|
| WIRE-12 | two-provides raise | engine.py:1008-1013, in `_select_answer` at :986 |
| WIRE-12 | persist | engine.py:2090 |
| WIRE-14 | `items` KeyError | engine.py:2074 |
| WIRE-11 | stale comments | scheduler.py:659-660 and 687 |
| — | `evaluate_guards` call | scheduler.py:674 |
| — | `_validated_guards` | scheduler.py:393-402 |
| — | `_CONCURRENCY_SETTING` | engine.py:433 |
| — | `environment_hash` call | scheduler.py:339 |
| — | `health()` | engine.py:1880-1950 |

**Protected tests the decisions rely on, unedited:**
- `test_hipporag_write_path.py`, `test_hipporag_query_path.py`, `test_ingest_abort.py` and `test_empty_inputs.py` (selector mappings).
- `test_seam_doc_consistency.py` (SEAM-16 docstring phrases).
- `test_refusal_catalogue.py` and `test_refusal_status_codes.py` (new refusals: in `__all__`, 422).
- `test_capability_scoping_modes.py` (STOR-05: run_wiring kwargs, node_exceptions).
- `test_dpr_fallback_guard.py` (HIPP-14: declare_guard signature, node-free codes).
- `test_health_honesty.py` and `test_health_probe.py` (key sets).
- `test_kg_fidelity.py` (LRAG-17: per-key asserts on assemble).

**Grant-needing edits (owner):**
- `tests/seam/test_query_trace_nodes.py` (LRAG-19, D-03).
- `tests/seam/test_lightrag_ingest_mach11.py` (LRAG-03, D-15).
- Re-check every file a task edits against the ledger at plan time with the Read tool.

**Helper files imported by protected tests are treated as protected:** `tests/seam/test_corpus_status.py` and the `tests/stores/test_graph_lock.py` helpers.

**Phase rules:**
- Commits need a `phase/13` trailer.
- `.planning/` changes are separate from code commits.
- Interpreter: `databasise/.venv/bin/python`.
- Executors run no ledger command.

</code_context>

<specifics>
## Specific Ideas

Fail-first notes:
- WIRE-01, 02, 03, 04 and 12 fail at HEAD.
- These legs already pass at HEAD, so each needs `record-fail --at` an older commit or a different failing leg:
  - WIRE-05's ingest/delete KeyError leg (feadf3e^);
  - WIRE-13's ingest-events half (before 11-01);
  - WIRE-16's four-member leg (prove it through the registration leg);
  - WIRE-18's semaphore leg (before 40e541f);
  - WIRE-07's placement check (prove it through the deleted-duplicate leg).
- On a fresh root, LightRAG queries refuse with EmptyNamespaceError, so LightRAG legs need a populated store (the `synthetic_naive_store` fixture).

</specifics>

<deferred>
## Deferred Ideas

- **The CONTRACT §14.2 load-time read-namespace typecheck** (the machine checks a declared namespace against the resolved store at load). D-01 is matching-only; revisit with the GUI capability picker (GUI-04/05).
- **The HippoRAG empty-namespace pre-check** (Phase 12 D-15). No WIRE row requires it, and it changes what protected STOR-06 means. It needs an owner grant, either an EmptyNamespaceError expectation or a populate-first rewrite.
- **A refusal for a trace whose run was refused at the seam but whose record is clean** (the D-04 unbudgetable case). This is Phase 14 (LEDG-02).
- **Real-engine A/A calibration once cache_hit is null.** This is TOOL-12 (Phase 15).

</deferred>

---

*Phase: 13-selectors-wiring-runner*
*Context gathered: 2026-10-19*
