# Phase 14: Promotion & Ledger - Context

**Gathered:** 2026-10-20
**Status:** Ready for planning
**Mode:** Auto discuss (autonomous). The owner delegated grey-area decisions in Phases 9–13 ("You decide") and asked the run to continue in gsd-autonomous mode. Each decision below is Claude's choice under that delegation. Each is grounded in a five-agent code study: four area lanes and a critic, with probes run against HEAD ed03b7d after Phase 13. Scripts are in the session scratchpad p14/. Every decision is numbered; planning and verification treat it as binding.

<domain>
## Phase Boundary

The operator verbs (promote, rollback, retire) never fail with a 500 on any trace. Every alias that has a generation can be selected and resolves, or refuses by name. An alias's history can be read from the ledger. Selection, validation and the registry agree with what the wirings do. Requirements: LEDG-01 to LEDG-14.

**State at HEAD (the probes found these):**
- A partial trace no longer gives a 500. It gives a false `UnknownTraceReferenceError` (404, from `promotion.py:141`), because `_dispatched_node_ids` keeps only completed nodes. An old-format partial record, with no `status` fields, is still promoted, because `partial` is never read at `engine.py:2265-2298`.
- `all_wirings()` gives `arm_id` equal to the arm name for all six arms (Phase 13 D-03).
- `resolve_arm('hipporag')` raises `UnknownArmError`, which is not a SeamRefusalError, so an alias whose row names hipporag gives a 500 (`selectors.py:300`).
- Retire checks only `active.minted_version` (`engine.py:2646`).
- `degraded = partial or any(guards_fired)` (`scheduler.py:849`, Phase 13 D-21). The LEDG-02 note "degraded always equals partial" is out of date.
- Already met at HEAD: capability matching uses the pruned run (LEDG-10, `selectors.py:188`, commit 3fd6e4c). The kind-mismatch violation exists (LEDG-11, `parse.py:229-238`, commit 5d61a79). Promote already refuses empty and hash-shaped aliases (LEDG-05 promote leg).

**Out of scope:**
- the REST and MCP ledger read routes (Phase 16: CONN-06, CONN-07, CONN-09);
- persisting a calibrated floor so the gate verbs can succeed (TOOL-12 / EVAL-10);
- authentication and an operator-only debug gate (no auth layer exists; see Deferred).
</domain>

<decisions>
## Implementation Decisions

### A. Trace evidence and gate verbs (LEDG-01, 02, 08)

- **D-01 (LEDG-01, M-06 option (b)):**
  - `promote` refuses any partial trace.
  - `rollback` and `retire` accept partial traces.
  - The arm comes from `record["arm_id"]` when it is an `all_wirings()` name. Node-set matching (`_arm_name_for_node_ids`) stays only as the fallback for pre-Phase-13 records.
  - A partial record whose arm cannot be identified (old format, `arm_id` `"seam"`) raises the new `PartialRunEvidenceError(trace_ids)` (422). It never raises the false 404 or an `AssertionError`.
  - **Basis:**
    - CONTRACT §9: a partial run is traced, scored and labeled like a completed one, and is never discarded.
    - CONTRACT §6: an operator-asserted record cites the traces the operator read.
    - rollback and retire keep only `arm_instance_hashes` (`engine.py:2485, 2626`), and since Phase 13 D-03 those hashes are stable for partial runs.
    - Under option (a), `clients=None` makes every multi-node trace partial, which would block rollback in exactly the case it exists for.
- **D-02 (LEDG-01/02, the refusal class):**
  - `PartialRunEvidenceError(trace_ids)` is defined in `seam/refusals.py`, listed in `__all__` and mapped to 422.
  - It needs one factory entry in `tests/seam/test_rest_transport.py::_REFUSAL_FACTORIES`, which SEAM-04's `test_refusal_status_codes` reads, and it must pass the SEAM-14 refusal catalogue.
  - Its message names neither the arm nor any node id (§18.3).
- **D-03 (LEDG-02, G-18):**
  - The partial rule applies to promote only, and is keyed on `partial`, not `degraded`. A degraded run that is not partial took a declared fallback and completed (Phase 13 D-21; CONTRACT §19.8). It stays promotable.
  - The check is one function in `seam/promotion.py`, for example `refuse_partial_evidence(records, trace_ids)`. It runs after trace resolution and before arm matching. It catches both the old-format bypass record (promoted today) and the failed bypass run that carries statuses.
  - Phase 16's CONN-09 preview must call the same function (see Specifics).
