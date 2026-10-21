# Phase 15: Offline Tooling & Packaging - Context

**Gathered:** 2026-10-21
**Status:** Ready for planning
**Mode:** Auto discuss (autonomous). The owner delegated grey-area decisions in Phases 9–14 ("You decide") and asked the run to continue in gsd-autonomous mode.

Each decision below is Claude's choice under that delegation. Each is grounded in a five-agent code study: four area lanes and a critic. The critic ran the full offline suite (2608 passed) with logging-only plugins that showed where proposed checks would refuse. It also built a wheel and simulated the dry-run defaults.

The study notes, with file:line evidence, are in the session scratchpad:
- `p15-study.txt` (lanes);
- `p15-critic.txt` (consolidation);
- `p15/` (probes).

Each decision is numbered. Planning and verification treat the numbered decisions as binding.

<domain>
## Phase Boundary

After this phase the offline CLIs:
- run from an installed wheel;
- refuse by name instead of crashing;
- never spend, and never write outside their own store, by default.

The evaluation and evidence records they produce state only what was measured. Admission is enforced when the registry loads. Requirements: TOOL-01 to TOOL-20.

**Facts at HEAD that shape this phase:**
- A wheel built from HEAD lacks `databasise.tools`, the eval bundles and both corpus fixtures. Every default path into the repo (`_REPO_ROOT/v1/...`, `tests/fixtures/...`) resolves inside site-packages from a wheel.
- `import_index --help` takes the store lock and runs a full import, because argv is checked only for the literal `--verify` (`import_index.py:710-721`).
- Only `corpus_ingest` and `aa_run` have `--spend`. run_arm, storage_audit, run_comparison and run_cross_modality spend by default.
- **TOOL-17 is already met by removal:** commit 226b2cf, Phase 10 D-15. Its check is `databasise/tests/test_removed_stores_absent.py`.
- Phase 14 refused the gate verbs up front (`GateNotCalibratedError`). TOOL-12 lifts that refusal per arm.
- Phase 14 also unregistered codebase-memory-mcp (it is in `probe_registry` only).
- No production part reports `cache_hit`; only `fake_llm_caller.py:48` does. So no real A/A run can persist a floor yet (RIG §AA.2).

**Out of scope:**
- a project license (HotpotQA CC BY-SA 4.0; see Deferred);
- REST/MCP routes for floors or ledger history (Phase 16);
- per-tool MCP input schemas (see D-18).
</domain>

<decisions>
## Implementation Decisions

### A. Packaging and the import boundary (TOOL-01, SC1)

- **D-01 (TOOL-01, ship the data):**
  - The wheel ships the fixture corpus and eval bundles as package data:
    - add `"databasise.tools"` to `packages`;
    - add package data `databasise = ["evidence/eval-bundles/**/*", "tests/fixtures/corpus/**/*", "tests/fixtures/eval-corpus/**/*"]`.
  - The version has one source: `dynamic = ["version"]` with `version = {attr = "databasise.__version__"}`, and `rest.py:363` uses `__version__`.
  - The `mcp` extra is bounded: `mcp>=2.2.0,<3`.
  - `uv.lock` is regenerated.
  - The parity CLIs cannot be excluded (the launcher imports `parity.import_index`). Their docstrings state that they need a source checkout (`v1/.venv`, the v1 index).
  - The packaging test copies the tree to `tmp_path` and builds there with `uv build --offline --wheel`, so no `build/` or egg-info lands in the repo.
  - Basis: CONTRACT §10 (the eval instrument precedes every claim); §18.3 (the CLI is a peer client of the installed product).
- **D-02 (SC1, the import-boundary scan):** `check_import_boundary` is fixed in five ways:
  - it skips any path whose parts start with `.`, or include `site-packages`, `build` or `dist`;
  - it reports a file that raises `SyntaxError`, `UnicodeDecodeError` or `ValueError` as a violation of kind `unparseable`;
  - it treats calls to a name bound by `from importlib import import_module [as x]` as dynamic imports;
  - it matches the two driver exclusions by resolved path, not filename;
  - it gets argparse.
  - When `repo_root/v1` is absent (a wheel), the provenance check prints one stderr line saying it was not checked, and the exit code follows the import-boundary result alone.

### B. CLI contract (TOOL-02, 03, 04, 05, SC2)