- **D-04 (LEDG-08, G-19):**
  - A new `GateNotCalibratedError(verb)` (422) is raised for `promote-next` and `promote-now`.
  - It sits at `engine.py:2342-2343`, right beside `GateVerbNotBuiltError`. That is before alias validation, trace resolution and `Ledger()` construction, so no `ledger.db` is created (this also covers LEDG-06(b)).
  - The refusal is the same for every arm and never depends on the mutation class.
  - `enforce_gate_verb_posture`, `MeasurementPostureRefusalError` and `UncalibratedFloorRefusalError` stay for TOOL-12, which lifts the refusal only for an arm that has a floor.
  - Tests and docs:
    - Five unprotected tests in `tests/seam/test_promotion_posture.py` that pin per-class outcomes are rewritten. The LEDG-08 test lives in that file.
    - `docs/gui/API-INVENTORY.md` §3.5.1 is updated.

### B. Aliases (LEDG-03, 04, 05)

- **D-05 (LEDG-03, M-07 option (a)):**
  - Alias resolution resolves every `all_wirings()` name, hipporag included.
  - The arm-name lookup (`promotion.py:144-157`) moves into `wirings/resolve.py`, which avoids the selectors/engine circular import. It returns None on a miss, because `resolve.py` cannot import seam refusals. Callers map None to a refusal.
  - D-01's `arm_id`-first check, `selectors._resolve_alias` and the verb-path calls (`engine.py:2353, 2368, 2504, 2508, 2649, 2651`) all use it. This also removes the `AssertionError` 500 on promote, rollback or retire against an alias whose row names an unknown arm.
  - A row that names an arm that cannot be resolved raises `UnsatisfiableSelectorError(selector_kind="alias", requested=alias)`. No body contains 'known arms' or any arm list.
  - The HippoRAG corpus surface exists (Phase 12), so ingest and delete under a HippoRAG alias route like `{arm: hipporag}`.
  - Unprotected follow-up: the six-arm promote test in `test_operator_verb_concurrency.py` expects the hipporag alias to resolve.
  - REST `/compare` and `/query/stream` under a HippoRAG alias are covered by the LEDG-03 test. The study did not probe them.
- **D-06 (LEDG-04, G-17: guard by version, through the rollback lineage):**
  - A new `Ledger.lineage(alias, version)` follows `targets_version` through the row that minted each version, using the unique index on `(alias, minted_version)`. It keeps a visited set and stops at a promotion row.
  - Retire refuses V with `ActiveGenerationRetirementError` when V is in the active row's lineage.
  - Rollback refuses with `TombstonedGenerationError` when any version in the target's lineage is tombstoned. This is Success Criterion 3, "never keeps serving a tombstoned generation".
  - Not by identity: RIG §PR.2 and the retire docstring (`engine.py:2609-2616`) treat a re-promotion as a new generation. An identity guard would wrongly refuse retiring naive@1.0.0 while naive@1.1.0 is active.
- **D-07 (LEDG-05):**
  - `InvalidPromotionAliasError` is reused for all three verbs.
  - The alias check (`engine.py:2347`) moves to the top of `_resolve_operator_preconditions`. That keeps the order verb, alias, change_origin, trace, which protected `test_promote_alias_validation.py` (SEAM-12) requires.
  - The class docstring (`refusals.py:167-171`) is updated.
  - Promote already refuses at HEAD. The fail-first leg is therefore rollback and retire on seeded bad-alias rows (they give `UnknownGenerationVersionError` today).

### C. Ledger store, history and tenancy (LEDG-06, 07, 09)

- **D-08 (LEDG-06, closing and read-only opening):**
  - `Ledger` gains `close()`, `__enter__` and `__exit__`. `with` is used at `selectors.py:297` and `engine.py:2363, 2496, 2636`, inside the executor-thread closures.
  - `Ledger.open_existing(root)` returns None when `ledger.db` is absent. Otherwise it builds `Ledger` normally, keeping the full `_create_schema` step: its index migration at `ledger.py:248-251` must not be skipped on old files.
  - `_resolve_alias`, rollback and retire use `open_existing`. rollback and retire raise `UnknownGenerationVersionError` on None.
  - The "stall" wording in `Ledger.transaction()`'s docstring (`ledger.py:184-187`) is rewritten.
  - Basis: CONTRACT §6, a read path must not write.
- **D-09 (LEDG-07, a projection type):**
  - `@dataclass(frozen=True, kw_only=True) class LedgerEntry(LedgerRecord)` adds `id` (the generation ordinal) and `created_at`. `LedgerRecord`'s CONTRACT §7 field list is unchanged.
  - `_row_to_record` takes a `cls` parameter.
  - `Ledger.history_for_alias(alias)` returns every row for the alias, ordered by id, oldest first.
  - `history(mutation_id)` is kept and documented as test-only, because six unprotected tests use it.
  - This phase adds the engine read only. REST and MCP routes come in Phase 16 (CONN-06, CONN-07).
- **D-10 (LEDG-09, G-35 tenancy and strict debug):**
  - One store_root is one tenant. This is documented in the `Databasise` class docstring (`engine.py:1127`) and in `docs/gui/API-INVENTORY.md` (lines 13 and 825, plus open question 14). No workspace key is added to `trace.db` or `ledger.db` now.
    - Basis: the launcher locks per store_root (`launcher/__init__.py:115`), CONN-04 assumes a single workspace, and aliases name wirings, not data.
  - `debug` on `/trace/resolve` and the MCP trace tool is `StrictBool` (`rest.py:214`, `mcp/tools.py:200`). A string or number gives a 422 or validation error, and no debug field is returned.
  - debug=true is not restricted to operators. There is no auth layer, and CONTRACT §18.3 privileges no client. A later gate would follow the CONN-14 launcher-flag pattern (see Deferred).

### D. Selection, validation and registry (LEDG-10 to 14)

- **D-11 (LEDG-10, already met):**
  - Capability matching uses Part effects over the pruned query run, so HippoRAG's index-side nodes do not count at query time (CONTRACT §19.9, and §2's deny-by-default rule).
  - The phase adds the table test that pins the effective effect set for every arm. The fail-first is recorded at `3fd6e4c^`.
  - The node-count tie-break (`selectors.py:194`) is unchanged, because switching it to pruned counts would change which arm is selected.
- **D-12 (LEDG-11, already met):**
  - The `kind-mismatch` violation exists. The phase adds `tests/validator/test_node_kind.py`, which also checks that every file under `databasise/wirings/` parses. The fail-first is recorded at `5d61a79^`.
  - "Raises" in the row text means "reports a named `kind-mismatch` violation" (Phase 13 D-07/D-08: parse_wiring reports and never raises).
- **D-13 (LEDG-12, unregister codebase-memory-mcp):**
  - `codebase-memory-mcp@0.1.0` is dropped from `default_registry()` (`registry.py:225`) and added to `falsifier2.probe_registry()`. `falsifier2._parse` (`falsifier2.py:297`) switches to that registry, so the Falsifier 2 gate does not fail with `unknown-component`.
  - `wirings/codebase-memory-mcp.json` moves to `databasise/tests/fixtures/codebase-memory-mcp.json` (14-RESEARCH §5.3). The evidence copy `w2` is a different, three-node wiring, so it does not replace this one.
  - Protected `tests/seam/test_refusal_reachability.py` (WIRE-17) reads the old path and the default registry, and no product-side fix exists. It is an owner `grant-check-edit` item with exactly the edit in 14-RESEARCH §6.4:
    - the `_CBM_WIRING_PATH` path;
    - an optional `registry=None` on `_engine`;
    - `test_compare_with_one_mutating_selector_is_refused` registers `CODEBASE_MEMORY_MCP_PART` on a `default_registry()` copy.
  - `test_mutable_store_exclusion.py` passes `registry=`. The `refusals.py:496` docstring is updated.
  - The reachability test covers admitted parts only. Reference and corpus-only parts are not reached through a selector by design.
  - Basis: F-07 lists it as "catalogued, not registered", CONTRACT §14.4 point 3, and the `mutates_store` risk before TOOL-18. CONN-05 already excludes it.
- **D-14 (LEDG-13):**
  - `engine._corpus_wiring` calls `wirings.resolve.load_wiring(family, variant=f"corpus-{operation}")` and maps `FileNotFoundError` to `NoWritePathForModalityError` (422).
  - `engine._WIRINGS_ROOT` (`engine.py:315`) is deleted. No source outside the tests uses it.
- **D-15 (LEDG-14):**
  - The docstrings listed in the row are rewritten to current facts.
  - Only the phrase "two declaration-only placeholders" is banned, because "declaration-only" is still correct at `registry.py:12, 157, 161, 199` and `schema.py:120, 130`.
  - New `selectors.py` wording must avoid SEAM-16's banned phrases: 'registry is empty', 'five arms', 'five Phase 3 arms', '_ARM_NAMES'.

### E. Execution rules

- **D-16 (protected checks):**
  - Each plan runs every protected `test_ref` file it touches after each task.
  - The alias and ledger-store changes (D-05 to D-10) were not run against protected tests with the changes applied, because the edit guard blocked the study's patched runs.
  - Any protected test that the change breaks must first get a product-side fix. Only if none exists is it reported as an owner `grant-check-edit` item, with the exact edit.