- **D-03 (TOOL-04, one exit-code table for every offline CLI):**
  - `0`: done, or estimate only.
  - `1`: named refusal, as one stderr line `ClassName: message`.
  - `2`: bad arguments (argparse).
  - `3`: ran but inconclusive.
  - Every `main()` returns the int. Test wording "SystemExit code 1" means "returns 1".
  - The shared refusal helper lives outside `launcher`, which imports `parity.import_index` at module level, so placing it there risks a cycle.
  - aa_run maps only named ValueError subclasses to 1, never a bare ValueError.
  - `remint._REPO_EVAL_DIR` may be renamed. The simulation passed all of `tests/eval`, including LRAG-15.
- **D-04 (TOOL-05 and SC2, spend nothing without `--spend`):**
  - The dry-run default covers `build_hipporag_index` and `remint` (TOOL-05's text). It also covers `run_arm`, `storage_audit`, `run_comparison` and `run_cross_modality`, because SC2 says every offline CLI.
  - A dry run makes no provider call, takes no lock and writes nothing. It prints its estimate and exits 0.
  - The 11 unprotected test cases that run those CLIs gain `--spend`: `test_cli_builder_refusals`, `test_parity_cli_store_lock`, `test_storage_audit` and `test_launch_refusals`.
  - The simulation found no protected conflict.
  - The TOOL-05 row's text is read as covering all six CLIs. REQUIREMENTS.md is not edited; the verification report records the reading.
- **D-05 (TOOL-02, M-04 and M-01):**
  - **M-04:** option (b), already decided in Phase 11. Re-importing `v1/.corpus_working_dir` is not the sanctioned path; the `lightrag/v1-index-sync` node is. `--v1-working-dir` stays as a plain pass-through.
  - **M-01:** option (a). The literal `launcher.DEFAULT_WORKSPACE` stays. `import_index` prints the derived workspace and its source ("derived from parity corpus snapshot …"), and a test pins `launcher.DEFAULT_WORKSPACE == import_index._import_workspace()`.
  - argparse runs before the store lock, so `--help` takes no lock.
- **D-06 (TOOL-03, verify_import):**
  - A v1 graph that is present while the v2 graph is absent is a `graph-topology` violation.
  - The `refused` result's assertion becomes `"precondition"`, added to the Literal.

### C. Parity and audit tools (TOOL-06 to TOOL-10)

- **D-07 (TOOL-06, run_comparison):**
  - A partial, degraded or cyclic decomposed run is reported as `inconclusive` with exit 3, never `completed`.
  - The parity-audit lane's full design stands (see `p15-study.txt`, parity-audit lane).
- **D-08 (TOOL-07, G-27 and IN-01):**
  - **G-27:** the v1 arm calls v1's own public `aquery_llm` once. `aquery` is only a wrapper over it (`v1/lightrag/lightrag.py:2077-2108`), and this matches Phase 11 D-16 ("match v1").
  - A `"failure"` status with `metadata.failure_reason == "no_results"` (`lightrag.py:2437-2451`) is a legitimate empty retrieval. It is reported as empty ids plus v1's `fail_response` answer, exactly what `aquery` returns.
  - Exit 1 only for v1's exception path (`lightrag.py:2467-2480`).
  - **IN-01** (a missing `.env.parity` read as empty) is reversed in `v1_arm` only: a missing env file there is a named refusal. The corpus adapter keeps its current behaviour (LRAG-06).
  - Never read the env file in tests; use a temp path.
- **D-09 (TOOL-08, storage_audit):**
  - storage_audit exits non-zero and prints `partial` or `cycle` when the audit run is not complete.
  - HippoRAG can be audited.
  - The parity-audit lane's design stands.
- **D-10 (TOOL-09, M-08, cross-modality arms):**
  - The §18.4 capability selectors stay.
  - Before any spend, the CLI checks that each selector resolves to the named wiring id (Phase 13 gave each arm its own `wiring_id`/`arm_id`), and refuses by name otherwise.
  - The same check applies to `corpus_ingest._ARM_SELECTORS` (`corpus_ingest.py:76-78`), which aa_run reuses. The dictionary's name and values stay (LRAG-15).
  - Preflight refuses an unusable workspace without writing anything.
- **D-11 (TOOL-10, run_wiring):**
  - `databasise.run_wiring` canonicalises the wiring before executing it.
  - The test puts `2**70` at the top level of the wiring. Inside a node config it is already refused.

### D. Evaluation and evidence records (TOOL-11 to TOOL-15)

- **D-12 (TOOL-11, G-34):**
  - Eval ingest never touches the operator corpus.
  - Under M-04(b) the operator corpus is `<store_root>/<workspace>/lightrag-v1`. The test's real assertion is that the spied v1 `working_dir` lies under the eval root.
- **D-13 (TOOL-12, G-19, calibration floors):**
  - **Refusals.** Calibration refuses a pass that yields no node traces, or that is otherwise unusable.
  - **Storage.** A usable two-sided floor is persisted in `<store_root>/floors.db`, following the `jobs_store.py` pattern.
  - **Key.** The floor is keyed on the traces' own `wiring_instance_hash`. Promote looks it up through the resolved traces' `arm_instance_hashes`, never by recomputing a hash.
  - **The gate lifts in two stages:**
    - an arm with no floor, or a stale floor, still raises `GateNotCalibratedError`;
    - an arm with a valid floor proceeds to the RIG §F3.2 posture, where a retrieval-side change raises `GateVerbNotBuiltError` until the comparison runner exists.
  - **No new refusal class,** so the SEAM-04 and SEAM-14 catalogue tests are untouched.
  - **LEDG-06 stays true on the floor path.** Deriving the mutation class uses `Ledger.open_existing(read_only=True)`, not `with Ledger(...)`, so no `ledger.db` is created.
  - **The test can fail first.** It asserts that the outcome is "not `GateNotCalibratedError`" for an arm with a floor, and adds the `run_b = run_a - 0.1` case.
  - **Recorded limits:**
    - no production part reports `cache_hit`, so no real A/A run can persist a floor yet;
    - only an engine started on the eval store root reads its floors.
- **D-14 (TOOL-13):**
  - The bundle content hash includes question text and `gold_document_ids`.
  - This is safe: `load_bundle` checks drift by the bytes' checksum, not `content_hash` (`bundle.py:417-433`).
- **D-15 (TOOL-14, EV-02):**
  - AI-recorded causes are accepted and shown with `recorded_by` in the verdict.
  - The basis is CONTRACT §5 line 308 ("name its declared deviations explicitly"), not line 364.
- **D-16 (TOOL-15, MODAL-05):**
  - MODAL-05 is marked discharged by the 2026-09-10 run. Both records state that Phase 12 changed the HippoRAG path since then.
  - `f07_report.main()` writes `render_f07_record(default_registry())`. Rendering from `probe_registry()` raises ValueError.
  - The codebase-memory-mcp row stays "admitted, not registered".
  - The parity, Falsifier 2, F-07 and cross-modality records render only states they read, compute verdicts and exit codes from results, and cite paths that exist.

### E. Registry, admission and MCP (TOOL-16 to TOOL-20)

- **D-17 (TOOL-16, admission at load):**
  - One `admit_registry()` enforces §8 conditions 7, 10 and 11 for every opaque part, plus the requirement's effect, kind and scope checks.
  - It is called by `default_registry()`, and by `Databasise.__init__` for an injected registry.
  - Shared scope is refused on `kind == "opaque"` only. Refusing on `structural_depth` would make `test_blast_radius`'s parse-time rule unreachable.
  - The admission evidence strings are not reworded (LRAG-12).
  - Test case 1 (an `as_of` effect) injects the effect after registration.
  - **Owner grant needed:**
    - The name-match check refuses WIRE-13's protected `databasise/tests/seam/test_seam_events.py::test_an_ingest_with_a_mutating_part_returns_one_seam_event`. That test attaches `lightrag/full-ingest@0.2.0`'s admission record to `test/seam-events-mutator@1.0.0`.
    - Edit: that record becomes `dataclasses.replace(<full-ingest record>, part_name_at_version="test/seam-events-mutator@1.0.0")`.
    - The only product-side alternative is dropping the name-match check, which leaves defect D2 open. It is rejected.
- **D-18 (TOOL-19):**
  - MCP tools keep the single `args` input and the generic output schema, and each gains a non-empty description with no plan references.
  - The count is ten tools (`mcp/tools.py:79-90`), not nine.
  - There is no Phase 16-18 conflict: those phases use REST, and CONN-01 only needs each new operation to have an MCP tool or be recorded as REST-only.
- **D-19 (TOOL-18, codebase-memory-mcp):**
  - The part stays unregistered (Phase 14 D-13) and keeps declaring `mutates_store`.
  - The adapter refuses mutating tools by name and times out on launch.
  - The effects test runs in the subset direction: every recorded touch is declared.
  - The citation is CONTRACT §14 line 623, not §2:214.
- **D-20 (TOOL-17):**
  - Already met by removal (226b2cf, Phase 10 D-15). The row's check is `databasise/tests/test_removed_stores_absent.py`, with fail-first recorded at `226b2cf^`.
  - No plan code. The "if kept" branch of the row text does not apply.
- **D-21 (TOOL-20):**
  - The registry lane's stale-docstring list stands.
  - `CROSS-MODALITY-EVIDENCE.md`, `FALSIFIER-2-EVIDENCE.md` and `falsifier2.py` belong to the same plan as D-16.

### F. Execution rules

- **D-22 (fail-first):**
  - Every row test is a new node in an unprotected file and fails on pre-fix code by plain AssertionError.
  - Rows already met record `record-fail --at <fixing commit>^`.
  - The orchestrator does all ledger work.
- **D-23 (protected checks):**
  - Each plan runs every protected `test_ref` file its code touches.
  - A protected test that breaks first gets a product-side fix. Only if none exists does it become an owner `grant-check-edit` item with the exact edit.
  - The only known item is WIRE-13 (D-17).
- **D-24 (no spend, no secrets):**
  - No test or probe spends provider tokens or reads `v1/.env.parity` or `v1/parity-env.txt`.
  - Every `--spend` path is tested with stub clients or by its refusal.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `docs/system-model/CONTRACT.md`. Frozen.
  - §5: the verb ladder, the A/A floor, line 308.
  - §7: provenance.
  - §8: conditions 7, 10 and 11.
  - §10: eval precedes claims.
  - §14: line 623.
  - §18.3 and §18.4.
- `docs/system-model/RIG.md`. §AA.2 (cache_hit and the A/A floor); §F3.2 (posture); §RUN.1.
- `.planning/REQUIREMENTS.md`, TOOL-01..20.
- `.planning/ROADMAP.md`, Phase 15.
- `.planning/phases/14-promotion-ledger/14-CONTEXT.md`. D-04 (the gate refusal), D-08 (with the read-path narrowing in 14-REVIEW-DISPOSITION.md) and D-13 (codebase-memory-mcp).
- `.planning/phases/11-lightrag-corpus-path/` CONTEXT: M-04(b) and D-16.
- The study notes in the session scratchpad: `p15-study.txt` and `p15-critic.txt`.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `jobs_store.py`: the sqlite store pattern for `floors.db`.
- `Ledger.open_existing(read_only=True)` (`ledger.py:163`).
- `GateNotCalibratedError` and `GateVerbNotBuiltError` (`seam/refusals.py`).
- `default_registry()` and `probe_registry()`; `render_f07_record(registry)`.
- `test_removed_stores_absent.py`: the TOOL-17 check.

### Integration Points
- The promote gate: `engine.py:2385` and `2396-2414`.
- `corpus_ingest._ARM_SELECTORS` (`corpus_ingest.py:76-78`), reused by aa_run.
- `import_index.py:710-721`: the argv handling and the lock.
- `v1/lightrag/lightrag.py:2077-2108`, `2437-2451` and `2467-2480`: v1 aquery_llm.
</code_context>

<specifics>
## Specific Ideas

- `test_packaging` fails on a cold uv cache. It must skip with a named reason when `uv build --offline` cannot resolve. That skip must never be counted as a pass.
- From a wheel, `remint --spend` and `.comparison_results` would write into site-packages (`run_comparison.py:657`, `run_cross_modality.py:362`). The D-04 dry-run default and the source-checkout docstrings cover this. Record it in the verification report.
</specifics>

<deferred>
## Deferred Ideas

- **A project LICENSE** and the HotpotQA CC BY-SA 4.0 attribution. These need an owner decision before any wheel is distributed.
- **Per-tool MCP input and output schemas.** This would affect every MCP client.
- **Floors readable from an engine not started on the eval store root.**
- **A production part that reports `cache_hit`,** so that real A/A floors can be persisted.
</deferred>

---

*Phase: 15-offline-tooling-packaging*
*Context gathered: 2026-10-21*