- **D-17 (fail-first):**
  - Every row test is a new node in an unprotected file, and it fails on pre-fix code by plain AssertionError.
  - Rows already met at HEAD (LEDG-10, LEDG-11, and the LEDG-05 promote leg) record fail-first with `record-fail --at <fixing commit>^`.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `docs/system-model/CONTRACT.md`. §5 is the verb ladder and the A/A floor; §6 covers operator-asserted records and the rule that reads never write; §7 is the LedgerRecord fields; §9 is partial runs; §14.4 is registry admission; §18.2–§18.5 are the consumer seam, selectors and tool surface; §19.8–§19.9 cover degradation and effects. This copy is frozen and must not be edited.
- `docs/system-model/RIG.md`. §PR.2 defines generations; §F3.2 is the measurement posture.
- `.planning/REQUIREMENTS.md`: LEDG-01..14, plus CONN-05/06/07/09 for the Phase 16 consumers.
- `.planning/ROADMAP.md`: the Phase 14 success criteria and owner-decision list.
- `.planning/phases/13-selectors-wiring-runner/13-CONTEXT.md`: D-01 (reads_namespaces), D-03 (per-arm identity and the hash), D-07/D-08 (report and never raise), D-21 (degraded).
- `docs/gui/API-INVENTORY.md`: §3.5.1, lines 13 and 825, and open question 14.
- `databasise/evidence/f07_report.py:40-46`: the codebase-memory-mcp catalogue entry.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_NOT_BUILT_VERBS` and `_GATE_VERBS` (`promotion.py:63-64`), and the guard at `engine.py:2339-2343`.
- `_resolve_operator_preconditions` (`engine.py:2265`) is the one shared prologue for all three verbs.
- `all_wirings()`, plus the arm-name lookup that moves into `wirings/resolve.py`.
- `UnsatisfiableSelectorError`, `InvalidPromotionAliasError`, `ActiveGenerationRetirementError`, `TombstonedGenerationError` and `UnknownGenerationVersionError` in `seam/refusals.py`.
- `Ledger.transaction()`, the `(alias, minted_version)` unique index, and `generation_state` (`ledger.py:370-375`). The new `open_existing` and `lineage` helpers are reused by CONN-06/07/09.
- `falsifier2.probe_registry()`, `render_f07_record(registry)`, and the engine's `registry=` argument.
- `eng._trace_store.persist(...)` builds synthetic partial traces in tests.

### Established Patterns
- REST maps any SeamRefusalError subclass through `_status_for` (`rest.py:149-154`, 422 by default). MCP maps it through `_find_refusal` (`mcp/server.py:102-109`).
- Every new refusal class goes in `refusals.__all__` and gets a `_REFUSAL_FACTORIES` entry (SEAM-04, SEAM-14).
- `_set_wal`'s retry (`ledger.py:145-173`) handles concurrent opens.

### Integration Points
- `selectors._resolve_alias` (`selectors.py:297-300`) receives D-05, D-08 and D-10 in one edit.
- The engine verb paths: `engine.py:2339-2400` (promote), `2477-2530` (rollback) and `2618-2660` (retire).
</code_context>

<specifics>
## Specific Ideas

- **Phase 16 text to amend before Phase 16 plans** (recorded here, so REQUIREMENTS.md is not edited in this phase):
  - CONN-09: "partial", not "partial or degraded"; the gate reason is `GateNotCalibratedError`; preview calls D-03's shared function.
  - CONN-07: `active` uses D-06's lineage.
  - CONN-05: the out-of-date `wiring_id` claim, and the hipporag node count (14, not 13).
- `test_operator_verb_concurrency::test_six_concurrent_promotes…` failed once under parallel background load, then passed 3/3 in isolation. Run it alone if it flakes.
- A rollback row may cite a failed run's trace (D-01). The Phase 17/18 console should label such evidence.
</specifics>

<deferred>
## Deferred Ideas

- Per-workspace trace and ledger namespaces (G-35's alternative). Revisit if one store_root ever serves more than one tenant.
- An operator-only debug gate on trace resolve, following the CONN-14 launcher-flag pattern, once an auth layer exists.
- Persisting a calibrated A/A floor so the gate verbs can succeed (TOOL-12 / EVAL-10).
- Wiring codebase-memory-mcp as a selectable arm (TOOL-15 and TOOL-18) once a consumer exists.
</deferred>

---

*Phase: 14-promotion-ledger*
*Context gathered: 2026-10-20*
